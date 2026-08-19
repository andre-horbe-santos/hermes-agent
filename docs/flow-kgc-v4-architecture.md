# Flow KGC v4 — arquitetura incremental

Status: proposta implementável  
Data: 2026-08-19

## Objetivo

O v4 deve permitir evoluir jornadas, prompts e políticas comerciais sem copiar
árvores inteiras de steps nem aumentar o acoplamento de `runner.py`. A migração
precisa preservar os flows ativos, os registros já persistidos e os controles
humanos existentes.

O primeiro vertical slice será Apollo A/B (`kgc_ii_ln_v2` e
`kgc_ii_ln_v3`), porque ambos compartilham a mesma jornada e diferem por
políticas de conversa. A regra corrigida em 2026-08-19 é um contrato do v4:

- convite enviado pelo próprio flow e depois aceito usa a DM pós-aceite;
- conexão que já existia antes do flow usa a DM de reativação;
- `ja_conectado_ln` sozinho não distingue esses dois fatos;
- `convite_aceito_flow` só pode existir quando há evidência persistida de
  `ln_invite_sent`.

## Princípios

1. **Migração por compilação, não por rewrite.** A definição v4 compila para o
   formato de steps que o runner atual já executa. O motor legado continua sendo
   o caminho de produção até a equivalência ser comprovada.
2. **Versão imutável por entrada.** Uma entrada guarda a revisão resolvida da
   definição quando é ativada. Alterar uma campanha não muda retroativamente
   leads em andamento.
3. **Fatos não são tags ambíguas.** Eventos observados, estado derivado e labels
   comerciais têm namespaces distintos.
4. **Política é dado testável.** Prompt, evidência permitida, maturidade,
   autoenvio, aprovação e limites de canal ficam fora da topologia da jornada.
5. **Efeitos são idempotentes.** Todo envio ou convite possui chave de operação;
   reprocessar um step não pode duplicar uma ação externa.
6. **Humano mantém autoridade.** Aprovação, pausa, descarte, troca de operador e
   revisão manual continuam sendo gates explícitos, não exceções no dispatcher.

## Modelo em quatro camadas

```text
CampaignSpec
  ├─ JourneySpec       topologia e transições
  ├─ PolicyBundle      conteúdo, evidência, aprovação e cadência
  ├─ RuntimeFacts      eventos observados e estado derivado
  └─ EffectAdapter     Unipile/LLM/DB, com idempotência
          │
          ▼
   LegacyStepCompiler  → FLOWS compatível com runner.py
```

### `CampaignSpec`

Identifica a campanha sem incorporar detalhes do executor:

```python
CampaignSpec(
    id="apollo_linkedin",
    revision="4.0.0",
    journey="linkedin_invite_then_conversation",
    policy="apollo_discovery",
    variant="A",
)
```

`variant` seleciona diferenças realmente experimentais. Não deve duplicar a
jornada. Toda entrada persiste `campaign_id`, `campaign_revision` e `variant`.

### `JourneySpec`

É um grafo pequeno de estados nomeados e transições declarativas. Estados têm
IDs estáveis; índices de lista são apenas detalhe do compilador.

Exemplo de núcleo Apollo:

```text
research → check_connection
  ├─ preexisting_connection → first_dm(reactivation)
  └─ not_connected → invite → wait_accept
                         ├─ accepted → first_dm(post_accept)
                         └─ timeout  → no_accept
first_dm → wait_reply → followup_or_handoff
```

Uma condição lê somente `RuntimeFacts`. Ela não chama rede, não grava banco e
não interpreta texto livre.

### `PolicyBundle`

Agrupa políticas ortogonais:

- `content`: templates e objetivos por intenção (`post_accept`,
  `reactivation`, `followup`), sem depender do índice do step;
- `evidence`: campos autorizados e alegações proibidas;
- `conversation`: classificação de maturidade e objetivo de descoberta;
- `approval`: quando exige revisão humana e quando autoenvio é permitido;
- `cadence`: janelas, atrasos, timeout e limites por operador/canal;
- `outcome`: tags comerciais e handoff resultantes.

Apollo A/B deve compartilhar `JourneySpec` e a política base. A variante contém
somente os campos que o experimento altera e é aplicada como overlay validado.

### `RuntimeFacts`

O v4 separa três categorias hoje misturadas em `tags`:

```python
observed = {
    "linkedin.connection.preexisting": True,
    "linkedin.invite.sent": False,
    "linkedin.invite.accepted": False,
}
derived = {
    "conversation.entry_mode": "reactivation",
}
labels = ["apollo_interest"]
```

`conversation.entry_mode` só admite:

- `post_accept`: `invite.sent` e `invite.accepted` pertencem à execução atual;
- `reactivation`: a conexão preexistia e não há convite enviado nesta execução.

