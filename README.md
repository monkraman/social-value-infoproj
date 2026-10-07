# Infosys Social Value RFP Response Builder POC

A backend-only Proof of Concept (POC) demonstrating an end-to-end Retrieval-Augmented Generation (RAG) decision-support system for **Infosys Social Value tender responses**.

Tested and verifiable entirely through terminal commands (`curl`) and **Postman**.

---

## Architecture Overview

```text
Documents (PDF, DOCX, XLSX)
   │
   ▼
Document Extraction (PyMuPDF, python-docx, openpyxl)
   │
   ▼
Text & Table Normalization
   │
   ▼
Section & Paragraph Chunking (~800 chars, 150 overlap)
   │
   ▼
OpenAI Embeddings (text-embedding-3-small, 1536 dim)
   │
   ▼
PostgreSQL + pgvector (cosine distance indexing)
   │
   │
User/RFP Opportunity Query
   │
   ▼
Query Formulation & Embedding
   │
   ▼
Vector Similarity Search (pgvector cosine similarity)
   │
   ▼
Ranked Relevant Evidence Chunks
   │
   ▼
OpenAI LLM (gpt-4o-mini with structured JSON mode)
   │
   ▼
Structured Initiative Packages (Core, Enhanced, Localised)
   │
   ▼
Deterministic TOMs Calculation Layer (metric × volume × duration × unit value)
   │
   ▼
Social Value Response + Financial Audit Trail + Validation Flags
```

---

## Key Design Principles & Guardrails

1. **Deterministic Calculation Layer (No LLM Arithmetic)**:
   - Public sector bids require audited, repeatable mathematics.
   - The LLM's role is strictly confined to identifying relevant initiatives and estimating delivery volume.
   - Authoritative Social Value impact calculations are executed by the Python backend:
     $$\text{Total SV} = \text{Annual Volume} \times \text{Contract Duration (Years)} \times \text{Unit Value (\pounds)}$$
   - Computes overall package Social Value as a percentage of Total Contract Value and assesses commercial gap against the client's target weighting.
2. **Strict Grounding & Anti-Hallucination Guardrails**:
   - Initiatives explicitly distinguish between grounded knowledge (`is_from_knowledge_base: true`) and best-practice proposals (`is_from_knowledge_base: false`).
   - If the knowledge base does not contain an approved delivery partner or local cost, the system sets `partner: null` and surfaces a note in `validation_required` rather than fabricating external entities.
3. **Multi-Format Ingestion**:
   - Native support for **PDF** (PyMuPDF / page tracking), **DOCX** (python-docx / paragraph and table extraction), and **XLSX** (openpyxl / multi-sheet cell rows).
4. **Resilient Offline Fallback**:
   - Can be run and demonstrated offline with deterministic 1536-dimensional pseudo-vectors and structured responses, or online by configuring `OPENAI_API_KEY`.

---

## Technology Stack

- **Framework**: Python 3.13 / FastAPI / Uvicorn
- **Database**: PostgreSQL 17 with `pgvector 0.8.6`
- **ORM & Drivers**: SQLAlchemy 2.0 + psycopg 3
- **Multi-Provider AI & Embeddings**:
  - **Google Gemini (Active, 100% Free)**: `gemini-3.5-flash` for generation & `gemini-embedding-001` (1536 dim) for embeddings.
  - **OpenAI (Optional / Swappable)**: `gpt-4o-mini` & `text-embedding-3-small`.
  - **Offline Fallback**: Deterministic grounded vectors & baseline recommendations.
- **Document Extractors**: PyMuPDF (PDF), python-docx (DOCX), openpyxl (XLSX)
- **Validation**: Pydantic v2 & Pydantic-Settings
- **Testing**: pytest & FastAPI TestClient

---

## Project Structure

