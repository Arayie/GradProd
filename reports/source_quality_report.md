# GROWWW – AI-POWERED INVESTOR DISCOVERY ENGINE
## Phase 3: Source Quality and Dataset Health Report

**Auditor / Roles:** Senior Data Engineer, NLP Engineer, Data Quality Specialist, Research Data Architect  
**Evaluation Baseline:** PRD Version 1.1, Phase 0 Governance Baseline, Phase 2 Ingestion Results  
**Audit Date:** 2026-11-06  
**Status:** **RESEARCH-GRADE DATASET CERTIFIED (3,790 ELIGIBLE RECORDS)**  

---

## 1. Executive Summary

This report establishes the source data quality, multilingual NLP distribution, PII minimization status, retention compliance, and SIP research relevance screening for the Growww AI-Powered Investor Discovery Engine following Phase 3 standardization.

A total of **3,798 review records** across eight candidate application listings were evaluated through the canonical Phase 3 pipeline. **3,790 records** met all data governance, source permission, and quality integrity standards and were certified as research-eligible (`ELIGIBLE`). **8 historical demonstration records** were strictly quarantined under `SYNTHETIC_DEMO` and blocked from research outputs.

```text
========================================================================================
DATASET HEALTH VERDICT:
- Total Database Records       : 3,798
- Research-Eligible Records    : 3,790 (99.8%)
- Governance-Blocked Records   : 8 (0.2%, Quarantined Synthetic Demo)
- High Quality (Score >= 0.85) : 3,657 (96.3%)
- Acceptable Quality (0.60-0.84): 133 (3.5%)
- Low Quality (Score < 0.60)   : 0 (0.0%)
- Direct & Indirect SIP Reviews: 165 reviews (4.3% of public review stream)
- General Investment Evidence  : 605 reviews (16.0%)
- PII Leaks (Phones/Emails/PAN): 0 (100% Clean)
========================================================================================
```

---

## 2. Source Coverage & Sampling Windows

Public customer reviews were ingested via Apple App Store's official iTunes public syndication feed for India (`storefront: IN`) across all eight registered applications. 

> [!IMPORTANT]
> **Methodological Sampling Note:**
> Apple's RSS syndication service enforces a fixed capacity ceiling of 10 pages / 500 reviews per application. Consequently, the historical duration represented by 500 reviews varies dramatically depending on the review velocity of the application. Raw review counts must **never** be compared across applications as if their sampling timeframes or user populations were identical.

### 2.1 Application-by-Application Sampling Bounds

| Application | Role in Study | Apple App ID | Total Reviews | Eligible Records | Date Range Spanned | Coverage Duration | Sampling Window Context |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Groww** | Primary Case Study | `1404871703` | 404 | 404 | 2026-09-02 to 2026-11-04 | **63 days (~2.1 mo)** | High velocity; captures real-time sentiment. |
| **Zerodha Coin** | Direct MF Competitor | `1392892554` | 500 | 500 | 2020-02-23 to 2026-11-04 | **2,446 days (~80.5 mo)**| Low velocity; spans 6.5+ years of SIP history. |
| **Zerodha Kite** | Trading Competitor | `1449453802` | 487 | 487 | 2025-07-01 to 2026-11-04 | **491 days (~16.2 mo)**| Flagship trading app; 16-month retrospective. |
| **Upstox** | Discount Broker MF | `1584953620` | 449 | 449 | 2025-11-26 to 2026-11-05 | **344 days (~11.3 mo)**| Near complete 1-year annual cycle. |
| **Angel One** | Hybrid Broker MF | `1060530981` | 476 | 476 | 2025-12-24 to 2026-11-04 | **315 days (~10.4 mo)**| 10-month retail trading and MF cohort. |
| **INDmoney** | Wealth & MF Tracker | `1450178837` | 477 | 477 | 2025-11-13 to 2026-11-03 | **355 days (~11.7 mo)**| Near complete 1-year annual cycle. |
| **ET Money** | Direct MF Competitor | `1212752482` | 500 | 500 | 2025-01-27 to 2026-11-03 | **645 days (~21.2 mo)**| Pioneer MF app; spans nearly 2 years. |
| **Paytm Money** | Discount Broker MF | `1344431352` | 497 | 497 | 2025-02-07 to 2026-11-05 | **636 days (~20.9 mo)**| Discount broker MF app; spans 21 months. |
| **TOTAL** | — | — | **3,790** | **3,790** | **2020-02-23 to 2026-11-05**| **2,447 days (>6.5 yrs)**| Comprehensive multi-cohort cross-section. |

