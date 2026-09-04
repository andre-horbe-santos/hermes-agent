"""Extract a compact design system from a public web page.

The tool intentionally reports evidence found in HTML/CSS instead of trying to
infer a brand system from screenshots.  It is useful for turning reference
sites into reusable design tokens without copying their content or assets.
"""

from __future__ import annotations

import html
import ipaddress
import json
import re
import socket
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from tools.registry import registry, tool_error
from hermes_constants import get_hermes_home


_HEX_RE = re.compile(r"(?<![\w#])#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})(?![\w])")
_FONT_RE = re.compile(r"font-family\s*:\s*([^;}{]+)", re.I)
_IMPORT_RE = re.compile(r"@import\s+(?:url\()?['\"]?([^'\")\s]+)", re.I)
_GOOGLE_FONT_RE = re.compile(r"fonts\.googleapis\.com/css[^\"'\s>]*", re.I)
_VAR_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;}{]+)", re.I)
_FONT_URL_RE = re.compile(r"fonts\.googleapis\.com/css2?[^\"'\s>]*", re.I)

_BLOCKED_HOSTS = {"localhost", "localhost.localdomain"}


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.styles: list[str] = []
        self.stylesheets: list[str] = []
        self.font_links: list[str] = []
        self._in_style = False
        self._style_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs_map = {str(k).lower(): str(v) for k, v in attrs if k and v is not None}
        if tag.lower() == "style":
            self._in_style = True
            self._style_parts = []
        if tag.lower() == "link":
            href = attrs_map.get("href", "")
            rel = attrs_map.get("rel", "").lower().split()
            if href and "stylesheet" in rel:
                self.stylesheets.append(href)
            if href and ("fonts.googleapis.com" in href or "fonts.gstatic.com" in href):
                self.font_links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "style" and self._in_style:
            self.styles.append("".join(self._style_parts))
            self._in_style = False
            self._style_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self._style_parts.append(data)


def _safe_url(raw_url: str, base: str | None = None) -> str:
    url = urljoin(base or "", raw_url.strip())
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("only public http(s) URLs are supported")
    host = parsed.hostname.lower().rstrip(".")
    if host in _BLOCKED_HOSTS:
        raise ValueError("local destinations are not allowed")
    try:
        addresses = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"could not resolve host: {host}") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("private or local destinations are not allowed")
    return url


_MAX_REDIRECTS = 5


def _fetch(client: httpx.Client, url: str, base: str | None = None) -> tuple[str, str]:
    # follow_redirects=True on the client would let httpx chase a redirect to
    # a private/internal address *before* _safe_url ever sees it — the
    # request already happened by the time we could reject it. Each hop is
    # validated here, before it is requested, instead.
    next_url = _safe_url(url, base)
    for _ in range(_MAX_REDIRECTS + 1):
        response = client.get(next_url, follow_redirects=False)
        if response.is_redirect:
            location = response.headers.get("location")
            if not location:
                response.raise_for_status()
            next_url = _safe_url(location, next_url)
            continue
        response.raise_for_status()
        return _safe_url(str(response.url)), response.text
    raise ValueError("too many redirects")


def _clean_font(value: str) -> str:
    value = value.strip().strip("\"'")
    value = re.sub(r"\s*!important\s*$", "", value, flags=re.I)
    return value


def _extract_tokens(css_text: str, font_links: list[str]) -> dict:
    colors = [c.upper() for c in _HEX_RE.findall(css_text)]
    color_counts = Counter(colors)
    variables = {}
    for name, value in _VAR_RE.findall(css_text):
        variables[name] = value.strip()

    fonts: Counter[str] = Counter()
    for raw in _FONT_RE.findall(css_text):
        for family in raw.split(","):
            cleaned = _clean_font(family)
            if cleaned and cleaned.lower() not in {"inherit", "initial", "unset", "sans-serif", "serif", "monospace"}:
                fonts[cleaned] += 1

    google_fonts = []
    for link in font_links + _GOOGLE_FONT_RE.findall(css_text):
        decoded = html.unescape(link)
        for family in re.findall(r"family=([^&:]+)", decoded):
            google_fonts.append(family.replace("+", " "))
    for family in google_fonts:
        fonts[family] += 3

    def variable_match(*terms: str) -> str | None:
        for name, value in variables.items():
            low = name.lower()
            if any(term in low for term in terms) and _HEX_RE.search(value):
                return _HEX_RE.search(value).group(0).upper()
        return None

    primary = variable_match("primary", "brand", "main")
    accent = variable_match("accent", "secondary", "highlight")
    background = variable_match("background", "surface", "bg")
    text = variable_match("text", "foreground", "font")
    return {
        "fonts": [{"family": name, "evidence_count": count} for name, count in fonts.most_common(12)],
        "google_fonts": list(dict.fromkeys(google_fonts))[:12],
        "colors": [{"hex": color, "evidence_count": count} for color, count in color_counts.most_common(24)],
        "roles": {k: v for k, v in {"primary": primary, "accent": accent, "background": background, "text": text}.items() if v},
        "css_variables": dict(list(variables.items())[:100]),
    }


