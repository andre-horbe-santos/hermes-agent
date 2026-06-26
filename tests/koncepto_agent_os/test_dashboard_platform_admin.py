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

