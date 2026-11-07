# GROWWW – AI-POWERED INVESTOR DISCOVERY ENGINE
# SOURCE RUNBOOKS & FAILURE RECOVERY PROCEDURES
## Operational Runbook for Ingestion Connectors, Checkpoints, and Adverse Conditions

**Version:** 1.0.0 (Phase 7 Hardened)  
**Last Updated:** 2026-11-07  
**Scope:** Apple App Store Public RSS Connector, Manual CSV Importer, Checkpoint Recovery

---

## 1. Apple App Store RSS Connector (`ingestion/apple_app_store_rss.py`)

### 1.1 Overview & Architecture
- **Route Identifier:** `apple_app_store_public_rss`
- **Protocol:** Public RSS/Atom feed endpoint (`https://itunes.apple.com/in/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/xml`).
- **Cost Tier:** 100% Free Tier (Public RSS feed; requires zero API keys, subscriptions, or credit card authorizations).
- **Pagination Constraint:** Apple enforces a hard ceiling of 10 pages (~50 reviews per page, ~500 reviews maximum per app).
- **Page Cap Behavior:** Requesting page 11+ yields HTTP 400 Bad Request (`FeedCeilingReachedError`).

### 1.2 Failure Modes & Automated Recovery Procedures

| Adverse Event | Detection Trigger | Connector Behavior | Automated Recovery Action |
| :--- | :--- | :--- | :--- |
| **HTTP 401 Unauthorized** | Status 401 | Logs security alert; stops run | Terminal error; manual audit required. |
| **HTTP 403 Forbidden** | Status 403 | Logs permission denial; stops run | Back off; verify User-Agent string. |
| **HTTP 429 Rate Limit** | Status 429 | Inspects `Retry-After` header | Executes exponential backoff ($1.0 \times 2^{\text{attempt}}$) with jitter; max 3 retries before graceful abort. |
| **HTTP 500 / 503 Server Error** | Status 500-599 | Catches `HTTPError` | Retries up to 3 times; if failure persists, logs run as `FAILED` without losing previously committed pages. |
| **Socket Timeout (12s)** | `TimeoutError` | Caught safely | Retries with politeness delay; does not crash process. |
| **Malformed XML/JSON** | Parse exception | Caught safely | Discards corrupted page payload; skips to next page without DB corruption. |
| **Missing `entry` array** | Empty XML/JSON | Yields empty review list `[]` | Clean exit; records successful 0-yield page. |

### 1.3 Checkpoint Continuity & Incremental Fetching
- Database Table: `collection_checkpoints`
- Key Columns: `app_id`, `storefront`, `collection_method`, `last_successful_page`, `last_retrieval_timestamp`, `last_seen_review_id`.
- Checkpoints are updated **page-by-page**: if page 4 fails due to network drop, pages 1–3 remain safely committed in SQLite. Subsequent runs resume from page 4 rather than refetching pages 1–3.

---

## 2. Manual Review CSV Importer (`ingestion/manual_review_csv.py`)

### 2.1 Overview & Architecture
- **Route Identifier:** `google_play_manual_csv` / `competitor_manual_csv`
- **Cost Tier:** 100% Free Tier (Permitted CSV import; zero scraping of Google Play Store HTML).
- **Provenance Gate:** Every uploaded CSV requires explicit affirmative confirmation that records were legally obtained in compliance with privacy policies. Unconfirmed uploads trigger `SecurityViolationError`.

### 2.2 Schema Validation & Cleaning Rules (`core/csv_validator.py`)
- **Required Columns:** `review_text`, `review_date`, `rating` (aliases automatically mapped, e.g. `content` -> `review_text`, `stars` -> `rating`).
- **Disallowed Columns:** Discards `user_name`, `email`, `phone_number`, `author_name` at ingestion.
- **Out-of-Bounds Ratings:** Reviews with rating $< 1$ or $> 5$ are rejected and logged in `rejected_rows`.
- **Date Normalization:** Flexible date parser converts string timestamps to ISO 8601 UTC (`YYYY-MM-DD HH:MM:SS`).

---

## 3. Disallowed and Rejected Data Sources

### 3.1 AppFollow Exclusion Runbook
- **Status:** **PERMANENTLY REJECTED & DISABLED** (`permission_status: REJECTED`, `enabled: false` in `config/source_access.yml`).
- **Rationale:** AppFollow competitor review API requires a paid commercial plan ($149+/mo). Free-tier constraint strictly prohibits paid dependencies.
- **Enforcement:** `CommonIngestionService._check_access_gate` raises `SourcePermissionError` if AppFollow route invocation is attempted.
- **Zero Scraping:** No unofficial scraping libraries (`google-play-scraper`, `beautifulsoup4` HTML scrapers) are permitted or installed.
