"""
Ingestion Run Logger and Error Diagnostics for Growww Discovery Engine.
Maintains audit logs in SQLite database and exports to outputs/ingestion_runs.csv
and outputs/collection_errors.csv on demand.
"""
import os
import sys
import uuid
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, List

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from database.connection import get_db, DatabaseConnection
from database.repositories import IngestionRunRepository

OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")

class IngestionRunLogger:
    """Manages audit trails for ingestion sessions and diagnostic error logging."""

    def __init__(self, db: DatabaseConnection = None):
        self.db = db or get_db()
        self.run_repo = IngestionRunRepository(self.db)
        self.active_run_id: Optional[str] = None
        self._ensure_outputs_dir()

    def _ensure_outputs_dir(self):
        """Ensures the outputs directory exists."""
        if not os.path.exists(OUTPUTS_DIR):
            os.makedirs(OUTPUTS_DIR, exist_ok=True)

    def start_run(
        self,
        app_id: str,
        store: str,
        collection_method: str,
        requested_count: int = 0
    ) -> str:
        """Initializes a new ingestion run record in the database."""
        run_id = f"RUN_{app_id[:4].upper()}_{store[:3].upper()}_{uuid.uuid4().hex[:8].upper()}"
        self.active_run_id = run_id
        
        self.run_repo.create_run({
            "run_id": run_id,
            "app_id": app_id,
            "store": store,
            "collection_method": collection_method,
            "started_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "requested_count": requested_count,
            "run_status": "STARTED"
        })
        return run_id

    def finish_run(
        self,
        run_id: str,
        received_count: int,
        accepted_count: int,
        duplicate_count: int,
        rejected_count: int,
        coverage_start: Optional[str] = None,
        coverage_end: Optional[str] = None,
        error_summary: Optional[str] = None,
        status: str = "COMPLETED"
    ):
        """Finalizes an ingestion run with stats and coverage metrics."""
        self.run_repo.update_run_stats(run_id, {
            "completed_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "received_count": received_count,
            "accepted_count": accepted_count,
            "duplicate_count": duplicate_count,
            "rejected_count": rejected_count,
            "coverage_start": coverage_start,
            "coverage_end": coverage_end,
            "error_summary": error_summary,
            "run_status": status
        })
        self.export_to_csv()
        self.export_errors_to_csv()

    def log_error(
        self,
        source_name: str,
        error_type: str,
        error_message: str,
        run_id: Optional[str] = None,
        retry_count: int = 0,
        resolution_status: str = "UNRESOLVED"
    ) -> int:
        """Records an operational failure into collection_errors."""
        err_id = self.run_repo.log_error({
            "run_id": run_id or self.active_run_id,
            "source_name": source_name,
            "error_type": error_type,
            "error_message": error_message,
            "occurred_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "retry_count": retry_count,
            "resolution_status": resolution_status
        })
        self.export_errors_to_csv()
        return err_id

    def export_to_csv(self) -> str:
        """Exports all ingestion run records from SQLite to outputs/ingestion_runs.csv."""
        runs = self.run_repo.list_runs(limit=5000)
        output_file = os.path.join(OUTPUTS_DIR, "ingestion_runs.csv")
        if runs:
            df = pd.DataFrame(runs)
        else:
            df = pd.DataFrame(columns=[
                "run_id", "app_id", "store", "collection_method",
                "started_at", "completed_at", "requested_count",
                "received_count", "accepted_count", "duplicate_count",
                "rejected_count", "run_status", "coverage_start",
                "coverage_end", "error_summary"
            ])
        df.to_csv(output_file, index=False)
        return output_file

    def export_errors_to_csv(self) -> str:
        """Exports all collection error records from SQLite to outputs/collection_errors.csv."""
        errors = self.run_repo.list_errors(limit=5000)
        output_file = os.path.join(OUTPUTS_DIR, "collection_errors.csv")
        if errors:
            df = pd.DataFrame(errors)
        else:
            df = pd.DataFrame(columns=[
                "error_id", "run_id", "source_name", "error_type",
                "error_message", "occurred_at", "retry_count", "resolution_status"
            ])
        df.to_csv(output_file, index=False)
        return output_file

_run_logger = None

def get_run_logger(db: DatabaseConnection = None) -> IngestionRunLogger:
    """Returns singleton instance of IngestionRunLogger."""
    global _run_logger
    if _run_logger is None:
        _run_logger = IngestionRunLogger(db)
    return _run_logger
