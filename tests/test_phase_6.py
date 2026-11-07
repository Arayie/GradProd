"""
Unit and Integration Test Suite for Phase 6
Covers RBAC permissions, OpportunityService lifecycle governance, pure-Python PDF generation,
page module integrity, and export governance compliance.
"""

import os
import sys
import sqlite3
import pytest
import pandas as pd

from core.auth import AuthService, UserRole, Permission, ROLE_PERMISSIONS
from services.opportunity_service import OpportunityService
from services.pdf_export_service import PDFDocumentWriter, PDFExportService
from ui.navigation import PAGE_DEFINITIONS


class TestPhase6RBAC:
    """Verifies strict Role-Based Access Control matrix and permissions."""

    def test_role_permissions_matrix(self):
        # Admin has full authority
        admin_perms = ROLE_PERMISSIONS[UserRole.ADMIN]
        assert Permission.MANAGE_SOURCES in admin_perms
        assert Permission.UPDATE_OPPORTUNITIES in admin_perms
        assert Permission.ADJUDICATE_REVIEWS in admin_perms
        assert Permission.EXPORT_RAW_DATA in admin_perms
        assert Permission.EXPORT_REPORTS in admin_perms

        # Researcher cannot manage sources or permissions, but can adjudicate and export
        res_perms = ROLE_PERMISSIONS[UserRole.RESEARCHER]
        assert Permission.MANAGE_SOURCES not in res_perms
        assert Permission.MANAGE_PERMISSIONS not in res_perms
        assert Permission.UPDATE_OPPORTUNITIES in res_perms
        assert Permission.ADJUDICATE_REVIEWS in res_perms
        assert Permission.EXPORT_RAW_DATA in res_perms
        assert Permission.EXPORT_REPORTS in res_perms

        # Viewer can only view analytics and export aggregate reports, CANNOT export raw data or adjudicate
        viewer_perms = ROLE_PERMISSIONS[UserRole.VIEWER]
        assert Permission.EXPORT_RAW_DATA not in viewer_perms
        assert Permission.ADJUDICATE_REVIEWS not in viewer_perms
        assert Permission.UPDATE_OPPORTUNITIES not in viewer_perms
        assert Permission.MANAGE_SOURCES not in viewer_perms
        assert Permission.EXPORT_REPORTS in viewer_perms
        assert Permission.VIEW_ANALYTICS in viewer_perms

        # Auditor can export raw data, audit logs, and reports, but CANNOT modify sources or adjudicate
        auditor_perms = ROLE_PERMISSIONS[UserRole.AUDITOR]
        assert Permission.EXPORT_RAW_DATA in auditor_perms
        assert Permission.VIEW_AUDIT_LOGS in auditor_perms
        assert Permission.MANAGE_SOURCES not in auditor_perms
        assert Permission.ADJUDICATE_REVIEWS not in auditor_perms

    def test_auth_service_has_permission(self):
        assert AuthService.has_permission(Permission.UPDATE_OPPORTUNITIES, UserRole.ADMIN) is True
        assert AuthService.has_permission(Permission.UPDATE_OPPORTUNITIES, UserRole.RESEARCHER) is True
        assert AuthService.has_permission(Permission.UPDATE_OPPORTUNITIES, UserRole.VIEWER) is False
        assert AuthService.has_permission(Permission.UPDATE_OPPORTUNITIES, UserRole.AUDITOR) is False

        assert AuthService.has_permission(Permission.EXPORT_RAW_DATA, UserRole.VIEWER) is False
        assert AuthService.has_permission(Permission.EXPORT_RAW_DATA, UserRole.RESEARCHER) is True


