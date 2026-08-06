from __future__ import annotations

import copy
import importlib.util
import sys
import types
from pathlib import Path


def _load_dashboard_app():
    # The dashboard lives in the canonical ~/.hermes checkout; this test file
    # is kept in the hermes-agent checkout for regression coverage.
    repo_root = Path(__file__).resolve().parents[3]
    app_path = repo_root / "dashboard" / "app.py"

    module_names = [
        "sales_signal",
        "sales_signal.db",
        "sales_signal.icp",
        "sales_signal.processor",
        "sales_signal.cron",
        "sales_signal.linkedin_api",
        "flow_kgc",
        "flow_kgc.db",
        "koncepto_dashboard_app_test",
    ]
    for name in module_names:
        sys.modules.pop(name, None)

    flow_pkg = types.ModuleType("flow_kgc")
    flow_db = types.ModuleType("flow_kgc.db")
    flow_pkg.db = flow_db
    sys.modules["flow_kgc"] = flow_pkg
    sys.modules["flow_kgc.db"] = flow_db

    spec = importlib.util.spec_from_file_location("koncepto_dashboard_app_test", app_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["koncepto_dashboard_app_test"] = module
    spec.loader.exec_module(module)
    return module


def _unwrap_response(result):
    if isinstance(result, tuple):
        response, status = result
        return response, status
    return result, result.status_code


class FakeFlowKGCDB:
    def __init__(self):
        self.operators = [
            {
                "id": "andre",
                "display_name": "André Santos",
                "operated_by": ["andre.santos@konceptogc.com", "andre"],
                "color": "#111111",
                "is_active": True,
            },
            {
                "id": "jefferson",
                "display_name": "Jefferson Frasnelli",
                "operated_by": ["jefferson@konceptogc.com", "jefferson"],
                "color": "#222222",
                "is_active": True,
            },
        ]
        self.entries = {
            "entry-jefferson": {
                "id": "entry-jefferson",
                "operator_id": "jefferson",
                "sandbox": True,
                "channel": "linkedin",
                "messages_sent": [{"_type": "pending_channel", "channel": "linkedin"}],
                "email_address": "",
                "wa_chat_id": None,
                "ln_chat_id": None,
            },
            "entry-andre": {
                "id": "entry-andre",
                "operator_id": "andre",
                "sandbox": True,
                "channel": "linkedin",
                "messages_sent": [{"_type": "pending_channel", "channel": "linkedin"}],
                "email_address": "",
                "wa_chat_id": None,
                "ln_chat_id": None,
            },
        }
        self.sent = []

    def get_operators(self):
        return copy.deepcopy(self.operators)

    def get_operator(self, operator_id: str):
        for op in self.operators:
            if op["id"] == operator_id:
                return copy.deepcopy(op)
        return None

    def list_pending_approval(self, limit: int = 20, operator_id: str | None = None):
        items = list(self.entries.values())
        if operator_id:
            items = [item for item in items if item.get("operator_id") == operator_id]
        return [copy.deepcopy(item) for item in items[:limit]]

    def count_pending_approval(self, operator_id: str | None = None) -> int:
        items = list(self.entries.values())
        if operator_id:
            items = [item for item in items if item.get("operator_id") == operator_id]
        return len(items)

    def _now(self) -> str:
        return "2026-07-09T12:00:00Z"

    def _patch_conditional(self, _table: str, record: dict, filters: dict):
        entry_id = filters.get("id", "").removeprefix("eq.")
        entry = self.entries.get(entry_id)
        if not entry:
            return []
        entry.update(record)
        return [copy.deepcopy(entry)]

    def get_entry(self, entry_id: str):
        entry = self.entries.get(entry_id)
        return copy.deepcopy(entry) if entry else None

    def send_approved_draft(self, entry_id: str, text_sent: str, channel: str):
        self.sent.append((entry_id, text_sent, channel))
        return {"ok": True}

    def _patch(self, _table: str, patch: dict, _col: str, entry_id: str):
        if entry_id in self.entries:
            self.entries[entry_id].update(copy.deepcopy(patch))
        return self.get_entry(entry_id)


def _login_session(app_module, user: str, display_name: str, role: str = "viewer"):
    app_module.session["logged_in"] = True
    app_module.session["user"] = user
    app_module.session["display_name"] = display_name
    app_module.session["role"] = role


def test_pending_approval_list_filters_to_authorized_operator(monkeypatch):
    app_module = _load_dashboard_app()
    fake_db = FakeFlowKGCDB()
    monkeypatch.setattr(app_module, "fkgc_db", fake_db)
    monkeypatch.setattr(app_module, "FKGC_ENABLED", True)

    with app_module.app.test_request_context("/api/flow-kgc/pending-approval", method="GET"):
        _login_session(app_module, "jefferson@konceptogc.com", "Jefferson Frasnelli")
        response, status = _unwrap_response(app_module.fkgc_pending_approval_list())

    assert status == 200
    payload = response.get_json()
    assert [item["operator_id"] for item in payload["items"]] == ["jefferson"]


def test_send_reply_rejects_unauthorized_profile(monkeypatch):
    app_module = _load_dashboard_app()
    fake_db = FakeFlowKGCDB()
    monkeypatch.setattr(app_module, "fkgc_db", fake_db)
    monkeypatch.setattr(app_module, "FKGC_ENABLED", True)

    with app_module.app.test_request_context(
        "/api/flow-kgc/send-reply",
        method="POST",
        json={"entry_id": "entry-andre", "text": "mensagem"},
    ):
        _login_session(app_module, "jefferson@konceptogc.com", "Jefferson Frasnelli")
        response, status = _unwrap_response(app_module.fkgc_send_reply())

    assert status == 403
    assert response.get_json()["error"] == "Você não tem permissão para operar este perfil"
    assert fake_db.sent == []


def test_send_reply_allows_authorized_profile(monkeypatch):
    app_module = _load_dashboard_app()
    fake_db = FakeFlowKGCDB()
    monkeypatch.setattr(app_module, "fkgc_db", fake_db)
    monkeypatch.setattr(app_module, "FKGC_ENABLED", True)

    # Desde 2026-08-04, fkgc_send_reply dispara o envio real numa thread em
    # background (queued=True) em vez de bloquear a requisição — o motor real
    # (_fkgc_send_reply_sync) importa flow_kgc.runner de verdade, fora do
    # escopo desta fake de autorização. Aqui o alvo é só o gate de acesso,
    # então trocamos o motor por um stub e a thread por execução síncrona
    # (senão a asserção corre antes da thread real terminar).
    def _fake_send_reply_sync(data=None):
        d = data or {}
        fake_db.send_approved_draft(d.get("entry_id"), d.get("text"), "linkedin")
        return app_module.jsonify({"ok": True})

    monkeypatch.setattr(app_module, "_fkgc_send_reply_sync", _fake_send_reply_sync)

    class _SyncThread:
        def __init__(self, target=None, name=None, daemon=None, args=(), kwargs=None):
            self._target, self._args, self._kwargs = target, args, kwargs or {}

        def start(self):
            self._target(*self._args, **self._kwargs)

    monkeypatch.setattr(app_module.threading, "Thread", _SyncThread)

    with app_module.app.test_request_context(
        "/api/flow-kgc/send-reply",
        method="POST",
        json={"entry_id": "entry-jefferson", "text": "mensagem validada"},
    ):
        _login_session(app_module, "jefferson@konceptogc.com", "Jefferson Frasnelli")
        response, status = _unwrap_response(app_module.fkgc_send_reply())

    assert status == 200
    assert response.get_json()["ok"] is True
    assert fake_db.sent == [("entry-jefferson", "mensagem validada", "linkedin")]


def test_operator_update_is_admin_only(monkeypatch):
    app_module = _load_dashboard_app()
    fake_db = FakeFlowKGCDB()
    monkeypatch.setattr(app_module, "fkgc_db", fake_db)
    monkeypatch.setattr(app_module, "FKGC_ENABLED", True)

    with app_module.app.test_request_context(
        "/api/flow-kgc/operators/andre",
        method="PATCH",
        json={"operated_by": "andre.santos@konceptogc.com"},
    ):
        _login_session(app_module, "jefferson@konceptogc.com", "Jefferson Frasnelli")
        response, status = _unwrap_response(app_module.fkgc_operator_update("andre"))

    assert status == 403
    assert response.get_json()["error"] == "Somente admin pode editar operadores"


def test_display_name_alone_no_longer_authorizes_operator(monkeypatch):
    app_module = _load_dashboard_app()
    fake_db = FakeFlowKGCDB()
    fake_db.operators[1]["operated_by"] = ["jefferson-id-interno"]
    monkeypatch.setattr(app_module, "fkgc_db", fake_db)
    monkeypatch.setattr(app_module, "FKGC_ENABLED", True)

    with app_module.app.test_request_context("/api/flow-kgc/pending-approval", method="GET"):
        _login_session(app_module, "nao-autorizado@konceptogc.com", "Jefferson Frasnelli")
        response, status = _unwrap_response(app_module.fkgc_pending_approval_list())

    assert status == 200
    payload = response.get_json()
    assert payload["items"] == []
