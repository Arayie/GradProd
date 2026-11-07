"""
Database Connection Management for Growww Discovery Engine.
Provides thread-safe connections, transaction context managers, and SQLite / SQLAlchemy initialization.
"""
import os
import sys
import sqlite3
from contextlib import contextmanager

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "growww_discovery.db")

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
        self.is_postgres = self.raw_url.startswith("postgres://") or self.raw_url.startswith("postgresql://")
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
            # PostgreSQL connection adapter via SQLAlchemy
            from sqlalchemy import create_engine
            normalized_url = self.raw_url
            if normalized_url.startswith("postgres://"):
                normalized_url = normalized_url.replace("postgres://", "postgresql://", 1)
            engine = create_engine(normalized_url)
            return engine.raw_connection()

        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        return conn

    @contextmanager
    def get_connection(self):
        """Context manager yielding a managed connection with auto-commit and rollback."""
        conn = self.get_raw_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def get_cursor(self):
        """Context manager yielding a managed cursor."""
        with self.get_connection() as conn:
            if self.is_postgres:
                try:
                    import psycopg2.extras
                    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                except Exception:
                    cursor = conn.cursor()
            else:
                cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()

    def initialize_schema(self, schema_file: str = None):
        """Executes the DDL schema to create tables and indexes."""
        if self.is_postgres:
            # PostgreSQL schema is managed via migration scripts
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
