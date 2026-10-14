# Frontend Integration & Backend API Specification
## Infosys Social Value RFP Response Builder

This document serves as the **single source of truth** for developers and AI agents implementing the frontend application (`Frontend-Social-value`) to connect seamlessly with the FastAPI backend (`social-value-infoproj`).

---

## 1. Backend Overview & Environment Setup

- **Backend Base URL**: `http://127.0.0.1:8000` (or `http://localhost:8000`)
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
- **CORS Setup**: Enabled for all origins (`*`), credentials allowed, all HTTP methods and headers enabled in `app/main.py`.
- **Database**: SQLite (`./social_value.db`) with fallback vector simulation, or PostgreSQL 17 + pgvector.

---

## 2. API Contract & Endpoints Summary

| Feature | HTTP Method | Endpoint | Request Body / Params | Expected Response Summary |
| :--- | :--- | :--- | :--- | :--- |
| **Health Check** | `GET` | `/health` | None | `{ "status": "healthy", "database": "connected", ... }` |
| **AI Connectivity Test** | `POST` | `/ai/test` | `{ "prompt": string }` | `{ "status": "success", "provider": string, "response": string }` |
| **Document Ingestion** | `POST` | `/documents/ingest` | `multipart/form-data` with `file` | `{ "document_id": string, "filename": string, "chunks_created": int, ... }` |
| **List Ingested Docs** | `GET` | `/documents` | None | Array of `{ "id", "filename", "document_type", "chunks_count", "created_at" }` |
| **Delete Document** | `DELETE` | `/documents/{id}` | Path param `id` (UUID) | `{ "message": "Document deleted successfully" }` |
| **Vector Semantic Search** | `POST` | `/search` | `{ "query": string, "top_k": int, "document_id"?: string }` | `{ "query": string, "total_results": int, "results": [...] }` |
| **RAG RFP Response Generation** | `POST` | `/responses/generate` | Opportunity details (JSON) | 3 Structured Packages (Core, Enhanced, Localised) + Financial Math |
| **TOMs Rate Card Catalog** | `GET` | `/calculations/metrics` | None | Array of National TOMs proxy metrics (code, name, unit, unit_value_gbp) |
| **Single Initiative Calculation** | `POST` | `/calculations/initiative` | `{ "initiative_name", "toms_code", "annual_volume", "duration_years" }` | Audited calculation with exact formula and total GBP |
| **Package Calculation** | `POST` | `/calculations/package` | Array of initiatives + contract value & duration | Package total GBP, percentage of contract, target gap status |

---

## 3. Detailed Request & Response Schemas

### 3.1 Generate RFP Response (`POST /responses/generate`)

#### Request Payload:
```json
{
  "contract_duration_years": 3,
  "contract_value_gbp": 10000000.0,
  "social_value_weighting_percent": 10.0,
  "client": "Birmingham City Council",
  "location": "Birmingham",
  "priorities": ["Digital Inclusion", "Youth Employment", "Local Supply Chain"],
  "top_k": 5
}
```

#### Response Structure:
```json
{
  "opportunity": {
    "client": "Birmingham City Council",
    "location": "Birmingham",
    "contract_value_gbp": 10000000.0,
    "duration_years": 3,
    "social_value_weighting_percent": 10.0,
    "target_social_value_gbp": 1000000.0,
    "priorities": ["Digital Inclusion", "Youth Employment"]
  },
  "core_package": {
    "name": "Core Baseline Package",
    "rationale": "Minimum risk baseline commitments directly aligned with mandatory criteria.",
    "expected_impact": ["12 Digital inclusion sessions", "9 Youth mentees supported"],
    "dependencies": ["Partner availability", "Community center access"],
    "initiatives": [
      {
        "name": "Birmingham Digital Skills Clinics",
        "theme": "Digital Inclusion",
        "location": "Birmingham",
        "description": "Quarterly hands-on digital skills sessions for underserved adults.",
        "delivery_mechanism": "4 workshops per year delivered with local libraries",
        "target_beneficiaries": "Elderly and jobseekers in East Birmingham",
        "annual_volume": 4.0,
        "toms_metric_code": "NT8",
        "partner": "Birmingham Central Library",
        "evidence_source": "Infosys_Birmingham_Digital_Inclusion.docx",
        "is_from_knowledge_base": true
      }
    ],
    "financial_calculation": {
      "package_name": "Core Baseline Package",
      "initiatives": [
        {
          "initiative_name": "Birmingham Digital Skills Clinics",
          "toms_code": "NT8",
          "metric_name": "Digital Inclusion Workshops Delivered",
          "unit": "workshops",
          "unit_value_gbp": 1250.0,
          "annual_volume": 4.0,
          "duration_years": 3,
          "total_volume": 12.0,
          "total_social_value_gbp": 15000.0,
          "calculation_formula": "4.0 × 3 yrs @ £1,250.00/workshops = £15,000.00"
        }
      ],
      "total_social_value_gbp": 15000.0,
      "contract_value_gbp": 10000000.0,
      "social_value_percentage": 0.15,
      "target_weighting_percent": 10.0,
      "target_social_value_gbp": 1000000.0,
      "target_met": false,
      "audit_trail": [
        "Birmingham Digital Skills Clinics (NT8): 4.0 annual × 3 yrs × £1,250.00 = £15,000.00"
      ]
    }
  },
  "enhanced_package": { ... },
  "localised_package": { ... },
  "assumptions": [
    "Volunteer hours supported by Birmingham delivery hub staff.",
    "Proxy rates derived from National TOMs v2024 guidance."
  ],
  "validation_required": [
    "Verify whether local charity partnership requires MOUs before tender submission."
  ],
  "retrieved_evidence_chunks": 5,
  "grounding_summary": {
    "total_chunks_matched": 5,
    "top_similarity_score": 0.92
  },
  "is_mock": false
}
```

