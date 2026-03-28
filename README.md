## NewsBot DevOps/SRE/Cloud → LinkedIn

Pipeline automatizado para coletar notícias via RSS, filtrar por temas relevantes (DevOps, SRE, Cloud, segurança, arquitetura e boas práticas), gerar posts opinativos com LLM e publicar periodicamente no LinkedIn.

---

### Arquitetura

```
RSS Feeds → Coleta + Filtro + Deduplicação → Ranking por título
          → Extração de conteúdo (trafilatura) → Resumo via LLM (top 3)
          → Editorial via LLM → Publicação via LinkedIn API
```

---

### Pré-requisitos

- Python 3.11+
- Conta e App no [LinkedIn Developers](https://www.linkedin.com/developers/) com produto **Share on LinkedIn** e escopo `w_member_social`
- `GROQ_API_KEY` — chave gratuita em [console.groq.com/keys](https://console.groq.com/keys)
- `OPENAI_API_KEY` — usado como fallback quando o Groq atinge limite de tokens

---

### Instalação local

```bash
git clone <seu-repo>
cd <seu-repo>
python -m venv env && source env/bin/activate
pip install -r requirements.txt
```

#### Obter token e URN do LinkedIn (rode uma vez)

```bash
python3 scripts/get_linkedin_token.py
```

#### Modo dry-run (imprime o post sem publicar)

```bash
export LINKEDIN_ACCESS_TOKEN="seu_token"
export LINKEDIN_MEMBER_URN="urn:li:person:XXXX"
export GROQ_API_KEY="sua_chave"
export DRY_RUN=1
python -m newsbot.main
```

#### Publicar

```bash
unset DRY_RUN
python -m newsbot.main
```

---

### Configuração de fontes e temas

Edite `newsbot/sources.yml`:
- `feeds`: lista de RSS feeds
- `keywords.include`: palavras-chave para filtrar notícias relevantes
- `keywords.exclude`: palavras-chave para descartar notícias irrelevantes

---

### GitHub Actions

#### Secrets necessários

| Secret | Descrição |
|---|---|
| `LINKEDIN_ACCESS_TOKEN` | Token OAuth gerado pelo `scripts/get_linkedin_token.py` |
| `LINKEDIN_MEMBER_URN` | `urn:li:person:ID` |
| `LINKEDIN_CLIENT_ID` | Client ID do app no LinkedIn Developers |
| `LINKEDIN_CLIENT_SECRET` | Client Secret do app |
| `GROQ_API_KEY` | Chave Groq (gratuita) |
| `GROQ_MODEL` | (opcional) modelo Groq, padrão: `llama-3.3-70b-versatile` |
| `OPENAI_API_KEY` | Chave OpenAI usada como fallback |
| `GH_PAT` | PAT do GitHub com permissão `secrets:write` |

#### Workflows

| Workflow | Arquivo | Quando roda |
|---|---|---|
| Publicar post | `schedule.yml` | Dias úteis às 12:00 UTC |
| Renovar token | `renew_token.yml` | Dia 1 a cada 2 meses (+ manual) |
| Lembrete de token | `token_reminder.yml` | Dia 1 de cada mês |

#### Renovação automática de token

O workflow `renew_token.yml` sobe um browser Chromium headless, faz login no LinkedIn, completa o OAuth e atualiza o secret `LINKEDIN_ACCESS_TOKEN` automaticamente.

Se falhar (2FA, CAPTCHA, senha alterada):
1. Rode `python3 scripts/get_linkedin_token.py` localmente
2. Copie o `ACCESS_TOKEN` impresso
3. Atualize o secret `LINKEDIN_ACCESS_TOKEN` em Settings → Secrets

---

### Estrutura do projeto

```
newsbot/
├── __init__.py
├── collector.py          coleta e filtra RSS feeds
├── extract.py            extrai conteúdo textual das URLs
├── llm_helper.py         cliente LLM com fallback Groq → OpenAI
├── summarize.py          resumo dos artigos via LLM
├── ranker.py             ranking por keywords e recência
├── editorial.py          geração do post via LLM
├── format_post.py        formata o texto final
├── publish_linkedin.py   publica via LinkedIn API
├── main.py               pipeline end-to-end
└── sources.yml           feeds RSS e palavras-chave

scripts/
├── get_linkedin_token.py      obtém token OAuth inicial
├── auto_renew_token.py        renovação headless via Playwright
├── validate_linkedin_token.py valida e verifica expiração do token
└── update_github_secret.py    atualiza secret via GitHub API

.github/workflows/
├── schedule.yml          publicação diária
├── renew_token.yml       renovação automática do token
└── token_reminder.yml    lembrete mensal de expiração
```

---

### Observações

- O ranking usa apenas o título na primeira passagem para evitar chamadas desnecessárias ao LLM.
- Apenas o top 3 de artigos é summarizado; o post final é gerado a partir do mais relevante.
- O limite diário do Groq (100k tokens) é suficiente para rodar o pipeline uma vez por dia; em caso de estouro, o OpenAI é acionado automaticamente.
- O token do LinkedIn expira em 60 dias; o workflow de renovação roda automaticamente antes disso.

---

© 2026 Guilherme Rogério Ramos Dias. Todos os direitos reservados.
