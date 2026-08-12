# Paid Media Prompt Library

Use these prompts as task templates. Replace bracketed fields and keep the result
read-only unless the user explicitly approves an operation.

## 1. Full account audit

```text
Audite a conta [PLATAFORMA/ID] no período [DATA INICIAL–DATA FINAL].
Objetivo principal: [VENDAS/LEADS/RECEITA/MARGEM]. Meta: [CPA/ROAS/CAC].

Analise estrutura, tracking, orçamento, pacing, estratégia de lance, termos de
pesquisa, Quality Score quando disponível, anúncios, públicos, Performance Max
quando aplicável e desperdício. Separe problemas de entrega, qualidade do tráfego,
anúncio, landing page e vendas.

Entregue: resumo executivo; evidências; impacto estimado; confiança; riscos; quick
wins; testes; correções estruturais; dados faltantes. Não faça alterações.
```

## 2. Search-term waste and negatives

```text
Analise os termos de pesquisa de [PERÍODO] para [CONTA/CAMPANHAS].
Encontre termos com gasto >= [VALOR] e 0 conversões, mas não use esse filtro
isoladamente: considere intenção, ciclo de conversão e volume.

Agrupe por intenção, indique motivo da exclusão, sugira palavra-chave negativa e
tipo de correspondência. Em uma seção separada, liste termos que merecem virar
palavras-chave próprias. Informe o gasto potencialmente desperdiçado. Não aplique.
```

## 3. Conversion-tracking health

```text
Verifique a saúde do tracking de conversões de [CONTA] nos últimos [N] dias.
Liste cada ação, status, fonte, contagem, valor, janela, duplicidade possível,
quedas anormais, atraso de importação e sinais de que o Smart Bidding está usando
dados incompletos. Compare com [CRM/ANALYTICS] se disponível.

Classifique cada problema como crítico, alto, médio ou baixo e proponha testes de
validação. Não altere configurações.
```

## 4. Budget pacing and reallocation

```text
Avalie o pacing de orçamento de [CONTA] entre [DATA INICIAL] e [DATA FINAL].
Compare orçamento planejado, gasto, conversões, CPA, receita e ROAS por campanha.
Simule a transferência de [PERCENTUAL]% de [CAMPANHA A] para [CAMPANHA B] usando
desempenho marginal e limitações de volume, não uma projeção linear ingênua.

Retorne cenários conservador/base/agressivo, premissas, risco de aprendizado e
plano de reversão. Não altere orçamento.
```

## 5. Bid-strategy fit

```text
Para cada campanha, avalie se a estratégia de lance atual é suportada pelo volume,
qualidade e valor das conversões. Considere objetivo, ciclo de vendas, orçamento,
conversões recentes, mudanças de tracking e sobreposição entre campanhas.

Recomende manter, testar ou revisar a estratégia. Explique o que precisaria ser
verdadeiro para uma mudança ser segura e qual janela de avaliação usar. Não aplique.
```

## 6. Performance Max diagnosis

```text
Analise as campanhas Performance Max de [CONTA] em [PERÍODO].
Compare grupos de recursos, sinais, categorias/termos de pesquisa disponíveis,
produtos ou feeds, valor de conversão, ROAS e distribuição de gasto. Identifique
possível sobreposição de marca, categorias irrelevantes, problemas de feed e assets
fracos. Separe fatos observados de inferências e proponha testes reversíveis.
```

## 7. Weekly executive report

```text
Gere um relatório semanal para [PÚBLICO] comparando [SEMANA ATUAL] com
[SEMANA ANTERIOR] e, quando relevante, com o mesmo período anterior.

Mostre somente mudanças materiais em gasto, conversões, CPA, receita, ROAS,
qualidade dos leads e pacing. Explique causas prováveis, grau de confiança,
impacto no negócio e as três próximas ações. Inclua uma seção “sem ação” para
itens que não justificam intervenção.
```

## 8. Creative testing

```text
Com base nos anúncios vencedores de [PERÍODO], crie [N] variações para o público
[PÚBLICO], oferta [OFERTA] e landing page [URL]. Preserve os elementos que parecem
contribuir para o resultado, teste uma hipótese por variação e respeite os limites,
políticas e claims da plataforma.

Entregue matriz hipótese → variação → métrica primária → critério de decisão →
janela mínima. Não publique.
```

## 9. Anomaly investigation

```text
Investigue a queda/aumento de [MÉTRICA] em [CONTA/CAMPANHA] entre [PERÍODOS].
Decomponha a variação por entrega, orçamento, leilão, consulta, dispositivo,
localização, público, anúncio, tracking e etapa pós-clique. Liste explicações
alternativas e evidências que confirmariam ou refutariam cada uma.

Conclua com ações de diagnóstico antes de ações de otimização.
```

## 10. Approval packet for a live change

```text
Prepare um pacote de aprovação para a alteração [AÇÃO].
Inclua recurso e ID, estado atual, estado proposto, motivo baseado em dados,
orçamento ou alcance afetado, impacto esperado, riscos, dependências, janela de
avaliação e rollback exato. Não execute até receber confirmação explícita.
```
