"""
Security Exceptions for Healthcare Systems
Custom exception classes for healthcare security operations
"""


class SecurityError(Exception):
    """Security-related errors in healthcare encryption and authentication"""

    pass


class EncryptionError(SecurityError):
    """Encryption-specific security errors"""

    pass


class AuthenticationError(SecurityError):
    """Authentication-specific security errors"""

    pass


class AuthorizationError(SecurityError):
    """Authorization-specific security errors"""

    pass


class PHISecurityError(SecurityError):
    """PHI-related security errors for HIPAA compliance"""

    pass


class ConfigurationSecurityError(SecurityError):
    """Security configuration errors"""

    pass