---

## 3. SIP Relevance & Coverage Analysis

### 3.1 Relevance Status Distribution

In Phase 3, reviews were screened using deterministic phrase matching against the version-controlled query bank (`config/review_queries.yml`). This distinguishes reviews with explicit SIP evidence from general investment feedback and unrelated app commentary:

| Relevance Status | Eligible Count | Percentage | Research Purpose & Handling |
| :--- | :---: | :---: | :--- |
| **DIRECT_SIP_RELEVANT** | **162** | **4.3%** | Reviews explicitly mentioning SIPs, monthly recurring instalments, or SIP setup/cancellation. Core evidence for Phase 4 pain-point modeling. |
| **INDIRECT_SIP_RELEVANT** | **3** | **0.1%** | Reviews describing mandate failures, auto-debit drops, or recurring instalment errors without explicit SIP tokens. Included in SIP evidence set. |
| **GENERAL_INVESTMENT_RELEVANT** | **605** | **16.0%** | Reviews discussing mutual funds, NAV, returns, redemption, portfolio statements, and KYC. Useful for general investor sentiment context. |
| **GENERAL_APP_FEEDBACK** | **1,083** | **28.6%** | Commentary on app interface, biometric login, system updates, crashes, and speed without specific financial product context. |
| **IRRELEVANT** | **1,945** | **51.3%** | Generic brief reviews ("Good app", "Superb", "Worst experience ever", "Fraud") lacking specific feature or journey descriptions. |
| **TOTAL** | **3,790** | **100.0%** | **Targeted SIP Sub-Corpus: 165 Reviews (Outputs: `outputs/sip_relevant_reviews.csv`)** |

### 3.2 Application-Wise SIP Relevance Proportions

The proportion of reviews identified as SIP-relevant closely mirrors the core product proposition of each application:

| Application | Sampling Window | Total Eligible | Direct SIP | Indirect SIP | Total SIP Evidence | SIP Proportion (%) | Product Context |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Zerodha Coin** | 2020 to 2026 (6.5 yrs) | 500 | 49 | 1 | **50** | **10.0%** | Dedicated direct mutual fund and SIP app. |
| **ET Money** | 2025 to 2026 (21 mo) | 500 | 39 | 0 | **39** | **7.8%** | Direct mutual fund investment & SIP platform. |
| **Paytm Money** | 2025 to 2026 (21 mo) | 497 | 26 | 0 | **26** | **5.2%** | Mutual funds and equity discount broker. |
| **Groww** | Sept to Nov 2026 (63 d)| 404 | 15 | 0 | **15** | **3.7%** | Comprehensive investment platform (Stocks, MF, F&O). |
| **INDmoney** | 2025 to 2026 (12 mo) | 477 | 14 | 1 | **15** | **3.1%** | Wealth tracking, US stocks, and mutual funds. |
| **Upstox** | 2025 to 2026 (11 mo) | 449 | 6 | 0 | **6** | **1.3%** | Primarily equity and F&O trading platform. |
| **Zerodha Kite** | 2025 to 2026 (16 mo) | 487 | 6 | 0 | **6** | **1.2%** | Flagship equity and derivatives platform. |
| **Angel One** | 2025 to 2026 (10 mo) | 476 | 1 | 0 | **1** | **0.2%** | Active retail trading broker. |
| **TOTAL** | — | **3,790** | **162** | **3** | **165** | **4.3%** | High-signal investor journey sub-corpus. |

### 3.3 SIP Research Coverage Flags (Boolean Distribution)

Across all 3,790 eligible research records, preliminary boolean flags were generated to assist Phase 4 AI interpretation:

| Coverage Dimension Flag | Matched Records | Sample Review Topic |
| :--- | :---: | :--- |
| `mentions_sip` | 156 | Explicit references to SIP or Systematic Investment. |
| `mentions_mutual_fund` | 368 | Mentions of mutual funds, AMCs, index funds, debt funds. |
| `mentions_payment` | 259 | Mentions of debits, deduction failures, missing balance. |
| `mentions_mandate` | 26 | Autopay mandates, NACH registration, e-mandate rejection. |
| `mentions_autopay` | 3 | Explicit autopay and standing instruction issues. |
| `mentions_instalment` | 3 | Monthly instalment tracking, missing instalment credit. |
| `mentions_nav` | 45 | NAV allotment date confusion, cut-off time discrepancies. |
| `mentions_returns` | 244 | Negative returns, portfolio loss, XIRR calculations. |
| `mentions_units` | 34 | Delay in unit allotment, unit statement reconciliation. |
| `mentions_pause_stop` | 115 | Cancelling or pausing recurring investments. |
| `mentions_restart` | 14 | Resuming discontinued investments. |
| `mentions_redemption` | 106 | Unit redemption delays, exit loads, bank payouts. |
| `mentions_support` | 459 | Unresolved customer support tickets, AI bot frustration. |
| `mentions_kyc` | 97 | Aadhaar/PAN re-KYC, CKYC verification delays. |
| `mentions_trust` | 435 | Trust deficit, allegations of fraud, hidden charges. |

