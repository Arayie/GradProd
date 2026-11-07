# Growww AI-Powered Investor Discovery Engine
# Canonical Data Dictionary (Phase 3)

**Schema Version:** 1.3.0  
**Last Updated:** 2026-11-06  
**Target Repository:** `growww_discovery.db` (Table: `reviews`)  
**Export Files:** `master_investor_feedback.csv`, `master_investor_feedback.parquet`, `outputs/sip_relevant_reviews.csv`, `outputs/general_investment_reviews.csv`

---

## 1. Overview & Data Architecture

The Growww Investor Discovery Engine standardizes public customer reviews from Apple App Store (syndication RSS) and Google Play Store (manual CSV imports) into a common, privacy-compliant, research-ready relational schema. 

The schema separates:
1. **Raw Source Provenance** (immutable audit information).
2. **Normalized Derived Content** (standardized Unicode text, PII redactions).
3. **Multilingual NLP Metadata** (detected script, code-switching, confidence).
4. **SIP Relevance Screening Signals** (deterministic category matches and 15 boolean coverage flags).
5. **Deduplication & Clustering Identifiers** (source ID, exact content hash, near-duplicate candidate groups).
6. **Data Quality & Governance Dimensions** (quality score, retention lifecycle, eligibility).

---

## 2. Field Specifications

### 2.1 Identity & Provenance Attributes

| Field Name | Data Type | Nullable | Description & Formatting Rules | Example |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `INTEGER` | No | Internal auto-incrementing SQLite primary key (excluded from research exports). | `42` |
| `evidence_id` | `TEXT` | No | Global unique research evidence identifier formatted as `EV_{APP[:4]}_{STORE[:3]}_{HASH[:8]}`. | `EV_GROW_APP_4e23bba6` |
| `store` | `TEXT` | No | Canonical platform name: `apple_app_store` or `google_play`. | `apple_app_store` |
| `app_id` | `TEXT` | No | Internal canonical application identifier registered in `config/apps.yml`. | `groww` |
| `app_name` | `TEXT` | Yes | Official registered application title. | `Groww Stocks, Mutual Fund, IPO` |
| `package_name` | `TEXT` | Yes | Google Play Android package name if applicable. | `com.nextbillion.groww` |
| `source_record_id` | `TEXT` | Yes | Platform-specific review identifier (Apple review ID or Google review ID). | `14750020582` |
| `canonical_url` | `TEXT` | Yes | Permanent web or store URL referencing the review or application listing. | `https://apps.apple.com/in/app/id1404871703` |
| `collection_run_id` | `TEXT` | Yes | Reference to the execution session in `ingestion_runs`. | `RUN_GROW_APP_FD3B2FFF` |
| `collection_method` | `TEXT` | No | Method of collection: `apple_app_store_rss` or `manual_csv_import`. | `apple_app_store_rss` |
| `source_permission_id`| `TEXT` | Yes | Reference to data governance audit clearance. | `PHASE2-AUDIT-APPLE-RSS-001` |
| `retrieved_at` | `TIMESTAMP`| No | UTC timestamp when the review was fetched or imported (`YYYY-MM-DD HH:MM:SS`). | `2026-11-06 04:54:51` |

---

### 2.2 Review Content & NLP Normalization

