# Dashboard Koncepto — inventário inicial de governança

Este documento registra o contexto de segurança que deve ser considerado por
Claude, Codex e qualquer outro agente ao trabalhar no dashboard.koncepto.

## Escopo atual

O módulo **Configurações** está organizado em:

- 👤 Usuários e Sistema
- 🏥 Infraestrutura
- 🏗️ Arquitetura

O dashboard implementado neste repositório está principalmente em `web/` e
`hermes_cli/web_server.py`.

## Controles já existentes

- Autenticação obrigatória em binds não locais.
- Sessão por cookie/OAuth e token de sessão para o modo local.
- CORS restrito a `localhost` e `127.0.0.1`.
- Validação do header `Host` contra DNS rebinding.
- Allowlist explícita de rotas públicas; APIs administrativas permanecem protegidas.
- Autenticação bearer somente em rotas explicitamente registradas.
- Proteção adicional para WebSockets.
- Escopo operacional por profile.
- Auditoria de autenticação com remoção de tokens, cookies e códigos.
- Recursos existentes de backup, security audit, logs e status de ações.

## Regras obrigatórias para novas alterações

1. Não tratar confirmação visual do frontend como autorização. Toda ação sensível deve ser autorizada no backend.
2. Toda operação deve declarar o usuário, organização/workspace, projeto e ambiente ao qual se aplica.
3. Usuários autenticados não devem receber automaticamente acesso de administrador. Preferir scopes mínimos por ação.
4. Segredos não podem aparecer em prompt, commit, log, resposta de API, screenshot ou documentação.
5. Ações externas, destrutivas, de produção, de credenciais, de permissões ou de instalação de extensões exigem aprovação explícita e rastreável.
6. Desenvolvimento, homologação e produção devem usar credenciais, dados e destinos separados.
7. Alterações de negócio devem gerar auditoria sanitizada com ator, ação, recurso, ambiente, resultado e request ID quando disponível.
8. Plugins, skills, MCPs e dependências novas precisam de origem, versão, responsável, escopo, dados acessados e procedimento de revogação.
9. Antes de publicar, registrar versão, backup, monitoramento, critério de abortar e rollback.
10. Testes de autorização devem cobrir acesso cruzado entre usuários, organizações, profiles e ambientes.

## Lacunas prioritárias identificadas

- RBAC/scopes de negócio ainda não está consolidado para todas as rotas.
- Profile local não deve ser tratado como isolamento multi-tenant.
- Auditoria existente é forte em autenticação, mas precisa abranger mutações administrativas e ações de negócio.
- Confirmações do frontend precisam de correspondente server-side nas ações críticas.
- Falta uma matriz única relacionando tela, endpoint, dado, risco, papel, aprovação e evidência.

## Critério para a primeira fase

Antes de implementar novos controles, mapear cada tela e endpoint das três áreas
do módulo Configurações, incluindo leitura, escrita, dados acessados, ambiente,
risco e resultado esperado. O inventário deve ser revisado pelo responsável do
negócio antes de virar política ou código.

## Inventário inicial de telas e endpoints

Este é o mapa inicial encontrado no código. A classificação indica o maior
risco da operação; todas as rotas `/api/*` passam pelo gate de autenticação
existente, mas ainda precisam receber autorização contextual por papel.

