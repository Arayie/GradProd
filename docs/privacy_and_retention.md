# Privacy, Data Governance & Retention Policy
## Data Governance Framework for Public Review Ingestion and AI Analytics
**Phase 0 Deliverable | Research Scope & Source Feasibility**  
**Document Version:** 1.0.0  
**Effective Date:** 2026-11-05  
**Compliance Scope:** India Digital Personal Data Protection (DPDP) Act 2023, App Store Platform Terms, Responsible AI Framework  

---

## 1. Foundational Architecture & Research Philosophy

The Groww AI-Powered Investor Discovery Engine is an **independent product research prototype** designed to uncover customer expectations, setup friction, and behavioral patterns surrounding Systematic Investment Plans (SIPs) by analyzing publicly accessible app store reviews.

### Core Legal & Analytical Axioms:
1. **Discovery Evidence, Not Ground Truth:** Public app store reviews represent *discovery signals* and *perceived customer sentiment*, not audited transactional behavior or verified financial account records. Public reviews must never be claimed as definitive proof of an individual's 12-month SIP retention or internal customer cohorts.
2. **Zero Internal Access:** The engine operates without access to Groww's internal transactional databases, core banking ledgers, KYC repositories, or customer support CRMs.
3. **Privacy by Design:** Public visibility of a review does not imply unrestricted license for profiling, de-anonymization, or identity linkage. All processing adheres to strict minimization principles.

---

## 2. Absolute Prohibitions

The following practices are **strictly prohibited** across all code, connectors, NLP models, and analytical reports:

> [!CAUTION]
> ### Strictly Prohibited Activities:
> 1. **No Reviewer Identity Resolution:** No attempt shall be made to uncover the real-world identity, email address, phone number, physical address, or legal identity of any reviewer.
> 2. **No Internal Account Matching:** No matching, cross-referencing, or probabilistic joining of app store review profiles with Groww customer accounts or financial records.
> 3. **No Inferred Demographics or Financial Status:** Demographic attributes (age, gender, income, religion, caste, geographic location, financial solvency) must **never** be inferred from usernames, avatars, writing styles, regional slang, or grammatical nuances. Segment fields default strictly to `UNKNOWN`.
> 4. **No Unauthorized Scraping:** No scraping of HTML pages, undocumented internal mobile endpoints, or anti-bot-protected web interfaces. Only approved RSS feeds, authorized APIs, and validated manual CSV exports may be ingested.
> 5. **No Security Boundary Bypass:** No automated bypassing of authentication gateways, CAPTCHA puzzles, Cloudflare shields, or platform rate limits.
> 6. **No AI Model Training Without Clear Title:** Review text shall not be used to pre-train or fine-tune public foundation models without explicit rights and licensing clearance. LLM interactions are restricted to zero-data-retention inference.
> 7. **No Synthetic Reviews in Production Analytics:** All analytical aggregates, sentiment clusters, and opportunity scoring models must derive solely from verified public records. Synthetic reviews or AI-hallucinated feedback are banned from analytics tables.

---

## 3. Data Minimization & Redaction Framework

Before any review is committed to persistent storage or made available to classification engines, it must pass through an automated **Sanitization and Redaction Pipeline**.

```
[Raw Ingestion Payload]
         │
         ▼
[PII Redaction Stage] ──► Strip author_name, author_uri, reviewer_id
         │
         ▼
[Regex Scrubbing]     ──► Redact phone numbers, emails, PANs, account numbers
         │
         ▼
[Clean Review Record] ──► Store review_id, text, rating, date, version
```

### 3.1 Field-Level Retention Rules

| Data Field | Collection Rule | Storage & Processing Treatment |
|---|---|---|
| **Author Name / Nickname** | **EXCLUDED** | Stripped at ingestion parser. Never written to SQLite, PostgreSQL, or Parquet files. |
| **Author Profile URI** | **EXCLUDED** | Stripped at ingestion parser. |
| **Platform Review ID** | **RETAINED** | Retained solely as an immutable cryptographic deduplication key. |
| **Review Title & Content** | **RETAINED** | Retained for NLP feature extraction and taxonomy classification. Preserves original script. |
| **Star Rating (1–5)** | **RETAINED** | Stored as integer for quantitative sentiment segmentation. |
| **Submission Timestamp** | **RETAINED** | Converted to UTC ISO 8601 string for longitudinal cohort grouping. |
| **App Version Code** | **RETAINED** | Retained to isolate regressions associated with specific releases. |
| **Storefront / Country** | **RETAINED** | Fixed to `IN` (India). |
| **Helpful Vote Count** | **RETAINED** | Stored as integer to gauge community resonance. |

