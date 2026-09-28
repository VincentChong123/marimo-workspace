# Multi-Dimensional Architecture Review: LLM-to-Dashboard 3-Tier Plans

**Target Plans Reviewed**: 
* [`secure_google_sheet_github_io_guardrail_plan.md`](./secure_google_sheet_github_io_guardrail_plan.md)
* [`otel_telemetry_google_firestore_audit_plan.md`](./otel_telemetry_google_firestore_audit_plan.md)

**Review Standards Applied**: 
* `multi-reviewer-patterns`: Multi-dimensional review, severity calibration, deduplicated reporting.
* `stride-analysis-patterns`: Systematic threat modeling (Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation of Privilege).
* `architecture-decision-records`: Structural decoupling, trust boundaries, failure modes.

---

## 1. Executive Assessment

The 3-tier architecture proposed across the two plans is **conceptually outstanding**:
1. **Tier 1 (Presentation / Compute):** Marimo WASM on `github.io` offloads 100% of compute to the client browser at $0 server cost.
2. **Tier 2 (AI Intelligence):** The LLM is restricted to emitting declarative JSON specifications rather than raw executable Python, effectively eliminating Remote Code Execution (RCE) vulnerabilities.
3. **Tier 3 (Data & State Storage):** Unifying on Google Cloud (Google Sheets, Firestore, BigQuery) under the Always Free Tier avoids multi-cloud fragmentation and keeps compliance inside a single legal boundary (Google DPA).

However, this review identified **several critical and high-priority architectural gaps** across trust boundaries, authentication, and client-to-cloud security that must be addressed before production implementation.

---

## 2. Detailed Findings by Severity

### Critical Findings (1)

#### [CR-001] Client-Side GCP Credential Leakage vs. API Gateway Boundary
* **Location**: `otel_telemetry_google_firestore_audit_plan.md:125-146`, `173-197`
* **Dimension**: **Security & Architecture** (Elevation of Privilege / Information Disclosure)
* **Description**: The plan includes code snippets where `google.cloud.firestore` and `google.cloud.bigquery` client libraries are invoked (`firestore.Client()`, `bigquery.Client()`). Because Tier 1 runs client-side inside the user's browser via WebAssembly (Pyodide), the browser **cannot and must not hold GCP Service Account credentials**. Exposing service account keys in a browser bundle allows any visitor to extract full write/admin access to your Google Cloud project.
* **Impact**: Total compromise of GCP project resources, potential data exfiltration, or billing exhaustion.
* **Fix**: Enforce the **Cloud Run API Gateway (`apps/api_gateway`)** as the mandatory Tier 2 trusted proxy:
  * Client (Browser WASM) $\xrightarrow{\text{User OAuth JWT}}$ Cloud Run Gateway $\xrightarrow{\text{GCP IAM Service Account}}$ Firestore / BigQuery.
  * The browser client only calls your authenticated Cloud Run endpoints (`POST /api/v1/layout`, `POST /api/v1/audit`), never GCP directly.

---

### High Findings (3)

#### [HI-001] User Identity Spoofing in Audit & Layout Payloads
* **Location**: `otel_telemetry_google_firestore_audit_plan.md:130-136`, `181-192`
* **Dimension**: **Security (STRIDE: Spoofing)**
* **Description**: The layout save function (`save_user_layout(sheet_id, user_email, layout_spec)`) and audit logging accept `user_email` as a plain unverified parameter from the request payload. In a multi-user environment, a malicious or curious user can spoof `user_email = "boss@company.com"`, overwriting another user's dashboard layout or generating forged compliance audit trails.
* **Impact**: Integrity violation of audit logs and layout persistence; inability to prove non-repudiation in an audit.
* **Fix**: The backend (Cloud Run API Gateway) must extract the user's identity directly from the cryptographically verified Google Workspace OAuth Bearer token (`claims["email"]`), completely ignoring any client-supplied `user_email` field in the request body.

---

#### [HI-002] Public Google Sheet Export in Enterprise Environments
* **Location**: `secure_google_sheet_github_io_guardrail_plan.md:128-132`
* **Dimension**: **Security & Architecture** (Information Disclosure)
* **Description**: The data loader uses `https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv`. This direct export URL only works if the Google Sheet is shared as **"Anyone with the link can view"**. For confidential enterprise/financial data, sheets are private. In private mode, this fetch returns an HTTP 302/401 redirect to Google login, which fails silently in browser Python.
* **Impact**: The dashboard fails for private Google Sheets, or forces organizations to make confidential sheets publicly accessible to work.
* **Fix**: Implement a dual-mode loader:
  1. *Public mode*: Direct CSV export (for demos/public datasets).
  2. *Enterprise mode*: Browser prompts for 1-click Google Sign-In using Google Identity Services (GIS), acquiring a temporary OAuth token, and passes `headers={"Authorization": "Bearer " + access_token}` when fetching the Google Sheets API v4 endpoint.

---

#### [HI-003] Unauthenticated Write-Back Webhook (Apps Script)
* **Location**: `secure_google_sheet_github_io_guardrail_plan.md:201-236`
* **Dimension**: **Security (STRIDE: Tampering)**
* **Description**: The Google Apps Script webhook `doPost(e)` is configured with *"Who has access: Anyone"*. Anyone who discovers the webhook URL (it is visible in browser network traffic) can send arbitrary POST requests and overwrite the `_metadata` layout configuration of the Google Sheet without authentication.
* **Impact**: Vandalism of dashboard layouts by external actors.
* **Fix**: Add a shared secret authorization header (e.g. `X-Webhook-Secret`) checked inside `doPost(e)`:
  ```javascript
  if (e.parameter.secret !== SCRIPT_PROPERTIES.getProperty("WEBHOOK_SECRET")) {
    return ContentService.createTextOutput("Unauthorized").setMimeType(ContentService.MimeType.TEXT);
  }
  ```
  Or restrict the Google Apps Script deployment to **"Anyone within [Your Domain]"**.

