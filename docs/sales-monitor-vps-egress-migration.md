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

## Estado atual

- O recálculo integral de Eng./Int. foi interrompido a pedido do usuário.
- A amostra Apify foi persistida no Lead Monitor.
- Não ativar novos jobs de backfill até a frente de egress definir o cache e o
  limite de consultas.