| Área | Tela/capacidade | Endpoints principais | Operações de maior risco |
| --- | --- | --- | --- |
| Usuários e Sistema | Profiles | `/api/profiles`, `/api/profiles/{name}`, `/api/profiles/active` | Criar, renomear, ativar, editar e excluir profile |
| Usuários e Sistema | Pairing/canais autorizados | `/api/pairing`, `/api/pairing/approve`, `/api/pairing/revoke` | Autorizar ou revogar usuário de canal |
| Usuários e Sistema | Sessões e histórico | `/api/sessions/*`, `/api/profiles/sessions` | Ler dados de conversa, exportar, excluir e fazer purge |
| Usuários e Sistema | Logs e diagnóstico | `/api/logs`, `/api/ops/dump`, `/api/ops/debug-share` | Expor dados operacionais ou compartilhar diagnóstico |
| Infraestrutura | System/gateway | `/api/status`, `/api/system/stats`, `/api/gateway/start`, `/api/gateway/stop`, `/api/gateway/restart` | Parar/reiniciar serviços e alterar disponibilidade |
| Infraestrutura | Env/credenciais | `/api/env`, `/api/env/reveal`, `/api/credentials/pool` | Gravar, revelar, remover ou trocar credenciais |
| Infraestrutura | Backup/import/update | `/api/ops/backup`, `/api/ops/import*`, `/api/hermes/update` | Importar dados, atualizar runtime e restaurar estado |
| Infraestrutura | Canais/webhooks/cron | `/api/messaging/*`, `/api/webhooks/*`, `/api/cron/*` | Enviar comunicação, ativar integração e disparar jobs |
| Arquitetura | Configuração/modelos | `/api/config*`, `/api/model/*`, `/api/model/moa` | Alterar comportamento global, provider ou modelo |
| Arquitetura | Skills/toolsets | `/api/skills/*`, `/api/tools/toolsets/*` | Instalar conteúdo executável e habilitar ferramentas |
| Arquitetura | MCP/plugins | `/api/mcp/*`, `/api/dashboard/agent-plugins/*` | Instalar código/extensões e conceder acesso a serviços |
| Arquitetura | Hooks/computer use | `/api/ops/hooks*`, `/api/tools/computer-use/*` | Registrar comandos e conceder capacidade de automação |

### Próxima coleta necessária

Para fechar a fase 1, cada linha deve receber os campos abaixo, validados pelo
responsável do negócio:

```text
tela → endpoint → método → dado acessado → ambiente → risco → papel permitido
→ aprovação necessária → evidência gerada → rollback
```

O mapa acima é uma baseline de engenharia, não uma autorização. A existência
de uma rota ou de um botão no dashboard nunca deve ser interpretada como
permissão para qualquer usuário autenticado.

## Matriz operacional v0.1

Esta matriz é a primeira proposta de autorização. Os scopes são nomes de
trabalho e devem ser confirmados antes da implementação.

| Operação | Método/endpoint | Risco | Scope proposto | Evidência mínima |
| --- | --- | --- | --- | --- |
| Consultar status e métricas | `GET /api/status`, `GET /api/system/stats` | Baixo | `system.read` | ator, profile, timestamp |
| Consultar configuração | `GET /api/config`, `GET /api/config/raw` | Médio | `config.read` | ator, profile, escopo |
| Alterar configuração | `PUT /api/config`, `PUT /api/config/raw` | Alto | `config.write` | diff sanitizado, ator, profile |
| Consultar credenciais | `GET /api/env`, `GET /api/credentials/pool` | Alto | `credentials.read` | ator, chave mascarada |
| Revelar/remover credencial | `POST /api/env/reveal`, `DELETE /api/env`, `DELETE /api/credentials/pool/{provider}/{index}` | Crítico | `credentials.manage` | aprovação, ator, alvo, resultado |
| Gerenciar profiles | `POST/PATCH/DELETE /api/profiles*` | Alto | `profiles.manage` | mudança antes/depois, ator |
| Gerenciar sessão/dados | `DELETE /api/sessions/{session_id}`, `POST /api/sessions/bulk-delete`, `POST /api/sessions/prune` | Alto | `sessions.delete` | alvo, quantidade, confirmação |
| Operar gateway | `POST /api/gateway/start`, `/stop`, `/restart` | Alto | `gateway.operate` | ambiente, motivo, resultado |
| Gerenciar canais e webhooks | `PUT /api/messaging/platforms/{id}`, `POST/DELETE/PUT /api/webhooks*` | Alto | `integrations.manage` | integração, destino, resultado |
| Executar automações | `POST /api/cron/*`, `POST /api/ops/hooks` | Alto | `automation.manage` | job/hook, comando sanitizado, ator |
| Gerenciar MCPs/plugins/skills | `POST/DELETE/PUT /api/mcp*`, `/api/dashboard/agent-plugins*`, `/api/skills*` | Crítico | `extensions.manage` | origem, versão, scan, aprovação |
| Backup/import/update | `POST /api/ops/backup`, `/api/ops/import*`, `/api/hermes/update` | Crítico | `system.maintain` | versão, backup, resultado, rollback |

### Observação de autorização

O método HTTP e a autenticação atual não são suficientes para definir o risco.
Por exemplo, `PUT /api/config` pode alterar apenas uma preferência ou pode
modificar a configuração de produção. A autorização futura precisa considerar
ator, organização/workspace, profile, ambiente, recurso e estado da operação.

