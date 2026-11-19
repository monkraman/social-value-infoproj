# High-Level Design (HLD) Document
# Infosys Social Value Initiative Generator

**Document Identifier:** INFOSYS-SV-HLD-2026-V2  
**Document Version:** 2.0.0 (supersedes 1.0.0, which described the earlier RFP Response Builder)  
**Status:** Proof of concept at handover  
**Audience:** Enterprise architects, IT and security, bid directors, lead engineers  
**Date:** 18 November 2026

---

## Summary

| Attribute | At handover |
| :--- | :--- |
| **System** | Social Value Initiative Generator |
| **Purpose** | Propose social value initiatives for a UK public sector tender and value them with the TOM System |
| **Frameworks** | PPN 06/20 (Social Value Model), PPN 002, PPN 026 |
| **Value tables** | Open Access TOM System, 2025 edition, imported from the Monk Spaces knowledge workbook |
| **Frontend** | React 19, TypeScript, Vite |
| **Backend** | Python, FastAPI, SQLAlchemy |
| **Database** | PostgreSQL with pgvector (1,536-dimension vectors) |
| **AI** | Azure OpenAI (UK South): gpt-4.1-mini for proposals, text-embedding-3-small for document search |
| **Security** | JWT sign-in (8-hour sessions), PBKDF2 password hashing, three roles, audit log kept 3 years |

The governing design rule: **the AI proposes, the code calculates.** The AI chooses initiatives and quantities. Every pound value comes from the TOM tables through deterministic code, and every AI claim that can be checked is checked before it reaches the user.

---

## 1. Business Context

### 1.1 The problem
UK public sector tenders score social value under PPN 06/20 and its successors, typically 10% or more of the evaluation. A bid team has to propose credible commitments, map them to the award criteria the buyer scores (Model Award Criteria, MACs), quantify them with TOM measures, and evidence them with past delivery. Done by hand, this takes days per bid and the numbers are hard to defend.

### 1.2 What the tool delivers
- A first set of initiatives for a tender in about one minute, sized to the social value target (contract value × social value weighting).
- A £ value for every initiative that can be traced to a TOM measure, a quantity and a published proxy.
- Checks that flag what a reviewer must confirm: criteria the initiative does not serve, citations that do not match, quantities that do not add up.
- Evidence from Infosys's own track record and past bid documents.
- A first-draft bid paragraph per initiative.

### 1.3 Out of scope at this stage
- Delivery cost of each initiative (left blank by design for Infosys to complete).
- Submitting anything to a buyer. The tool drafts; people decide and submit.

---

## 2. Architectural Principles

| Principle | How it is applied |
| :--- | :--- |
| **AI proposes, code calculates** | The AI output contract has no £ fields. Any £ amount the AI writes is removed. Values = units × proxy from the tables. |
| **Single source of facts** | TOM measures, proxies, localisation factors, the track record and the capability profile come from one workbook, imported into `tables.json`. |
| **Check every checkable claim** | Claimed criteria, cited past work, measure codes and quantities are validated in code. |
| **Additive safeguards** | A check either corrects the output with a visible note or warns; it never silently drops an initiative. |
| **Keys stay on the server** | The browser never holds an AI key or calls an AI provider. |
| **Provider independence** | The AI model is configuration. A second Azure OpenAI deployment can be added as a backup and is tried automatically on quota or outage. |
| **Explainability** | Each card shows where its values, criteria, evidence and model came from. |

---

## 3. System Context

| Actor or system | Interaction |
| :--- | :--- |
| Bid writer (`bid_author`) | Describes a tender, runs the generator, edits quantities, chooses partners, copies wording |
| Reviewer (`reviewer`) | Same access as a bid writer today; a separate review permission is not yet enforced |
| Super-administrator (`superadmin`) | Creates users, chooses the primary AI model, reviews the audit log |
| Azure OpenAI | Receives the tender, tables and rules; returns proposed initiatives as JSON; creates embeddings for document search |
| Knowledge workbook | Source of TOM tables, track record, capability profile and Measure-to-MAC map, imported by a script |

---

## 4. Containers

| Container | Responsibility | Technology |
| :--- | :--- | :--- |
| **Frontend** | Tender entry (prompt or form), framework and criteria selection, buyer document upload, initiative cards, editing, saved runs, administration panel | React 19, TypeScript, Vite; static files |
| **Backend API** | Authentication and roles, prompt building, AI calls, valuation and checks, evidence search, document ingestion, run history, audit | Python, FastAPI, SQLAlchemy |
| **Database** | Users, saved runs, documents and their vector index, audit log, settings | PostgreSQL with pgvector |
| **Knowledge files** | TOM tables, rules, initiative types | JSON and Markdown in the backend repository |
| **AI service** | Text generation and embeddings | Azure OpenAI (UK South) |

The frontend talks only to the backend, over HTTPS with a JWT bearer token. The backend is the only component that reaches the database and Azure OpenAI.

---

## 5. Core Subsystems

### 5.1 Tender intake
The user writes the tender in a sentence or fills a form. A deterministic parser (no AI) reads buyer, value, weighting, years, region and framework from the sentence and reports what it could not find. Buyer documents (PDF, Word, Excel, text) are read on the server and discarded; the buyer's stated priorities are passed to the AI.

