# GROWWW – AI-POWERED INVESTOR DISCOVERY ENGINE
# PHASE 7 INITIAL INDEPENDENT AUDIT REPORT
## Technical Architecture, Data Integrity, Security & Blocker Identification

**Audit Date:** 2026-11-06  
**Auditor:** Independent QA Lead & Security Architect  
**Scope:** Complete Codebase, Database (`growww_discovery.db`), Pipeline Connectors, Model Outputs, UI Components, and Documentation.

---

## 1. Executive Summary

This initial audit provides an objective, critical evaluation of the Growww AI-Powered Investor Discovery Engine. The inspection audited the repository across 10 mandatory dimensions to uncover defects, formula discrepancies, security vulnerabilities, and release blockers prior to Phase 8 deployment.

### System Vital Statistics (Audited):
- **Total Database Records:** 3,798 reviews (3,790 eligible research records, 8 quarantined synthetic demo records).
- **AI Enriched Records:** 1,533 records in `ai_evidence_log` (1,526 valid eligible, 7 orphaned test records).
- **Human Adjudications:** 307 records in `human_adjudications` (300 valid benchmark, 7 orphaned test records).
- **Opportunities Seeded:** 7 prioritized product opportunities (`OPP-01` through `OPP-07`).
- **Test Baseline:** 110 automated tests passing across 13 test suites.

---

## 2. Comprehensive 10-Dimension Audit Findings

### 2.1 Implemented Features
1. **Source Connectors:** Apple App Store public customer review RSS syndication connector with pagination, backoff, and checkpointing (`ingestion/apple_app_store_rss.py`).
2. **Manual Ingestion:** Compliant CSV import pipeline with schema validation and provenance tracking (`ingestion/manual_review_csv.py`).
3. **Data Normalization & PII Scrubbing:** Unicode cleaning, Indian phone number, email, PAN card, UPI handle, and bank account context redaction (`processing/pii_minimization.py`).
4. **Multilingual Language Tagging:** Language detection for English (`en`), Hindi (`hi`), Romanized Hindi (`hi-Latn`), and mixed code-switching (`processing/language_detection.py`).
5. **Deduplication:** Content hashing (SHA-256) and deduplication group assignment (`processing/deduplicate.py`).
6. **SIP Relevance Engine:** Rule-based keyword matching across 15 core SIP and mutual fund concepts (`processing/sip_relevance.py`).
7. **Rule-Based AI Classifier:** Taxonomy mapping, character-level verbatim span extraction, and confidence scoring (`ai/classifier.py`).
8. **Traceable AI Evidence Log:** Audit trail with model IDs, taxonomy versions, and prompt SHA-256 hashes (`ai/evidence_log_service.py`).
9. **Research Analytics:** 29-theme prevalence engine with app-specific sampling frame denominators, lifecycle journey mapping (S0–S7), and cross-app RPPI benchmarking (`analytics/`).
10. **Role-Based Access Control (RBAC):** Server-side enforcement across Admin, Researcher, Viewer, and Auditor (`core/auth.py`).
11. **Pure-Python PDF Generation:** Standalone PDF 1.4 document compiler (`services/pdf_export_service.py`).
12. **Full Research Website:** 14 interactive pages across 6 functional sections in Streamlit (`app.py`, `ui/navigation.py`, `ui/pages/`).

### 2.2 Partially Implemented Features
1. **Google Play Store Integration:** Google Play automated API collection is on standby because competitor console API credentials do not exist. Ingestion relies on manual CSV imports.
2. **Opportunity Scoring Dual Formulation:** Phase 5 implemented a 4-component weighted model (`0.30 P + 0.30 S + 0.25 L + 0.15 A`), while the Phase 7 prompt specifies a 6-component formulation (`0.25 Retention + 0.20 Recurrence + 0.15 Severity + 0.15 First-Time + 0.15 Actionability + 0.10 Evidence Quality`). Both formulations must be reconciled.
3. **Longitudinal Journey Analytics:** S0–S7 stages are inferred from cross-sectional customer reviews, not multi-year account telemetry. Research disclaimers are present, but must be reinforced.

