# Contrato do snapshot

Use JSON UTF-8. Desconhecido é `null`, não zero.

```json
{
  "generated_at": "2026-08-27T15:00:00-03:00",
  "period": "2026-08-01 a 2026-08-27",
  "campaign": "Piloto V1",
  "source": "Apollo MCP",
  "coverage": "Listas selecionadas",
  "metrics": {"accounts": 0, "contacts": 0, "active": 0, "tasks_due": 0, "delivered": null, "replies": 0, "positive_replies": 0, "meetings": 0, "opportunities": null},
  "deal_flow": [{"stage": "Contatos", "required": 300, "planned": 300, "actual": 0}],
  "sequences": [{"name": "Prospecção", "active": 0, "tasks_due": 0, "replies": 0, "meetings": 0}],
  "alerts": [{"severity": "high", "title": "Exemplo", "detail": "Substitua por dado real"}],
  "queue": [{"due": "2026-08-28", "owner": "André", "type": "Retomada agendada", "count": 3}],
  "notes": ["Sem estimativas silenciosas"]
}
```

Não inclua e-mails, telefones ou listas nominais no painel salvo necessidade explícita.
