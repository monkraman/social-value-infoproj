# Build Brief — Infosys Social Value RFP Response Builder POC

## Objective

Build a backend-only proof of concept for an Infosys Social Value RFP Response Builder.

Do NOT build the frontend yet.

The POC must be testable entirely through terminal commands and Postman.

The purpose is to prove that we can:

1. ingest Social Value knowledge documents,
2. extract and chunk their content,
3. generate embeddings,
4. store embeddings in PostgreSQL using pgvector,
5. retrieve relevant knowledge for an RFP/opportunity,
6. send the retrieved context to an LLM,
7. generate a structured Social Value recommendation,
8. keep numerical/business calculations deterministic rather than relying on the LLM.

---

## Technology Stack

Use:

- Python
- FastAPI
- PostgreSQL
- pgvector
- OpenAI API
- Pydantic
- PyMuPDF for PDF extraction
- python-docx for DOCX extraction
- openpyxl for XLSX extraction

Do NOT introduce:

- LangChain initially
- LlamaIndex initially
- Agentic RAG
- Pinecone
- Weaviate
- custom ML models
- fine-tuning
- microservices
- complex authentication
- frontend

Keep the implementation simple and understandable.

---

# Target Architecture

```text
Documents
   |
   v
Document Extraction
   |
   v
Text / Tables
   |
   v
Chunking
   |
   v
OpenAI Embeddings
   |
   v
PostgreSQL + pgvector
   |
   |
User/RFP Query
   |
   v
Query Embedding
   |
   v
Vector Similarity Search
   |
   v
Relevant Chunks
   |
   v
OpenAI LLM
   |
   v
Structured JSON
   |
   v
Business / TOMs Calculation Layer
   |
   v
Social Value Packages
```

---

# Initial Project Structure

Create a clean structure similar to:

```text
social-value-rfp-poc/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── health.py
│   │   ├── ai.py
│   │   ├── documents.py
│   │   ├── search.py
│   │   └── responses.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   │
│   ├── models/
│   │   ├── document.py
│   │   └── chunk.py
│   │
│   ├── schemas/
│   │   ├── ai.py
│   │   ├── document.py
│   │   ├── search.py
│   │   └── response.py
│   │
│   └── services/
│       ├── openai_service.py
│       ├── document_service.py
│       ├── embedding_service.py
│       ├── retrieval_service.py
│       ├── rag_service.py
│       └── calculation_service.py
│
├── scripts/
│   └── init_db.py
│
├── documents/
│
├── tests/
│
├── .env.example
├── requirements.txt
├── README.md
└── docker-compose.yml
```

The exact structure can be adjusted if there is a strong technical reason, but keep responsibilities separated.

---

# Environment

Use environment variables.

Example:

```env
OPENAI_API_KEY=
DATABASE_URL=
OPENAI_CHAT_MODEL=
OPENAI_EMBEDDING_MODEL=
```

Never hardcode API keys.

Never expose the OpenAI API key through a future frontend.

---

# Milestone 1 — FastAPI

Create:

```text
GET /health
```

Expected:

```json
{
  "status": "ok"
}
```

The application must start locally using a simple documented command.

---

# Milestone 2 — PostgreSQL + pgvector

Create PostgreSQL configuration.

Enable pgvector.

Create a minimal document/chunk model.

Suggested conceptual schema:

```text
documents
---------
id
filename
document_type
metadata
created_at
```

```text
document_chunks
---------------
id
document_id
chunk_index
content
metadata
embedding vector(...)
created_at
```

Do not over-design the schema yet.

The embedding dimension must match the selected OpenAI embedding model.

---

# Milestone 3 — OpenAI Connectivity

Create:

```text
POST /ai/test
```

Input:

```json
{
  "prompt": "Explain Social Value in one sentence."
}
```

Return a clean JSON response.

Use the OpenAI API from the backend only.

---

# Milestone 4 — Embeddings

Implement an embedding service.

Input:

```text
A text chunk
```

Output:

```text
embedding vector
```

Create a small test that:

1. sends text to the embedding model,
2. receives the vector,
3. stores it in PostgreSQL.

---

# Milestone 5 — Document Ingestion

Create:

```text
POST /documents/ingest
```

Initially support:

- PDF
- DOCX
- XLSX

Pipeline:

```text
file
 ↓
extract text
 ↓
normalize text
 ↓
split into chunks
 ↓
generate embeddings
 ↓
store document
 ↓
store chunks
```

Return useful information such as:

```json
{
  "document_id": "...",
  "filename": "...",
  "chunks_created": 25
}
```