## Classificação de risco v0.1

### Nível 1 — leitura controlada

Inclui status, métricas, catálogos e configuração não sensível. Pode ser
executado automaticamente em ambiente autorizado, desde que a resposta não
exponha segredos, dados pessoais ou conteúdo de outro workspace.

Exemplos: `GET /api/status`, `GET /api/system/stats`, catálogos de modelos e
listagem de extensões.

Controle mínimo: `*.read`, escopo de organização/profile e log de acesso.

### Nível 2 — escrita reversível

Inclui alterações que podem ser revertidas sem perda relevante, como ajustes
de preferência, habilitar/desabilitar uma integração ou editar uma descrição.

Exemplos: alterações limitadas em configuração, tema, fonte e metadados de
profile.

Controle mínimo: `*.write`, diff ou antes/depois, teste em homologação e
confirmação contextual quando houver impacto operacional.

### Nível 3 — dados internos ou execução operacional

Inclui leitura de sessões, logs, credenciais mascaradas, dados de clientes,
restart de gateway, jobs, canais e webhooks. O risco depende do workspace e do
ambiente, mesmo quando a operação parece tecnicamente reversível.

Controle mínimo: papel explícito, escopo por organização/profile, auditoria
sanitizada, limite de ambiente e aprovação do responsável pelo dado ou serviço.

### Nível 4 — produção ou ação externa

Inclui revelar/remover credenciais, apagar dados, importar backup, instalar
extensões executáveis, enviar comunicação, conceder permissões, atualizar
runtime ou alterar produção.

Controle mínimo: aprovação server-side específica para o alvo, credencial
separada, backup/rollback, janela de mudança, monitoramento e evidência de
resultado. Uma aprovação para planejar não aprova automaticamente o deploy ou
a ação externa.

## Regra de escalonamento

Se uma operação puder assumir mais de um nível, aplicar o nível mais alto. A
classificação deve considerar o dado e o ambiente reais, não apenas o método
HTTP. Um endpoint de leitura de produção com dados de cliente pode ser Nível 3
ou 4, enquanto uma alteração local de tema pode ser Nível 2.

## Priorização inicial de endpoints críticos

| Prioridade | Endpoint | Nível | Motivo | Controle a implementar primeiro |
| --- | --- | --- | --- | --- |
| P0 | `POST /api/env/reveal` | 4 | Revela segredo | `credentials.reveal` + aprovação server-side + auditoria |
| P0 | `PUT /api/env`, `DELETE /api/env` | 4 | Cria/remove credencial | `credentials.manage` + ambiente + rotação/rollback |
| P0 | `POST /api/ops/import*` | 4 | Pode sobrescrever estado | `system.restore` + backup + aprovação |
| P0 | `POST /api/hermes/update` | 4 | Altera runtime | `system.update` + janela + rollback |
| P0 | `POST /api/mcp/catalog/install`, `POST /api/mcp/servers` | 4 | Instala código ou integração | `extensions.install` + scan + aprovação |
| P0 | `POST /api/dashboard/agent-plugins/install` | 4 | Instala plugin executável | `extensions.install` + origem/versão + aprovação |
| P0 | `POST /api/skills/hub/install`, `PUT /api/skills/content` | 4 | Instala/edita instrução executável | `skills.manage` + scan + revisão |
| P0 | `POST /api/ops/hooks` | 4 | Registra comando executável | `hooks.manage` + aprovação + comando sanitizado |
| P1 | `POST /api/pairing/approve`, `POST /api/pairing/revoke` | 3 | Concede/revoga acesso de canal | `channel.access.manage` + ator + alvo |
| P1 | `POST /api/messaging/telegram/onboarding/apply` | 4 | Grava credenciais e altera canal | `integrations.manage` + aprovação |
| P1 | `PUT /api/messaging/platforms/{platform_id}` | 3/4 | Altera integração externa | `integrations.manage` + ambiente + destino |
| P1 | `POST/DELETE/PUT /api/webhooks*` | 4 | Cria ou ativa chamadas externas | `integrations.manage` + allowlist de destino |
| P1 | `POST /api/cron/*` | 3/4 | Agenda/dispara automação | `automation.manage` + revisão do comando |
| P1 | `POST /api/gateway/start`, `/stop`, `/restart` | 3 | Afeta disponibilidade | `gateway.operate` + ambiente + motivo |
| P1 | `DELETE /api/sessions/{id}`, `/bulk-delete`, `/prune` | 3 | Remove histórico | `sessions.delete` + escopo + confirmação server-side |
| P1 | `POST /api/profiles`, `PATCH/DELETE /api/profiles/{name}` | 3 | Altera isolamento/configuração | `profiles.manage` + proteção do profile ativo |
| P1 | `PUT /api/config`, `PUT /api/config/raw` | 3/4 | Pode alterar comportamento de produção | `config.write` + diff + ambiente |
| P1 | `POST /api/tools/computer-use/permissions/grant` | 4 | Concede automação de computador | `computer_use.grant` + aprovação explícita |