---

### 3.2 Document Ingestion (`POST /documents/ingest`)

- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Fields**: `file`: Binary file (`.pdf`, `.docx`, `.xlsx`, `.txt`, `.md`)
- **Response**:
```json
{
  "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "filename": "Infosys_Birmingham_Case_Study.pdf",
  "document_type": "pdf",
  "chunks_created": 14,
  "message": "Document successfully ingested and indexed with pgvector"
}
```

---

### 3.3 Interactive Calculations (`POST /calculations/package`)

Allows frontend users to dynamically tune initiative volumes and instantly recalculate Social Value impact and commercial target status without calling the LLM.

#### Request:
```json
{
  "package_name": "Custom Tuned Package",
  "contract_value_gbp": 10000000.0,
  "duration_years": 3,
  "target_weighting_percent": 10.0,
  "initiatives": [
    {
      "initiative_name": "Local SME Supply Chain Spend",
      "toms_code": "NT31",
      "annual_volume": 150000.0,
      "duration_years": 3
    },
    {
      "initiative_name": "Apprentice Cohort",
      "toms_code": "NT1",
      "annual_volume": 4.0,
      "duration_years": 3
    }
  ]
}
```

#### Response:
```json
{
  "package_name": "Custom Tuned Package",
  "initiatives": [...],
  "total_social_value_gbp": 1024340.0,
  "contract_value_gbp": 10000000.0,
  "social_value_percentage": 10.24,
  "target_weighting_percent": 10.0,
  "target_social_value_gbp": 1000000.0,
  "target_met": true,
  "audit_trail": [...]
}
```

---

## 4. Recommended Frontend Architecture (`Frontend-Social-value`)

```text
Frontend-Social-value/
├── src/
│   ├── api/
│   │   ├── client.ts             # Axios / Fetch client configured to http://127.0.0.1:8000
│   │   ├── responses.ts          # generateResponse(), getStatus()
│   │   ├── documents.ts          # uploadDocument(), listDocuments(), deleteDocument()
│   │   ├── calculations.ts       # getMetrics(), calculatePackage()
│   │   └── search.ts             # searchKnowledge()
│   ├── components/
│   │   ├── Header.tsx            # Navigation, Backend Health badge, Theme
│   │   ├── OpportunityForm.tsx   # Tender inputs (Client, £ Value, Yrs, Weighting %, Priorities)
│   │   ├── PackageCard.tsx       # Package view (Core / Enhanced / Localised) with metrics
│   │   ├── InitiativeTable.tsx   # TOMs code, volumes, unit values, audit formula
│   │   ├── CommercialGapBanner.tsx # Target Met vs Target Gap status bar
│   │   ├── VolumeTunerModal.tsx  # Dynamic slider to tweak volumes & test target met
│   │   ├── DocumentManager.tsx   # Drag-and-drop file upload & chunks list
│   │   └── KnowledgeSearch.tsx   # Live vector search tester
│   ├── types/
│   │   └── index.ts              # Full TypeScript definitions matching backend Pydantic models
│   ├── App.tsx                   # Main layout and tab switching
│   └── main.tsx
├── package.json
└── vite.config.ts
```

---

## 5. UI Views & User Journeys

1. **RFP Response Generator (Primary Flow)**:
   - User inputs opportunity requirements (Council, Contract Value, Duration, Weighting %, Social Value Priorities).
   - Real-time submission triggers `/responses/generate`.
   - Side-by-side or tabbed view comparing **Core**, **Enhanced**, and **Localised** packages.
   - Financial breakdown with explicit anti-hallucination badges (`Grounded in Evidence` vs `Model Recommended`).
   - Audit trail drawer explaining exact mathematical equations.

2. **Knowledge Ingestion Portal**:
   - Drag-and-drop uploader for previous RFP documents, case studies, and TOMs rate cards.
   - Shows file type, uploaded timestamp, and chunk count.
   - Live vector search test box to confirm retrieval works as expected.

3. **TOMs Rate Card & Interactive Tuner**:
   - View official National TOMs rates (`NT1`, `NT8`, `NT31`, etc.).
   - Interactive calculator to test what volumes are needed to hit a specific financial commitment.

---

## 6. Anti-Hallucination & Guardrails Front-End Display Rules

- **Partner Badge**: If `partner` is `null` or missing, display a yellow badge: `⚠️ Verification Needed: No partner in knowledge base`.
- **Grounding Badge**: If `is_from_knowledge_base` is `true`, display a green badge `✓ Verified from Grounding Docs`. If `false`, display `ℹ️ AI Proposed Suggestion`.
- **Math Audit Trail**: Always display the `calculation_formula` string under each initiative so tender evaluators see the deterministic arithmetic proof.
