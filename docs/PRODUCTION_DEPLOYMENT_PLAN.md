# Production Deployment Plan
# Infosys Social Value Initiative Generator

**Document Identifier:** INFOSYS-SV-DEPLOY-2026-V1  
**Document Version:** 1.0 (draft for review)  
**Date:** 19 November 2026

---

## 1. Document control

| Field | Value |
| --- | --- |
| Document | Production Deployment Plan |
| System | Infosys Social Value Initiative Generator |
| Version | 1.0 (draft for review) |
| Related documents | High-Level Design v2.0 (INFOSYS-SV-HLD-2026-V2), Low-Level Design v2.0, Client Handover Pack |
| Prepared by | Monk Spaces |
| Approved by | To be completed at sign-off |

**Purpose.** This plan describes how the Initiative Generator moves from its current proof-of-concept hosting to a production service on Microsoft Azure: the target setup, what must be in place first, the deployment and verification steps, how to roll back, and how the service is run afterwards.

**Scope.** Frontend, backend API, database, Azure OpenAI and their configuration. Not in scope: changes to the tool's features or AI behaviour, which follow the normal change process (branch, before/after comparison, approval).

---

## 2. Target production architecture

| Component | Service | Role |
| --- | --- | --- |
| Browser | Bid team | Signs in and uses the tool |
| Frontend | Azure Static Web App | Serves the React frontend |
| Backend API | Azure App Service `infosys-social-value` (B1) | FastAPI backend; the only component that holds secrets |
| Secrets | Azure Key Vault | AI keys, database password, JWT secret |
| Database | PostgreSQL with pgvector | Users, saved runs, documents, audit log |
| AI | Azure OpenAI, UK South: `gpt-4.1-mini` and `text-embedding-3-small` | Proposes initiatives; creates the vectors for evidence search |

The browser loads the frontend from Azure Static Web Apps and calls only the backend API. The backend is the single component that holds secrets and reaches the database and Azure OpenAI. All data and AI processing stay in Azure, UK South.

**Environments**

| Environment | Frontend | Backend | Database | Purpose |
| --- | --- | --- | --- | --- |
| Development | Local (Vite) | Local (uvicorn) | Development database | Building and testing changes |
| Staging (recommended) | Static Web Apps preview environment | App Service deployment slot `staging` | Separate database or branch | Checking a release before production |
| Production | Static Web App | App Service `infosys-social-value` | Production PostgreSQL | Client use |

The current Render and Vercel copies remain as a fallback during the first week, then are switched off.

---

## 3. Readiness gates before go-live

Each gate must be met, or explicitly accepted as a risk by the approver, before production use.

| # | Gate | Owner | Status |
| --- | --- | --- | --- |
| G1 | Azure subscription, resource group and budget alert in place | Infosys / Azure admin | Open |
| G2 | App Service plan scaled to B1 or higher, Always On enabled | Azure admin | Open |
| G3 | Azure OpenAI key and database password rotated; new values stored only in Key Vault or App Service settings | Azure admin | Open |
| G4 | Production database chosen (Neon paid plan or Azure Database for PostgreSQL with the `vector` extension) and backups confirmed | Azure admin | Open |
| G5 | Data residency agreed: AI runs in UK South; decide whether App Service and database must also be in the UK | Infosys | Open |
| G6 | All backend tests pass (123 at handover) and frontend lint and build pass on the release commit | Developer | Met at handover |
| G7 | Knowledge workbook reviewed by Infosys: TOM edition, track record, capability profile, contract name | Infosys | Open |
| G8 | Client user accounts and roles agreed (super-administrator, bid writers, reviewers) | Infosys | Open |
| G9 | Acceptance tests in section 6 passed on staging | Developer + Infosys | Open |
| G10 | Users briefed that every figure is reviewed by a person before it goes into a bid | Infosys | Open |

---

## 4. Security and configuration hardening

**Already in place**

- Sign-in required for every endpoint except health and sign-in; JWT sessions expire after 8 hours.
- Passwords stored as PBKDF2 hashes; no public sign-up — only a super-administrator creates users.
- AI keys and the database password live only on the server; the browser never holds a key or calls Azure OpenAI directly.
- Requests, errors, security events and AI model changes are written to the audit log, kept for 3 years.
- The AI's £ figures are removed; every value is calculated in code from the TOM tables.

