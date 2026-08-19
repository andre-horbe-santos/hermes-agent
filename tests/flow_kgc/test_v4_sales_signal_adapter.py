from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from flow_kgc_v4 import adapt_legacy_sales_signals, compile_apollo_signals


def test_adapter_maps_current_sales_signal_payload_and_internal_hubspot_alert():
    signals = adapt_legacy_sales_signals({
        "lead": {
            "follows_company_page": True,
            "engagement_score": 87,
            "tags": ["compara_mercado"],
            "crm_id": "hs-123",
            "crm_deal_status": "active",
        },
        "engagements": [
            {"event_type": "tracked_post_comment", "description": "orquestração de GTM"},
            {"event_type": "post_repost", "description": "governança de playbooks"},
        ],
        "leadmagnet": {"post_title": "Blueprint de Prospecção B2B"},
        "page_engagement": {"event_type": "page_reaction", "post_content": "receita previsível"},
        "personal_signals": [
            {"event_type": "profile_follower", "ssk_profiles": {"name": "André Santos"}},
            {"event_type": "connection_organic", "ssk_profiles": {"name": "Jefferson Frasnelli"}},
        ],
        "company_peers": [{"first_name": "Ana", "last_name": "Silva", "job_title": "SDR"}],
        "landing_pages_downloaded": ["Guia de RevOps"],
        "newsletter_subscriptions": ["Vendas Modernas B2B"],
    })
    compiled = compile_apollo_signals(signals)

    assert signals.post_comments == ("orquestração de GTM",)
    assert signals.reposts == ("governança de playbooks",)
    assert signals.follows_operators == ("André Santos",)
    assert signals.connected_operators == ("Jefferson Frasnelli",)
    assert signals.compares_market is True
    assert signals.engagement_intent_score == 87
    assert signals.in_hubspot is True
    assert "Eng. Int.: 87" in compiled.block
    assert "Contato já existe no HubSpot" in compiled.block
    assert "status do deal: active" in compiled.block
    assert "nunca mostrar nem mencionar ao contato" in compiled.block


def test_hubspot_presence_is_not_promoted_to_contact_facing_evidence():
    signals = adapt_legacy_sales_signals({"lead": {"crm_id": "hs-456"}})
    compiled = compile_apollo_signals(signals)

    observed_section = compiled.block.split("INSIGHTS DERIVADOS", 1)[0]
    assert "HubSpot" not in observed_section
    assert compiled.strongest_signal == ""


def test_entry_post_is_used_when_engagement_description_is_generic():
    signals = adapt_legacy_sales_signals(
        {"engagements": [{"event_type": "post_like", "description": "post_like"}]},
        {"signal_type": "post_like", "liked_post_text": "dados e previsibilidade comercial"},
    )

    assert signals.post_reactions[0] == "dados e previsibilidade comercial"


def test_competitor_engagement_becomes_silent_context_when_no_koncepto_signal():
    signals = adapt_legacy_sales_signals({
        "engagements": [{
            "event_type": "competitor_post_engagement",
            "description": "governança de dados e cadências comerciais",
        }],
    })
    compiled = compile_apollo_signals(signals)

    assert signals.competitor_content_context == ("governança de dados e cadências comerciais",)
    assert "tema contextual: governança de dados e cadências comerciais" in compiled.block
    assert "nunca revele fonte, concorrente ou interação" in compiled.block
    assert compiled.strongest_signal == ""


def test_direct_koncepto_signal_suppresses_competitor_context():
    signals = adapt_legacy_sales_signals({
        "engagements": [
            {"event_type": "competitor_post_comment", "description": "automação comercial"},
            {"event_type": "tracked_post_comment", "description": "prospecção orientada por ICP"},
        ],
    })
    compiled = compile_apollo_signals(signals)

    assert "contexto concorrente suprimido: existe sinal direto com a Koncepto" in compiled.block
    assert compiled.strongest_signal == "comentou em uma publicação sobre prospecção orientada por ICP"