Os endpoints P0 devem ser protegidos antes de habilitar o dashboard para uso
multiusuário ou exposição com dados reais. Os endpoints P1 podem seguir em uma
segunda onda, mas não devem ser considerados seguros apenas porque já exigem
login.

## Matriz inicial de papéis e permissões

Esta matriz é uma proposta mínima para validação. Login não concede nenhum
scope administrativo por padrão.

| Papel | Pode fazer | Não pode fazer por padrão |
| --- | --- | --- |
| **Auditor** | `system.read`, `config.read`, `sessions.read`, `audit.read`, `extensions.read` | Qualquer escrita, revelar credenciais, exportar dados restritos ou operar produção |
| **Analista** | Auditor + `analytics.read`, `models.read`, `profiles.read`, `sessions.export` autorizado | Credenciais, integrações, extensões, exclusões e automações |
| **Operador** | Analista + `gateway.operate`, `automation.manage`, `integrations.manage`, escritas reversíveis em homologação | Produção, credenciais, instalação de extensões e exclusões sem aprovação |
| **Administrador** | Operador + `config.write`, `profiles.manage`, `credentials.manage`, `extensions.manage`, `system.maintain` | Ações de Nível 4 sem aprovação específica |
| **Responsável de produção** | `production.approve`, `production.deploy`, `production.rollback` | Acesso automático a credenciais ou dados fora do escopo aprovado |
| **Serviço/integração** | Somente scopes técnicos listados, por rota e ambiente | Acesso amplo ao dashboard ou scopes não declarados |

### Scopes reservados

Os scopes abaixo não devem ser incluídos em papéis comuns:

```text
credentials.reveal
credentials.manage
extensions.install
hooks.manage
system.restore
system.update
production.deploy
production.rollback
computer_use.grant
channel.access.manage
```

Cada scope precisa ser avaliado junto com `organization_id`, `workspace_id`,
`profile`, `environment` e recurso-alvo. Um operador de homologação não deve
ganhar acesso à produção.

### Ordem de implementação

1. Extrair o principal autenticado da sessão ou token.
2. Resolver organização/workspace, profile e ambiente do recurso.
3. Verificar o scope necessário no backend.
4. Para Nível 4, exigir aprovação específica e não reutilizável.
5. Registrar a decisão permitida ou negada sem dados sensíveis.

Até a validação pelo negócio, esta matriz é uma proposta de design e não uma
autorização já implementada.

## RBAC inicial baseado em Usuários e permissões

O dashboard legado já possui uma autorização parcial na fonte canônica
`/home/hermes/.hermes/dashboard/`: `role` controla administração, `modules`
controla abas/capacidades, `dm_accounts` limita contas de comunicação e
`allowed_operators` permite delegação operacional no Flow KGC. A proposta
abaixo preserva esse comportamento e o traduz para os papéis novos.

### Mapeamento de papéis existente → papel inicial

| Usuário/fonte atual | Estado atual | Papel RBAC inicial | Escopo |
| --- | --- | --- | --- |
| André Santos | `role=admin`, sem restrição de módulos | Administrador | Plataforma Koncepto; todos os módulos; aprovação de Nível 4 ainda obrigatória |
| Thiago Trindade | `role=member` | Operador | Inteligência, Vendas, Módulo MKT e Ferramentas |
| Jefferson Frasnelli | `role=member` | Operador | Inteligência, Outreach, Vendas, Módulo MKT e Ferramentas |
| Renato Trindade | `role=member` | Operador | Inteligência, Outreach, Vendas, Módulo MKT e Ferramentas; delegações explícitas de operadores |
| Tami Roger | `role=member` | Operador | Inteligência, Outreach, Módulo MKT e Ferramentas |
| Jean Lima | `role=member` | Operador | Inteligência, Outreach, Módulo MKT e Ferramentas |
| Canal Data Dias | `role=member` | Operador | Inteligência, Outreach e Ferramentas |

