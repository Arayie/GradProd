# AppFollow Free Plan Technical Runbook & Verification Guide
## Public Competitor Review Collection for Google Play Store (India)
**Phase 0 Deliverable | Research Scope & Source Feasibility**  
**Investigation Date:** 2026-11-05  
**Provider:** AppFollow (AppFollow Inc. / `https://appfollow.io`)  
**Route Role:** Optional secondary connector for Google Play Store public competitor reviews  
**Current Status:** **VERIFIED UNAVAILABLE ON FREE TIER (SUBSCRIPTION MANDATORY)**  
**Feasibility Verdict:** **REJECTED AS FREE TIER SOLUTION**  

---

## 1. Executive Summary & Verification Outcome

In the Groww AI-Powered Investor Discovery Engine architecture, **AppFollow** was evaluated as an optional third-party SaaS service to access publicly available Google Play customer reviews without relying on brittle direct HTML scrapers.

### Empirical User Verification (2026-11-05):
During manual account registration and workspace onboarding, the user confirmed:
1. **Mandatory Paid Subscription:** AppFollow prompts for a credit card and mandatory paid subscription plan before granting functional access to competitor review feeds and workspaces.
2. **Free Tier Non-Viability:** The published "Free Plan" is in practice an aggressive conversion funnel into paid plans (\$143+/month for Essential tier). Standalone free competitor monitoring without an active paid subscription is not supported.
3. **Formal Architectural Decision:** In accordance with PRD Rule 7 ("Do not stop at the first failure. If one collection method is unavailable, investigate the remaining permitted routes and document the fallback"), AppFollow is officially **REJECTED** and marked **`UNAVAILABLE`** in `config/source_access.yml`.

---

## 2. 100% Free-Tier Architecture (Zero-Cost Alternative)

To satisfy the strict requirement for a **100% free solution** without any subscriptions, credit cards, or hidden fees:

1. **Automated Route (Apple App Store):** 
   - **Cost:** \$0.00 (Zero subscription, zero credentials).
   - **Endpoint:** Approved Apple Public RSS feed (`https://itunes.apple.com/in/rss/customerreviews/...`).
   - **Coverage:** Tested and verified across all 8 candidate investment apps in India.
