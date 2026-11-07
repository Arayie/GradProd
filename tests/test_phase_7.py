"""
Automated Test Suite for Phase 7 (End-to-End Validation, Model Audit, Security & Hardening)
Verifies gold standard data, model metrics quality gates, evidence audit grounding,
database referential integrity, quarantine isolation, privacy protection, and zero open release blockers.
"""

import os
import sys
import sqlite3
import json
import pytest
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.auth import AuthService, UserRole, Permission, ROLE_PERMISSIONS
from validation.evidence_audit import EvidenceAuditor

DB_PATH = os.path.join(REPO_ROOT, "growww_discovery.db")

class TestPhase7Validation:
    """Verifies Phase 7 validation results, quality gates, and release readiness."""

    def test_01_gold_standard_dataset_exists(self):
        gold_path = os.path.join(REPO_ROOT, "outputs", "gold_standard_300.json")
        assert os.path.exists(gold_path), "Gold standard 300 dataset must exist"
        with open(gold_path, "r", encoding="utf-8") as f:
            gold_data = json.load(f)
        assert len(gold_data) == 300, f"Gold standard must contain exactly 300 records, got {len(gold_data)}"

        # Check required fields
        required_fields = ["evidence_id", "review_text", "app_name", "star_rating", "language", "assigned_labels"]
        for field in required_fields:
            assert field in gold_data[0], f"Gold record missing field: {field}"

    def test_02_inter_annotator_agreement_gates(self):
        csv_path = os.path.join(REPO_ROOT, "outputs", "annotation_agreement_report.csv")
        assert os.path.exists(csv_path), "Annotation agreement report must exist"
        df = pd.read_csv(csv_path)
        assert len(df) == 60, f"Expected 60 double-annotated records, got {len(df)}"

        stage_acc = df["stage_agreement"].mean()
        pain_acc = df["pain_point_agreement"].mean()
        assert stage_acc >= 0.85, f"Stage agreement must be >= 85%, got {stage_acc:.2%}"
        assert pain_acc >= 0.85, f"Pain point agreement must be >= 85%, got {pain_acc:.2%}"

    def test_03_model_evaluation_quality_gates(self):
        metrics_path = os.path.join(REPO_ROOT, "outputs", "model_validation_metrics.csv")
        assert os.path.exists(metrics_path), "Model validation metrics must exist"
        df = pd.read_csv(metrics_path)
        assert len(df) >= 2
        assert all(df["status"] == "PASS"), f"All model metrics gates must pass: {df['status'].tolist()}"

        pain_metrics = df[df["dimension"].str.contains("Pain-Point")].iloc[0]
        lifecycle_metrics = df[df["dimension"].str.contains("Lifecycle")].iloc[0]

        # PRD Quality Gates
        assert float(pain_metrics["macro_f1"]) >= 0.80, f"Pain point Macro F1 must be >= 0.80, got {pain_metrics['macro_f1']}"
        assert float(pain_metrics["cohens_kappa"]) >= 0.70, f"Pain point Kappa must be >= 0.70, got {pain_metrics['cohens_kappa']}"
        assert float(lifecycle_metrics["macro_f1"]) >= 0.75, f"Lifecycle Macro F1 must be >= 0.75, got {lifecycle_metrics['macro_f1']}"
        assert float(lifecycle_metrics["cohens_kappa"]) >= 0.70, f"Lifecycle Kappa must be >= 0.70, got {lifecycle_metrics['cohens_kappa']}"

    def test_04_evidence_grounding_audit(self):
        audit_csv = os.path.join(REPO_ROOT, "outputs", "evidence_audit_results.csv")
        assert os.path.exists(audit_csv), "Evidence audit results CSV must exist"
        df = pd.read_csv(audit_csv)
        assert len(df) == 7, "All 7 opportunities must be audited"
        assert all(df["verdict"] == "PASS"), f"All opportunities must pass evidence audit: {df['verdict'].tolist()}"

    def test_05_database_referential_integrity(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_key_check;")
        violations = cursor.fetchall()
        conn.close()
        assert len(violations) == 0, f"Expected 0 foreign key violations, found {len(violations)}"

    def test_06_quarantine_enforcement(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM reviews WHERE eligibility_status = 'SYNTHETIC_DEMO'")
        demo_cnt = cursor.fetchone()[0]
        assert demo_cnt == 8, f"Expected exactly 8 synthetic demo records, got {demo_cnt}"

        cursor.execute("""
            SELECT COUNT(*) FROM ai_evidence_log a
            JOIN reviews r ON a.evidence_id = r.evidence_id
            WHERE r.eligibility_status = 'SYNTHETIC_DEMO'
        """)
        leaked_cnt = cursor.fetchone()[0]
        conn.close()
        assert leaked_cnt == 0, f"Synthetic demo records must not exist in ai_evidence_log, found {leaked_cnt}"

    def test_07_rbac_permission_matrix(self):
        # Viewer cannot export raw data or adjudicate
        assert AuthService.has_permission(Permission.EXPORT_RAW_DATA, UserRole.VIEWER) is False
        assert AuthService.has_permission(Permission.ADJUDICATE_REVIEWS, UserRole.VIEWER) is False

        # Admin can do all
        assert AuthService.has_permission(Permission.MANAGE_SOURCES, UserRole.ADMIN) is True
        assert AuthService.has_permission(Permission.EXPORT_RAW_DATA, UserRole.ADMIN) is True

        # Researcher can adjudicate and export raw data, but cannot manage sources
        assert AuthService.has_permission(Permission.ADJUDICATE_REVIEWS, UserRole.RESEARCHER) is True
        assert AuthService.has_permission(Permission.MANAGE_SOURCES, UserRole.RESEARCHER) is False

    def test_08_release_blockers_zero_open(self):
        blockers_csv = os.path.join(REPO_ROOT, "outputs", "release_blockers.csv")
        assert os.path.exists(blockers_csv), "release_blockers.csv must exist"
        df = pd.read_csv(blockers_csv)

        open_critical = df[(df["severity"] == "CRITICAL") & (df["status"] != "RESOLVED")]
        open_major = df[(df["severity"] == "MAJOR") & (df["status"] != "RESOLVED")]

        assert len(open_critical) == 0, f"Found {len(open_critical)} open CRITICAL blockers"
        assert len(open_major) == 0, f"Found {len(open_major)} open MAJOR blockers"
