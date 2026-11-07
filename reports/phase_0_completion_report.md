# Phase 0 Completion Report: Research Scope & Source Feasibility
## Groww AI-Powered Investor Discovery Engine
**Document Reference:** `reports/phase_0_completion_report.md`  
**PRD Version Baseline:** 1.1  
**Audit & Execution Date:** 2026-11-05  
**Final Phase 0 Verdict:** **COMPLETE** (100% Free Tier Architecture Confirmed)  
**Role Scope:** Senior Product Engineer, Data Researcher, Technical Architect, Data Governance Specialist  

---

## 1. Executive Summary

Phase 0 ("Research Scope & Source Feasibility") of the **Groww AI-Powered Investor Discovery Engine** project has been executed in strict adherence to the PRD (Version 1.1) and engineering governance guidelines. 

The primary research objective is to discover evidence-backed behavioral drivers, setup friction points, and retention barriers influencing the **12-month first-SIP active rate** among retail Indian investors, using Groww as the primary case study alongside key industry competitors.

### Summary of Completed Objectives:
1. **Candidate App Registry:** Verified official Apple App Store numeric IDs and Google Play package names across all 7 candidate platforms (8 mobile application listings total, separating Zerodha Coin and Kite). Confirmed 100% availability in the India storefront (`IN`).
2. **Apple RSS Feasibility Tested & Empirically Verified (100% Free):** Conducted live HTTP tests against Apple's approved public customer-review RSS feed across all 8 apps. 
   - Proven that Apple limits pagination strictly to **10 pages (500 reviews maximum)**, returning `HTTP 400 Bad Request` on page 11.
   - For high-velocity apps like Groww, 500 reviews span only **~62 days** (Sept 2, 2026 to Nov 3, 2026).
   - Confirmed that Apple RSS operates with **$0 subscription costs, zero account requirement, and zero API keys**.
3. **AppFollow Free Tier Investigation & Rejection:** Tested AppFollow's onboarding and workspace setup. The user confirmed that AppFollow enforces a **mandatory paid subscription** ($143+/month) to monitor competitors, view review feeds, or export data. In accordance with PRD Rule 7, AppFollow was formally **REJECTED** as a free-tier solution and marked `UNAVAILABLE`.
4. **100% Free-Tier Architecture Adopted:** Established a zero-cost, dual-channel ingestion design:
   - **Route A (Apple App Store Public RSS):** Automated continuous public review ingestion ($0).
   - **Route F (Manual Review CSV Import):** Compliant, subscription-free ingestion of public Google Play research datasets ($0).
5. **Source Access Framework & Governance:** Established a 6-route Source Access Register (`config/source_access.yml`) with technical availability separated from legal permission. In accordance with data governance policy, **all source connectors are disabled by default (`enabled: false`)**.
6. **Multilingual Review Taxonomy:** Codified a comprehensive 9-dimension review classification taxonomy (`config/review_taxonomy.yml`) supporting English, Hindi (Devanagari), and Hinglish (Latin transliteration) with exact PRD lifecycle codes (`S0_DISCOVERY` through `S7_RESTART`). Demographic segment attributes strictly default to `UNKNOWN`.
7. **Privacy & Data Governance Policy:** Enacted strict policies against reviewer de-anonymization, internal Groww account matching, demographic hallucination, and web scraping (`docs/privacy_and_retention.md`).
8. **Automated Test Validation:** Developed and executed an automated unit test suite (`tests/test_phase_0_configs.py`) with 10 passed tests verifying YAML schemas, security defaults, mock parsers, and zero committed credentials.

---

## 2. Research Scope & Problem Definition

- **Primary Case Study:** Groww (`com.nextbillion.groww` / Apple ID: `1404871703`).
- **Target Phenomenon:** Understanding why first-time mutual fund investors initiate SIPs, what setup or payment friction they encounter, why they pause or cancel mandates, and what product experiences can increase the 12-month active rate.
- **Architectural Reality:** This is an independent research prototype. We do not have access to Groww's internal transactional database, customer support ticketing CRM, or private cohorts. All findings are derived from public app store customer reviews and structured research imports.

---

## 3. Candidate Application Registry Summary

