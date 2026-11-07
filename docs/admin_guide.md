# GROWWW INVESTOR DISCOVERY ENGINE – ADMINISTRATOR'S OPERATING MANUAL
**Document Version:** 1.0  
**Phase:** 8 – Production Operations & Handover  
**Target Audience:** System Administrators, Security Officers, Compliance Auditors  

---

## 1. ACCESS CONTROL & ROLE MANAGEMENT

The Growww Discovery Engine enforces server-side Role-Based Access Control (RBAC) across four tiers:

| Role | Intended Audience | Key Capabilities | Restricted Actions |
| :--- | :--- | :--- | :--- |
| **`ADMIN`** | Platform Administrators, Tech Leads | Full control: Source routing, manual ingestion triggers, opportunity updates, raw review downloads, schema migrations | None |
| **`RESEARCHER`** | Senior PMs, Qualitative Researchers | AI evidence exploration, human adjudication, opportunity scoring, CSV & PDF export generation | Source routing modification, admin debugging |
| **`VIEWER`** | Executive Stakeholders, External PMs | Read-only access to Executive Overview, Opportunity Radar, 12M Retention Simulator, PDF Digest downloads | Raw review exports, review adjudication, ingestion triggers |
| **`AUDITOR`** | Security & Data Compliance Leads | Audit log inspection, quarantine verification, model validation benchmarks, privacy audits, raw data downloads | Source editing, review adjudication |

### Password Management & Rotation
Passwords are authenticated using PBKDF2-HMAC-SHA256 with 100,000 iterations and unique 16-byte cryptographic salts. To rotate passwords for any role:
1. Update the corresponding environment variable in `.env`:
   - `ADMIN_PASSWORD`
   - `RESEARCHER_PASSWORD`
   - `VIEWER_PASSWORD`
   - `AUDITOR_PASSWORD`
2. Restart the application container:
   ```bash
   docker-compose restart growww-engine
   ```
3. Verify login using the new credentials.

---

## 2. MANAGING INGESTION SOURCES & GOVERNANCE

### Permitted Ingestion Channels
1. **Apple App Store Customer Review RSS:** Fully automated via `scripts/run_scheduled_collection.py`.
2. **Google Play Store CSV Imports:** Place compliant, sourced CSV files into `/app/data/imports/`. The scheduler automatically ingests, validates, anonymizes, and archives them into `/app/data/imports/processed/`.

### Prohibited Sources & Mandatory Governance
- **AppFollow Connector:** Permanently disabled and rejected. Any source configuration specifying `AppFollow` raises `PermissionError` and is blocked immediately.
- **HTML Scrapers:** Direct web scraping of app store HTML pages is prohibited to protect IP rights and prevent rate limit blocks.

---

## 3. SYNTHETIC RECORD QUARANTINE GOVERNANCE

The database contains 8 synthetic demonstration records created during Phase 1 for interface testing.
- **Quarantine Identifier:** `eligibility_status = 'SYNTHETIC_DEMO'`.
- **Enforcement:** Every analytical query across `ReviewRepository`, `AnalyticsService`, and UI pages includes the filter:
  ```sql
  WHERE eligibility_status = 'ELIGIBLE'
  ```
- **Auditor Verification:** Run `python3 scripts/health_check.py`. It guarantees:
  - `quarantined_records: 8`
  - `leaked_into_eligible: 0`

---

## 4. BACKUP SCHEDULE & RECOVERY PROCEDURES

- **Automated Backup:** Configured via `scripts/backup_database.py`. Backups are stored in `/app/data/backups/growww_backup_<TIMESTAMP>.db.gz` alongside SHA-256 `.meta.json` manifests.
- **Integrity Validation:** Run `python3 scripts/restore_database.py --backup-file <FILE> --target-db <TEST_PATH>`. It executes `PRAGMA quick_check;`, checks for 0 foreign key violations, and validates 100% opportunity quote grounding.

---

## 5. ADMINISTRATIVE TROUBLESHOOTING

| Symptom | Cause | Remediation Procedure |
| :--- | :--- | :--- |
| `sqlite3.OperationalError: database is locked` | Long-running write transaction | Confirm WAL mode is active (`PRAGMA journal_mode = WAL;`) and busy timeout is set to 30,000 ms. |
| Ingestion fails with `HTTP 429` | Store rate limiting | Reduce collection frequency or lower `max_pages` parameter in `scripts/run_scheduled_collection.py`. |
| Login gateway not appearing | `REQUIRE_AUTH=false` | Ensure `REQUIRE_AUTH=true` is set in production `.env` and restart service. |
| User session expired prematurely | Inactivity timeout reached | Increase `AUTH_SESSION_TIMEOUT_MINUTES` in `.env` (default is 120 mins). |