class TestOpportunityService:
    """Verifies opportunity lifecycle management, querying, and audit trail persistence."""

    @pytest.fixture
    def test_db(self, tmp_path):
        db_file = str(tmp_path / "test_opportunities.db")
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Create schema
        cursor.execute("""
            CREATE TABLE opportunities (
                opportunity_id TEXT PRIMARY KEY,
                priority_rank INTEGER NOT NULL,
                title TEXT NOT NULL,
                theme_code TEXT NOT NULL,
                lifecycle_stage TEXT NOT NULL,
                target_application TEXT NOT NULL,
                opportunity_score REAL NOT NULL,
                prevalence_score REAL NOT NULL,
                severity_score REAL NOT NULL,
                lifecycle_criticality REAL NOT NULL,
                actionability_score REAL NOT NULL,
                evidence_confidence REAL NOT NULL,
                problem_statement TEXT NOT NULL,
                proposed_intervention TEXT NOT NULL,
                testable_hypothesis TEXT NOT NULL,
                exemplar_verbatim_quote TEXT NOT NULL,
                lifecycle_status TEXT NOT NULL DEFAULT 'DISCOVERED',
                primary_metric TEXT DEFAULT '12-Month First-SIP Active Rate',
                guardrail_metric TEXT DEFAULT 'Mandate Bounce & Dispute Rate',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE TABLE opportunity_audits (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_id TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                previous_status TEXT NOT NULL,
                new_status TEXT NOT NULL,
                change_rationale TEXT NOT NULL,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (opportunity_id) REFERENCES opportunities (opportunity_id)
            );
        """)
        # Insert sample opportunity
        cursor.execute("""
            INSERT INTO opportunities (
                opportunity_id, priority_rank, title, theme_code, lifecycle_stage,
                target_application, opportunity_score, prevalence_score, severity_score,
                lifecycle_criticality, actionability_score, evidence_confidence,
                problem_statement, proposed_intervention, testable_hypothesis,
                exemplar_verbatim_quote, lifecycle_status
            ) VALUES (
                'OPP-TEST', 1, 'Test Mandate Tracker', 'PAYMENT_MANDATE', 'S1_SETUP',
                'Groww', 6.50, 7.0, 6.0, 7.0, 6.0, 0.95,
                'Users experience mandate confusion.', 'Implement live tracker.',
                'If tracker added, drop-off decreases.', 'Mandate took 4 days without update.',
                'DISCOVERED'
            );
        """)
        conn.commit()
        conn.close()
        return db_file

    def test_get_all_opportunities(self, test_db):
        service = OpportunityService(db_path=test_db)
        opps = service.get_all_opportunities()
        assert len(opps) == 1
        assert opps[0]["opportunity_id"] == "OPP-TEST"
        assert opps[0]["lifecycle_status"] == "DISCOVERED"

    def test_update_status_success(self, test_db):
        service = OpportunityService(db_path=test_db)
        success = service.update_status(
            opportunity_id="OPP-TEST",
            new_status="READY_FOR_EXPERIMENT",
            actor_id="researcher_lead_01",
            rationale="Validated by engineering as Q1 priority."
        )
        assert success is True

        # Verify opportunity status updated
        opp = service.get_opportunity("OPP-TEST")
        assert opp["lifecycle_status"] == "READY_FOR_EXPERIMENT"

        # Verify audit record created
        audits = service.get_opportunity_audits("OPP-TEST")
        assert len(audits) == 1
        assert audits[0]["previous_status"] == "DISCOVERED"
        assert audits[0]["new_status"] == "READY_FOR_EXPERIMENT"
        assert audits[0]["actor_id"] == "researcher_lead_01"
        assert "Q1 priority" in audits[0]["change_rationale"]

    def test_update_status_invalid_status_raises(self, test_db):
        service = OpportunityService(db_path=test_db)
        with pytest.raises(ValueError, match="Invalid opportunity status"):
            service.update_status("OPP-TEST", "INVALID_STATUS", "actor", "rationale")

    def test_update_status_empty_rationale_raises(self, test_db):
        service = OpportunityService(db_path=test_db)
        with pytest.raises(ValueError, match="rationale is strictly required"):
            service.update_status("OPP-TEST", "READY_FOR_EXPERIMENT", "actor", "   ")


class TestPDFExportService:
    """Verifies pure-Python PDF generation and document byte structure."""

    def test_pdf_document_writer_output(self, tmp_path):
        out_pdf = str(tmp_path / "test_doc.pdf")
        sections = [
            {"heading": "Executive Summary", "lines": ["Key finding 1", "Key finding 2"]},
            {"heading": "Recommendations", "lines": ["Action item A", "Action item B"]}
        ]
        result_path = PDFDocumentWriter.generate_pdf(
            title="Groww Test Report",
            subtitle="Investor Discovery Summary",
            sections=sections,
            output_path=out_pdf
        )
        assert os.path.exists(result_path)
        assert os.path.getsize(result_path) > 500

        with open(result_path, "rb") as f:
            pdf_bytes = f.read()

        # Valid PDF structure check
        assert pdf_bytes.startswith(b"%PDF-1.4")
        assert b"%%EOF" in pdf_bytes
        assert b"Groww Test Report" in pdf_bytes

    def test_weekly_digest_generation(self, tmp_path):
        out_pdf = str(tmp_path / "weekly_digest.pdf")
        path = PDFExportService.generate_weekly_digest(out_pdf)
        assert os.path.exists(path)
        with open(path, "rb") as f:
            bytes_content = f.read()
        assert bytes_content.startswith(b"%PDF-")
        assert b"Groww Investor Discovery Engine" in bytes_content

    def test_opportunity_dossier_generation(self, tmp_path):
        out_pdf = str(tmp_path / "opportunity_dossier.pdf")
        path = PDFExportService.generate_opportunity_dossier(out_pdf)
        assert os.path.exists(path)
        with open(path, "rb") as f:
            bytes_content = f.read()
        assert bytes_content.startswith(b"%PDF-")
        assert b"Groww SIP Opportunity Dossier" in bytes_content


class TestPhase6PageSuite:
    """Verifies page definition registry and module integrity."""

    def test_page_definitions_count(self):
        # 16 registered pages across the 6 functional sections
        assert len(PAGE_DEFINITIONS) == 16
        page_titles = [p[0] for p in PAGE_DEFINITIONS]

        required_pages = [
            "Executive Overview",
            "Source Manager",
            "Collection History",
            "Review Explorer",
            "SIP Journey Explorer",
            "Investor Behaviour",
            "Theme Explorer",
            "App Comparison",
            "Opportunity Radar",
            "Opportunity Detail",
            "AI Evidence Log",
            "Model Validation",
            "Human Validation",
            "Exports & Reports"
        ]
        for req in required_pages:
            assert req in page_titles, f"Missing required page in navigation: {req}"

    def test_all_pages_have_render(self):
        from ui.pages import (
            executive_overview,
            source_manager_ui,
            collection_history_ui,
            review_explorer_ui,
            sip_journey_explorer,
            investor_behaviour,
            theme_explorer,
            app_comparison,
            opportunity_radar,
            opportunity_detail,
            ai_evidence_log_ui,
            model_validation_ui,
            human_validation_ui,
            exports_reports,
        )
        pages = [
            executive_overview, source_manager_ui, collection_history_ui,
            review_explorer_ui, sip_journey_explorer, investor_behaviour,
            theme_explorer, app_comparison, opportunity_radar, opportunity_detail,
            ai_evidence_log_ui, model_validation_ui, human_validation_ui, exports_reports
        ]
        for p in pages:
            assert hasattr(p, "render"), f"Module {p.__name__} must define a callable render() function"
            assert callable(p.render), f"render in {p.__name__} must be callable"
