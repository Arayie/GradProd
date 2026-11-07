"""
Database Repositories for Growww Discovery Engine.
Provides high-level data access interfaces for apps, sources, reviews, and import batches.
"""
import os
import sys
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from database.connection import DatabaseConnection, get_db
from core.exceptions import DatabaseError, DuplicateRecordError

def compute_content_hash(text: str) -> str:
    """Computes a SHA-256 fingerprint of normalized text for deduplication."""
    normalized = " ".join(text.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

class AppRepository:
    """Data access repository for candidate investment applications."""

    def __init__(self, db: DatabaseConnection = None):
        self.db = db or get_db()

    def sync_from_config(self, apps_list: List[Dict[str, Any]]):
        """Synchronizes applications from config/apps.yml into the SQLite database."""
        with self.db.get_cursor() as cursor:
            for app in apps_list:
                apple = app.get("apple_app_store", {})
                gplay = app.get("google_play_store", {})
                
                cursor.execute("""
                    INSERT INTO apps (
                        internal_app_id, app_name, developer_name,
                        apple_app_id, google_play_package,
                        apple_listing_url, google_play_listing_url,
                        storefront, app_role, verification_status,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(internal_app_id) DO UPDATE SET
                        app_name = excluded.app_name,
                        developer_name = excluded.developer_name,
                        apple_app_id = excluded.apple_app_id,
                        google_play_package = excluded.google_play_package,
                        apple_listing_url = excluded.apple_listing_url,
                        google_play_listing_url = excluded.google_play_listing_url,
                        app_role = excluded.app_role,
                        verification_status = excluded.verification_status,
                        updated_at = CURRENT_TIMESTAMP;
                """, (
                    app["internal_id"],
                    app["official_name"],
                    app["developer_name"],
                    apple.get("app_id"),
                    gplay.get("package_name"),
                    apple.get("listing_url"),
                    gplay.get("listing_url"),
                    "IN",
                    app.get("role", "competitor"),
                    apple.get("verification_status", "VERIFIED")
                ))

    def list_all(self) -> List[Dict[str, Any]]:
        """Returns all registered application records ordered by role and name."""
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM apps ORDER BY app_role ASC, app_name ASC;")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_by_internal_id(self, internal_id: str) -> Optional[Dict[str, Any]]:
        """Finds application record by internal ID."""
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM apps WHERE internal_app_id = ?;", (internal_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def count(self) -> int:
        """Returns total count of registered apps."""
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM apps;")
            return cursor.fetchone()[0]


class SourceRouteRepository:
    """Repository for managing review collection routes and permission state."""

    def __init__(self, db: DatabaseConnection = None):
        self.db = db or get_db()

    def sync_from_config(self, sources_list: List[Dict[str, Any]]):
        """Synchronizes source access definitions from source_access.yml into SQLite."""
        with self.db.get_cursor() as cursor:
            for src in sources_list:
                allowed_str = ",".join(src.get("allowed_fields", []))
                cursor.execute("""
                    INSERT INTO source_routes (
                        source_id, source_name, store, collection_method,
                        technical_status, permission_status, enabled,
                        allowed_fields, retention_policy, last_verified_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_id) DO UPDATE SET
                        source_name = excluded.source_name,
                        store = excluded.store,
                        collection_method = excluded.collection_method,
                        technical_status = excluded.technical_status,
                        permission_status = excluded.permission_status,
                        enabled = excluded.enabled,
                        allowed_fields = excluded.allowed_fields,
                        retention_policy = excluded.retention_policy,
                        last_verified_at = excluded.last_verified_at;
                """, (
                    src["source_id"],
                    src["source_name"],
                    src.get("source_family", "unknown"),
                    src.get("collection_method", "unknown"),
                    src.get("technical_availability", "UNAVAILABLE"),
                    src.get("permission_status", "NOT_REVIEWED"),
                    1 if src.get("enabled", False) else 0,
                    allowed_str,
                    src.get("data_retention_requirements", ""),
                    src.get("last_verification_date")
                ))

    def list_all(self) -> List[Dict[str, Any]]:
        """Returns all configured source routes."""
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM source_routes ORDER BY id ASC;")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_by_source_id(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Finds a source route by its unique source_id."""
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM source_routes WHERE source_id = ?;", (source_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def set_enabled(self, source_id: str, enabled: bool):
        """Toggles the enabled status of a source route in the database."""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE source_routes SET enabled = ? WHERE source_id = ?;",
                (1 if enabled else 0, source_id)
            )


