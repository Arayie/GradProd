# GROWWW INVESTOR DISCOVERY ENGINE – PRODUCTION ROLLBACK RUNBOOK
**Document Version:** 1.0  
**Phase:** 8 Production Operations  

---

## 1. ROLLBACK TRIGGER CONDITIONS

A production rollback must be initiated immediately upon encountering any of the following conditions:
- **CRITICAL Data Integrity Failure:** Database foreign key violations $> 0$ or corruption detected.
- **Quarantine Breach:** Synthetic demo records detected in eligible research analytics (`leaked_into_eligible > 0`).
- **PII Exposure Incident:** Unredacted customer names, phone numbers, or bank account details visible in UI or exports.
- **Deployment Crash Loop:** Streamlit container fails health checks $> 3$ consecutive cycles.

---

## 2. COMPONENT-LEVEL ROLLBACK PROCEDURES

### Component A: Application Code Rollback (Docker Container)
When deploying via Docker Compose or container registries:

1. **Tag Rollback:** Revert image tag in `docker-compose.yml` to the previously certified release tag (e.g., `v1.0.0-phase7`):
   ```yaml
   services:
     growww-engine:
       image: growww-discovery-engine:v1.0.0-phase7
   ```
2. **Restart Container:**
   ```bash
   docker-compose up -d --force-recreate growww-engine
   ```
3. **Verify Health:**
   ```bash
   docker exec -it growww-discovery-engine python3 scripts/health_check.py
   ```

### Component B: Database State Rollback
If a faulty ingestion or migration corrupts the database:

1. **Halt Application Writes:**
   ```bash
   docker-compose stop growww-engine
   ```
2. **Identify Certified Pre-Incident Backup:**
   Inspect manifests in `data/backups/*.meta.json` to find the last known good snapshot.
3. **Execute Atomic Restore:**
   ```bash
   PYTHONPATH=.:./lib python3 scripts/restore_database.py \
       --backup-file data/backups/growww_backup_<TIMESTAMP>.db.gz \
       --target-db growww_discovery.db
   ```
4. **Restart Application:**
   ```bash
   docker-compose start growww-engine
   ```

### Component C: AI Prompt & Classification Heuristic Rollback
If an updated prompt or model configuration degrades categorization accuracy:

1. Revert `prompts/pain_point_prompt.txt` or `config/model_config.yml` to the baseline certified version:
   ```bash
   git checkout HEAD~1 -- prompts/ config/model_config.yml
   ```
2. Re-run golden set evaluation to confirm Macro F1 recovery ($\ge 0.80$):
   ```bash
   PYTHONPATH=.:./lib python3 validation/model_validation.py
   ```

### Component D: Scheduled Ingestion Job Rollback
If Apple RSS feeds or network scrapers cause rate limits or errors:

1. **Disable Crontab Immediately:**
   ```bash
   crontab -e
   # Comment out the collection line with '#'
   ```
2. **Stop Running Daemons:**
   ```bash
   pkill -f "run_scheduled_collection.py"
   ```
3. **Verify Collection Status:**
   Inspect `collection_errors` table for unresolved error logs.
