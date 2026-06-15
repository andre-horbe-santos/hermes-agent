"""Terminal input processing helpers — bracketed paste, mouse leak stripping, key bindings."""

from __future__ import annotations

import logging
import os
import re
import sys
import time

logger = logging.getLogger(__name__)


def _strip_leaked_bracketed_paste_wrappers(text: str) -> str:
    """Strip leaked bracketed-paste wrapper markers from user-visible text.

    Defensive normalization for cases where terminal/prompt_toolkit parsing
    fails and bracketed-paste markers end up in the buffer as literal text.

    We strip canonical wrappers unconditionally and also handle degraded
    visible forms like ``[200~`` / ``[201~`` and ``00~`` / ``01~`` when they
    look like wrapper boundaries, not arbitrary user content.
    """
    if not text:
        return text

    text = (
        text.replace("\x1b[200~", "")
        .replace("\x1b[201~", "")
        .replace("^[[200~", "")
        .replace("^[[201~", "")
    )
    text = re.sub(r"(^|[\s\n>:\]\)])\[200~", r"\1", text)
    text = re.sub(r"\[201~(?=$|[\s\n<\[\(\):;.,!?])", "", text)
    text = re.sub(r"(^|[\s\n>:\]\)])00~", r"\1", text)
    text = re.sub(r"01~(?=$|[\s\n<\[\(\):;.,!?])", "", text)
    return text


def _apply_bracketed_paste_timeout_patch() -> None:
    """Patch prompt_toolkit to recover from torn bracketed-paste sequences.

    prompt_toolkit's ``Vt100Parser.feed()`` buffers all input while waiting
    for the ESC[201~ end mark.  If a terminal drops that end mark (terminal
    race, torn write, SSH glitch, macOS sleep/wake), input appears frozen
    forever — the only recovery used to be killing the tab.

    This patch wraps ``Vt100Parser.feed`` so that bracketed-paste mode
    flushes buffered content as a normal ``BracketedPaste`` event after
    ``_BP_TIMEOUT_S`` seconds without an end marker, then resumes normal
    parsing.  See upstream issue #16263.

    The patch is idempotent — repeated calls are no-ops via the
    ``_hermes_bp_timeout_patched`` sentinel on the module.
    """
    try:
        import prompt_toolkit.input.vt100_parser as _vt100_mod
        from prompt_toolkit.keys import Keys as _PtKeys
        from prompt_toolkit.key_binding.key_processor import KeyPress as _PtKeyPress

        if getattr(_vt100_mod, "_hermes_bp_timeout_patched", False):
            return

        _BP_TIMEOUT_S = 2.0  # max time to wait for ESC[201~ before flushing

        def _patched_vt100_feed(self_parser, data: str) -> None:
            if self_parser._in_bracketed_paste:
                self_parser._paste_buffer += data
                end_mark = "\x1b[201~"

                if end_mark in self_parser._paste_buffer:
                    end_index = self_parser._paste_buffer.index(end_mark)
                    paste_content = self_parser._paste_buffer[:end_index]
                    self_parser.feed_key_callback(
                        _PtKeyPress(_PtKeys.BracketedPaste, paste_content)
                    )
                    self_parser._in_bracketed_paste = False
                    remaining = self_parser._paste_buffer[
                        end_index + len(end_mark):
                    ]
                    self_parser._paste_buffer = ""
                    self_parser._hermes_bp_start = None
                    if remaining:
                        _patched_vt100_feed(self_parser, remaining)
                else:
                    bp_start = getattr(self_parser, "_hermes_bp_start", None)
                    now = time.monotonic()
                    if bp_start is None:
                        self_parser._hermes_bp_start = now
                    elif now - bp_start > _BP_TIMEOUT_S:
                        paste_content = self_parser._paste_buffer
                        self_parser._in_bracketed_paste = False
                        self_parser._paste_buffer = ""
                        self_parser._hermes_bp_start = None
                        if paste_content:
                            self_parser.feed_key_callback(
                                _PtKeyPress(_PtKeys.BracketedPaste, paste_content)
                            )
                            logger.warning(
                                "Bracketed-paste timeout (%.1fs) — flushed %d bytes "
                                "without end mark. Terminal may have dropped ESC[201~ "
                                "(see #16263).",
                                now - bp_start,
                                len(paste_content),
                            )
            else:
                # Normal mode — re-inline prompt_toolkit's normal feed path.
                # Calling the original feed here would double-buffer after the
                # bracketed-paste entry transition.
                for i, c in enumerate(data):
                    if self_parser._in_bracketed_paste:
                        _patched_vt100_feed(self_parser, data[i:])
                        break
                    self_parser._input_parser.send(c)

        _vt100_mod.Vt100Parser.feed = _patched_vt100_feed
        _vt100_mod._hermes_bp_timeout_patched = True
        logger.debug("Applied Vt100Parser bracketed-paste timeout patch (#16263)")
    except Exception as exc:  # noqa: BLE001 — defensive: never break startup
        logger.debug("Bracketed-paste timeout patch skipped: %s", exc)


