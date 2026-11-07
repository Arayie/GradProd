# GROWWW INVESTOR DISCOVERY ENGINE – DEPLOYMENT ARCHITECTURE
**Document Version:** 1.0  
**Phase:** 8 Production Architecture  
**Author:** DevOps & Cloud Engineering Lead  

---

## 1. ARCHITECTURAL OVERVIEW

The Growww Investor Discovery Engine is designed as a secure, containerized, stateful research platform. It integrates automated data ingestion, AI-driven categorization, evidence logging, quantitative opportunity scoring, and interactive product exploration into an accessible web interface.

```mermaid
graph TD
    User["Authorized User / PM / Auditor"] -->|HTTPS 443| RevProxy["TLS Reverse Proxy (Nginx / Cloudflare)"]
    RevProxy -->|HTTP 8501| StreamlitApp["Growww Engine (Streamlit Web App)"]

    subgraph "Application Runtime Container"
        StreamlitApp --> AuthModule["RBAC & Auth Engine (Admin/Researcher/Viewer/Auditor)"]
        AuthModule --> AppPages["16 Research & Discovery UI Pages"]
        AppPages --> Services["Service Layer (Analytics, AI Evidence, Scoring)"]
        Services --> DBManager["Database Abstraction Layer"]
        Services --> PDFExport["PDF Digest & CSV Export Engine"]
    end

    subgraph "Persistent Storage Volume"
        DBManager --> SQLiteDB[("SQLite 3.35+ (WAL Mode)<br/>or Managed PostgreSQL")]
        PDFExport --> ReportsVol[("/app/reports & /app/outputs")]
    end

    subgraph "External Permitted Data Sources"
        Scheduler["Scheduled Refresh Daemon"] -->|HTTPS (Public XML/JSON)| AppleRSS["Apple App Store Public RSS"]
        CSVImport["Admin CSV Uploader"] -->|Local File| StagedCSV["Google Play CSV Drop"]
        Scheduler --> DBManager
        CSVImport --> DBManager
    end

    subgraph "Strict Exclusions & Quarantine"
        AppFollow["AppFollow Paid API"] -.->|PERMANENTLY BLOCKED| Blocked["Rejected (Zero Paid APIs)"]
        Scraper["HTML Web Scraping"] -.->|STRICTLY PROHIBITED| Blocked2["Rejected (Zero HTML Scrapers)"]
        Quarantine["8 Synthetic Demo Reviews"] -.->|Quarantined| QTable["Excluded from Analytics"]
    end
```

---

## 2. HOSTING PLATFORM OPTIONS & SIZING

The platform supports four deployment tiers depending on organizational infrastructure:

### Tier 1: Containerized Docker on Cloud VM / VPS (Recommended Default)
- **Host Platforms:** AWS EC2, DigitalOcean Droplet, Hetzner Cloud, Google Compute Engine.
- **Minimum Sizing:** 1 vCPU, 1 GB RAM, 10 GB SSD.
- **Recommended Sizing:** 2 vCPU, 2 GB RAM, 25 GB SSD.
- **Persistence:** Docker named volume or host directory bind mount mapped to `/app/data`.
- **Reverse Proxy:** Nginx or Caddy with automated Let's Encrypt TLS certificates.

### Tier 2: Managed PaaS (Render / Railway / Fly.io)
- **Host Platforms:** Render Web Service, Railway Project.
- **Resource Sizing:** Standard plan (1 GB - 2 GB RAM).
- **Persistence:** Render Persistent Disk or Railway Volume attached to `/app/data`.
- **Database:** Internal SQLite on persistent disk, or linked Managed PostgreSQL add-on.

### Tier 3: Streamlit Community Cloud (Rapid Team Sharing)
- **Host Platforms:** Streamlit Community Cloud linked to private GitHub repository.
- **Secrets Management:** Built-in Streamlit Secrets (`.streamlit/secrets.toml`).
- **Database:** Managed Cloud PostgreSQL (Supabase, Neon, AWS RDS) via `DATABASE_URL`.

### Tier 4: Enterprise Kubernetes / ECS Fargate
- **Host Platforms:** AWS ECS Fargate, GCP Cloud Run, Azure Container Apps, EKS.
- **Persistence:** AWS EFS volume mount or Cloud SQL / RDS PostgreSQL.
- **Scaling:** Single replica or multi-replica with centralized PostgreSQL database.

---

## 3. MULTI-USER CONCURRENCY & MEMORY BUDGET

### Memory Profile
- **Base Container Footprint:** ~108 MB RSS at idle.
- **Per Active User Session:** ~22 MB - 28 MB RAM (cached DataFrames and chart states).
- **Peak Load (15 Concurrent Researchers):** ~450 MB RAM.
- **Enforced Budget:** < 512 MB under standard operation.

### Concurrency Characteristics
- **Read Operations:** Highly optimized via SQLite WAL (Write-Ahead Logging) mode, allowing unlimited concurrent readers while writes execute.
- **Write Operations (Adjudications / Opportunity Updates):** Serialized atomic transactions with 30-second timeout (`PRAGMA busy_timeout = 30000;`).
- **Cold-Start Latency:** Initial load completes in 2.1 seconds; cached queries execute in < 3.0 milliseconds.

---

## 4. PERSISTENT STORAGE ARCHITECTURE

All business-critical data is stored in the `/app/data` volume mount.

```
/app/data/
├── growww_discovery.db        # Primary SQLite database (WAL mode)
├── growww_discovery.db-wal    # Write-Ahead Log
├── growww_discovery.db-shm    # Shared memory index
├── backups/                   # Timestamped compressed backups (.db.gz)
└── imports/                   # Google Play CSV import drop folder
```

### Dual SQLite / PostgreSQL Compatibility
The application database manager inspects `DATABASE_URL`:
- `sqlite:////app/data/growww_discovery.db`: Uses native SQLite 3.35+ engine with foreign keys, WAL journaling, and zero-latency local I/O.
- `postgresql://user:pass@host:5432/dbname`: Uses PostgreSQL connection pool via SQLAlchemy/psycopg2 for high-concurrency enterprise clusters.

---

## 5. NETWORK SECURITY & FIREWALL TOPOLOGY

1. **Inbound Traffic:**
   - Only port 443 (HTTPS) and port 80 (HTTP redirect) should be open to the public or corporate VPN.
   - Reverse proxy terminates TLS and forwards requests to port 8501 internally.
2. **Outbound Traffic:**
   - Permitted: Apple App Store RSS endpoint (`https://itunes.apple.com`).
   - Permitted: Optional Google Gemini API (`https://generativelanguage.googleapis.com`).
   - Blocked: All other outbound connections are unnecessary and can be firewalled.
3. **Internal Application Security:**
   - Streamlit XSRF protection enabled (`enableXsrfProtection = true`).
   - Streamlit telemetry permanently disabled (`gatherUsageStats = false`).
   - Private authentication gateway enforced (`REQUIRE_AUTH = true`).
