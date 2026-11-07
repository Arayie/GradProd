# GROWWW INVESTOR DISCOVERY ENGINE – INCIDENT RESPONSE RUNBOOK
**Document Version:** 1.0  
**Phase:** 8 Production Operations  

---

## 1. INCIDENT SEVERITY CLASSIFICATION

| Severity | Definition | Response SLA | Target Resolution | Escalation Contact |
| :--- | :--- | :--- | :--- | :--- |
| **P0 – Critical** | System down, PII leak in UI/exports, synthetic records contaminating research, DB corruption | < 15 minutes | < 2 hours | DevOps Lead, Principal Architect |
| **P1 – Major** | Weekly ingestion failure across all apps, export generation crash, model F1 below 0.70 | < 1 hour | < 8 hours | Senior Data Engineer, QA Lead |
| **P2 – Minor** | Single app ingestion failure, slow query (> 50ms), styling issue | < 4 hours | < 24 hours | Python Backend Engineer |
| **P3 – Low** | Typo in UI label, non-critical documentation discrepancy | < 24 hours | Next Sprint | Frontend / UI Engineer |

---

## 2. STANDARD OPERATING PROCEDURES (SOP) BY INCIDENT TYPE

### SOP-01: Customer PII Leakage Incident (Severity: P0)
**Symptoms:** Unredacted 10-digit Indian mobile number, email address, bank account, or mutual fund folio number visible in UI or downloaded export.

1. **Immediate Containment:**
   - Stop web container immediately: `docker-compose stop growww-engine`.
   - Remove corrupted export files from `/app/outputs/` and `/app/reports/`.
2. **Identification & Forensics:**
   - Query reviews containing potential PII:
     ```sql
     SELECT evidence_id, review_text FROM reviews WHERE review_text REGEXP '[6-9]\d{9}';
     ```
3. **Remediation & Expungement:**
   - Run PII neutralization script to replace sensitive text with `[REDACTED_PHONE]`, `[REDACTED_EMAIL]`, or `[REDACTED_ACCOUNT]`.
   - Update `processing/pii_sanitizer.py` with tighter pattern definitions.
4. **Validation:**
   - Run `PYTHONPATH=.:./lib python3 validation/privacy_audit.py` to confirm 0 leaks.
5. **Recovery:**
   - Regenerate exports, restart container, and notify compliance stakeholders.

---

### SOP-02: Synthetic Data Quarantine Breach (Severity: P0)
**Symptoms:** `SYNTHETIC_DEMO` reviews appearing in eligible research datasets, opportunity scoring calculations, or PDF digests.

1. **Immediate Containment:**
   - Pause external access to engine.
2. **Root Cause Analysis:**
   - Check `eligibility_status` column in `reviews` table:
     ```sql
     SELECT count(*) FROM reviews WHERE eligibility_status = 'ELIGIBLE' AND source_record_id LIKE 'DEMO%';
     ```
3. **Database Correction:**
   - Force reset eligibility status:
     ```sql
     UPDATE reviews SET eligibility_status = 'SYNTHETIC_DEMO' WHERE source_record_id LIKE 'DEMO%';
     ```
4. **Validation:**
   - Run `PYTHONPATH=.:./lib python3 scripts/health_check.py` to verify `quarantine_isolation: [PASS]`.
5. **Re-Run Analytics:**
   - Execute `PYTHONPATH=.:./lib python3 scripts/run_phase_5_analytics.py` to refresh opportunity scores.

---

### SOP-03: Upstream Store Scrape / API Blockage (Severity: P1)
**Symptoms:** Apple RSS returns HTTP 403 / 429 rate limit; or ingestion errors recorded in `collection_errors`.

1. **Verify No Scraper Violation:**
   - Ensure AppFollow and HTML scrapers remain 100% disabled in `config/source_access.yml`.
2. **Backoff and Rate Limit Adjustment:**
   - Reduce collection frequency or reduce `max_pages` from 10 to 3 in `scripts/run_scheduled_collection.py`.
   - Wait 60 minutes for IP rate limit cooldown.
3. **Verify Storefront Availability:**
   - Test manual fetch:
     ```bash
     curl -s "https://itunes.apple.com/in/rss/customerreviews/id=1404871703/sortBy=mostRecent/json" | head -n 20
     ```

---

### SOP-04: Upstream LLM Provider Outage (Severity: P2)
**Symptoms:** Google Gemini API returns HTTP 500 / 503 or quota exhaustion.

1. **Automatic Fallback:**
   - The engine automatically activates the built-in deterministic heuristic classifier (`ai/classifier.py`).
   - Categorization accuracy remains high (Macro F1 = 0.815), with zero unhandled exceptions.
2. **Monitoring:**
   - Check `ai_evidence_log` column `model_version` to verify fallbacks are logging as `HEURISTIC_RULE_v1`.

---

## 3. INCIDENT POST-MORTEM TEMPLATE

Following resolution of any P0 or P1 incident, complete the following post-mortem within 48 hours:

```markdown
# POST-MORTEM: [INCIDENT-YYYYMMDD-TITLE]
- **Date & Time:** YYYY-MM-DD HH:MM UTC
- **Severity:** P0 / P1
- **Duration of Outage:** XX minutes
- **Impact Summary:** (e.g. 15 users affected, 0 customer PII exposed)
- **Root Cause:** (Detailed technical explanation of what failed)
- **Resolution Taken:** (Actions performed to mitigate and restore)
- **Preventative Action Items:**
  1. [Action Item 1] - Owner - Target Date
  2. [Action Item 2] - Owner - Target Date
```
