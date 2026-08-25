"""Consulta cadastral de empresas brasileiras por CNPJ.

Consulta somente: não altera Ploomes, HubSpot ou qualquer outro CRM.
BrasilAPI é a fonte principal e ReceitaWS pode ser usada como fallback quando
RECEITAWS_TOKEN estiver configurado.
"""

from __future__ import annotations

import os
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx

from tools.registry import registry, tool_error


BRASIL_API = "https://brasilapi.com.br/api/cnpj/v1"
RECEITA_API = "https://www.receitaws.com.br/v1/cnpj"


def _load_token() -> str:
    token = os.environ.get("RECEITAWS_TOKEN", "").strip()
    if token:
        return token
    env_path = Path("/home/hermes/.hermes/.env")
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() == "RECEITAWS_TOKEN":
                return value.strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def clean_cnpj(value: object) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 14 or len(set(digits)) == 1:
        return ""
    for length, weights in (
        (12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]),
        (13, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]),
    ):
        check = (sum(int(digits[i]) * weights[i] for i in range(length)) * 10) % 11
        if check == 10:
            check = 0
        if int(digits[length]) != check:
            return ""
    return digits


def _first(data: dict, *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _normalize(data: dict, source: str, cnpj: str) -> dict:
    activities = data.get("atividade_principal") or []
    activity = activities[0] if isinstance(activities, list) and activities else {}
    return {
        "cnpj": cnpj,
        "razao_social": _first(data, "razao_social", "nome"),
        "nome_fantasia": _first(data, "nome_fantasia", "fantasia"),
        "situacao_cadastral": _first(data, "descricao_situacao_cadastral", "situacao"),
        "porte": _first(data, "porte"),
        "capital_social": _first(data, "capital_social"),
        "data_inicio_atividade": _first(data, "data_inicio_atividade", "abertura"),
        "cnae": _first(data, "cnae_fiscal") or _first(activity, "code"),
        "cnae_descricao": _first(data, "cnae_fiscal_descricao") or _first(activity, "text"),
        "telefone": _first(data, "ddd_telefone_1", "telefone", "ddd_telefone_2"),
        "email": _first(data, "correio_eletronico", "email"),
        "site": _first(data, "site"),
        "endereco": {
            "logradouro": _first(data, "logradouro"),
            "numero": _first(data, "numero"),
            "complemento": _first(data, "complemento"),
            "bairro": _first(data, "bairro"),
            "municipio": _first(data, "municipio"),
            "uf": _first(data, "uf"),
            "cep": _first(data, "cep"),
        },
        "socios": data.get("qsa") or [],
        "fonte": source,
        "consultado_em": datetime.now(timezone.utc).isoformat(),
    }


def consultar_cnpj(cnpj: str) -> str:
    """Consulta dados cadastrais públicos e retorna JSON normalizado."""
    normalized = clean_cnpj(cnpj)
    if not normalized:
        return tool_error("CNPJ inválido. Informe os 14 dígitos, com ou sem pontuação.")

    errors = []
    try:
        with httpx.Client(timeout=30, headers={"User-Agent": "Hermes CNPJ Lookup/1.0"}) as client:
            response = client.get(f"{BRASIL_API}/{normalized}")
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("resposta inválida")
            return json.dumps(_normalize(data, "BrasilAPI", normalized), ensure_ascii=False)
    except Exception as exc:
        errors.append(f"BrasilAPI: {str(exc)[:180]}")

    token = _load_token()
    if token:
        try:
            with httpx.Client(timeout=30, headers={"User-Agent": "Hermes CNPJ Lookup/1.0"}) as client:
                response = client.get(f"{RECEITA_API}/{normalized}", params={"token": token})
                response.raise_for_status()
                data = response.json()
                if str(data.get("status", "")).lower() == "error":
                    raise ValueError(data.get("message") or "ReceitaWS retornou erro")
                return json.dumps(_normalize(data, "ReceitaWS", normalized), ensure_ascii=False)
        except Exception as exc:
            errors.append(f"ReceitaWS: {str(exc)[:180]}")

    return tool_error("Não foi possível consultar o CNPJ: " + " | ".join(errors))


CNPJ_LOOKUP_SCHEMA = {
    "name": "consultar_cnpj",
    "description": (
        "Consultar dados cadastrais públicos de uma empresa brasileira pelo CNPJ. "
        "Retorna razão social, nome fantasia, situação, CNAE, endereço, contato e sócios. "
        "Somente leitura: não altera nenhum CRM."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "cnpj": {"type": "string", "description": "CNPJ com ou sem pontuação."},
        },
        "required": ["cnpj"],
    },
}


registry.register(
    name="consultar_cnpj",
    toolset="web",
    schema=CNPJ_LOOKUP_SCHEMA,
    handler=lambda args, **kw: consultar_cnpj(args.get("cnpj", "")),
    emoji="🏢",
    max_result_size_chars=50_000,
)