| Field Name | Data Type | Nullable | Description & Formatting Rules | Example |
| :--- | :--- | :---: | :--- | :--- |
| `review_title` | `TEXT` | Yes | Normalized review title (HTML decoded, control whitespace stripped). | `SIP Autopay failed` |
| `review_text_original`| `TEXT` | No | Immutable original raw review text exactly as captured from source feed. | `My SIP <br> failed!` |
| `review_text` | `TEXT` | No | Normalized, NFKC Unicode decoded, PII-sanitized review body text. | `My SIP failed!` |
| `language_original` | `TEXT` | No | Source feed declared language tag (defaults to `unknown`). | `unknown` |
| `language_detected` | `TEXT` | No | Algorithmic language classification: `en`, `hi`, `hi-Latn`, `mixed`, `other`, `unknown`. | `hi-Latn` |
| `language_confidence`| `REAL` | No | Confidence score of language detection (0.00 to 1.00). | `0.95` |
| `script_detected` | `TEXT` | No | Dominant script: `LATIN`, `DEVANAGARI`, `MIXED`, `OTHER_INDIC`, `UNKNOWN`. | `LATIN` |
| `language_detection_method`| `TEXT` | No | Identifier of the detection algorithm. | `heuristic_lexical_script_v1` |
| `translated_text` | `TEXT` | Yes | Reserved for Phase 4 machine translation if enabled (currently `NULL`). | `NULL` |
| `content_hash` | `TEXT` | No | SHA-256 digest of whitespace-collapsed lowercase normalized text. | `4e23bba620ffd...` |
| `content_status` | `TEXT` | No | Processing status: `NORMALIZED` or `EMPTY`. | `NORMALIZED` |
| `redaction_status` | `TEXT` | No | PII scrubbing status: `CLEAN` or `REDACTED`. | `CLEAN` |
| `redaction_categories`| `TEXT` | Yes | JSON array of detected PII types (e.g. `["phone", "email"]`). | `[]` |
| `pii_processed_at` | `TIMESTAMP`| Yes | UTC timestamp of PII minimization execution. | `2026-11-06 16:47:00` |

---

### 2.3 Storefront Metadata & Timestamps

| Field Name | Data Type | Nullable | Description & Formatting Rules | Example |
| :--- | :--- | :---: | :--- | :--- |
| `storefront` | `TEXT` | No | Storefront country ISO code (default: `IN`). | `IN` |
| `app_version` | `TEXT` | Yes | Semantic application version reported by reviewer. | `18.22.0` |
| `star_rating` | `INTEGER` | No | Validated customer star rating (integer between 1 and 5). | `1` |
| `developer_reply_present`| `INTEGER`| No | Binary flag (0 or 1) indicating if developer reply was published. | `0` |
| `review_created_at` | `TIMESTAMP`| No | Standardized UTC review creation timestamp (`YYYY-MM-DD HH:MM:SS`). | `2026-11-04 13:49:50` |
| `review_updated_at` | `TIMESTAMP`| Yes | UTC timestamp of customer review modification if provided. | `NULL` |
| `provider_name` | `TEXT` | Yes | Sourcing entity name. | `Apple Inc.` |
| `store_listing_url` | `TEXT` | Yes | Canonical application web listing URL. | `https://apps.apple.com/...` |
| `provider_limit_snapshot`| `TEXT`| Yes | Technical capacity note (e.g. `10_pages_500_max`). | `NULL` |

---

### 2.4 SIP Relevance Screening & Coverage Flags (Phase 3)

| Field Name | Data Type | Nullable | Description & Values | Example |
| :--- | :--- | :---: | :--- | :--- |
| `sip_relevance_status`| `TEXT` | No | Preliminary screening status: `DIRECT_SIP_RELEVANT`, `INDIRECT_SIP_RELEVANT`, `GENERAL_INVESTMENT_RELEVANT`, `GENERAL_APP_FEEDBACK`, `IRRELEVANT`, `NEEDS_REVIEW`. | `DIRECT_SIP_RELEVANT` |
| `matched_query_categories`| `TEXT`| No | JSON array of matched query categories from `config/review_queries.yml`. | `["payment_and_mandate_failures"]` |
| `matched_terms` | `TEXT` | No | JSON array of exact phrases matched in review text. | `["sip payment failed"]` |
| `relevance_rule_version`| `TEXT`| No | Semantic version of the query dictionary. | `1.0.0` |
| `mentions_sip` | `INTEGER` | No | Binary flag (1/0): Explicitly mentions SIP or Systematic Investment. | `1` |
| `mentions_mutual_fund`| `INTEGER`| No | Binary flag (1/0): Mentions mutual funds, AMC, ETF, index fund. | `1` |
| `mentions_payment` | `INTEGER` | No | Binary flag (1/0): Mentions payment, paid, debit, deducted, paise. | `1` |
| `mentions_mandate` | `INTEGER` | No | Binary flag (1/0): Mentions mandate, NACH, e-mandate. | `0` |
| `mentions_autopay` | `INTEGER` | No | Binary flag (1/0): Mentions autopay, auto-debit, standing instruction. | `0` |
| `mentions_instalment` | `INTEGER` | No | Binary flag (1/0): Mentions instalment, installment, kisht. | `0` |
| `mentions_nav` | `INTEGER` | No | Binary flag (1/0): Mentions NAV, net asset value, cut-off. | `0` |
| `mentions_returns` | `INTEGER` | No | Binary flag (1/0): Mentions returns, XIRR, CAGR, profit, loss. | `0` |
| `mentions_units` | `INTEGER` | No | Binary flag (1/0): Mentions units, unit allotment. | `0` |
| `mentions_pause_stop` | `INTEGER` | No | Binary flag (1/0): Mentions pause, stop, cancel, discontinue, band. | `0` |
| `mentions_restart` | `INTEGER` | No | Binary flag (1/0): Mentions restart, resume, re-activate. | `0` |
| `mentions_redemption` | `INTEGER` | No | Binary flag (1/0): Mentions redeem, withdraw, exit load, nikalna. | `0` |
| `mentions_support` | `INTEGER` | No | Binary flag (1/0): Mentions customer support, care, ticket, helpdesk. | `1` |
| `mentions_kyc` | `INTEGER` | No | Binary flag (1/0): Mentions KYC, PAN, Aadhaar, verification. | `0` |
| `mentions_trust` | `INTEGER` | No | Binary flag (1/0): Mentions trust, scam, fraud, cheat, chor, loot. | `0` |