def _design_system_path(page_url: str) -> Path:
    host = (urlparse(page_url).hostname or "site").lower().rstrip(".")
    slug = re.sub(r"[^a-z0-9.-]+", "-", host).strip("-.") or "site"
    return get_hermes_home() / "design-systems" / f"{slug}.json"


def _save_design_system(result: dict) -> str | None:
    """Persist one canonical JSON file per site, returning its path."""
    try:
        path = _design_system_path(result["url"])
        path.parent.mkdir(parents=True, exist_ok=True)
        previous = {}
        if path.exists():
            try:
                previous = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                previous = {}
        seen = list(previous.get("pages_seen") or [])
        if result["url"] not in seen:
            seen.append(result["url"])
        result["pages_seen"] = seen[-50:]
        result["saved_path"] = str(path)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return str(path)
    except OSError:
        return None


def design_extract(url: str, max_stylesheets: int = 20, timeout: float = 20.0) -> str:
    """Fetch *url*, persist its design system by domain, and return JSON."""
    try:
        with httpx.Client(
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": "Hermes Design Extractor/1.0"},
            follow_redirects=False,
        ) as client:
            page_url, page = _fetch(client, url)
            parser = _PageParser()
            parser.feed(page)
            css_parts = list(parser.styles)
            source_urls = [page_url]
            errors = []
            for raw_css_url in parser.stylesheets[:max_stylesheets]:
                try:
                    css_url, css = _fetch(client, raw_css_url, page_url)
                    css_parts.append(css)
                    source_urls.append(css_url)
                except Exception as exc:
                    errors.append({"url": urljoin(page_url, raw_css_url), "error": str(exc)[:180]})

            tokens = _extract_tokens("\n".join(css_parts), parser.font_links)
            confidence = "high" if len(source_urls) > 1 and (tokens["fonts"] or tokens["colors"]) else "medium" if tokens["fonts"] or tokens["colors"] else "low"
            result = {
                "url": page_url,
                "confidence": confidence,
                "fonts": tokens["fonts"],
                "google_fonts": tokens["google_fonts"],
                "colors": tokens["colors"],
                "roles": tokens["roles"],
                "css_variables": tokens["css_variables"],
                "sources": source_urls,
                "errors": errors,
                "notes": [
                    "Tokens are extracted from accessible HTML/CSS; dynamic canvas or image-only colors are not inferred.",
                    "Frequency is evidence, not a guarantee of brand-semantic role unless a CSS variable exposes that role.",
                ],
            }
            result["collected_at"] = datetime.now(timezone.utc).isoformat()
            _save_design_system(result)
            return json.dumps(result, ensure_ascii=False)
    except (httpx.HTTPError, ValueError, UnicodeError) as exc:
        return tool_error(f"design extraction failed: {exc}")


DESIGN_EXTRACT_SCHEMA = {
    "name": "cor_fonte_site",
    "description": (
        "Inspect a public web page and extract evidence-backed design tokens: fonts, "
        "Google Fonts, hexadecimal colors, CSS variable roles, source stylesheets, "
        "and confidence. Persist one JSON design system per domain for reuse. "
        "It does not copy page content or assets."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Public http(s) URL to inspect."},
            "max_stylesheets": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20, "description": "Maximum linked stylesheets to fetch."},
            "timeout": {"type": "number", "minimum": 3, "maximum": 60, "default": 20, "description": "Per-request timeout in seconds."},
        },
        "required": ["url"],
    },
}


registry.register(
    name="cor_fonte_site",
    toolset="web",
    schema=DESIGN_EXTRACT_SCHEMA,
    handler=lambda args, **kw: design_extract(
        args.get("url", ""),
        max_stylesheets=args.get("max_stylesheets", 20),
        timeout=args.get("timeout", 20.0),
    ),
    emoji="🎨",
    max_result_size_chars=100_000,
)
