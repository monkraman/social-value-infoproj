# Low-Level Design (LLD) Document
# Infosys Social Value Initiative Generator

**Document Identifier:** INFOSYS-SV-LLD-2026-V2  
**Document Version:** 2.0.0 (supersedes 1.0.0, which described the earlier RFP Response Builder)  
**Status:** Proof of concept at handover  
**Audience:** Backend and frontend engineers, QA, DevOps  
**Date:** 18 November 2026

---

## 1. Scope

This document specifies the modules, data, interfaces and algorithms of the Initiative Generator as built in the `main` branch of the two repositories at handover. The High-Level Design (INFOSYS-SV-HLD-2026-V2) gives the context and principles. Where this document and the code differ, the code is right; please update this document.

---

## 2. Repositories and Modules

### 2.1 Backend (`social-value-infoproj`)

| Path | Responsibility |
| :--- | :--- |
| `app/main.py` | FastAPI app, middleware (request ID, audit logging, CORS), router registration, table creation at startup |
| `app/core/config.py` | Settings from environment variables; provider order and configured-provider checks |
| `app/core/security.py` | PBKDF2-HMAC-SHA256 password hashing, HS256 JWT creation and validation |
| `app/core/database.py` | SQLAlchemy engine and session |
| `app/api/auth.py` | Sign-in, current user, password change, user creation (superadmin), `require_roles` |
| `app/api/generator.py` | Initiative Generator endpoints, evidence attachment, document text extraction |
| `app/api/generator_runs.py` | Saved runs per user |
| `app/api/admin_ai.py` | Primary AI model choice (superadmin) |
| `app/api/documents.py`, `app/api/search.py` | Past bid document ingestion, listing, archive and vector search |
| `app/api/audit.py`, `app/api/health.py` | Audit log, summary, retention purge; health and diagnostics |
| `app/api/calculations.py` | TOMs Catalog, Regional Partners and Value Tuner endpoints |
| `app/services/generator_service.py` | Prompt builder, output contract, `generate()`, initiative type labels |
| `app/services/initiative_valuation.py` | Valuation and all checks (pure functions) |
| `app/services/llm_client.py` | Provider calls (Azure OpenAI, Gemini, OpenAI), ordered fallback, JSON parsing |
| `app/services/ai_settings_service.py` | Stored primary-provider choice and the effective order |
| `app/services/embedding_service.py`, `retrieval_service.py`, `document_service.py` | Embeddings, vector search, text extraction and chunking |
| `app/services/tender_prompt.py` | Deterministic parser for the tender sentence |
| `app/knowledge/` | `tables.json` (workbook import), `initiative_types.json`, `rules.md` |
| `scripts/import_workbook.py` | Rebuilds `tables.json` from the knowledge workbook |
| `tests/` | 123 pytest tests |

The `responses` router, `prompt_interpreter_service.py`, `rag_service.py` and `openai_service.py` belong to the earlier prompt-based builder. They remain registered but are not used by the Initiative Generator.

### 2.2 Frontend (`Frontend-Social-value`)

| Path | Responsibility |
| :--- | :--- |
| `src/App.tsx` | Shell, sign-in gate, page switching |
| `src/components/Sidebar.tsx` | Navigation, recent tenders, diagnostics panel |
| `src/components/AiModelPanel.tsx` | AI model card in diagnostics |
| `src/components/generator/LocalGenerator.tsx` | Tender entry, framework and criteria, buyer documents, results, totals, checks |
| `src/components/generator/InitiativeCard.tsx` | One initiative: lines, partner choice, done before, evidence, wording, questions |
| `src/api/client.ts` | Base URL, auth headers, fetch wrapper |
| `src/api/generator.ts`, `src/api/adminAi.ts` | Typed calls to the generator and admin endpoints |
| `src/local/backendAi.ts` | Maps the backend result to the card model (`fromBackend`), value drift check |
| `src/local/engine.ts`, `frameworks.ts`, `measureMac.ts`, `infosysLens.ts` | Totals, framework definitions, criteria mapping, fallback fit rating |
| `src/local/repository.ts`, `policy.ts` | Document text and buyer policy reading |

---

## 3. Data Model

All tables are created by SQLAlchemy `create_all` at startup. UUID primary keys unless noted.

| Table | Key columns | Notes |
| :--- | :--- | :--- |
| `users` | `id`, `name`, `email` (unique), `password_hash`, `role`, `is_active`, `created_at` | Roles: `superadmin`, `bid_author`, `reviewer` |
| `generator_runs` | `id`, `user_id`, `title`, `client`, `region`, `framework`, `contract_value_gbp`, `target_gbp`, `value_gbp`, `initiative_count`, `state` (JSON), `created_at`, `updated_at` | `state` holds the full form and result; filtered by `user_id` on every read |
| `documents` | `id`, `filename`, `document_type`, `is_archived`, `archived_at`, `created_at` | Archived documents are excluded from search |
| `document_chunks` | `id`, `document_id`, `chunk_index`, `content`, `embedding` (vector 1536), `created_at` | Cosine distance search via pgvector |
| `system_audit_logs` | `id`, `request_id`, `timestamp`, `event_type`, `severity`, `endpoint`, `method`, `status_code`, `duration_ms`, `user_id`, `client_ip`, `message`, `error_detail`, `metadata_payload` (JSON) | Retention 1,095 days; purge endpoint |
| `app_settings` | `key` (PK), `value` (JSON), `updated_by`, `updated_at` | `ai_primary_provider` = `{"provider": "azure" or null}` |
| `regional_partners` | `id` (integer), `location`, `partner_name`, `theme`, `toms_code`, `focus_area`, `contact_info`, `description`, `is_approved` | Regional Partners page |
| `toms_metrics` | `id` (integer), `code`, `name`, `theme`, `unit`, `unit_value_gbp`, … | TOMs Catalog page |
| `prompt_history` | Earlier builder's prompts and results | Kept for reference |