Nenhum usuário `member` recebe acesso à configuração administrativa por padrão.
No código atual, a aba `config` e a gestão de usuários permanecem exclusivas do
admin da plataforma, o que deve ser preservado durante a migração.

### Conversão de módulos em scopes

| Módulo legado | Scopes iniciais |
| --- | --- |
| `inteligencia` | `signal.read`, `analytics.read` |
| `outreach` | `outreach.read`, `outreach.operate` dentro do operador autorizado |
| `vendas` | `sales.read`, `sales.operate` |
| `modulo_mkt` | `marketing.read`, `marketing.operate` |
| `ferramentas` | `tools.read`, `tools.operate` |
| `config` | `config.read` para leitura autorizada; `config.write` somente Administrador |

O campo `dm_accounts` deve virar uma restrição de recurso, não um scope: o
usuário pode operar somente as contas listadas. Valor nulo, que hoje significa
acesso total, deve ser reservado ao Administrador ou explicitamente aprovado.

### Compatibilidade e migração

1. `admin` → Administrador.
2. `member` → Operador limitado aos módulos e recursos existentes.
3. `mkt` legado → Analista de Marketing, limitado a `modulo_mkt`; nenhum usuário
   atual usa esse papel na fonte consultada.
4. `modules` vazio ou ausente não deve ampliar acesso de um não-admin.
5. `allowed_operators` permanece uma delegação explícita e não promove o
   usuário a Administrador.
6. Toda rota nova deve validar módulo, scope, recurso e ambiente no backend.

Este é o RBAC inicial mais compatível com o que já está em produção. A próxima
etapa técnica é criar testes de paridade: cada usuário atual deve conservar seu
acesso permitido e perder qualquer acesso fora de seus módulos/recursos.

## Separação de ambientes — fase 5

### Achado atual

O dashboard canônico (`/home/hermes/.hermes/dashboard/app.py`) não possui hoje
um identificador explícito de ambiente nem uma configuração versionada que
separe desenvolvimento, homologação e produção. Há referências diretas a
serviços externos e ao callback OAuth de produção. Login e RBAC não devem ser
tratados como substitutos de isolamento de ambiente.

### Contrato obrigatório para implantação

Cada deployment deve possuir identidade própria e não reutilizar secrets,
bancos ou contas operacionais de outro ambiente:

| Ambiente | Dados | Integrações externas | Operações permitidas |
| --- | --- | --- | --- |
| Desenvolvimento | Banco/projeto de desenvolvimento | Contas de teste ou mocks | Testes locais; sem envio real |
| Homologação | Banco/projeto de homologação | Contas sandbox dedicadas | Validação controlada; aprovação explícita |
| Produção | Banco/projeto de produção | Contas produtivas | Operações reais conforme RBAC |

Requisitos mínimos antes de promover código:

1. O deployment declara explicitamente `development`, `staging` ou
   `production`; ausência ou valor desconhecido deve impedir a inicialização.
2. URL, chave e projeto de banco são distintos por ambiente.
3. Chaves Unipile, Apollo, HubSpot, e-mail, OAuth e webhooks são distintas por
   ambiente; nenhum secret de produção entra em desenvolvimento/homologação.
4. Homologação bloqueia envio real, criação de campanha produtiva e operações
   irreversíveis por padrão.
5. OAuth e webhooks usam callback e segredo próprios por ambiente.
6. O ambiente atual aparece no healthcheck, logs sanitizados e tela de
   Infraestrutura, sem expor secrets.
7. A promoção para produção registra versão, responsável, aprovação e plano
   de rollback.

### Gate de implementação

Não aplicar bloqueios por inferência de hostname, branch ou modo debug. A
próxima alteração deve introduzir uma configuração explícita de ambiente e
validá-la no startup; depois, cada integração crítica deve consultar essa
configuração para impedir mistura de recursos entre ambientes. A infraestrutura
de deployment precisa fornecer os três conjuntos de secrets antes dessa
alteração ser ativada no dashboard canônico.