```text
social-value-rfp-poc/
├── app/
│   ├── main.py                     # FastAPI application entrypoint & lifecycle
│   ├── api/
│   │   ├── __init__.py
│   │   ├── health.py               # GET /health
│   │   ├── ai.py                   # POST /ai/test
│   │   ├── documents.py            # POST /documents/ingest, GET /documents
│   │   ├── search.py               # POST /search (pgvector similarity search)
│   │   ├── responses.py            # POST /responses/generate (RAG + Calculation)
│   │   └── calculations.py         # GET /calculations/metrics, POST /calculations/...
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic environment configuration
│   │   └── database.py             # SQLAlchemy engine & session factory
│   ├── models/
│   │   ├── __init__.py
│   │   ├── document.py             # Document model (metadata, filename, type)
│   │   └── chunk.py                # DocumentChunk model with Vector(1536)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── ai.py                   # AI test request/response schemas
│   │   ├── document.py             # Ingestion & document schemas
│   │   ├── search.py               # Vector search request/response schemas
│   │   ├── calculation.py          # TOMs metric & package calculation schemas
│   │   └── response.py             # RFP opportunity & package response schemas
│   └── services/
│       ├── __init__.py
│       ├── embedding_service.py    # OpenAI & deterministic fallback embeddings
│       ├── openai_service.py       # OpenAI chat completion & structured JSON prompting
│       ├── document_service.py     # PDF, DOCX, XLSX extraction & chunking pipeline
│       ├── retrieval_service.py    # pgvector cosine similarity retrieval
│       ├── calculation_service.py  # Deterministic National TOMs arithmetic engine
│       └── rag_service.py          # End-to-end RAG orchestrator
│
├── documents/
│   └── synthetic/                  # Sample knowledge documents (clearly marked synthetic)
│       ├── Infosys_Birmingham_Digital_Inclusion.docx
│       ├── Infosys_Youth_Employment_Pathways.pdf
│       ├── Infosys_Social_Value_Initiatives_Catalog.xlsx
│       └── Synthetic_National_TOMs_Proxy_Reference.xlsx
│
├── scripts/
│   ├── init_db.py                  # Enables pgvector & creates database schema
│   ├── generate_synthetic_docs.py  # Generates realistic PDF, DOCX, XLSX sample files
│   ├── seed_data.py                # Ingests documents into PostgreSQL + pgvector
│   ├── start_db.ps1                # Starts local PostgreSQL instance with pgvector
│   └── start_db.bat                # Batch script to start local PostgreSQL
│
├── tests/
│   ├── test_health.py              # Health check & root tests
│   ├── test_calculation.py         # Deterministic calculation unit tests
│   ├── test_documents.py           # Ingestion, search, and response generation tests
│   └── test_embedding_pgvector.py  # Standalone embedding + pgvector integration test
│
├── .env.example                    # Environment variable template
├── .env                            # Active environment variables
├── requirements.txt                # Python package dependencies
├── docker-compose.yml              # Containerized pgvector for Docker environments
├── postman_collection.json         # Postman collection for all endpoints
└── README.md                       # Comprehensive POC documentation
```

---

## Quickstart Guide

### 1. Configure Environment
Copy `.env.example` to `.env` and configure your credentials:

```bash
cp .env.example .env
```

Set your OpenAI API key in `.env`:
```env
OPENAI_API_KEY=sk-...
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:5434/social_value_db
```
*(If `OPENAI_API_KEY` is not set, the POC automatically runs in high-fidelity offline demonstration mode).*

### 2. Start PostgreSQL with pgvector

#### Option A: Portable Local Server (Already configured on port 5434)
Run the helper script:
```powershell
.\scripts\start_db.ps1
```
*(Or on Windows cmd: `scripts\start_db.bat`)*

#### Option B: Docker Compose (Port 5432)
```bash
docker compose up -d
```
*(Update `DATABASE_URL` in `.env` to port 5432 if using Docker).*

### 3. Initialize Database Schema
```bash
python scripts/init_db.py
```
Expected output:
```text
Connected to PostgreSQL: PostgreSQL 17.5...
Ensuring pgvector extension is enabled...
Creating database tables if not existing...
Verified tables in public schema: ['documents', 'document_chunks']
Database initialization completed successfully!
```

### 4. Generate Synthetic Knowledge Documents
```bash
python scripts/generate_synthetic_docs.py
```
Generates 4 synthetic documents across PDF, DOCX, and XLSX in `documents/synthetic/`.

### 5. Ingest Knowledge Base
```bash
python scripts/seed_data.py
```
Extracts, chunks, embeds, and loads all documents into PostgreSQL via pgvector.

### 6. Run the FastAPI Server
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive API docs are available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

## Automated Test Suite

Run the full pytest suite:
```bash
python -m pytest tests/ -v
```
All 9 test cases will execute:
- Database connectivity & pgvector extension check
- 1536-dimensional embedding storage & pgvector query
- Deterministic TOMs arithmetic & formula verification
- Document listing & chunk retrieval
- Vector similarity search
- Full end-to-end RAG response generation

---

## Postman Collection

Import `postman_collection.json` directly into Postman. It contains pre-configured requests for all milestones:
1. `GET /health`
2. `POST /ai/test`
3. `POST /documents/ingest`
4. `GET /documents`
5. `POST /search`
6. `POST /responses/generate`
7. `GET /calculations/metrics`
8. `POST /calculations/initiative`

---

## Milestone Verification & Terminal Commands (curl)

### Milestone 1 — FastAPI Health Check
```bash
curl.exe -s http://127.0.0.1:8000/health
```
**Response:**
```json
{
  "status": "ok",
  "app_name": "Infosys Social Value RFP Response Builder POC",
  "database": {
    "connected": true,
    "postgres_version": "PostgreSQL 17.5 on x86_64-windows...",
    "pgvector_installed": true,
    "pgvector_version": "0.8.6"
  },
  "openai_configured": true,
  "embedding_model": "text-embedding-3-small",
  "chat_model": "gpt-4o-mini"
}
```