**Knowledge file `tables.json`** (generated, versioned): `measures` (code, theme, name, unit, proxy, localised flag, unit guidance), `regions` (median wage and factors), `industries`, `settings` (default region and industry, carbon baseline 2.4%, contract name), `initiative_library` (track record: id, name, what, mac, measures, delivered_by), `capability` (partner, capability, proven, available, notes), `measure_mac` (measure, framework version, MAC, strength), `patterns`, `wording`, `source`, `edition`, `imported_at`.

---

## 4. API

All endpoints except `/health`, `/ping`, `/auth/login` and `/auth/status` need a valid bearer token. Errors return `{"detail": "<reason>"}`.

| Method and path | Purpose | Notes |
| :--- | :--- | :--- |
| `POST /auth/login` | Email and password to JWT | 8-hour token |
| `GET /auth/me` | Current user | |
| `POST /auth/change-password` | Change own password | 204 |
| `POST /auth/register` | Create a user | superadmin only |
| `POST /generator/parse` | Tender sentence to form fields | No AI; lists what is missing |
| `GET /generator/options` | Regions, themes, defaults, table edition | |
| `GET /generator/knowledge` | Track record, measures, MAC map, partners, documents for the frontend | |
| `POST /generator/run` | Generate, value, check and attach evidence | 422 unknown region; 503 when no AI provider answers |
| `POST /generator/extract` | Text of an uploaded file, not stored | PDF, DOCX, XLSX, TXT, MD; 15 MB; 413, 422 |
| `GET /generator/documents/{id}/text` | Text of a repository document | |
| `GET/POST /generator/runs`, `GET/PUT/DELETE /generator/runs/{id}` | Saved runs of the current user | |
| `GET/PUT /admin/ai` | Read or set the primary AI model | superadmin only; 422 if not configured; audited |
| `POST /documents/ingest`, `GET /documents`, `DELETE /documents/{id}`, `POST /documents/{id}/restore`, `GET /documents/{id}/chunks` | Past bid documents | Delete archives by default (`?permanent=true` removes the document and its vectors); 503 when embeddings are unavailable, nothing half-written |
| `POST /search` | Vector search over passages | 503 when embeddings are unavailable |
| `GET /audit/logs`, `GET /audit/summary`, `POST /audit/purge-expired` | Audit log | |
| `GET /health` | Database, pgvector, active provider, configured providers | Used by diagnostics |

### 4.1 `POST /generator/run`

Request:

```json
{"company": "Infosys", "bid_amount_gbp": 12000000, "sv_percent": 10, "region": "North East",
 "duration_years": 5, "themes": ["Work", "Community"], "industry": "Computer programming, consultancy and related services",
 "client": "North East Lincolnshire Council", "framework": "PPN0620", "brief": "Scored criteria and buyer priorities"}
```

Response (abridged):

```json
{"target_gbp": 1200000, "totals": {"infosys_gbp": 0, "partner_gbp": 0, "conditional_gbp": 0},
 "initiatives": [{"name": "...", "theme": "...", "description": "...", "attribution": "Infosys", "partner": "Springpod",
   "macs": ["2.2"], "no_tom_reason": null, "done_before": [{"id": "INI-22", "name": "...", "why": "..."}],
   "lines": [{"measure": "NT12", "measure_name": "...", "unit": "no. weeks", "units": 1000, "basis": "250 x 4",
              "proxy_gbp": 96.53, "proxy_basis": "national proxy", "value_gbp": 96530, "status": "Counted", "note": ""}],
   "value_gbp": 96530, "conditional_gbp": 0, "cost_gbp": null, "bid_paragraph": "...", "questions": ["..."],
   "status": "Proposal", "type": {"id": "PAT-04", "fit": "Deliverable"}, "evidence": []}],
 "checks": ["..."], "tables": {"source": "...", "edition": "...", "imported_at": "..."},
 "form": {"...": "..."}, "model": "azure/gpt-4.1-mini"}
```

---

## 5. Algorithms