# Cursor Position Report (CPR / DSR) response, format ``ESC[<row>;<col>R``.
# prompt_toolkit's _on_resize() + renderer send ``ESC[6n`` queries to the
# terminal; under resize storms or tab switches the terminal's reply can
# race past the input parser and end up in the input buffer as literal
# text (see issue #14692). Also matches the visible-form ``^[[<row>;<col>R``
# that appears when the ESC byte was stripped by a prior filter.
_DSR_CPR_ESC_RE = re.compile(r"\x1b\[\d+;\d+R")
_DSR_CPR_VISIBLE_RE = re.compile(r"\^\[\[\d+;\d+R")
_SGR_MOUSE_ESC_RE = re.compile(r"\x1b\[<\d+;\d+;\d+[Mm]")
_SGR_MOUSE_VISIBLE_RE = re.compile(r"\^\[\[<\d+;\d+;\d+[Mm]")
# Some terminals/filters can drop ESC and literal "^[[", leaving only
# "<btn;col;rowM" fragments in the buffer. Keep this broad on purpose:
# these fragments are extremely unlikely to be intentional user input, and
# stripping them is better than sending corrupted prompts.
_SGR_MOUSE_BARE_RE = re.compile(r"<\d+;\d+;\d+[Mm]")

_TERMINAL_INPUT_MODE_RESET_SEQ = (
    "\x1b[?1006l"  # disable SGR mouse
    "\x1b[?1003l"  # disable any-motion tracking
    "\x1b[?1002l"  # disable button-motion tracking
    "\x1b[?1000l"  # disable click tracking
    "\x1b[?1004l"  # disable focus events
    "\x1b[?2004l"  # disable bracketed paste
    "\x1b[?1049l"  # leave alt screen (if stuck there)
    "\x1b[<u"      # pop kitty keyboard mode
    "\x1b[>4m"     # reset modifyOtherKeys
    "\x1b[0m"      # reset text attributes
    "\x1b[?25h"    # ensure cursor visible
)