---

## 4. Multilingual Language & Script Distribution

Indian retail investors frequently utilize mixed languages, transliterated Hindi, and code-switching. The Phase 3 language detector categorized the corpus without forcing Hinglish into English:

| Language Tag | Language Description | Script | Record Count | Percentage |
| :--- | :--- | :--- | :---: | :---: |
| `en` | English | Latin | 3,256 | 85.7% |
| `mixed` | Code-Switching (English + Hindi) | Latin / Mixed | 268 | 7.1% |
| `hi-Latn` | Hinglish / Romanized Hindi | Latin | 231 | 6.1% |
| `unknown` | Ambiguous / Very Short | Unknown | 34 | 0.9% |
| `hi` | Hindi (Devanagari script) | Devanagari | 8 | 0.2% |
| `other` | Indic Scripts (Tamil, Telugu) | Other Indic | 1 | 0.0% |
| **TOTAL** | — | — | **3,790** | **100.0%** |

> [!NOTE]
> Hinglish (`hi-Latn`) and code-switching (`mixed`) together account for **13.2% (499 reviews)** of the corpus. Phase 4 prompts must explicitly accommodate Hindi and Hinglish idioms (e.g., "paise kat gaye lekin units nahi mile", "mandate reject ho gaya").

---

## 5. PII Minimization & Data Privacy Audit

A zero-leakage invariant was maintained across the entire database:
1. **Author Identity Stripping:** Reviewer author names, profile URLs, and reviewer identifiers are stripped at ingestion and never enter `reviews`.
2. **Regex Redaction:** The pipeline evaluated phone numbers, emails, PAN cards, bank account numbers, and UPI handles. In the public Apple review stream, no unredacted phone numbers, emails, or PAN tokens exist.
3. **Synthetic Demonstration Separation:** The 8 sample records from Phase 1 remain strictly marked as `SYNTHETIC_DEMO` and are excluded from `master_investor_feedback.csv` and `outputs/sip_relevant_reviews.csv`.

---

## 6. Retention & Governance Audit

1. **Policy Period:** Under the research governance policy, public review records are retained for **365 days** from ingestion.
2. **Expiry Evaluation:** All 3,790 genuine reviews have `retention_expiry_at` set to November 2027 (`ACTIVE`).
3. **Deletion Workflows:** Automated gates in `RetentionManager.is_eligible_for_research()` ensure that any record with `deletion_status != 'ACTIVE'` is excluded from research exports.

---

## 7. Data Quality Scoring Summary

Records were evaluated across 8 quality dimensions (provenance, application ID, store ID, text substance, date validity, rating validity, language confidence, PII status, and retention):

- **HIGH_QUALITY (Score >= 0.85):** **3,657 reviews (96.3%)**
  Complete metadata, verified application ID, substantive text, valid rating and date.
- **ACCEPTABLE (Score 0.60 - 0.84):** **133 reviews (3.5%)**
  Brief text ("Ok", "Nice app") or lower language confidence, but valid provenance and metadata.
- **LOW_QUALITY (Score < 0.60):** **0 reviews (0.0%)**
- **BLOCKED:** **8 records (Quarantined Synthetic Demo)**

---

## 8. Exported Research Datasets Inventory

| File Path | Format | Record Count | File Size | Description |
| :--- | :--- | :---: | :---: | :--- |
| `master_investor_feedback.csv` | CSV | 3,790 | ~3.58 MB | Complete master research-ready dataset of all eligible reviews. |
| `master_investor_feedback.parquet` | Parquet | 3,790 | ~1.26 MB | Columnar compressed research dataset for high-performance analytics. |
| `outputs/sip_relevant_reviews.csv` | CSV | 165 | ~195 KB | Dedicated sub-corpus of direct and indirect SIP-relevant reviews. |
| `outputs/general_investment_reviews.csv`| CSV | 605 | ~701 KB | Mutual fund, NAV, and general investment review evidence. |
| `outputs/blocked_records_report.csv` | CSV | 8 | ~1.7 KB | Governance audit report of quarantined synthetic records. |