---

### Milestone 2 — PostgreSQL + pgvector
Verified automatically via `python scripts/init_db.py` and `python tests/test_embedding_pgvector.py`.

---

### Milestone 3 — OpenAI Connectivity Test
```bash
curl.exe -s -X POST http://127.0.0.1:8000/ai/test \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain Social Value in one sentence."}'
```
**Response:**
```json
{
  "prompt": "Explain Social Value in one sentence.",
  "response": "Social Value represents the wider positive social, economic, and environmental benefits generated by public procurement and corporate activities.",
  "model": "gpt-4o-mini",
  "is_mock": false
}
```

---

### Milestone 5 — Document Ingestion (PDF / DOCX / XLSX)
Ingest a document via multipart upload:
```bash
curl.exe -s -X POST http://127.0.0.1:8000/documents/ingest \
  -F "file=@documents/synthetic/Infosys_Birmingham_Digital_Inclusion.docx"
```
**Response:**
```json
{
  "document_id": "f76ca252-d81a-45c6-9c57-8f4199c9291d",
  "filename": "Infosys_Birmingham_Digital_Inclusion.docx",
  "document_type": "docx",
  "chunks_created": 4,
  "message": "Document successfully ingested and indexed with pgvector"
}
```

View all ingested documents:
```bash
curl.exe -s http://127.0.0.1:8000/documents
```

---

### Milestone 6 — Vector Similarity Search
Test similarity search independently before invoking the LLM:
```bash
curl.exe -s -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "digital inclusion initiatives for Birmingham", "top_k": 3}'
```
**Response:**
```json
{
  "query": "digital inclusion initiatives for Birmingham",
  "total_results": 3,
  "results": [
    {
      "chunk_id": "847528e5-397a-42c2-8fe0-c8f742c3848b",
      "document_id": "f76ca252-d81a-45c6-9c57-8f4199c9291d",
      "filename": "Infosys_Birmingham_Digital_Inclusion.docx",
      "content": "Initiative Name: Digital Inclusion Workshop Series\nTheme: Digital Inclusion\nDelivery Mechanism: 4 workshops per contract year...",
      "similarity": 0.8421,
      "chunk_index": 1,
      "metadata": {
        "section_type": "paragraphs",
        "source_type": "docx"
      }
    }
  ]
}
```

---

### Milestone 7 & 8 — RAG Generation & Deterministic Calculations
Submit the RFP opportunity scenario:
- **Contract Duration**: 3 years
- **Contract Value**: £10,000,000
- **Social Value Target**: 10% (£1,000,000)
- **Location**: Birmingham
- **Priorities**: Digital Inclusion, Youth Employment

```bash
curl.exe -s -X POST http://127.0.0.1:8000/responses/generate \
  -H "Content-Type: application/json" \
  -d '{
    "contract_duration_years": 3,
    "contract_value_gbp": 10000000,
    "social_value_weighting_percent": 10,
    "client": "Birmingham City Council",
    "location": "Birmingham",
    "priorities": ["Digital Inclusion", "Youth Employment"],
    "top_k": 5
  }'
```