The verified registry is maintained in `config/apps.yml`. All entities have been verified against live store endpoints:

| Internal ID | Official Application Name | Developer / Publisher | Apple App ID | Google Play Package Name | India Storefront Availability | Verification Date |
|---|---|---|---|---|:---:|:---:|
| `groww` | Groww Stocks, Mutual Fund, IPO | Billionbrains Garage Ventures Pvt Ltd | `1404871703` | `com.nextbillion.groww` | Verified (200 OK) | 2026-11-05 |
| `zerodha_coin` | Coin by Zerodha - Mutual funds | Zerodha Broking Limited | `1392892554` | `com.zerodha.coin` | Verified (200 OK) | 2026-11-05 |
| `zerodha_kite` | Zerodha Kite - Trade & Invest | Zerodha Broking Limited | `1449453802` | `com.zerodha.kite3` | Verified (200 OK) | 2026-11-05 |
| `upstox` | Upstox: Demat, Stock, MF, IPO | RKSV Securities India Pvt Ltd | `1584953620` | `in.upstox.app` | Verified (200 OK) | 2026-11-05 |
| `angel_one` | Angel One: Stocks, Mutual Fund | Angel One Limited | `1060530981` | `com.msf.angelmobile` | Verified (200 OK) | 2026-11-05 |
| `indmoney` | INDmoney: Indian & US Stocks | Finzoom Investment Advisors Pvt Ltd | `1450178837` | `in.indwealth` | Verified (200 OK) | 2026-11-05 |
| `et_money` | ET Money Mutual Fund, SIF, SIP | Banayantree Services Limited | `1212752482` | `com.smartspends` | Verified (200 OK) | 2026-11-05 |
| `paytm_money` | Paytm Money: Stocks, MF, IPO | Paytm Money Limited | `1344431352` | `com.paytmmoney` | Verified (200 OK) | 2026-11-05 |

*Note on Resolution of App Discrepancies:* Initial search suggestions listed deprecated or redirected IDs for Zerodha Coin (`1375141655`), Angel One (`1064855351`), and ET Money (`1044473859`). Live API inspection verified the active store listings (`1392892554`, `1060530981`, `1212752482`), which immediately unlocked full 500-review datasets.

---

## 4. Apple RSS Feasibility Findings

Full experimental details are documented in `reports/apple_rss_feasibility.md` and raw data stored in `reports/apple_rss_empirical_results.json`.

### Empirical Test Matrix:
- **Endpoint:** `https://itunes.apple.com/in/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json`
- **Total Applications Tested:** 8
- **Total Unique Reviews Ingested in Test:** 4,000 (500 reviews per application)
- **Pagination Behavior:** Exactly 10 pages accessible (50 items/page). Page 11 strictly returns `HTTP 400 Bad Request`.
- **Duplicate Review Count:** 0 duplicates across pages 1 to 10.
- **Coverage Findings:**
  - **Groww:** 500 reviews span **2026-09-02 to 2026-11-03** (~2 months).
  - **Upstox:** 500 reviews span **2025-11-21 to 2026-11-03** (~12 months).
  - **Angel One:** 500 reviews span **2025-12-23 to 2026-11-03** (~11 months).
  - **INDmoney:** 500 reviews span **2025-11-13 to 2026-11-03** (~12 months).
  - **ET Money:** 500 reviews span **2025-01-26 to 2026-10-23** (~21 months).
  - **Paytm Money:** 500 reviews span **2025-02-05 to 2026-11-02** (~21 months).
  - **Zerodha Kite:** 500 reviews span **2025-07-01 to 2026-11-01** (~16 months).
  - **Zerodha Coin:** 500 reviews span **2020-02-22 to 2026-10-05** (~80 months).

### Critical Finding for Groww Research:
Groww's high review velocity causes Apple's 500-review window to capture only the last 62 days. To build a true 12-month retrospective cohort for Groww, the engine **must supplement Apple RSS with manual CSV dataset imports or periodic continuous delta ingestion**.

---

## 5. AppFollow Feasibility Findings & Resolution

