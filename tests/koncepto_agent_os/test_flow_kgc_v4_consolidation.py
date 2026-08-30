from __future__ import annotations

import importlib.util
import types
from pathlib import Path

import pytest


def _load_flow_steps():
    koncepto_root = Path(__file__).resolve().parents[3]
    flow_root = koncepto_root / "scripts" / "flow_kgc"
    package_name = "koncepto_agent_os.scripts.flow_kgc"

    package = types.ModuleType(package_name)
    package.__path__ = [str(flow_root)]
    import sys

    sys.modules[package_name] = package
    module_name = f"{package_name}.flow_steps"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, flow_root / "flow_steps.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_consultoria_v4_uses_v3_tree_and_keeps_apollo_v4_separate():
    flow_steps = _load_flow_steps()
    consultoria = flow_steps.FLOWS["kgc_i_ln_v4"]
    consultoria_v3 = flow_steps.FLOWS["kgc_i_ln_v3"]
    apollo_v4 = flow_steps.FLOWS["kgc_ii_ln_v4"]

    consultoria_types = [step["type"] for step in consultoria["steps"]]
    v3_types = [step["type"] for step in consultoria_v3["steps"]]
    assert consultoria_types == v3_types

    consultoria_wait = next(step for step in consultoria["steps"] if step["type"] == "wait_reply")
    assert consultoria_wait["timeout_days_sequence"] == [2, 2, 3, 2]
    assert "timeout_days" not in consultoria_wait

    consultoria_dm = next(step for step in consultoria["steps"] if step["type"] == "ln_message")
    apollo_dm = next(step for step in apollo_v4["steps"] if step["type"] == "ln_message")
    assert consultoria_dm["prompt"] != apollo_dm["prompt"]
    assert consultoria["name"] == "Flow v4 — ICP I · Consultoria (LinkedIn)"
    assert apollo_v4["name"] == "V4 — Flow KGC ICP II · LinkedIn (Apollo)"


@pytest.mark.parametrize("flow_id", ["kgc_i_ln_v4", "kgc_ii_ln_v4"])
def test_v4_connection_request_prompt_keeps_linkedin_contract(flow_id):
    flow_steps = _load_flow_steps()
    invite = next(step for step in flow_steps.FLOWS[flow_id]["steps"] if step["type"] == "ln_invite")
    prompt = invite["prompt"]

    assert "Máx 280 caracteres TOTAL" in prompt
    assert "Contexto disponível" in prompt
    assert "{first_name}" in prompt
    assert "{company_industry}" in prompt
    assert "contexto do lead" in prompt.lower()


@pytest.mark.parametrize("flow_id", ["kgc_i_ln_v4", "kgc_ii_ln_v4"])
def test_v4_connected_prompt_does_not_treat_existing_connection_as_new(flow_id):
    flow_steps = _load_flow_steps()
    message = next(step for step in flow_steps.FLOWS[flow_id]["steps"] if step["type"] == "ln_message")
    prompt = message["prompt_if_connected"].lower()

    assert "já são conexão" in prompt
    assert "não trate isso como convite novo" in prompt or "não trate a conexão como relacionamento prévio" in prompt
    assert "obrigado por conectar" in prompt
    assert "obrigado por seguir" in prompt


@pytest.mark.parametrize("flow_id", ["kgc_i_ln_v4", "kgc_ii_ln_v4"])
def test_v4_followup_loop_has_three_ordered_messages_with_low_friction_ctas(flow_id):
    flow_steps = _load_flow_steps()
    loop = next(step for step in flow_steps.FLOWS[flow_id]["steps"] if step["type"] == "ln_followup_loop")
    prompts = loop["prompts"]

    assert len(prompts) == 3
    assert all("follow-up" in prompt.lower() for prompt in prompts)
    assert "baixíssima fricção" in prompts[0].lower()
    assert "não pergunte ainda sobre newsletter ou material" in prompts[0].lower()
    assert "cta sutil" in prompts[1].lower()
    assert "último follow-up" in prompts[2].lower()
    assert all("bom dia" in prompt.lower() for prompt in prompts[:2])
