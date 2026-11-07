# GROWWW – AI-POWERED INVESTOR DISCOVERY ENGINE
## User Guide & Research Workflow Manual

---

## 1. Introduction & Target Audiences

The Growww Investor Discovery Engine is designed for cross-functional product and research teams:
- **Product Managers (PMs):** Discover user drop-off drivers, inspect grounded customer feedback, evaluate prioritized product interventions, and manage opportunity lifecycle states.
- **Product Researchers & Data Analysts:** Explore lifecycle journey friction, run cross-app sentiment benchmarks, filter reviews by granular taxonomy tags, and download standardized CSV datasets.
- **Data Governance & ML Engineers:** Audit AI classifications, verify model quality gates, inspect verbatim evidence grounding, and execute human adjudication workflows.
- **Executive Leadership:** Review executive KPI digests, competitive benchmark positioning, and 12-month retention scenario models.

---

## 2. Navigating the Research Platform

### 2.1 The Sidebar & Role Switcher
- The left sidebar provides instant navigation across all 14 research pages.
- At the bottom of the sidebar is the **Active User & Role Access** selector. You can switch between:
  - **ADMIN:** Unrestricted access to manage sources, update opportunities, adjudicate reviews, and export raw data.
  - **RESEARCHER:** Full access to explore reviews, update opportunity states, adjudicate reviews, and export datasets.
  - **VIEWER:** Safe stakeholder view. Can view all analytics, explore journeys, and export executive reports, but **cannot** download raw customer reviews or alter opportunity states.
  - **AUDITOR:** Compliance view. Can inspect audit logs and export datasets, but cannot alter operational configurations.

---

## 3. Core Research Workflows

### 3.1 Opportunity Discovery & Lifecycle Management
1. Navigate to **Opportunity Discovery > Opportunity Radar**.
2. Review the **Prioritization Leaderboard** and the **2D Strategic Matrix** (Customer Severity vs Actionability).
3. Use the filters to focus on a specific lifecycle stage (e.g. `S1_SETUP` or `S5_FRICTION`).
4. Click **Inspect Dossier** on any opportunity (e.g. `OPP-01` or `OPP-06`) to open the **Opportunity Detail** dossier.
5. In the dossier, explore:
   - **Problem Definition:** Why first-time investors struggle and when the friction occurs.
   - **Grounded Evidence:** Exact verbatim quotes with evidence confidence scores.
   - **Scoring Breakdown:** Transparent factor weights.
   - **Product Intervention:** Proposed feature, testable hypothesis, primary metric, and guardrails.
   - **Lifecycle Governance & Audits:** (If logged in as Researcher or Admin) Select a new status (e.g. `READY_FOR_EXPERIMENT` or `IN_PROGRESS`), enter a mandatory adjudication rationale, and click **Submit Status Transition**.

### 3.2 Evidence Deep-Dive in Review Explorer
1. Navigate to **Data & Sources > Review Explorer**.
2. Filter reviews by:
   - Application (Groww, Zerodha Coin, PayTM Money, etc.)
   - Star Rating (1 to 5 stars)
   - SIP Relevance Status (`SIP_SPECIFIC_EVIDENCE`, `GENERAL_MUTUAL_FUND`, etc.)
   - Lifecycle Stage (`S0_DISCOVERY` through `S7_CHURN`)
   - Text Search keyword (e.g. "mandate", "autopay", "delay", "customer care")
3. Expand any review card to inspect the exact verbatim character spans extracted by the AI and verify grounding veracity.

### 3.3 Human Adjudication Workflow
1. Switch your role to **RESEARCHER** or **ADMIN**.
2. Navigate to **AI & Validation > Human Validation**.
3. Inspect pending reviews flagged for human audit (low confidence or boundary cases).
4. Review the original customer text alongside AI predicted labels.
5. Select **ACCEPT** (confirm correct), **CORRECT** (manually adjust stage or theme), or **REJECT** (flag irrelevant).
6. Enter an adjudication rationale and click **Record Adjudication**.

### 3.4 Exporting Datasets & Generating Executive PDFs
1. Navigate to **Reports & Exports > Exports & Reports**.
2. **Executive PDF Reports:**
   - Click **Download Weekly Digest (PDF)** for a high-level briefing.
   - Click **Download Opportunity Dossier (PDF)** for a formal opportunity specification.
3. **Standardized Analytics Exports:**
   - Download CSVs for `ranked_product_opportunities.csv`, `theme_frequencies.csv`, `lifecycle_journey_analytics.csv`, and `cross_app_benchmarks.csv`.
4. **Customer Review Evidence:**
   - (Researchers and Admins only) Export filtered PII-masked customer review datasets for offline NLP analysis.

---

## 4. Phase 7 Validation Workflows & Audit Tools

The discovery engine includes standalone validation scripts and audited quality gates to ensure research-grade integrity:

### 4.1 Running Validation Scripts
All validation tools can be executed directly from the terminal using `PYTHONPATH=.:./lib python3`:

| Validation Script | Function / Objective | Key Output Report |
| :--- | :--- | :--- |
| `validation/gold_set.py` | Generates 300-record stratified gold-standard dataset across apps & ratings | `outputs/gold_standard_300.json` |
| `validation/model_validation.py` | Evaluates classifier against gold standard (Macro F1, Cohen's Kappa, Grounding) | `reports/independent_model_validation.md` |
| `validation/evidence_audit.py` | Verifies 10 evidentiary criteria for all 7 product opportunities | `reports/evidence_grounding_audit.md` |
| `validation/pipeline_failure_tests.py` | Tests network disruptions, rate limits, timeouts, and AppFollow blocking | `reports/pipeline_failure_test_report.md` |
| `validation/database_integrity.py` | Audits foreign keys, content deduplication, and synthetic quarantine | `reports/database_integrity_report.md` |
| `validation/privacy_audit.py` | Scans review corpus, exports, and logs for unredacted PII patterns | `reports/privacy_retention_audit.md` |
| `validation/security_tests.py` | Evaluates 4-role RBAC, SQL injection, XSS escaping, and secrets | `reports/security_audit.md` |
| `validation/application_tests.py` | Tests all 16 page renders, empty states, and PDF/CSV downloads | `reports/application_test_report.md` |
| `validation/analytics_audit.py` | Validates metrics denominators, 4-factor & 6-factor models, noise stability | `reports/analytics_validation_report.md` |
| `validation/performance_tests.py` | Benchmarks query latencies, export throughput, and concurrency | `reports/performance_test_report.md` |

### 4.2 Automated Quality Gates
- **Pain-Point Macro F1:** Must meet or exceed **0.80** (Achieved: **0.815**).
- **Inter-Annotator Agreement ($\kappa$):** Must meet or exceed **0.70** (Achieved: **1.000** for pain points, **0.973** for lifecycle).
- **Verbatim Evidence Grounding:** Exactly **100.0%** verified exact text matches (0 synthetic quotes).
- **Database Referential Integrity:** Exactly **0** foreign key check violations.
- **Privacy Gate:** Zero unredacted personal identifiers (phones, emails, PANs, Aadhaar, UPI).
- **Quarantine Gate:** 8 demonstration records strictly isolated from research evidence.