**Structured JSON Response (abbreviated extract):**
```json
{
  "opportunity": {
    "client": "Birmingham City Council",
    "location": "Birmingham",
    "contract_value_gbp": 10000000.0,
    "social_value_weighting_percent": 10.0,
    "contract_duration_years": 3
  },
  "core_package": {
    "name": "Core Package",
    "rationale": "Baseline compliance package grounded in verified Birmingham evidence.",
    "initiatives": [
      {
        "name": "Birmingham Digital Skills & Inclusion Clinics",
        "theme": "Digital Inclusion",
        "location": "Birmingham",
        "annual_volume": 4.0,
        "toms_metric_code": "NT8",
        "partner": "Birmingham Community Matters",
        "evidence_source": "Infosys_Birmingham_Digital_Inclusion.docx",
        "is_from_knowledge_base": true
      },
      {
        "name": "Birmingham Youth Tech Mentoring & Work Experience",
        "theme": "Youth Employment",
        "location": "Birmingham",
        "annual_volume": 3.0,
        "toms_metric_code": "NT3",
        "partner": "St Basils Youth Charity",
        "evidence_source": "Infosys_Youth_Employment_Pathways.pdf",
        "is_from_knowledge_base": true
      }
    ],
    "financial_calculation": {
      "package_name": "Core Package",
      "total_social_value_gbp": 58650.0,
      "contract_value_gbp": 10000000.0,
      "social_value_percentage": 0.59,
      "target_weighting_percent": 10.0,
      "target_social_value_gbp": 1000000.0,
      "target_met": false,
      "audit_trail": [
        "[NT8] Birmingham Digital Skills & Inclusion Clinics: 4.0 workshops/yr × 3 yrs = 12.0 workshops @ £1,250.00 = £15,000.00",
        "[NT3] Birmingham Youth Tech Mentoring & Work Experience: 3.0 people/yr × 3 yrs = 9.0 people @ £4,850.00 = £43,650.00",
        "Package Total: £58,650.00 (0.59% of £10,000,000.00 contract value). Target (10.0%): £1,000,000.00 -> GAP"
      ]
    }
  },
  "enhanced_package": {
    "name": "Enhanced Package",
    "financial_calculation": {
      "total_social_value_gbp": 71040.0,
      "social_value_percentage": 0.71,
      "target_met": false,
      "audit_trail": [
        "[NT20] Hardware Reuse Programme: 25.0 devices/yr × 3 yrs = 75.0 devices @ £320.00 = £24,000.00",
        "[NT1] Tech Apprenticeship Pathway: 52.0 weeks/yr × 3 yrs = 156.0 weeks @ £215.00 = £33,540.00",
        "[NT10] STEM Volunteering Outreach: 100.0 hours/yr × 3 yrs = 300.0 hours @ £45.00 = £13,500.00",
        "Package Total: £71,040.00 (0.71% of £10,000,000.00 contract value). Target (10.0%): £1,000,000.00 -> GAP"
      ]
    }
  },
  "localised_package": {
    "name": "Localised Package",
    "financial_calculation": {
      "total_social_value_gbp": 63000.0,
      "social_value_percentage": 0.63,
      "audit_trail": [
        "[NT8] Birmingham Digital Inclusion Workshop: 8.0 workshops/yr × 3 yrs = 24.0 workshops @ £1,250.00 = £30,000.00",
        "[NT14] Birmingham SME Supply Chain Commitment: 50,000.0 GBP spend/yr × 3 yrs = 150,000.0 GBP spend @ £0.22 = £33,000.00",
        "Package Total: £63,000.00 (0.63% of £10,000,000.00 contract value). Target (10.0%): £1,000,000.00 -> GAP"
      ]
    }
  },
  "assumptions": [
    "Client will provide access to local council/community venues in Birmingham at nominal or zero cost.",
    "Infosys delivery staff will be permitted 2 working days/year dedicated to Social Value volunteering."
  ],
  "validation_required": [
    "Confirm local community partner availability and formal agreement in Birmingham.",
    "Validate whether client accepts National TOMs proxy values or requires a proprietary Social Value measurement tool.",
    "Verify IT equipment availability for device refurbishment and GDPR sanitization protocol."
  ],
  "retrieved_evidence_chunks": 5
}
```

---

## National TOMs Proxy Metric Catalog

| Code | Metric Name | Theme | Unit | Unit Proxy Value | Audit Description |
|:---|:---|:---|:---|:---|:---|
| **NT1** | Local Apprenticeship Weeks | Employment & Skills | weeks | £215.00 | Apprentice training weeks delivered on contract |
| **NT3** | Young People Supported into Work (16-24 NEET) | Youth Employment | people | £4,850.00 | Young people supported into sustained employment |
| **NT8** | Digital Inclusion / Skills Workshops | Digital Inclusion | workshops | £1,250.00 | Community sessions for digitally excluded residents |
| **NT10**| Staff STEM Volunteering Hours | Community Engagement | hours | £45.00 | Employee volunteer hours supporting schools/charities |
| **NT14**| Local SME Supply Chain Spend Proxy | Economic Growth | £ spend | £0.22 | Direct subcontracting spend with local SMEs |
| **NT20**| Refurbished Digital Devices Donated | Digital Inclusion | devices | £320.00 | Donated wiped laptops/tablets with connectivity |

*(Note: Stored unit values are synthetic proxy figures intended for POC validation, not official National Social Value Portal figures).*

---

## API Reference Summary

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/health` | Application status, PostgreSQL connectivity & pgvector version |
| `POST` | `/ai/test` | OpenAI chat connectivity test |
| `POST` | `/documents/ingest` | Upload & chunk PDF/DOCX/XLSX into pgvector |
| `GET` | `/documents` | List all ingested documents and chunk counts |
| `DELETE` | `/documents/{id}` | Delete document and cascaded chunks |
| `POST` | `/search` | Cosine similarity vector search over document chunks |
| `POST` | `/responses/generate` | End-to-end RAG response builder with calculation layer |
| `GET` | `/calculations/metrics` | Retrieve all TOMs proxy metrics |
| `POST` | `/calculations/initiative` | Calculate single initiative Social Value |
| `POST` | `/calculations/package` | Calculate package Social Value total & percentage |
#   s o c i a l - v a l u e - i n f o p r o j  
 