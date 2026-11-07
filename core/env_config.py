"""
Environment Secrets and Runtime Configuration Manager (Phase 8)
Validates required environment variables, enforces fail-fast integrity, and masks secrets in logs.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("growww.config")

# Recognized environment names
VALID_ENVIRONMENTS = {"development", "testing", "production", "staging"}
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

class ConfigurationError(Exception):
    """Raised when critical environment variables or secrets fail validation."""
    pass

class EnvironmentConfig:
    """Central configuration container with startup validation and secret masking."""

    def __init__(self):
        self.app_env: str = os.getenv("APP_ENV", "production").lower()
        self.app_host: str = os.getenv("APP_HOST", "0.0.0.0")
        self.app_port: int = int(os.getenv("APP_PORT", "8501"))
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///growww_discovery.db")
        self.require_auth: bool = os.getenv("REQUIRE_AUTH", "true").lower() in ("true", "1", "yes")
        self.auth_session_timeout_minutes: int = int(os.getenv("AUTH_SESSION_TIMEOUT_MINUTES", "120"))
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_file: str = os.getenv("LOG_FILE", "logs/production.log")
        self.scheduled_refresh_enabled: bool = os.getenv("SCHEDULED_REFRESH_ENABLED", "false").lower() in ("true", "1", "yes")
        self.schedule_cron: str = os.getenv("SCHEDULE_CRON", "0 0 * * 0")
        self.enable_demo_mode: bool = os.getenv("ENABLE_DEMO_MODE", "false").lower() in ("true", "1", "yes")

        # User Credentials / Password Hashes
        self.admin_password_hash: str = os.getenv("ADMIN_PASSWORD_HASH", "")
        self.researcher_password_hash: str = os.getenv("RESEARCHER_PASSWORD_HASH", "")
        self.viewer_password_hash: str = os.getenv("VIEWER_PASSWORD_HASH", "")
        self.auditor_password_hash: str = os.getenv("AUDITOR_PASSWORD_HASH", "")

        self.validate()

    def validate(self):
        """Validates configuration sanity and raises ConfigurationError if invalid."""
        if self.app_env not in VALID_ENVIRONMENTS:
            raise ConfigurationError(
                f"Invalid APP_ENV '{self.app_env}'. Must be one of: {', '.join(VALID_ENVIRONMENTS)}"
            )

        if self.log_level not in VALID_LOG_LEVELS:
            raise ConfigurationError(
                f"Invalid LOG_LEVEL '{self.log_level}'. Must be one of: {', '.join(VALID_LOG_LEVELS)}"
            )

        if not self.database_url:
            raise ConfigurationError("DATABASE_URL cannot be empty.")

        # Ensure directories exist
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

    def mask_secret(self, val: str) -> str:
        """Returns masked version of secret strings for logging."""
        if not val:
            return "[NOT SET]"
        if len(val) <= 6:
            return "******"
        return f"{val[:2]}****{val[-2:]}"

    def get_sanitized_summary(self) -> Dict[str, Any]:
        """Returns safe dictionary suitable for logging and health checks."""
        return {
            "app_env": self.app_env,
            "app_host": self.app_host,
            "app_port": self.app_port,
            "database_url": self.database_url.split("@")[-1] if "@" in self.database_url else self.database_url,
            "require_auth": self.require_auth,
            "session_timeout_mins": self.auth_session_timeout_minutes,
            "scheduled_refresh_enabled": self.scheduled_refresh_enabled,
            "demo_mode": self.enable_demo_mode,
            "log_level": self.log_level,
            "gemini_api_key_configured": bool(self.gemini_api_key),
            "admin_configured": bool(self.admin_password_hash or os.getenv("ADMIN_PASSWORD")),
            "researcher_configured": bool(self.researcher_password_hash or os.getenv("RESEARCHER_PASSWORD")),
        }

_config_instance: Optional[EnvironmentConfig] = None

def get_env_config() -> EnvironmentConfig:
    """Singleton getter for EnvironmentConfig."""
    global _config_instance
    if _config_instance is None:
        _config_instance = EnvironmentConfig()
    return _config_instance
