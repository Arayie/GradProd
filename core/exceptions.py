"""
Core domain exceptions for Growww Investor Discovery Engine.
"""

class DiscoveryEngineError(Exception):
    """Base exception for all domain errors."""
    pass

class ConfigError(DiscoveryEngineError):
    """Raised when configuration files are missing, malformed, or contain invalid attributes."""
    pass

class ValidationError(DiscoveryEngineError):
    """Raised when data input fails schema, field, or format validation."""
    pass

class DatabaseError(DiscoveryEngineError):
    """Raised when database operations encounter errors or constraint violations."""
    pass

class DuplicateRecordError(DatabaseError):
    """Raised when an attempt is made to re-import an existing review."""
    pass

class SecurityViolationError(DiscoveryEngineError):
    """Raised when PII, unredacted names, or unauthorized sources are detected."""
    pass

class SourcePermissionError(DiscoveryEngineError):
    """Raised when a data source or route lacks required permission approval."""
    pass
