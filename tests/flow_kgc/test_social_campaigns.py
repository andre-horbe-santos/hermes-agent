from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from flow_kgc.social_campaigns import plan_for_flow_entry
from sales_signal.social_campaigns import (
    CampaignKind,
    LinkedInPost,
    SocialTarget,
    approve_comment,
    execute_intent,
    plan_engagement,
    vary_comment_for_operator,
)


NOW = datetime(2026, 8, 25, 12, tzinfo=timezone.utc)


def _post(**overrides):
    data = dict(
        id="post-1",
        author_linkedin_id="lead-ln",
        text="Uma reflexao concreta sobre previsibilidade comercial.",
        published_at=NOW - timedelta(days=1),
        url="https://linkedin.test/post-1",
    )
    data.update(overrides)
    return LinkedInPost(**data)


def test_warmup_plans_like_and_a_manually_approved_comment():
    target = SocialTarget("lead-1", "lead-ln", "Lead Teste", lead_uuid="lead-1")

    intents = plan_engagement("campaign-1", CampaignKind.WARMUP, target, [_post()], now=NOW)

    assert [intent.action for intent in intents] == ["like", "comment"]
    assert intents[0].status == "waiting_approval"
    assert intents[1].status == "waiting_approval"
    assert intents[0].idempotency_key != intents[1].idempotency_key


def test_warmup_accepts_any_flow_contact_without_lead_uuid():
    target = SocialTarget("entry-1", "lead-ln", "Lead do Flow")

    intents = plan_engagement("campaign-1", "warmup", target, [_post()], now=NOW)

    assert len(intents) == 2


def test_explicit_name_marker_becomes_unipile_linkedin_mention():
    target = SocialTarget("entry-1", "ACo-target", "Pessoa do Flow")

    comment = plan_engagement(
        "campaign-1", "warmup", target, [_post(author_linkedin_id="ACo-target")],
        comment_text="[@nome], ótima reflexão.", now=NOW,
    )[1]

    assert comment.comment_text == "{{0}}, ótima reflexão."
    assert comment.mentions == ({"name": "Pessoa do Flow", "profile_id": "ACo-target"},)


def test_authority_campaign_also_supports_explicit_name_marker():
    target = SocialTarget("profile-1", "ACo-author", "Perfil Estratégico", strategic=True)

    comment = plan_engagement(
        "authority-1", "authority", target,
        [_post(author_linkedin_id="ACo-author")],
        comment_text="[@nome], esse ponto é importante.", now=NOW,
    )[1]

    assert comment.comment_text == "{{0}}, esse ponto é importante."
    assert comment.mentions == ({"name": "Perfil Estratégico", "profile_id": "ACo-author"},)


def test_authority_rejects_unmarked_profile_and_accepts_strategic_profile():
    ordinary = SocialTarget("profile-1", "profile-ln", "Perfil")
    with pytest.raises(ValueError, match="perfil estrategico"):
        plan_engagement("campaign-1", "authority", ordinary, [], now=NOW)

    strategic = SocialTarget("profile-1", "lead-ln", "Perfil", strategic=True)
    intents = plan_engagement("campaign-1", "authority", strategic, [_post()], now=NOW)
    assert len(intents) == 2


def test_post_selection_rejects_old_repost_and_wrong_author():
    target = SocialTarget("lead-1", "lead-ln", "Lead", lead_uuid="lead-1")
    posts = [
        _post(id="old", published_at=NOW - timedelta(days=15)),
        _post(id="repost", is_repost=True),
        _post(id="other", author_linkedin_id="other-ln"),
    ]

    assert plan_engagement("campaign-1", "warmup", target, posts, now=NOW) == []


