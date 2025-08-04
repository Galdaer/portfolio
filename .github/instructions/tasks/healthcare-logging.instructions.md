# Healthcare AI Logging Instructions

## Purpose

Comprehensive guidance for implementing healthcare-compliant logging across all Intelluxe AI healthcare systems with PHI protection and HIPAA compliance.

## Healthcare Logging Architecture

### Core Logging Infrastructure

```python
# ✅ CORRECT: Healthcare logging configuration
# File: core/infrastructure/healthcare_logger.py

import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional
import re
from datetime import datetime

class HealthcareLogFormatter(logging.Formatter):
    """Healthcare-specific log formatter with PHI scrubbing."""
    
    PHI_PATTERNS = [
        (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]'),      # SSN
        (r'\b\d{3}-\d{3}-\d{4}\b', '[PHONE_REDACTED]'),    # Phone
        (r'\b[A-Z]{2}\d{6,10}\b', '[MRN_REDACTED]'),       # Medical Record Numbers
        (r'patient_id["\']?\s*:\s*["\']?[^,}\]]+', 'patient_id: [PATIENT_ID_REDACTED]'),
        (r'insurance_id["\']?\s*:\s*["\']?[^,}\]]+', 'insurance_id: [INSURANCE_ID_REDACTED]'),
    ]
    
    def format(self, record):
        # Format the message first
        formatted = super().format(record)
        
        # Scrub any potential PHI
        for pattern, replacement in self.PHI_PATTERNS:
            formatted = re.sub(pattern, replacement, formatted, flags=re.IGNORECASE)
        
        return formatted

def setup_healthcare_logging(log_dir: Path = Path("logs")) -> None:
    """Setup healthcare-compliant logging infrastructure."""
    
    # Ensure log directory exists
    log_dir.mkdir(exist_ok=True)
    
    # Custom log levels for healthcare
    logging.addLevelName(25, 'PHI_ALERT')
    logging.addLevelName(35, 'MEDICAL_ERROR') 
    logging.addLevelName(33, 'COMPLIANCE_WARNING')
    
    # Healthcare root logger
    healthcare_logger = logging.getLogger('healthcare')
    healthcare_logger.setLevel(logging.INFO)
    
    # File handler with rotation for HIPAA retention compliance
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'healthcare_system.log',
        maxBytes=50*1024*1024,  # 50MB
        backupCount=10,         # Keep 10 files for audit trail
        encoding='utf-8'
    )
    
    # Healthcare-specific formatter
    formatter = HealthcareLogFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Console handler for development (with PHI scrubbing)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)  # Only warnings+ to console
    
    healthcare_logger.addHandler(file_handler)
    healthcare_logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    healthcare_logger.propagate = False

# ✅ CORRECT: PHI monitoring utilities
class PHIMonitor:
    """Real-time PHI detection and monitoring for healthcare compliance."""
    
    PHI_INDICATORS = [
        'ssn', 'social security', 'social_security_number',
        'insurance_id', 'insurance_number', 'policy_number',
        'patient_id', 'medical_record_number', 'mrn',
        'birth_date', 'date_of_birth', 'dob',
        'phone_number', 'telephone', 'cell_phone',
        'home_address', 'mailing_address', 'street_address'
    ]
    
    @classmethod
    def scan_for_phi(cls, data: Any) -> bool:
        """Scan any data structure for potential PHI indicators."""
        data_str = str(data).lower()
        
        # Check for PHI field names
        for indicator in cls.PHI_INDICATORS:
            if indicator in data_str:
                return True
        
        # Check for PHI patterns (SSN, phone, etc.)
        import re
        phi_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN format
            r'\b\d{3}-\d{3}-\d{4}\b',  # Phone format
            r'\b\d{2}/\d{2}/\d{4}\b',  # Date format (potential DOB)
        ]
        
        for pattern in phi_patterns:
            if re.search(pattern, data_str):
                return True
        
        return False
    
    @classmethod
    def log_phi_detection(cls, context: str, data_summary: str) -> None:
        """Log PHI detection with healthcare compliance context."""
        logger = logging.getLogger('healthcare.phi_monitor')
        logger.log(25, f"PHI detected in {context}", extra={
            'healthcare_context': {
                'phi_detection': True,
                'context': context,
                'data_summary': data_summary[:100],  # Limited summary
                'requires_review': True,
                'timestamp': datetime.now().isoformat()
            }
        })
```

### Healthcare Method Logging Decorators

