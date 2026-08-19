from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from flow_kgc_v4 import (
    ApolloSignalContext,
    ContactPreparationInput,
    HistoricalMaterialDelivery,
    LinkedInIdentity,
    compile_apollo_signals,
    prepare_contact,
)


def test_nemora_reconciles_vanity_and_provider_identity_and_recovers_old_material():
    snapshot = prepare_contact(ContactPreparationInput(
        primary_identity=LinkedInIdentity(
            lead_id="344b6f24-75db-4172-910d-fdaddb2d860c",
            vanity_name="nemoramadeiragomes",
            profile_url="https://www.linkedin.com/in/nemoramadeiragomes",
        ),
        related_identities=(LinkedInIdentity(
            lead_id="65f4d003-22c1-463f-9689-67cd95b7b7f5",
            provider_id="ACoAAAKm3zEB0R_aH5gv4Ipa38nBM2FhyetP7-g",
            profile_url="https://www.linkedin.com/in/ACoAAAKm3zEB0R_aH5gv4Ipa38nBM2FhyetP7-g",
        ),),
        signal_fragments=(
            ApolloSignalContext(
                post_comments=("modernização da operação comercial",),
                compares_market=True,
            ),
            ApolloSignalContext(follows_operators=("André Santos",)),
        ),
        material_deliveries=(HistoricalMaterialDelivery(
            title="Ímã de Lead sobre Prospecção B2B",
            sent_at="2026-04-15T14:00:00-03:00",
            source="unipile_history",
        ),),
        prepared_at="2026-08-19T15:00:00-03:00",
    ))

    assert snapshot.lead_ids == (
        "344b6f24-75db-4172-910d-fdaddb2d860c",
        "65f4d003-22c1-463f-9689-67cd95b7b7f5",
    )
    assert "nemoramadeiragomes" in snapshot.identity_keys
    assert "ACoAAAKm3zEB0R_aH5gv4Ipa38nBM2FhyetP7-g" in snapshot.identity_keys
    assert snapshot.signals.follows_operators == ("André Santos",)
    assert snapshot.signals.leadmagnet_received == ("Ímã de Lead sobre Prospecção B2B",)
    assert snapshot.signals.landing_pages_downloaded == ()
    assert "material recuperado do histórico" in " ".join(snapshot.warnings)

    compiled = compile_apollo_signals(snapshot.signals)
    assert "recebeu um material sobre Ímã de Lead sobre Prospecção B2B" in compiled.block
    assert "baixou o material" not in compiled.block


def test_preparation_merges_fragments_without_duplicate_signals():
    snapshot = prepare_contact(ContactPreparationInput(
        primary_identity=LinkedInIdentity(lead_id="lead-1", vanity_name="lead"),
        signal_fragments=(
            ApolloSignalContext(post_reactions=("tema A",), engagement_intent_score=20),
            ApolloSignalContext(post_reactions=("tema A", "tema B"), engagement_intent_score=45),
        ),
    ))

    assert snapshot.signals.post_reactions == ("tema A", "tema B")
    assert snapshot.signals.engagement_intent_score == 45


def test_confirmed_landing_page_event_is_preserved_as_download():
    snapshot = prepare_contact(ContactPreparationInput(
        primary_identity=LinkedInIdentity(lead_id="lead-1"),
        material_deliveries=(HistoricalMaterialDelivery(
            title="Guia de RevOps",
            sent_at="2026-08-01T10:00:00Z",
            source="landing_page",
            downloaded=True,
        ),),
    ))

    assert snapshot.signals.landing_pages_downloaded == ("Guia de RevOps",)
    assert snapshot.signals.leadmagnet_received == ()
