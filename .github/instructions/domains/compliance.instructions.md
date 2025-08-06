# Healthcare Compliance Instructions

## Purpose

HIPAA, GDPR, FDA guidelines, and regulatory requirements with audit trail management for healthcare AI systems.

## HIPAA Compliance Framework

### 1. Administrative Safeguards

```python
# ✅ CORRECT: HIPAA Administrative Safeguards Implementation
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class HIPAARole(Enum):
    SECURITY_OFFICER = "security_officer"
    PRIVACY_OFFICER = "privacy_officer"  
    WORKFORCE_MEMBER = "workforce_member"

@dataclass
class HIPAAWorkforceTraining:
    employee_id: str
    training_type: str
    completion_date: datetime
    next_due_date: datetime

class HIPAAAdministrativeSafeguards:
    def assign_security_responsibility(self, officer_id: str):
        # Assign HIPAA security officer with documented responsibilities
        pass
    
    def conduct_workforce_training(self, employee_id: str):
        # Mandatory HIPAA training for all workforce members
        pass
    
    def manage_access_authorization(self, user_id: str, access_level: str):
        # Role-based access control with minimum necessary principle
        pass
```

### 2. Physical Safeguards

```python
# ✅ CORRECT: HIPAA Physical Safeguards for Healthcare AI
class HIPAAPhysicalSafeguards:
    def control_facility_access(self, location: str):
        # Physical security controls for servers and workstations
        pass
    
    def secure_workstation_use(self, workstation_id: str):
        # Workstation access controls and monitoring
        pass
    
    def control_device_media(self, media_id: str):
        # Secure handling of storage media containing PHI
        pass
```

### 3. Technical Safeguards

```python
# ✅ CORRECT: HIPAA Technical Safeguards Implementation
class HIPAATechnicalSafeguards:
    def implement_access_control(self, user_id: str):
        # Unique user identification, emergency procedures, automatic logoff
        pass
    
    def enable_audit_controls(self, system_activity: Dict[str, Any]):
        # Comprehensive audit logging of PHI access and modifications
        pass
    
    def ensure_data_integrity(self, phi_data: str):
        # Protect PHI from unauthorized alteration or destruction
        pass
    
    def implement_transmission_security(self, data: str):
        # End-to-end encryption for PHI transmission
        pass
```

## GDPR Compliance (for International Healthcare)

### 1. Data Subject Rights

```python
# ✅ CORRECT: GDPR Data Subject Rights Implementation
class GDPRDataSubjectRights:
    def handle_access_request(self, data_subject_id: str):
        # Right to access personal data
        pass
    
    def handle_rectification_request(self, data_subject_id: str, corrections: Dict):
        # Right to correct inaccurate personal data
        pass
    
    def handle_erasure_request(self, data_subject_id: str):
        # Right to erasure ("right to be forgotten")
        pass
```

### 2. Data Protection Impact Assessment (DPIA)

```python
# ✅ CORRECT: GDPR DPIA Implementation for Healthcare AI
class GDPRDataProtectionImpactAssessment:
    def conduct_dpia(self, processing_activity: str):
        # Assess high-risk data processing activities
        pass
    
    def document_privacy_measures(self, measures: List[str]):
        # Document privacy by design and default measures
        pass
```

## FDA Compliance (for AI/ML Medical Devices)

### 1. Software as Medical Device (SaMD) Classification

```python
# ✅ CORRECT: FDA SaMD Classification and Quality Management
class FDASaMDCompliance:
    def classify_samd_risk(self, software_function: str):
        # Classify AI software based on healthcare situation and state
        pass
    
    def implement_quality_management(self):
        # ISO 13485 quality management system for medical devices
        pass
```

## Audit Trail and Compliance Monitoring

### 1. Comprehensive Audit System

```python
# ✅ CORRECT: Healthcare Compliance Audit System
class HealthcareComplianceAuditSystem:
    def log_phi_access(self, user_id: str, patient_id: str, access_type: str):
        # Log all PHI access with user, patient, timestamp, purpose
        pass
    
    def generate_compliance_report(self, start_date: datetime, end_date: datetime):
        # Generate audit reports for HIPAA compliance officers
        pass
    
    def monitor_unauthorized_access(self):
        # Real-time monitoring for suspicious access patterns
        pass
```

### 2. Automated Compliance Monitoring

```python
class AutomatedComplianceMonitor:
    def scan_for_compliance_violations(self):
        # Automated scanning for HIPAA/GDPR violations
        pass
    
    def enforce_data_retention_policies(self):
        # Automated enforcement of 7-year HIPAA retention requirements
        pass
```

## Implementation Guidelines

### Compliance Best Practices

- **HIPAA Requirements**: Administrative, Physical, and Technical safeguards
- **Audit Logging**: Comprehensive logging of all PHI access and modifications
- **Access Controls**: Role-based access with minimum necessary principle
- **Data Encryption**: Encrypt PHI at rest and in transit
- **Regular Training**: Mandatory HIPAA training for all workforce members
- **Incident Response**: Documented procedures for security incidents

---