### 5.1 Provider order and fallback (`llm_client`, `ai_settings_service`)
1. Configured providers: Azure needs key, endpoint and deployment; Gemini and OpenAI need a key.
2. Default order: `LLM_PROVIDER`, then each of `LLM_FALLBACK`, keeping only configured ones, no repeats.
3. Effective order: the stored superadmin choice first (if configured), then the default order. The stored choice is cached for 15 seconds; a database error falls back to the default order.
4. For each provider: call with the system and user prompt, JSON response format; parse JSON (code fences stripped). Any failure moves to the next provider. Gemini also moves down its own model list on HTTP 404, 429, 500 or 503 and rests a failed model for 10 minutes.
5. All failed: raise `LLMUnavailable` with every reason; the API returns 503.

### 5.2 Valuation (`value_initiatives`)
For each initiative and line:
1. Strip any key or text containing a £ amount from the AI output (rule 2, E3).
2. Unknown measure → `Not valued`. Missing or non-positive units → `Not valued`.
3. Caps: barrier-group measures (NT3, NT4, NT5, NT6, NT76) at one FTE-year per person (A-06); NT1 at people × years; supply-chain spend (NT14, NT18, NT19) at the contract value.
4. Quantity check (no change to the number): if the basis splits on `x` or `×` into factors that each contain a number and their product differs from units by more than 1%, or a `weeks` measure gives one person more than 52 × contract years weeks, add a line note, a check and a question.
5. Proxy: national, or localised by region and industry where the measure requires it (A-03; NT1 = regional median wage).
6. Value = units × proxy, rounded to pence.
7. A-07: within an initiative only the first employment measure counts; later ones are `Alternative`.
8. A-13: carbon measures are `Conditional` beyond the 2.4% a year baseline.

Then per initiative: keep only claimed MACs served by a proposed measure under the framework (A1) and flag criteria with only supporting links (A2); validate citations against the track record (D2); add the standing question on cost, owner and evidence. Totals add counted values to Infosys or partner by attribution. A total above 150% of the target adds a warning.

### 5.3 Initiative type (`apply_initiative_types`)
The AI returns a type ID from the 19 curated types. The fit rating, name and reason come from `initiative_types.json`; an unknown ID leaves the rating empty with a check.

### 5.4 Evidence (`attach_evidence`)
Documents are split into chunks of up to 800 characters with 150 overlap, embedded with `gemini-embedding-001` at 1,536 dimensions. For each initiative the query is its name and description; the top six hits are considered; a hit counts at similarity ≥ 0.6; each chunk goes to its best initiative; at most two passages per initiative and one per document; snippets are cut to 400 characters. When embeddings are unavailable, search returns 503 or the run notes that evidence is unavailable; synthetic vectors are used only when `EMBEDDING_ALLOW_SYNTHETIC` is set.

### 5.5 Frontend mapping (`fromBackend`)
Backend values are used as given (`proxy_gbp`, `value_gbp`). The frontend recomputes totals for display and adds a check if any differ from the backend's (value drift). Backend citations, evidence and type are used, with the earlier local heuristics as fallback when a field is absent (older saved runs).

---

## 6. Configuration

| Variable | Default | Notes |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | `auto` | `azure`, `gemini`, `openai` or `offline` |
| `LLM_FALLBACK` | empty | Comma list, e.g. `gemini` |
| `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT` | empty | All three needed |
| `AZURE_OPENAI_API_VERSION` | `2024-10-21` | `2025-01-01-preview` in use |
| `AZURE_OPENAI_TEMPERATURE` | unset | Leave unset for reasoning models |
| `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_EMBEDDING_MODEL` | | Embedding model `gemini-embedding-001` |
| `OPENAI_API_KEY`, `OPENAI_CHAT_MODEL` | | Optional third provider |
| `EMBEDDING_PROVIDER` | `auto` | Changing it means re-indexing documents |
| `EMBEDDING_DIMENSION` | `1536` | Must match the column |
| `EMBEDDING_ALLOW_SYNTHETIC` | false | Development only |
| `DATABASE_URL` | | PostgreSQL with pgvector |
| `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` minutes | |
| `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD` | | First superadmin |
| `CORS_ORIGINS` | | Frontend address |
| `VITE_API_URL` (frontend) | | Backend address |

---

## 7. Error Handling

| Situation | Behaviour |
| :--- | :--- |
| No AI provider answers | 503 with each provider's reason; nothing valued |
| AI returns invalid JSON | Treated as a provider failure; next provider tried |
| Unknown region | 422 |
| Embeddings unavailable during ingestion | 503, transaction rolled back, nothing stored |
| Embeddings unavailable during a run | Run succeeds; a check says evidence is unavailable |
| No documents in the repository | Run succeeds; a check says so |
| Unreadable upload | 422 with the reason (protected file, scanned PDF needing OCR) |
| Missing or expired token | 401; wrong role 403 |

---

## 8. Testing

Run `pytest` in the backend repository (123 tests, about nine minutes against a remote database). Coverage includes valuation rules and checks (`test_initiative_valuation.py`), generator API with a fake AI (`test_generator_api.py`), Phase 1 behaviour (`test_generator_phase1.py`), provider order, fallback and the admin switch (`test_llm_providers.py`), authentication and route protection, documents and pgvector, and saved runs. Tests create users named `pytest-…` and remove them afterwards. The frontend is checked with `tsc` and `oxlint`.
