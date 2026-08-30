from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from sales_signal import social_engagement_worker as worker


def _row(**overrides):
    row = {
        "id": "intent-1",
        "campaign_id": "campaign-1",
        "target_id": "target-1",
        "post_id": "post-1",
        "post_text": "Texto real",
        "post_url": "https://linkedin.test/post-1",
        "action": "comment",
        "comment_text": "{{0}}, ótima leitura.",
        "mentions": [{"name": "Pessoa", "profile_id": "ACo-target"}],
        "idempotency_key": "key-1",
    }
    row.update(overrides)
    return row


def test_worker_claims_ready_intent_and_marks_completed(monkeypatch):
    calls = []
    monkeypatch.setattr(worker.store, "list_ready", lambda limit: [_row()])
    monkeypatch.setattr(worker.store, "claim_for_execution", lambda _id: _row())
    monkeypatch.setattr(worker.store, "get_campaign", lambda _id: {"operator_id": "op-1"})
    monkeypatch.setattr(worker.store, "mark_completed", lambda *args: calls.append(("completed", args)))

    result = worker.run_once(
        operator_lookup=lambda _id: {"ln_account_id": "account-1"},
        post=lambda path, payload: calls.append((path, payload)) or {"id": "remote-1"},
    )

    assert result["completed"] == 1
    assert calls[0] == ("/api/v1/posts/post-1/comments", {
        "account_id": "account-1",
        "text": "{{0}}, ótima leitura.",
        "mentions": [{"name": "Pessoa", "profile_id": "ACo-target"}],
    })
    assert calls[1][0] == "completed"


def test_worker_never_retries_ambiguous_external_failure(monkeypatch):
    errors = []
    monkeypatch.setattr(worker.store, "list_ready", lambda limit: [_row()])
    monkeypatch.setattr(worker.store, "claim_for_execution", lambda _id: _row())
    monkeypatch.setattr(worker.store, "get_campaign", lambda _id: {"operator_id": "op-1"})
    monkeypatch.setattr(worker.store, "mark_needs_reconciliation", lambda *args: errors.append(args))

    result = worker.run_once(
        operator_lookup=lambda _id: {"ln_account_id": "account-1"},
        post=lambda *_args: (_ for _ in ()).throw(RuntimeError("timeout")),
    )

    assert result["reconciliation"] == 1
    assert errors == [("intent-1", "timeout")]


def test_reconciliation_marks_comment_completed_without_posting(monkeypatch):
    marked = []
    monkeypatch.setattr(worker.store, "get_intent", lambda _id: {
        **_row(), "status": "needs_reconciliation",
    })
    monkeypatch.setattr(worker.store, "mark_reconciled", lambda *args: marked.append(args))
    calls = []

    result = worker.reconcile_intent(
        "intent-1",
        account_id="account-1",
        get=lambda path, params: calls.append((path, params)) or {
            "items": [{"id": "remote-1", "text": "{{0}}, ótima leitura."}]
        },
    )

    assert result["status"] == "reconciled"
    assert calls == [("/api/v1/posts/post-1/comments", {"account_id": "account-1"})]
    assert marked[0][0] == "intent-1"
