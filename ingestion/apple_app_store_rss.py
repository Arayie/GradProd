"""
Apple App Store Public Customer Review RSS Connector for Growww Discovery Engine.
Implements robust HTTP fetching, exponential backoff with jitter, pagination,
checkpointing, incremental collection, and field normalization.
"""
import os
import sys
import json
import time
import random
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from database.repositories import CheckpointRepository
from ingestion.deduplicate import compute_canonical_content_hash
from core.exceptions import DiscoveryEngineError, ValidationError

class FeedCeilingReachedError(DiscoveryEngineError):
    """Raised when requesting beyond Apple's 10-page RSS ceiling (HTTP 400)."""
    pass

class RateLimitExceededError(DiscoveryEngineError):
    """Raised when Apple returns HTTP 429 and retries are exhausted."""
    pass

APPLE_RSS_URL_TEMPLATE = "https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class AppleRSSConnector:
    """Connector for Apple App Store public RSS customer-review feeds."""

    def __init__(
        self,
        checkpoint_repo: Optional[CheckpointRepository] = None,
        timeout_seconds: float = 12.0,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        politeness_delay: float = 0.3
    ):
        self.checkpoint_repo = checkpoint_repo
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.politeness_delay = politeness_delay

    def construct_url(self, app_id: str, page: int = 1, country: str = "in", format_type: str = "json") -> str:
        """Builds the canonical Apple customer reviews endpoint URL."""
        if format_type.lower() == "xml":
            return f"https://itunes.apple.com/{country.lower()}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/xml"
        return APPLE_RSS_URL_TEMPLATE.format(
            country=country.lower(),
            page=page,
            app_id=app_id
        )

    def fetch_page(
        self,
        apple_app_id: str,
        page: int = 1,
        storefront: str = "IN",
        format_type: str = "xml"
    ) -> str:
        """
        Fetches raw page content for an Apple review feed (XML or JSON).
        Raises FeedCeilingReachedError on HTTP 400.
        Raises RateLimitExceededError if 429 persists.
        """
        if page > 10:
            raise FeedCeilingReachedError(f"Apple RSS ceiling reached at page {page} (max 10 pages).")

        url = self.construct_url(app_id=apple_app_id, page=page, country=storefront, format_type=format_type)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "application/xml, application/json, text/xml, */*"
            }
        )

        for attempt in range(1, self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return resp.read().decode("utf-8", errors="replace")
            except urllib.error.HTTPError as http_err:
                if http_err.code == 400:
                    raise FeedCeilingReachedError(f"HTTP 400: Apple pagination ceiling reached at page {page}.")
                if http_err.code == 429:
                    retry_after = http_err.headers.get("Retry-After")
                    wait_sec = float(retry_after) if retry_after else (self.backoff_base * (2 ** attempt))
                    time.sleep(wait_sec)
                    if attempt == self.max_retries:
                        raise RateLimitExceededError(f"HTTP 429: Rate limit exceeded after {self.max_retries} attempts.")
                    continue
                if 500 <= http_err.code < 600:
                    if attempt < self.max_retries:
                        wait_sec = self.backoff_base * (2 ** (attempt - 1))
                        time.sleep(wait_sec)
                        continue
                raise
            except (urllib.error.URLError, TimeoutError):
                if attempt < self.max_retries:
                    time.sleep(self.backoff_base * (2 ** (attempt - 1)))
                    continue
                raise

        raise FeedCeilingReachedError("Max retries exhausted.")

    def parse_feed_xml(
        self,
        xml_string: str,
        app_id: str,
        storefront: str = "IN"
    ) -> List[Dict[str, Any]]:
        """
        Parses Apple Atom XML feed into canonical review dictionaries.
        Strips reviewer name, author URI, and personal identifiers.
        """
        reviews = []
        root = ET.fromstring(xml_string)

        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "im": "http://itunes.apple.com/rss"
        }

        entries = root.findall("atom:entry", ns)
        if not entries:
            entries = root.findall("{http://www.w3.org/2005/Atom}entry")
            if not entries:
                entries = root.findall("entry")

        for entry in entries:
            rating_elem = entry.find("im:rating", ns)
            if rating_elem is None:
                rating_elem = entry.find("{http://itunes.apple.com/rss}rating")
            if rating_elem is None:
                continue

            try:
                star_rating = int(rating_elem.text.strip())
            except (ValueError, AttributeError):
                continue

            # Safe ElementTree element lookup (avoiding bool(elem) == False for childless elements)
            id_elem = entry.find("atom:id", ns)
            if id_elem is None:
                id_elem = entry.find("{http://www.w3.org/2005/Atom}id")
            if id_elem is None:
                id_elem = entry.find("id")

            title_elem = entry.find("atom:title", ns)
            if title_elem is None:
                title_elem = entry.find("{http://www.w3.org/2005/Atom}title")
            if title_elem is None:
                title_elem = entry.find("title")

            content_elem = entry.find("atom:content", ns)
            if content_elem is None:
                content_elem = entry.find("{http://www.w3.org/2005/Atom}content")
            if content_elem is None:
                content_elem = entry.find("content")

            version_elem = entry.find("im:version", ns)
            if version_elem is None:
                version_elem = entry.find("{http://itunes.apple.com/rss}version")

            updated_elem = entry.find("atom:updated", ns)
            if updated_elem is None:
                updated_elem = entry.find("{http://www.w3.org/2005/Atom}updated")
            if updated_elem is None:
                updated_elem = entry.find("updated")

            rev_id = id_elem.text.strip() if id_elem is not None and id_elem.text else ""
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
            content = content_elem.text.strip() if content_elem is not None and content_elem.text else ""
            version = version_elem.text.strip() if version_elem is not None and version_elem.text else None
            updated = updated_elem.text.strip() if updated_elem is not None and updated_elem.text else None

            if not content:
                continue

            content_hash = compute_canonical_content_hash(content)
            now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

            reviews.append({
                "store": "apple_app_store",
                "app_id": app_id,
                "source_record_id": rev_id,
                "canonical_url": f"https://apps.apple.com/in/app/id{app_id}",
                "review_title": title,
                "review_text": content,
                "star_rating": star_rating,
                "app_version": version,
                "storefront": storefront.upper(),
                "review_created_at": updated,
                "retrieved_at": now_utc,
                "content_hash": content_hash,
                "redaction_status": "CLEAN",
                "content_status": "RAW_NORMALIZED",
                "eligibility_status": "ELIGIBLE"
            })

        return reviews

    def fetch_page_payload(self, url: str) -> Tuple[int, Optional[Dict[str, Any]], Optional[str]]:
        """
        Executes an HTTP request with retry logic, exponential backoff, and rate-limit handling.
        Returns: (http_status, json_data_or_none, error_message_or_none)
        """
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "en-US,en;q=0.9"
            }
        )

        for attempt in range(1, self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    status = resp.status
                    raw_body = resp.read().decode("utf-8", errors="replace")
                    try:
                        data = json.loads(raw_body)
                        return status, data, None
                    except json.JSONDecodeError as exc:
                        return status, None, f"JSON decode error: {exc}"

            except urllib.error.HTTPError as http_err:
                status = http_err.code

                # Stop immediately on 401 Unauthorized or 403 Forbidden
                if status in (401, 403):
                    return status, None, f"Access denied (HTTP {status}): {http_err.reason}"

                # Standard Apple hard page cap is 400 Bad Request on page 11+
                if status == 400:
                    return status, None, "Hard pagination ceiling reached (HTTP 400 Bad Request)"

                # Handle Rate Limiting (429)
                if status == 429:
                    retry_after = http_err.headers.get("Retry-After")
                    wait_sec = float(retry_after) if retry_after else (self.backoff_base * (2 ** attempt))
                    time.sleep(wait_sec)
                    continue

                # Temporary 5xx Server Errors -> Retry with exponential backoff & jitter
                if 500 <= status < 600 and attempt < self.max_retries:
                    jitter = random.uniform(0.1, 0.5)
                    wait_sec = (self.backoff_base * (2 ** (attempt - 1))) + jitter
                    time.sleep(wait_sec)
                    continue

                return status, None, f"HTTPError {status}: {http_err.reason}"

            except (urllib.error.URLError, TimeoutError) as net_err:
                if attempt < self.max_retries:
                    jitter = random.uniform(0.1, 0.5)
                    wait_sec = (self.backoff_base * (2 ** (attempt - 1))) + jitter
                    time.sleep(wait_sec)
                    continue
                return 0, None, f"Network/Timeout error: {net_err}"

            except Exception as exc:
                return 0, None, f"Unexpected request failure: {exc}"

        return 0, None, "Max retries exhausted without response"

    def extract_reviews_from_payload(
        self,
        payload: Dict[str, Any],
        internal_app_id: str,
        apple_id: str,
        storefront: str = "IN"
    ) -> List[Dict[str, Any]]:
        """
        Parses Apple RSS Atom feed JSON structure into canonical review dictionaries.
        Strictly excludes reviewer author names and profile URIs.
        """
        feed = payload.get("feed", {})
        entries = feed.get("entry", [])

        if isinstance(entries, dict):
            entries = [entries]

        reviews = []
        now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        for entry in entries:
            # Entry 0 is frequently application metadata which lacks 'im:rating'
            if "im:rating" not in entry:
                continue

            rev_id = entry.get("id", {}).get("label")
            title = entry.get("title", {}).get("label")
            content = entry.get("content", {}).get("label")
            rating_str = entry.get("im:rating", {}).get("label")
            version = entry.get("im:version", {}).get("label")
            updated = entry.get("updated", {}).get("label")
            link_url = entry.get("link", {}).get("attributes", {}).get("href")

            if not content:
                continue

            # Parse rating
            try:
                star_rating = int(rating_str)
            except (ValueError, TypeError):
                continue

            content_hash = compute_canonical_content_hash(content)
            evidence_id = f"EV_{internal_app_id[:4].upper()}_APP_{content_hash[:8]}"

            review_record = {
                "evidence_id": evidence_id,
                "app_id": internal_app_id,
                "store": "apple_app_store",
                "source_record_id": str(rev_id) if rev_id else None,
                "canonical_url": link_url or f"https://apps.apple.com/in/app/id{apple_id}",
                "collection_method": "apple_app_store_rss",
                "review_title": title,
                "review_text": content,
                "star_rating": star_rating,
                "review_created_at": updated,
                "app_version": version,
                "storefront": storefront.upper(),
                "content_hash": content_hash,
                "language_original": "unknown",
                "eligibility_status": "ELIGIBLE",
                "redaction_status": "CLEAN",
                "retrieved_at": now_utc
            }
            reviews.append(review_record)

        return reviews

    def collect_app_reviews(
        self,
        app_config: Dict[str, Any],
        max_pages: int = 10,
        stop_on_checkpoint: bool = True,
        on_page_collected: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Executes a paginated collection run for a single application with checkpointing,
        immediate per-page persistence via on_page_collected, and coverage tracking.
        """
        internal_app_id = app_config["internal_id"]
        apple_id = app_config["apple_app_store"]["app_id"]
        storefront = app_config.get("storefront", "IN")

        # Load existing checkpoint if available
        checkpoint = None
        last_seen_id = None
        if self.checkpoint_repo:
            checkpoint = self.checkpoint_repo.get_checkpoint(
                app_id=internal_app_id,
                storefront=storefront,
                collection_method="apple_app_store_rss"
            )
            if checkpoint:
                last_seen_id = checkpoint.get("last_seen_review_id")

        collected_reviews: List[Dict[str, Any]] = []
        seen_ids = set()
        pages_retrieved = 0
        pages_requested = 0
        http_errors: List[str] = []
        newest_date = None
        oldest_date = None
        hit_checkpoint = False

        for page in range(1, max_pages + 1):
            pages_requested += 1
            url = self.construct_url(app_id=apple_id, page=page, country=storefront)
            status, payload, err = self.fetch_page_payload(url)

            if status != 200 or not payload:
                if status == 400:
                    # Normal Apple hard ceiling reached (usually after page 10)
                    break
                else:
                    http_errors.append(f"Page {page}: HTTP {status} ({err})")
                    break

            pages_retrieved += 1
            page_reviews = self.extract_reviews_from_payload(
                payload=payload,
                internal_app_id=internal_app_id,
                apple_id=apple_id,
                storefront=storefront
            )

            if not page_reviews:
                # Empty page detected
                break

            page_new_reviews = []
            new_on_page = 0
            for r in page_reviews:
                r_id = r.get("source_record_id")
                # Incremental stopping condition: stop if we hit the review ID from the last checkpoint
                if stop_on_checkpoint and last_seen_id and r_id == last_seen_id:
                    hit_checkpoint = True
                    break

                if r_id and r_id in seen_ids:
                    continue

                if r_id:
                    seen_ids.add(r_id)
                collected_reviews.append(r)
                page_new_reviews.append(r)
                new_on_page += 1

            # Immediate per-page callback/persistence
            if on_page_collected and page_new_reviews:
                try:
                    on_page_collected(page, page_new_reviews)
                except Exception as cb_err:
                    http_errors.append(f"Persistence error on page {page}: {cb_err}")

            if hit_checkpoint:
                break

            if new_on_page == 0:
                # Repeated page / loop detected
                break

            time.sleep(self.politeness_delay)

        # Calculate coverage bounds
        if collected_reviews:
            dated = [r for r in collected_reviews if r.get("review_created_at")]
            if dated:
                dated.sort(key=lambda x: str(x["review_created_at"]), reverse=True)
                newest_date = str(dated[0]["review_created_at"])
                oldest_date = str(dated[-1]["review_created_at"])

        # Calculate coverage duration in days
        coverage_days = 0
        if newest_date and oldest_date:
            try:
                dt_new = datetime.strptime(newest_date[:10], "%Y-%m-%d")
                dt_old = datetime.strptime(oldest_date[:10], "%Y-%m-%d")
                coverage_days = max(1, (dt_new - dt_old).days)
            except Exception:
                coverage_days = 0

        # Save new checkpoint if we gathered reviews
        if self.checkpoint_repo and collected_reviews:
            top_review_id = collected_reviews[0].get("source_record_id")
            prev_total = checkpoint.get("total_reviews_collected", 0) if checkpoint else 0
            self.checkpoint_repo.save_checkpoint({
                "app_id": internal_app_id,
                "storefront": storefront,
                "collection_method": "apple_app_store_rss",
                "last_successful_page": pages_retrieved,
                "last_seen_review_id": top_review_id or last_seen_id,
                "last_coverage_date": newest_date,
                "newest_review_date": newest_date,
                "oldest_review_date": oldest_date,
                "total_reviews_collected": prev_total + len(collected_reviews),
                "checkpoint_data": json.dumps({
                    "pages_retrieved": pages_retrieved,
                    "coverage_days": coverage_days,
                    "hit_checkpoint": hit_checkpoint
                })
            })

        status_str = "COMPLETED" if not http_errors else ("PARTIAL" if collected_reviews else "FAILED")

        return {
            "app_id": internal_app_id,
            "apple_id": apple_id,
            "store": "apple_app_store",
            "storefront": storefront,
            "pages_requested": pages_requested,
            "pages_retrieved": pages_retrieved,
            "reviews_received": len(collected_reviews),
            "newest_review_date": newest_date,
            "oldest_review_date": oldest_date,
            "coverage_duration_days": coverage_days,
            "hit_checkpoint": hit_checkpoint,
            "http_errors": http_errors,
            "status": status_str,
            "reviews": collected_reviews
        }