class ReviewRepository:
    """Repository managing canonical reviews storage, querying, and filtering."""

    def __init__(self, db: DatabaseConnection = None):
        self.db = db or get_db()

    def insert_review(self, review_data: Dict[str, Any]) -> int:
        """Inserts a single review record. Raises DuplicateRecordError if already present."""
        content_hash = review_data.get("content_hash") or compute_content_hash(review_data["review_text"])
        evidence_id = review_data.get("evidence_id")
        if not evidence_id:
            evidence_id = f"EV_{review_data['app_id']}_{review_data['store'][:3].upper()}_{content_hash[:10]}"

        with self.db.get_cursor() as cursor:
            try:
                cursor.execute("""
                    INSERT INTO reviews (
                        evidence_id, store, app_id, source_record_id,
                        canonical_url, collection_run_id, collection_method,
                        source_permission_id, review_title, review_text,
                        language_original, language_detected, translated_text,
                        content_hash, content_status, redaction_status,
                        storefront, app_version, star_rating,
                        review_created_at, review_updated_at, retrieved_at,
                        provider_name, store_listing_url,
                        eligibility_status, source_policy_version, retention_expiry_at,
                        deletion_status
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?
                    );
                """, (
                    evidence_id,
                    review_data["store"],
                    review_data["app_id"],
                    review_data.get("source_record_id"),
                    review_data.get("canonical_url"),
                    review_data.get("collection_run_id"),
                    review_data.get("collection_method", "manual_csv_import"),
                    review_data.get("source_permission_id"),
                    review_data.get("review_title"),
                    review_data["review_text"],
                    review_data.get("language_original", "unknown"),
                    review_data.get("language_detected"),
                    review_data.get("translated_text"),
                    content_hash,
                    review_data.get("content_status", "ORIGINAL"),
                    review_data.get("redaction_status", "CLEAN"),
                    review_data.get("storefront", "IN"),
                    review_data.get("app_version"),
                    int(review_data["star_rating"]),
                    review_data["review_created_at"],
                    review_data.get("review_updated_at"),
                    review_data.get("provider_name"),
                    review_data.get("store_listing_url"),
                    review_data.get("eligibility_status", "PENDING"),
                    review_data.get("source_policy_version", "1.0.0"),
                    review_data.get("retention_expiry_at"),
                    review_data.get("deletion_status", "ACTIVE")
                ))
                return cursor.lastrowid
            except Exception as e:
                err_str = str(e).lower()
                if "unique constraint" in err_str or "integrityerror" in err_str:
                    raise DuplicateRecordError(f"Duplicate review detected: {review_data.get('source_record_id')} / hash {content_hash}") from e
                raise DatabaseError(f"Failed to insert review: {e}") from e

    def exists(self, app_id: str, store: str, source_record_id: Optional[str] = None, content_hash: Optional[str] = None) -> bool:
        """Checks if a review already exists by platform ID or content fingerprint."""
        with self.db.get_cursor() as cursor:
            if source_record_id:
                cursor.execute("""
                    SELECT 1 FROM reviews 
                    WHERE app_id = ? AND store = ? AND source_record_id = ?;
                """, (app_id, store, source_record_id))
                if cursor.fetchone():
                    return True
            if content_hash:
                cursor.execute("""
                    SELECT 1 FROM reviews 
                    WHERE app_id = ? AND store = ? AND content_hash = ?;
                """, (app_id, store, content_hash))
                if cursor.fetchone():
                    return True
        return False

    def query_reviews(
        self,
        app_id: Optional[str] = None,
        store: Optional[str] = None,
        rating: Optional[int] = None,
        eligibility: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Queries reviews with filters and pagination. Returns (records, total_matching)."""
        where_clauses = ["deletion_status = 'ACTIVE'"]
        params = []

        if app_id:
            where_clauses.append("app_id = ?")
            params.append(app_id)
        if store:
            where_clauses.append("store = ?")
            params.append(store)
        if rating:
            where_clauses.append("star_rating = ?")
            params.append(rating)
        if eligibility:
            where_clauses.append("eligibility_status = ?")
            params.append(eligibility)
        if search_query:
            where_clauses.append("(review_text LIKE ? OR review_title LIKE ?)")
            term = f"%{search_query}%"
            params.extend([term, term])

        where_sql = " AND ".join(where_clauses)

        with self.db.get_cursor() as cursor:
            # Count total matching
            cursor.execute(f"SELECT COUNT(*) FROM reviews WHERE {where_sql};", params)
            total = cursor.fetchone()[0]

            # Fetch page
            query_sql = f"""
                SELECT r.*, a.app_name 
                FROM reviews r
                LEFT JOIN apps a ON r.app_id = a.internal_app_id
                WHERE {where_sql}
                ORDER BY r.review_created_at DESC
                LIMIT ? OFFSET ?;
            """
            cursor.execute(query_sql, params + [limit, offset])
            rows = cursor.fetchall()
            return [dict(row) for row in rows], total

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Calculates foundational metrics for the Overview dashboard."""
        with self.db.get_cursor() as cursor:
            # Review counts by eligibility with strict separation of genuine vs synthetic
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    COALESCE(SUM(CASE WHEN eligibility_status != 'SYNTHETIC_DEMO' THEN 1 ELSE 0 END), 0) as genuine_reviews,
                    COALESCE(SUM(CASE WHEN eligibility_status = 'ELIGIBLE' THEN 1 ELSE 0 END), 0) as eligible_reviews,
                    COALESCE(SUM(CASE WHEN eligibility_status = 'PENDING' THEN 1 ELSE 0 END), 0) as pending_reviews,
                    COALESCE(SUM(CASE WHEN eligibility_status = 'REJECTED' THEN 1 ELSE 0 END), 0) as rejected_reviews,
                    COALESCE(SUM(CASE WHEN eligibility_status = 'SYNTHETIC_DEMO' THEN 1 ELSE 0 END), 0) as demo_reviews,
                    MAX(CASE WHEN eligibility_status != 'SYNTHETIC_DEMO' THEN review_created_at ELSE NULL END) as latest_genuine_review_timestamp,
                    MAX(review_created_at) as latest_review_timestamp,
                    MAX(retrieved_at) as latest_import_timestamp
                FROM reviews
                WHERE deletion_status = 'ACTIVE';
            """)
            raw_summary = dict(cursor.fetchone())
            summary_row = {
                "total_records": raw_summary.get("total_records") or 0,
                "genuine_reviews": raw_summary.get("genuine_reviews") or 0,
                "total_reviews": raw_summary.get("genuine_reviews") or 0,  # Never count synthetic records as genuine
                "eligible_reviews": raw_summary.get("eligible_reviews") or 0,
                "pending_reviews": raw_summary.get("pending_reviews") or 0,
                "rejected_reviews": raw_summary.get("rejected_reviews") or 0,
                "demo_reviews": raw_summary.get("demo_reviews") or 0,
                "latest_genuine_review_timestamp": raw_summary.get("latest_genuine_review_timestamp"),
                "latest_review_timestamp": raw_summary.get("latest_review_timestamp"),
                "latest_import_timestamp": raw_summary.get("latest_import_timestamp")
            }

            # Store counts (Strictly genuine reviews only)
            cursor.execute("""
                SELECT store, COUNT(*) as count 
                FROM reviews 
                WHERE deletion_status = 'ACTIVE' AND eligibility_status != 'SYNTHETIC_DEMO'
                GROUP BY store;
            """)
            store_dist = {row["store"]: row["count"] for row in cursor.fetchall()}

            # Rating counts (Strictly genuine reviews only)
            cursor.execute("""
                SELECT star_rating, COUNT(*) as count 
                FROM reviews 
                WHERE deletion_status = 'ACTIVE' AND eligibility_status != 'SYNTHETIC_DEMO'
                GROUP BY star_rating ORDER BY star_rating ASC;
            """)
            rating_dist = {row["star_rating"]: row["count"] for row in cursor.fetchall()}

            # App distribution (Strictly genuine reviews only)
            cursor.execute("""
                SELECT a.app_name, COUNT(r.id) as count
                FROM apps a
                LEFT JOIN reviews r ON a.internal_app_id = r.app_id AND r.deletion_status = 'ACTIVE' AND r.eligibility_status != 'SYNTHETIC_DEMO'
                GROUP BY a.internal_app_id, a.app_name
                ORDER BY count DESC;
            """)
            app_dist = {row["app_name"]: row["count"] for row in cursor.fetchall()}

            # App store counts in apps table
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_apps,
                    SUM(CASE WHEN apple_app_id IS NOT NULL THEN 1 ELSE 0 END) as apple_supported,
                    SUM(CASE WHEN google_play_package IS NOT NULL THEN 1 ELSE 0 END) as google_play_supported
                FROM apps;
            """)
            app_stats = dict(cursor.fetchone())

            return {
                **summary_row,
                **app_stats,
                "store_distribution": store_dist,
                "rating_distribution": rating_dist,
                "app_distribution": app_dist
            }

    def delete_synthetic_demo_data(self) -> int:
        """Safely removes all records labeled SYNTHETIC_DEMO."""
        with self.db.get_cursor() as cursor:
            cursor.execute("DELETE FROM reviews WHERE eligibility_status = 'SYNTHETIC_DEMO';")
            return cursor.rowcount


