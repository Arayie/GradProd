# GROWWW – AI-Powered Investor Discovery Engine
## Production Platform & Research Operating System (Phase 8)

An independent, evidence-backed research engine analyzing customer reviews across Indian wealth management applications to discover the friction points, emotional drivers, and product opportunities governing the **12-month first-SIP active rate**.

**Groww** is the primary case study, benchmarked against Zerodha Coin, Upstox, Angel One, and Paytm Money.

> [!NOTE]
> This is an independent research platform. It does not access Groww's internal transactional customer databases, proprietary CRM, or private cohorts. All insights derive from publicly available customer reviews collected via permitted channels (Apple App Store public RSS and sourced Google Play CSV imports) and processed under strict PII redaction and author anonymization standards.

---

## 1. KEY PLATFORM CAPABILITIES

1. **Permitted Multi-Store Ingestion:**
   - Automated ingestion of public customer reviews from the Apple App Store (India Storefront).
   - Structured Google Play Store CSV import engine with column validation and provenance verification.
   - Deterministic SHA-256 content deduplication preventing inflated frequencies.
   - **Zero Paid APIs & Zero HTML Scraping:** AppFollow permanently excluded; HTML scraping strictly prohibited.

2. **Standardization & Privacy Assurance:**
   - Automated PII redaction (Indian 10-digit mobile numbers, emails, bank accounts, folio IDs).
   - Language and script detection across English, Hindi, and Hinglish (`hi-Latn`).
   - Demographic attributes default strictly to `UNKNOWN`. Author identifiers permanently discarded.
   - 8 synthetic demonstration records quarantined (`SYNTHETIC_DEMO`) from production analytics.

3. **AI Enrichment & 100% Verbatim Grounding:**
   - Categorization across 6 SIP pain-point categories and 5 investor lifecycle stages.
   - Every analytical opportunity grounded in genuine verbatim customer quotes (zero AI hallucinations).
   - High classification accuracy verified against 300 human-annotated gold standard reviews: Pain-Point Macro F1 = **0.815**, Cohen's Kappa = **0.855**.

4. **Opportunity Radar & Quantification Engine:**
   - Multi-factor opportunity scoring algorithm:
     $$\text{Opportunity Score} = ((0.30 P + 0.30 S + 0.25 L + 0.15 A)) \times C$$
   - 7 prioritized product opportunities with testable hypotheses, proposed interventions, and counter-evidence.
   - Monte Carlo sensitivity tested: 100% ranking stability under $\pm 10\%$ input perturbations.
   - 12-Month Retention Impact Simulator modeling first-year active rate sensitivity.

5. **Production Research Portal:**
   - 16-page interactive Streamlit dashboard with high-contrast financial research styling.
   - Role-Based Access Control (RBAC) with 4 discrete roles: `ADMIN`, `RESEARCHER`, `VIEWER`, `AUDITOR`.
   - Automated export pipeline generating CSV, JSON, and PDF Weekly Discovery Digests.

6. **Hardened Operations & Cloud Deployment:**
   - Multi-stage Docker container with dedicated non-root `appuser`.
   - Dual storage adapter: SQLite with Write-Ahead Logging (WAL mode) and PostgreSQL.
   - Automated database backup and restore scripts with SHA-256 cryptographic verification.
   - Diagnostics health check reporting sub-5ms query latencies and 0 foreign key violations.

---

## 2. REPOSITORY ARCHITECTURE

