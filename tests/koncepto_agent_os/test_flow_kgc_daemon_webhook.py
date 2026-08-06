from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


def _load_daemon_module(monkeypatch):
    koncepto_root = Path(__file__).resolve().parents[3]
    flow_root = koncepto_root / "scripts" / "flow_kgc"

    monkeypatch.setenv("VPS_FUNIL_URL", "http://supabase.test")
    monkeypatch.setenv("VPS_FUNIL_SERVICE_ROLE_KEY", "test-service-role")
    monkeypatch.setenv("UNIPILE_DSN", "http://unipile.test")
    monkeypatch.setenv("UNIPILE_API_KEY", "test-unipile-key")
    monkeypatch.setenv("FLOW_KGC_WEBHOOK_SECRET", "webhook-secret")

    for name in [
        "koncepto_agent_os",
        "koncepto_agent_os.scripts",
        "koncepto_agent_os.scripts.flow_kgc",
        "koncepto_agent_os.scripts.flow_kgc.db",
        "koncepto_agent_os.scripts.flow_kgc.flow_steps",
        "koncepto_agent_os.scripts.flow_kgc.runner",
        "koncepto_agent_os.scripts.flow_kgc.daemon",
        # daemon.py importa via sys.path.insert(scripts/) + "from flow_kgc import db" /
        # "from flow_kgc.runner import ..." (nomes nus, não o pacote namespaced acima).
        # Outros testes (ex. test_flow_kgc_operator_authorization.py) registram um
        # stub falso em sys.modules["flow_kgc"] (sem __path__, não é pacote) e nunca
        # limpam — se sobrar daqui, o import de flow_kgc.runner falha com
        # "'flow_kgc' is not a package" quando este teste roda depois no mesmo processo.
        "flow_kgc",
        "flow_kgc.db",
        "flow_kgc.runner",
    ]:
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

    spec = importlib.util.spec_from_file_location(
        "koncepto_agent_os.scripts.flow_kgc.daemon",
        flow_root / "daemon.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _FakeRequest:
    def __init__(self, body: dict, headers: dict | None = None, query: dict | None = None):
        self._raw = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.headers = headers or {}
        self.query = query or {}

    async def read(self) -> bytes:
        return self._raw


def _unipile_signature(secret: str, raw_body: bytes, timestamp: str = "1720000000") -> str:
    payload = f"{timestamp}.".encode("utf-8") + raw_body
    sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v0={sig}"


@pytest.mark.asyncio
async def test_handle_webhook_accepts_unipile_signature_and_nested_chat_id(monkeypatch):
    daemon = _load_daemon_module(monkeypatch)
    daemon.WEBHOOK_SECRET = "webhook-secret"

    captured: dict[str, object] = {}

    def _find_waiting_reply_by_chat(chat_id: str):
        captured["chat_id"] = chat_id
        return {"id": "entry-1"}

    def _try_process_immediately(entry, source: str):
        captured["entry"] = entry
        captured["source"] = source
        return True

    monkeypatch.setattr(daemon, "_find_waiting_reply_by_chat", _find_waiting_reply_by_chat)
    monkeypatch.setattr(daemon, "_find_pending_ln_message_by_chat", lambda _chat_id: None)
    monkeypatch.setattr(daemon, "_try_process_immediately", _try_process_immediately)

    body = {
        "event": "message_received",
        "chat": {"id": "GXydpTABU-yrNtKXBxo4jw"},
        "message": "Oi, já vi sua conexão.",
        "sender": {"attendee_provider_id": "other-user"},
    }
    req = _FakeRequest(
        body,
        headers={"unipile-signature": _unipile_signature("webhook-secret", json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))},
    )

    resp = await daemon.handle_webhook(req)

    assert resp.status == 200
    assert captured["chat_id"] == "GXydpTABU-yrNtKXBxo4jw"
    assert captured["source"] == "webhook:new_message"
    assert captured["entry"] == {"id": "entry-1"}


@pytest.mark.asyncio
async def test_handle_webhook_keeps_legacy_token_and_own_message_short_circuit(monkeypatch):
    daemon = _load_daemon_module(monkeypatch)
    daemon.WEBHOOK_SECRET = "webhook-secret"

    called = {"waiting": 0, "pending": 0, "process": 0}

    monkeypatch.setattr(daemon, "_find_waiting_reply_by_chat", lambda _chat_id: called.__setitem__("waiting", called["waiting"] + 1) or {"id": "entry-2"})
    monkeypatch.setattr(daemon, "_find_pending_ln_message_by_chat", lambda _chat_id: called.__setitem__("pending", called["pending"] + 1) or None)
    monkeypatch.setattr(daemon, "_try_process_immediately", lambda *_args, **_kwargs: called.__setitem__("process", called["process"] + 1) or True)

    body = {
        "event": "message_received",
        "chat_id": "GXydpTABU-yrNtKXBxo4jw",
        "from_me": True,
        "message": "Obrigado pela conexão!",
    }
    req = _FakeRequest(body, query={"token": "webhook-secret"})

    resp = await daemon.handle_webhook(req)

    assert resp.status == 200
    assert "own message" in resp.text
    assert called["waiting"] == 0
    assert called["pending"] == 0
    assert called["process"] == 0
