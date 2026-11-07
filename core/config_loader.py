"""
Central Configuration Loader for Growww Discovery Engine.
Loads, validates, and exposes apps.yml, source_access.yml, and review_taxonomy.yml.
"""
import os
import sys
import yaml
from typing import Dict, List, Any, Optional

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from core.exceptions import ConfigError

DEFAULT_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")

class ConfigLoader:
    """Loads and validates all project YAML configuration files."""

    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or DEFAULT_CONFIG_DIR
        self._apps_data: Optional[Dict[str, Any]] = None
        self._source_access_data: Optional[Dict[str, Any]] = None
        self._review_taxonomy_data: Optional[Dict[str, Any]] = None

    def _read_yaml(self, filename: str) -> Dict[str, Any]:
        """Safely parses a YAML file from the config directory."""
        filepath = os.path.join(self.config_dir, filename)
        if not os.path.exists(filepath):
            raise ConfigError(f"Required configuration file not found: {filename} (searched in {self.config_dir})")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                if not isinstance(content, dict):
                    raise ConfigError(f"Root structure of {filename} must be a dictionary/mapping, got {type(content).__name__}")
                return content
        except yaml.YAMLError as exc:
            raise ConfigError(f"YAML parsing error in {filename}: {exc}") from exc
        except Exception as exc:
            raise ConfigError(f"Unexpected error reading {filename}: {exc}") from exc

    # -------------------------------------------------------------------------
    # Apps Configuration (apps.yml)
    # -------------------------------------------------------------------------
    def get_apps_config(self, reload: bool = False) -> Dict[str, Any]:
        """Loads and validates apps.yml."""
        if self._apps_data is None or reload:
            data = self._read_yaml("apps.yml")
            self._validate_apps_config(data)
            self._apps_data = data
        return self._apps_data

    def _validate_apps_config(self, data: Dict[str, Any]):
        """Validates schema requirements for apps.yml."""
        if "applications" not in data or not isinstance(data["applications"], list):
            raise ConfigError("apps.yml must define an 'applications' list.")

        if "primary_case_study" not in data:
            raise ConfigError("apps.yml must specify 'primary_case_study'.")

        required_keys = [
            "internal_id",
            "official_name",
            "developer_name",
            "role",
            "apple_app_store",
            "google_play_store"
        ]

        internal_ids = set()
        for idx, app in enumerate(data["applications"]):
            for key in required_keys:
                if key not in app:
                    raise ConfigError(f"App index {idx} in apps.yml is missing required field '{key}'.")

            app_id = app["internal_id"]
            if app_id in internal_ids:
                raise ConfigError(f"Duplicate internal_id '{app_id}' detected in apps.yml.")
            internal_ids.add(app_id)

            # Store checks
            apple = app["apple_app_store"]
            if "app_id" not in apple or not apple["app_id"]:
                raise ConfigError(f"App '{app_id}' has missing Apple App ID.")

            gplay = app["google_play_store"]
            if "package_name" not in gplay or not gplay["package_name"]:
                raise ConfigError(f"App '{app_id}' has missing Google Play package name.")

    def get_registered_apps(self) -> List[Dict[str, Any]]:
        """Returns the list of all registered application dictionaries."""
        return self.get_apps_config().get("applications", [])

    def get_app_by_id(self, internal_id: str) -> Optional[Dict[str, Any]]:
        """Finds an application by its internal identifier."""
        for app in self.get_registered_apps():
            if app.get("internal_id") == internal_id:
                return app
        return None

    # -------------------------------------------------------------------------
    # Source Access Configuration (source_access.yml)
    # -------------------------------------------------------------------------
    def get_source_access_config(self, reload: bool = False) -> Dict[str, Any]:
        """Loads and validates source_access.yml."""
        if self._source_access_data is None or reload:
            data = self._read_yaml("source_access.yml")
            self._validate_source_access_config(data)
            self._source_access_data = data
        return self._source_access_data

    def _validate_source_access_config(self, data: Dict[str, Any]):
        """Validates source_access.yml rules and default disabled state."""
        if "sources" not in data or not isinstance(data["sources"], list):
            raise ConfigError("source_access.yml must define a 'sources' list.")

        allowed_perm_states = {"NOT_REVIEWED", "PENDING_VERIFICATION", "APPROVED", "REJECTED", "UNAVAILABLE"}

        for src in data["sources"]:
            src_id = src.get("source_id")
            if not src_id:
                raise ConfigError("Every source entry must specify 'source_id'.")

            perm_status = src.get("permission_status")
            if perm_status not in allowed_perm_states:
                raise ConfigError(f"Source '{src_id}' has invalid permission_status '{perm_status}'.")

    def get_active_sources(self) -> List[Dict[str, Any]]:
        """Returns only sources that are both technically available and operationally enabled."""
        config = self.get_source_access_config()
        active = []
        for src in config.get("sources", []):
            # Strict governance: must be enabled and not rejected
            if src.get("enabled", False) and src.get("permission_status") == "APPROVED":
                active.append(src)
        return active

    def get_all_sources(self) -> List[Dict[str, Any]]:
        """Returns all configured source routes with their current permissions and statuses."""
        return self.get_source_access_config().get("sources", [])

    def is_source_permitted(self, source_id: str) -> bool:
        """Checks if a collection route is permitted for active ingestion."""
        for src in self.get_all_sources():
            if src.get("source_id") == source_id:
                return src.get("permission_status") == "APPROVED" and src.get("enabled", False)
        return False

    # -------------------------------------------------------------------------
    # Review Taxonomy Configuration (review_taxonomy.yml)
    # -------------------------------------------------------------------------
    def get_review_taxonomy_config(self, reload: bool = False) -> Dict[str, Any]:
        """Loads and validates review_taxonomy.yml."""
        if self._review_taxonomy_data is None or reload:
            data = self._read_yaml("review_taxonomy.yml")
            self._validate_taxonomy_config(data)
            self._review_taxonomy_data = data
        return self._review_taxonomy_data

    def _validate_taxonomy_config(self, data: Dict[str, Any]):
        """Validates review_taxonomy.yml schema and PRD lifecycle stages."""
        if "dimensions" not in data or not isinstance(data["dimensions"], dict):
            raise ConfigError("review_taxonomy.yml must define a 'dimensions' mapping.")

        dimensions = data["dimensions"]
        if "sip_lifecycle_stages" not in dimensions:
            raise ConfigError("Taxonomy missing required dimension 'sip_lifecycle_stages'.")

        required_stages = {
            "S0_DISCOVERY", "S1_SETUP", "S2_EARLY", "S3_HABIT",
            "S4_REVIEW", "S5_FRICTION", "S6_PAUSE_STOP", "S7_RESTART"
        }
        actual_stages = set(dimensions["sip_lifecycle_stages"].get("allowed_labels", []))
        if not required_stages.issubset(actual_stages):
            raise ConfigError(f"Taxonomy missing required lifecycle stages: {required_stages - actual_stages}")

# Singleton accessor
_config_loader = None

def get_config_loader(config_dir: str = None) -> ConfigLoader:
    """Returns singleton ConfigLoader instance."""
    global _config_loader
    if _config_loader is None or (config_dir and _config_loader.config_dir != config_dir):
        _config_loader = ConfigLoader(config_dir)
    return _config_loader
