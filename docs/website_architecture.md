# GROWWW – AI-POWERED INVESTOR DISCOVERY ENGINE
## Phase 6 Website Architecture & Technical Specification

---

## 1. Architectural Overview

The Growww Investor Discovery Engine web platform is a unified, full-stack research portal built using Python 3.9, Streamlit, and SQLite (`growww_discovery.db`). The architecture bridges quantitative review ingestion, AI-powered semantic enrichment, empirical validation gates, discovery analytics, and opportunity backlog governance into a cohesive, evidence-backed user interface.

```
+------------------------------------------------------------------------------------+
|                                STREAMLIT RESEARCH WEB PORTAL                        |
|                                         (app.py)                                   |
+------------------------------------------------------------------------------------+
       |                              |                                |
+---------------+              +---------------+              +--------------------+
|  CORE & AUTH  |              | UI NAVIGATION |              | SERVICES & STORAGE |
| (core/auth.py)|              |(ui/navigation)|              |   (SQLite / CSVs)  |
| - RBAC Engine |              | - 6 Sections  |              | - DatabaseManager  |
| - 4 Roles     |              | - 14 Pages    |              | - OpportunityServ  |
| - Permissions |              | - CSS Styles  |              | - PDFExportService |
+---------------+              +---------------+              +--------------------+
       |                              |                                |
       +------------------------------+--------------------------------+
                                      |
     +--------------------------------+--------------------------------+
     |                                                                 |
[1. OVERVIEW]                     [2. DATA & SOURCES]             [3. RESEARCH & INSIGHTS]
- Executive Overview              - Source Manager                - SIP Journey Explorer
                                  - Collection History            - Investor Behaviour
                                  - Review Explorer               - Theme Explorer
                                  - SIP Data Quality              - App Comparison
     |                                                                 |
[4. OPPORTUNITY DISCOVERY]        [5. AI & VALIDATION]            [6. REPORTS & EXPORTS]
- Opportunity Radar               - AI Evidence Log               - Exports & Reports
- Opportunity Detail              - Model Validation
- 12M Retention Simulator         - Human Validation
```

---

## 2. Functional Sections & Page Directory

The web portal is organized into 6 functional sections comprising 14 research-grade pages and 2 auxiliary simulation views:

| Section | Page Name | Primary Objective | Backing Data Store |
| :--- | :--- | :--- | :--- |
| **1. Overview** | `Executive Overview` | C-level KPI cards, health status, top friction points, and quick jump navigation | SQLite `reviews`, `ai_evidence_log`, Phase 5 analytics CSVs |
| **2. Data & Sources** | `Source Manager` | Apple RSS feed registry, Google Play import controls, and store route toggles | `config/app_registry.json`, ingestion logs |
| | `Collection History` | Audit history of all collection runs, batch IDs, review yields, and store latencies | `ingestion_runs` table / CSV |
| | `Review Explorer` | Full-text keyword search, multi-faceted filtering, and verbatim span inspection | SQLite `reviews` table (3,790 eligible records) |
| | `SIP Data Quality` | Standardization audits, PII masking verification, deduplication diagnostics | `data/processed/`, quarantine metrics |
| **3. Research & Insights** | `SIP Journey Explorer` | 8-stage longitudinal SIP lifecycle (S0-S7) with friction density and verbatim quotes | `outputs/lifecycle_journey_analytics.csv` |
| | `Investor Behaviour` | Motivations, expectations, triggers, workarounds, and reported outcomes | SQLite `ai_evidence_log`, behavioural distributions |
| | `Theme Explorer` | 29 canonical themes, dossier cards, and cross-app prevalence charts | `outputs/theme_frequencies.csv` |
| | `App Comparison` | 11-dimension benchmarking, RPPI indices, and competitive positioning | `outputs/cross_app_benchmarks.csv` |
| **4. Opportunity Discovery** | `Opportunity Radar` | Prioritization leaderboard, 2D strategic matrix, and multi-factor scoring | SQLite `opportunities` table |
| | `Opportunity Detail` | Comprehensive opportunity dossier, problem breakdown, intervention, and status update | SQLite `opportunities`, `opportunity_audits` |
| | `12M Retention Simulator` | Dynamic sensitivity simulator evaluating compound retention impact of interventions | `outputs/sip_retention_hypotheses.csv` |
| **5. AI & Validation** | `AI Evidence Log` | Searchable, auditable record of all 1,527 enrichments, prompt hashes, and confidence | SQLite `ai_evidence_log` table |
| | `Model Validation` | Quality gates against gold set (Macro F1, Cohen's $\kappa$, Direct Grounding) | `outputs/model_evaluation_metrics.json` |
| | `Human Validation` | Adjudication workbench for auditing low-confidence classifications and corrections | `HumanReviewService`, `human_adjudications` |
| **6. Reports & Exports** | `Exports & Reports` | Unified portal for downloading all CSV datasets and compiling executive PDF dossiers | `outputs/*.csv`, `services/pdf_export_service.py` |

---

## 3. Data Flow & Provenance Architecture

1. **Zero Hardcoded Metrics:** Every metric card, chart, and table in the website is queried dynamically from SQLite or loaded from reproducible Phase 5 export CSVs.
2. **Immutable Traceability:** Review text is stored immutably. AI classifications maintain the exact character spans matching the original text, prompt SHA-256 hashes, model versions, and latency timestamps.
3. **Audited Governance:** State transitions in the Opportunity Backlog record an immutable audit entry into `opportunity_audits` capturing `actor_id`, `previous_status`, `new_status`, `change_rationale`, and `changed_at`.
4. **Pure-Python PDF Generation:** Uses `PDFDocumentWriter` to generate standard PDF 1.4 documents without requiring C libraries (like `wkhtmltopdf` or `cairo`), ensuring 100% portability in constrained server environments.

---

## 4. State Management & Navigation Flow

- **Session State Variables:**
  - `st.session_state.current_page`: Active navigation page.
  - `st.session_state.auth_role`: Current user role (`ADMIN`, `RESEARCHER`, `VIEWER`, `AUDITOR`).
  - `st.session_state.auth_user_id`: Active actor identifier.
  - `st.session_state.selected_opportunity_id`: Active opportunity for the Opportunity Detail dossier.
  - `st.session_state.db_initialized`: Flag ensuring single-pass initialization on app startup.
- **Deep-Link Transitions:**
  - Clicking "Inspect Dossier" on the Executive Overview or Opportunity Radar sets `st.session_state.selected_opportunity_id` and navigates directly to `Opportunity Detail`.
  - Clicking "Explore Stage" on the Executive Overview jumps to `SIP Journey Explorer` with the targeted stage pre-selected.
