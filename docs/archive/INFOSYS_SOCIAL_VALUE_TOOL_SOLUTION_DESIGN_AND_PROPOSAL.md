# Infosys Social Value RFP Response Builder
## Solution Design, Functional Architecture & Delivery Blueprint

---

## 1. Executive Summary & Business Context

### 1.1 The Business Need in UK Public Sector Bids
In UK public procurement (Central Government under **PPN 06/20**, NHS Trusts, and Local Authorities such as Birmingham City Council), tender submissions are legally required to include a dedicated **Social Value commitment**. 

Social Value accounts for **10% to 20% of the total tender evaluation score**, frequently determining the difference between winning and losing multi-million-pound contracts.

```text
Typical Tender Evaluation Weighting:
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│     Commercial / Price       │     Technical / Delivery     │        Social Value          │
│            40%               │            45%               │          10% - 15%           │
└──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
                                                              ▲
                                                    Determines Bid Outcome
```

### 1.2 Current Bid Team Pain Points
1. **Manual, Repetitive Research**: Bid managers spend days scouring fragmented shared drives, past bid submissions, and corporate CSR brochures to find relevant proof points.
2. **LLM Arithmetic & Compliance Risk**: Generative AI tools (ChatGPT, etc.) hallucinate numbers, fabricate partnerships, and misapply unit rates. Public sector tenders require auditable, contractually binding figures linked to **National TOMs (Themes, Outcomes, and Measures)**.
3. **Localisation Deficit**: Councils penalize generic national initiatives; they demand ward-level, local evidence tailored to local socio-economic challenges.

### 1.3 The Solution Vision
The **Infosys Social Value RFP Response Builder** is an intelligent decision-support platform designed specifically for Infosys bid and commercial teams. It retrieves verified past evidence, uses an LLM to formulate tailored initiatives, and applies a strict, deterministic backend calculation engine to compute auditable Social Value commitments without hallucinations.

---

## 2. High-Level Solution Architecture & Flowcharts

### 2.1 The End-to-End System Flowchart
This diagram illustrates the complete journey: from initial document ingestion to client RFP processing, AI structuring, and final audited package generation.

```mermaid
flowchart TD
    subgraph S1["Stage 1: Enterprise Knowledge Ingestion"]
        DOCS["Source Documents<br/>(Past Bids, Case Studies, CSR Policies, Rate Cards)"]
        PARSER["Multi-Format Extractors<br/>(PyMuPDF, python-docx, openpyxl)"]
        CHUNKER["Normalizer & Semantic Chunker<br/>(~800 chars, 150 overlap)"]
        EMBED["Vector Embedding Engine<br/>(1536-Dimensional Unit Vectors)"]
        PGV[("PostgreSQL 17 + pgvector<br/>Cosine Distance Index")]
        
        DOCS --> PARSER --> CHUNKER --> EMBED --> PGV
    end

    subgraph S2["Stage 2: RFP Opportunity Query & Vector Retrieval"]
        RFP["Bid Team RFP Inputs<br/>• Client: Birmingham Council<br/>• Duration: 3 Years<br/>• Value: £10M (10% Target)<br/>• Priorities: Digital Inclusion, Youth"]
        QGEN["Semantic Query Formulation"]
        SIM["Vector Similarity Search<br/>(pgvector Cosine Distance <=>)"]
        EV["Top-K Grounded Evidence Chunks<br/>(Source documents, similarity scores, page refs)"]
        
        RFP --> QGEN --> SIM
        PGV --> SIM --> EV
    end

    subgraph S3["Stage 3: Multi-Provider AI Reasoning"]
        PROMPT["Structured Anti-Hallucination Prompt"]
        TOMS_REF["National TOMs Metric Catalog<br/>(Proxy Unit Values)"]
        LLM{"Swappable LLM Engine<br/>• Google Gemini (Active Free Tier)<br/>• OpenAI GPT-4o-mini (Enterprise)"}
        PACKAGES["Structured Initiative Packages<br/>(Core, Enhanced, Localised)"]
        
        EV --> PROMPT
        RFP --> PROMPT
        TOMS_REF --> PROMPT
        PROMPT --> LLM --> PACKAGES
    end

    subgraph S4["Stage 4: Deterministic Financial Calculation Engine"]
        MATH["Python Calculation Engine<br/>Vol/Yr × Duration × Unit Value (£) = Total SV (£)"]
        AUDIT["Audited Package Totals<br/>• % of Contract Value<br/>• Target vs Gap Analysis"]
        VAL["Validation & Risk Flags<br/>(Missing partners, cost checks, ward data)"]
        
        PACKAGES --> MATH --> AUDIT
        PACKAGES --> VAL
    end

    subgraph S5["Stage 5: Delivery & Output"]
        OUT["Bid-Ready Deliverables<br/>• Interactive Web UI / Dashboard<br/>• Export to Word (.docx) Tender Submission<br/>• Export to Excel (.xlsx) Calculation Sheet"]
        
        AUDIT --> OUT
        VAL --> OUT
    end
```

