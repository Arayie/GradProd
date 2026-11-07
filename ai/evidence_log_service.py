"""
AI Evidence Log Service
Stores, queries, and exports reproducible audit trails for AI enrichments and verbatim spans.
"""

from typing import Dict, Any, List, Optional
import os
import json
import sqlite3
import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EvidenceLogService:
    """Service for managing the AI Evidence Log in SQLite and exporting research datasets."""

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

    def log_enrichment(
        self,
        enrichment_result: Any,
        source_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Persist an EnrichmentResult into ai_evidence_log and update reviews table.
        Returns enrichment_id.
        """
        res = enrichment_result.to_dict() if hasattr(enrichment_result, "to_dict") else enrichment_result
        evidence_id = res["evidence_id"]
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        enrichment_id = f"ENR-{evidence_id}-{timestamp}"

        meta = source_metadata or {}
        source = meta.get("source", "apple_app_store_public_rss")
        app_name = meta.get("app_name", "Groww")
        store = meta.get("store", "apple_app_store")
        source_record_id = meta.get("source_record_id", "")
        canonical_url = meta.get("canonical_url", "")
        review_created_at = meta.get("review_created_at", "")
        retrieved_at = meta.get("retrieved_at", "")

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO ai_evidence_log (
                    enrichment_id, evidence_id, insight_id, source, app_name, store,
                    source_record_id, canonical_url, review_created_at, retrieved_at,
                    model_provider, model_id, prompt_id, prompt_version, prompt_hash,
                    taxonomy_version, inference_latency_ms, token_count_input, token_count_output,
                    primary_research_relevance, lifecycle_stage, secondary_lifecycle_stages,
                    investor_intent, expectations, behaviour, pain_points, triggers,
                    outside_app_actions, reported_outcome, disclosed_context,
                    confidence_overall, confidence_lifecycle, confidence_intent,
                    confidence_pain_points, confidence_outcome, confidence_tier,
                    routing_decision, evidence_spans, evidence_grounding_status,
                    adjudication_status, reasoning_summary
                ) VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?
                )
                """,
                (
                    enrichment_id,
                    evidence_id,
                    f"INS-{evidence_id[:12]}",
                    source,
                    app_name,
                    store,
                    source_record_id,
                    canonical_url,
                    review_created_at,
                    retrieved_at,
                    res["model_provider"],
                    res["model_id"],
                    "PRM-PHASE4-CLS",
                    res["prompt_version"],
                    res["prompt_hash"],
                    res["taxonomy_version"],
                    res["inference_latency_ms"],
                    res["token_count_input"],
                    res["token_count_output"],
                    res["primary_research_relevance"],
                    res["lifecycle_stage"],
                    json.dumps(res["secondary_lifecycle_stages"]),
                    json.dumps(res["investor_intent"]),
                    json.dumps(res["expectations"]),
                    json.dumps(res["behaviour"]),
                    json.dumps(res["pain_points"]),
                    json.dumps(res["triggers"]),
                    json.dumps(res["outside_app_actions"]),
                    res["reported_outcome"],
                    json.dumps(res["disclosed_context"]),
                    res["confidence_overall"],
                    res["confidence_lifecycle"],
                    res["confidence_intent"],
                    res["confidence_pain_points"],
                    res["confidence_outcome"],
                    res["confidence_tier"],
                    res["routing_decision"],
                    json.dumps(res["evidence_spans"]),
                    res["evidence_grounding_status"],
                    "PENDING",
                    res.get("reasoning_summary", ""),
                ),
            )

            # Update reviews table with summary classification
            primary_pain = res["pain_points"][0] if res["pain_points"] else "NO_PAIN_POINT_STATED"
            cursor.execute(
                """
                UPDATE reviews SET
                    ai_enrichment_status = 'ENRICHED',
                    ai_lifecycle_stage = ?,
                    ai_primary_pain_point = ?,
                    ai_pain_points = ?,
                    ai_confidence_score = ?,
                    ai_confidence_tier = ?,
                    ai_adjudication_status = 'PENDING'
                WHERE evidence_id = ?
                """,
                (
                    res["lifecycle_stage"],
                    primary_pain,
                    json.dumps(res["pain_points"]),
                    res["confidence_overall"],
                    res["confidence_tier"],
                    evidence_id,
                ),
            )

            conn.commit()
            return enrichment_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to log enrichment for {evidence_id}: {e}")
            raise e
        finally:
            conn.close()

    def query_log(
        self,
        app_name: Optional[str] = None,
        lifecycle_stage: Optional[str] = None,
        confidence_tier: Optional[str] = None,
        routing_decision: Optional[str] = None,
        adjudication_status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query AI evidence log with optional filters."""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM ai_evidence_log WHERE 1=1"
        params: List[Any] = []

        if app_name:
            query += " AND app_name = ?"
            params.append(app_name)
        if lifecycle_stage:
            query += " AND lifecycle_stage = ?"
            params.append(lifecycle_stage)
        if confidence_tier:
            query += " AND confidence_tier = ?"
            params.append(confidence_tier)
        if routing_decision:
            query += " AND routing_decision = ?"
            params.append(routing_decision)
        if adjudication_status:
            query += " AND adjudication_status = ?"
            params.append(adjudication_status)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        conn.close()
        return result

    def export_csv(self, output_path: str) -> int:
        """Export all ai_evidence_log records to CSV."""
        conn = self.get_connection()
        df = pd.read_sql_query("SELECT * FROM ai_evidence_log ORDER BY classification_timestamp DESC", conn)
        conn.close()

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        df.to_csv(output_path, index=False, encoding="utf-8")
        return len(df)
