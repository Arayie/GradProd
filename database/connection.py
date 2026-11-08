"""
Database Connection Management for Growww Discovery Engine.
Provides thread-safe connections, transaction context managers, and SQLite / SQLAlchemy initialization.
"""
import os
import sys
import time
import logging
import sqlite3
from typing import Dict, Any, Optional
from urllib.parse import urlsplit, urlunsplit, parse_qs, urlencode
from contextlib import contextmanager

# Ensure workspace root is always at the front of sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

DEFAULT_DB_PATH = os.path.join(REPO_ROOT, "growww_discovery.db")

class DictRow(dict):
    """Row object supporting both dictionary key access and tuple integer index access."""
    def __init__(self, cols, vals):
        super().__init__(zip(cols, vals))
        self._vals = list(vals)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._vals[key]
        return super().__getitem__(key)

class ManagedCursorWrapper:
    """Cursor wrapper providing dictionary row conversion and SQL parameter normalization (? -> %s)."""
    def __init__(self, cursor, is_postgres: bool = False):
        self._cursor = cursor
        self.is_postgres = is_postgres

    def execute(self, sql, params=None):
        if self.is_postgres and params is not None and "?" in sql:
            sql = sql.replace("?", "%s")
        if params is not None:
            return self._cursor.execute(sql, params)
        return self._cursor.execute(sql)

    def executemany(self, sql, seq_of_params):
        if self.is_postgres and "?" in sql:
            sql = sql.replace("?", "%s")
        return self._cursor.executemany(sql, seq_of_params)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        if hasattr(row, "keys") and not isinstance(row, (tuple, list)):
            return row
        cols = [c[0] for c in self._cursor.description] if self._cursor.description else []
        return DictRow(cols, row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        if rows and hasattr(rows[0], "keys") and not isinstance(rows[0], (tuple, list)):
            return rows
        cols = [c[0] for c in self._cursor.description] if self._cursor.description else []
        return [DictRow(cols, r) if isinstance(r, (tuple, list)) else r for r in rows]

    def __iter__(self):
        return iter(self.fetchall())

    def __getattr__(self, name):
        return getattr(self._cursor, name)

class ConnectionWrapper:
    """Wraps DBAPI connection to provide auto ? -> %s translation and DictRow cursors."""
    def __init__(self, raw_conn, is_postgres: bool = False):
        self._raw_conn = raw_conn
        self.is_postgres = is_postgres

    def cursor(self, *args, **kwargs):
        raw_cur = self._raw_conn.cursor(*args, **kwargs)
        return ManagedCursorWrapper(raw_cur, is_postgres=self.is_postgres)

    def execute(self, sql, *args, **kwargs):
        cur = self.cursor()
        cur.execute(sql, *args, **kwargs)
        return cur

    def commit(self):
        if hasattr(self._raw_conn, "commit"):
            self._raw_conn.commit()

    def rollback(self):
        if hasattr(self._raw_conn, "rollback"):
            self._raw_conn.rollback()

    def close(self):
        """Returns the underlying connection back to the connection pool."""
        if hasattr(self._raw_conn, "close"):
            self._raw_conn.close()

    def __getattr__(self, name):
        return getattr(self._raw_conn, name)

def mask_connection_url(url: str) -> str:
    """Masks database password in connection string for safe logging and error reporting."""
    if not url:
        return ""
    if "@" in url and "://" in url:
        prefix, rest = url.split("://", 1)
        auth, host_db = rest.split("@", 1)
        if ":" in auth:
            user, _ = auth.split(":", 1)
            return f"{prefix}://{user}:****@{host_db}"
    return url

def normalize_database_url(url: str) -> str:
    """
    Normalizes PostgreSQL URL for SQLAlchemy using explicit postgresql+psycopg2 driver
    and strictly enforces sslmode=require without query parameter corruption or duplication.
    """
    if not url:
        return url
    normalized = url.strip()
    if not (normalized.startswith("postgres://") or normalized.startswith("postgresql://") or normalized.startswith("postgresql+")):
        return normalized

    parts = urlsplit(normalized)
    scheme = "postgresql+psycopg2"
    query_params = parse_qs(parts.query, keep_blank_values=True)
    
    # Strictly enforce sslmode=require
    query_params["sslmode"] = ["require"]
    new_query = urlencode(query_params, doseq=True)

    return urlunsplit((scheme, parts.netloc, parts.path, new_query, parts.fragment))

def get_env_database_url_with_source() -> tuple:
    """
    Retrieves DATABASE_URL and its configuration source ('environment' vs 'streamlit_secrets').
    Safely inspects st.secrets if available without raising when running outside Streamlit.
    """
    # 1. Inspect Streamlit Cloud secrets first if available
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if "DATABASE_URL" in st.secrets:
                val = str(st.secrets["DATABASE_URL"]).strip()
                if val:
                    return val, "streamlit_secrets"
            # Check nested dictionary structures e.g. [postgres] or [database]
            for sec_key in ("postgres", "database", "postgresql", "render"):
                if sec_key in st.secrets:
                    sec = st.secrets[sec_key]
                    if isinstance(sec, dict):
                        if "url" in sec and sec["url"]:
                            return str(sec["url"]).strip(), "streamlit_secrets"
                        if "DATABASE_URL" in sec and sec["DATABASE_URL"]:
                            return str(sec["DATABASE_URL"]).strip(), "streamlit_secrets"
                        # Assemble components if separate
                        if "host" in sec and ("user" in sec or "username" in sec):
                            user = sec.get("user") or sec.get("username")
                            pwd = sec.get("password", "")
                            host = sec.get("host")
                            port = sec.get("port", 5432)
                            dbname = sec.get("dbname") or sec.get("database", "growww_discovery")
                            return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{dbname}?sslmode=require", "streamlit_secrets"
    except Exception:
        pass

    # 2. Inspect environment variables
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url, "environment"

    return "", "none"

def get_env_database_url() -> str:
    """
    Retrieves DATABASE_URL from environment variables or Streamlit secrets.
    Safely inspects st.secrets if available without raising when running outside Streamlit.
    """
    return get_env_database_url_with_source()[0]

def is_production_environment() -> bool:
    """Detects whether running in production mode (via IS_PRODUCTION, Streamlit Cloud mount, or production env vars)."""
    if os.getenv("IS_PRODUCTION", "").lower() in ("true", "1", "yes"):
        return True
    # Streamlit Cloud deployment environment marker
    if os.path.exists("/mount/src"):
        return True
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if str(st.secrets.get("IS_PRODUCTION", "")).lower() in ("true", "1", "yes"):
                return True
            if str(st.secrets.get("APP_ENV", "")).lower() == "production" and not os.getenv("TESTING"):
                return True
            if str(st.secrets.get("ENVIRONMENT", "")).lower() == "production" and not os.getenv("TESTING"):
                return True
    except Exception:
        pass
    return False

def get_connection_diagnostics(url: str = None, source: str = None) -> Dict[str, Any]:
    """
    Returns safe database connection diagnostics without exposing credentials.
    Reports:
    - Database hostname
    - Database port
    - Database name
    - Selected driver
    - SSL mode
    - Configuration source (environment vs streamlit_secrets)
    Never exposes passwords, usernames, or sensitive connection strings.
    """
    if url is None:
        url, detected_source = get_env_database_url_with_source()
        source = source or detected_source

    if not url:
        return {
            "hostname": "localhost",
            "port": None,
            "database": DEFAULT_DB_PATH,
            "driver": "sqlite3",
            "sslmode": None,
            "source": source or "local_default",
        }

    norm = normalize_database_url(url)
    parts = urlsplit(norm)
    netloc = parts.netloc
    host_port = netloc.split("@")[-1] if "@" in netloc else netloc
    hostname = host_port.split(":")[0] if ":" in host_port else host_port
    port = int(host_port.split(":")[1]) if ":" in host_port and host_port.split(":")[1].isdigit() else 5432
    dbname = parts.path.lstrip("/")
    driver = parts.scheme
    query_params = parse_qs(parts.query)
    sslmode = query_params.get("sslmode", ["require"])[0]

    return {
        "hostname": hostname,
        "port": port,
        "database": dbname,
        "driver": driver,
        "sslmode": sslmode,
        "source": source or "unknown",
    }

class ManagedConnectionContext:
    """Provides a managed connection supporting both context manager usage and direct method access."""
    def __init__(self, db: "DatabaseConnection"):
        self._db = db
        self._conn = None

    def __enter__(self):
        self._conn = self._db.get_raw_connection()
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn is not None:
            try:
                if exc_type is not None:
                    self._conn.rollback()
                else:
                    self._conn.commit()
            finally:
                self._conn.close()
                self._conn = None

    def cursor(self, *args, **kwargs):
        if self._conn is None:
            self._conn = self._db.get_raw_connection()
        return self._conn.cursor(*args, **kwargs)

    def commit(self):
        if self._conn is not None:
            self._conn.commit()

    def rollback(self):
        if self._conn is not None:
            self._conn.rollback()

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __getattr__(self, name):
        if self._conn is None:
            self._conn = self._db.get_raw_connection()
        return getattr(self._conn, name)

def parse_database_url(url: str = None) -> str:
    """Resolves database file path from DATABASE_URL or DATABASE_PATH env var."""
    raw = url or os.getenv("DATABASE_URL") or os.getenv("DATABASE_PATH") or DEFAULT_DB_PATH
    if raw.startswith("sqlite:///"):
        return raw.replace("sqlite:///", "")
    if raw.startswith("sqlite:////"):
        return "/" + raw.replace("sqlite:////", "")
    return raw

class DatabaseConnection:
    """Manages SQLite / PostgreSQL database connections, pooling, verification, and schema setup."""

    def __init__(self, db_path: str = None):
        self.url_source = "default"
        env_url, detected_source = get_env_database_url_with_source()

        if db_path and (db_path.startswith("postgres://") or db_path.startswith("postgresql://") or db_path.startswith("postgresql+")):
            self.raw_url = db_path
            self.url_source = "explicit_argument"
        elif env_url:
            self.raw_url = env_url
            self.url_source = detected_source
        else:
            self.raw_url = ""
            self.url_source = "none"

        self.is_postgres = (
            self.raw_url.startswith("postgres://") or
            self.raw_url.startswith("postgresql://") or
            self.raw_url.startswith("postgresql+")
        )
        self.db_path = db_path or parse_database_url(self.raw_url)
        self._engine = None

        # Missing DATABASE_URL in production raises a clear configuration error.
        # Production never silently falls back to SQLite.
        if is_production_environment() and not self.is_postgres:
            raise RuntimeError(
                "Production environment detected (APP_ENV=production or Streamlit Cloud) but no valid "
                "PostgreSQL DATABASE_URL was found in Streamlit secrets or environment variables. "
                "Production cannot run on SQLite. Please configure DATABASE_URL in Streamlit secrets."
            )

        if not self.is_postgres:
            self._ensure_directory()

    def _ensure_directory(self):
        """Ensures the directory containing the SQLite database exists."""
        directory = os.path.dirname(self.db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def get_diagnostics(self) -> Dict[str, Any]:
        """Returns safe database diagnostics for logging and verification."""
        return get_connection_diagnostics(self.raw_url, self.url_source)

    def log_diagnostics(self):
        """Logs safe database configuration diagnostics without exposing credentials."""
        diag = self.get_diagnostics()
        logging.getLogger("database").info(
            f"Database Configuration Diagnostics: Host='{diag['hostname']}', Port={diag['port']}, "
            f"DB='{diag['database']}', Driver='{diag['driver']}', SSL='{diag['sslmode']}', Source='{diag['source']}'"
        )

    def get_engine(self):
        """Returns cached SQLAlchemy Engine with configured connection pool and SSL settings."""
        if not self.is_postgres:
            return None
        if self._engine is None:
            from sqlalchemy import create_engine
            normalized_url = normalize_database_url(self.raw_url)
            self._engine = create_engine(
                normalized_url,
                pool_pre_ping=True,      # Tests connection liveness before checkout to prevent dead sockets
                pool_size=5,             # Bounded pool size suitable for Render PostgreSQL and Streamlit Cloud
                max_overflow=10,         # Maximum overflow connections
                pool_recycle=300,        # Recycle connections every 5 min to prevent Render idle timeout drops
                pool_timeout=20,         # Maximum wait for a connection before timeout
                connect_args={
                    "sslmode": "require",
                    "connect_timeout": 15,
                    "keepalives": 1,
                    "keepalives_idle": 30,
                    "keepalives_interval": 10,
                    "keepalives_count": 5,
                }
            )
            self.log_diagnostics()
        return self._engine

    def dispose_engine(self):
        """Safely closes all pooled connections and disposes the SQLAlchemy engine."""
        if self._engine is not None:
            try:
                self._engine.dispose()
            except Exception as exc:
                logging.getLogger("database").warning(f"Error disposing SQLAlchemy engine: {exc}")
            finally:
                self._engine = None

    def close(self):
        """Disposes the cached engine and releases connection resources."""
        self.dispose_engine()

    def verify_connection(self, max_retries: int = 3, retry_delay: float = 2.0) -> Dict[str, Any]:
        """
        Verifies database connectivity with bounded exponential backoff retries.
        Runs 'SELECT 1;' and verifies database identity.
        Fails fast on authentication/credential errors.
        Retries transient SSL drops or sleeping Render instances.
        """
        if not self.is_postgres:
            with self.get_connection() as conn:
                res = conn.execute("SELECT 1;").fetchone()
                return {"status": "ok", "dialect": "sqlite", "verified": bool(res)}

        from sqlalchemy import text
        import time
        engine = self.get_engine()
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                with engine.connect() as conn:
                    check = conn.execute(text("SELECT 1;")).scalar()
                    db_name = conn.execute(text("SELECT current_database();")).scalar()
                    db_user = conn.execute(text("SELECT current_user;")).scalar()
                    return {
                        "status": "ok",
                        "dialect": "postgresql",
                        "database": db_name,
                        "user": db_user,
                        "verified": bool(check),
                        "attempt": attempt,
                    }
            except Exception as exc:
                last_error = exc
                err_str = str(exc).lower()
                # Fail fast on authentication/authorization errors
                if any(k in err_str for k in ("password authentication failed", "permission denied", "does not exist", "unknown user")):
                    masked = mask_connection_url(self.raw_url)
                    raise RuntimeError(f"Database authentication failed on {masked}: {exc}") from exc

                # For transient SSL or sleeping Render instances, wait and retry
                if attempt < max_retries:
                    wait_time = retry_delay * (1.5 ** (attempt - 1))
                    time.sleep(wait_time)
                else:
                    masked = mask_connection_url(self.raw_url)
                    raise RuntimeError(
                        f"PostgreSQL connection verification failed after {max_retries} attempts ({masked}): {last_error}"
                    ) from last_error

    def get_raw_connection(self):
        """Returns a configured connection with foreign keys and WAL mode enabled (SQLite) or pooled connection (Postgres)."""
        if self.is_postgres:
            engine = self.get_engine()
            try:
                raw_conn = engine.raw_connection()
                return ConnectionWrapper(raw_conn, is_postgres=True)
            except Exception as exc:
                masked = mask_connection_url(self.raw_url)
                # In production mode, NEVER silently fall back to local SQLite
                raise RuntimeError(
                    f"Production PostgreSQL database connection checkout failed ({masked}): {exc}. "
                    f"Verify DATABASE_URL and Render database status."
                ) from exc

        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        return conn

    def get_connection(self) -> ManagedConnectionContext:
        """Returns a managed connection context supporting with-statement and direct calls."""
        return ManagedConnectionContext(self)

    @contextmanager
    def get_cursor(self):
        """Context manager yielding a managed cursor."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()

    def initialize_schema(self, schema_file: str = None):
        """Executes the DDL schema to create tables and indexes."""
        if self.is_postgres:
            self._initialize_postgres_schema(schema_file=schema_file)
            return

        if schema_file is None:
            schema_file = os.path.join(os.path.dirname(__file__), "schema.sql")

        if not os.path.exists(schema_file):
            raise FileNotFoundError(f"SQLite schema definition file not found at: {schema_file}")

        with open(schema_file, "r", encoding="utf-8") as f:
            ddl_script = f.read()

        with self.get_connection() as conn:
            conn.executescript(ddl_script)

        self.migrate_phase_3_columns()

    def _initialize_postgres_schema(self, schema_file: str = None):
        """
        Ensures PostgreSQL schema tables and indexes exist without dropping existing data.
        Verifies all 11 required tables before deciding whether DDL execution is needed.
        Uses clean SQLAlchemy 2.x transaction management with engine.begin().
        """
        from sqlalchemy import text

        if schema_file is None:
            schema_file = os.path.join(os.path.dirname(__file__), "postgres_schema.sql")

        if not os.path.exists(schema_file):
            raise FileNotFoundError(f"PostgreSQL schema definition file not found at: {schema_file}")

        # 1. Verify connection first with bounded retries
        try:
            self.verify_connection()
        except Exception as exc:
            masked = mask_connection_url(self.raw_url)
            logging.getLogger("database").error(f"PostgreSQL schema initialization connection check failed on {masked}: {exc}")
            raise RuntimeError(f"PostgreSQL schema initialization failed on {masked}: {exc}") from exc

        engine = self.get_engine()
        required_tables = [
            "apps",
            "source_routes",
            "import_batches",
            "ingestion_runs",
            "collection_errors",
            "collection_checkpoints",
            "reviews",
            "ai_evidence_log",
            "human_adjudications",
            "opportunities",
            "opportunity_audits",
        ]

        try:
            # 2. Comprehensive Idempotency Check: inspect all 11 required tables
            with engine.connect() as check_conn:
                existing_res = check_conn.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
                ).fetchall()
                existing_tables = {row[0].lower() for row in existing_res}

            missing_tables = [t for t in required_tables if t.lower() not in existing_tables]
            if not missing_tables:
                logging.getLogger("database").info("PostgreSQL schema verified: all 11 required tables exist.")
                return

            logging.getLogger("database").info(
                f"PostgreSQL schema missing tables: {missing_tables}. Applying postgres_schema.sql..."
            )

            # 3. Read DDL statements from postgres_schema.sql
            with open(schema_file, "r", encoding="utf-8") as f:
                ddl_content = f.read()

            statements = []
            current_stmt = []
            for line in ddl_content.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("--"):
                    continue
                if stripped.upper() in ("BEGIN;", "COMMIT;"):
                    continue
                current_stmt.append(line)
                if stripped.endswith(";"):
                    stmt_text = "\n".join(current_stmt).strip()
                    if stmt_text:
                        statements.append(stmt_text)
                    current_stmt = []

            # 4. Execute DDL in a clean transaction using engine.begin() (SQLAlchemy 2.x standard)
            with engine.begin() as ddl_conn:
                for stmt in statements:
                    ddl_conn.execute(text(stmt))

            # 5. Verify that all required tables now exist
            with engine.connect() as verify_conn:
                post_res = verify_conn.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
                ).fetchall()
                post_tables = {row[0].lower() for row in post_res}
                still_missing = [t for t in required_tables if t.lower() not in post_tables]
                if still_missing:
                    raise RuntimeError(f"PostgreSQL schema initialization incomplete. Missing tables: {still_missing}")

            logging.getLogger("database").info("PostgreSQL schema initialization completed and verified successfully.")

        except Exception as exc:
            masked = mask_connection_url(self.raw_url)
            logging.getLogger("database").error(f"PostgreSQL schema initialization failed on {masked}: {exc}")
            raise RuntimeError(f"PostgreSQL schema initialization failed on {masked}: {exc}") from exc

    def migrate_phase_3_columns(self):
        """Idempotently adds Phase 3 standardization, language, relevance, and quality columns."""
        if self.is_postgres:
            return
        new_columns = [
            ("review_text_original", "TEXT"),
            ("app_name", "TEXT"),
            ("package_name", "TEXT"),
            ("language_confidence", "REAL DEFAULT 0.0"),
            ("script_detected", "TEXT"),
            ("language_detection_method", "TEXT"),
            ("redaction_categories", "TEXT"),
            ("pii_processed_at", "TIMESTAMP"),
            ("developer_reply_present", "INTEGER DEFAULT 0"),
            ("provider_limit_snapshot", "TEXT"),
            ("sip_relevance_status", "TEXT DEFAULT 'NEEDS_REVIEW'"),
            ("matched_query_categories", "TEXT"),
            ("matched_terms", "TEXT"),
            ("relevance_rule_version", "TEXT DEFAULT '1.0.0'"),
            ("mentions_sip", "INTEGER DEFAULT 0"),
            ("mentions_mutual_fund", "INTEGER DEFAULT 0"),
            ("mentions_payment", "INTEGER DEFAULT 0"),
            ("mentions_mandate", "INTEGER DEFAULT 0"),
            ("mentions_autopay", "INTEGER DEFAULT 0"),
            ("mentions_instalment", "INTEGER DEFAULT 0"),
            ("mentions_nav", "INTEGER DEFAULT 0"),
            ("mentions_returns", "INTEGER DEFAULT 0"),
            ("mentions_units", "INTEGER DEFAULT 0"),
            ("mentions_pause_stop", "INTEGER DEFAULT 0"),
            ("mentions_restart", "INTEGER DEFAULT 0"),
            ("mentions_redemption", "INTEGER DEFAULT 0"),
            ("mentions_support", "INTEGER DEFAULT 0"),
            ("mentions_kyc", "INTEGER DEFAULT 0"),
            ("mentions_trust", "INTEGER DEFAULT 0"),
            ("dedupe_group_id", "TEXT"),
            ("duplicate_status", "TEXT DEFAULT 'UNIQUE'"),
            ("duplicate_of_evidence_id", "TEXT"),
            ("deduplication_method", "TEXT"),
            ("data_quality_score", "REAL DEFAULT 1.0"),
            ("data_quality_status", "TEXT DEFAULT 'HIGH_QUALITY'"),
            ("data_quality_issues", "TEXT"),
        ]
        with self.get_connection() as conn:
            c = conn.cursor()
            # Check if reviews table exists
            table_check = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reviews'").fetchone()
            if not table_check:
                return

            existing_cols = {row[1] for row in c.execute("PRAGMA table_info(reviews)").fetchall()}
            for col_name, col_type in new_columns:
                if col_name not in existing_cols:
                    c.execute(f"ALTER TABLE reviews ADD COLUMN {col_name} {col_type};")

            c.execute("CREATE INDEX IF NOT EXISTS idx_reviews_sip_relevance ON reviews(sip_relevance_status);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_reviews_quality_status ON reviews(data_quality_status);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_reviews_language ON reviews(language_detected);")

# Singleton global instance
_db_instance = None

def get_db(db_path: str = None) -> DatabaseConnection:
    """Retrieves or creates the database connection manager singleton."""
    global _db_instance
    if _db_instance is None or (db_path and _db_instance.db_path != db_path):
        _db_instance = DatabaseConnection(db_path)
    return _db_instance
