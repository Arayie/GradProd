# Apple App Store RSS Feasibility Report
## Public Customer-Review Ingestion Feasibility for Indian Investment Applications
**Phase 0 Deliverable | Research Scope & Source Feasibility**  
**Investigation Date:** 2026-11-05  
**Storefront:** India (`in`)  
**Data Collection Protocol:** Apple iTunes Public Customer Reviews JSON/Atom RSS Feed  
**Compliance Standard:** Privacy-preserving, data-minimized, zero HTML scraping  

---

## 1. Executive Summary

As part of Phase 0 of the Groww AI-Powered Investor Discovery Engine, we conducted technical feasibility testing of Apple's approved public customer-review RSS feed across all candidate Indian investment applications. 

Testing was conducted against live Apple App Store endpoints in the Indian storefront (`in`). All 8 application listings (Groww, Zerodha Coin, Zerodha Kite, Upstox, Angel One, INDmoney, ET Money, and Paytm Money) were successfully tested.

### Key Empirical Findings:
1. **Endpoint Viability:** Apple's approved RSS JSON endpoint is fully operational without authentication or API keys for the India storefront.
2. **Standard Pagination Limit:** Apple enforces a strict hard ceiling at **Page 10** (`page=10`). Each page returns up to 50 review entries. Attempting to fetch Page 11 (`page=11`) consistently triggers an **`HTTP 400 Bad Request`** across all applications.
3. **Maximum Reachable Volume:** Exactly **500 reviews** can be accessed per application per storefront via this channel.
4. **Historical Reach vs. Review Velocity:** 
   - For high-volume apps like **Groww**, 500 reviews span only **62 days** (2026-09-02 to 2026-11-03). Apple RSS alone **cannot** provide a full 12-month historical cohort for Groww.
   - For moderate-velocity apps (Upstox, Angel One, INDmoney), 500 reviews span approximately **11 to 12 months** (covering late 2025 to late 2026).
   - For lower-velocity apps (Zerodha Coin, ET Money, Paytm Money), 500 reviews span **21 to 80 months** (Zerodha Coin reviews stretch back to February 2020).
5. **Data Structure:** The feed returns structured JSON adhering to the Atom syndication format. Critical investor discovery fields (Review ID, Star Rating, Title, Review Text, App Version, Submission Date) are reliably present. Reviewer nicknames are present in the payload but **must be strictly redacted** prior to storage.

---

## 2. Tested Applications & Empirical Results

All tests were executed on 2026-11-05 using automated Python scripts connecting to `https://itunes.apple.com/in/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json`.

| App Name | Apple App ID | HTTP Status (P1-P10) | HTTP Status (P11) | Reviews Accessible | Newest Review (UTC-7) | Oldest Review (UTC-7) | Historical Depth | Status |
|---|---|---|---|---|---|---|---|---|
| **Groww** (Primary) | `1404871703` | 200 OK | 400 Bad Request | 500 | 2026-11-03 10:25 | 2026-09-02 20:35 | ~2 months | Successfully Tested |
| **Zerodha Coin** | `1392892554` | 200 OK | 400 Bad Request | 500 | 2026-10-05 18:02 | 2020-02-22 12:28 | ~80 months | Successfully Tested |
| **Zerodha Kite** | `1449453802` | 200 OK | 400 Bad Request | 500 | 2026-11-01 19:06 | 2025-07-01 08:58 | ~16 months | Successfully Tested |
| **Upstox** | `1584953620` | 200 OK | 400 Bad Request | 500 | 2026-11-03 07:40 | 2025-11-21 07:03 | ~12 months | Successfully Tested |
| **Angel One** | `1060530981` | 200 OK | 400 Bad Request | 500 | 2026-11-03 01:39 | 2025-12-23 21:58 | ~11 months | Successfully Tested |
| **INDmoney** | `1450178837` | 200 OK | 400 Bad Request | 500 | 2026-11-03 00:11 | 2025-11-13 20:43 | ~12 months | Successfully Tested |
| **ET Money** | `1212752482` | 200 OK | 400 Bad Request | 500 | 2026-10-23 23:02 | 2025-01-26 21:26 | ~21 months | Successfully Tested |
| **Paytm Money** | `1344431352` | 200 OK | 400 Bad Request | 500 | 2026-11-02 20:30 | 2025-02-05 04:00 | ~21 months | Successfully Tested |
| **Total Sample** | – | – | – | **4,000** | – | – | – | **All 8 Verified** |

---

## 3. Technical Inspection & Endpoint Behavior

### 3.1 Approved Endpoint Construction
The standard approved Apple customer reviews RSS endpoint format is:
```http
GET https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json
```
- `{country}`: 2-letter ISO storefront code (`in` for India).
- `{page}`: Integer index `1` through `10`.
- `{app_id}`: Verified numeric Apple ID.
- `sortby`: `mostrecent` ensures retrieval ordered by date descending.
- format: `json` produces structured JSON over Atom.

### 3.2 Response Payload Structure
The top-level response envelope contains a single object `{"feed": {...}}`.
The payload includes metadata about the storefront feed, links to pagination, and an `entry` array of up to 50 items.

