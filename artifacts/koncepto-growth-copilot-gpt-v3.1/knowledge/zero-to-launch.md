# Implantação guiada: do zero ao piloto

Este é o fluxo principal para uma conta nova. Não avance silenciosamente. Cada fase termina com resumo, artefato, pendências e aprovação.

## Fase 0 — Acesso e governança

Confirme workspace Apollo, plano e permissões; conector MCP; usuários e responsáveis; caixas/domínios disponíveis; CRM e fonte oficial; mercado e restrições legais; quem aprova estratégia, copy e lançamento.

Entregável: mapa de acessos, responsáveis e limitações das ferramentas. Não faça escrita.

## Fase 1 — Estratégia comercial

Conduza uma entrevista guiada sobre meta, período, oferta, problema, diferenciais, provas, ticket, ciclo, geografia, setores, porte, tecnologias, gatilhos, exclusões e capacidade humana. Para cada resposta, separe fato, hipótese e lacuna.

Construa nesta ordem:

1. meta e Deal Flow reverso, com cenários;
2. TAM/SAM/SOM e critérios de conta;
3. ICP primário/secundário e anti-ICP;
4. personas e comitê de compra;
5. problemas/impactos por persona e perguntas SPICED;
6. hipótese de mensagem e critérios de sucesso do piloto.

Entregável: documento estratégico aprovado e matriz segmento × persona. Ainda não crie listas ou sequências.

## Fase 2 — Prontidão técnica e entregabilidade

Para cada domínio e caixa, registre responsável, idade, provedor e uso atual. Verifique:

- SPF publicado e sem múltiplos registros conflitantes;
- DKIM habilitado pelo provedor da caixa;
- DMARC publicado e alinhamento monitorado;
- subdomínio de rastreamento personalizado, preferencialmente um por domínio de envio;
- caixa conectada ao Apollo, assinatura, endereço e descadastro;
- limites diário/horário, intervalo, janela/fuso e ramp-up;
- status de diagnóstico, bounce e reputação.

DNS é alterado por administrador no provedor de domínio/e-mail, não pelo Claude. Apollo pode diagnosticar e fornecer os valores. Nunca invente registros DNS. Revalide após propagação e bloqueie o lançamento enquanto houver falha crítica.

Entregável: checklist verde/amarelo/vermelho por domínio/caixa e plano de correção com responsável.

## Fase 3 — Projeto das pesquisas

Traduza ICP/personas em filtros Apollo. Para cada pesquisa, defina nome padrão, objetivo, filtros, exclusões, tamanho esperado, evidência e frequência de revisão. Faça uma consulta exploratória pequena, revise falsos positivos/negativos e refine.

Convenção: `[CLIENTE] | [SEGMENTO] | [PERSONA] | [REGIÃO] | vN`.

Após aprovação, salve a pesquisa pelo MCP se a ferramenta permitir. Caso contrário, entregue os filtros e o passo a passo exato para salvar na interface. Registre URL/ID quando disponível.

Entregável: catálogo de pesquisas salvas e log de critérios.

## Fase 4 — Listas e dados

Defina listas de contas antes de listas de pessoas quando possível. Proponha estrutura mínima:

- contas ICP aprovadas;
- pessoas por segmento/persona;
- mudança de contato — indicação;
- mudança de contato — mudança observada;
- retomada agendada;
- retomada sem conexão 90+ dias;
- exclusões/supressão.

Defina campos, proprietário, estágios, deduplicação e regra de entrada/saída. Mostre contagens e amostra de até 10. Após aprovação, crie/salve pelo MCP se suportado e verifique por leitura.

Entregável: mapa de listas com IDs/URLs, contagens e qualidade.

## Fase 5 — Sequências

Leia `sequences.md` e `writing-and-calls.md`. Para cada uma das quatro sequências, conduza decisões sobre audiência, objetivo, gatilho, canais, intensidade, remetente, tom, prova, CTA, horários, tarefas manuais, SLA e paradas.

Escreva a copy somente depois dessas decisões. Mostre a sequência completa e teste merge fields. Crie inicialmente **inativa**, após conferir duplicidade de nome. Não inscreva contatos nesta fase.

Entregável: quatro contratos aprovados; sequência criada/inativa ou checklist manual; versão da copy.

## Fase 6 — QA e piloto controlado

Use no máximo 10 contatos aprovados. Verifique fit, e-mail, exclusões, proprietário, personalização, timezone, sequência correta, caixa, limites e paradas. Faça envio de teste interno quando disponível. Só inscreva/ative após aprovação explícita que nomeie sequência, contatos, caixa e volume.

Entregável: checklist de QA, lote piloto e plano de reversão.

## Fase 7 — Operação e melhoria

Monte fila diária, responsáveis e SLAs; dashboard sob demanda; ritual de revisão; métricas e denominadores. Primeiro checkpoint após volume suficiente, sem otimizar por abertura isoladamente. Respostas passam ao humano e pausam automação.

Entregável: rotina operacional, painel, baseline e próxima hipótese de teste.

## Índice de prontidão

Mostre 0–100% por blocos: Estratégia 20; Técnica 20; Pesquisas 15; Listas/dados 15; Sequências 15; QA 10; Operação 5. Um bloco crítico vermelho impede “pronto para lançar”, independentemente da soma.
