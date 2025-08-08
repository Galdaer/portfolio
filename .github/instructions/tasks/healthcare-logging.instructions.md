````instructions
# Healthcare AI Logging Instructions

## Purpose

Guidance for implementing healthcare-compliant logging with PHI protection and HIPAA compliance.

## Healthcare Logging Principles

### PHI Protection in Logs
- **Never log real patient data**: Use patient IDs, redacted values, or synthetic data
- **Automatic PHI scrubbing**: Implement patterns to detect and redact SSN, phone numbers, MRNs
- **Secure log storage**: Encrypt log files and restrict access to authorized personnel
- **Log retention**: Follow healthcare regulations for log data retention periods

### Compliance Logging Requirements
- **Audit trails**: Log all data access, modifications, and administrative actions
- **User attribution**: Include user ID and role in all logged actions
- **Timestamp precision**: Use consistent timezone and high-precision timestamps
- **Action tracking**: Log what was accessed, when, by whom, and from where

### Healthcare Log Categories
- **Clinical operations**: Patient encounters, diagnosis entry, treatment plans
- **Administrative**: Billing, insurance verification, appointment scheduling
- **Security events**: Login attempts, permission changes, data exports
- **System events**: Service starts/stops, configuration changes, errors

### Performance and Security
- **Async logging**: Use non-blocking logging to maintain system responsiveness
- **Log rotation**: Implement size and time-based log rotation
- **Monitoring**: Alert on unusual patterns or security-relevant events
- **Compliance reporting**: Generate reports for HIPAA and regulatory audits
````