class ImportBatchRepository:
    """Repository managing manual CSV import batches."""

    def __init__(self, db: DatabaseConnection = None):
        self.db = db or get_db()

    def create_batch(self, batch_data: Dict[str, Any]):
        """Records initial metadata for an import batch."""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO import_batches (
                    batch_id, original_filename, app_id, store,
                    source_description, permission_status, total_rows,
                    accepted_rows, rejected_rows, duplicate_rows, batch_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                batch_data["batch_id"],
                batch_data["original_filename"],
                batch_data["app_id"],
                batch_data["store"],
                batch_data.get("source_description", ""),
                batch_data.get("permission_status", "PENDING_VERIFICATION"),
                batch_data.get("total_rows", 0),
                batch_data.get("accepted_rows", 0),
                batch_data.get("rejected_rows", 0),
                batch_data.get("duplicate_rows", 0),
                batch_data.get("batch_status", "PROCESSING")
            ))

    def update_batch_stats(self, batch_id: str, accepted: int, rejected: int, duplicates: int, status: str):
        """Updates final counts upon completion of CSV import."""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                UPDATE import_batches SET
                    accepted_rows = ?,
                    rejected_rows = ?,
                    duplicate_rows = ?,
                    batch_status = ?
                WHERE batch_id = ?;
            """, (accepted, rejected, duplicates, status, batch_id))

    def list_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Lists recent import batches for monitoring and auditing."""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                SELECT b.*, a.app_name 
                FROM import_batches b
                LEFT JOIN apps a ON b.app_id = a.internal_app_id
                ORDER BY b.uploaded_at DESC
                LIMIT ?;
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]