def _preserve_ctrl_enter_newline() -> bool:
    """Detect environments where Ctrl+Enter must produce a newline, not submit.

    Windows Terminal, WSL, SSH sessions, Ghostty, and some modern terminals
    deliver Ctrl+Enter/Ctrl+J as bare LF (c-j). On those terminals c-j must
    NOT be bound to submit;
    binding it to submit makes Ctrl+Enter (intended as 'newline like Alt+Enter')
    submit instead. Local POSIX TTYs that deliver Enter as LF (docker exec,
    some thin PTYs without SSH) still need c-j bound to submit, so we keep
    that binding for those.

    See issue #22379.
    """
    if sys.platform == "win32":
        return True
    if any(os.environ.get(v) for v in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY")):
        return True
    if os.environ.get("WT_SESSION"):
        return True
    if os.environ.get("GHOSTTY_RESOURCES_DIR") or os.environ.get("GHOSTTY_BIN_DIR"):
        return True
    if os.environ.get("TERM", "").lower() == "xterm-ghostty":
        return True
    if os.environ.get("TERM_PROGRAM", "").lower() == "ghostty":
        return True
    if "microsoft" in os.environ.get("WSL_DISTRO_NAME", "").lower():
        return True
    # WSL detection — env vars can be scrubbed under sudo, also peek /proc.
    for p in ("/proc/version", "/proc/sys/kernel/osrelease"):
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                if "microsoft" in f.read().lower():
                    return True
        except OSError:
            continue
    return False


def _bind_prompt_submit_keys(kb, handler) -> None:
    """Bind terminal Enter forms to the submit handler.

    Enter is always submit. On POSIX we also bind c-j (LF) to submit because
    some thin PTYs (docker exec, certain SSH flavors) deliver Enter as LF
    instead of CR — without this, Enter appears dead on those terminals.

    Exception: on Windows, WSL, SSH sessions, Windows Terminal, and Ghostty,
    c-j is the wire encoding of Ctrl+Enter (a distinct keystroke from
    plain Enter / c-m). We leave c-j unbound there so the c-j newline
    handler registered separately can fire — giving the user an
    Enter-involving newline keystroke without terminal settings changes.
    See _preserve_ctrl_enter_newline() and issue #22379.
    """
    kb.add("enter")(handler)
    if sys.platform != "win32" and not _preserve_ctrl_enter_newline():
        kb.add("c-j")(handler)


def _disable_prompt_toolkit_cpr_warning(app) -> None:
    """Let prompt_toolkit fall back from CPR without printing into the prompt."""
    try:
        app.renderer.cpr_not_supported_callback = None
    except Exception:
        pass


def _strip_leaked_terminal_responses_with_meta(text: str) -> tuple[str, bool]:
    """Strip leaked terminal control-response sequences from user input.

    Covers Cursor Position Report (CPR / DSR) responses — ``ESC[<row>;<col>R``
    and the visible ``^[[<row>;<col>R`` form. These are replies the terminal
    sends back to queries prompt_toolkit makes during ``_on_resize`` /
    ``_request_absolute_cursor_position``. When the input parser drops one
    (resize storms, multiplexer focus changes, slow PTYs) the response
    lands in the input buffer as literal text and corrupts what the user
    typed.

    Also strips leaked SGR mouse-report fragments (``ESC[<...M/m`` and
    degraded visible forms). Returns ``(cleaned_text, had_mouse_reports)``
    so callers can trigger an in-place terminal mode recovery when needed.
    """
    if not text:
        return text, False

    has_esc = "\x1b[" in text
    has_visible = "^[" in text
    has_bare_mouse = "<" in text and ";" in text and ("M" in text or "m" in text)
    if not (has_esc or has_visible or has_bare_mouse):
        return text, False

    had_mouse_reports = False

    if has_esc:
        text = _DSR_CPR_ESC_RE.sub("", text)
        text, count = _SGR_MOUSE_ESC_RE.subn("", text)
        had_mouse_reports = had_mouse_reports or count > 0

    if has_visible:
        text = _DSR_CPR_VISIBLE_RE.sub("", text)
        text, count = _SGR_MOUSE_VISIBLE_RE.subn("", text)
        had_mouse_reports = had_mouse_reports or count > 0

    if has_bare_mouse:
        text, count = _SGR_MOUSE_BARE_RE.subn("", text)
        had_mouse_reports = had_mouse_reports or count > 0

    return text, had_mouse_reports


def _strip_leaked_terminal_responses(text: str) -> str:
    """Compatibility wrapper returning only cleaned text."""
    cleaned, _ = _strip_leaked_terminal_responses_with_meta(text)
    return cleaned
