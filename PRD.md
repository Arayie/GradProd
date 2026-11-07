# Product Requirements Document (PRD) – Version 1.1
## Growww – AI-Powered Investor Discovery Engine

---

### 1. Executive Summary & Problem Context
The **Growww AI-Powered Investor Discovery Engine** is an independent research platform designed to systematically analyze publicly available customer reviews across top Indian investment applications.

The central research inquiry focuses on understanding the customer journey around **Systematic Investment Plans (SIPs)**:
- Why first-time investors begin mutual fund SIPs.
- What expectations they bring regarding returns, liquidity, safety, and effort.
- What operational friction they face during onboarding, KYC, and mandate setup.
- Why payment debits fail or cause confusion.
- How user behavior shifts across the first 12 months.
- What triggers cause users to pause, stop, or restart SIPs.
- What product experiences can drive improvement in the **12-month first-SIP active rate**.

> [!IMPORTANT]
> **Independent Research Boundary:**
> This engine operates strictly as an independent research prototype. It does not possess access to Groww's internal transactional customer databases, proprietary CRM ledgers, or private retention cohorts. Public reviews represent qualitative discovery signals and customer sentiment, not audited financial records or definitive proof of retention.

---

### 2. Research Scope & Candidate Applications
The primary case study is **Groww**, benchmarked against key peer platforms in India:
1. **Groww** (Primary case study: Direct mutual funds, stocks, IPOs)
2. **Zerodha Coin** (Direct mutual funds and NPS platform)
3. **Zerodha Kite** (Flagship demat trading and equity ecosystem)
4. **Upstox** (Discount broker with mutual funds and equity)
5. **Angel One** (Full-service hybrid broker with widespread tier-2/3 penetration)
6. **INDmoney** (Super-money app with US stocks, mutual funds, and net-worth tracking)
7. **ET Money** (Direct mutual funds, SIP advisory, and smart deposit tracking)
8. **Paytm Money** (Discount broker and direct mutual fund platform)

---

### 3. Data Ingestion Architecture & Free-Tier Governance
Following Phase 0 feasibility investigations, commercial aggregator **AppFollow was permanently removed** due to its paid subscription requirement. The architecture operates on a 100% free-tier framework:
- **Apple App Store Public RSS Feed:** Approved syndication endpoint for the India (`IN`) storefront. Ingests up to 500 reviews per app without credentials or API keys.
- **Manual Review CSV Import:** Compliant fallback route for Google Play customer reviews sourced from open public research datasets or verified manual dumps.
- **Security & Privacy Invariants:**
  - Automated redaction of reviewer names, nicknames, and profile links.
  - Regex sanitization of Indian phone numbers, emails, PANs, bank accounts, and UPI handles.
  - Demographics strictly default to `UNKNOWN`. No demographic guessing or profiling.
  - Source connectors disabled by default (`enabled: false`) until verified.

---

### 4. SIP Lifecycle Stages
The engine classifies customer review journeys across 8 discrete stages:
- **`S0_DISCOVERY`:** Exploring funds, comparing past performance, browsing app UI.
- **`S1_SETUP`:** Initial onboarding, KYC, bank linking, e-mandate/autopay setup.
- **`S2_EARLY`:** Months 1–3 of SIP. First debits, initial NAV allocation, portfolio viewing.
- **`S3_HABIT`:** Months 4–12. Routine, repeated monthly debits running smoothly.
- **`S4_REVIEW`:** Portfolio health checks, evaluating XIRR/CAGR, comparing benchmarks.
- **`S5_FRICTION`:** Operational failures, delayed NAV, mandate bounce fees, unhelpful support.
- **`S6_PAUSE_STOP`:** Active decisions to pause installments, cancel autopay, or stop SIP.
- **`S7_RESTART`:** Resuming a paused SIP, stepping up monthly amounts, or re-initiating after a break.

---

### 5. Multi-Phase Implementation Roadmap
- **Phase 0:** Research Scope & Source Feasibility (Completed).
- **Phase 1:** Repository and Application Foundation (Current Phase: Modular Streamlit app, SQLite schema, CSV import, sample data mode).
- **Phase 2:** Automated Ingestion Connectors (Apple RSS connector, checkpointing).
- **Phase 3:** Data Normalization & Hygiene (Deduplication, PII scrubbing, language tagging).
- **Phase 4:** AI Classification & Enrichment (Taxonomy mapping, evidence spans, confidence scoring).
- **Phase 5:** Analytics & Discovery Dashboard (SIP retention insights, opportunity scoring).