```text
growww-investor-discovery/
│
├── app.py                             # Main Streamlit application entrypoint
├── Dockerfile                         # Production multi-stage Dockerfile
├── docker-compose.yml                 # Production Docker Compose specification
├── requirements.txt                   # Production Python package dependencies
├── .env.example                       # Environment configuration template
├── growww_discovery.db                # Production SQLite database (WAL mode)
│
├── config/                            # Core Configuration & Taxonomies
│   ├── apps.yml                       # Registered candidate investment applications
│   ├── source_access.yml              # Source access register (AppFollow disabled)
│   ├── review_taxonomy.yml            # Multilingual pain-point taxonomy
│   └── model_config.yml               # AI classifier configuration
│
├── core/                              # Core Architecture & Foundation
│   ├── auth.py                        # PBKDF2 authentication & RBAC permission matrix
│   ├── env_config.py                  # Fail-fast configuration & secrets manager
│   ├── database_manager.py            # High-level database orchestrator
│   └── csv_validator.py               # Google Play CSV schema validator
│
├── database/                          # Persistence Layer
│   ├── connection.py                  # Dual SQLite WAL / PostgreSQL connection pool
│   ├── repositories.py                # Data access objects (reviews, apps, runs)
│   └── schema.sql                     # SQLite DDL schema script
│
├── services/                          # Business Logic & Service Layer
│   ├── ingestion_service.py           # Review collection & import orchestrator
│   ├── scheduler_service.py           # Automated weekly refresh service
│   ├── enrichment_service.py          # AI enrichment & evidence extraction
│   ├── analytics_service.py           # Quantitative metrics & aggregations
│   ├── opportunity_service.py         # Opportunity radar & scoring engine
│   ├── health_service.py              # System diagnostics & health check service
│   └── pdf_export_service.py          # Pure-Python PDF digest compiler
│
├── scripts/                           # Operational CLI Tools
│   ├── backup_database.py             # Atomic database backup tool
│   ├── restore_database.py            # Backup restoration & validation tool
│   ├── health_check.py                # Production diagnostics CLI
│   ├── run_scheduled_collection.py    # Scheduled review ingestion runner
│   ├── migrate_sqlite_to_postgres.py  # SQLite to PostgreSQL migration tool
│   └── benchmark_production.py        # Performance & concurrency benchmark
│
├── ui/                                # Research Portal & Presentation Layer
│   ├── navigation.py                  # Sidebar navigation & theme styles
│   └── pages/                         # 16 Specialized Research Pages
│       ├── executive_overview.py      # Executive research overview
│       ├── review_explorer_ui.py      # Filterable customer review explorer
│       ├── sip_journey_explorer.py    # 5-stage SIP lifecycle explorer
│       ├── opportunity_radar.py       # 7 ranked roadmap opportunities
│       ├── opportunity_detail.py      # Deep-dive dossiers with verbatim quotes
│       ├── retention_model_ui.py      # 12-month retention sensitivity simulator
│       ├── ai_evidence_log_ui.py      # AI evidence inspection log
│       └── exports_reports.py         # One-click CSV, JSON, PDF downloads
│
├── docs/                              # Operational Guides & Documentation
│   ├── deployment_architecture.md     # System architecture & sizing
│   ├── deployment_runbook.md          # Step-by-step production setup guide
│   ├── database_migration_guide.md    # SQLite to PostgreSQL migration guide
│   ├── backup_and_restore_runbook.md  # Disaster recovery & restore procedures
│   ├── monitoring_and_alerting.md     # Health metrics & Prometheus integration
│   ├── scheduled_collection_runbook.md# Weekly automated ingestion guide
│   ├── admin_guide.md                 # System administrator operating manual
│   ├── research_methodology.md        # Qualitative research methodology guide
│   └── BUILD_PROGRESS.md              # Milestone tracker across all 8 phases
│
└── tests/                             # Comprehensive Automated Test Suite
    ├── test_production_smoke.py       # Production end-to-end smoke tests
    └── ... (14 other test suites, 125 total passing tests)
```

---

## 3. QUICKSTART: LOCAL DOCKER DEPLOYMENT

The fastest way to run the production platform:

```bash
# 1. Clone repository
git clone <repository-url> growww-discovery-engine
cd growww-discovery-engine

# 2. Configure environment
cp .env.example .env

# 3. Build and launch container
docker-compose up -d --build

# 4. Open browser
open http://localhost:8501
```

---

## 4. PRODUCTION ROLES & DEFAULT CREDENTIALS

The platform operates in **Private Deployment Mode** (`REQUIRE_AUTH=true`). Authorized roles and initial credentials:

| Role | Username | Default Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `Admin@Growww2026!` | Full platform administration, source routing, raw downloads |
| **Researcher** | `researcher` | `Research@Growww2026!` | Exploration, AI evidence inspection, adjudications, exports |
| **Viewer** | `viewer` | `Viewer@Growww2026!` | Read-only executive overview, opportunities, PDF digests |
| **Auditor** | `auditor` | `Auditor@Growww2026!` | Audit log inspection, quarantine checks, validation reports |

*Change default passwords immediately in production by setting `ADMIN_PASSWORD`, etc., in `.env`.*

---

## 5. ESSENTIAL OPERATIONAL COMMANDS

### Run Full Test Suite
```bash
PYTHONPATH=.:./lib python3 -m pytest tests/
# Result: 125 passed in 4.23s
```

### System Health Diagnostics
```bash
PYTHONPATH=.:./lib python3 scripts/health_check.py
```

### Create Atomic Database Backup
```bash
PYTHONPATH=.:./lib python3 scripts/backup_database.py
```

### Restore & Validate Database Backup
```bash
PYTHONPATH=.:./lib python3 scripts/restore_database.py \
    --backup-file data/backups/<BACKUP_FILE>.db.gz \
    --target-db data/backups/restored_test.db
```

### Run Performance & Concurrency Benchmark
```bash
PYTHONPATH=.:./lib python3 scripts/benchmark_production.py
```

### Run Weekly Review Ingestion (Dry Run)
```bash
PYTHONPATH=.:./lib python3 scripts/run_scheduled_collection.py --dry-run
```

---

## 6. RESEARCH CITATIONS & METHODOLOGY

Please refer to `docs/research_methodology.md` for full mathematical formulations of the opportunity scoring index, Monte Carlo sensitivity analysis, and SIP lifecycle heuristics.
