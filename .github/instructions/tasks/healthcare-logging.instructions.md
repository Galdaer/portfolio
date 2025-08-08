`````instructions
````instructions
# Healthcare AI Logging Instructions

## Purpose

Comprehensive PHI-safe logging and monitoring implementation for healthcare AI systems with HIPAA compliance patterns.

## Healthcare Logging Patterns

### PHI-Safe Logging Implementation
```python
# ✅ CORRECT: PHI scrubbing pattern
import re
import logging
from typing import Any, Dict

class HealthcareLogger:
    PHI_PATTERNS = {
        'ssn': re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b'),
        'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
        'mrn': re.compile(r'\bMRN[-:]?\s*\d+\b', re.IGNORECASE),
        'dob': re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b')
    }
    
    def scrub_phi(self, message: str) -> str:
        """Remove PHI from log messages"""
        for phi_type, pattern in self.PHI_PATTERNS.items():
            message = pattern.sub(f'[REDACTED_{phi_type.upper()}]', message)
        return message
    
    def log_clinical_action(self, user_id: str, action: str, patient_id: str = None):
        """Log clinical actions with PHI protection"""
        safe_message = self.scrub_phi(f"User {user_id} performed {action}")
        if patient_id:
            safe_message += f" for patient {patient_id[:4]}***"
        
        logging.info(safe_message, extra={
            'event_type': 'clinical_action',
            'user_id': user_id,
            'timestamp': datetime.utcnow(),
            'compliance_flag': 'hipaa_audit'
        })
```

### Audit Trail Implementation
```python
# ✅ CORRECT: HIPAA-compliant audit logging
class AuditLogger:
    def log_data_access(self, 
                       user_id: str, 
                       resource: str, 
                       action: str,
                       ip_address: str,
                       success: bool = True):
        """Log all healthcare data access for compliance"""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'resource_type': resource,
            'action': action,
            'ip_address': ip_address,
            'success': success,
            'session_id': self.get_session_id(),
            'compliance': 'hipaa_required'
        }
        
        # Use structured logging for audit trails
        logging.info("Data access event", extra=audit_entry)
```

### Performance Monitoring with PHI Protection
```python
# ✅ CORRECT: Monitor healthcare system performance safely
import psutil
import asyncio
from datetime import datetime

class HealthcareSystemMonitor:
    async def log_performance_metrics(self):
        """Monitor system performance without exposing PHI"""
        metrics = {
            'timestamp': datetime.utcnow(),
            'memory_usage_mb': psutil.virtual_memory().used / 1024 / 1024,
            'cpu_percent': psutil.cpu_percent(),
            'active_sessions': await self.count_active_sessions(),
            'database_connections': await self.count_db_connections(),
            'queue_size': await self.get_task_queue_size()
        }
        
        # Log performance without any patient context
        logging.info("System performance", extra=metrics)
        
        # Alert on concerning metrics
        if metrics['memory_usage_mb'] > 8000:  # 8GB
            logging.warning("High memory usage detected", extra={
                'alert_type': 'resource_exhaustion',
                'memory_mb': metrics['memory_usage_mb']
            })
```

### Error Handling with Healthcare Context
```python
# ✅ CORRECT: Healthcare-safe error logging
class HealthcareErrorHandler:
    def log_medical_data_error(self, 
                             error: Exception, 
                             context: Dict[str, Any],
                             user_id: str = None):
        """Log errors while protecting PHI"""
        # Scrub any potential PHI from error messages
        safe_error_msg = self.scrub_phi(str(error))
        
        # Create safe context (no patient data)
        safe_context = {
            'operation': context.get('operation', 'unknown'),
            'module': context.get('module', 'unknown'),
            'error_type': type(error).__name__,
            'timestamp': datetime.utcnow(),
            'user_id': user_id
        }
        
        logging.error(f"Healthcare operation failed: {safe_error_msg}", 
                     extra=safe_context, exc_info=True)
```

### Database Operation Logging
```python
# ✅ CORRECT: Database access logging with PHI protection  
class DatabaseAuditLogger:
    def log_query_execution(self, 
                          query_type: str,
                          table: str, 
                          user_id: str,
                          execution_time: float,
                          row_count: int = None):
        """Log database operations for audit compliance"""
        log_entry = {
            'event_type': 'database_access',
            'query_type': query_type,  # SELECT, INSERT, UPDATE, DELETE
            'table_name': table,
            'user_id': user_id,
            'execution_time_ms': execution_time * 1000,
            'affected_rows': row_count,
            'timestamp': datetime.utcnow(),
            'compliance_required': table in ['patients', 'encounters', 'lab_results']
        }
        
        logging.info("Database operation", extra=log_entry)
```

### Multi-Agent Coordination Logging
```python
# ✅ CORRECT: Agent interaction logging for healthcare workflows
class AgentCoordinationLogger:
    def log_agent_handoff(self, 
                         from_agent: str,
                         to_agent: str, 
                         task_type: str,
                         session_id: str):
        """Log agent-to-agent task handoffs"""
        handoff_log = {
            'event_type': 'agent_handoff',
            'from_agent': from_agent,
            'to_agent': to_agent,
            'task_type': task_type,
            'session_id': session_id,
            'timestamp': datetime.utcnow(),
            'workflow_stage': self.get_workflow_stage(task_type)
        }
        
        logging.info("Agent coordination event", extra=handoff_log)
```

## Security & Compliance Requirements

### Log Security Patterns
- **Encryption at rest**: Encrypt log files using healthcare-grade encryption
- **Access control**: Limit log access to authorized healthcare personnel only
- **Network security**: Use TLS for log transmission to external systems
- **Retention policies**: Implement healthcare-compliant log retention (typically 7 years)

### Performance Considerations  
- **Async logging**: Use asyncio-compatible logging to avoid blocking healthcare operations
- **Log rotation**: Implement size and time-based rotation to manage storage
- **Sampling**: For high-volume operations, use intelligent sampling to reduce log volume
- **Buffering**: Buffer logs for batch writing to improve performance

### Common Healthcare Logging Errors to Avoid

**❌ PHI in Log Messages**:
```python
# Wrong - exposes patient data
logging.info(f"Patient John Doe (SSN: 123-45-6789) checked in")

# ✅ Correct - PHI protected
logging.info(f"Patient {patient_id[:4]}*** checked in", extra={
    'event': 'patient_checkin',
    'patient_ref': patient_id
})
```

**❌ Missing Audit Context**:
```python
# Wrong - no audit trail
logging.info("Updated patient record")

# ✅ Correct - complete audit trail
logging.info("Updated patient record", extra={
    'user_id': user_id,
    'patient_ref': patient_id, 
    'fields_modified': ['insurance', 'contact'],
    'timestamp': datetime.utcnow(),
    'audit_required': True
})
```
````
`````
- **Monitoring**: Alert on unusual patterns or security-relevant events
- **Compliance reporting**: Generate reports for HIPAA and regulatory audits
````
