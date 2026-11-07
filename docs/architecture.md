# Growww AI-Powered Investor Discovery Engine
## System Architecture & Technical Design Specification
**Phase 1 Deliverable | Repository & Application Foundation**  
**Document Version:** 1.0.0  
**Effective Date:** 2026-11-05  

---

## 1. Architectural Philosophy & Context

The **Growww AI-Powered Investor Discovery Engine** is an independent research prototype engineered to systematically discover customer friction, payment mandate failures, setup obstacles, and behavioral retention patterns in Systematic Investment Plans (SIPs) across Indian investment platforms.

### Core Architectural Invariants:
1. **Independent Research Boundary:** Operates exclusively on publicly accessible customer reviews and verified CSV research datasets. Does not access Groww internal databases or private customer CRM cohorts.
2. **100% Free-Tier Operation:** Following the empirical rejection of paywalled SaaS tools (AppFollow), the architecture operates on zero subscription costs, relying on Apple's public RSS syndication feed and compliant CSV imports.
3. **Data Governance & Privacy-by-Design:** Enforces data minimization by stripping reviewer identities and scrubing Indian financial PII (phone, email, PAN, bank accounts) before persistence.
4. **Layered Decoupling:** Strict separation between presentation (Streamlit UI), service business logic, core validation/configuration, and data persistence layers.

---

## 2. High-Level Architecture Diagram

```
+---------------------------------------------------------------------------------+
|                                 USER BROWSER                                    |
+---------------------------------------------------------------------------------+
                                         ▲
                                         │  HTTP / WebSockets
                                         ▼
+---------------------------------------------------------------------------------+
|                           STREAMLIT PRESENTATION TIER                           |
|  app.py • ui/navigation.py • ui/pages/ (Overview, App Registry, Import, ...)   |
+---------------------------------------------------------------------------------+
                                         │
                                         ▼
+---------------------------------------------------------------------------------+
|                               SERVICE LAYER                                     |
|  • AppRegistryService: Search, filtering, and application metadata             |
|  • ImportService: Ingestion orchestration, transactions, and audit logging      |
+---------------------------------------------------------------------------------+
         │                                                        │
         ▼                                                        ▼
+---------------------------------------+  +--------------------------------------+
|             CORE ENGINE               |  |           PERSISTENCE LAYER          |
|  • ConfigLoader (YAML validation)     |  |  • DatabaseConnection (SQLite pool)  |
|  • CSVValidator (PII regex & schema)  |  |  • AppRepository (apps)             |
|  • SampleDataManager (Demo mode)      |  |  • SourceRouteRepository (sources)  |
|  • Exceptions (Domain errors)         |  |  • ReviewRepository (reviews)        |
+---------------------------------------+  |  • ImportBatchRepository (batches)   |
                                           +--------------------------------------+
                                                              │
                                                              ▼
                                                   [growww_discovery.db]
```

---

## 3. Module Responsibilities & Service Boundaries

### 3.1 Presentation Tier (`ui/` & `app.py`)
- **`app.py`:** Main entry point. Initializes database schema, synchronizes YAML configs, applies custom CSS, and handles routing.
- **`ui/navigation.py`:** Shared visual styling, brand green palette (`#00D09C`), sidebar navigation, and demo mode alert banners.
- **`ui/pages/overview.py`:** Executive overview with KPI cards, store breakdown pie chart, star rating bar chart, and recent batch activity.
- **`ui/pages/app_registry.py`:** Live directory of all 8 candidate investment platforms with search and role filtering.
- **`ui/pages/data_import.py`:** Interactive CSV upload, column mapping preview, PII scanning, and transactional ingestion.
- **`ui/pages/data_explorer.py`:** Paginated, multi-filter review browser with expandable provenance cards.
- **`ui/pages/system_status.py`:** Diagnostics monitor reporting database health, configuration status, and source route permission gates.

### 3.2 Service Layer (`services/`)
- **`AppRegistryService`:** Decouples UI pages from direct SQL queries on candidate applications.
- **`ImportService`:** Orchestrates atomic transactions across batch auditing (`import_batches`) and canonical review persistence (`reviews`). Handles deduplication and row-level error reporting.

### 3.3 Core Engine (`core/`)
- **`ConfigLoader`:** Validates and parses `apps.yml`, `source_access.yml`, and `review_taxonomy.yml`. Ensures no hardcoded IDs exist.
- **`CSVValidator`:** Enforces canonical schema (`review_text`, `review_date`, `rating`), maps column aliases, executes PII regex sanitization, and verifies date parsing.
- **`SampleDataManager`:** Manages 35+ realistic synthetic demo reviews covering SIP failure modes, strictly quarantined under `SYNTHETIC_DEMO`.

### 3.4 Persistence Tier (`database/`)
- **`DatabaseConnection`:** Thread-safe connection context manager with SQLite WAL mode and foreign key enforcement (`PRAGMA foreign_keys = ON;`).
- **Repositories (`AppRepository`, `ReviewRepository`, etc.):** Normalized data access objects shielding SQL dialect differences.

---

## 4. Data Flow: Ingestion Lifecycle

```
[Raw CSV File]
      │
      ▼
1. Preview & Header Inspection (CSVValidator.inspect_dataframe)
      │  └── Checks for disallowed PII columns (user_name, phone_number, etc.)
      ▼
2. Column Mapping & Type Normalization
      │  └── Auto-maps 'content' -> 'review_text', 'stars' -> 'rating', etc.
      ▼
3. Row-Level Validation & Sanitization (CSVValidator.validate_and_clean_rows)
      │  ├── Date parsed to ISO 8601 UTC
      │  ├── Rating validated as integer between 1 and 5
      │  ├── SHA-256 content hash generated
      │  └── PII regex scrubbed ([PHONE_REDACTED], [EMAIL_REDACTED], etc.)
      ▼
4. Provenance & Permission Verification (ImportService)
      │  └── Verified provenance -> 'ELIGIBLE' / Unverified -> 'PENDING'
      ▼
5. Atomic Transaction Persistence (ReviewRepository.insert_review)
      │  ├── Skips duplicates (by app_id + store + source_record_id / hash)
      │  └── Updates batch audit stats in import_batches
      ▼
[Persisted in SQLite]
```

---

## 5. Future Phase Integration Points

- **Phase 2 (Automated Ingestion):** `AppleRSSConnector` will plug directly into `ReviewRepository`, replacing manual CSV uploads with scheduled RSS delta pulls.
- **Phase 3 (Data Hygiene):** Review normalization and language identification pipelines will enrich `language_detected` and `translated_text` in the canonical `reviews` table.
- **Phase 4 (AI Classification):** LLM worker will query unclassified reviews from `reviews`, apply `review_taxonomy.yml` labels, and write to dedicated evidence span tables.
- **Phase 5 (Analytics Dashboard):** Aggregation services will query classified reviews to compute SIP retention friction scores and opportunity matrices.
