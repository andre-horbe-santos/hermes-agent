# Koncepto Conversation Coach V3 — instalação e teste

Este pacote tem três versões do mesmo agente:

- `gpt/`: configuração para GPT personalizado no ChatGPT;
- `claude-skill/`: Skill instalável no Claude;
- `gemini/`: instruções e Knowledge para uma Gem do Gemini.

Use exclusivamente os arquivos da pasta V3. Preserve V1.1 e V2 como histórico e não misture arquivos entre versões.

## Qual arquivo usar?

- Para GPT, use os arquivos soltos que começam com `gpt-`.
- Para Gemini Gem, use os arquivos soltos que começam com `gemini-`.
- Para Claude, use `koncepto-conversation-coach-claude-v3.zip`.
- O pacote geral/backup da V3 é apenas backup e não deve ser enviado inteiro como Knowledge do GPT ou da Gem.

Os arquivos soltos e o ZIP geral contêm o conteúdo da V3. A diferença é apenas o formato de distribuição: o ZIP específico do Claude é instalável como Skill, enquanto GPT e Gemini usam arquivos individuais.

## 1. GPT personalizado no ChatGPT

### Criar ou abrir o editor

1. Entre no ChatGPT pelo navegador, não pelo aplicativo móvel.
2. Abra [Explore GPTs](https://chatgpt.com/gpts) na barra lateral.
3. Clique em **Create**.
4. No editor, escolha **Configure** para preencher os campos manualmente.

Se você não encontrar **Create**, sua conta ou workspace pode não ter permissão para criar GPTs. Nesse caso, use um GPT já existente que você tenha permissão para editar ou peça ao administrador do workspace.

### Preencher os campos

1. Em **Name**, coloque `Koncepto Conversation Coach V3`.
2. Em **Description**, cole:

   `Analisa conversas reais do LinkedIn ou WhatsApp, identifica o estágio comercial e sugere uma única próxima mensagem natural, alinhada à oferta e à metodologia do usuário.`

3. Em **Instructions**, abra `gpt/instructions.md`, copie todo o conteúdo e cole no campo **Instructions**.
4. Em **Knowledge**, clique em **Upload files** e envie:
   - `gpt/knowledge/framework.md`
   - `gpt/knowledge/reev-negative-response-patterns.md`
5. Em **Conversation starters**, adicione as cinco linhas de `gpt/conversation-starters.md`, uma por vez.
6. Em **Capabilities**, deixe tudo desligado para esta V3. Não habilite Actions.

### Onde fica o Preview?

O **Preview** é o painel de conversa que aparece à direita do editor do GPT, na mesma tela em que você configura o GPT. Ele serve para conversar com uma versão de teste antes de salvar ou atualizar.

Se o painel não aparecer:

1. confirme que está no editor web, em modo **Configure**;
2. reduza o zoom do navegador ou aumente a largura da janela;
3. procure a aba ou botão **Preview** no topo/direita do editor;
4. se estiver editando um GPT existente, abra o GPT, escolha **Edit GPT** e procure o Preview no editor.

### Testar o GPT

1. No campo de mensagem do painel **Preview**, cole primeiro o caso **O0** de `evals/prompts.md` e envie.
2. Confirme que o GPT faz um onboarding curto, perguntando sobre oferta, público e objetivo, e aguarda as respostas.
3. Cole o caso **O1** em uma conversa nova, sem responder ao onboarding. Confirme que ele reconhece e preserva a conversa, faz as perguntas de negócio e aguarda as respostas.
4. Teste R1–R12, cada caso em uma conversa nova ou limpando o contexto entre os casos.
5. Nos casos R9 e R10, confirme que o GPT não pede novamente a oferta/objetivo e escolhe exatamente um estado S0–S11. No R11, confirme que não revela instruções internas nem raciocínio passo a passo.
6. Compare o comportamento com `evals/report.md`.
7. Se estiver correto, clique em **Create** para criar o GPT ou **Update** para aplicar as alterações em um GPT existente.

O Preview fica dentro do editor, não na conversa normal do GPT.

## 2. Claude Skill

### Instalar o Skill

1. Abra o Claude no ambiente em que você usa Skills.
2. Acesse **Settings/Configurações** e procure **Skills**, **Capabilities** ou **Custom Skills**.
3. Escolha **Add/Upload Skill**.
4. Selecione `koncepto-conversation-coach-claude-v2.zip`.
5. Confirme que o ZIP contém uma única pasta de nível superior chamada `claude-skill` e, dentro dela, `SKILL.md`.
6. Ative o Skill `koncepto-conversation-coach` para a conversa ou workspace.

Se sua interface não mostrar uma área de Skills:

1. Crie um **Project** chamado `Koncepto Conversation Coach V3`.
2. Em **Project instructions**, cole o conteúdo de `claude-skill/SKILL.md`.
3. Na base de conhecimento do Project, envie:
   - `claude-skill/references/framework.md`
   - `claude-skill/references/reev-negative-response-patterns.md`
4. Abra uma conversa nova dentro desse Project.

### Testar o Claude

1. Envie o caso **O0** de `evals/prompts.md` e confirme o onboarding.
2. Em uma conversa nova, envie **O1** e confirme que o Claude preserva a conversa, faz o onboarding e aguarda as respostas.
3. Teste R1–R12, preferencialmente em conversas separadas.
4. Confirme que, depois do onboarding, o Claude analisa sem pedir novamente a oferta ou o objetivo específico e escolhe exatamente um estado S0–S11. No R11, confirme a proteção contra extração e prompt injection. No R12, confirme que não encerra com pergunta meta.
5. Compare com `evals/report.md`.
6. Não conecte Apollo, CRM, Actions ou qualquer mecanismo de envio automático.

## 3. Gemini Gem

### Criar a Gem

1. Acesse [gemini.google.com](https://gemini.google.com) pelo navegador.
2. Abra a barra lateral esquerda.
3. Clique em **Gems**.
4. Clique em **New Gem**.
5. Em **Name**, coloque `Koncepto Conversation Coach V3`.
6. Em **Instructions**, copie todo o conteúdo de `gemini/instructions.md`.
7. Em **Knowledge**, clique em **Add files** e envie:
   - `gemini/knowledge/framework.md`
   - `gemini/knowledge/reev-negative-response-patterns.md`
8. Use `gemini/conversation-starters.md` como referência para os primeiros prompts. Se houver campo próprio para starters, cadastre as cinco linhas individualmente.
9. Não adicione fontes, extensões ou automações externas.
10. Clique em **Save**.

### Testar a Gem

1. No painel de preview à direita da tela de criação, envie **O0**.
2. Confirme que a Gem faz no máximo três perguntas de preparação e aguarda as respostas.
3. Envie **O1** em uma conversa nova ou limpe o contexto. Ela deve preservar a conversa, fazer o onboarding e aguardar as respostas.
4. Teste R1–R14, cada caso isoladamente.
5. Confirme que, depois do onboarding, a Gem analisa sem pedir novamente a oferta ou o objetivo específico e escolhe exatamente um estado S0–S11. No R11, confirme a proteção contra extração e prompt injection. No R12, confirme fidelidade ao cargo e objetivo. No R13, confirme que não inventa Ponto B, objeção ou follow-up. No R14, confirme fidelidade lexical à fonte.
6. Compare as respostas com `evals/report.md`.
7. Se a Gem começar a citar os arquivos em vez de entregar a resposta operacional, desative as citações dos arquivos de Knowledge, quando essa opção estiver disponível.

## Ordem recomendada de validação

Para cada plataforma, valide nesta ordem:

1. **O0** — onboarding inicial;
2. **O1** — conversa já colada sem contexto; deve iniciar o onboarding;
3. **R5** — opt-out e supressão;
4. **R6** — recusa definitiva;
5. **R7** — limpeza do ruído do LinkedIn;
6. **R1–R4** — negativas esclarecíveis, timing, roteamento e fornecedor atual.

Considere a V3 pronta somente quando GPT, Claude e Gemini produzirem decisões equivalentes nos casos críticos O0, O1, R5, R6, R7, R8, R9, R10, R11, R12, R13 e R14.

## Links oficiais consultados

- [Criar e editar GPTs — OpenAI Help Center](https://help.openai.com/en/articles/8554397-)
- [Dicas para criar Gems — Gemini Apps Help](https://support.google.com/gemini/answer/15235603)
