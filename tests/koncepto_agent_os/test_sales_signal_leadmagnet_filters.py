from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from sales_signal import db


def test_match_or_partial_excludes_pending_and_non_matches():
    params = db._leads_filter_params(None, "match_or_partial", False, None)

    assert params["icp_match"] == "in.(match,partial)"


def test_count_leads_by_ids_applies_final_filters_and_chunks(monkeypatch):
    calls = []

    def fake_get(table, params):
        calls.append((table, params))
        return [{"count": 7 if len(calls) == 1 else 2}]

    monkeypatch.setattr(db, "_get", fake_get)
    lead_ids = [f"lead-{index}" for index in range(db._LEADS_ID_CHUNK + 1)]

    total = db.count_leads_by_ids(
        lead_ids,
        icp_match="match_or_partial",
        extra_filters={"follows_company_page": "eq.true"},
    )

    assert total == 9
    assert len(calls) == 2
    assert all(call[1]["icp_match"] == "in.(match,partial)" for call in calls)
    assert all(call[1]["stage"] == "neq.discarded" for call in calls)
    assert all(call[1]["follows_company_page"] == "eq.true" for call in calls)


def test_all_stages_and_all_icps_add_no_implicit_exclusions(monkeypatch):
    captured = []

    def fake_get(_table, params):
        captured.append(params)
        return [{"count": 177}]

    monkeypatch.setattr(db, "_get", fake_get)

    total = db.count_leads_by_ids(
        ["lead-1"],
        icp_match=None,
        skip_icp_exclude=True,
        include_discarded=True,
    )

    assert total == 177
    assert "stage" not in captured[0]
    assert "icp_match" not in captured[0]


def test_direct_all_filters_do_not_hide_excluded_or_discarded():
    params = db._leads_filter_params(None, None, False, None)

    assert "stage" not in params
    assert "icp_match" not in params
