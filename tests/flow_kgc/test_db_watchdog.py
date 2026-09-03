from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

import flow_kgc.db as db


def test_release_stale_processing_only_releases_old_rows(monkeypatch):
    now = datetime.now(timezone.utc)
    rows = [
        {"id": "old-one", "updated_at": (now - timedelta(minutes=21)).isoformat()},
        {"id": "fresh-one", "updated_at": (now - timedelta(minutes=5)).isoformat()},
        {"id": "bad-ts", "updated_at": "not-a-timestamp"},
    ]
    patched: list[tuple[str, dict]] = []

    monkeypatch.setattr(db, "_get", lambda table, params=None: rows if params and params.get("status") == "eq.processing" else [])

    def _patch(table: str, record: dict, col: str, val: str, minimal: bool = False):
        patched.append((val, record))
        return {}

    monkeypatch.setattr(db, "_patch", _patch)

    recovered = db.release_stale_processing(max_age_seconds=20 * 60)

    assert recovered == 1
    assert len(patched) == 1
    assert patched[0][0] == "old-one"
    assert patched[0][1]["status"] == "active"
    assert "updated_at" in patched[0][1]