## Capacidade do host atual — avaliação inicial

Diagnóstico read-only realizado em 2026-09-12 no host `srv1581367`:

| Recurso | Observado | Avaliação para 3 ambientes |
| --- | --- | --- |
| CPU | 2 vCPU | Insuficiente para três ambientes completos com folga operacional |
| Memória | 7,8 GiB; 3,5 GiB disponíveis | Insuficiente se cada ambiente mantiver app, workers e serviços próprios |
| Swap | 4 GiB, 2,5 GiB usados | Sinal de pressão de memória; não deve ser usado como capacidade planejada |
| Disco raiz | 96 GiB; 45 GiB livres (55% usado) | Código cabe, mas dados, backups e logs de 3 ambientes reduzem rapidamente a margem |
| Inodes | 8% usados | Sem risco imediato |
| Rede | `eth0` ativa, 0 erros e 0 descartes observados | Interface saudável; banda contratada, latência e limites do provedor ainda não medidos |

O host já executa o dashboard, daemon do Flow KGC, PostgreSQL, PostgREST,
bridge e outros serviços. O dashboard Gunicorn está configurado com um worker e
o processo observado usa aproximadamente 340 MiB residentes; isso não inclui o
custo total de banco, integrações e caches por ambiente.

### Decisão

Não promover três ambientes completos para este mesmo host neste momento. A
capacidade é adequada para manter produção atual e talvez um ambiente de
desenvolvimento leve, mas não para desenvolvimento + homologação + produção
isolados com margem para picos, backups e rollback.

Sizing inicial recomendado para um host compartilhado, sujeito a teste de carga:
4–6 vCPU, 16 GiB de RAM, 120 GiB ou mais de disco SSD com política de retenção
de logs/backups. A opção preferencial é separar produção de desenvolvimento e
homologação, ou usar banco gerenciado/projetos separados, reduzindo o risco de
contenção e de mistura de dados.

Antes da implantação, medir: limite de banda do provedor, latência para
Supabase/Unipile/Apollo, IOPS e throughput de disco, pico de memória/CPU por
ambiente e tamanho/retensão real de banco, logs e backups.

## Aprovação de ações críticas — fase 7

O Flow KGC já mantém envios reais em `waiting_approval` e usa claim atômico
antes do disparo, evitando que duas sessões enviem a mesma aprovação. A fase 7
formaliza esse controle:

- aprovar uma entrada é uma decisão explícita e auditável;
- enviar uma resposta só pode reivindicar uma entrada ainda aguardando
  aprovação;
- aprovação em lote exige lista explícita de entradas selecionadas;
- a aprovação preserva o rascunho persistido; o conteúdo não é alterado nem
  copiado para o audit log;
- aprovação, envio individual e envio em lote geram eventos sanitizados nos
  escopos `critical:flow-kgc.approve`, `critical:flow-kgc.send` e
  `critical:flow-kgc.bulk_send`.

O próximo endurecimento, após validar o fluxo com o negócio, é separar
“responsável por preparar” de “responsável por aprovar” para operações Nível 4
e exigir confirmação adicional quando o destino for produção.

## Backup, monitoramento e rollback — fase 8

### Estado verificado

No host atual, o script `/home/hermes/.hermes/scripts/pg_backup.sh` está
registrado no scheduler como `pg-backup-koncepto-funil`, diário às 03:00 BRT,
com retenção local de diários, semanais e mensais. O dump diário mais recente
verificado foi `koncepto_funil_20260911.dump`; `pg_restore --list` terminou com
sucesso e listou 316 entradas, sem executar restauração.

Os serviços `koncepto-dashboard`, `hermes-dashboard` e `flow-kgc-daemon` foram
observados ativos. A interface do dashboard respondeu localmente e o bridge
WhatsApp respondeu ao healthcheck. O backup local ocupa aproximadamente 1,9 GiB
e os logs aproximadamente 1,2 GiB; o `flow_kgc_audit.jsonl` sozinho está acima
de 500 MiB. Já existe rotação própria em
`/home/hermes/.hermes/scripts/log_rotation.sh`, executada pelo job
`log-rotation` aos domingos às 03:00, com corte de 50 MiB, compressão e até 5
arquivos por log, além de vacuum do journal até 200 MiB. O `logrotate` do
sistema também está ativo para nginx, PostgreSQL, journald e serviços do SO.