### 2.3 Missing Features
1. **Foreign Key Enforcement in Service Connections:** Direct SQLite connections in `EvidenceLogService`, `HumanReviewService`, and `OpportunityService` omit `PRAGMA foreign_keys = ON;`.
2. **HTML Escaping on Review Text in UI:** Untrusted customer review text is interpolated directly into `st.markdown(..., unsafe_allow_html=True)` without `html.escape()`.
3. **300-Record Stratified Gold Set:** The existing gold standard consists of $N=150$ records. Task 1 will expand this to $N=300$ stratified records with verified double-annotation metrics.

### 2.4 Broken Features & Identified Defects
1. **Orphaned Test Records (`EV_UNIT_03`):** Running `tests/test_phase_4.py` inserted 7 records with `evidence_id = 'EV_UNIT_03'` into `ai_evidence_log` and `human_adjudications` without a matching record in `reviews`. `PRAGMA foreign_key_check;` failed with 14 violations.
2. **Export Query Column Error:** In `ui/pages/exports_reports.py`, the review query references `is_sip_relevant` instead of `sip_relevance_status`, causing raw export queries to fail if triggered.

### 2.5 Incorrect Calculations & Discrepancies
1. **Scoring Factor Normalization:** The 4-factor multiplicative formula vs 6-factor linear additive formula. Mathematical equivalence and ranking stability must be audited.
2. **Prevalence Denominators:** Must strictly ensure app-specific eligible review counts are used as denominators (Groww: 404, Zerodha Coin: 500), never the total multi-app dataset (3,790).

### 2.6 Unsupported Assumptions
1. **App Store Review Representation:** Public reviews suffer from vocal negative reporting bias and cannot be presented as proof of verified 12-month customer account retention.
2. **Demographic Inference Prohibition:** Investor demographics (age, income, gender, location) cannot be assumed and must default strictly to `UNKNOWN`.

### 2.7 Security Weaknesses
1. **Stored Cross-Site Scripting (XSS) via Review Text:** Unsanitized user review text rendered inside `unsafe_allow_html=True` HTML blocks in Streamlit. Malicious tags (`<script>`, `<iframe>`, `<img>`) could execute in researcher browsers.
2. **Lack of DB-Level Foreign Key Enforcement:** Without `PRAGMA foreign_keys = ON;`, child records can be inserted with broken references.

### 2.8 Privacy Weaknesses
1. **Review Text in Error Diagnostics:** Raw unredacted review text must never be dumped into unhandled exception stack traces or diagnostic log files.
2. **Viewer Role Enforcement:** The Viewer role is restricted in the UI, but database connection boundaries must ensure zero unredacted PII leaks.

### 2.9 Data Integrity Issues
1. **7 Orphaned Rows in `ai_evidence_log` and `human_adjudications`:** Must be purged from `growww_discovery.db`.
2. **Quarantine Verification:** The 8 synthetic demo records (`EV_GROWW_0001` to `EV_GROWW_0008`) must remain strictly excluded from eligible research evidence.

### 2.10 Release Blockers
- **BLOCKER-01 (CRITICAL):** Stored XSS vulnerability in UI markdown rendering (apply `html.escape()`).
- **BLOCKER-02 (HIGH):** Orphaned records in `ai_evidence_log` and missing `PRAGMA foreign_keys = ON;` in services.
- **BLOCKER-03 (HIGH):** Column name bug (`is_sip_relevant` -> `sip_relevance_status`) in `exports_reports.py`.
- **BLOCKER-04 (HIGH):** Gold standard expansion to 300 stratified records with genuine double-annotation agreement audit.
- **BLOCKER-05 (MEDIUM):** Dual opportunity scoring calculation and validation.

---

## 3. Immediate Action Plan

1. Build independent 300-record gold-standard dataset (`validation/gold_set.py`).
2. Implement double-annotation agreement audit with Cohen's kappa (`validation/gold_set.py`, Task 2).
3. Execute independent AI model evaluation (`validation/model_validation.py`, Task 3).
4. Perform 100% exact-match evidence grounding audit (`validation/evidence_audit.py`, Task 4).
5. Execute pipeline failure tests, database integrity tests, privacy audits, and security tests (Tasks 5–8).
6. Run Streamlit E2E tests, analytics validation, and performance benchmarks (Tasks 9–11).
7. Resolve all identified release blockers (Blockers 01 to 05), add regression tests, and rerun the full test suite (Tasks 12–13).
8. Issue release readiness verdict and comprehensive Phase 7 completion report (Task 14).