### 5.2 Prompt builder
Builds one request from: the tender; the valid TOM measures with a sizing proxy each; the Infosys track record (cite by ID, never re-propose); the capability profile; the 19 initiative type labels; the Measure-to-MAC map for the chosen framework; and the rules in `rules.md`. The output contract fixes the JSON shape the AI must return.

### 5.3 AI gateway
Calls the configured Azure OpenAI deployment. If a backup deployment is configured, it is tried automatically on failure; if none answers, the user sees the reason. A super-administrator can choose the primary deployment from the diagnostics panel. The result records which model answered.

### 5.4 Valuation and checks
Pure functions with no database or network access, so every rule is unit-tested. For each line: validate the measure, apply caps (A-06, NT1, supply-chain spend), compute units × localised proxy, apply A-07 (one employment measure per group of people) and A-13 (carbon is conditional). Then validate claimed criteria (A1, A2), citations (D2), and quantities against their stated basis; remove £ figures from text; and compare the total with the target.

### 5.5 Evidence search
Uploaded past bids are split into passages of about 800 characters, embedded and stored in pgvector. After valuation, each initiative's name and description is searched; passages scoring at least 0.6 similarity are attached, at most two per initiative and each passage to only its best-matching initiative. Evidence never changes what is proposed or valued.

### 5.6 Run history and administration
Each run is saved with its full state so a user can reopen it. A super-administrator chooses the primary AI model from the diagnostics panel; the choice (never a key) is stored in the database and audit-logged.

---

## 6. End-to-End Flow

1. The user signs in; the frontend stores the JWT.
2. The frontend loads the knowledge summary and form options from the backend.
3. The user enters the tender, picks the framework and criteria, and optionally uploads buyer documents (text extracted by the backend).
4. **Ask the AI** sends the tender to `/generator/run`.
5. The backend builds the prompt and calls the AI gateway; Azure OpenAI answers with JSON.
6. The valuation layer values and checks every initiative and adds the curated Infosys fit rating.
7. Evidence search attaches supporting passages.
8. The frontend shows the cards, totals and checks; the user edits quantities and partners and copies wording.
9. The run is saved to `/generator/runs`.

If Azure OpenAI is unavailable, step 5 returns HTTP 503 with the reason and nothing is valued.

---

## 7. Data Architecture

| Store | Content | Notes |
| :--- | :--- | :--- |
| `users` | Accounts, role, password hash | No public sign-up |
| `generator_runs` | Saved runs: tender, totals, full result state | Visible only to the user who saved them |
| `documents`, `document_chunks` | Past bid documents and their embedded passages | Archived documents are excluded from search |
| `system_audit_logs` | Requests, errors, security and settings events | Retained 3 years (1,095 days) |
| `app_settings` | The chosen primary AI model | Choice only, never a key |
| `regional_partners`, `toms_metrics` | Reference data for the Regional Partners and TOMs Catalog pages | Not yet used by the generator |
| `prompt_history` | History of the earlier prompt-based builder | Retained for reference |
| `tables.json` | TOM measures, proxies, localisation, track record, capability profile, Measure-to-MAC map | Generated from the workbook; versioned in Git |

---

## 8. Non-Functional Requirements

| Attribute | Design response |
| :--- | :--- |
| **Accuracy** | All £ values computed in code from versioned tables; AI £ figures removed |
| **Traceability** | Each line shows measure, units, basis, proxy and its source; each card names the AI model |
| **Availability of AI** | Clear error and retry when Azure OpenAI is unavailable; optional backup deployment |
| **Data residency** | Azure OpenAI deployed in UK South |
| **Security** | Keys only in server settings; JWT with 8-hour expiry; role checks on every protected endpoint |
| **Auditability** | Request and security events logged with user, time and outcome; AI model changes recorded |
| **Response time** | About one minute per generation, dominated by the AI call |
| **Testability** | 123 automated backend tests; valuation rules are pure functions |

---

## 9. Deployment

| Environment | Frontend | Backend | Database |
| :--- | :--- | :--- | :--- |
| Proof of concept (current) | Static hosting | Render web service | Managed PostgreSQL (Neon) |
| Target | Azure Static Web Apps | Azure App Service `infosys-social-value` | Azure Database for PostgreSQL or the current managed PostgreSQL |

GitHub Actions deploy on every push to `main`: the backend to Azure App Service and the frontend to Azure Static Web Apps. Configuration is supplied as environment variables (see the LLD and `.env.example`); in Azure, secrets belong in Key Vault. Database tables are created when the backend starts.

---

## 10. Risks and Mitigations

| Risk | Mitigation in place | Further action |
| :--- | :--- | :--- |
| AI proposes unrealistic quantities | Quantity check flags lines whose units do not match their basis or exceed the contract's weeks; target check flags totals above 150% | Have the AI return the parts and let code multiply |
| AI names a partner Infosys has not agreed with | Partner is a suggestion; nothing is named until the user chooses | Give the AI the regional partner list |
| Azure OpenAI quota or outage | Clear error; the user retries | Add a backup Azure OpenAI deployment in a second UK region |
| Thin knowledge base weakens evidence | Evidence threshold hides weak matches | Add past bids, track record and measures |
| Key exposure | Keys only on the server; rotation process | Move secrets to Key Vault |
| TOM edition changes | Yearly re-import script with a reviewable diff | Assign an owner for the yearly update |
