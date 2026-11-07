# GROWWW INVESTOR DISCOVERY ENGINE – DATABASE MIGRATION & PERSISTENCE GUIDE
**Document Version:** 1.0  
**Phase:** 8 Production Operations  
**Target Database Engines:** SQLite 3.35+ (WAL Mode) & PostgreSQL 14+  

---

## 1. STORAGE ARCHITECTURE & ENGINE SELECTION

The Growww Investor Discovery Engine employs an engine-agnostic database abstraction layer (`database/connection.py`), allowing seamless operation across two tiers:

| Attribute | Tier 1: SQLite (Production Default) | Tier 2: Managed PostgreSQL (Enterprise) |
| :--- | :--- | :--- |
| **Best For** | Single-container Docker, Cloud VPS, local teams | Multi-replica containers, Kubernetes, enterprise cloud |
| **Setup Complexity** | Zero-config (single file: `growww_discovery.db`) | Requires hosted PostgreSQL instance or RDS |
| **Concurrency Mode** | WAL mode: unlimited concurrent readers, 1 writer | Full ACID multi-writer row-level locking |
| **Memory Footprint** | ~5 MB RAM buffer cache | 20 MB - 60 MB connection pool cache |
| **Connection String** | `sqlite:////app/data/growww_discovery.db` | `postgresql://user:pass@host:5432/growww_discovery` |
| **Tested Dataset** | 3,798 reviews, 1,531 AI evidence rows (8.2 MB) | 100% row-for-row parity |

---

## 2. SQLITE HARDENING FOR PRODUCTION (WAL MODE)

When deploying with SQLite, the following PRAGMAs are executed on every connection:

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 30000;
```

### Why WAL Mode?
1. **Concurrent Read Concurrency:** Multiple Streamlit worker threads can query analytical aggregations simultaneously without blocking write operations or each other.
2. **Durability:** With `synchronous = NORMAL`, committed transactions survive application crashes without sacrificing disk write speed.
3. **Lock Contention Neutralization:** `busy_timeout = 30000` allows threads to wait up to 30 seconds for an active write transaction rather than immediately throwing `sqlite3.OperationalError: database is locked`.

---

## 3. STEP-BY-STEP MIGRATION: SQLITE TO POSTGRESQL

The workspace provides an automated migration script: `scripts/migrate_sqlite_to_postgres.py`.

### Step 1: Generate PostgreSQL DDL & Seed Script
To generate a complete, standalone SQL migration script without requiring a live PostgreSQL instance:

```bash
PYTHONPATH=.:./lib python3 scripts/migrate_sqlite_to_postgres.py \
    --sqlite-path growww_discovery.db \
    --output-sql data/growww_discovery_postgres.sql
```

This creates `data/growww_discovery_postgres.sql` containing:
- Complete table DDL with PostgreSQL data types (`INTEGER`, `DOUBLE PRECISION`, `TIMESTAMP`, `TEXT`).
- Primary key constraints and secondary indexes.
- All 3,798 reviews, 1,531 AI evidence records, and 7 opportunities formatted with `ON CONFLICT DO NOTHING`.

### Step 2: Provision PostgreSQL Database
Create a new database and user on your PostgreSQL cluster (e.g., AWS RDS, Supabase, Neon, or Docker):

```sql
CREATE DATABASE growww_discovery;
CREATE USER growww_user WITH ENCRYPTED PASSWORD 'secure_password_2026';
GRANT ALL PRIVILEGES ON DATABASE growww_discovery TO growww_user;
```

### Step 3: Execute Direct Live Migration
Alternatively, migrate directly over the network:

```bash
PYTHONPATH=.:./lib python3 scripts/migrate_sqlite_to_postgres.py \
    --sqlite-path growww_discovery.db \
    --pg-url "postgresql://growww_user:secure_password_2026@pg-host:5432/growww_discovery"
```

Or pipe the generated SQL script via standard `psql`:

```bash
psql -h pg-host -U growww_user -d growww_discovery -f data/growww_discovery_postgres.sql
```

### Step 4: Update Environment Variables
In your production `.env` file or cloud secrets manager, set:

```ini
DATABASE_URL=postgresql://growww_user:secure_password_2026@pg-host:5432/growww_discovery
```

### Step 5: Post-Migration Parity Verification
Verify row counts match across both databases:

| Table | Expected Count | Description |
| :--- | :--- | :--- |
| `apps` | 8 | Registered application profiles |
| `source_routes` | 6 | Permitted collection routes |
| `import_batches` | 2 | Google Play CSV batches |
| `ingestion_runs` | 12 | Ingestion run logs |
| `reviews` | 3,798 | Total customer reviews (3,790 eligible + 8 quarantined) |
| `ai_evidence_log` | 1,531 | Verbatim quotes & classifications |
| `human_adjudications` | 305 | Gold standard validation rows |
| `opportunities` | 7 | Ranked SIP pain-point opportunities |

Verification query in `psql`:
```sql
SELECT 'reviews' AS tbl, count(*) FROM reviews
UNION ALL SELECT 'ai_evidence_log', count(*) FROM ai_evidence_log
UNION ALL SELECT 'opportunities', count(*) FROM opportunities;
```

---

## 4. CONNECTION POOLING CONFIGURATION (POSTGRESQL)

When connecting to PostgreSQL, `database/connection.py` configures SQLAlchemy's QueuePool:

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=10,          # Standard connection pool
    max_overflow=20,       # Burst headroom for peak research queries
    pool_timeout=30,       # Wait up to 30s before timeout
    pool_recycle=1800,     # Recycle idle connections every 30 mins
    pool_pre_ping=True     # Test connection liveliness before checkout
)
```

---

## 5. PERSISTENT DISK VOLUMES IN CLOUD DEPLOYMENTS

When hosting the SQLite production database on Docker, Kubernetes, or PaaS, mount `/app/data` to a persistent volume:

```yaml
# docker-compose.yml example
volumes:
  - growww_db_data:/app/data

volumes:
  growww_db_data:
    driver: local
```

- **Render:** Attach a Persistent Disk mounted at `/app/data` (minimum 5 GB).
- **Railway:** Attach a Railway Volume mounted at `/app/data`.
- **AWS ECS:** Use an AWS EFS (Elastic File System) volume mapped to `/app/data`.
