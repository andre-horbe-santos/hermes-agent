"""HubSpot deal report tool for ad-hoc @claude mentions in WhatsApp groups
(Sócios, Vendas) — replaces "traz um report do que está aberto pra foco em
FUPs" pedidos que hoje caem só no André.

Registers one LLM-callable, read-only tool:
- ``hs_report_deals`` -- lista deals abertos por pipeline/dono, com status
  de FUP (atrasado / sem próxima atividade / em dia)

Auth via ``HUBSPOT_ACCESS_TOKEN`` env var (mesmo token usado por
scripts/funil_cache_sync.py e demais scripts HubSpot do projeto).

v1 registrada em 2026-08-12 no toolset `hubspot_report`, habilitado só pra
`platform_toolsets.whatsapp` em config.yaml. Ainda NÃO testada contra o
HubSpot real — primeiro teste é via menção no grupo depois do restart do
gateway.

NÃO tem escrita nenhuma de propósito — ver project_whatsapp_hubspot_claude_
mention_2026-08-12.md: só sócios podem estar no grupo mas não há passo de
confirmação por menção, então nenhuma mutação de CRM deve ser disparável
daqui.
"""

import json
import logging
import os
import time
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

HS_BASE = "https://api.hubapi.com"

# Mesmos pipelines/estágios "abertos" curados em scripts/funil_cache_sync.py
# (fonte de verdade original). Duplicado aqui de propósito — os dois repos
# (hermes-agent e ~/.hermes/scripts) não compartilham sys.path. Se o funil
# mudar de estágio lá, replicar aqui também.
PIPELINES = [
    {
        "key": "funil_koncepto",
        "id": "default",
        "name": "Funil Koncepto",
        "stages": {
            "36480172": "MQL",
            "14502906": "Agendar Diagnóstico",
            "decisionmakerboughtin": "Apresentar Solução",
            "contractsent": "Negociações Iniciadas",
        },
    },
    {
        "key": "leads_prospeccao",
        "id": "866607466",
        "name": "Leads Prospecção P",
        "stages": {
            "1296482489": "Mudança Contato",
            "1321923381": "Conectado",
            "1296482561": "Pré-MQL",
            "1329913520": "No-show",
            "1296482560": "Retomada Agendada",
            "1296482563": "Sem Conexão",
        },
    },
    {
        "key": "leads_mkt",
        "id": "866608452",
        "name": "Leads MKT M",
        "stages": {
            "1296729382": "Conectado",
            "1296729383": "Pré-MQL",
            "1296729385": "No-show",
            "1347529881": "Retomada Agendada",
            "1296729387": "Sem Resposta",
            "1296729388": "Sem Conexão",
        },
    },
]

_MAX_DEALS_RETURNED = 20  # mantém a resposta curta pra caber numa mensagem de WhatsApp


def _get_token() -> str:
    return os.getenv("HUBSPOT_ACCESS_TOKEN", "")


def _headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Owners (resolve nome/e-mail digitado -> hubspot_owner_id)
# ---------------------------------------------------------------------------

_owners_cache: Dict[str, Any] = {"fetched_at": 0.0, "owners": []}
_OWNERS_TTL_SECONDS = 600  # 10min -- lista de sócios/donos muda raramente