---

### 2.2 The Critical AI vs. Deterministic Logic Boundary
To prevent tender disqualification, the tool strictly divides responsibilities between Generative AI and Deterministic Code:

```mermaid
flowchart LR
    subgraph GenerativeAI["Generative AI (LLM) Responsibilities"]
        direction TB
        G1["Interprets Tender Requirements"]
        G2["Synthesizes Retrieved Evidence"]
        G3["Proposes Initiative Titles & Descriptions"]
        G4["Estimates Annual Delivery Volumes"]
        G5["Maps Initiatives to TOMs Metric Codes"]
    end

    subgraph Divider["Strict Boundary"]
        DIV["NO LLM ARITHMETIC<br/>NO FABRICATED PARTNERS<br/>NO INVENTED COSTS"]
    end

    subgraph DeterministicEngine["Deterministic Backend (Python) Responsibilities"]
        direction TB
        D1["Multiplies Volume × Years × Unit Value"]
        D2["Calculates % of Total Contract Value"]
        D3["Compares Against Client Target Weighting"]
        D4["Generates Line-by-Line Audit Trail"]
        D5["Flags Commercial Gap (GAP / MET)"]
    end

    GenerativeAI --> Divider --> DeterministicEngine
```

---

## 3. How the Tool Functions (Core Functional Modules)

### 3.1 Module 1: Multi-Format Knowledge Ingestion
- Ingests **PDF**, **Word (.docx)**, and **Excel (.xlsx)** tender assets.
- Captures paragraphs, hierarchical headings, and data tables.
- Standardizes content into ~800-character overlapping chunks to preserve semantic context across sentence boundaries.
- Generates 1536-dimensional unit vectors stored in PostgreSQL with pgvector indexing.

### 3.2 Module 2: Semantic Evidence Retrieval
- Automatically builds contextual search queries from tender priorities, client name, and geographical focus.
- Executes cosine similarity search against stored chunks:
  $$\text{Cosine Similarity} = 1.0 - (\text{embedding} \Leftrightarrow \text{query\_vector})$$
- Returns ranked chunks with document provenance (filename, page/sheet, excerpt, similarity score).

### 3.3 Module 3: Tri-Package Initiative Structuring
The AI model structures the proposal into three distinct strategic options:
1. **Core Package (Baseline Compliance)**: High-confidence, low-risk initiatives strictly grounded in verified historical data.
2. **Enhanced Package (Winning Advantage)**: High-impact initiatives designed to maximize tender evaluation scores.
3. **Localised Package (Place-Based Multiplier)**: Initiatives tailored to local council wards, local supply chain spend, and regional charities.

### 3.4 Module 4: Deterministic TOMs Calculation Engine
- Applies verified proxy values from the National TOMs framework:
  $$\text{Total Social Value (\pounds)} = \text{Annual Volume} \times \text{Duration (Years)} \times \text{Proxy Unit Value (\pounds)}$$
- Generates complete audit trails for tender compliance:
  `[NT8] Digital Inclusion Clinics: 4.0 workshops/yr × 3 yrs = 12.0 workshops @ £1,250.00 = £15,000.00`
- Performs commercial gap analysis: compares calculated value against the client's percentage weighting target.