Durante a compatibilidade, o adapter traduz os marcadores legados:

| Legado | Fato v4 |
|---|---|
| registro `_type=ln_invite_sent` | `linkedin.invite.sent=true` |
| `ja_conectado_ln` + convite enviado | `linkedin.invite.accepted=true` |
| `ja_conectado_ln` sem convite enviado | `linkedin.connection.preexisting=true` |
| `convite_aceito_flow` | confirmação derivada, nunca fonte única |

### `EffectAdapter`

O executor resolve uma intenção em um efeito. A chave idempotente mínima é
`entry_id + state_id + attempt_kind`. O registro da intenção ocorre antes da
chamada externa; resposta e identificador remoto são anexados depois.

Interfaces iniciais:

```python
class Effects(Protocol):
    def send_invite(self, command: InviteCommand) -> EffectResult: ...
    def send_message(self, command: MessageCommand) -> EffectResult: ...
    def generate_draft(self, command: DraftCommand) -> DraftResult: ...
```

Falha indeterminada após uma chamada externa deve ir para reconciliação/manual,
não para retry cego.

## Persistência e compatibilidade

Nenhuma coluna existente é removida na primeira fase. Os campos v4 podem entrar
como colunas nullable ou em um envelope JSON versionado:

- `campaign_id`, `campaign_revision`, `campaign_variant`;
- `state_id` (em paralelo a `current_step`);
- `runtime_facts`;
- `definition_snapshot` ou hash + registro imutável da revisão;
- `effect_journal` com chave idempotente, estado e remote ID.

O compilador produz `steps`, `branch_if_connected`, prompts e delays legados.
Um `LegacyFactsAdapter` projeta mensagens/tags atuais em `RuntimeFacts`. Isso
permite executar uma campanha v4 no runner atual antes de extrair o executor.

## Validação da definição

Antes de uma campanha ser registrável, o validator deve rejeitar:

- estado inicial ou destino inexistente;
- estado inalcançável;
- transição sem fallback quando as condições não são exaustivas;
- loop sem limite explícito;
- intenção de conteúdo sem política correspondente;
- variante que tente alterar topologia fora da allowlist;
- revisão já publicada com conteúdo diferente;
- step com efeito externo sem chave idempotente.

Testes devem afirmar invariantes e equivalência comportamental, não snapshots de
todo o dicionário compilado.

## Plano de entrega

### Fase 0 — contratos Apollo A/B (concluída)

- distinguir conexão preexistente de aceite do convite do flow;
- compartilhar a política estrita de reativação entre A/B;
- cobrir ambos os caminhos com import real do código operacional.

### Fase 1 — modelo puro e compilador

- criar pacote `flow_kgc_v4` sem I/O;
- implementar `CampaignSpec`, `JourneySpec`, `PolicyBundle` e validator;
- compilar Apollo para o formato legado;
- comparar as transições observáveis do compilado com v2/v3 em testes de
  contrato.

Critério de saída: Apollo compilado alcança os mesmos estados, gates humanos e
efeitos que os flows atuais para conexão preexistente, aceite, timeout e reply.

### Fase 2 — fatos e journal de efeitos

- introduzir `LegacyFactsAdapter`;
- persistir revisão, `state_id` e fatos sem remover campos legados;
- adicionar journal idempotente para convite e DM;
- executar em shadow mode, sem novos efeitos externos.

Critério de saída: decisão v4 e decisão legada coincidem em entradas reais
amostradas; divergências são auditadas.

### Fase 3 — executor por handlers

- extrair handlers de convite, mensagem, espera e branching do god-file;
- manter `runner.advance()` como fachada durante a migração;
- habilitar Apollo v4 por campanha/revisão em configuração persistida;
- rollback troca a revisão ativa; entradas em andamento mantêm seu snapshot.

### Fase 4 — generalização

- migrar os demais ICPs por política, não por cópia de árvore;
- remover derivações v2/v3 somente quando não houver entradas ativas nelas;
- remover adapters legados depois da janela de rollback.

## Fora de escopo inicial

- novo model tool no core Hermes;
- DSL configurável pelo usuário no dashboard;
- editor visual de jornadas;
- event sourcing completo do banco;
- mudança simultânea de todos os ICPs;
- substituição do Unipile ou do provedor de LLM.

## Primeira unidade de código

A primeira implementação deve ser pequena e reversível:

1. pacote puro `flow_kgc_v4/spec.py`;
2. `validator.py` com testes de grafo e revisão;
3. `apollo.py` declarando uma única jornada e overlays A/B;
4. `legacy_compiler.py` que emite o contrato consumido por `FLOWS`;
5. testes de decisão para `post_accept` versus `reactivation`.

Ela não altera o dispatcher nem envia mensagens. Só depois da equivalência
essa definição deve ser conectada ao runtime operacional.
