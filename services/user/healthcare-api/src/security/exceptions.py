"""
Security Exceptions for Healthcare Systems
Custom exception classes for healthcare security operations
"""


class SecurityError(Exception):
    """Security-related errors in healthcare encryption and authentication"""


class EncryptionError(SecurityError):
    """Encryption-specific security errors"""


class AuthenticationError(SecurityError):
    """Authentication-specific security errors"""


class AuthorizationError(SecurityError):
    """Authorization-specific security errors"""


class PHISecurityError(SecurityError):
    """PHI-related security errors for HIPAA compliance"""


class ConfigurationSecurityError(SecurityError):
    """Security configuration errors"""