### Lacunas que permanecem

- Ainda não foi realizado um restore completo em área isolada.
- O monitoramento e os alertas operacionais já existem: `infra-audit-daily`
  verifica infraestrutura a cada 5 minutos e `flow-kgc-monitor` verifica o
  Flow KGC no mesmo intervalo, com alertas imediatos/repetidos conforme o job.
- Para backup, foi adicionado o watchdog
  `/home/hermes/.hermes/scripts/pg_backup_watchdog.sh`, agendado no scheduler
  como `pg-backup-watchdog` a cada hora no minuto 15. Ele considera crítico um
  dump diário ausente ou com mais de 30 horas, confere também o último status do
  job principal e envia alerta pelo `WA_SECURITY_ALERT_CHAT` já configurado.
  O estado é deduplicado em `~/.hermes/run/pg_backup_watchdog.state` e há alerta
  de recuperação quando o backup volta a ficar saudável.
- O rollback de aplicação e banco ainda não foi ensaiado com critério de
  sucesso/abortamento.
- A cópia externa precisa de verificação periódica de existência e restauração,
  não apenas de tentativa de upload.

### Runbook mínimo

1. Antes da mudança: registrar versão, hash, responsável e backup verificado.
2. Durante a mudança: acompanhar healthcheck, erro HTTP, CPU, memória, swap,
   disco, fila e latência das integrações.
3. Critério de abortamento: erro persistente, crescimento anormal de fila,
   indisponibilidade de integração ou pressão de memória/disco acima do limite
   operacional definido.
4. Rollback de aplicação: retornar para a última versão aprovada e reiniciar
   somente o serviço afetado.
5. Rollback de dados: restaurar o dump em instância isolada, validar contagens e
   integridade, e só então executar a troca controlada.
6. Pós-mudança: registrar resultado, incidentes, evidência e janela de retenção.

O próximo trabalho operacional é fazer um restore de ensaio sem tocar na
produção, acompanhar o primeiro ciclo do watchdog e definir RPO/RTO com o
negócio.

## Checklist de revisão periódica — fase 9

### Diário

- [ ] Dashboard, daemon e integrações críticas respondem ao healthcheck.
- [ ] Não há erro persistente, fila travada ou crescimento anormal de retry.
- [ ] Backup previsto foi concluído e o tamanho está dentro da variação esperada.
- [ ] Não há pressão anormal de memória, swap, CPU, disco ou inodes.
- [ ] Eventos `deny` e ações críticas recentes foram revisados para anomalias.

### Semanal

- [ ] Revisar usuários ativos, papel, módulos, `dm_accounts` e delegações.
- [ ] Remover acessos temporários e delegações vencidas.
- [ ] Conferir serviços, portas expostas, certificados e alterações de configuração.
- [ ] Verificar cópia externa do backup e o resultado do job de backup.
- [ ] Revisar crescimento e rotação de logs.
- [ ] Confirmar que dev/homologação não apontam para recursos produtivos.

### Mensal

- [ ] Revalidar a matriz RBAC com os responsáveis de negócio.
- [ ] Revisar endpoints novos ou alterados contra o inventário de autorização.
- [ ] Executar restore de ensaio em área isolada e registrar RPO/RTO observado.
- [ ] Testar rollback da aplicação com a última versão aprovada.
- [ ] Revisar secrets, validade, rotação e correspondência por ambiente sem
  expor os valores.
- [ ] Revisar integrações, plugins, skills, MCPs e permissões concedidas.

### Trimestral ou após incidente

- [ ] Realizar revisão de acesso com cada gestor, incluindo desligamentos e
  mudança de função.
- [ ] Fazer exercício de incidente: contenção, preservação de evidência,
  comunicação e recuperação.
- [ ] Reavaliar sizing de CPU, memória, disco, rede, logs e backups.
- [ ] Atualizar os critérios de risco, aprovação e rollback.

### Evidência mínima

Cada revisão deve registrar data, ambiente, responsável, versão, resultado,
itens pendentes, prazo e link para evidências sanitizadas. Falha de backup,
ausência de responsável, acesso sem justificativa, mistura de ambientes ou
impossibilidade de rollback deve bloquear a promoção seguinte até tratamento
ou aceite formal de risco.