### 3.2 Automated Regex PII Scrubbing
All review title and text fields are sanitized using strict regular expressions to detect and neutralize inadvertently posted confidential information:
- **Indian Mobile Numbers:** `(\+91[\-\s]?)?[6-9]\d{9}` -> replaced with `[PHONE_REDACTED]`
- **Email Addresses:** `[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+` -> replaced with `[EMAIL_REDACTED]`
- **PAN Card Numbers:** `[A-Z]{5}[0-9]{4}[A-Z]{1}` -> replaced with `[PAN_REDACTED]`
- **Bank Account Numbers:** Sequences of 9 to 18 continuous digits -> replaced with `[ACCOUNT_REDACTED]`
- **UPI Handles:** `[\w\.\-_]+@[\w]+` -> replaced with `[UPI_REDACTED]`

---

## 4. Language & Cultural Preservation

1. **Multilingual Script Integrity:** Reviews written in Devanagari script (Hindi) and Latin script (English, Hinglish) must be stored in their original encoding (`UTF-8`). 
2. **No Forced Machine Translation at Rest:** Original review text must not be permanently overwritten by automated English translations. Retaining the authentic voice of tier-2/3 Indian investors is essential for qualitative fidelity.
3. **Transliteration Heuristics:** In-line translation or phonetic normalization is permitted as a temporary intermediate step in RAM during LLM classification, but the source of truth remains the verbatim user submission.

---

## 5. Storage, Retention & Deletion Lifecycle

1. **Research Prototype Window:** Ingested review data is retained exclusively for the duration of the investor discovery research cycle (Phase 0 through Phase 4).
2. **Provider Deletion Obligations:** If a data provider (e.g., AppFollow, Apple) updates its syndication policies or requests data purging, cached datasets associated with that provider must be wiped within 30 calendar days.
3. **Isolated Encrypted Storage:** All database files (SQLite/DuckDB) and Parquet exports must reside within access-controlled workspace directories with local encryption at rest.
4. **Audit Trail Logging:** All ingestion jobs must log execution metadata (source endpoint, timestamp in UTC, records ingested, records dropped due to PII violations, and checksums). Logs must never print raw review contents or potential PII.

---

## 6. Secure Credential & Secret Management

1. **Zero Hardcoded Secrets:** No API tokens, AppFollow keys, Google Cloud service account JSON files, or Apple private keys (`.p8`) shall be committed to git repositories or markdown documentation.
2. **Environment Variables:** All authentication secrets must be supplied via environment variables (e.g., `APPFOLLOW_API_TOKEN`).
3. **Gitignore Protection:** The project `.gitignore` must explicitly block `.env`, `.env.*`, `*.pem`, `*.p8`, `*service_account*.json`, and credential caches.

---

## 7. AI Processing & Governance Boundaries

1. **Inference-Only Protocol:** LLM integration (e.g. Gemini, OpenAI) must operate under commercial zero-data-retention (ZDR) enterprise APIs where prompts are not logged for training.
2. **No Demographic Hallucination:** System prompts passed to LLMs must explicitly forbid guessing user demographics from vernacular phrasing or syntax.
3. **Grounded Attribution:** Every AI-generated finding, friction taxonomy tag, or opportunity score must maintain a strict traceable link back to anonymized review IDs.

---

## 8. Data Export & Sharing Restrictions

1. **No Raw Review Redistribution:** The project will not distribute raw bulk customer review datasets externally.
2. **Aggregated Reporting:** External reports, dashboards, and PRD recommendations must only display aggregated metrics, anonymized thematic summaries, or synthesized archetypes.
3. **Individual Review Quotes:** Any direct quote used in qualitative presentations must be manually reviewed to verify complete absence of identifying context or confidential financial details.