---

### 2.5 Deduplication & Clustering Attributes

| Field Name | Data Type | Nullable | Description & Values | Example |
| :--- | :--- | :---: | :--- | :--- |
| `dedupe_group_id` | `TEXT` | No | Cluster group ID for linking duplicate or near-duplicate reviews. | `GRP_EV_GROW_APP_4e23bba6` |
| `duplicate_status` | `TEXT` | No | Deduplication classification: `UNIQUE`, `DUPLICATE_SOURCE_ID`, `DUPLICATE_HASH`, `NEAR_DUPLICATE_CANDIDATE`. | `UNIQUE` |
| `duplicate_of_evidence_id`| `TEXT`| Yes | Evidence ID of the primary original review if duplicated. | `NULL` |
| `deduplication_method`| `TEXT` | No | Method: `none`, `source_id_exact`, `content_hash_exact`, `similarity_{score}`. | `none` |

---

### 2.6 Data Quality & Governance Lifecycle

| Field Name | Data Type | Nullable | Description & Values | Example |
| :--- | :--- | :---: | :--- | :--- |
| `data_quality_score` | `REAL` | No | Normalized quality score from 0.00 to 1.00 based on weighted dimensions. | `1.00` |
| `data_quality_status`| `TEXT` | No | Quality status: `HIGH_QUALITY`, `ACCEPTABLE`, `LOW_QUALITY`, `BLOCKED`. | `HIGH_QUALITY` |
| `data_quality_issues`| `TEXT` | No | JSON array of detected quality or governance flaws. | `[]` |
| `eligibility_status` | `TEXT` | No | Research governance status: `ELIGIBLE`, `PENDING`, `REJECTED`, `SYNTHETIC_DEMO`. | `ELIGIBLE` |
| `source_policy_version`| `TEXT` | No | Data governance policy version reference. | `1.0.0` |
| `retention_expiry_at`| `TIMESTAMP`| No | UTC timestamp when review must be retired or deleted (365 days). | `2027-11-06 04:54:51` |
| `deletion_status` | `TEXT` | No | Lifecycle status: `ACTIVE`, `EXPIRED`, `QUARANTINED`, `DELETED`. | `ACTIVE` |

---

## 3. Research Export Filtering Contract

Researchers consuming `master_investor_feedback.csv` and `outputs/sip_relevant_reviews.csv` are guaranteed that:
1. Every record satisfies:
   `eligibility_status = 'ELIGIBLE' AND deletion_status = 'ACTIVE' AND data_quality_status != 'BLOCKED'`.
2. All synthetic demonstration records (`SYNTHETIC_DEMO`) are completely excluded.
3. Reviewer usernames, author emails, and raw personal identifiers are zeroed out.
4. `outputs/sip_relevant_reviews.csv` strictly contains records where `sip_relevance_status IN ('DIRECT_SIP_RELEVANT', 'INDIRECT_SIP_RELEVANT')`.
