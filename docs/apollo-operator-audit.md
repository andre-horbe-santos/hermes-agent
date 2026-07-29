# Auditoria do `apollo-operator`

Data: 2026-07-29

Repositório analisado: <https://github.com/jimmy-creatop/apollo-operator>

## Conclusão de segurança

No snapshot/tag `v1.2.0` auditado não foram encontrados indícios de malware.
O projeto contém somente skills e referências em Markdown, sem código executável,
dependências, instaladores ou rotinas aparentes de exfiltração.

O risco é operacional: as instruções podem orientar ações reais no Apollo, como
enriquecimento pago, matrícula em sequências, ativação de campanhas, remoção de
contatos e provisionamento de mailboxes.

## Reaproveitar no stack Koncepto

- Construção de ICP com amostras aprovadas manualmente.
- Separação entre filtros rígidos, sinais e pontuação.
- Deduplicação e scorecard de qualidade de listas.
- Filtrar antes de enriquecer, reduzindo consumo de créditos.
- Verificação de e-mails, catch-all e contatos duplicados.
- Aprovação humana antes de qualquer ação externa.
- Kill switch, confirmação de custo e registro do resultado.

Esses princípios são compatíveis com o uso atual do Apollo no Flow KGC:
`people/match`, `bulk_match`, enriquecimento de organizações e staging para
curadoria antes da promoção.

## Não importar diretamente

- Skills de go-live, sequências, multicanal e infraestrutura de envio.
- Instruções que ativem campanhas, enviem e-mails ou comprem mailboxes.
- Receitas de CLI/curl que possam contornar o controle central de créditos.
- Custos e limites fixos sem validação do plano Apollo vigente.

O repositório não deve ser instalado integralmente como skill global. Caso seja
reutilizado, deve ser criada uma versão interna sanitizada, limitada a ICP,
qualidade, deduplicação e enriquecimento.

## Ponto de atenção local

O `scripts/apollo_credit_guard.py` atualmente opera em modo fail-open: se o
arquivo de controle estiver ausente ou inválido, chamadas Apollo são permitidas.
Para operações pagas, avaliar a mudança para fail-closed em uma alteração futura.

Nenhuma alteração de código foi feita nesta auditoria.
