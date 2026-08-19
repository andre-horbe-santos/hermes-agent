from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from flow_kgc_v4.apollo_persona import resolve_apollo_persona


def test_revops_enablement_uses_governance_and_orchestration_hypotheses():
    policy = resolve_apollo_persona(
        "Revenue Operations (RevOps) & Sales Enablement Manager",
        "CRM Optimization | GTM Orchestration | Sales Playbooks | Sales Tools",
    )

    assert policy.key == "revops_enablement"
    assert any("CRM" in capability for capability in policy.capabilities)
    assert any("playbook" in pain for pain in policy.pains)
    assert any("governança" in question for question in policy.discovery_questions)


def test_revops_wins_over_generic_sales_terms():
    policy = resolve_apollo_persona(
        "Sales Operations Manager",
        "Revenue Operations and Sales Leadership",
    )

    assert policy.key == "revops_enablement"


def test_unknown_title_falls_back_without_inventing_a_specific_pain():
    policy = resolve_apollo_persona("Sócia", "Tecnologia e negócios")

    assert policy.key == "apollo_generic"
    assert "não afirme como fato" in policy.prompt_block()


def test_prompt_block_requires_evidence_and_only_one_discovery_question():
    block = resolve_apollo_persona("RevOps Manager").prompt_block()

    assert "Dados da empresa e do perfil precisam sustentar" in block
    assert "escolha apenas uma" in block
