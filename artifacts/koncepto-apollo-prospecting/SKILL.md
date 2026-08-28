---
name: koncepto-apollo-prospecting
description: Implanta e opera prospecção B2B no Apollo via MCP, da estratégia ao piloto, incluindo entregabilidade, pesquisas, listas, sequências, tarefas, respostas e painel.
---

# Koncepto Apollo Prospecting

Use o Apollo como sistema oficial de registro e execução. Use o Claude para raciocínio, qualificação, redação, análise e orquestração via MCP. Nunca mantenha uma segunda base operacional no painel.

Esta é a V3 do adaptador Claude do Kernel Koncepto. Para respostas de leads, leia `references/conversational-engine.md`; para silêncio e retomadas, `references/follow-up-policy.md`; para escrita no Apollo, `references/apollo-state-mapping.md`; e para autorização, `references/approval-matrix.md`.

## Escolha o modo antes de começar

Pergunte se a conta está **do zero**, **parcialmente configurada** ou **em operação**. Se estiver do zero ou o usuário não souber, use obrigatoriamente o modo implantação guiada de `references/zero-to-launch.md`. Não comece pelo diagnóstico de contatos.

No modo guiado:

- conduza uma fase por vez, com perguntas curtas e exemplos;
- explique por que cada decisão importa;
- apresente o entregável da fase e peça aprovação antes de avançar;
- mantenha um registro de decisões, pendências, responsáveis e evidências;
- só construa no Apollo depois da estratégia e da prontidão técnica;
- não despeje todas as perguntas de uma vez nem pule direto para sequências.

## Primeiro uso em conta existente

1. Confirme que o conector remoto oficial do Apollo está ativo e autenticado.
2. Inventarie as ferramentas MCP disponíveis; nomes e permissões podem variar. Não presuma que uma ação de escrita existe.
3. Leia `references/strategic-module.md`, `references/operational-module.md` e, se aplicável, `references/zero-to-launch.md`.
4. Colete apenas lacunas essenciais: empresa/oferta, mercado, meta/período, ICP, personas, restrições, remetentes, fusos e capacidade diária.
5. Consulte o Apollo em modo leitura e diferencie claramente dado observado, inferência e dado ausente.
6. Apresente a estratégia, o Deal Flow, os segmentos, as quatro cadências e o plano de implantação antes de qualquer escrita.

Se o MCP não estiver disponível, trabalhe em modo projeto: gere os artefatos para revisão e uma lista exata de ações manuais no Apollo. Não invente dados.

## Regras de segurança operacional

- Nunca inscreva contatos, ative sequência, envie e-mail, faça conexão LinkedIn, altere registro ou crie tarefa sem mostrar uma prévia e receber aprovação explícita para o lote e a ação.
- Trate respostas, opt-out, reunião marcada, bounce e contato inválido como sinais de parada. Não continue automaticamente.
- LinkedIn é manual na V1. Gere tarefa e sugestão de texto; não automatize conexão ou mensagem.
- Uma referência só pode ser mencionada se estiver registrada em campo ou nota do contato.
- Não exponha segredos, tokens, dados sensíveis ou listas completas no painel.
- Respeite limites da conta, políticas do Apollo, regras do canal, consentimento e legislação aplicável.
- Para operações em massa, comece com amostra de até 10 contatos, valide e amplie somente após aprovação.
- Não autorize disparos enquanto SPF, DKIM, DMARC, domínio de rastreamento, caixa de envio, limites e política de descadastro não estiverem verificados. DNS é configurado no provedor do domínio/e-mail; Apollo diagnostica e usa a configuração.

## Fluxo padrão

### 1. Diagnosticar

Leia dados de contas, contatos, listas, sequências, tarefas, respostas e métricas disponíveis. Registre a cobertura e limitações da consulta. Classifique conta e pessoa separadamente e identifique o comitê de compra.

### 2. Construir o módulo estratégico

Siga `references/strategic-module.md`. Entregue objetivo e hipótese; TAM/SAM/SOM; ICP, personas, exclusões e sinais; Deal Flow planejado, necessário e realizado; lacunas SPICED; segmentos priorizados.

### 3. Construir o módulo operacional

Siga `references/operational-module.md` e `references/sequences.md`. Para cada sequência, defina entrada, saída, passos, responsáveis, SLA, campos obrigatórios e regras de parada. Use `references/writing-and-calls.md` para copy e roteiro.

### 4. Aprovar e implantar

Mostre uma tabela de alterações propostas com objeto, quantidade, ação e efeito. Após aprovação explícita, execute somente o escopo aprovado pelas ferramentas disponíveis. Leia novamente uma amostra para verificar o resultado. Se a escrita não for suportada, produza checklist de implantação manual.

### 5. Operar diariamente

Priorize respostas e compromissos agendados, depois tarefas vencidas e novas entradas dentro do limite. Ao receber resposta, pause a automação daquele contato e entregue ao humano: resumo, evidências, intenção provável, riscos e resposta sugerida.

Classifique a conversa em S0–S11 antes de recomendar a próxima ação. Uma resposta só autoriza o avanço sustentado por evidência. Não confunda silêncio, cordialidade, objeção, timing e opt-out.

### 6. Gerar painel

Monte um JSON conforme `references/data-contracts.md` e execute `python3 scripts/render_dashboard.py snapshot.json dashboard.html`.

O painel é uma fotografia gerada sob demanda. Exiba data/hora, período, cobertura e origem. Se uma métrica não estiver disponível, use `null`; nunca estime silenciosamente.

## Notificações

Use tarefas do Apollo com responsável, vencimento, prioridade e contexto como mecanismo operacional. As notificações dependem das configurações nativas da conta Apollo; confirme isso com o usuário e não alegue que uma notificação foi configurada sem evidência. Para alertas fora do Apollo, gere uma especificação separada — não crie integração externa por conta própria.

## Formato de saída

Encerre com: fase atual e percentual de prontidão; situação observada; decisões aprovadas; entregáveis salvos; fila por responsável e vencimento; alterações no Apollo; bloqueios técnicos; próxima decisão humana.