class IngestionRunRepository:
    """Repository managing audit trails for review ingestion runs and errors."""

    def __init__(self, db: DatabaseConnection = None):
        self.db = db or get_db()

    def create_run(self, run_data: Dict[str, Any]):
        """Creates an initial ingestion run record."""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO ingestion_runs (
                    run_id, app_id, store, collection_method,
                    started_at, requested_count, run_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (
                run_data["run_id"],
                run_data["app_id"],
                run_data["store"],
                run_data["collection_method"],
                run_data.get("started_at", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
                run_data.get("requested_count", 0),
                run_data.get("run_status", "STARTED")
            ))

    def update_run_stats(self, run_id: str, stats: Dict[str, Any]):
        """Updates ingestion run with final metrics and status."""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                UPDATE ingestion_runs SET
                    completed_at = ?,
                    received_count = ?,
                    accepted_count = ?,
                    rejected_count = ?,
                    duplicate_count = ?,
                    run_status = ?,
                    coverage_start = ?,
                    coverage_end = ?,
                    error_summary = ?
                WHERE run_id = ?;
            """, (
                stats.get("completed_at", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
                stats.get("received_count", 0),
                stats.get("accepted_count", 0),
                stats.get("rejected_count", 0),
                stats.get("duplicate_count", 0),
                stats.get("run_status", "COMPLETED"),
                stats.get("coverage_start"),
                stats.get("coverage_end"),
                stats.get("error_summary"),
                run_id
            ))

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves an ingestion run by ID."""
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM ingestion_runs WHERE run_id = ?;", (run_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_runs(
        self,
        app_id: Optional[str] = None,
        store: Optional[str] = None,
        method: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Queries ingestion runs with optional filtering."""
        where_clauses = []
        params = []

        if app_id:
            where_clauses.append("r.app_id = ?")
            params.append(app_id)
        if store:
            where_clauses.append("r.store = ?")
            params.append(store)
        if method:
            where_clauses.append("r.collection_method = ?")
            params.append(method)
        if status:
            where_clauses.append("r.run_status = ?")
            params.append(status)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        with self.db.get_cursor() as cursor:
            query = f"""
                SELECT r.*, a.app_name
                FROM ingestion_runs r
                LEFT JOIN apps a ON r.app_id = a.internal_app_id
                {where_sql}
                ORDER BY r.started_at DESC
                LIMIT ?;
            """
            cursor.execute(query, params + [limit])
            return [dict(row) for row in cursor.fetchall()]

    def log_error(self, error_data: Dict[str, Any]) -> int:
        """Records a collection failure into collection_errors."""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO collection_errors (
                    run_id, source_name, error_type, error_message,
                    occurred_at, retry_count, resolution_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (
                error_data.get("run_id"),
                error_data["source_name"],
                error_data["error_type"],
                error_data["error_message"],
                error_data.get("occurred_at", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
                error_data.get("retry_count", 0),
                error_data.get("resolution_status", "UNRESOLVED")
            ))
            return cursor.lastrowid

    def list_errors(self, run_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Queries collection errors."""
        with self.db.get_cursor() as cursor:
            if run_id:
                cursor.execute("""
                    SELECT * FROM collection_errors 
                    WHERE run_id = ? 
                    ORDER BY occurred_at DESC LIMIT ?;
                """, (run_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM collection_errors 
                    ORDER BY occurred_at DESC LIMIT ?;
                """, (limit,))
            return [dict(row) for row in cursor.fetchall()]


class CheckpointRepository:
    """Repository managing persistent ingestion checkpoints."""

    def __init__(self, db: DatabaseConnection = None):
        self.db = db or get_db()

    def get_checkpoint(
        self,
        app_id: str,
        storefront: str = "IN",
        collection_method: str = "apple_app_store_rss"
    ) -> Optional[Dict[str, Any]]:
        """Retrieves existing checkpoint state for an application and method."""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM collection_checkpoints
                WHERE app_id = ? AND storefront = ? AND collection_method = ?;
            """, (app_id, storefront, collection_method))
            row = cursor.fetchone()
            return dict(row) if row else None

    def save_checkpoint(self, checkpoint_data: Dict[str, Any]):
        """Persists or updates checkpoint state."""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO collection_checkpoints (
                    app_id, storefront, collection_method,
                    last_successful_page, last_retrieval_timestamp,
                    last_seen_review_id, last_coverage_date,
                    newest_review_date, oldest_review_date,
                    total_reviews_collected, checkpoint_data, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(app_id, storefront, collection_method) DO UPDATE SET
                    last_successful_page = excluded.last_successful_page,
                    last_retrieval_timestamp = excluded.last_retrieval_timestamp,
                    last_seen_review_id = excluded.last_seen_review_id,
                    last_coverage_date = excluded.last_coverage_date,
                    newest_review_date = excluded.newest_review_date,
                    oldest_review_date = excluded.oldest_review_date,
                    total_reviews_collected = excluded.total_reviews_collected,
                    checkpoint_data = excluded.checkpoint_data,
                    updated_at = CURRENT_TIMESTAMP;
            """, (
                checkpoint_data["app_id"],
                checkpoint_data.get("storefront", "IN"),
                checkpoint_data.get("collection_method", "apple_app_store_rss"),
                checkpoint_data.get("last_successful_page", 0),
                checkpoint_data.get("last_retrieval_timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
                checkpoint_data.get("last_seen_review_id"),
                checkpoint_data.get("last_coverage_date"),
                checkpoint_data.get("newest_review_date"),
                checkpoint_data.get("oldest_review_date"),
                checkpoint_data.get("total_reviews_collected", 0),
                checkpoint_data.get("checkpoint_data")
            ))

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """Returns all persistent collection checkpoints."""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                SELECT c.*, a.app_name 
                FROM collection_checkpoints c
                LEFT JOIN apps a ON c.app_id = a.internal_app_id
                ORDER BY c.updated_at DESC;
            """)
            return [dict(row) for row in cursor.fetchall()]

    def reset_checkpoint(
        self,
        app_id: str,
        storefront: str = "IN",
        collection_method: str = "apple_app_store_rss"
    ):
        """Removes a collection checkpoint to trigger a full re-crawl."""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                DELETE FROM collection_checkpoints
                WHERE app_id = ? AND storefront = ? AND collection_method = ?;
            """, (app_id, storefront, collection_method))