---

### Medium Findings (3)

#### [MD-001] Client-Side Cache Invalidation on Sheet Updates
* **Location**: `secure_google_sheet_github_io_guardrail_plan.md:128-131`
* **Dimension**: **Architecture & Reliability**
* **Description**: The data loader uses `@mo.cache` without a cache invalidation or TTL strategy. When a user adds rows in Google Sheets, refreshing the browser may serve the stale cached DataFrame.
* **Impact**: Users see outdated data even after updating the spreadsheet.
* **Fix**: Add an explicit "Refresh Data" action button in the Marimo UI (`refresh_btn = mo.ui.button(label="🔄 Refresh Data")`) that triggers a cache-busting timestamp query parameter (`&_t={time.time()}`).

---

#### [MD-002] BigQuery PII Retention in Prompts (GDPR / Right to be Forgotten)
* **Location**: `otel_telemetry_google_firestore_audit_plan.md:155-171`
* **Dimension**: **Data Governance & Compliance**
* **Description**: While the plan correctly sanitizes OTEL traces, BigQuery stores the raw `natural_prompt STRING`. If an employee types: *"Show sales for customer John Smith (SSN: 000-11-2222)"*, that raw PII is now permanently stored in the BigQuery audit log. Under GDPR Article 17 ("Right to be Forgotten"), you cannot easily delete individual rows from an immutable log.
* **Impact**: Potential compliance breach during privacy data erasure requests.
* **Fix**: Apply client-side regex redaction to the natural language prompt *before* streaming to BigQuery, or assign BigQuery Policy Tags (Column-level encryption) to the `natural_prompt` column with restricted access.

---

#### [MD-003] Free Tier Quota Exhaustion (Denial of Service)
* **Location**: `otel_telemetry_google_firestore_audit_plan.md:92-98`
* **Dimension**: **Performance & Cost Optimization**
* **Description**: Google Cloud Firestore free tier allows **20,000 writes/day**. If multiple users or an automated loop updates layouts repeatedly, writes could exceed the free limit, causing unexpected billing or write rejections.
* **Impact**: Temporary inability to save dashboard layouts once the daily free quota is exceeded.
* **Fix**: Add client-side debouncing (e.g., save only after 3 seconds of inactivity) and enforce an API Gateway rate limit (e.g., maximum 30 layout saves per user/hour).

---

### Low Findings (2)

#### [LO-001] Absence of JSON Schema Formal Validation Library
* **Location**: `secure_google_sheet_github_io_guardrail_plan.md:161-190`
* **Dimension**: **Architecture (Code Quality)**
* **Description**: The parser validates JSON via manual dictionary lookups (`spec.get("x")`, `spec.get("charts")`).
* **Fix**: Use Pydantic or `jsonschema` (which runs in Pyodide WASM) to validate the layout JSON against a formal schema, generating descriptive validation error toasts if the LLM hallucinates malformed keys.

#### [LO-002] OTEL GenAI Semantic Conventions Version Drift
* **Location**: `otel_telemetry_google_firestore_audit_plan.md:64-75`
* **Dimension**: **Architecture (Observability Standards)**
* **Description**: The attributes use custom names like `prompt.char_length` and `latency.ms` instead of OpenTelemetry's official GenAI Semantic Conventions (`gen_ai.usage.input_tokens`, `gen_ai.operation.name`).
* **Fix**: Align strictly with OpenTelemetry 1.27+ GenAI semantic attributes.

---

## 3. Consolidated Review Summary

| Dimension | Critical | High | Medium | Low | Total |
|---|---|---|---|---|---|
| **Security (STRIDE)** | 1 | 3 | 0 | 0 | **4** |
| **Architecture & Reliability** | 0 | 0 | 2 | 2 | **4** |
| **Performance & Cost** | 0 | 0 | 1 | 0 | **1** |
| **Data Governance & Compliance** | 0 | 0 | 1 | 0 | **1** |
| **Total** | **1** | **3** | **4** | **2** | **10** |

---

## 4. Actionable Architecture Recommendation

To achieve a production-grade 3-tier system, the final implementation should enforce this **Clean Trust Boundary**:

```
[ Tier 1: Client Web Browser (github.io) ]
  • Runs Marimo WASM (Zero secrets, zero GCP keys).
  • Reads public/OAuth Google Sheet via browser fetch.
  • Authenticates user via Google Workspace OAuth2 (Google Identity Services).
             │
             │ HTTPS + Bearer JWT
             ▼
[ Tier 2: Trusted Cloud Run Gateway (apps/api_gateway) ]
  • Cryptographically validates Google JWT (extracts authentic user email).
  • Enforces rate limiting & PII scrubbing.
  • Calls Gemini AI with guardrailed prompt.
             │
             │ Internal GCP IAM (Service Account)
             ▼
[ Tier 3: Managed Storage (Google Cloud) ]
  • Firestore: Saves user layout JSON under verified user ID.
  • BigQuery: Streams non-sampled audit rows into partitioned table.
  • Google Sheet: Holds raw business data & acts as tabular data entry.
```
