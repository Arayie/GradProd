"""
Opportunity Management and Lifecycle Service (Phase 6)
Manages opportunity backlog queries, audited status transitions, and audit logs.
"""

from typing import Dict, Any, List, Optional
import os
import sqlite3
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class OpportunityService:
    """Manages product discovery opportunities, audited status changes, and export synchronization."""

    VALID_STATUSES = {
        "DISCOVERED",
        "NEEDS_VALIDATION",
        "READY_FOR_EXPERIMENT",
        "IN_PROGRESS",
        "VALIDATED",
        "REJECTED",
        "ON_HOLD",
    }

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            db_path = os.path.join(base_dir, "growww_discovery.db")
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def get_all_opportunities(
        self,
        status: Optional[str] = None,
        lifecycle_stage: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all ranked opportunities with optional status and stage filtering."""
        conn = self.get_connection()
        query = "SELECT * FROM opportunities WHERE 1=1"
        params = []

        if status and status != "ALL":
            query += " AND lifecycle_status = ?"
            params.append(status)
        if lifecycle_stage and lifecycle_stage != "ALL":
            query += " AND lifecycle_stage = ?"
            params.append(lifecycle_stage)

        query += " ORDER BY priority_rank ASC"
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_opportunity(self, opportunity_id: str) -> Optional[Dict[str, Any]]:
        """Get single opportunity by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM opportunities WHERE opportunity_id = ?", (opportunity_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_status(
        self,
        opportunity_id: str,
        new_status: str,
        actor_id: str,
        rationale: str,
    ) -> bool:
        """
        Update opportunity status with mandatory audit recording.
        """
        if new_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid opportunity status: '{new_status}'")
        if not rationale.strip():
            raise ValueError("Adjudication rationale is strictly required for status updates.")

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Fetch previous status
            cursor.execute("SELECT lifecycle_status FROM opportunities WHERE opportunity_id = ?", (opportunity_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False
            previous_status = row["lifecycle_status"]

            # Update opportunity
            cursor.execute(
                """
                UPDATE opportunities 
                SET lifecycle_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE opportunity_id = ?
                """,
                (new_status, opportunity_id),
            )

            # Record audit event
            cursor.execute(
                """
                INSERT INTO opportunity_audits (
                    opportunity_id, actor_id, previous_status, new_status, change_rationale
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (opportunity_id, actor_id, previous_status, new_status, rationale.strip()),
            )

            conn.commit()
            conn.close()

            # Keep CSV in sync
            self.sync_csv_export()
            return True
        except Exception as e:
            conn.rollback()
            conn.close()
            logger.error(f"Failed to update opportunity {opportunity_id}: {e}")
            raise e

    def get_audit_history(self, opportunity_id: str) -> List[Dict[str, Any]]:
        """Retrieve audit history for an opportunity."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM opportunity_audits 
            WHERE opportunity_id = ? 
            ORDER BY changed_at DESC
            """,
            (opportunity_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # Alias for API convenience
    get_opportunity_audits = get_audit_history

    def sync_csv_export(self, output_path: str = "outputs/ranked_product_opportunities.csv"):
        """Synchronize opportunities table to CSV."""
        conn = self.get_connection()
        df = pd.read_sql_query("SELECT * FROM opportunities ORDER BY priority_rank ASC", conn)
        conn.close()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        df.to_csv(output_path, index=False, encoding="utf-8")