async def _fetch_owners(session) -> List[dict]:
    now = time.monotonic()
    if _owners_cache["owners"] and (now - _owners_cache["fetched_at"]) < _OWNERS_TTL_SECONDS:
        return _owners_cache["owners"]

    owners: List[dict] = []
    after = None
    while True:
        params = {"limit": 100}
        if after:
            params["after"] = after
        async with session.get(
            f"{HS_BASE}/crm/v3/owners", headers=_headers(), params=params, timeout=15,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
        owners.extend(data.get("results", []))
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break

    _owners_cache["owners"] = owners
    _owners_cache["fetched_at"] = now
    return owners


def _match_owner(query: str, owners: List[dict]) -> Optional[dict]:
    """Fuzzy-match por nome/sobrenome/e-mail. Retorna o primeiro match ou None."""
    q = query.strip().lower()
    for o in owners:
        full_name = f"{o.get('firstName', '')} {o.get('lastName', '')}".strip().lower()
        email = (o.get("email") or "").lower()
        if q == email or q in full_name:
            return o
    return None


def _owner_display_name(owner: dict) -> str:
    name = f"{owner.get('firstName', '')} {owner.get('lastName', '')}".strip()
    return name or owner.get("email", owner.get("id", "?"))


# ---------------------------------------------------------------------------
# Deal search + FUP status
# ---------------------------------------------------------------------------

def _fup_status(hs_next_activity_date: Optional[str]) -> Dict[str, Any]:
    """Classifica o deal em atrasado / sem próxima atividade / em dia."""
    if not hs_next_activity_date:
        return {"label": "sem próxima atividade agendada", "overdue": True}
    try:
        next_date = date.fromisoformat(str(hs_next_activity_date)[:10])
    except Exception:
        return {"label": "sem próxima atividade agendada", "overdue": True}
    if next_date < date.today():
        late_days = (date.today() - next_date).days
        return {"label": f"atrasado há {late_days}d", "overdue": True}
    return {"label": f"agendado pra {next_date.strftime('%d/%m')}", "overdue": False}


async def _search_pipeline_deals(
    session, pipeline: dict, owner_id: Optional[str],
) -> List[dict]:
    filters = [
        {"propertyName": "pipeline", "operator": "EQ", "value": pipeline["id"]},
        {"propertyName": "dealstage", "operator": "IN", "values": list(pipeline["stages"].keys())},
    ]
    if owner_id:
        filters.append({"propertyName": "hubspot_owner_id", "operator": "EQ", "value": owner_id})

    body = {
        "filterGroups": [{"filters": filters}],
        "properties": [
            "dealname", "dealstage", "amount", "closedate",
            "hs_next_activity_date", "hs_lastmodifieddate", "hubspot_owner_id",
        ],
        "sorts": [{"propertyName": "hs_lastmodifieddate", "direction": "ASCENDING"}],
        "limit": 100,
    }
    async with session.post(
        f"{HS_BASE}/crm/v3/objects/deals/search",
        headers=_headers(), json=body, timeout=20,
    ) as resp:
        resp.raise_for_status()
        data = await resp.json()

    results = []
    for d in data.get("results", []):
        props = d["properties"]
        results.append({
            "pipeline": pipeline["name"],
            "dealname": props.get("dealname") or "(sem nome)",
            "stage": pipeline["stages"].get(props.get("dealstage"), props.get("dealstage")),
            "amount": props.get("amount"),
            "owner_id": props.get("hubspot_owner_id"),
            "fup": _fup_status(props.get("hs_next_activity_date")),
        })
    return results


async def _async_report(
    pipeline_key: Optional[str], owner_query: Optional[str], fup_only: bool,
) -> Dict[str, Any]:
    import aiohttp

    async with aiohttp.ClientSession() as session:
        owner_id = None
        owner_name = None
        if owner_query:
            owners = await _fetch_owners(session)
            match = _match_owner(owner_query, owners)
            if not match:
                return {"error": f"Nenhum dono do HubSpot encontrado pra '{owner_query}'"}
            owner_id = match["id"]
            owner_name = _owner_display_name(match)

        scope = [p for p in PIPELINES if pipeline_key in (None, "all", p["key"])]
        if not scope:
            valid = ", ".join(p["key"] for p in PIPELINES)
            return {"error": f"Pipeline '{pipeline_key}' inválido. Use: {valid}, ou 'all'."}

        all_deals: List[dict] = []
        for pipeline in scope:
            all_deals.extend(await _search_pipeline_deals(session, pipeline, owner_id))

    if fup_only:
        all_deals = [d for d in all_deals if d["fup"]["overdue"]]

    # Atrasados primeiro
    all_deals.sort(key=lambda d: (not d["fup"]["overdue"], d["dealname"]))

    truncated = len(all_deals) > _MAX_DEALS_RETURNED
    all_deals = all_deals[:_MAX_DEALS_RETURNED]

    return {
        "owner_filter": owner_name,
        "pipelines_checked": [p["name"] for p in scope],
        "count": len(all_deals),
        "truncated": truncated,
        "deals": all_deals,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Sync wrapper + handler
# ---------------------------------------------------------------------------

def _run_async(coro):
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=45)
    return asyncio.run(coro)


def _handle_report_deals(args: dict, **kw) -> str:
    pipeline_key = (args.get("pipeline") or "all").strip().lower()
    owner_query = args.get("owner")
    fup_only = bool(args.get("fup_only", False))
    try:
        result = _run_async(_async_report(pipeline_key, owner_query, fup_only))
        if "error" in result:
            return tool_error(result["error"])
        return json.dumps({"result": result}, ensure_ascii=False)
    except Exception as e:
        logger.error("hs_report_deals error: %s", e)
        return tool_error(f"Falha ao consultar HubSpot: {e}")


def _check_hubspot_available() -> bool:
    return bool(os.getenv("HUBSPOT_ACCESS_TOKEN"))


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

HS_REPORT_DEALS_SCHEMA = {
    "name": "hs_report_deals",
    "description": (
        "Consulta ao vivo os deals ABERTOS no HubSpot (nunca ganhos/perdidos), "
        "opcionalmente filtrados por dono e por status de follow-up (FUP). "
        "Use quando alguém pedir um report do funil/pipeline aberto, ex.: "
        "'traz o que tá aberto pra foco em FUP' ou 'o que o Thiago tem aberto'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "pipeline": {
                "type": "string",
                "description": (
                    "Qual pipeline consultar: 'funil_koncepto', 'leads_prospeccao', "
                    "'leads_mkt', ou 'all' pra todos. Default: 'all'."
                ),
            },
            "owner": {
                "type": "string",
                "description": (
                    "Nome (ou parte do nome) ou e-mail do dono do deal no HubSpot, "
                    "ex.: 'Thiago'. Omitir pra trazer de todos os donos."
                ),
            },
            "fup_only": {
                "type": "boolean",
                "description": (
                    "Se true, retorna só deals atrasados ou sem próxima atividade "
                    "agendada (foco em FUP). Default: false (todos os deals abertos "
                    "no escopo)."
                ),
            },
        },
        "required": [],
    },
}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

from tools.registry import registry, tool_error  # noqa: E402  (usado pelos handlers acima)

registry.register(
    name="hs_report_deals",
    toolset="hubspot_report",
    schema=HS_REPORT_DEALS_SCHEMA,
    handler=_handle_report_deals,
    check_fn=_check_hubspot_available,
    emoji="📊",
)