```python
# ✅ CORRECT: Healthcare method logging decorator
# File: core/infrastructure/logging_decorators.py

import functools
import logging
import time
from typing import Any, Callable
from .phi_monitor import PHIMonitor

def healthcare_log_method(
    operation_type: str = "healthcare_operation",
    phi_risk_level: str = "medium"
):
    """Decorator for comprehensive healthcare method logging."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(f'healthcare.{func.__module__}')
            method_name = f"{func.__qualname__}"
            
            # Entry logging
            start_time = time.time()
            logger.info(f"Healthcare method entry: {method_name}", extra={
                'healthcare_context': {
                    'method': method_name,
                    'operation_type': operation_type,
                    'phi_risk_level': phi_risk_level,
                    'args_count': len(args),
                    'kwargs_count': len(kwargs)
                }
            })
            
            # PHI detection on inputs
            all_inputs = {'args': args, 'kwargs': kwargs}
            if PHIMonitor.scan_for_phi(all_inputs):
                PHIMonitor.log_phi_detection(
                    context=f"method_input_{method_name}",
                    data_summary=f"Method {method_name} received potential PHI"
                )
            
            try:
                # Execute method
                result = func(*args, **kwargs)
                
                # PHI detection on outputs
                if PHIMonitor.scan_for_phi(result):
                    PHIMonitor.log_phi_detection(
                        context=f"method_output_{method_name}",
                        data_summary=f"Method {method_name} returned potential PHI"
                    )
                
                # Success logging
                execution_time = time.time() - start_time
                logger.info(f"Healthcare method success: {method_name}", extra={
                    'healthcare_context': {
                        'method': method_name,
                        'execution_time_ms': round(execution_time * 1000, 2),
                        'success': True
                    }
                })
                
                return result
                
            except Exception as e:
                # Error logging with healthcare context
                execution_time = time.time() - start_time
                logger.log(35, f"Healthcare method error: {method_name}: {str(e)}", extra={
                    'healthcare_context': {
                        'method': method_name,
                        'error_type': type(e).__name__,
                        'error_message': str(e)[:200],  # Truncated for safety
                        'execution_time_ms': round(execution_time * 1000, 2),
                        'success': False
                    }
                })
                raise
                
        return wrapper
    return decorator

# ✅ CORRECT: Healthcare agent logging decorator
def healthcare_agent_log(agent_name: str):
    """Specialized logging decorator for healthcare agents."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(f'healthcare.agent.{agent_name}')
            
            # Agent-specific logging
            logger.info(f"Agent {agent_name} processing: {func.__name__}", extra={
                'healthcare_context': {
                    'agent': agent_name,
                    'operation': func.__name__,
                    'agent_version': '1.0',  # Could be dynamic
                    'processing_start': time.time()
                }
            })
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

### Healthcare Integration Patterns

```python
# ✅ CORRECT: Healthcare system integration logging
# Example: agents/intake/intake_agent.py

from core.infrastructure.logging_decorators import healthcare_log_method, healthcare_agent_log
from core.infrastructure.phi_monitor import PHIMonitor
import logging

class IntakeAgent:
    """Patient intake agent with comprehensive healthcare logging."""
    
    def __init__(self):
        self.logger = logging.getLogger('healthcare.agent.intake')
        self.logger.info("Intake agent initialized", extra={
            'healthcare_context': {
                'agent': 'intake',
                'initialization': True,
                'phi_monitoring': True
            }
        })
    
    @healthcare_log_method(operation_type="patient_intake", phi_risk_level="high")
    @healthcare_agent_log("intake")
    def process_patient_checkin(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process patient check-in with comprehensive logging and PHI monitoring."""
        
        # Validate required fields for healthcare compliance
        required_fields = ['patient_id', 'appointment_time', 'insurance_info']
        missing_fields = [field for field in required_fields if field not in patient_data]
        
        if missing_fields:
            self.logger.log(33, f"Missing required patient data fields: {missing_fields}")
        
        # Process intake (implementation details...)
        processed_data = self._process_intake_data(patient_data)
        
        # Log successful processing
        self.logger.info("Patient intake completed successfully", extra={
            'healthcare_context': {
                'operation_completed': 'patient_intake',
                'data_fields_processed': len(processed_data),
                'compliance_verified': True
            }
        })
        
        return processed_data
    
    def _process_intake_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Internal processing with PHI protection."""
        # Implementation with PHI-safe processing
        return data
```

## Implementation Checklist

### Phase 1: Core Infrastructure
- [ ] Create `core/infrastructure/healthcare_logger.py`
- [ ] Create `core/infrastructure/phi_monitor.py` 
- [ ] Create `core/infrastructure/logging_decorators.py`
- [ ] Update `main.py` with healthcare logging initialization

### Phase 2: Agent Integration
- [ ] Update `agents/intake/` with comprehensive logging
- [ ] Update `agents/document_processor/` with logging
- [ ] Update `agents/research_assistant/` with logging
- [ ] Verify PHI monitoring across all agents

### Phase 3: Core System Integration  
- [ ] Update `core/medical/` modules with logging
- [ ] Update `core/orchestration/` with workflow logging
- [ ] Update `core/reasoning/` with AI decision logging
- [ ] Update `core/infrastructure/` background services

### Phase 4: Testing & Validation
- [ ] Test PHI detection accuracy with synthetic data
- [ ] Validate log rotation and retention policies
- [ ] Performance testing (ensure <5% overhead)
- [ ] HIPAA compliance validation
- [ ] Integration testing across all components

## Critical Healthcare Compliance Notes

1. **PHI Protection**: All logs are automatically scrubbed of PHI
2. **Audit Trails**: Every healthcare operation is logged for compliance
3. **Real-time Monitoring**: PHI detection alerts in real-time
4. **Retention Policy**: Logs retained according to HIPAA requirements
5. **Access Control**: Healthcare logs require special access permissions

## Performance Considerations

- Log file rotation prevents disk space issues
- PHI detection optimized for minimal performance impact
- Structured logging enables efficient log analysis
- Background log processing for high-throughput scenarios

This comprehensive logging infrastructure ensures HIPAA compliance while providing the visibility needed for healthcare AI system monitoring and debugging.