**To do for production**

| Item | Action |
| --- | --- |
| Secrets | Store `AZURE_OPENAI_API_KEY`, `DATABASE_URL` and `JWT_SECRET_KEY` in Key Vault; reference them from App Service settings using a managed identity |
| Rotation | Rotate the Azure OpenAI key and the database password before go-live, and use new values for production |
| JWT secret | New random value of at least 32 characters, different from every other environment |
| First administrator | Use `INITIAL_ADMIN_EMAIL` / `INITIAL_ADMIN_PASSWORD` once, then remove both settings |
| Debug | `APP_ENV=production`, `DEBUG=False` |
| CORS | `CORS_ORIGINS` lists only the production frontend URL(s); remove `localhost` entries |
| HTTPS | App Service: HTTPS Only on, minimum TLS 1.2 |
| API docs page | Confirm whether the interactive API docs (`/docs`) should be reachable in production; restrict or turn off if not |
| Access to Azure | Least-privilege roles on the resource group; deployment through GitHub Actions only |

---

## 5. Deployment procedure

Code reaches Azure through GitHub Actions on every push to `main`: the backend repository deploys to App Service, the frontend repository builds and deploys to Static Web Apps. No manual upload is needed.

**One-time setup**

1. Scale the App Service plan to B1, turn on Always On, HTTPS Only and TLS 1.2.
2. Create the Key Vault, add the secrets, give the App Service a managed identity with read access.
3. Add the App Service settings: `LLM_PROVIDER=azure`, the four `AZURE_OPENAI_*` values (endpoint, key, deployment `gpt-4.1-mini`, API version `2025-01-01-preview`), `AZURE_OPENAI_TEMPERATURE=0.2`, `EMBEDDING_PROVIDER=azure`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small`, `DATABASE_URL`, `JWT_SECRET_KEY`, `APP_ENV=production`, `DEBUG=False`, `CORS_ORIGINS`.
4. Set the startup command to `bash startup.sh`.
5. Restart the App Service. Database tables are created automatically at start-up.
6. In the frontend repository, set the GitHub variable `VITE_API_URL` to the App Service URL and re-run the Static Web Apps workflow.
7. Create the first super-administrator, then remove the bootstrap settings.

**Every release after go-live**

1. Work on a branch; run backend tests and frontend lint and build.
2. For any change to AI behaviour, compare results before and after on 2–3 real tenders and get approval.
3. Merge to `main` — GitHub Actions deploys automatically.
4. Run the smoke checks in section 6.
5. Record the release (commit, date, what changed) in the release log.

---

## 6. Verification and acceptance tests

**Smoke checks (after every deployment, about 10 minutes)**

| # | Check | Expected result |
| --- | --- | --- |
| S1 | Open `<backend>/health` | `status: ok`, database connected, pgvector installed, `active_provider: azure` |
| S2 | Open the frontend URL | Sign-in page loads with no browser errors |
| S3 | Sign in as a test user | Lands on the Initiative Generator |
| S4 | Run one representative tender | Initiatives appear in about one minute; each card names "Azure OpenAI · gpt-4.1-mini" |
| S5 | Diagnostics, as super-administrator | AI model card shows Azure OpenAI `gpt-4.1-mini` |

**Acceptance tests (before go-live, with Infosys)**

| # | Test | Expected result |
| --- | --- | --- |
| A1 | Run 3 real past tenders | Initiatives relevant to each tender; values traceable to a TOM measure, quantity and proxy |
| A2 | Change a quantity under "How much" | Line value and totals update; "Suggested numbers" restores them |
| A3 | Untick an initiative | It stays on screen, folded, and leaves the total |
| A4 | A line marked "Check the quantity" | The warning explains the mismatch; the reviewer can correct the quantity |
| A5 | Choose a delivery partner and draft the bid response | Wording can be copied |
| A6 | Reopen a run from "Recent tenders" | The run reopens as saved |
| A7 | Upload, search and archive a past bid document | Passages appear in Evidence Search; archived documents are excluded |
| A8 | AI unavailable | With Azure OpenAI temporarily unavailable, the user sees a clear message, nothing is valued, and a retry works once it is back |
| A9 | Access control | A bid writer cannot open user creation or the AI model settings |
| A10 | Session expiry | After 8 hours the user is asked to sign in again |

---

## 7. Rollback plan

| Situation | Action | Time |
| --- | --- | --- |
| New release breaks something | Revert the commit on `main`; GitHub Actions redeploys the previous version. With a staging slot, swap the slots back instead | Minutes |
| Azure backend unavailable on go-live day | Point the frontend's `VITE_API_URL` back to the Render backend and re-run the frontend workflow | About 10 minutes |
| Azure OpenAI fails or is out of quota | Users retry; raise the quota or add a backup Azure OpenAI deployment in another UK region | Minutes to hours |
| Knowledge workbook import gives wrong values | Re-import the previous workbook version from Git | Minutes |
| Database problem | Restore from the provider's backup or point-in-time restore | Depends on provider |

**Rollback decision:** taken by the release owner if any smoke check fails and cannot be fixed within 30 minutes.

---

## 8. Operations after go-live

| Area | What | How often | Owner |
| --- | --- | --- | --- |
| Monitoring | Turn on Application Insights for the App Service; alert on HTTP 5xx errors and on `/health` failing | Continuous | Azure admin |
| AI usage and cost | Azure OpenAI token metrics and the subscription budget alert | Monthly review | Infosys |
| Audit log | Review sign-ins, errors and AI model changes in Diagnostics | Monthly | Super-administrator |
| Backups | Confirm database backups exist and test one restore | Quarterly | Azure admin |
| Secrets | Rotate the AI keys, database password and JWT secret | Every 90 days, and at once if exposed | Azure admin |
| Users | Add and remove users; remove leavers the same week | As needed | Super-administrator |
| Knowledge | Re-import the workbook when the track record, capability profile or pattern library changes | As needed | Developer, on Infosys request |
| TOM edition | Import the new Open Access TOM edition and review the value changes | Yearly | Developer + Infosys |
| AI model | Check the Azure OpenAI model retirement dates and move to the successor model with a before/after comparison | Twice a year | Developer |
| Dependencies | Update libraries and re-run all tests | Quarterly | Developer |

**Support:** issues are reported to the agreed Monk Spaces contact with the tender, the time and a screenshot; never with passwords or keys.

---

## 9. Known limitations, risks and sign-off

**Known limitations at go-live**

| Limitation | Effect | Planned improvement |
| --- | --- | --- |
| The AI writes the final quantity itself | Some quantities do not match their stated basis; these are flagged "Check the quantity" | Code calculates quantities from the AI's parts |
| Thin knowledge base: 0 patterns, track record from one contract, 2 past bid documents | Initiatives can be generic and vary between runs | Pattern library and more track record from Infosys |
| Regional partners are not given to the AI | Partners are suggestions until the user chooses | Send the approved partner list |
| Reviewer role has the same access as a bid writer; saved runs are private to each user | No formal review or sharing workflow | Review permission and shared runs |
| Users are created through the API only | Needs a developer or super-administrator | User management page |
| Database tables are created at start-up, without versioned migrations | Schema changes need care | Add migrations before the first schema change |
| Delivery cost per initiative is blank by design | Cost must be added by Infosys | — |

**Risks**

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| AI model retired by Microsoft | Medium | Twice-yearly model check; move to the successor with a before/after comparison |
| Unrealistic figure reaches a bid | Medium | Quantity and target checks; human review of every figure |
| Key exposure | Low after rotation | Key Vault, 90-day rotation |
| Cost overrun | Low | Budget alert; small model (`gpt-4.1-mini`) |
| Azure OpenAI outage | Low | Clear error and retry; optional backup deployment |

**Sign-off**

| Role | Name | Decision | Date |
| --- | --- | --- | --- |
| Infosys business owner |  | Approve / Approve with risks / Reject |  |
| Infosys IT / security |  |  |  |
| Monk Spaces delivery lead |  |  |  |
