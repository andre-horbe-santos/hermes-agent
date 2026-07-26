# Sales Monitor — redução de egress via VPS

## Decisão

Centralizar na VPS o acesso do Sales Monitor ao Supabase. O frontend e os
consumidores externos não devem consultar o PostgREST diretamente.

Fluxo-alvo:

```text
Supabase -> VPS (worker/cache/API) -> dashboard e clientes
```

Isso concentra as leituras, permite cache local e evita que cada usuário ou
tela repita consultas grandes. O tráfego Supabase → VPS ainda é egress; para
eliminá-lo quase totalmente, será necessária uma réplica/cache local das
tabelas de leitura.

## Fases

1. Identificar e desligar acessos diretos do frontend, jobs e integrações ao
   Supabase.
2. Expor na VPS uma API interna para o Lead Monitor e mover o cache para a
   VPS.
3. Substituir consultas amplas por campos explícitos, paginação, compressão e
   respostas sem `return=representation` quando não forem necessárias.
4. Executar backfills e recomputações em lotes na VPS, evitando milhares de
   requisições individuais.
5. Avaliar réplica local/read model para `ssk_leads`, `ssk_engagements`,
   `ssk_posts` e tabelas de suporte; manter no Supabase apenas as escritas e a
   fonte de verdade até validar a réplica.

## Limite importante

Mover o processo para a VPS não zera o egress do Supabase: dados enviados do
Supabase para a VPS continuam sendo tráfego de saída. A redução vem de
concentrar, agregar e cachear as leituras. Migração do banco ou réplica local
é a etapa necessária para retirar a maior parte do tráfego do caminho do
Supabase.

## Estado atual (histórico — ver atualização de 2026-07-25 abaixo)

- O recálculo integral de Eng./Int. foi interrompido a pedido do usuário.
- A amostra Apify foi persistida no Lead Monitor.
- ~~Não ativar novos jobs de backfill até a frente de egress definir o
  cache e o limite de consultas.~~ Superado — ver abaixo, migração
  completa concluída no mesmo dia.

## Decisão — 2026-07-25: migração completa (não só cache) — CONCLUÍDA

André autorizou ir além do cache/mirror parcial descrito acima: sair do
Supabase gerenciado e rodar Postgres self-hosted na própria VPS
(PostgreSQL nativo via apt + PostgREST self-hosted na frente, mantendo os
~15 módulos `db.py` sem alteração de código), incluindo uma rotina de
backup/DR que hoje não existe.

- Plano aprovado: `~/.claude/plans/ticklish-shimmying-corbato.md`
- Runbook de execução (comandos exatos, Fases 1-4):
  `~/.hermes/operations/postgres-selfhost-migration-runbook.md`
- Registro do cutover: `~/.hermes/operations/postgres-selfhost-cutover-2026-07-25.md`
- Scripts prontos: `scripts/postgrest_jwt_gen.py`, `scripts/pg_backup.sh`

**Concluído no mesmo dia (2026-07-25), mesma sessão:** o bloqueio de sudo
foi resolvido (allowlist escopada, 4 scripts idempotentes) e as Fases 1-4
rodaram de ponta a ponta — Postgres 17 + PostgREST self-hosted instalados,
dados migrados (194MB, contagem idêntica à origem), cutover de produção
feito (14 crons + `flow-kgc-daemon` apontando pro banco novo). **A partir
daqui, `SUPABASE_FUNIL_URL` aponta pro self-hosted (`127.0.0.1:3101`) — o
Supabase gerenciado não é mais tocado por tráfego de aplicação nenhum**,
só existe como rollback (`SUPABASE_MANAGED_FUNIL_*` no `.env`). Ou seja: a
premissa "reduzir egress do Supabase" está resolvida da forma mais forte
possível (zero egress de aplicação), não só mitigada — qualquer job novo
(backfill Apify incluso) escreve no banco self-hosted, sem custo de egress
Supabase.

Pendências conscientes (não bloqueiam o item acima): backup/DR ainda não
registrado em cron, `local_mirror.py` ainda ativo (redundante), Cloudflare
Worker não migrado, secrets novos ainda só no `.env` (não Bitwarden).
