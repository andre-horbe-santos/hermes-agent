from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


def _load_dashboard_app():
    repo_root = Path(__file__).resolve().parents[2]
    app_path = repo_root / "koncepto-agent-os" / "dashboard" / "app.py"

    module_names = [
        "sales_signal",
        "sales_signal.db",
        "sales_signal.icp",
        "sales_signal.processor",
        "sales_signal.cron",
        "sales_signal.linkedin_api",
        "flow_kgc",
        "flow_kgc.db",
        "koncepto_dashboard_leadmagnet_test",
    ]
    for name in module_names:
        sys.modules.pop(name, None)

    flow_pkg = types.ModuleType("flow_kgc")
    flow_db = types.ModuleType("flow_kgc.db")
    flow_pkg.db = flow_db
    sys.modules["flow_kgc"] = flow_pkg
    sys.modules["flow_kgc.db"] = flow_db

    spec = importlib.util.spec_from_file_location("koncepto_dashboard_leadmagnet_test", app_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["koncepto_dashboard_leadmagnet_test"] = module
    spec.loader.exec_module(module)
    return module


def _unwrap_response(result):
    if isinstance(result, tuple):
        response, status = result
        return response, status
    return result, result.status_code


def _login_session(app_module, user: str, allowed_tabs=None):
    app_module.session["logged_in"] = True
    app_module.session["user"] = user
    app_module.session["display_name"] = user.split("@")[0]
    app_module.session["role"] = "member"
    app_module.session["allowed_tabs"] = allowed_tabs


def test_leadmagnet_posts_endpoint_requires_module_access():
    app_module = _load_dashboard_app()

    with app_module.app.test_request_context("/api/leadmagnet/posts", method="GET"):
        _login_session(app_module, "jefferson.frasnelli@konceptogc.com", allowed_tabs=["signal"])
        response, status = _unwrap_response(app_module.lm_posts_get())

    assert status == 403
    assert response.get_json()["error"] == "Acesso restrito ao módulo leadmagnet"


def test_leadmagnet_send_reply_blocks_real_send_for_sandbox(monkeypatch):
    app_module = _load_dashboard_app()

    def fake_lm_get(table: str, params: dict):
        if table == "leadmagnet_interactions":
            return [{
                "id": "interaction-1",
                "leadmagnet_post_id": "post-1",
                "comment_id": "comment-1",
                "commenter_provider_id": "ACoAAA123",
                "commenter_name": "Lead Teste",
            }]
        if table == "leadmagnet_posts":
            return [{
                "id": "post-1",
                "account_id": "acc-1",
                "post_social_id": "social-1",
                "sandbox": True,
            }]
        raise AssertionError(f"Tabela inesperada: {table}")

    def fail_httpx_post(*_args, **_kwargs):
        raise AssertionError("httpx.post não deveria ser chamado para post em sandbox")

    monkeypatch.setattr(app_module, "_lm_get", fake_lm_get)
    monkeypatch.setitem(sys.modules, "httpx", types.SimpleNamespace(post=fail_httpx_post))

    with app_module.app.test_request_context(
        "/api/leadmagnet/interactions/interaction-1/send-reply",
        method="POST",
        json={"text": "Resposta manual"},
    ):
        _login_session(app_module, "jefferson.frasnelli@konceptogc.com", allowed_tabs=["leadmagnet"])
        response, status = _unwrap_response(app_module.lm_send_reply("interaction-1"))

    assert status == 409
    assert response.get_json()["error"] == "Post em sandbox não permite envio real"


def test_leadmagnet_react_blocks_real_send_for_sandbox(monkeypatch):
    app_module = _load_dashboard_app()

    def fake_lm_get(table: str, params: dict):
        if table == "leadmagnet_interactions":
            return [{
                "id": "interaction-1",
                "leadmagnet_post_id": "post-1",
                "comment_id": "comment-1",
            }]
        if table == "leadmagnet_posts":
            return [{
                "id": "post-1",
                "account_id": "acc-1",
                "post_social_id": "social-1",
                "sandbox": True,
            }]
        raise AssertionError(f"Tabela inesperada: {table}")

    def fail_httpx_post(*_args, **_kwargs):
        raise AssertionError("httpx.post não deveria ser chamado para reação em sandbox")

    monkeypatch.setattr(app_module, "_lm_get", fake_lm_get)
    monkeypatch.setitem(sys.modules, "httpx", types.SimpleNamespace(post=fail_httpx_post))

    with app_module.app.test_request_context(
        "/api/leadmagnet/interactions/interaction-1/react",
        method="POST",
        json={"reaction_type": "like"},
    ):
        _login_session(app_module, "jefferson.frasnelli@konceptogc.com", allowed_tabs=["leadmagnet"])
        response, status = _unwrap_response(app_module.lm_interaction_react("interaction-1"))

    assert status == 409
    assert response.get_json()["error"] == "Post em sandbox não permite reação real"
