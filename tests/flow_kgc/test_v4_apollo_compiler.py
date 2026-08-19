from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from flow_kgc_v4 import (
    ApolloLeadContext,
    ApolloPromptInput,
    ApolloSignalContext,
    compile_apollo_prompt_context,
    compile_apollo_signals,
)


def _mariana() -> ApolloLeadContext:
    return ApolloLeadContext(
        full_name="Mariana Schlithler Bonini",
        title="Revenue Operations (RevOps) & Sales Enablement Manager",
        headline="CRM Optimization | GTM Orchestration | Sales Playbooks",
        company_name="SoftExpert - Software for Excellence",
        company_industry="information technology & services",
        company_evidence=(
            "A empresa publica vagas de SDR/BDR com cadências, qualificação e registro em CRM.",
            "A operação apresenta sinais de inbound, outbound, parceiros e segmentos.",
        ),
        profile_evidence=("O perfil declara RevOps, Sales Enablement e otimização de CRM.",),
    )


def test_compiler_combines_mariana_company_persona_and_signals():
    block = compile_apollo_prompt_context(ApolloPromptInput(
        lead=_mariana(),
        signals=ApolloSignalContext(
            post_reactions=("orquestração de GTM",),
            leadmagnet_received=("prospecção ativa B2B",),
            follows_company_page=True,
            company_page_engagements=("operações comerciais previsíveis",),
            company_peer_engagements=("1 colega da SoftExpert reagiu a conteúdo da página",),
            compares_market=True,
        ),
    ))

    assert "SoftExpert - Software for Excellence" in block
    assert "RevOps / Sales Enablement" in block
    assert "recebeu um material sobre prospecção ativa B2B" in block
    assert "🔥 Compara/acompanha o mercado ativamente" in block
    assert "🏢 Engaja mais com a página" in block
    assert "🏢 1 colega da mesma empresa também engaja" in block
    assert "não cite literalmente" in block
    assert "não empilhe sinal, dor, funcionalidades" in block.lower()


def test_leadmagnet_does_not_claim_download_or_reading():
    result = compile_apollo_signals(ApolloSignalContext(
        leadmagnet_received=("playbook de outbound",),
    ))

    assert "recebeu um material" in result.block
    assert "baixou o material playbook" not in result.block
    assert "leu o material" not in result.block


def test_confirmed_landing_page_download_authorizes_download_wording():
    result = compile_apollo_signals(ApolloSignalContext(
        landing_pages_downloaded=("Guia de RevOps",),
    ))

    assert "baixou o material Guia de RevOps" in result.block


def test_repost_is_not_treated_as_authored_post():
    result = compile_apollo_signals(ApolloSignalContext(
        reposts=("rituais de gestão comercial",),
    ))

    assert "republicou uma publicação" in result.block
    assert "não atribua autoria" in result.block


def test_no_signal_keeps_neutral_fallback():
    block = compile_apollo_prompt_context(ApolloPromptInput(lead=_mariana()))

    assert "nenhum sinal observado disponível" in block
    assert "ROTA: CONTATO FRIO POR CARGO" in block
    assert "Escolha UMA hipótese" in block
    assert "nunca como dor confirmada da empresa" in block
    assert "como esse desafio é tratado hoje na operação" in block


def test_compiler_uses_competitor_topic_without_authorizing_source_disclosure():
    block = compile_apollo_prompt_context(ApolloPromptInput(
        lead=_mariana(),
        signals=ApolloSignalContext(
            competitor_content_context=("integração entre dados, cadências e CRM",),
        ),
    ))

    assert "tema contextual: integração entre dados, cadências e CRM" in block
    assert "nunca nomeie o concorrente" in block
    assert "ROTA: CONTEXTO COM SINAL" in block
    assert "use silenciosamente o tema de mercado" in block


def test_cold_unknown_role_uses_generic_apollo_challenge_without_diagnosis():
    block = compile_apollo_prompt_context(ApolloPromptInput(
        lead=ApolloLeadContext(
            full_name="Contato Frio",
            title="Sócio",
            headline="Tecnologia e negócios",
            company_name="Empresa Exemplo",
        ),
    ))

    assert "PERSONA APOLLO: Operação Comercial B2B" in block
    assert "dificuldade de encontrar contas e decisores aderentes ao ICP" in block
    assert "não afirme como fato" in block
    assert "ROTA: CONTATO FRIO POR CARGO" in block
