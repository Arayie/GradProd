# GROWWW – AI-POWERED INVESTOR DISCOVERY ENGINE
## Phase 1 Dashboard Audit & Data Integrity Completion Report
**Auditor:** Senior Product Engineer, Software Architect, Database Engineer, Data Governance Specialist  
**Evaluation Scope:** Database Audit, Metric Disaggregation, Contrast & Design Correction, and Integrity Verification  
**Date of Audit:** 2026-11-06  
**Status:** **AUDIT COMPLETE – ALL DATA INTEGRITY & DESIGN ISSUES RESOLVED**  

---

## 1. Executive Summary

A forensic audit of the Growww Investor Discovery Engine database (`growww_discovery.db`) and Streamlit user interface was conducted following the observation that the Overview dashboard displayed **8 reviews ingested** and **8 eligible research records** despite Phase 1 being a foundation and sample-data release.

### Forensic Findings Summary:
1. **Origin of the 8 Records:** The 8 records were imported during Phase 1 manual CSV testing on `2026-11-05 14:19:14` under batch `BATCH_8B010BED_202611051419` from [`data/sample_google_play_reviews.csv`](file:///Users/aradhyayadav/Downloads/GradProd/data/sample_google_play_reviews.csv).
2. **Authenticity Classification:** **SYNTHETIC DEMONSTRATION RECORDS.**
   - The review IDs (`gp_groww_001` through `gp_groww_004`, `gp_coin_001`, `gp_coin_002`, `gp_upstox_001`, `gp_angel_001`) are handcrafted sample keys.
   - All 8 records were inserted under `app_id: groww` despite their text referring to other competitor apps (Zerodha Coin, Upstox, Angel One).
   - They had no canonical listing URLs (`canonical_url: None`).
   - They were imported without the `is_synthetic=True` toggle, causing them to improperly receive `eligibility_status = 'ELIGIBLE'`.
3. **Database Remediation:** All 8 records have been updated to `eligibility_status = 'SYNTHETIC_DEMO'`. Their batch record in `import_batches` has been re-tagged to `permission_status = 'SYNTHETIC_DEMO'`.
4. **Metric Disaggregation:** The metric engine ([`database/repositories.py`](file:///Users/aradhyayadav/Downloads/GradProd/database/repositories.py)) was restructured to dynamically separate **Total Records Stored**, **Genuine Review Records**, **Eligible Research Evidence**, **Pending Verification**, **Rejected Records**, and **Synthetic Demo Records**. Synthetic records are strictly excluded from genuine counts and distribution charts.
5. **Dashboard Contrast & UI Polish:** Corrected Streamlit metric card CSS to eliminate low-contrast/invisible labels, configured light theme in `.streamlit/config.toml`, improved typography, added empty-state handling for charts, and maintained Growww branding (`#00D09C`, `#1E3A2F`).
6. **Automated Verification:** Added [`tests/test_data_integrity.py`](file:///Users/aradhyayadav/Downloads/GradProd/tests/test_data_integrity.py) with 6 comprehensive integrity tests. All 56 tests across the entire test suite pass with 100% success rate.

---

## 2. Forensic Investigation of the 8 Records (Task 1)

All 8 records were queried and inspected directly from SQLite:

| Field | Record 1 | Record 2 | Record 3 | Record 4 |
| :--- | :--- | :--- | :--- | :--- |
| **Evidence ID** | `EV_GROW_GOO_f96213f7` | `EV_GROW_GOO_58e69c58` | `EV_GROW_GOO_6c0156df` | `EV_GROW_GOO_38425860` |
| **Source Record ID** | `gp_groww_001` | `gp_groww_002` | `gp_groww_003` | `gp_groww_004` |
| **Review Text** | *"Started my first 1000 rupees monthly SIP in Nifty 50 index fund..."* | *"My bank debited 2000 rupees for my SIP yesterday but app still shows order pending..."* | *"3 mahine se SIP chal rahi hai par portfolio minus me dikha raha hai..."* | *"Bacho ki higher education ke liye 15 saal ka plan banaya hai..."* |
| **Target Application** | Groww (`groww`) | Groww (`groww`) | Groww (`groww`) | Groww (`groww`) |
| **Platform Store** | Google Play (`google_play`) | Google Play (`google_play`) | Google Play (`google_play`) | Google Play (`google_play`) |
| **Collection Method**| `manual_csv_import` | `manual_csv_import` | `manual_csv_import` | `manual_csv_import` |
| **Source URL** | `None` | `None` | `None` | `None` |
| **Import Batch** | `BATCH_8B010BED_202611051419` | `BATCH_8B010BED_202611051419` | `BATCH_8B010BED_202611051419` | `BATCH_8B010BED_202611051419` |
| **Original File** | `sample_google_play_reviews.csv` | `sample_google_play_reviews.csv` | `sample_google_play_reviews.csv` | `sample_google_play_reviews.csv` |
| **Initial Eligibility**| `ELIGIBLE` (Improper) | `ELIGIBLE` (Improper) | `ELIGIBLE` (Improper) | `ELIGIBLE` (Improper) |
| **Corrected Status** | **`SYNTHETIC_DEMO`** | **`SYNTHETIC_DEMO`** | **`SYNTHETIC_DEMO`** | **`SYNTHETIC_DEMO`** |
| **Classification** | **SYNTHETIC DEMO** | **SYNTHETIC DEMO** | **SYNTHETIC DEMO** | **SYNTHETIC DEMO** |

| Field | Record 5 | Record 6 | Record 7 | Record 8 |
| :--- | :--- | :--- | :--- | :--- |
| **Evidence ID** | `EV_GROW_GOO_a71a7893` | `EV_GROW_GOO_ce784c77` | `EV_GROW_GOO_8cc7755f` | `EV_GROW_GOO_ee1864ee` |
| **Source Record ID** | `gp_coin_001` | `gp_coin_002` | `gp_upstox_001` | `gp_angel_001` |
| **Review Text** | *"No commission direct funds. NPS and mutual fund SIP management is seamless..."* | *"e-mandate got rejected due to signature mismatch..."* | *"Setup my monthly SIP easily. Demat holding statement reflects correctly..."* | *"App did not trigger reminder before SIP date and bank deducted 590 rupees bounce..."* |
| **Target Application** | Groww (`groww`) [Misattributed] | Groww (`groww`) [Misattributed] | Groww (`groww`) [Misattributed] | Groww (`groww`) [Misattributed] |
| **Platform Store** | Google Play (`google_play`) | Google Play (`google_play`) | Google Play (`google_play`) | Google Play (`google_play`) |
| **Collection Method**| `manual_csv_import` | `manual_csv_import` | `manual_csv_import` | `manual_csv_import` |
| **Source URL** | `None` | `None` | `None` | `None` |
| **Import Batch** | `BATCH_8B010BED_202611051419` | `BATCH_8B010BED_202611051419` | `BATCH_8B010BED_202611051419` | `BATCH_8B010BED_202611051419` |
| **Original File** | `sample_google_play_reviews.csv` | `sample_google_play_reviews.csv` | `sample_google_play_reviews.csv` | `sample_google_play_reviews.csv` |
| **Initial Eligibility**| `ELIGIBLE` (Improper) | `ELIGIBLE` (Improper) | `ELIGIBLE` (Improper) | `ELIGIBLE` (Improper) |
| **Corrected Status** | **`SYNTHETIC_DEMO`** | **`SYNTHETIC_DEMO`** | **`SYNTHETIC_DEMO`** | **`SYNTHETIC_DEMO`** |
| **Classification** | **SYNTHETIC DEMO** | **SYNTHETIC DEMO** | **SYNTHETIC DEMO** | **SYNTHETIC DEMO** |

### Proof of Synthetic Origin:
1. **Handcrafted Keys:** The IDs `gp_groww_001` through `gp_angel_001` were authored as illustrative test cases covering primary investor journey frictions (SIP debit delays, Hindi return confusion, signature mismatch, bank bounce penalties).
2. **Cross-App Misattribution:** Records 5 through 8 represent Zerodha Coin, Upstox, and Angel One in text, but were imported into the database targeting `app_id = 'groww'`.
3. **Zero Scraping / Public Provenance:** There is no corresponding Google Play store URL, device metadata, or developer response.

---

## 3. Corrected Dashboard Metrics (Task 2)

### Dynamic Metric Segregation Formula:
```sql
SELECT 
    COUNT(*) as total_records,
    COALESCE(SUM(CASE WHEN eligibility_status != 'SYNTHETIC_DEMO' THEN 1 ELSE 0 END), 0) as genuine_reviews,
    COALESCE(SUM(CASE WHEN eligibility_status = 'ELIGIBLE' THEN 1 ELSE 0 END), 0) as eligible_reviews,
    COALESCE(SUM(CASE WHEN eligibility_status = 'PENDING' THEN 1 ELSE 0 END), 0) as pending_reviews,
    COALESCE(SUM(CASE WHEN eligibility_status = 'REJECTED' THEN 1 ELSE 0 END), 0) as rejected_reviews,
    COALESCE(SUM(CASE WHEN eligibility_status = 'SYNTHETIC_DEMO' THEN 1 ELSE 0 END), 0) as demo_reviews
FROM reviews
WHERE deletion_status = 'ACTIVE';
```

### Invariants Enforced:
- **`genuine_reviews`:** Excludes `SYNTHETIC_DEMO`. Returns 0 if no genuine reviews exist.
- **`total_reviews`:** Alias strictly mapped to `genuine_reviews` (never counts synthetic data).
- **`total_records`:** Total rows stored in database across all categories.
- **`eligible_reviews`:** Only genuine records with `eligibility_status = 'ELIGIBLE'`.
- **Zero-State Rule:** When no genuine reviews exist, genuine review metrics return **0**. Synthetic demonstration records are quarantined and displayed separately.

---

## 4. UI & Dashboard Design Improvements (Task 3)

### 4.1 Contrast & Typography Fixes
- **Root Cause Identified:** Streamlit in dark mode applied dark-mode text colors (`#FAFAFA` or translucent white) to child elements inside `div[data-testid="stMetricLabel"]`. Because metric cards had `background-color: white;` hardcoded, light text on white backgrounds resulted in illegible, nearly invisible labels.
- **Remediation in `ui/navigation.py`:**
  - Applied `!important` color overrides across all metric label descendants (`p`, `span`, `div`, `label`) to deep dark slate (`#0F172A`), providing high-contrast readability exceeding WCAG AAA standards.
  - Formatted metric values with `#1E3A2F` (deep research dark green), bold 800 weight, and 1.85rem typography.
  - Upgraded metric card containers with 8px radius, `#CBD5E1` slate borders, and subtle elevation (`0 1px 3px rgba(0,0,0,0.05)`).
- **Streamlit Theme Configuration (`.streamlit/config.toml`):**
  - Configured native theme: `backgroundColor = "#FFFFFF"`, `secondaryBackgroundColor = "#F8FAFC"`, `textColor = "#0F172A"`, and `primaryColor = "#00D09C"`.

### 4.2 Empty-State Handling & Segregated Inspection
- **Empty State Callout:** When `genuine_reviews == 0`, distribution charts are replaced with a clear informational callout explaining that genuine reviews must be ingested via Route A or Route B.
- **Segregated Demonstration Expander:** If synthetic demo records are present, they are quarantined and displayed in a collapsible audit view (`🧪 Inspect Quarantined Synthetic Demonstration Records`) clearly separated from genuine research analytics.
- **Professional Chart Cards:** When genuine reviews are present, charts render with transparent backgrounds (`paper_bgcolor="rgba(0,0,0,0)"`), crisp `#1E293B` typography, and `#E2E8F0` gridlines.

---

## 5. Automated Data Integrity Verification (Task 4)

A dedicated test suite was implemented in [`tests/test_data_integrity.py`](file:///Users/aradhyayadav/Downloads/GradProd/tests/test_data_integrity.py) testing all 6 criteria:

```text
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/aradhyayadav/Downloads/GradProd
collected 6 items

tests/test_data_integrity.py::TestDataIntegrityAndMetrics::test_01_empty_database_produces_zero_metrics PASSED
tests/test_data_integrity.py::TestDataIntegrityAndMetrics::test_02_synthetic_records_excluded_from_genuine_review_metrics PASSED
tests/test_data_integrity.py::TestDataIntegrityAndMetrics::test_03_unverified_records_are_not_eligible PASSED
tests/test_data_integrity.py::TestDataIntegrityAndMetrics::test_04_genuine_permitted_reviews_counted_correctly PASSED
tests/test_data_integrity.py::TestDataIntegrityAndMetrics::test_05_loading_demo_data_does_not_alter_production_review_counts PASSED
tests/test_data_integrity.py::TestDataIntegrityAndMetrics::test_06_restarting_application_preserves_correct_counts PASSED

============================== 6 passed in 0.10s ===============================
```

### Full Test Suite Results (All 8 Suites):
```text
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/aradhyayadav/Downloads/GradProd
collected 56 items

tests/test_app_registry.py ....                                          [  7%]
tests/test_apple_rss.py ........                                         [ 21%]
tests/test_config.py .....                                               [ 30%]
tests/test_csv_import.py ......                                          [ 41%]
tests/test_data_integrity.py ......                                      [ 51%]
tests/test_database.py .....                                             [ 60%]
tests/test_ingestion_service.py .........                                [ 76%]
tests/test_phase_0_configs.py ..........                                 [ 94%]
tests/test_sample_data.py ...                                            [100%]

============================== 56 passed in 1.81s ==============================
```
