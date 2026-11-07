"""
Unit and Integration Tests for Apple App Store RSS Connector (Route A).
Tests feed XML parsing, PII author stripping, pagination ceilings (HTTP 400),
rate-limiting backoff (HTTP 429), server error retries (500), and checkpoint halts.
"""
import unittest
from unittest.mock import patch, MagicMock
import urllib.error
import io
import os
import sys

# Ensure workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from ingestion.apple_app_store_rss import (
    AppleRSSConnector, FeedCeilingReachedError, RateLimitExceededError
)

SAMPLE_APPLE_RSS_XML = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:im="http://itunes.apple.com/rss">
  <id>https://itunes.apple.com/in/rss/customerreviews/page=1/id=1404871703/sortby=mostrecent/xml</id>
  <title>Customer Reviews: Groww</title>
  <updated>2026-11-06T10:00:00-07:00</updated>
  <entry>
    <id>14750020582</id>
    <title>Fund balance not showing</title>
    <content type="text">Fund balance is not updated after SIP debit.</content>
    <im:rating>1</im:rating>
    <im:version>14.2.1</im:version>
    <im:voteCount>0</im:voteCount>
    <im:voteSum>0</im:voteSum>
    <updated>2026-11-04T06:49:50-07:00</updated>
    <author>
      <name>Confidential Reviewer 1</name>
      <uri>https://itunes.apple.com/author/12345</uri>
    </author>
  </entry>
  <entry>
    <id>14746757331</id>
    <title>Great for SIP</title>
    <content type="text">Started my first mutual fund SIP easily without any hassle.</content>
    <im:rating>5</im:rating>
    <im:version>14.2.0</im:version>
    <im:voteCount>3</im:voteCount>
    <im:voteSum>3</im:voteSum>
    <updated>2026-11-03T10:25:11-07:00</updated>
    <author>
      <name>Confidential Reviewer 2</name>
      <uri>https://itunes.apple.com/author/67890</uri>
    </author>
  </entry>
