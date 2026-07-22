from __future__ import annotations

import copy
import importlib.util
import sys
import types
from pathlib import Path

import pytest


def _load_flow_kgc_modules(monkeypatch):
    # ~/.hermes é o único clone canônico desde a consolidação (koncepto-agent-os/,
    # o clone aninhado dentro de hermes-agent/, foi removido — não tinha nenhum
    # commit exclusivo, era um ancestral desatualizado do mesmo repo).
    koncepto_root = Path(__file__).resolve().parents[3]
    flow_root = koncepto_root / "scripts" / "flow_kgc"

    monkeypatch.setenv("SUPABASE_FUNIL_URL", "http://supabase.test")
    monkeypatch.setenv("SUPABASE_FUNIL_SERVICE_ROLE_KEY", "test-service-role")
    monkeypatch.setenv("UNIPILE_DSN", "http://unipile.test")
    monkeypatch.setenv("UNIPILE_API_KEY", "test-unipile-key")

    module_names = [
        "koncepto_agent_os",
        "koncepto_agent_os.scripts",
        "koncepto_agent_os.scripts.flow_kgc",
        "koncepto_agent_os.scripts.flow_kgc.db",
        "koncepto_agent_os.scripts.flow_kgc.flow_steps",
        "koncepto_agent_os.scripts.flow_kgc.runner",
    ]
    for name in module_names:
        sys.modules.pop(name, None)

    pkg = types.ModuleType("koncepto_agent_os")
    pkg.__path__ = [str(koncepto_root)]
    sys.modules[pkg.__name__] = pkg

    scripts_pkg = types.ModuleType("koncepto_agent_os.scripts")
    scripts_pkg.__path__ = [str(koncepto_root / "scripts")]
    sys.modules[scripts_pkg.__name__] = scripts_pkg

    flow_pkg = types.ModuleType("koncepto_agent_os.scripts.flow_kgc")
    flow_pkg.__path__ = [str(flow_root)]
    sys.modules[flow_pkg.__name__] = flow_pkg

    def _load(name: str, path: Path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    flow_steps = _load("koncepto_agent_os.scripts.flow_kgc.flow_steps", flow_root / "flow_steps.py")
    db = _load("koncepto_agent_os.scripts.flow_kgc.db", flow_root / "db.py")
    runner = _load("koncepto_agent_os.scripts.flow_kgc.runner", flow_root / "runner.py")
    return runner, db, flow_steps


class FakeFlowKGCDB:
    def __init__(self, entry: dict):
        self.entries = {entry["id"]: copy.deepcopy(entry)}

    def _entry(self, entry_id: str) -> dict:
        return self.entries[entry_id]

    def _patch(self, _table: str, patch: dict, _col: str, entry_id: str) -> dict:
        self._entry(entry_id).update(copy.deepcopy(patch))
        return self.get_entry(entry_id)

    def _now(self) -> str:
        return "2026-07-09T12:00:00Z"

    def _get(self, _table: str, _params: dict | None = None) -> list:
        return []

    def get_entry(self, entry_id: str) -> dict:
        return copy.deepcopy(self._entry(entry_id))

    def list_queue(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        operator_id: str | None = None,
        select: str | None = None,
    ) -> list:
        rows = list(self.entries.values())
        if status and status != "all":
            rows = [row for row in rows if row.get("status") == status]
        if operator_id and operator_id != "all":
            rows = [row for row in rows if row.get("operator_id") == operator_id]
        return [copy.deepcopy(row) for row in rows[offset:offset + limit]]

    def get_due_entries(self) -> list:
        rows = []
        for row in self.entries.values():
            if row.get("status") != "active":
                continue
            if row.get("step_status") in {"waiting_approval", "done", "failed", "skipped"}:
                continue
            rows.append(copy.deepcopy(row))
        return rows

    def activate(self, entry_id: str) -> dict:
        entry = self._entry(entry_id)
        entry.update({"status": "active", "step_status": "pending", "next_run_at": "now"})
        return self.get_entry(entry_id)

    def set_channel(self, entry_id: str, channel: str, wa_chat_id: str | None, ln_chat_id: str | None, flow_id: str) -> dict:
        entry = self._entry(entry_id)
        entry.update({
            "channel": channel,
            "wa_chat_id": wa_chat_id,
            "ln_chat_id": ln_chat_id,
            "flow_id": flow_id,
        })
        return self.get_entry(entry_id)

    def advance_step(self, entry_id: str) -> dict:
        entry = self._entry(entry_id)
        entry["current_step"] += 1
        entry["step_status"] = "pending"
        entry["next_run_at"] = "now"
        entry["event_detected"] = False
        return self.get_entry(entry_id)

    def schedule_next(self, entry_id: str, _delay_sec: int) -> dict:
        return self.advance_step(entry_id)

    def jump_to_step(self, entry_id: str, step_idx: int) -> dict:
        entry = self._entry(entry_id)
        entry["current_step"] = step_idx
        entry["step_status"] = "pending"
        entry["next_run_at"] = "now"
        entry["event_detected"] = False
        return self.get_entry(entry_id)

    def jump_to_step_scheduled(self, entry_id: str, step_idx: int, _delay_sec: int) -> dict:
        return self.jump_to_step(entry_id, step_idx)

    def set_waiting(self, entry_id: str, wait_type: str, _timeout_days: int, **_kwargs) -> dict:
        entry = self._entry(entry_id)
        entry["step_status"] = wait_type
        entry["pending_draft"] = None
        entry["reply_received"] = None
        return self.get_entry(entry_id)

    def set_pending_approval(self, entry_id: str, draft: str, stage: int, reply_text: str, reply_channel: str = "linkedin") -> dict:
        entry = self._entry(entry_id)
        msgs = list(entry.get("messages_sent") or [])
        msgs = [m for m in msgs if not (isinstance(m, dict) and m.get("_type") == "pending_channel")]
        msgs.append({"_type": "pending_channel", "channel": reply_channel})
        entry.update({
            "step_status": "waiting_approval",
            "pending_draft": draft,
            "pending_draft_at": "now",
            "reply_received": reply_text,
            "messages_sent": msgs,
            "next_run_at": "later",
            "playbook_stage": stage,
        })
        return self.get_entry(entry_id)

    def log_message(self, entry_id: str, channel: str, text: str) -> None:
        entry = self._entry(entry_id)
        msgs = list(entry.get("messages_sent") or [])
        msgs.append({"channel": channel, "text": text, "sent_at": "now"})
        entry["messages_sent"] = msgs

    def complete(self, entry_id: str, tag: str | None = None) -> dict:
        entry = self._entry(entry_id)
        entry["status"] = "completed"
        entry["step_status"] = "done"
        if tag:
            tags = set(entry.get("tags") or [])
            tags.add(tag)
            entry["tags"] = sorted(tags)
        return self.get_entry(entry_id)

    def mark_failed(self, entry_id: str, error: str) -> dict:
        entry = self._entry(entry_id)
        entry["status"] = "failed"
        entry["step_status"] = "failed"
        entry["error_message"] = error
        return self.get_entry(entry_id)

    def add_tag(self, entry_id: str, tag: str) -> dict:
        entry = self._entry(entry_id)
        tags = set(entry.get("tags") or [])
        tags.add(tag)
        entry["tags"] = sorted(tags)
        return self.get_entry(entry_id)

    def set_ln_chat(self, entry_id: str, ln_chat_id: str) -> dict:
        self._entry(entry_id)["ln_chat_id"] = ln_chat_id
        return self.get_entry(entry_id)

    def get_operator(self, _operator_id: str) -> dict:
        return {
            "ln_account_id": "ln-account-test",
            "wa_account_id": "wa-account-test",
            "wa_notify_number": "",
        }

    def get_operator_profile(self, _operator_id: str) -> dict:
        return {}

    def get_context_block(self) -> str:
        return ""

    def get_paused_operator_ids(self) -> list[str]:
        return []

    def set_invite_pending(self, entry_id: str, note: str, draft_variants=None) -> dict:
        entry = self._entry(entry_id)
        msgs = list(entry.get("messages_sent") or [])
        msgs = [m for m in msgs if not (isinstance(m, dict) and m.get("_type") in {"pending_channel", "pending_invite"})]
        msgs.append({"_type": "pending_invite"})
        entry.update({
            "step_status": "waiting_approval",
            "pending_draft": note,
            "pending_draft_at": "now",
            "draft_variants": copy.deepcopy(draft_variants or []),
            "messages_sent": msgs,
        })
        return self.get_entry(entry_id)


def _make_entry(flow_id: str) -> dict:
    return {
        "id": f"{flow_id}-entry",
        "lead_uuid": "lead-123",
        "linkedin_id": "lead-linkedin-id",
        "linkedin_url": "https://linkedin.com/in/test-lead",
        "full_name": "Test Lead",
        "headline": "Head of Sales",
        "company_name": "Acme Industrial",
        "company_industry": "industrial automation",
        "phone_number": "",
        "email_address": "",
        "icp_match": "match",
        "signal_type": "prospect",
        "signal_score": 88,
        "flow_selected": flow_id,
        "flow_id": None,
        "channel": None,
        "operator_id": "andre",
        "wa_chat_id": None,
        "ln_chat_id": None,
        "current_step": 0,
        "step_status": "pending",
        "next_run_at": "now",
        "event_detected": False,
        "tags": [],
        "messages_sent": [],
        "status": "approved",
        "sandbox": True,
        "playbook_stage": 1,
        "pending_draft": None,
        "reply_received": None,
        "sector_insight": "",
    }


def _pump_runner_until_waiting_approval(runner, fake_db: FakeFlowKGCDB, entry_id: str, max_cycles: int = 20) -> dict:
    for _ in range(max_cycles):
        runner.run()
        entry = fake_db.get_entry(entry_id)
        if entry.get("step_status") == "waiting_approval":
            return entry
        if entry.get("status") == "failed":
            raise AssertionError(f"flow failed unexpectedly: {entry.get('error_message')}")
    raise AssertionError("flow did not reach waiting_approval in time")


def test_jefferson_followup_loop_advances_and_resets_to_wait_reply(monkeypatch):
    runner, _db_module, flow_steps = _load_flow_kgc_modules(monkeypatch)
    entry = _make_entry("kgc_i_ln")
    entry.update({
        "current_step": 13,
        "flow_id": "kgc_i_ln",
        "status": "active",
        "step_status": "pending",
        "metadata": {},
    })
    fake_db = FakeFlowKGCDB(entry)

    sandbox_sends: list[tuple[str, str, list[str] | None]] = []

    monkeypatch.setattr(runner, "db", fake_db)
    monkeypatch.setattr(runner, "_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(runner, "_notify_pending_approval", lambda *args, **kwargs: None)
    monkeypatch.setattr(runner, "_fetch_lead_signals", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(runner, "_refresh_entry_from_signals", lambda entry, _signals: entry)
    monkeypatch.setattr(runner, "_business_hours", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(runner, "_next_business_slot", lambda _kind: 0)
    monkeypatch.setattr(
        runner,
        "_haiku",
        lambda prompt, entry, signals=None, max_tokens=400, step_type="", **_kwargs: "Follow-up Jefferson",
    )
    monkeypatch.setattr(
        runner,
        "_sbx_wa_send",
        lambda lead_name, channel_icon, text, extra=None, entry=None: (
            sandbox_sends.append((channel_icon, text, list(extra or []))) or text
        ),
    )

    runner.advance(fake_db.get_entry("kgc_i_ln-entry"))

    updated = fake_db.get_entry("kgc_i_ln-entry")
    assert flow_steps.FLOWS["kgc_i_ln"]["steps"][13]["type"] == "ln_followup_loop"
    assert updated["current_step"] == 12
    assert updated["step_status"] == "pending"
    assert updated["metadata"]["follow_up_count"] == 1
    assert updated["messages_sent"] == []
    assert sandbox_sends and sandbox_sends[0][0] == "🔵 LN Follow-up 1"
    # _normalize_followup_greeting sempre prefixa saudação BRT + nome (por
    # design — ver docstring da função); só não força mais "tudo bem?" nem
    # duplica saudação quando o rascunho do LLM já vem sem uma.
    sent_text = sandbox_sends[0][1]
    assert sent_text.startswith(("Bom dia, Test,", "Boa tarde, Test,", "Boa noite, Test,"))
    assert sent_text.endswith("Follow-up Jefferson")


def test_jefferson_reaction_only_skips_to_followup_loop(monkeypatch):
    runner, _db_module, flow_steps = _load_flow_kgc_modules(monkeypatch)
    entry = _make_entry("kgc_i_ln")
    entry.update({
        "current_step": 12,
        "flow_id": "kgc_i_ln",
        "status": "active",
        "step_status": "pending",
        "channel": "linkedin",
        "ln_chat_id": "chat-123",
        "sandbox": False,
        "messages_sent": [
            {"channel": "linkedin", "text": "Mensagem anterior", "sent_at": "2026-07-08T10:00:00Z"},
            {"_type": "wait_meta", "wait_type": "waiting_reply", "timeout_at": "2026-07-15T10:00:00Z", "started_at": "now"},
        ],
        "metadata": {},
    })
    fake_db = FakeFlowKGCDB(entry)

    sandbox_sends: list[tuple[str, str, list[str] | None]] = []

    monkeypatch.setattr(runner, "db", fake_db)
    monkeypatch.setattr(runner, "_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(runner, "_notify_pending_approval", lambda *args, **kwargs: None)
    monkeypatch.setattr(runner, "_fetch_lead_signals", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(runner, "_refresh_entry_from_signals", lambda entry, _signals: entry)
    monkeypatch.setattr(runner, "_business_hours", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(runner, "_next_business_slot", lambda _kind: 0)
    monkeypatch.setattr(
        runner,
        "_u_get",
        lambda path, _params=None: [
            {"is_sender": True, "timestamp": "2026-07-08T10:00:00Z", "text": "Mensagem anterior"},
            {"is_sender": False, "timestamp": "2026-07-08T10:05:00Z", "reaction_type": "like"},
        ] if path.endswith("/messages") else {},
    )
    monkeypatch.setattr(
        runner,
        "_haiku",
        lambda prompt, entry, signals=None, max_tokens=400, step_type="", **_kwargs: "Follow-up Jefferson",
    )

    runner.run()
    updated = fake_db.get_entry("kgc_i_ln-entry")
    assert updated["current_step"] == 13
    assert updated["step_status"] == "pending"
    assert updated["pending_draft"] is None
    assert updated["reply_received"] is None

    runner.run()
    updated = fake_db.get_entry("kgc_i_ln-entry")
    assert updated["current_step"] == 12
    assert updated["step_status"] == "waiting_approval"
    assert updated["metadata"]["follow_up_count"] == 1
    assert "Follow-up Jefferson" in updated["pending_draft"]
    assert flow_steps.FLOWS["kgc_i_ln"]["steps"][12]["branch_reaction"] == 13


def test_ln_message_without_chat_keeps_manual_approval_instead_of_failing(monkeypatch):
    runner, _db_module, _flow_steps = _load_flow_kgc_modules(monkeypatch)
    entry = _make_entry("kgc_i_ln")
    entry.update({
        "current_step": 11,
        "flow_id": "kgc_i_ln",
        "status": "active",
        "step_status": "pending",
        "sandbox": False,
        "ln_chat_id": None,
        "tags": [],
        "messages_sent": [
            {"_type": "pending_invite", "text": "Convite aprovado"},
            {"_type": "ln_invite_sent", "channel": "ln_invite"},
        ],
    })
    fake_db = FakeFlowKGCDB(entry)

    monkeypatch.setattr(runner, "db", fake_db)
    monkeypatch.setattr(runner, "_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(runner, "_notify_pending_approval", lambda *args, **kwargs: None)
    monkeypatch.setattr(runner, "_business_hours", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(runner, "_fetch_lead_signals", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(runner, "_refresh_entry_from_signals", lambda entry, _signals: entry)
    monkeypatch.setattr(runner, "_fetch_sector_insight", lambda _entry: None)
    monkeypatch.setattr(runner, "_get_or_create_ln_chat", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(runner, "check_accepted", lambda _entry: False)
    monkeypatch.setattr(
        runner,
        "_haiku",
        lambda prompt, entry, signals=None, max_tokens=400, step_type="", **_kwargs: "DM aprovada para Maxwell",
    )

    runner.advance(fake_db.get_entry("kgc_i_ln-entry"))
    runner.advance(fake_db.get_entry("kgc_i_ln-entry"))

    updated = fake_db.get_entry("kgc_i_ln-entry")
    assert updated["status"] == "active"
    assert updated["step_status"] == "waiting_accept"
    assert updated["current_step"] == 10
    assert updated["pending_draft"] is None
    assert updated.get("error_message") is None


def test_signals_block_prefers_page_engagement_over_generic_follow_page(monkeypatch):
    runner, _db_module, _flow_steps = _load_flow_kgc_modules(monkeypatch)
    entry = {
        "id": "lead-1",
        "full_name": "Alison Lucas Orth",
        "company_name": "Koncepto",
        "company_industry": "consultoria",
        "flow_id": "kgc_i_ln",
        "operator_id": "jefferson",
        "sector_insight": "",
    }
    signals = {
        "lead": {"follows_company_page": True},
        "leadmagnet": {},
        "page_engagement": {"event_type": "page_post_comment", "comment_text": "Ótimo conteúdo"},
    }

    monkeypatch.setattr(runner.db, "get_operator", lambda _op_id: {"display_name": "Jefferson Frasnelli"})

    block = runner._signals_block(signals, entry=entry, step_type="ln_message")

    assert "comentou em um post da página" in block
    assert "segue a página da Koncepto" not in block


@pytest.mark.parametrize(
    ("flow_id", "expected_step", "expected_prompt_marker"),
    [
        ("kgc_i_ln", 9, "Como vocês têm lidado com isso?"),
        ("kgc_ii_ln", 8, "Como você tem feito pra captar novas contas hoje"),
    ],
)
def test_flow_kgc_linkedin_sandbox_reaches_manual_approval(monkeypatch, flow_id, expected_step, expected_prompt_marker):
    runner, _db_module, _flow_steps = _load_flow_kgc_modules(monkeypatch)
    fake_db = FakeFlowKGCDB(_make_entry(flow_id))

    sandbox_sends: list[tuple[str, str]] = []
    prompt_log: list[tuple[str, str]] = []

    monkeypatch.setattr(runner, "db", fake_db)
    monkeypatch.setattr(runner, "_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(runner, "_social_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(runner, "_notify_pending_approval", lambda *args, **kwargs: None)
    monkeypatch.setattr(runner, "_fetch_lead_signals", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(runner, "detect_channel", lambda _entry: ("linkedin", None))
    monkeypatch.setattr(runner, "check_accepted", lambda _entry: False)
    monkeypatch.setattr(
        runner,
        "_u_get",
        lambda path, _params=None: (
            {"provider_id": "provider-1"} if "/api/v1/users/" in path and "/posts" not in path
            else {"items": [{"social_id": "social-1", "id": "post-1", "text": "Post real do lead", "url": "https://example.test/post"}]}
        ),
    )
    monkeypatch.setattr(runner, "_perplexity_research", lambda _entry, scope, sub_scope="": f"[{scope.upper()}: pesquisa {sub_scope or 'base'}]")
    monkeypatch.setattr(
        runner,
        "_fetch_team_post",
        lambda *_args, **_kwargs: {
            "text": "a diferença entre outbound como volume e outbound como sistema",
            "author": "Andre Santos",
            "author_display": "André Santos",
            "is_me": True,
            "url": "https://example.test/team-post",
        },
    )
    monkeypatch.setattr(runner, "_fetch_apollo_profile", lambda _entry: "[APOLLO_PROFILE: fundador | vendas B2B | sem CRM definido]")
    monkeypatch.setattr(
        runner,
        "_sbx_wa_send",
        lambda lead_name, channel_icon, text, extra=None, entry=None: (
            sandbox_sends.append((channel_icon, text)) or "\n".join([text] + (extra or []))
        ),
    )

    def _fake_haiku(prompt_template: str, entry: dict, signals=None, max_tokens: int = 400, step_type: str = "") -> str:
        prompt_log.append((step_type, prompt_template))
        first_name = runner._safe_first_name(entry.get("full_name", ""))
        if step_type == "ln_message":
            return f"Rascunho LinkedIn para {first_name}"
        if step_type == "ln_invite":
            return f"Convite LinkedIn para {first_name}"
        return f"Texto gerado para {step_type or 'step'}"

    monkeypatch.setattr(runner, "_haiku", _fake_haiku)

    final_entry = _pump_runner_until_waiting_approval(runner, fake_db, f"{flow_id}-entry")

    assert final_entry["status"] == "active"
    assert final_entry["step_status"] == "waiting_approval"
    assert final_entry["current_step"] == expected_step
    assert final_entry["pending_draft"].startswith("Convite LinkedIn para Test")
    assert "Vale uma conversa?" in final_entry["pending_draft"]
    assert final_entry["reply_received"] in ("", None)
    assert any(step_type == "ln_invite" for step_type, _prompt in prompt_log)
    assert sandbox_sends == []

    ln_invite_prompts = [prompt for step_type, prompt in prompt_log if step_type == "ln_invite"]
    assert ln_invite_prompts
