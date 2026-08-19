from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from flow_kgc_v4 import EntryCollectors, snapshot_to_dict


def test_entry_collector_reconciles_identity_and_finds_old_material_in_chat():
    calls = []

    def rest_get(table, params):
        calls.append((table, params))
        if table == "ssk_leads" and params.get("id"):
            return [{
                "id": "lead-vanity", "first_name": "Nêmora", "last_name": "Gomes Rosa",
                "company_id": "dcit", "linkedin_username": "nemoramadeiragomes",
                "job_title": "Gerente Comercial", "tags": ["compara_mercado"],
                "crm_id": "hs-123", "crm_deal_status": "qualified",
            }]
        if table == "ssk_leads":
            return [
                {"id": "lead-vanity", "first_name": "Nêmora", "last_name": "Gomes Rosa",
                 "company_id": "dcit", "linkedin_username": "nemoramadeiragomes"},
                {"id": "lead-provider", "first_name": "Nêmora", "last_name": "Gomes Rosa",
                 "company_id": "dcit", "linkedin_username": "ACoAAA-provider"},
            ]
        if table == "ssk_engagements":
            if params["lead_id"] == "eq.lead-provider":
                return [{"event_type": "profile_follower", "description": "",
                         "ssk_profiles": {"name": "André Santos"}}]
            return [{"event_type": "tracked_post_comment", "description": "modernização comercial"}]
        if table == "leadmagnet_posts":
            return [{"post_title": "Ímã de Lead Apollo", "material_link": "https://k.example/ima"}]
        return []

    collector = EntryCollectors(
        rest_get=rest_get,
        resolve_provider_id=lambda vanity, entry: "ACoAAA-provider",
        find_existing_chat=lambda provider, entry: "chat-1",
        get_chat_history=lambda chat, entry, limit: [{
            "from_lead": False,
            "text": "Como prometido: https://k.example/ima",
            "timestamp": "2026-04-15T14:00:00-03:00",
        }],
    )
    snapshot = collector.collect({
        "id": "entry-1", "lead_uuid": "lead-vanity", "linkedin_id": "nemoramadeiragomes",
        "linkedin_url": "https://linkedin.com/in/nemoramadeiragomes", "tags": ["apollo"],
    })

    assert snapshot.lead_ids == ("lead-vanity", "lead-provider")
    assert snapshot.signals.post_comments == ("modernização comercial",)
    assert snapshot.signals.follows_operators == ("André Santos",)
    assert snapshot.signals.leadmagnet_received == ("Ímã de Lead Apollo",)
    assert snapshot.signals.in_hubspot is True
    assert snapshot.signals.hubspot_contact_id == "hs-123"
    assert snapshot.signals.landing_pages_downloaded == ()
    assert snapshot_to_dict(snapshot)["schema_version"] == 1
    assert any(table == "leadmagnet_interactions" for table, _ in calls)


def test_entry_collector_never_creates_chat_when_none_exists():
    history_calls = []
    collector = EntryCollectors(
        rest_get=lambda table, params: [],
        resolve_provider_id=lambda vanity, entry: "provider-1",
        find_existing_chat=lambda provider, entry: None,
        get_chat_history=lambda *args: history_calls.append(args) or [],
    )

    snapshot = collector.collect({"lead_uuid": "lead-1", "linkedin_id": "cold-lead"})

    assert history_calls == []
    assert snapshot.lead_ids == ("lead-1",)


def test_entry_collector_recovers_legacy_material_not_present_in_catalog():
    collector = EntryCollectors(
        rest_get=lambda table, params: [],
        resolve_provider_id=lambda vanity, entry: "provider-1",
        find_existing_chat=lambda provider, entry: "chat-1",
        get_chat_history=lambda chat, entry, limit: [{
            "from_lead": False,
            "text": ("Você solicitou o envio do material sobre Objeções de Vendas no meu post. "
                     "Aqui está: https://konceptogc.kit.com/material-objecoes-de-vendas"),
            "timestamp": "2026-04-09T18:19:19.541Z",
        }],
    )

    snapshot = collector.collect({"lead_uuid": "lead-1", "linkedin_id": "nemora"})

    assert snapshot.signals.leadmagnet_received == ("Objeções de Vendas",)
    assert snapshot.signals.landing_pages_downloaded == ()


def test_entry_collector_extracts_explicit_platform_mentions_from_profile():
    collector = EntryCollectors(
        rest_get=lambda table, params: [{
            "id": "lead-1",
            "first_name": "Mariana",
            "last_name": "Bonini",
            "company_id": "softexpert",
            "linkedin_username": "mariana-bonini",
            "linkedin_url": "https://www.linkedin.com/in/mariana-bonini",
            "headline": (
                "Revenue Operations (RevOps) & Sales Enablement Manager | "
                "CRM Optimization | GTM Orchestration | Sales Tools"
            ),
            "job_title": "Revenue Operations (RevOps) & Sales Enablement Manager",
        }] if table == "ssk_leads" and params.get("id") else [],
        resolve_provider_id=lambda vanity, entry: "mariana-bonini",
        find_existing_chat=lambda provider, entry: None,
        get_chat_history=lambda *args: [],
    )

    snapshot = collector.collect({
        "lead_uuid": "lead-1",
        "linkedin_id": "mariana-bonini",
        "linkedin_url": "https://www.linkedin.com/in/mariana-bonini",
    })

    assert snapshot.profile_evidence == ("O perfil menciona CRM.",)
    assert snapshot.company_evidence == ()
    assert snapshot.signals.engagement_intent_score == 0
