# Infosys Social Value Initiative Generator — Backend

FastAPI backend for the Social Value Initiative Generator. It proposes social value initiatives for a UK public sector tender with an AI model, then values and checks every one in code against the Open Access TOM System.

**The rule that shapes the code: the AI proposes, the code calculates.** The AI returns initiatives and quantities only; every £ value is units × proxy from `app/knowledge/tables.json`, and every checkable claim is checked.

Design documents: [High-Level Design](docs/HIGH_LEVEL_DESIGN_DOCUMENT_HLD.md) and [Low-Level Design](docs/LOW_LEVEL_DESIGN_DOCUMENT_LLD.md) (version 2.0, also as `.docx`). Older documents for the earlier RFP Response Builder are in [`docs/archive`](docs/archive/README.md).

---

## Stack

- Python, FastAPI, SQLAlchemy
- PostgreSQL with pgvector (1,536-dimension embeddings)
- AI: Azure OpenAI (primary), Google Gemini (fallback and embeddings), OpenAI (optional)
- Frontend: separate repository `Frontend-Social-value` (React, TypeScript, Vite)

## Project layout

```text
app/
  main.py                  App, middleware, routers
  core/                    Settings, security (JWT, PBKDF2), database
  api/                     Endpoints: auth, generator, generator_runs, admin_ai, documents, search, audit, health
  services/
    generator_service.py   Prompt builder and generate()
    initiative_valuation.py  Valuation and all checks (pure functions)
    llm_client.py          Provider calls and ordered fallback
    ai_settings_service.py Primary-provider choice
    embedding_service.py, retrieval_service.py, document_service.py
  knowledge/               tables.json, initiative_types.json, rules.md
scripts/
  import_workbook.py       Rebuild tables.json from the knowledge workbook
  generate_docx_designs.py Build the HLD and LLD .docx files from Markdown
tests/                     pytest suite
```

## Run locally

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill it in. At least `DATABASE_URL`, `JWT_SECRET_KEY` and one AI provider are needed. `.env` is excluded from Git; never commit keys.

3. Start the server. Tables are created at startup.

```bash
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

API documentation is served at `http://127.0.0.1:8000/docs`.

## AI providers

| Setting | Meaning |
| :--- | :--- |
| `LLM_PROVIDER` | Provider tried first: `azure`, `gemini` or `openai` |
| `LLM_FALLBACK` | Providers tried next, in order, when the first is out of quota or down |
| `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` | Azure OpenAI; used only when endpoint, key and deployment are all set |
| `GEMINI_API_KEY` | Gemini, also used for document embeddings |
| `EMBEDDING_PROVIDER` | Embedding provider; changing it means re-indexing every document |

A super-administrator can change which configured provider answers first from the diagnostics panel (`GET/PUT /admin/ai`). Only the choice is stored; keys stay in the environment. `GET /health` reports the active provider.

## Tests

```bash
.venv/Scripts/python -m pytest -q
```

123 tests. They use the database in `DATABASE_URL`, create users named `pytest-…` and remove them afterwards. AI calls are faked, so no AI quota is used.

## Updating the knowledge base

When the TOM System publishes a new edition, or the track record or capability profile changes:

```bash
.venv/Scripts/python scripts/import_workbook.py "<path to workbook>.xlsx"
```

Review the diff of `app/knowledge/tables.json` and commit it. Past bid documents are uploaded through the Repository page, not committed.

## Deployment

Pushing to `main` runs `.github/workflows/main_infosys-social-value.yml`, which deploys to Azure App Service `infosys-social-value`. Set the settings from `.env.example` as App Service environment variables, with secrets in Key Vault.