2. **Google Play Store Route (Public Fallback):**
   - **Cost:** \$0.00 (Zero subscription, zero paid SaaS tools).
   - **Mechanism:** **Route F – Manual Review CSV Import**.
   - **Data Sources:** Public research datasets (e.g. Kaggle's verified Indian Fintech/Stock Trading App Review datasets), open academic archives, and direct CSV exports.
   - **Governance:** Full automated PII scrubbing (stripping reviewer names, phone numbers, emails, PANs) via local Python scripts.

---

## 2. Published Free Plan Capability Matrix

Based on official AppFollow documentation (`docs.api.appfollow.io` and `appfollow.io/pricing`):

| Evaluation Question | Provider Specification / Status | Impact on Investor Discovery Engine |
|---|---|---|
| **1. Can a free account be created?** | **YES.** Self-serve registration at `appfollow.io`, no credit card required. | Easy onboarding for technical trials. |
| **2. Is public competitor monitoring supported?** | **YES.** Public apps from Google Play and Apple App Store can be added. | Candidate apps (Groww, Zerodha, Upstox, etc.) can be tracked. |
| **3. Can 7+ apps be monitored simultaneously?** | **NO.** Hard limit of **2 sources/apps** on the Free plan. | Cannot monitor all 7 candidate applications concurrently on one Free workspace. |
| **4. Is competitor Reviews Feed accessible?** | **PARTIALLY.** Visible in web UI feed for the 2 tracked apps. | Reviews can be read manually or via API, but reply/automation tools are disabled for non-owned apps. |
| **5. Are CSV/Excel exports available in UI?** | **NO.** Locked behind paid Essential tier and above. | **Primary Blocker:** Automated manual CSV extraction from the AppFollow web UI is unavailable on Free. |
| **6. Is API v2 access available?** | **YES.** Token authentication (`X-AppFollow-API-Token`) on `https://api.appfollow.io`. | Programmatic extraction is theoretically possible within credit quotas. |
| **7. What are the API credit restrictions?** | `GET /api/v2/reviews` costs **12 credits per call**. Hourly cap of 1,000 requests. | Limited review retrieval volume before credits are exhausted. |
| **8. Does the 7-day history limit apply?** | **YES.** Reviews older than 7 days are truncated on Free accounts. | **Critical Blocker:** Cannot construct historical 12-month retention cohorts using AppFollow Free. |
| **9. Are Indian Storefront apps searchable?** | **YES.** India (`IN`) Google Play storefront is indexed. | Confirmed support for Indian package names. |
| **10. Are competitor reviews in closed beta?** | **NO for basic feed; YES for advanced AI sentiment.** | Basic review feed is GA; AI-driven competitive benchmarking requires enterprise add-ons. |

---

## 3. Account Provisioning & Setup Procedure (User Guide)

Because account registration requires human email confirmation and manual workspace provisioning, follow this exact procedure to establish the test workspace:

### Step 1: Account Registration
1. Navigate to [https://appfollow.io/signup](https://appfollow.io/signup).
2. Sign up using your work or project email.
3. Verify your email address via the confirmation link sent by AppFollow.
4. When prompted to select a plan, select **"Free Plan"** (or skip trial upgrade prompts).

### Step 2: Workspace Configuration
1. In the initial onboarding wizard, choose **"Monitor Competitors"**.
2. When asked to add applications (2 max on Free):
   - **App 1 (Primary):** Search for **"Groww"** -> select Google Play (`com.nextbillion.groww`) -> Country: **India**.
   - **App 2 (Benchmark):** Search for **"Zerodha Coin"** -> select Google Play (`com.zerodha.coin`) -> Country: **India**.
3. Confirm workspace creation.

### Step 3: Inspect Review Feed Capability
1. In the left navigation sidebar, click on **Reviews** -> **Reviews Feed**.
2. Verify that customer reviews for Groww and Zerodha Coin appear.
3. Check the date of the oldest visible review in the feed:
   - Does it stop at 7 days prior to today?
   - Or does it allow infinite scrolling into earlier months?
4. Look at the top-right corner of the Reviews Feed:
   - Check if the **"Export"** button is clickable or displays a padlock icon indicating an upgrade required.

### Step 4: Inspect API Token Generation
1. Click your profile avatar / account name in the lower left corner.
2. Navigate to **Account Settings** -> **API**.
3. Check whether an **API v2 Token** can be generated.
4. Record the current balance of **Monthly API Credits**.
5. **SECURITY NOTICE:** Do not share the raw API token in public repositories or unencrypted chats. Store it in a local `.env` file as `APPFOLLOW_API_TOKEN=...`.

---

## 4. API Testing Procedure (Once Token is Available)

Once an authorized token is provisioned, execute the following standardized validation script to test endpoint reachability and credit consumption:

```bash
# Export the token in your local shell session
export APPFOLLOW_API_TOKEN="<your-token-here>"

# Test 1: Check account identity and credit balance
curl -s -H "X-AppFollow-API-Token: $APPFOLLOW_API_TOKEN" \
     "https://api.appfollow.io/api/v2/users/me" | jq .

# Test 2: Check tracked applications in workspace
curl -s -H "X-AppFollow-API-Token: $APPFOLLOW_API_TOKEN" \
     "https://api.appfollow.io/api/v2/apps" | jq .

# Test 3: Attempt review retrieval for Groww (Package: com.nextbillion.groww)
curl -s -H "X-AppFollow-API-Token: $APPFOLLOW_API_TOKEN" \
     "https://api.appfollow.io/api/v2/reviews?ext_id=com.nextbillion.groww&country=in" | jq .
```

### Response Validation Checklist:
- [ ] HTTP status code: `200 OK` (not `401 Unauthorized` or `403 Forbidden`).
- [ ] Credit deduction: Check whether credit balance decreases by 12 points.
- [ ] Review date range: Verify oldest review timestamp returned.
- [ ] Personal data: Verify whether author names are returned and ensure redaction pipeline is active.

---

## 5. Common Errors & Troubleshooting

| Observed Error | Cause | Resolution |
|---|---|---|
| `HTTP 401 Unauthorized` | Invalid or expired `X-AppFollow-API-Token`. | Regenerate token in AppFollow Account Settings. |
| `HTTP 402 Payment Required` | Feature locked on Free plan (e.g. export or historical reviews). | Confirms Free plan gating; switch to manual CSV or Apple RSS fallback. |
| `HTTP 429 Too Many Requests` | Exceeded 1,000 requests/hour or monthly credit pool exhausted. | Inspect `Retry-After` header; throttle requests. |
| `Source Limit Reached (2/2)` | Attempted to add a 3rd app on Free tier. | Delete an existing app or rotate apps sequentially across collection runs. |
| Padlock icon on "Export CSV" | Direct export requires paid *Essential* plan (\$143/mo). | Use API-based extraction within credit limit or manual CSV import fallback. |

---

## 6. Verification Evidence Checklist for User

To resolve the **PENDING MANUAL VERIFICATION** status, please complete the following checklist and provide the answers:

- [ ] **Account Created:** Was registration on the Free plan completed? (`Yes / No`)
- [ ] **Apps Added:** Were Groww (`com.nextbillion.groww`) and a competitor added successfully? (`Yes / No`)
- [ ] **Oldest Review Date in UI:** What is the oldest date visible in the Reviews Feed? (e.g., `7 days ago` vs. `6 months ago`)
- [ ] **Export Button Status:** Is the CSV export button accessible or disabled/locked? (`Accessible / Locked`)
- [ ] **API Token Generated:** Was an API v2 token successfully generated? (`Yes / No`)
- [ ] **Monthly Credit Balance:** How many credits are displayed in the API settings? (e.g., `0`, `100`, `1,000`)

---

## 7. Recommended Fallback Strategy

Given that AppFollow Free enforces a **2-app ceiling** and a **7-day historical limit**, the Groww Investor Discovery Engine **must not depend on AppFollow Free as its primary collection channel**.

### Recommended Hierarchy:
1. **Primary Automated Route:** Apple App Store Public RSS (Free, no account needed, 500 reviews per app across all 7 apps, 100% verified).
2. **Primary Google Play Route (Owner):** Google Play Console CSV Export (if Groww internal access is available to the user) or direct Google Play Publisher API.
3. **Primary Google Play Route (Public/Competitor):** Manual Review CSV Import (Standardized schema, compliant with privacy policy, bypassing SaaS paywalls).
4. **AppFollow Role:** Periodic delta monitoring of recent reviews (last 7 days) if API credits permit, kept strictly as an optional connector.

---

## 8. Final Route Verdict

```text
VERDICT: REJECTED / UNAVAILABLE (SUBSCRIPTION MANDATORY)
```
- **Technical Availability:** UNAVAILABLE without paid subscription.
- **Cost:** Paid subscription required ($143+/month).
- **Usability for Free-Tier Solution:** **0 / 5 (Unusable)**.
- **Source Connector State in Config:** **`DISABLED`** (`enabled: false`, `technical_availability: "UNAVAILABLE"`, `permission_status: "REJECTED"`).
- **Active Alternative:** 100% Free pipeline combining Apple App Store Public RSS + Manual Review CSV Import.
