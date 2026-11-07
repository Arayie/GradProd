"""
Growww Discovery Engine – Render Backend API Service (Phase 8)
Lightweight production HTTP service for health checks, analytical metrics,
opportunity rankings, and scheduled ingestion triggers on Render.
"""

import os
import sys
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

# Ensure workspace and lib in sys.path
REPO_ROOT = os.path.abspath(os.path.dirname(__file__))
LIB_DIR = os.path.join(REPO_ROOT, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from services.health_service import HealthService
from services.analytics_service import AnalyticsService
from services.scheduler_service import ScheduledRefreshService
from database.connection import get_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("growww.backend")

class GrowwwBackendHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for Render Backend Service."""

    def _send_json_response(self, status_code: int, data: Dict[str, Any]):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests."""
        self._send_json_response(200, {"status": "OK"})

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")
        if not path:
            path = "/"

        # 1. Healthcheck Endpoint (used by Render)
        if path in ("/healthz", "/health", "/_health"):
            try:
                diag = HealthService().run_full_diagnostics()
                status_code = 200 if diag["overall_status"] == "HEALTHY" else 503
                self._send_json_response(status_code, diag)
            except Exception as e:
                self._send_json_response(500, {"status": "ERROR", "error": str(e)})

        # 2. Root Welcome Endpoint
        elif path == "/":
            self._send_json_response(200, {
                "service": "GROWWW Investor Discovery Engine – Backend Service",
                "version": "1.0.0",
                "environment": os.getenv("APP_ENV", "production"),
                "endpoints": [
                    "GET /healthz",
                    "GET /api/overview",
                    "GET /api/opportunities",
                    "POST /api/refresh"
                ]
            })

        # 3. Overview Metrics Endpoint
        elif path == "/api/overview":
            try:
                analytics = AnalyticsService()
                overview = analytics.get_executive_overview()
                self._send_json_response(200, overview)
            except Exception as e:
                self._send_json_response(500, {"status": "ERROR", "error": str(e)})

        # 4. Opportunity Rankings Endpoint
        elif path == "/api/opportunities":
            try:
                analytics = AnalyticsService()
                opps = analytics.get_all_opportunities()
                self._send_json_response(200, {"count": len(opps), "opportunities": opps})
            except Exception as e:
                self._send_json_response(500, {"status": "ERROR", "error": str(e)})

        else:
            self._send_json_response(404, {"error": "Not Found", "path": self.path})

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")

        # 1. Trigger Review Refresh
        if path == "/api/refresh":
            try:
                scheduler = ScheduledRefreshService()
                report = scheduler.execute_scheduled_refresh(max_pages=3)
                self._send_json_response(200, report)
            except Exception as e:
                self._send_json_response(500, {"status": "ERROR", "error": str(e)})
        else:
            self._send_json_response(404, {"error": "Not Found", "path": self.path})

def run_server(port: int = None):
    port = port or int(os.getenv("PORT", "8000"))
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, GrowwwBackendHandler)
    logger.info(f"Growww Backend API running on http://0.0.0.0:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping backend server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