def test_comment_only_becomes_ready_with_nonempty_approved_copy():
    target = SocialTarget("lead-1", "lead-ln", "Lead", lead_uuid="lead-1")
    comment = plan_engagement("campaign-1", "warmup", target, [_post()], now=NOW)[1]

    approved = approve_comment(comment, "Boa leitura sobre o papel da previsibilidade.")

    assert approved.status == "ready"
    assert approved.comment_text.startswith("Boa leitura")
    with pytest.raises(ValueError, match="nao pode ser vazio"):
        approve_comment(comment, "  ")


def test_flow_adapter_preserves_campaign_and_target_identity():
    intents = plan_for_flow_entry(
        {"id": "entry-1", "lead_uuid": "lead-1", "linkedin_id": "lead-ln", "full_name": "Lead"},
        {"id": "campaign-1", "kind": "warmup"},
        [{"social_id": "post-1", "text": "Conteudo", "published_at": NOW.isoformat()}],
        now=NOW,
    )

    assert {intent.campaign_id for intent in intents} == {"campaign-1"}
    assert {intent.target_id for intent in intents} == {"lead-1"}


def test_execution_claims_before_unipile_and_does_not_repeat_effect():
    target = SocialTarget("lead-1", "lead-ln", "Lead", lead_uuid="lead-1")
    like = approve_comment(
        plan_engagement("campaign-1", "warmup", target, [_post()], now=NOW)[0], ""
    )
    claimed = set()
    calls = []

    def claim(key):
        if key in claimed:
            return False
        claimed.add(key)
        return True

    def post(path, payload):
        calls.append((path, payload))
        return {"id": "remote-1"}

    first = execute_intent(like, account_id="account-1", claim=claim, post=post)
    duplicate = execute_intent(like, account_id="account-1", claim=claim, post=post)

    assert first["status"] == "completed"
    assert duplicate["status"] == "duplicate"
    assert calls == [("/api/v1/posts/reaction", {
        "account_id": "account-1", "post_id": "post-1", "reaction_type": "like",
    })]


def test_comment_execution_uses_approved_copy():
    target = SocialTarget("lead-1", "lead-ln", "Lead", lead_uuid="lead-1")
    draft = plan_engagement("campaign-1", "warmup", target, [_post()], now=NOW)[1]
    approved = approve_comment(draft, "Comentario humano aprovado.")
    calls = []

    execute_intent(
        approved,
        account_id="account-1",
        claim=lambda _key: True,
        post=lambda path, payload: calls.append((path, payload)) or {},
    )

    assert calls == [("/api/v1/posts/post-1/comments", {
        "account_id": "account-1", "text": "Comentario humano aprovado.",
    })]


def test_comment_execution_sends_mentions_separately_from_text():
    target = SocialTarget("entry-1", "ACo-target", "Pessoa do Flow")
    draft = plan_engagement(
        "campaign-1", "warmup", target,
        [_post(author_linkedin_id="ACo-target")],
        comment_text="[@nome], ótima reflexão.", now=NOW,
    )[1]
    approved = approve_comment(draft, draft.comment_text)
    calls = []

    execute_intent(
        approved, account_id="account-1", claim=lambda _key: True,
        post=lambda path, payload: calls.append((path, payload)) or {},
    )

    assert calls[0][1]["text"] == "{{0}}, ótima reflexão."
    assert calls[0][1]["mentions"] == [{"name": "Pessoa do Flow", "profile_id": "ACo-target"}]


def test_team_operator_variant_keeps_first_copy_and_changes_next_angle():
    base = "Boa leitura sobre previsibilidade comercial."

    first = vary_comment_for_operator(base, "andre", [])
    second = vary_comment_for_operator(base, "jefferson", [first], force=True)

    assert first != second
    assert first == base
    assert "mercado percebe valor" in second


def test_operator_variant_is_only_added_when_copy_collides():
    base = "Esse ponto merece atenção."

    assert vary_comment_for_operator(base, "andre", []) == base
    changed = vary_comment_for_operator(base, "andre", [base])

    assert changed != base
    assert changed.startswith("Esse ponto merece atenção.")
