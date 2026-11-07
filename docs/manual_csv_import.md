# Manual Review CSV Import Specification (Route B)
**Module:** `ingestion/manual_review_csv.py`  
**Status:** PRODUCTION READY (Phase 2 Two-Store Ingestion MVP)  
**Route Code:** `ROUTE_B`  
**Primary Platform Target:** Google Play Competitor Review Ingestion  
**Approval Reference:** `PHASE2-AUDIT-MANUAL-CSV-006`

---

## 1. Purpose & Source Strategy Context

Because Google Play HTML scraping and undocumented APIs are strictly prohibited by data governance policy, and AppFollow was rejected due to mandatory paid subscription requirements, **Route B (Manual CSV Import)** serves as the primary route for ingesting Google Play customer reviews across competitor applications and historical archives.

### Ingestion Flow:
```
Uploaded CSV 
   │
   ▼
1. Structural Inspection & Column Alias Auto-Detection
   │
   ▼
2. Disallowed Identifiers Check (Blocks usernames, reviewer IDs)
   │
   ▼
3. Indian PII Regex Redaction (Phones, PANs, UPI IDs, Emails)
   │
   ▼
4. Legal Provenance Certification (Mandatory user confirmation)
   │
   ▼
5. Multi-Level Canonical Deduplication
   │
   ▼
6. SQLite Canonical Persistence (`reviews` & `ingestion_runs`)
```

---

## 2. Canonical Column Specification

The import engine accepts flexible CSV structures and automatically maps common column aliases.

### Required Fields:
| Canonical Field | Type | Accepted Aliases | Description |
| :--- | :--- | :--- | :--- |
| `review_text` | String | `content`, `text`, `comment`, `review`, `body` | The raw text of the customer review. Cannot be empty. |
| `review_date` | Date/Timestamp | `date`, `created_at`, `timestamp`, `review_timestamp` | Submission date (ISO-8601, `YYYY-MM-DD`, or `DD/MM/YYYY`). |
| `rating` | Integer | `star_rating`, `score`, `stars`, `user_rating` | Numeric score between 1 and 5. |

### Optional Fields:
| Canonical Field | Type | Accepted Aliases | Description |
| :--- | :--- | :--- | :--- |
| `review_title` | String | `title`, `headline`, `subject` | Review header or summary line. |
| `review_id` | String | `id`, `source_id`, `review_id` | Platform record ID for idempotency. |
| `app_version` | String | `version`, `version_name`, `app_version` | App release version at time of review. |
| `storefront` | String | `country`, `market`, `territory` | Country code (defaults to `IN`). |

---

## 3. Data Governance & Privacy Invariants

### 3.1 Prohibited Columns
If an uploaded CSV contains any of the following column names, the file is **immediately rejected** before processing:
- `user_name`, `reviewer_name`, `author_name`, `author`
- `email`, `user_email`
- `phone`, `mobile_number`
- `customer_id`, `user_id`, `account_number`
- `profile_url`, `author_uri`, `avatar`

### 3.2 Automated Indian PII Regex Sanitization
Every review text is scanned for sensitive Indian identity and financial tokens:
- **Indian Mobile Numbers:** `(\+91[\-\s]?)?[6789]\d{9}` -> Replaced with `[PHONE_REDACTED]`
- **Email Addresses:** `[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+` -> Replaced with `[EMAIL_REDACTED]`
- **UPI IDs:** `[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}` -> Replaced with `[UPI_REDACTED]`
- **Indian PAN Cards:** `[A-Z]{5}[0-9]{4}[A-Z]{1}` -> Replaced with `[PAN_REDACTED]`
- **Bank Account Sequences:** Sequence of 9-18 consecutive digits -> Replaced with `[ACCOUNT_REDACTED]`

If redactions occur, `redaction_status` is updated from `CLEAN` to `REDACTED`.

### 3.3 Mandatory Provenance Sign-Off
Before any record is persisted, the custodian must affirm:
- Certified origin from legitimate public archives, academic datasets, or authorized internal feedback dumps.
- Zero confidential customer account records.
- If unconfirmed, the ingestion pipeline aborts with `SecurityViolationError`.
