# AI Instructions for Core Infrastructure Development

## Purpose

**DATABASE-FIRST INFRASTRUCTURE**: All core infrastructure must require database connectivity and fail gracefully when unavailable.

Specialized guidance for developing core healthcare AI infrastructure components including authentication, caching, monitoring, logging, and PHI protection systems.

## CRITICAL: Database-First Infrastructure Requirements

**All core infrastructure components** must:
- Require database connectivity at startup
- Fail gracefully with clear error messages when database unavailable  
- Provide database setup guidance in error messages
- Log database connection attempts for audit compliance

**✅ CORRECT: Database-First Infrastructure Pattern**
```python
# core/infrastructure/healthcare_service_base.py
from abc import ABC, abstractmethod
from typing import Optional
import logging
from core.dependencies import get_database_connection

class HealthcareInfrastructureBase(ABC):
    """Base class for all core infrastructure services"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(f'healthcare.{service_name}')
        self.db_connection = None
        
    async def initialize(self) -> bool:
        """Initialize infrastructure service with database requirement"""
        try:
            self.db_connection = await get_database_connection()
            await self.validate_database_connectivity()
            
            self.logger.info(f"{self.service_name} infrastructure initialized successfully")
            return True
            
        except DatabaseConnectionError as e:
            self.logger.critical(
                f"{self.service_name} requires database connectivity",
                extra={
                    'error': str(e),
                    'service': self.service_name,
                    'remedy': 'Ensure PostgreSQL is running and accessible'
                }
            )
            raise HealthcareInfrastructureError(
                f"{self.service_name} cannot start without database connection. "
                f"Please run 'make deps' and ensure PostgreSQL is running."
            )
```

## Infrastructure Development Patterns

### Healthcare Logger Development
```python
# When working on healthcare_logger.py
from typing import Dict, Any, Optional
import logging
import structlog
from datetime import datetime

# ✅ CORRECT: Healthcare-specific logging enhancement
def enhance_healthcare_logging():
    """Add healthcare-specific logging capabilities."""
    
    # Ensure PHI-safe log formatting
    def phi_safe_processor(logger, method_name, event_dict):
        # Automatically scan and redact potential PHI
        return sanitize_log_event(event_dict)
    
    # Configure healthcare logging pipeline
    structlog.configure(
        processors=[
            phi_safe_processor,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer()
        ]
    )
```

### PHI Monitor Development
```python
# When working on phi_monitor.py
import re
from typing import List, Set, Any

# ✅ CORRECT: PHI detection patterns
PHI_PATTERNS = {
    'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    'phone': re.compile(r'\b\d{3}-\d{3}-\d{4}\b'),
    'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    'mrn': re.compile(r'\bMRN[:\s]*\d+\b', re.IGNORECASE),
    'dob': re.compile(r'\b\d{1,2}/\d{1,2}/\d{4}\b')
}

def scan_for_phi(data: Any) -> List[str]:
    """Scan data for potential PHI patterns."""
    found_patterns = []
    text = str(data)
    
    for pattern_name, pattern in PHI_PATTERNS.items():
        if pattern.search(text):
            found_patterns.append(pattern_name)
    
    return found_patterns
```

### Authentication Infrastructure
```python
# When working on authentication.py
from core.infrastructure.healthcare_logger import get_healthcare_logger
from core.infrastructure.phi_monitor import phi_monitor

logger = get_healthcare_logger('core.auth')

# ✅ CORRECT: Healthcare-aware authentication
@phi_monitor
def authenticate_healthcare_user(credentials: Dict[str, str]) -> Optional[User]:
    """Authenticate healthcare users with audit logging."""
    
    # Log authentication attempt (without credentials)
    log_healthcare_event('auth.attempt', {
        'username': credentials.get('username'),
        'timestamp': datetime.utcnow(),
        'source_ip': get_client_ip()
    })
    
    # Authenticate user
    user = verify_credentials(credentials)
    
    if user:
        log_healthcare_event('auth.success', {
            'user_id': user.id,
            'role': user.role,
            'permissions': user.permissions
        })
    else:
        log_healthcare_event('auth.failure', {
            'username': credentials.get('username'),
            'reason': 'invalid_credentials'
        })
    
    return user
```

## Configuration Management
```python
# When working on config_manager.py
def load_healthcare_config():
    """Load healthcare-specific configuration with security validation."""
    
    config = load_base_config()
    
    # Validate required healthcare settings
    required_settings = [
        'HEALTHCARE_AUDIT_ENABLED',
        'PHI_MONITORING_ENABLED', 
        'HIPAA_COMPLIANCE_MODE',
        'HEALTHCARE_LOG_RETENTION_DAYS'
    ]
    
    for setting in required_settings:
        if setting not in config:
            raise ConfigurationError(f"Required healthcare setting missing: {setting}")
    
    return config
```

## Cache Development
```python
# When working on healthcare_cache.py
def create_phi_safe_cache_key(data: Dict[str, Any]) -> str:
    """Create cache keys that don't contain PHI."""
    
    # Remove or hash any fields that might contain PHI
    safe_data = {}
    for key, value in data.items():
        if key in ['ssn', 'mrn', 'email', 'phone', 'dob']:
            # Hash PHI fields for cache keys
            safe_data[key] = hash_for_cache(value)
        else:
            safe_data[key] = value
    
    return generate_cache_key(safe_data)
```

## Testing Infrastructure Components
- Use synthetic data for all tests
- Mock external healthcare services
- Validate PHI protection in all scenarios
- Test audit logging functionality
- Verify proper error handling and cleanup