Do not make chunking unnecessarily sophisticated in V1.

---

# Milestone 6 — Retrieval

Create:

```text
POST /search
```

Example:

```json
{
  "query": "digital inclusion initiatives for Birmingham",
  "top_k": 5
}
```

Process:

```text
query
 ↓
embedding
 ↓
pgvector similarity search
 ↓
top K chunks
```

Return:

```json
{
  "results": [
    {
      "chunk_id": "...",
      "content": "...",
      "similarity": 0.87,
      "document_id": "..."
    }
  ]
}
```

This endpoint is important because it lets us independently test whether RAG retrieval is working before involving the LLM.

---

# Milestone 7 — RAG Generation

Create:

```text
POST /responses/generate
```

Example input:

```json
{
  "contract_duration_years": 3,
  "contract_value_gbp": 10000000,
  "social_value_weighting_percent": 10,
  "client": "Example Council",
  "location": "Birmingham",
  "priorities": [
    "Digital Inclusion",
    "Youth Employment"
  ]
}
```

The backend should:

1. construct a retrieval query,
2. generate its embedding,
3. retrieve relevant knowledge,
4. build a controlled context,
5. send context + opportunity requirements to OpenAI,
6. request structured JSON,
7. return the structured result.

---

# Expected LLM Output

Do not return an uncontrolled essay.

Use a predictable structure similar to:

```json
{
  "core_package": {
    "initiatives": [],
    "rationale": "",
    "expected_impact": [],
    "dependencies": []
  },
  "enhanced_package": {
    "initiatives": [],
    "rationale": "",
    "expected_impact": [],
    "dependencies": []
  },
  "localised_package": {
    "initiatives": [],
    "rationale": "",
    "expected_impact": [],
    "dependencies": []
  },
  "assumptions": [],
  "validation_required": []
}
```

The exact schema can evolve.

---

# Critical Rule — Do Not Hallucinate

The system must distinguish between:

1. information retrieved from source documents,
2. calculated values,
3. model-generated recommendations,
4. assumptions,
5. information requiring human validation.

If the knowledge base does not contain sufficient evidence, the system should flag:

```text
validation_required
```

rather than inventing an Infosys initiative, partner, cost or TOMs value.

---

# Critical Rule — TOMs / Numerical Calculations

Do NOT ask the LLM to perform authoritative Social Value calculations.

The architecture should eventually be:

```text
LLM
 ↓
identify relevant metric
 ↓
backend calculation service
 ↓
metric × volume × duration × unit value
 ↓
calculated impact
```

The calculation layer must be deterministic and auditable.

For the initial POC, it is acceptable to use synthetic/sample TOMs data.

Do not claim that synthetic values are official National TOMs values.

---

# Initial Test Data

Before real Infosys documents are available, create a small synthetic knowledge set.

For example:

### Initiative

```text
Name:
Digital Inclusion Workshop

Theme:
Digital Inclusion

Location:
Birmingham

Delivery:
4 workshops per year

Participants:
12 young people per session

Frequency:
4 sessions per year

Evidence:
Synthetic POC data only
```

Create several synthetic initiatives covering:

- Digital Inclusion
- Youth Employment
- Skills
- Community engagement

Also create synthetic partner examples.

Clearly label synthetic data.

---

# Test Scenario

Use:

```text
Contract duration: 3 years
Contract value: £10,000,000
SV weighting: 10%
Location: Birmingham
Priorities:
- Digital Inclusion
- Youth Employment
```

Expected behavior:

The system should retrieve relevant initiatives and generate multiple possible packages.

It should NOT invent unsupported partner/cost/TOMs information.

---

# Testing

Every milestone must be testable independently.

At minimum document Postman requests for:

```text
GET  /health
POST /ai/test
POST /documents/ingest
POST /search
POST /responses/generate
```

Also provide curl examples.

---

# Development Approach

Do not build everything at once.

Implement in this order:

1. FastAPI
2. PostgreSQL connection
3. pgvector
4. OpenAI connection
5. embeddings
6. document ingestion
7. vector retrieval
8. RAG
9. structured recommendation
10. deterministic calculation layer

After each milestone:

- run the application,
- test the endpoint,
- fix errors,
- update README,
- only then move to the next milestone.

---

# Important

This is a POC, not the production platform.

Optimize for:

- clarity
- working end-to-end flow
- easy debugging
- low API cost
- simple architecture
- traceability

Do not over-engineer.

When something is ambiguous, choose the simplest implementation that preserves the architecture above and explain the decision in the README.
