from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


def _load_dashboard_app():
    # ~/.hermes é o único clone canônico desde a consolidação (koncepto-agent-os/,
    # o clone aninhado dentro de hermes-agent/, foi removido).
    koncepto_root = Path(__file__).resolve().parents[3]
    app_path = koncepto_root / "dashboard" / "app.py"

    module_names = [
        "sales_signal",
        "sales_signal.db",
        "sales_signal.icp",
        "sales_signal.processor",
        "sales_signal.cron",
        "sales_signal.linkedin_api",
        "flow_kgc",
        "flow_kgc.db",
        "koncepto_dashboard_platform_admin_test",
    ]
    for name in module_names:
        sys.modules.pop(name, None)

    flow_pkg = types.ModuleType("flow_kgc")
    flow_db = types.ModuleType("flow_kgc.db")
    flow_pkg.db = flow_db
    sys.modules["flow_kgc"] = flow_pkg
    sys.modules["flow_kgc.db"] = flow_db

    spec = importlib.util.spec_from_file_location("koncepto_dashboard_platform_admin_test", app_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["koncepto_dashboard_platform_admin_test"] = module
    spec.loader.exec_module(module)
    return module


def _unwrap_response(result):
    if isinstance(result, tuple):
        response, status = result
        return response, status
    return result, result.status_code


def _login_session(app_module, user: str, role: str = "admin"):
    app_module.session["logged_in"] = True
    app_module.session["user"] = user
    app_module.session["display_name"] = user.split("@")[0]
    app_module.session["role"] = role


def test_platform_admin_email_is_explicit():
    app_module = _load_dashboard_app()
    assert app_module._default_role_for_email("andre.santos@konceptogc.com") == "admin"
    assert app_module._default_role_for_email("jefferson.frasnelli@konceptogc.com") == "member"


def test_require_platform_admin_blocks_non_platform_admin():
    app_module = _load_dashboard_app()
    with app_module.app.test_request_context("/api/config/users", method="GET"):
        _login_session(app_module, "jefferson.frasnelli@konceptogc.com", role="admin")
        response, status = _unwrap_response(app_module._require_platform_admin())
    assert status == 403
    assert response.get_json()["error"] == "Acesso restrito ao admin da plataforma"


def test_require_platform_admin_allows_andre():
    app_module = _load_dashboard_app()
    with app_module.app.test_request_context("/api/config/users", method="GET"):
        _login_session(app_module, "andre.santos@konceptogc.com", role="admin")
        result = app_module._require_platform_admin()
    assert result is None


def test_config_users_endpoint_requires_platform_admin(monkeypatch):
    app_module = _load_dashboard_app()
    monkeypatch.setattr(app_module, "_load_users_db", lambda: {
        "andre.santos@konceptogc.com": {"name": "Andre", "role": "admin"},
        "jefferson.frasnelli@konceptogc.com": {"name": "Jefferson", "role": "admin"},
    })

    with app_module.app.test_request_context("/api/config/users", method="GET"):
        _login_session(app_module, "jefferson.frasnelli@konceptogc.com", role="admin")
        response, status = _unwrap_response(app_module.cfg_users_list())
    assert status == 403

    with app_module.app.test_request_context("/api/config/users", method="GET"):
        _login_session(app_module, "andre.santos@konceptogc.com", role="admin")
        response, status = _unwrap_response(app_module.cfg_users_list())
    assert status == 200
    payload = response.get_json()
    assert {item["email"] for item in payload} == {
        "andre.santos@konceptogc.com",
        "jefferson.frasnelli@konceptogc.com",
    }


@pytest.mark.parametrize(
    ("role", "modules", "expected_tabs"),
    [
        ("admin", None, None),
        (
            "member",
            ["inteligencia", "vendas"],
            {"signal", "funil", "prospec", "mkt", "diagnostico", "metas", "parceiros", "dealflow"},
        ),
        (
            "member",
            ["outreach", "modulo_mkt", "ferramentas"],
            {"flow-kgc", "leadmagnet", "leadinbound", "nm", "editorial", "aprendizado"},
        ),
        ("member", [], set()),
    ],
)
def test_complete_login_builds_allowed_tabs_from_rbac_modules(
    monkeypatch, role, modules, expected_tabs
):
    """The session is the enforcement input for the module-level RBAC gate."""
    app_module = _load_dashboard_app()
    monkeypatch.setattr(app_module, "FKGC_ENABLED", False)
    monkeypatch.setattr(app_module, "_append_login_log", lambda *args: None)

    with app_module.app.test_request_context("/login", method="POST"):
        app_module.session["mfa_user"] = "jefferson.frasnelli@konceptogc.com"
        app_module.session["mfa_display_name"] = "Jefferson Frasnelli"
        app_module.session["mfa_role"] = role
        app_module.session["mfa_modules"] = modules
        app_module.session["mfa_dm_accounts"] = None

        app_module._complete_login("127.0.0.1")

        if expected_tabs is None:
            assert app_module.session["allowed_tabs"] is None
        else:
            assert set(app_module.session["allowed_tabs"]) == expected_tabs


@pytest.mark.parametrize(
    ("allowed_tabs", "tab", "allowed"),
    [
        ({"signal", "funil"}, "signal", True),
        ({"signal", "funil"}, "config", False),
        ({"signal", "funil"}, "leadmagnet", False),
        (None, "config", True),
    ],
)
def test_module_access_gate_matches_session_rbac(monkeypatch, allowed_tabs, tab, allowed):
    app_module = _load_dashboard_app()
    with app_module.app.test_request_context(f"/api/{tab}"):
        app_module.session["allowed_tabs"] = (
            None if allowed_tabs is None else list(allowed_tabs)
        )
        result = app_module._require_module_access(tab)

    if allowed:
        assert result is None
    else:
        response, status = _unwrap_response(result)
        assert status == 403
        assert response.get_json()["error"] == f"Acesso restrito ao módulo {tab}"


@pytest.mark.parametrize(
    ("handler_name", "method", "path", "role", "allowed_tabs", "expected_error"),
    [
        (
            "fkgc_queue_list",
            "GET",
            "/api/flow-kgc/queue",
            "member",
            ["signal"],
            "Acesso restrito ao módulo flow-kgc",
        ),
        (
            "fkgc_context_save",
            "PUT",
            "/api/flow-kgc/context",
            "member",
            ["flow-kgc"],
            "Acesso restrito a administradores",
        ),
        (
            "fkgc_operator_create",
            "POST",
            "/api/flow-kgc/operators",
            "member",
            ["flow-kgc"],
            "Acesso restrito a administradores",
        ),
    ],
)
def test_flow_kgc_sensitive_endpoints_enforce_rbac(
    monkeypatch, handler_name, method, path, role, allowed_tabs, expected_error
):
    app_module = _load_dashboard_app()
    monkeypatch.setattr(app_module, "FKGC_ENABLED", True)

    with app_module.app.test_request_context(path, method=method, json={}):
        _login_session(app_module, "thiago.trindade@konceptogc.com", role=role)
        app_module.session["allowed_tabs"] = allowed_tabs
        response, status = _unwrap_response(getattr(app_module, handler_name)())

    assert status == 403
    assert response.get_json()["error"] == expected_error


def test_authorization_audit_is_sanitized(monkeypatch, tmp_path):
    app_module = _load_dashboard_app()
    audit_file = tmp_path / "security-audit.jsonl"
    monkeypatch.setattr(app_module, "_SECURITY_AUDIT_FILE", str(audit_file))

    with app_module.app.test_request_context("/api/flow-kgc/queue?token=secret", method="GET"):
        _login_session(app_module, "thiago.trindade@konceptogc.com", role="member")
        app_module.session["allowed_tabs"] = ["signal"]
        response, status = _unwrap_response(app_module._require_module_access("flow-kgc"))

    assert status == 403
    event = json.loads(audit_file.read_text(encoding="utf-8"))
    assert event["event"] == "authorization"
    assert event["decision"] == "deny"
    assert event["scope"] == "module:flow-kgc"
    assert event["route"] == "fkgc_queue_list"
    assert "thiago.trindade@konceptogc.com" not in audit_file.read_text(encoding="utf-8")
    assert "secret" not in audit_file.read_text(encoding="utf-8")
