# Source Access & Feasibility Matrix
## Comprehensive Evaluation of Public Customer Review Ingestion Routes
**Phase 0 Deliverable | Research Scope & Source Feasibility**  
**Investigation Date:** 2026-11-05  
**Governance Standard:** Principle of Least Privilege, Explicit Consent Separation, Zero Web Scraping  

---

## 1. Overview & Architectural Principle

The Groww AI-Powered Investor Discovery Engine evaluates publicly accessible customer reviews across Indian wealth management applications. Because our engine operates as an **independent research prototype**, we do not possess internal Groww credentials, private customer databases, or proprietary telemetry cohorts.

To prevent architectural brittleness, legal non-compliance, and data contamination, six ingestion routes are systematically evaluated across two independent criteria:
1. **Technical Availability:** Can the endpoint or file format be programmatically accessed and parsed with reliable stability?
2. **Permission & Data Governance Status:** Is collection legally sanctioned under platform terms of service, data privacy regulations (e.g., DPDP Act 2023), and ethical AI processing norms?

> [!IMPORTANT]
> **Strict Governance Mandate:** Every connector is configured with `enabled: false` by default in `config/source_access.yml`. A route is never enabled based on technical reachability alone; explicit permission verification is mandatory.

---

## 2. Source Comparison Matrix

| Route ID | Collection Route | Technical Availability | Permission Status | Account Ownership Required | Historical Depth | India Coverage | Usability Score (1-5) | Default State |
|---|---|---|---|---|---|---|:---:|:---:|
| **A** | **Apple App Store Public RSS** | **AVAILABLE** | **PENDING_VERIFICATION** | None (Public) | 500 reviews (~2 mo for Groww, up to 80 mo for Coin) | Full (All 8 verified apps) | **5 / 5** (100% Free Automated Route) | `DISABLED` |
| **B** | **Apple App Store Connect API** | **AVAILABLE** | **UNAVAILABLE** (No credentials) | Yes (Admin / Developer) | Full app history (owned apps) | N/A (Groww owned only) | **1 / 5** (Competitors inaccessible) | `DISABLED` |
| **C** | **AppFollow Competitor Feed & API** | **UNAVAILABLE** (Paywalled) | **REJECTED** | Third-party SaaS account | 7 days on Free / Paid required | Capped at 2 apps on Free | **0 / 5** (Subscription mandatory; rejected) | `DISABLED` |
| **D** | **Google Play Publisher API (v3)**| **AVAILABLE** | **UNAVAILABLE** (No credentials) | Yes (Service Account) | Full app history (owned apps) | N/A (Groww owned only) | **1 / 5** (Competitors inaccessible) | `DISABLED` |
| **E** | **Google Play Console CSV Export** | **AVAILABLE** | **UNAVAILABLE** (No credentials) | Yes (Console access) | Full export history (owned apps) | N/A (Groww owned only) | **1 / 5** (Competitors inaccessible) | `DISABLED` |
| **F** | **Manual Review CSV Import** | **AVAILABLE** | **APPROVED** | None (File upload) | Arbitrary historical cohorts (Provided in dataset) | Full (Any app in CSV) | **5 / 5** (100% Free Google Play Route) | `DISABLED` |

---

## 3. Deep-Dive Analysis of Collection Routes

### Route A: Apple App Store Public RSS
- **Mechanism:** HTTP GET against `https://itunes.apple.com/in/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json`.
- **Ownership Required:** None. Approved public syndication channel.
- **Empirical Feasibility:** Tested and verified across all 8 application listings in the Indian storefront. Exactly 500 reviews accessible per application. Zero 5xx errors; strict 400 Bad Request on page 11.
- **Privacy Controls:** Review ID, title, text body, star rating, app version, and timestamp retained. Author name and author profile URI are strictly stripped during ingestion.
- **Limitation:** For high-velocity apps like Groww, 500 reviews span only ~62 days. Insufficient for a standalone 12-month retention cohort without periodic polling.
- **Verdict:** Highly usable as the primary automated public review source.

