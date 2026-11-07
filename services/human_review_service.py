"""
Human Review and Validation Service
Manages stratified gold-set sampling, adjudication decisions, rationale recording,
and inter-annotator agreement metrics.
"""

from typing import Dict, Any, List, Optional, Tuple
import os
import json
import sqlite3
import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class HumanReviewService:
    """Service orchestrating human-in-the-loop validation, adjudication, and gold-set management."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            db_path = os.path.join(base_dir, "growww_discovery.db")
        self.db_path = db_path

    def get_connection(self):
        from database.connection import get_db
        return get_db().get_raw_connection()

    def assemble_validation_sample(
        self,
        target_size: int = 300,
        output_csv_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Assemble a representative, stratified human validation sample across apps, languages, and ratings.
        Stratification:
        - 158 direct/indirect SIP reviews (priority)
        - General investment reviews
        - Stratified across all 8 apps and languages (English, Hinglish, Hindi)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Prioritize SIP-relevant reviews, then general investment, then general feedback
        query = """
        SELECT 
            evidence_id, app_id, app_name, store, star_rating,
            language_detected, sip_relevance_status, review_title,
            review_text, review_text_original, canonical_url,
            review_created_at
        FROM reviews
        WHERE eligibility_status = 'ELIGIBLE'
        ORDER BY 
            CASE 
                WHEN sip_relevance_status = 'DIRECT_SIP_RELEVANT' THEN 1
                WHEN sip_relevance_status = 'INDIRECT_SIP_RELEVANT' THEN 2
                WHEN sip_relevance_status = 'GENERAL_INVESTMENT_RELEVANT' THEN 3
                ELSE 4
            END ASC,
            CASE WHEN language_detected IN ('hi', 'hi-Latn', 'mixed') THEN 1 ELSE 2 END ASC,
            star_rating ASC
        LIMIT ?
        """
        cursor.execute(query, (target_size,))
        rows = cursor.fetchall()
        sample = [dict(r) for r in rows]
        conn.close()

        if output_csv_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_csv_path)), exist_ok=True)
            df = pd.DataFrame(sample)
            df.to_csv(output_csv_path, index=False, encoding="utf-8")

        return sample

    def record_adjudication(
        self,
        evidence_id: str,
        enrichment_id: str,
        adjudicator_id: str,
        action: str,  # 'ACCEPT', 'CORRECT', 'REJECT', 'ADD_LABEL'
        dimension: str,
        original_labels: List[str],
        adjudicated_labels: List[str],
        rationale: str,
        original_spans: Optional[Dict[str, Any]] = None,
        adjudicated_spans: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Record a human review decision into human_adjudications and update ai_evidence_log.
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        status_map = {
            "ACCEPT": "ACCEPTED",
            "CORRECT": "CORRECTED",
            "REJECT": "REJECTED",
            "ADD_LABEL": "CORRECTED",
        }
        new_status = status_map.get(action, "CORRECTED")

        try:
            cursor.execute(
                """
                INSERT INTO human_adjudications (
                    evidence_id, enrichment_id, adjudicator_id, adjudication_action,
                    dimension, original_ai_labels, adjudicated_labels,
                    original_evidence_spans, adjudicated_evidence_spans, rationale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_id,
                    enrichment_id,
                    adjudicator_id,
                    action,
                    dimension,
                    json.dumps(original_labels),
                    json.dumps(adjudicated_labels),
                    json.dumps(original_spans or {}),
                    json.dumps(adjudicated_spans or {}),
                    rationale,
                ),
            )
            adj_id = cursor.lastrowid

            # Update ai_evidence_log
            cursor.execute(
                """
                UPDATE ai_evidence_log SET
                    adjudication_status = ?,
                    adjudicated_by = ?,
                    adjudicated_at = CURRENT_TIMESTAMP,
                    adjudication_rationale = ?,
                    adjudicated_labels = ?
                WHERE enrichment_id = ?
                """,
                (
                    new_status,
                    adjudicator_id,
                    rationale,
                    json.dumps({dimension: adjudicated_labels}),
                    enrichment_id,
                ),
            )

            # Update reviews table status
            cursor.execute(
                """
                UPDATE reviews SET
                    ai_adjudication_status = ?
                WHERE evidence_id = ?
                """,
                (new_status, evidence_id),
            )

            conn.commit()
            return adj_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to record adjudication for {evidence_id}: {e}")
            raise e
        finally:
            conn.close()

    def get_pending_adjudications(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get enriched reviews awaiting human review (low confidence or mandatory review)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT e.*, r.review_text, r.review_title, r.star_rating, r.language_detected
            FROM ai_evidence_log e
            JOIN reviews r ON e.evidence_id = r.evidence_id
            WHERE e.adjudication_status = 'PENDING'
            ORDER BY 
                CASE WHEN e.routing_decision = 'MANDATORY_REVIEW' THEN 1 ELSE 2 END ASC,
                e.confidence_overall ASC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        result = [dict(r) for r in rows]
        conn.close()
        return result

    def accept_enrichment(self, enr_id: str, ev_id: str, adjudicator_id: str, rationale: str) -> int:
        """Accepts all AI predictions for an enrichment record."""
        return self.record_adjudication(
            evidence_id=ev_id,
            enrichment_id=enr_id,
            adjudicator_id=adjudicator_id,
            action="ACCEPT",
            dimension="lifecycle_stage",
            original_labels=[],
            adjudicated_labels=[],
            rationale=rationale,
        )

    def correct_enrichment(
        self,
        enr_id: str,
        ev_id: str,
        adjudicator_id: str,
        dimension: str,
        corrected_labels: List[str],
        rationale: str,
    ) -> int:
        """Records a human correction override for an enrichment record."""
        return self.record_adjudication(
            evidence_id=ev_id,
            enrichment_id=enr_id,
            adjudicator_id=adjudicator_id,
            action="CORRECT",
            dimension=dimension,
            original_labels=[],
            adjudicated_labels=corrected_labels,
            rationale=rationale,
        )

    def reject_enrichment(self, enr_id: str, ev_id: str, adjudicator_id: str, rationale: str) -> int:
        """Marks an enrichment record as rejected/irrelevant."""
        return self.record_adjudication(
            evidence_id=ev_id,
            enrichment_id=enr_id,
            adjudicator_id=adjudicator_id,
            action="REJECT",
            dimension="lifecycle_stage",
            original_labels=[],
            adjudicated_labels=["REJECTED"],
            rationale=rationale,
        )

    def get_adjudication_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves recent human adjudication decisions."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT adjudication_id, evidence_id, enrichment_id, adjudicator_id, adjudication_action,
                   dimension, adjudicated_labels, rationale, adjudicated_at
            FROM human_adjudications
            ORDER BY adjudicated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        result = [dict(r) for r in rows]
        conn.close()
        return result

    def export_adjudicated_labels(self, output_csv_path: str) -> int:
        """Export all human adjudication decisions to CSV."""
        conn = self.get_connection()
        df = pd.read_sql_query(
            """
            SELECT a.*, r.review_text, r.app_name, r.language_detected
            FROM human_adjudications a
            JOIN reviews r ON a.evidence_id = r.evidence_id
            ORDER BY a.adjudicated_at DESC
            """,
            conn,
        )
        conn.close()

        os.makedirs(os.path.dirname(os.path.abspath(output_csv_path)), exist_ok=True)
        df.to_csv(output_csv_path, index=False, encoding="utf-8")
        return len(df)
