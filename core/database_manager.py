"""
Database Manager for Growww Discovery Engine.
Orchestrates schema initialization, configuration synchronization, and database lifecycle.
"""
import os
import sys
from typing import Dict, Any

# Ensure workspace root is always at the front of sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from database.connection import DatabaseConnection, get_db
from database.repositories import (
    AppRepository, SourceRouteRepository, ReviewRepository,
    ImportBatchRepository, IngestionRunRepository, CheckpointRepository
)
from core.config_loader import ConfigLoader, get_config_loader

class DatabaseManager:
    """High-level orchestrator for database operations and repository access."""

    def __init__(self, db: DatabaseConnection = None, config_loader: ConfigLoader = None):
        self.db = db or get_db()
        self.config_loader = config_loader or get_config_loader()
        self.app_repo = AppRepository(self.db)
        self.source_repo = SourceRouteRepository(self.db)
        self.review_repo = ReviewRepository(self.db)
        self.batch_repo = ImportBatchRepository(self.db)
        self.run_repo = IngestionRunRepository(self.db)
        self.checkpoint_repo = CheckpointRepository(self.db)

    def get_connection(self):
        """Returns managed connection context from the underlying DatabaseConnection."""
        return self.db.get_connection()

    def get_cursor(self):
        """Returns managed cursor context from the underlying DatabaseConnection."""
        return self.db.get_cursor()

    def initialize(self):
        """Creates tables, indexes, and syncs YAML configurations."""
        self.db.initialize_schema()
        self.sync_configurations()

    def sync_configurations(self):
        """Reads apps.yml and source_access.yml and syncs to database."""
        # 1. Sync apps
        apps = self.config_loader.get_registered_apps()
        self.app_repo.sync_from_config(apps)

        # 2. Sync sources
        sources = self.config_loader.get_all_sources()
        self.source_repo.sync_from_config(sources)

    def check_health(self) -> Dict[str, Any]:
        """Performs a lightweight query to verify database connectivity and integrity."""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
            
            app_count = self.app_repo.count()
            metrics = self.review_repo.get_summary_metrics()
            
            return {
                "status": "HEALTHY",
                "database_path": self.db.db_path,
                "registered_apps": app_count,
                "total_records": metrics.get("total_records", 0),
                "genuine_reviews": metrics.get("genuine_reviews", 0),
                "total_reviews": metrics.get("genuine_reviews", 0),
                "demo_reviews": metrics.get("demo_reviews", 0),
                "error": None
            }
        except Exception as exc:
            return {
                "status": "UNHEALTHY",
                "database_path": self.db.db_path,
                "registered_apps": 0,
                "total_reviews": 0,
                "error": str(exc)
            }

_db_manager = None

def get_database_manager(db: DatabaseConnection = None) -> DatabaseManager:
    """Returns singleton DatabaseManager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db)
    return _db_manager
