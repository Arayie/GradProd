# GROWWW INVESTOR DISCOVERY ENGINE – PRODUCTION DEPLOYMENT RUNBOOK
**Document Version:** 1.0  
**Phase:** 8 – Production Deployment & Operations  
**Audience:** DevOps Engineers, Cloud Platform Architects, Technical Leads  

---

## 1. PRE-REQUISITES & ENVIRONMENT PREPARATION

### System Requirements
- **Operating System:** Linux (Ubuntu 22.04 LTS / Debian 12 recommended) or macOS Darwin.
- **Docker Engine:** Docker 24.0+ & Docker Compose v2.20+.
- **Python Runtime (if non-containerized):** Python 3.9+ with `pip`.
- **System Memory:** Minimum 1 GB RAM (2 GB recommended).
- **Disk Storage:** Minimum 10 GB persistent SSD storage.

---

## 2. DEPLOYMENT PROCEDURE VIA DOCKER COMPOSE (RECOMMENDED)

### Step 1: Clone Repository & Configure Environment
```bash
git clone <repository-url> growww-discovery-engine
cd growww-discovery-engine

# Copy production environment template
cp .env.example .env
```

### Step 2: Configure Production Secrets in `.env`
Edit `.env` to configure authentication and persistent database paths:
```ini
APP_ENV=production
APP_PORT=8501
APP_HOST=0.0.0.0
DATABASE_URL=sqlite:////app/data/growww_discovery.db
REQUIRE_AUTH=true
AUTH_SESSION_TIMEOUT_MINUTES=120

# Configure production passwords for all 4 roles:
ADMIN_PASSWORD=Admin@SecurePass2026!
RESEARCHER_PASSWORD=Research@SecurePass2026!
VIEWER_PASSWORD=Viewer@SecurePass2026!
AUDITOR_PASSWORD=Auditor@SecurePass2026!

# Logging
LOG_LEVEL=INFO
```

### Step 3: Build & Launch Containers
```bash
# Build multi-stage hardened image and start in detached mode
docker-compose up -d --build
```

### Step 4: Verify Container Health & Status
```bash
# Check container status
docker-compose ps

# Query built-in health diagnostics inside the container
docker exec -it growww-discovery-engine python3 scripts/health_check.py
```

Expected output:
```
================================================================================
GROWWW INVESTOR DISCOVERY ENGINE – HEALTH DIAGNOSTICS: [HEALTHY]
================================================================================
 - database_latency         : [PASS]
 - database_integrity       : [PASS]
 - quarantine_isolation     : [PASS]
 - data_metrics             : [PASS]
 - system_resources         : [PASS]
```

### Step 5: Configure Reverse Proxy (TLS / HTTPS)
Follow `docs/production_domain_and_https_guide.md` to map Nginx or Caddy to port 8501 and terminate SSL with Let's Encrypt certificates.

---

## 3. DEPLOYMENT PROCEDURE VIA DIRECT PYTHON RUNTIME

For environments where Docker is unavailable:

```bash
# 1. Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Initialize SQLite database & configurations
python3 -c "from core.database_manager import get_database_manager; get_database_manager().initialize()"

# 4. Launch Streamlit server in production mode
streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=true
```

---

## 4. VERIFYING PRODUCTION SMOKE TEST

Run the end-to-end smoke test suite against the deployed environment:

```bash
PYTHONPATH=.:./lib python3 -m pytest tests/test_production_smoke.py -v
```

All 7 test stages must return `PASSED`:
- `test_smoke_a_authentication_and_rbac`
- `test_smoke_b_database_connection_and_integrity`
- `test_smoke_c_overview_metric_and_quarantine_parity`
- `test_smoke_d_ai_evidence_and_grounding`
- `test_smoke_e_opportunity_ranking_and_scores`
- `test_smoke_f_export_pipeline`
- `test_smoke_g_health_check_service`

---

## 5. SCHEDULED COLLECTION CRON SETUP

Configure automated weekly review retrieval on the host machine:

```bash
crontab -e
```

Add the following entry:
```cron
# Weekly Growww discovery refresh: Sunday 00:00 IST (Saturday 18:30 UTC)
30 18 * * 6 cd /path/to/growww-discovery-engine && docker exec growww-discovery-engine python3 scripts/run_scheduled_collection.py --pages 5 >> /path/to/logs/cron.log 2>&1
```

---

## 6. BACKUP & RECOVERY PROCEDURES

To initiate an immediate verified backup:
```bash
docker exec growww-discovery-engine python3 scripts/backup_database.py
```

To test restore verification in an isolated target:
```bash
docker exec growww-discovery-engine python3 scripts/restore_database.py \
    --backup-file /app/data/backups/<BACKUP_FILE>.db.gz \
    --target-db /app/data/backups/test_restore.db
```