### 3.5 Module 5: Anti-Hallucination & Validation Safeguards
- Highlights which initiatives are supported by source documents (`is_from_knowledge_base: true`).
- If no approved local partner or cost exists in the evidence, the tool sets `partner: null` and surfaces a mandatory verification task in `validation_required`.

---

## 4. Technology Stack & Architectural Rationale

| Layer | Chosen Technology | Why This Technology? | Production Evolution |
|:---|:---|:---|:---|
| **API & Backend** | **FastAPI + Python 3.13** | High-performance async REST API, auto-generated OpenAPI documentation, native Pydantic validation. | Containerized microservice on AWS ECS / Azure App Service. |
| **Vector Database** | **PostgreSQL 17 + pgvector 0.8.6** | Eliminates separate vector DB licensing (Pinecone/Weaviate); integrates relational metadata and vector similarity in one ACID-compliant engine. | Managed Amazon RDS for PostgreSQL / Azure Database with pgvector. |
| **Active LLM** | **Google Gemini 3.5 Flash** | **100% Free tier (Google AI Studio)**, fast response time, native JSON output mode, zero upfront cost. | Enterprise Google Cloud Vertex AI or OpenAI GPT-4o. |
| **Swappable LLM** | **OpenAI GPT-4o-mini** | Zero-code switch via `.env` setting; ready if enterprise client mandates OpenAI. | Azure OpenAI Service instance. |
| **Document Parsers** | **PyMuPDF, python-docx, openpyxl** | Lightweight, robust extraction of text and complex tables across PDF, Word, and Excel formats. | Scalable batch background parsing queue (Celery/Redis). |
| **Frontend UI** | **Next.js / React (Phase 5)** | Modern responsive web interface for non-technical bid teams with interactive charts and export triggers. | Enterprise corporate intranet or SSO portal. |

---

## 5. Working Proof-of-Concept (POC) Proof Points

### 5.1 What Has Been Proven in the Working POC
The backend POC is built, running locally, and verified across all milestones:

| Milestone / Capability | Verification Proof |
|:---|:---|
| **FastAPI Backend** | `GET /health` returns `status: ok` with PostgreSQL and multi-provider status. |
| **PostgreSQL + pgvector** | Native PG17 instance on port 5434 storing 1536-dimensional vectors with cosine indexing. |
| **Document Ingestion** | Successfully ingested 5 documents (PDF, DOCX, XLSX) into 22 vector chunks. |
| **Vector Search** | `POST /search` retrieves Birmingham evidence with `0.7285` similarity score. |
| **Live AI Reasoning** | Live `gemini-3.5-flash` produces structured JSON packages with zero hallucination. |
| **Deterministic Calculations** | Backend Python engine computes all math, producing formula strings and gap assessments. |
| **Automated Test Suite** | **9 out of 9 automated pytest test cases passing** (`100% test pass rate`). |

### 5.2 Birmingham Test Scenario Results (£10M Contract, 3 Years, 10% Target)
The system was tested against the benchmark scenario:

```text
Input Requirements:
• Contract Duration: 3 Years
• Contract Value: £10,000,000.00
• Target Social Value Weighting: 10.0% (£1,000,000.00 Target)
• Location: Birmingham
• Priorities: Digital Inclusion, Youth Employment

Live System Results:
┌─────────────────────┬──────────────────────┬────────────────┬────────────────────────┐
│ Package             │ Total Calculated SV  │ SV % of Value  │ Commercial Assessment  │
├─────────────────────┼──────────────────────┼────────────────┼────────────────────────┤
│ Core Package        │ £58,650.00           │ 0.59%          │ £941,350.00 GAP        │
│ Enhanced Package    │ £71,040.00           │ 0.71%          │ £928,960.00 GAP        │
│ Localised Package   │ £66,540.00           │ 0.67%          │ £933,460.00 GAP        │
└─────────────────────┴──────────────────────┴────────────────┴────────────────────────┘

Actionable Safeguards Surfaced by System:
1. "Confirm specific local Birmingham secondary schools to partner with for the INF-SV-003 STEM volunteering initiative."
2. "Verify capability and legal compliance of West Midlands Digital Device Bank (INF-SV-004) to handle corporate data-wiped assets."
3. "Identify and validate local Birmingham training providers/colleges to partner with for the proposed NT1 Local Apprenticeship Weeks."
```

