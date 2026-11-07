"""
Database Connection Management for Growww Discovery Engine.
Provides thread-safe connections, transaction context managers, and SQLite / SQLAlchemy initialization.
"""
import os
import sys
import sqlite3
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
    """Normalizes PostgreSQL URL for SQLAlchemy using the explicit psycopg2 driver."""
    if not url:
        return url
    normalized = url.strip()
    if normalized.startswith("postgres://"):
        normalized = normalized.replace("postgres://", "postgresql+psycopg2://", 1)
    elif normalized.startswith("postgresql://") and not normalized.startswith("postgresql+"):
        normalized = normalized.replace("postgresql://", "postgresql+psycopg2://", 1)
    return normalized

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
    """Manages SQLite / PostgreSQL database connections and schema setup."""

    def __init__(self, db_path: str = None):
        self.raw_url = os.getenv("DATABASE_URL", "")
        self.is_postgres = (
            self.raw_url.startswith("postgres://") or
            self.raw_url.startswith("postgresql://") or
            self.raw_url.startswith("postgresql+")
        )
        self.db_path = db_path or parse_database_url(self.raw_url)
        if not self.is_postgres:
            self._ensure_directory()

    def _ensure_directory(self):
        """Ensures the directory containing the SQLite database exists."""
        directory = os.path.dirname(self.db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def get_raw_connection(self):
        """Returns a configured connection with foreign keys and WAL mode enabled."""
        if self.is_postgres:
            # PostgreSQL connection adapter via SQLAlchemy with explicit psycopg2 driver
            from sqlalchemy import create_engine
            normalized_url = normalize_database_url(self.raw_url)
            try:
                engine = create_engine(normalized_url)
                raw_conn = engine.raw_connection()
                return ConnectionWrapper(raw_conn, is_postgres=True)
            except Exception as exc:
                masked = mask_connection_url(self.raw_url)
                # In production mode, NEVER silently fall back to local SQLite
                raise RuntimeError(
                    f"Production PostgreSQL database connection failed ({masked}): {exc}. "
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
            self._initialize_postgres_schema()
            return

        if schema_file is None:
            schema_file = os.path.join(os.path.dirname(__file__), "schema.sql")

        if not os.path.exists(schema_file):
            raise FileNotFoundError(f"Schema definition file not found at: {schema_file}")

        with open(schema_file, "r", encoding="utf-8") as f:
            ddl_script = f.read()

        with self.get_connection() as conn:
            conn.executescript(ddl_script)

        self.migrate_phase_3_columns()

    def _initialize_postgres_schema(self):
        """Ensures PostgreSQL schema tables and indexes exist without dropping existing data."""
        from sqlalchemy import create_engine, text
        normalized_url = normalize_database_url(self.raw_url)
        engine = create_engine(normalized_url)

        try:
            with engine.connect() as conn:
                # Check if tables already exist
                table_exists = conn.execute(text("SELECT to_regclass('public.reviews');")).scalar()
                if table_exists:
                    return

                # If brand new database, apply DDL statements individually
                from scripts.migrate_sqlite_to_postgres import generate_postgres_ddl_list
                sqlite_conn = sqlite3.connect(DEFAULT_DB_PATH)
                stmts = generate_postgres_ddl_list(sqlite_conn)
                sqlite_conn.close()

                for stmt in stmts:
                    try:
                        conn.execute(text(stmt))
                        conn.commit()
                    except Exception:
                        conn.rollback()
        except Exception as exc:
            import logging
            logging.getLogger("database").error(f"PostgreSQL schema initialization check: {exc}")

        if schema_file is None:
            schema_file = os.path.join(os.path.dirname(__file__), "schema.sql")

        if not os.path.exists(schema_file):
            raise FileNotFoundError(f"Schema definition file not found at: {schema_file}")

        with open(schema_file, "r", encoding="utf-8") as f:
            ddl_script = f.read()

        with self.get_connection() as conn:
            conn.executescript(ddl_script)

        self.migrate_phase_3_columns()

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