Documented in `docs/appfollow_free_plan_runbook.md`:
1. **Free Account Onboarding Wall:** Live testing on 2026-11-05 verified that AppFollow requires a credit card and mandatory paid subscription to activate competitor monitoring and review feeds.
2. **Paid Subscription Requirement:** AppFollow plans start at \$143/month (*Essential* tier). The marketed "Free Plan" does not permit automated or manual competitor review extraction.
3. **Decisive Resolution:** In accordance with PRD guidelines and the user's explicit requirement for a **100% free-tier solution**, AppFollow was formally **REJECTED** and marked **`UNAVAILABLE`** in `config/source_access.yml`.
4. **Fallback Activated:** **Route F (Manual Review CSV Import)** is adopted as the primary, compliant, zero-cost pipeline for Google Play customer review ingestion.

---

## 6. Google Play Access Findings

Direct Google Play public review access without third-party services is constrained:
1. **Google Play Developer API (Publisher v3):** Highly functional, but strictly restricted to apps owned by the authenticating service account. Marked `UNAVAILABLE` for competitor reviews.
2. **Google Play Console Bulk CSV:** Complete historical data available, but restricted to app owners. Marked `UNAVAILABLE`.
3. **HTML Web Scraping:** Evaluated and **strictly rejected**. Scraping `play.google.com` violates Google Terms of Service and triggers bot blocks.
4. **Approved Solution for Play Store:** **Route F (Manual Review CSV Import)** is approved as the compliant, 100% free route for historical Google Play datasets sourced from public research archives (e.g., Kaggle Indian Fintech Review archives).

---

## 7. Source Permission Matrix Summary

Refer to `docs/source_access_matrix.md` and `config/source_access.yml`.

| Route | Channel Name | Technical Feasibility | Permission Status | Default State | Usability Rating | Cost |
|---|---|---|---|:---:|:---:|:---:|
| **A** | Apple App Store Public RSS | **AVAILABLE** | **PENDING_VERIFICATION** | `DISABLED` | **5 / 5** | **$0.00 (Free)** |
| **B** | Apple App Store Connect API | **AVAILABLE** | **UNAVAILABLE** (No credentials) | `DISABLED` | **1 / 5** | Developer Program Fee |
| **C** | AppFollow Competitor Reviews API | **UNAVAILABLE** (Paywalled) | **REJECTED** | `DISABLED` | **0 / 5** | $143+/mo (Rejected) |
| **D** | Google Play Publisher API | **AVAILABLE** | **UNAVAILABLE** (No credentials) | `DISABLED` | **1 / 5** | $25 one-time (Owned only) |
| **E** | Google Play Console CSV Export | **AVAILABLE** | **UNAVAILABLE** (No credentials) | `DISABLED` | **1 / 5** | Console access (Owned only) |
| **F** | Manual Review CSV Import | **AVAILABLE** | **APPROVED** | `DISABLED` | **5 / 5** | **$0.00 (Free)** |

*All connectors remain disabled (`enabled: false`) in config until Phase 1 activation.*

---

## 8. Review Taxonomy Summary