---

## 6. Phased Delivery Blueprint (Proposal Deliverables Roadmap)

```mermaid
gantt
    title Infosys Social Value RFP Response Builder — Delivery Blueprint
    dateFormat  YYYY-MM-DD
    section Phase 1: Core POC
    FastAPI & PostgreSQL pgvector        :done, p1_1, 2026-09-01, 2026-09-15
    Document Ingestion (PDF, DOCX, XLSX) :done, p1_2, 2026-09-16, 2026-09-25
    Vector Search & Multi-Provider LLM   :done, p1_3, 2026-09-26, 2026-10-05
    Deterministic TOMs Math Engine       :done, p1_4, 2026-10-06, 2026-10-07
    section Phase 2: Document Export
    Word (.docx) Tender Response Export  :active, p2_1, 2026-10-08, 2026-10-18
    Excel (.xlsx) Financial Audit Sheet  :p2_2, 2026-10-19, 2026-10-25
    section Phase 3: Interactive Tuner
    Dynamic Volume Adjuster API          :p3_1, 2026-10-26, 2026-11-05
    Target Gap Re-balancing Engine       :p3_2, 2026-11-06, 2026-11-15
    section Phase 4: Enterprise Ingestion
    Real Bid Document Archive Sync       :p4_1, 2026-11-16, 2026-11-25
    National TOMs v29.x Rate Card Import :p4_2, 2026-11-26, 2026-12-05
    section Phase 5: Web UI Dashboard
    Next.js Interactive Tender Portal    :p5_1, 2026-12-06, 2026-12-25
    Visual Charts, Comparison & Review   :p5_2, 2026-12-26, 2027-01-10
```

### 6.1 Proposal Deliverables vs. Status Matrix

| Proposal Deliverable | Scope Description | Current Status | Delivery Phase |
|:---|:---|:---:|:---:|
| **DEL-01: Multi-Format Ingestion Engine** | Extract & chunk PDF, DOCX, XLSX into vector database | **Completed & Verified** | Phase 1 (POC) |
| **DEL-02: pgvector Similarity Search** | High-speed semantic similarity retrieval | **Completed & Verified** | Phase 1 (POC) |
| **DEL-03: Multi-Provider LLM Reasoning** | Grounded package synthesis (Gemini Free + OpenAI Swappable) | **Completed & Verified** | Phase 1 (POC) |
| **DEL-04: Deterministic TOMs Math Engine** | Zero-hallucination arithmetic, percentage calculation, and gap analysis | **Completed & Verified** | Phase 1 (POC) |
| **DEL-05: Anti-Hallucination Guardrails** | Automated validation logging for missing partners/costs | **Completed & Verified** | Phase 1 (POC) |
| **DEL-06: Formatted Tender Export** | Direct download of client-ready Word (.docx) & Excel (.xlsx) responses | *Planned* | Phase 2 |
| **DEL-07: Interactive Bid Tuner** | Real-time slider/API to adjust initiative volume to hit target % | *Planned* | Phase 3 |
| **DEL-08: Enterprise Knowledge Sync** | Ingestion of real Infosys tender history & full TOMs v29 tables | *Planned* | Phase 4 |
| **DEL-09: Next.js Interactive Dashboard** | Modern web portal for bid teams with visual package comparisons | *Planned* | Phase 5 |

---

## 7. Conclusion & Recommendation

The **Infosys Social Value RFP Response Builder POC** has successfully proven all foundational technical hypotheses:
1. Unstructured tender documents can be parsed and semantically retrieved with high precision using native **PostgreSQL + pgvector**.
2. **Generative AI** can be effectively constrained to qualitative reasoning and volume estimation without hallucinating tender commitments.
3. **Deterministic Python math** eliminates commercial risk by ensuring every calculated pound and percentage is strictly auditable.
4. The **Multi-Provider Architecture** provides enterprise flexibility—running on Google Gemini's free tier today while remaining fully OpenAI-ready for production.

The platform is now ready for presentation to leadership and commercial teams as the validated technical foundation for the full product delivery.