</feed>
"""

SAMPLE_JSON_PAYLOAD = {
    "feed": {
        "entry": [
            {"im:name": {"label": "Groww"}},  # App metadata entry 0
            {
                "id": {"label": "14750020582"},
                "title": {"label": "Fund balance not showing"},
                "content": {"label": "Fund balance is not updated after SIP debit."},
                "im:rating": {"label": "1"},
                "im:version": {"label": "14.2.1"},
                "updated": {"label": "2026-11-04T06:49:50-07:00"},
                "link": {"attributes": {"href": "https://itunes.apple.com/review"}}
            },
            {
                "id": {"label": "14746757331"},
                "title": {"label": "Great for SIP"},
                "content": {"label": "Started my first mutual fund SIP easily."},
                "im:rating": {"label": "5"},
                "im:version": {"label": "14.2.0"},
                "updated": {"label": "2026-11-03T10:25:11-07:00"},
                "link": {"attributes": {"href": "https://itunes.apple.com/review"}}
            }
        ]
    }
}

class TestAppleRSSConnector(unittest.TestCase):
    """Test suite for Apple App Store customer review RSS connector."""

    def setUp(self):
        self.connector = AppleRSSConnector()
        self.app_config = {
            "internal_id": "groww",
            "apple_app_store": {"app_id": "1404871703"},
            "storefront": "IN"
        }

    def test_parse_feed_xml_valid(self):
        """Verifies XML parsing extracts all required fields and completely strips author PII."""
        reviews = self.connector.parse_feed_xml(SAMPLE_APPLE_RSS_XML, app_id="groww", storefront="IN")
        
        self.assertEqual(len(reviews), 2)
        
        rev1 = reviews[0]
        self.assertEqual(rev1["source_record_id"], "14750020582")
        self.assertEqual(rev1["review_title"], "Fund balance not showing")
        self.assertEqual(rev1["star_rating"], 1)
        self.assertEqual(rev1["app_version"], "14.2.1")
        self.assertEqual(rev1["review_created_at"], "2026-11-04T06:49:50-07:00")
        self.assertEqual(rev1["store"], "apple_app_store")
        self.assertEqual(rev1["app_id"], "groww")
        self.assertEqual(rev1["storefront"], "IN")
        self.assertEqual(rev1["redaction_status"], "CLEAN")
        self.assertTrue(len(rev1["content_hash"]) == 64)

        # STRICT PRIVACY INVARIANT: Ensure author name and URI are never stored
        self.assertNotIn("author", rev1)
        self.assertNotIn("author_name", rev1)
        self.assertNotIn("reviewer_name", rev1)
        self.assertNotIn("author_uri", rev1)

        rev2 = reviews[1]
        self.assertEqual(rev2["source_record_id"], "14746757331")
        self.assertEqual(rev2["star_rating"], 5)
        self.assertIn("mutual fund SIP", rev2["review_text"])

    def test_parse_feed_xml_empty(self):
        """Verifies empty or malformed XML feed returns empty list safely."""
        empty_feed = """<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>"""
        reviews = self.connector.parse_feed_xml(empty_feed, app_id="groww")
        self.assertEqual(reviews, [])

    @patch("urllib.request.urlopen")
    def test_fetch_page_http_200_success(self, mock_urlopen):
        """Verifies successful HTTP 200 response fetches XML content."""
        mock_response = MagicMock()
        mock_response.read.return_value = SAMPLE_APPLE_RSS_XML.encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        content = self.connector.fetch_page(apple_app_id="1404871703", page=1, storefront="IN")
        self.assertIn("Customer Reviews: Groww", content)
        self.assertIn("Fund balance not showing", content)

    @patch("urllib.request.urlopen")
    def test_fetch_page_http_400_hard_ceiling(self, mock_urlopen):
        """Verifies Apple's 10-page ceiling (HTTP 400) raises FeedCeilingReachedError."""
        err = urllib.error.HTTPError(
            url="http://itunes.apple.com/rss",
            code=400,
            msg="Bad Request (Beyond Page 10)",
            hdrs={},
            fp=io.BytesIO(b"Page index out of bounds")
        )
        mock_urlopen.side_effect = err

        with self.assertRaises(FeedCeilingReachedError):
            self.connector.fetch_page(apple_app_id="1404871703", page=11, storefront="IN")

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_fetch_page_http_429_rate_limiting_retry(self, mock_sleep, mock_urlopen):
        """Verifies HTTP 429 with Retry-After header backs off and retries."""
        err = urllib.error.HTTPError(
            url="http://itunes.apple.com/rss",
            code=429,
            msg="Too Many Requests",
            hdrs={"Retry-After": "2"},
            fp=io.BytesIO(b"Rate limit exceeded")
        )
        success_response = MagicMock()
        success_response.read.return_value = SAMPLE_APPLE_RSS_XML.encode("utf-8")
        success_response.__enter__.return_value = success_response

        # First call fails with 429, second call succeeds
        mock_urlopen.side_effect = [err, success_response]

        content = self.connector.fetch_page(apple_app_id="1404871703", page=1)
        self.assertIn("Customer Reviews: Groww", content)
        mock_sleep.assert_called()

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_fetch_page_http_500_exponential_backoff(self, mock_sleep, mock_urlopen):
        """Verifies transient HTTP 500 error triggers retries with exponential backoff."""
        err_500 = urllib.error.HTTPError(
            url="http://itunes.apple.com/rss",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=io.BytesIO(b"Server error")
        )
        success_response = MagicMock()
        success_response.read.return_value = SAMPLE_APPLE_RSS_XML.encode("utf-8")
        success_response.__enter__.return_value = success_response

        mock_urlopen.side_effect = [err_500, success_response]

        content = self.connector.fetch_page(apple_app_id="1404871703", page=1)
        self.assertIn("Customer Reviews: Groww", content)
        mock_sleep.assert_called()

    @patch.object(AppleRSSConnector, "fetch_page_payload")
    def test_collect_app_reviews_pagination_stop_on_checkpoint(self, mock_fetch):
        """Verifies incremental collection stops immediately when reaching checkpoint."""
        mock_fetch.return_value = (200, SAMPLE_JSON_PAYLOAD, None)

        # Mock CheckpointRepository returning a checkpoint for the top review
        mock_checkpoint_repo = MagicMock()
        mock_checkpoint_repo.get_checkpoint.return_value = {
            "last_seen_review_id": "14750020582",  # Matches first review in SAMPLE_JSON_PAYLOAD
            "last_successful_page": 1
        }

        connector_with_mock_chk = AppleRSSConnector(checkpoint_repo=mock_checkpoint_repo)
        res = connector_with_mock_chk.collect_app_reviews(
            app_config=self.app_config,
            max_pages=5,
            stop_on_checkpoint=True
        )

        self.assertTrue(res["hit_checkpoint"])
        # Should have stopped on page 1 without fetching page 2
        self.assertEqual(mock_fetch.call_count, 1)

    @patch.object(AppleRSSConnector, "fetch_page_payload")
    def test_collect_app_reviews_full_pagination_metrics(self, mock_fetch):
        """Verifies date span and coverage calculation across multiple pages."""
        payload_page1 = SAMPLE_JSON_PAYLOAD
        payload_page2 = {
            "feed": {
                "entry": [
                    {"im:name": {"label": "Groww"}},
                    {
                        "id": {"label": "14746000001"},
                        "title": {"label": "Page 2 Review 1"},
                        "content": {"label": "Review from page 2 content."},
                        "im:rating": {"label": "4"},
                        "im:version": {"label": "14.2.0"},
                        "updated": {"label": "2026-11-02T10:00:00-07:00"}
                    },
                    {
                        "id": {"label": "14746000002"},
                        "title": {"label": "Page 2 Review 2"},
                        "content": {"label": "Another review from page 2."},
                        "im:rating": {"label": "3"},
                        "im:version": {"label": "14.1.9"},
                        "updated": {"label": "2026-11-01T10:00:00-07:00"}
                    }
                ]
            }
        }
        mock_fetch.side_effect = [
            (200, payload_page1, None),
            (200, payload_page2, None)
        ]
        mock_checkpoint_repo = MagicMock()
        mock_checkpoint_repo.get_checkpoint.return_value = None

        connector = AppleRSSConnector(checkpoint_repo=mock_checkpoint_repo)
        res = connector.collect_app_reviews(
            app_config=self.app_config,
            max_pages=2,
            stop_on_checkpoint=False
        )

        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["pages_retrieved"], 2)
        self.assertEqual(len(res["reviews"]), 4)  # 2 per page * 2 pages
        self.assertEqual(res["newest_review_date"], "2026-11-04T06:49:50-07:00")
        self.assertEqual(res["oldest_review_date"], "2026-11-01T10:00:00-07:00")
        self.assertEqual(res["coverage_duration_days"], 3)  # Nov 4 to Nov 1 = 3 days

if __name__ == "__main__":
    unittest.main()
