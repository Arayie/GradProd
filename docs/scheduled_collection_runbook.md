# GROWWW INVESTOR DISCOVERY ENGINE – SCHEDULED COLLECTION RUNBOOK
**Document Version:** 1.0  
**Phase:** 8 Production Operations  
**Frequency:** Weekly (Every Sunday 00:00 IST / Saturday 18:30 UTC)  

---

## 1. PURPOSE & ARCHITECTURAL SCOPE

The scheduled collection system continuously monitors public feedback for Groww and its peer group across the Indian investment ecosystem. It ensures that the investor discovery engine stays up to date with emerging pain points, newly introduced app updates, and shifts in sentiment without manual operator intervention.

### Permitted Ingestion Channels
1. **Apple App Store Public Customer Review RSS:** Automated weekly retrieval for all registered applications via Apple's official storefront feeds (`itunes.apple.com/in/rss/customerreviews`).
2. **Google Play Staged CSV Drops:** Ingestion of authorized CSV review exports placed by researchers into `/app/data/imports/`.

### Strictly Prohibited Channels
- **AppFollow API:** Permanently rejected due to commercial paywall. Any configuration referencing AppFollow fails fast with `PermissionError`.
- **Google Play HTML Scraping:** Strictly prohibited to respect Google Play Terms of Service and prevent IP bans.

---

## 2. DEDUPLICATION & INCREMENTAL PROCESSING

To prevent duplicate records from inflating analytics:
1. Every review is assigned a SHA-256 `content_hash` derived deterministically from:
   $$\text{SHA-256}(\text{app\_id} + \text{store} + \text{author\_name} + \text{review\_title} + \text{review\_text} + \text{rating})$$
2. Ingestion checks `(app_id, content_hash)` against existing records in SQLite/PostgreSQL.
3. Existing records are skipped with zero database modification.
4. Newly discovered reviews are passed through:
   - Automated PII Redaction (`processing/pii_sanitizer.py`).
   - Language & Script Detection (`processing/language_detector.py`).
   - SIP Relevance Heuristic Classifier (`processing/relevance_classifier.py`).
   - AI Pain-Point Categorization & Verbatim Grounding (`ai/classifier.py`).
5. Ingestion run metrics are logged to `ingestion_runs` and `collection_checkpoints`.

---

## 3. DEPLOYMENT & SCHEDULING OPTIONS

### Option A: Standard Linux Crontab (Recommended for Cloud VM)
Edit crontab with `crontab -e`:

```cron
# Run Growww review collection every Sunday at 00:00 IST (Saturday 18:30 UTC)
30 18 * * 6 cd /app && PYTHONPATH=.:./lib python3 scripts/run_scheduled_collection.py --pages 5 >> /app/logs/cron_collection.log 2>&1
```

### Option B: Systemd Service & Timer Unit
Create `/etc/systemd/system/growww-collection.service`:

```ini
[Unit]
Description=Growww Discovery Engine Scheduled Review Refresh
After=network.target

[Service]
Type=oneshot
User=appuser
WorkingDirectory=/app
Environment="PYTHONPATH=.:./lib"
ExecStart=/usr/local/bin/python3 scripts/run_scheduled_collection.py --pages 5
StandardOutput=append:/app/logs/scheduled_collection.log
StandardError=append:/app/logs/scheduled_collection.log
```

Create `/etc/systemd/system/growww-collection.timer`:

```ini
[Unit]
Description=Trigger Growww Review Refresh Weekly on Sunday Midnight IST

[Timer]
OnCalendar=Sat *-*-* 18:30:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start timer:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now growww-collection.timer
```

### Option C: Container Daemon Mode
When running inside Docker without external cron:

```bash
docker exec -d growww-discovery-engine python3 scripts/run_scheduled_collection.py --daemon --interval-hours 168
```

---

## 4. FAILURE RESILIENCE & ERROR HANDLING

1. **Network Fluctuations / Apple Rate Limiting:**
   - The scheduler implements 3x exponential backoff (2s, 4s delays).
   - If Apple RSS fails after 3 attempts, the error is isolated to that specific application and recorded in `collection_errors`. Other applications continue processing.
2. **Corrupted CSV Drop:**
   - If a CSV drop in `/app/data/imports/` fails schema validation, it is rejected without touching the database, and an alert is recorded in `collection_errors`.
3. **Database Integrity Preservation:**
   - All review inserts run within atomic database transactions. If an unhandled exception occurs mid-batch, the transaction rolls back cleanly, leaving zero orphaned rows.
