from __future__ import annotations

import copy
import importlib.util
import sys
import types
from pathlib import Path

import pytest


def _load_flow_kgc_modules(monkeypatch):
    repo_root = Path(__file__).resolve().parents[2]
    koncepto_root = repo_root / "koncepto-agent-os"
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

    def _get(self, _table: str, _params: dict | None = None) -> list:
        return []

    def get_entry(self, entry_id: str) -> dict:
        return copy.deepcopy(self._entry(entry_id))

    def list_queue(self, status: str | None = None, limit: int = 50, offset: int = 0, operator_id: str | None = None) -> list:
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

    def get_context_block(self) -> str:
        return ""


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


@pytest.mark.parametrize(
    ("flow_id", "expected_step", "expected_prompt_marker"),
    [
        ("kgc_i_ln", 7, "Como vocês têm lidado com isso?"),
        ("kgc_ii_ln", 9, "Como você tem feito pra captar novas contas hoje"),
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
    assert final_entry["pending_draft"] == "Rascunho LinkedIn para Test"
    assert final_entry["reply_received"] == ""
    assert any(icon == "🔵 LN CONVITE" for icon, _text in sandbox_sends)
    assert all(icon != "🔵 LN DM" for icon, _text in sandbox_sends)

    ln_message_prompts = [prompt for step_type, prompt in prompt_log if step_type == "ln_message"]
    assert len(ln_message_prompts) == 1
    assert expected_prompt_marker in ln_message_prompts[0]

