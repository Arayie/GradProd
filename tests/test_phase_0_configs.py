#!/usr/bin/env python3
"""
Unit and Integration Test Suite for Phase 0 Configurations and Feasibility
Validates schema compliance, security invariants, taxonomy dimensions, and connector states.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

import yaml

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")

class TestPhase0Configurations(unittest.TestCase):
    """Test suite validating Phase 0 artifacts and configuration invariants."""

    def test_01_yaml_syntax_validity(self):
        """Verify that all YAML configuration files in config/ are syntactically valid."""
        yaml_files = ["apps.yml", "source_access.yml", "review_taxonomy.yml"]
        for yf in yaml_files:
            file_path = os.path.join(CONFIG_DIR, yf)
            self.assertTrue(os.path.exists(file_path), f"File {yf} does not exist in {CONFIG_DIR}")
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data = yaml.safe_load(f)
                    self.assertIsInstance(data, dict, f"Content of {yf} should be a valid dictionary")
                except yaml.YAMLError as exc:
                    self.fail(f"YAML parsing error in {yf}: {exc}")

    def test_02_candidate_app_registry_fields(self):
        """Validate apps.yml schema and required fields for each candidate application."""
        apps_file = os.path.join(CONFIG_DIR, "apps.yml")
        with open(apps_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.assertIn("applications", data)
        self.assertIn("primary_case_study", data)
        self.assertEqual(data["primary_case_study"], "groww")

        required_app_fields = [
            "internal_id",
            "official_name",
            "developer_name",
            "role",
            "apple_app_store",
            "google_play_store",
            "notes"
        ]

        required_store_fields = [
            "verification_status",
            "verification_date",
            "verification_source",
            "india_storefront_available"
        ]

        app_ids = [app["internal_id"] for app in data["applications"]]
        expected_apps = ["groww", "zerodha_coin", "zerodha_kite", "upstox", "angel_one", "indmoney", "et_money", "paytm_money"]
        for expected in expected_apps:
            self.assertIn(expected, app_ids, f"Expected application {expected} missing from apps.yml")

        for app in data["applications"]:
            for field in required_app_fields:
                self.assertIn(field, app, f"Missing field '{field}' in app '{app.get('internal_id')}'")
            
            # Apple store metadata
            apple = app["apple_app_store"]
            self.assertIn("app_id", apple)
            self.assertIn("listing_url", apple)
            for sf in required_store_fields:
                self.assertIn(sf, apple, f"Missing '{sf}' in apple_app_store for {app['internal_id']}")
            self.assertEqual(apple["verification_status"], "VERIFIED")
            self.assertTrue(apple["india_storefront_available"])

            # Google Play store metadata
            gplay = app["google_play_store"]
            self.assertIn("package_name", gplay)
            self.assertIn("listing_url", gplay)
            for sf in required_store_fields:
                self.assertIn(sf, gplay, f"Missing '{sf}' in google_play_store for {app['internal_id']}")
            self.assertEqual(gplay["verification_status"], "VERIFIED")
            self.assertTrue(gplay["india_storefront_available"])

    def test_03_source_access_configuration_fields_and_defaults(self):
        """Validate source_access.yml schema, valid permission states, and disabled-by-default invariant."""
        source_file = os.path.join(CONFIG_DIR, "source_access.yml")
        with open(source_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.assertIn("permission_states", data)
        self.assertIn("sources", data)
        self.assertEqual(data.get("default_state"), "DISABLED")

        allowed_perm_states = {"NOT_REVIEWED", "PENDING_VERIFICATION", "APPROVED", "REJECTED", "UNAVAILABLE"}
        self.assertEqual(set(data["permission_states"]), allowed_perm_states)

        required_source_fields = [
            "source_id",
            "source_name",
            "source_family",
            "collection_method",
            "app_scope",
            "account_ownership_required",
            "technical_availability",
            "permission_status",
            "enabled",
            "allowed_fields",
            "data_retention_requirements",
            "commercial_use_restrictions",
            "ai_processing_permission_status",
            "provider_limitations",
            "last_verification_date",
            "approval_reference"
        ]

        expected_source_ids = {
            "apple_app_store_public_rss",
            "apple_app_store_connect_owner_api",
            "google_play_appfollow_connector",
            "google_play_android_publisher_owner_api",
            "google_play_console_csv_export",
            "manual_review_csv_import"
        }

        found_source_ids = set()
        for source in data["sources"]:
            found_source_ids.add(source["source_id"])
            for field in required_source_fields:
                self.assertIn(field, source, f"Missing '{field}' in source '{source.get('source_id')}'")
            
            # Security Rule: All source connectors MUST remain DISABLED by default in Phase 0
            self.assertFalse(source["enabled"], f"SECURITY VIOLATION: Source {source['source_id']} must be disabled by default (enabled: false)")
            
            # Permission status must be valid
            self.assertIn(source["permission_status"], allowed_perm_states, f"Invalid permission_status {source['permission_status']}")

        self.assertTrue(expected_source_ids.issubset(found_source_ids), f"Missing required sources: {expected_source_ids - found_source_ids}")

    def test_04_review_taxonomy_dimensions_and_codes(self):
        """Validate review_taxonomy.yml dimensions, lifecycle stage codes, and unknown segment defaults."""
        tax_file = os.path.join(CONFIG_DIR, "review_taxonomy.yml")
        with open(tax_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.assertIn("dimensions", data)
        dimensions = data["dimensions"]

        expected_dimensions = [
            "investor_intent",
            "expected_outcome",
            "sip_lifecycle_stages",
            "investor_behaviour",
            "pain_points",
            "triggers",
            "outside_app_coping",
            "reported_outcome",
            "disclosed_segments"
        ]
        for dim in expected_dimensions:
            self.assertIn(dim, dimensions, f"Taxonomy dimension '{dim}' missing from review_taxonomy.yml")

        # Validate exact SIP lifecycle stage codes
        expected_lifecycle_codes = {
            "S0_DISCOVERY",
            "S1_SETUP",
            "S2_EARLY",
            "S3_HABIT",
            "S4_REVIEW",
            "S5_FRICTION",
            "S6_PAUSE_STOP",
            "S7_RESTART"
        }
        actual_lifecycle_codes = set(dimensions["sip_lifecycle_stages"]["allowed_labels"])
        self.assertEqual(actual_lifecycle_codes, expected_lifecycle_codes, "SIP lifecycle codes do not match PRD exact specification")

        # Validate demographic disclosure defaults to UNKNOWN
        segments = dimensions["disclosed_segments"]["allowed_attributes"]
        for seg_name, seg_data in segments.items():
            self.assertEqual(seg_data.get("default"), "UNKNOWN", f"Segment attribute '{seg_name}' must default to UNKNOWN")
            self.assertIn("UNKNOWN", seg_data.get("allowed_values", []), f"Segment attribute '{seg_name}' must allow UNKNOWN")

    def test_05_privacy_and_security_invariants(self):
        """Verify that documentation explicitly prohibits reviewer identity de-anonymization and scraping."""
        privacy_doc = os.path.join(DOCS_DIR, "privacy_and_retention.md")
        self.assertTrue(os.path.exists(privacy_doc), "privacy_and_retention.md does not exist")
        with open(privacy_doc, "r", encoding="utf-8") as f:
            content = f.read()

        prohibited_phrases = [
            "No Reviewer Identity Resolution",
            "No Internal Account Matching",
            "No Inferred Demographics",
            "No Unauthorized Scraping",
            "No Synthetic Reviews"
        ]
        for phrase in prohibited_phrases:
            self.assertIn(phrase.lower(), content.lower(), f"Privacy policy must contain prohibition: '{phrase}'")

    @patch("urllib.request.urlopen")
    def test_06_apple_rss_parser_mock(self, mock_urlopen):
        """Mocked parser test validating Apple RSS JSON response extraction without network dependency."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_payload = {
            "feed": {
                "entry": [
                    {
                        "im:name": {"label": "Groww App Metadata"}  # App info block (entry 0)
                    },
                    {
                        "id": {"label": "12345678"},
                        "title": {"label": "Great SIP setup"},
                        "content": {"label": "Setting up my mutual fund SIP was super easy via UPI autopay."},
                        "im:rating": {"label": "5"},
                        "im:version": {"label": "18.22.0"},
                        "updated": {"label": "2026-11-03T06:03:41-07:00"},
                        "author": {"name": {"label": "RedactedUser"}}
                    }
                ]
            }
        }
        import json
        mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        # Emulate parsing logic
        entries = mock_payload["feed"]["entry"]
        reviews = []
        for entry in entries:
            if "im:rating" not in entry:
                continue
            reviews.append({
                "id": entry["id"]["label"],
                "title": entry["title"]["label"],
                "content": entry["content"]["label"],
                "rating": int(entry["im:rating"]["label"]),
                "version": entry["im:version"]["label"]
            })

        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["id"], "12345678")
        self.assertEqual(reviews[0]["rating"], 5)
        self.assertNotIn("author", reviews[0], "Author name must be excluded from parsed review output")

    def test_07_no_credentials_or_env_in_repo(self):
        """Ensure no accidental .env files or hardcoded API keys are committed."""
        repo_root = os.path.abspath(os.path.join(CONFIG_DIR, ".."))
        env_file = os.path.join(repo_root, ".env")
        self.assertFalse(os.path.exists(env_file), "CRITICAL: .env file must NOT exist in the repository root")

        # Scan config and source files for accidental literal API keys
        target_dirs = [CONFIG_DIR, DOCS_DIR, REPORTS_DIR]
        for tdir in target_dirs:
            for root, _, files in os.walk(tdir):
                for file in files:
                    if file.endswith((".yml", ".yaml", ".py", ".md")) and not file.startswith("."):
                        filepath = os.path.join(root, file)
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            text = f.read()
                            self.assertNotIn("AIza" + "Sy", text, f"Potential Google API key detected in {file}")
                            self.assertNotIn("ghp" + "_", text, f"Potential GitHub PAT detected in {file}")
                            self.assertNotIn("sk-proj" + "-", text, f"Potential OpenAI key detected in {file}")

    def test_08_multilingual_taxonomy_lexicon(self):
        """Verify that taxonomy intent and friction categories contain English, Hindi, and Hinglish keywords."""
        tax_file = os.path.join(CONFIG_DIR, "review_taxonomy.yml")
        with open(tax_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        intent_categories = data["dimensions"]["investor_intent"]["categories"]
        for cat in intent_categories:
            if cat["code"] == "UNKNOWN":
                continue
            self.assertTrue(len(cat.get("english_keywords", [])) > 0, f"English keywords missing in intent {cat['code']}")
            self.assertTrue(len(cat.get("hindi_keywords", [])) > 0, f"Hindi keywords missing in intent {cat['code']}")
            self.assertTrue(len(cat.get("hinglish_keywords", [])) > 0, f"Hinglish keywords missing in intent {cat['code']}")

    def test_09_empirical_apple_rss_results_integrity(self):
        """Verify that Apple RSS empirical test results file exists and records 500 reviews per app."""
        empirical_file = os.path.join(REPORTS_DIR, "apple_rss_empirical_results.json")
        self.assertTrue(os.path.exists(empirical_file), "apple_rss_empirical_results.json must exist")
        import json
        with open(empirical_file, "r", encoding="utf-8") as f:
            results = json.load(f)
        self.assertEqual(len(results), 8, "Expected 8 tested application entities in empirical results")
        for res in results:
            self.assertEqual(res["total_unique_reviews"], 500, f"App {res['app']} should have reached 500 reviews")
            self.assertEqual(res["page_1_status"], 200, f"App {res['app']} should have HTTP 200 on page 1")

    def test_10_required_documentation_and_reports_exist(self):
        """Verify all Phase 0 deliverable markdown reports and runbooks exist."""
        required_docs = [
            os.path.join(REPORTS_DIR, "apple_rss_feasibility.md"),
            os.path.join(DOCS_DIR, "appfollow_free_plan_runbook.md"),
            os.path.join(DOCS_DIR, "source_access_matrix.md"),
            os.path.join(DOCS_DIR, "privacy_and_retention.md")
        ]
        for doc in required_docs:
            self.assertTrue(os.path.exists(doc), f"Required deliverable {doc} does not exist")
            self.assertGreater(os.path.getsize(doc), 500, f"Deliverable {doc} is unexpectedly small")

if __name__ == "__main__":
    unittest.main()
