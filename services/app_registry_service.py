"""
Application Registry Service for Growww Discovery Engine.
Provides business logic for searching, filtering, and inspecting candidate investment applications.
"""
import os
import sys
from typing import List, Dict, Any, Optional

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from database.connection import get_db
from database.repositories import AppRepository
from core.config_loader import get_config_loader

class AppRegistryService:
    """Service providing search and filtering over registered investment applications."""

    def __init__(self, app_repo: AppRepository = None):
        self.app_repo = app_repo or AppRepository(get_db())
        self.config_loader = get_config_loader()

    def get_all_apps(self) -> List[Dict[str, Any]]:
        """Returns all applications from the database; synchronizes from config if table is empty."""
        apps = self.app_repo.list_all()
        if not apps:
            config_apps = self.config_loader.get_registered_apps()
            self.app_repo.sync_from_config(config_apps)
            apps = self.app_repo.list_all()
        return apps

    def search_apps(
        self,
        query: Optional[str] = None,
        store_filter: Optional[str] = None,
        role_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Filters applications by name/developer search term, storefront, and role."""
        apps = self.get_all_apps()
        filtered = []

        q = query.strip().lower() if query else ""

        for app in apps:
            # Query match
            if q:
                name_match = q in app.get("app_name", "").lower()
                dev_match = q in app.get("developer_name", "").lower()
                id_match = q in app.get("internal_app_id", "").lower()
                if not (name_match or dev_match or id_match):
                    continue

            # Role filter
            if role_filter and role_filter != "ALL":
                if app.get("app_role") != role_filter:
                    continue

            # Store filter
            if store_filter == "APPLE_ONLY" and not app.get("apple_app_id"):
                continue
            elif store_filter == "GOOGLE_PLAY_ONLY" and not app.get("google_play_package"):
                continue

            filtered.append(app)

        return filtered

    def get_app_stats(self) -> Dict[str, Any]:
        """Returns aggregate metrics on registered applications."""
        apps = self.get_all_apps()
        return {
            "total_apps": len(apps),
            "primary_apps": sum(1 for a in apps if a.get("app_role") == "primary_case_study"),
            "competitor_apps": sum(1 for a in apps if a.get("app_role") != "primary_case_study"),
            "apple_ready": sum(1 for a in apps if a.get("apple_app_id")),
            "play_ready": sum(1 for a in apps if a.get("google_play_package"))
        }

_app_registry_service = None

def get_app_registry_service() -> AppRegistryService:
    """Returns singleton instance of AppRegistryService."""
    global _app_registry_service
    if _app_registry_service is None:
        _app_registry_service = AppRegistryService()
    return _app_registry_service