> [!NOTE]
> In some versions of the feed, `feed.entry[0]` represents the target application metadata (containing app name, icon, developer links) and lacks `im:rating`. Subsequent items (`feed.entry[1:]`) represent individual user reviews. The ingestion parser must conditionally filter for the presence of `im:rating`.

### 3.3 Available Review Fields
Every review entry exposes the following structured attributes:

| Apple Feed Key | Field Name | Type | Value Example | Governance / Usage Handling |
|---|---|---|---|---|
| `id.label` | Review ID | String / Numeric | `"14745855461"` | Retained as unique deduplication key. |
| `title.label` | Review Title | String | `"Best investment app"` | Retained for NLP / intent classification. |
| `content.label` | Review Text | String | `"Smooth setup and easy SIP deduction..."` | Primary text for taxonomy classification. Preserves original script/language. |
| `im:rating.label` | Star Rating | String (`1`-`5`) | `"5"` | Normalized to integer (1-5). |
| `im:version.label` | App Version | String | `"18.22.0"` | Retained to isolate version-specific friction. |
| `updated.label` | Review Timestamp | ISO 8601 | `"2026-11-03T06:03:41-07:00"` | Converted to UTC. Used for cohort analysis. |
| `im:voteCount.label` | Vote Count | String | `"0"` | Helpful count. Stored as metadata. |
| `im:voteSum.label` | Vote Sum | String | `"0"` | Net score. Stored as metadata. |
| `link.attributes.href`| Review URL | URL | `"https://itunes.apple.com/..."` | Stored as provenance link. |
| `author.name.label` | Author Name | String | `"JohnDoe_123"` | **STRICTLY EXCLUDED / REDACTED.** Never stored. |
| `author.uri.label` | Author Profile URI | URL | `"https://itunes.apple.com/..."` | **STRICTLY EXCLUDED / REDACTED.** Never stored. |

---

## 4. Pagination & Edge Case Analysis

1. **Page Boundaries:**
   - Pages 1 to 10 return `HTTP 200 OK` with 50 entries each.
   - Page 11 returns `HTTP 400 Bad Request` across all tested endpoints.
   - Paging beyond 10 is rejected by Apple's edge infrastructure.
2. **Deduplication Check:**
   - Reviews across pages 1 to 10 are strictly ordered by `updated` timestamp.
   - In our empirical tests, 0 duplicate review IDs were encountered across pages 1 through 10.
3. **App ID Discrepancies Resolved:**
   - Initial web references suggested legacy App Store IDs for certain applications (e.g., Zerodha Coin `1375141655`, Angel One `1064855351`, ET Money `1044473859`). Feasibility tests revealed that these legacy IDs returned empty feeds (`0` reviews).
   - Authoritative verification via Apple iTunes Search API identified the live active IDs:
     - Zerodha Coin: `1392892554`
     - Angel One: `1060530981`
     - ET Money: `1212752482`
   - Once verified, all three live IDs immediately yielded full 500-review datasets.

---

## 5. Critical Constraints & Architectural Implications

> [!WARNING]
> **Groww 12-Month First-SIP Active Rate Gap:**
> Because Groww experiences intense consumer review volume, the 500-review ceiling only reaches back to **September 2, 2026 (~62 days)**. 
> To evaluate 12-month retention cohorts, the research engine **cannot rely exclusively on one-time Apple RSS collection**.

### Necessary Architectural Mitigations:
1. **Periodic Ingestion (Delta Scraping):** By polling the Apple RSS feed weekly, new reviews can be incrementally captured and archived over time.
2. **Multi-Source Hybrid Strategy:** Public competitor reviews from Google Play Store (via AppFollow or direct console CSV imports) must be integrated to achieve comprehensive historical depth.
3. **Manual CSV Import Fallback:** For deep historical cohorts (pre-September 2026), manual CSV imports of exported public store datasets must be supported as specified in PRD Section 4.

---

## 6. Feed Compliance & Ethical Rules

1. **Approved Endpoints Only:** Ingestion uses Apple's publicly exposed RSS syndication endpoints. No internal App Store APIs or private session tokens are utilized.
2. **No HTML Scraping:** No headless browsers (Puppeteer, Selenium, Playwright) or HTML parsers are used against `apps.apple.com`.
3. **Polite Request Throttling:** Requests must implement an exponential backoff and a minimum 0.5-second politeness delay between page queries to prevent rate-limiting or service burden.
4. **Data Minimization:** Reviewer names, Apple user IDs, and profile URLs are stripped before data is persisted.

---

## 7. Conclusion & Feasibility Verdict

| Metric | Result |
|---|---|
| **Apple RSS Technical Feasibility** | **FEASIBLE & VERIFIED** |
| **India Storefront Reach** | **100% (8/8 Applications Accessible)** |
| **Feed Stability** | **High (Zero HTTP 5xx errors observed)** |
| **Single-Pass Historical Coverage** | **Capped at 500 reviews per app (60 days to 80 months depending on review velocity)** |
| **Phase 1 Ingestion Readiness** | **READY for automated connector implementation** |