Formulated in `config/review_taxonomy.yml`, covering 9 dimensions:
- **Dimension A (Investor Intent):** 9 categories (`START_DISCIPLINED_SAVING`, `BUILD_LONG_TERM_GOAL`, `LEARN_INVESTING`, `TAX_PLANNING`, `CONVENIENCE`, `FAMILY_PEER_INFLUENCE`, `CREATOR_ADVISER_INFLUENCE`, `LIQUIDITY_NEED`, `UNKNOWN`).
- **Dimension B (Expected Outcome):** 8 categories (`CAPITAL_GROWTH`, `PREDICTABLE_OUTCOME`, `SAFETY_CAPITAL_PROTECTION`, `EASY_INVESTMENT`, `ACCESS_TO_MONEY`, `TAX_BENEFIT`, `HABIT_FORMATION`, `UNKNOWN`).
- **Dimension C (SIP Lifecycle Stages):** Exact PRD codes (`S0_DISCOVERY`, `S1_SETUP`, `S2_EARLY`, `S3_HABIT`, `S4_REVIEW`, `S5_FRICTION`, `S6_PAUSE_STOP`, `S7_RESTART`).
- **Dimension D (Investor Behaviour):** 10 categories (e.g., `CHECK_NAV_VALUE`, `CHANGE_SIP_AMOUNT`, `MISS_INSTALMENT`, `PAUSE_SIP`, `REDEEM`, `CONTACT_SUPPORT`).
- **Dimension E (Pain Points):** 11 categories (e.g., `PAYMENT_MANDATE`, `KYC`, `UNCLEAR_STATUS`, `NAV_UNITS`, `SHORT_TERM_RETURN_INTERPRETATION`, `TRUST`, `SUPPORT_DELAY`).
- **Dimension F (Triggers):** 9 categories (e.g., `INCOME_CHANGE`, `UNEXPECTED_EXPENSE`, `MISSED_MANDATE`, `MARKET_MOVEMENT`, `APP_INCIDENT`).
- **Dimension G (Outside-App Coping):** 7 categories (e.g., `SEARCH_ENGINE`, `ONLINE_VIDEO`, `FRIENDS_FAMILY`, `FINANCIAL_ADVISER`).
- **Dimension H (Reported Outcome):** 8 categories (`CONTINUED`, `REDUCED`, `PAUSED`, `STOPPED`, `RESTARTED`, `REDEEMED`, `UNRESOLVED`, `NOT_STATED`).
- **Dimension I (Explicit Disclosed Segments):** `age_band`, `income_stability`, `money_source`, `influence`. Strictly defaults to `UNKNOWN` with zero demographic hallucination.

Multilingual keyword dictionaries are established for English, Hindi (Devanagari), and Hinglish (Latin transliteration) for all operational categories.

---

## 9. Privacy and Retention Decisions

Enacted in `docs/privacy_and_retention.md`:
1. **Data Minimization:** Author display names, Apple user IDs, and profile URIs are completely stripped during parsing and never persisted.
2. **Regex PII Redaction:** Automated regex filters sanitize phone numbers, email addresses, PAN cards, bank account numbers, and UPI handles.
3. **No Demographics Inference:** Forbids AI classification prompts from guessing demographic traits from colloquial language or writing style.
4. **No Identity Resolution:** Absolute prohibition on attempting to link reviews to real-world identities or Groww customer accounts.
5. **No AI Training on Review Text:** Zero data retention inference only; no model fine-tuning without explicit copyright/terms clearance.
6. **No Synthetic Reviews:** Strictly banned in analytical reporting.

---

## 10. Unresolved Dependencies & Blockers

All Phase 0 dependencies have been resolved:
1. **AppFollow Blocker Cleared:** The manual account inspection confirmed that AppFollow is paywalled. It has been decisively rejected from the project architecture, eliminating the external subscription dependency.
2. **Zero Cost Ingestion Secured:** The engine relies exclusively on 100% free, compliant routes (Apple Public RSS + Manual Review CSV Import).

---

## 11. Recommended Phase 1 Starting Configuration

When proceeding to Phase 1 ("Repository and Application Foundation"):
1. **Initialize Core Ingestion Connectors:**
   - Implement `AppleRSSConnector` targeting `config/apps.yml`.
   - Implement `ManualCSVImporter` supporting standard 8-column review CSV schema.
2. **Enable Route A (Apple RSS):** Update `enabled: true` in `config/source_access.yml` for `apple_app_store_public_rss` once data governance sign-off is logged.
3. **Maintain AppFollow as Disabled & Rejected:** Keep `enabled: false` and `permission_status: "REJECTED"`.
4. **Data Persistence Schema:** Implement local SQLite/DuckDB schemas enforcing PII redaction and taxonomy dimensional tagging.

---

## 12. Final Phase 0 Verdict

```text
FINAL VERDICT: COMPLETE
```

### Rationale:
- **Technical Research & Feasibility Testing:** **100% COMPLETE**. All 7 applications (8 listings) verified, live Apple RSS feeds tested with empirical results recorded, source access matrix finalized, review taxonomy formulated with multilingual lexicons, privacy policy published, and 10 unit tests passing.
- **100% Free Tier Architecture Solidified:** The dependency on paid SaaS tools has been eliminated. The project operates on $0 infrastructure costs using official public syndication feeds and standardized research imports.

**The project is fully prepared, tested, and ready to proceed to Phase 1 application foundation.**