### Route B: Apple App Store Connect Owner API
- **Mechanism:** Authenticated REST API (`api.appstoreconnect.apple.com/v1/apps/{id}/customerReviews`) using JSON Web Tokens (JWT) signed with private keys.
- **Ownership Required:** Yes. Requires Team ID, Key ID, and `.p8` private key generated in App Store Connect.
- **Limitation:** Cannot access competitor reviews (Zerodha, Upstox, Angel One, INDmoney, ET Money, Paytm Money). As an independent research project without Groww organization credentials, this route is marked `UNAVAILABLE`.
- **Verdict:** Preserved in architecture for future enterprise integration, currently disabled.

### Route C: Google Play Public Competitor Reviews via AppFollow
- **Mechanism:** Third-party aggregator REST API v2 (`https://api.appfollow.io/api/v2/reviews`) with token authentication.
- **Ownership Required:** AppFollow paid account.
- **Verification Finding (2026-11-05):** During live onboarding, AppFollow demands a mandatory credit card and subscription payment ($143+/month) to access competitor review tracking, exports, and feeds.
- **Verdict:** **REJECTED & MARKED UNAVAILABLE**. Does not satisfy the zero-cost free-tier requirement. Deprecated in favor of Route F (Manual Review CSV Import).

### Route D: Google Play Developer API (Android Publisher v3)
- **Mechanism:** Google Cloud Service Account OAuth 2.0 querying `androidpublisher.reviews.list`.
- **Ownership Required:** Yes. Google Play Developer Console ownership of `com.nextbillion.groww`.
- **Limitation:** Zero competitor visibility. Requires private internal credentials.
- **Verdict:** Marked `UNAVAILABLE`.

### Route E: Google Play Console Bulk Reviews CSV Export
- **Mechanism:** Manual download of monthly review archives from Google Play Console (Reports -> Reviews).
- **Ownership Required:** Yes. Account administrator credentials.
- **Limitation:** Available only to app owners.
- **Verdict:** Marked `UNAVAILABLE`.

### Route F: Manual Review CSV Fallback Import
- **Mechanism:** Multipart file upload or local file ingestion supporting predefined schema (`review_id`, `app_name`, `platform`, `star_rating`, `review_date`, `app_version`, `review_title`, `review_text`).
- **Ownership Required:** None.
- **Data Governance Enforcements:**
  - Automated PII scrubbing on ingest (regex detection for phone numbers, emails, PAN numbers, bank account numbers).
  - Schema validation.
  - Review text preserved in original scripts (English, Hindi, Hinglish).
- **Advantage:** Enables ingesting deep historical Google Play review datasets obtained through sanctioned research dumps or manual audits without breaking platform terms.
- **Verdict:** **APPROVED** as the primary multi-platform historical fallback.

---

## 4. Disallowed Collection Methods

To maintain documentation and research integrity, the following collection techniques are **strictly prohibited and architecturally blocked**:

1. **Direct Google Play Store HTML Scraping:** Banned. Violates Google Terms of Service; vulnerable to IP blocking, bot traps, and layout changes.
2. **Apple App Store Web Scraping:** Banned. Bypassing public RSS to parse HTML on `apps.apple.com` is prohibited.
3. **Headless Browser Automation:** Tools such as Puppeteer, Selenium, or Playwright for automated review scraping are strictly prohibited.
4. **CAPTCHA / Rate-Limit Bypass:** Reverse engineering session tokens or using rotating proxy networks to bypass security boundaries is prohibited.

---

## 5. Architectural Recommendation for Phase 1

1. **Automated Continuous Ingestion:** Implement `AppleRSSConnector` (Route A) with automated deduplication and weekly delta polling.
2. **Historical Cohort Ingestion:** Implement `ManualCSVImporter` (Route F) with strict schema validation and PII regex filters for historical Google Play data (including pre-September 2026 Groww reviews).
3. **Secondary SaaS Ingestion:** Keep `AppFollowConnector` (Route C) in a modular plugin state, disabled until the user provides manual API credentials and determines if paid quotas are warranted.
