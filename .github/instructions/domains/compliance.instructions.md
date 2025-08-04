# Healthcare Compliance Instructions

## Purpose

Comprehensive compliance patterns for healthcare AI systems, covering HIPAA, GDPR, FDA guidelines, and regulatory requirements with practical implementation guidance and audit trail management.

## HIPAA Compliance Framework

### 1. Administrative Safeguards

```python
# ✅ CORRECT: HIPAA Administrative Safeguards Implementation
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum

class HIPAARole(Enum):
    """HIPAA-compliant user roles with specific permissions"""
    SECURITY_OFFICER = "security_officer"
    PRIVACY_OFFICER = "privacy_officer" 
    COVERED_ENTITY_ADMIN = "covered_entity_admin"
    HEALTHCARE_PROVIDER = "healthcare_provider"
    BUSINESS_ASSOCIATE = "business_associate"
    WORKFORCE_MEMBER = "workforce_member"
    MINIMUM_NECESSARY_USER = "minimum_necessary_user"

@dataclass
class HIPAAWorkforceTraining:
    """HIPAA workforce training compliance tracking"""
    user_id: str
    training_type: str
    completion_date: datetime
    trainer_id: str
    certification_valid_until: datetime
    training_topics: List[str]
    quiz_score: Optional[int] = None
    remedial_training_required: bool = False

class HIPAAAdministrativeSafeguards:
    """Implementation of HIPAA Administrative Safeguards"""
    
    def __init__(self):
        self.logger = get_healthcare_logger('hipaa_admin_safeguards')
    
    async def assign_security_responsibilities(
        self, 
        user_id: str, 
        role: HIPAARole,
        assigned_by: str,
        justification: str
    ) -> Dict[str, Any]:
        """Assign HIPAA security responsibilities with audit trail"""
        
        assignment = {
            'user_id': user_id,
            'role': role.value,
            'assigned_by': assigned_by,
            'assignment_date': datetime.utcnow(),
            'justification': justification,
            'responsibilities': self._get_role_responsibilities(role)
        }
        
        # Log assignment
        self.logger.info(
            f"HIPAA role assigned: {role.value}",
            extra={
                'operation_type': 'hipaa_role_assignment',
                'user_id': user_id,
                'role': role.value,
                'assigned_by': assigned_by,
                'compliance_requirement': 'HIPAA_164.308(a)(2)'
            }
        )
        
        # Store in compliance database
        await self._store_role_assignment(assignment)
        
        return assignment
    
    def _get_role_responsibilities(self, role: HIPAARole) -> List[str]:
        """Get specific responsibilities for HIPAA roles"""
        responsibilities = {
            HIPAARole.SECURITY_OFFICER: [
                "Implement and maintain security policies",
                "Conduct security risk assessments",
                "Monitor security incidents and breaches",
                "Oversee workforce training on security",
                "Manage access controls and permissions"
            ],
            HIPAARole.PRIVACY_OFFICER: [
                "Develop privacy policies and procedures",
                "Handle privacy complaints and inquiries",
                "Conduct privacy training for workforce",
                "Monitor privacy compliance",
                "Manage patient rights requests"
            ],
            HIPAARole.HEALTHCARE_PROVIDER: [
                "Access PHI for treatment purposes only",
                "Follow minimum necessary standard",
                "Report privacy/security incidents",
                "Maintain patient confidentiality",
                "Complete required HIPAA training"
            ]
        }
        return responsibilities.get(role, [])

    async def conduct_workforce_training(
        self,
        user_id: str,
        training_type: str,
        trainer_id: str
    ) -> HIPAAWorkforceTraining:
        """Conduct and track HIPAA workforce training"""
        
        training_record = HIPAAWorkforceTraining(
            user_id=user_id,
            training_type=training_type,
            completion_date=datetime.utcnow(),
            trainer_id=trainer_id,
            certification_valid_until=datetime.utcnow() + timedelta(days=365),
            training_topics=self._get_training_topics(training_type)
        )
        
        # Log training completion
        self.logger.info(
            f"HIPAA training completed: {training_type}",
            extra={
                'operation_type': 'hipaa_training_completion',
                'user_id': user_id,
                'training_type': training_type,
                'trainer_id': trainer_id,
                'compliance_requirement': 'HIPAA_164.308(a)(5)'
            }
        )
        
        return training_record
```

### 2. Physical Safeguards

```python
# ✅ CORRECT: HIPAA Physical Safeguards for Healthcare AI
class HIPAAPhysicalSafeguards:
    """Implementation of HIPAA Physical Safeguards for AI systems"""
    
    def __init__(self):
        self.logger = get_healthcare_logger('hipaa_physical_safeguards')
    
    async def log_facility_access(
        self,
        user_id: str,
        facility_location: str,
        access_type: str,  # 'ENTRY', 'EXIT', 'ATTEMPTED'
        access_method: str,  # 'KEYCARD', 'BIOMETRIC', 'PIN'
        workstation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log physical facility access for HIPAA compliance"""
        
        access_log = {
            'log_id': str(uuid4()),
            'user_id': user_id,
            'facility_location': facility_location,
            'access_type': access_type,
            'access_method': access_method,
            'workstation_id': workstation_id,
            'timestamp': datetime.utcnow(),
            'ip_address': self._get_client_ip(),
            'compliance_requirement': 'HIPAA_164.310(a)(1)'
        }
        
        self.logger.info(
            f"Physical facility access: {access_type}",
            extra=access_log
        )
        
        # Check for suspicious access patterns
        await self._analyze_access_patterns(user_id, facility_location)
        
        return access_log
    
    async def implement_workstation_controls(
        self,
        workstation_id: str,
        security_controls: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Implement HIPAA workstation security controls"""
        
        required_controls = {
            'automatic_screen_lock': True,
            'lock_timeout_minutes': 5,
            'encryption_enabled': True,
            'antivirus_enabled': True,
            'firewall_enabled': True,
            'unauthorized_software_blocked': True,
            'usb_ports_disabled': True,
            'audit_logging_enabled': True
        }
        
        # Validate all required controls are present
        missing_controls = []
        for control, required_value in required_controls.items():
            if control not in security_controls:
                missing_controls.append(control)
            elif security_controls[control] != required_value:
                missing_controls.append(f"{control} (current: {security_controls[control]}, required: {required_value})")
        
        if missing_controls:
            raise HIPAAComplianceError(
                f"Workstation {workstation_id} missing required controls: {missing_controls}"
            )
        
        # Log workstation configuration
        self.logger.info(
            f"HIPAA workstation controls configured",
            extra={
                'operation_type': 'hipaa_workstation_config',
                'workstation_id': workstation_id,
                'controls_applied': list(security_controls.keys()),
                'compliance_requirement': 'HIPAA_164.310(b)'
            }
        )
        
        return {
            'workstation_id': workstation_id,
            'compliance_status': 'COMPLIANT',
            'controls_applied': security_controls,
            'last_updated': datetime.utcnow()
        }
```

### 3. Technical Safeguards

```python
# ✅ CORRECT: HIPAA Technical Safeguards Implementation
class HIPAATechnicalSafeguards:
    """Implementation of HIPAA Technical Safeguards"""
    
    def __init__(self):
        self.logger = get_healthcare_logger('hipaa_technical_safeguards')
    
    async def implement_access_controls(
        self,
        user_id: str,
        requested_permissions: List[str],
        requesting_supervisor: str,
        business_justification: str
    ) -> Dict[str, Any]:
        """Implement HIPAA-compliant access controls"""
        
        # Apply minimum necessary standard
        approved_permissions = await self._apply_minimum_necessary_standard(
            user_id, requested_permissions, business_justification
        )
        
        # Create access control record
        access_control = {
            'user_id': user_id,
            'approved_permissions': approved_permissions,
            'denied_permissions': list(set(requested_permissions) - set(approved_permissions)),
            'requesting_supervisor': requesting_supervisor,
            'business_justification': business_justification,
            'approval_date': datetime.utcnow(),
            'review_required_by': datetime.utcnow() + timedelta(days=90),
            'compliance_requirement': 'HIPAA_164.312(a)(1)'
        }
        
        # Log access control decision
        self.logger.info(
            f"HIPAA access controls applied",
            extra={
                'operation_type': 'hipaa_access_control',
                'user_id': user_id,
                'approved_permissions': len(approved_permissions),
                'denied_permissions': len(access_control['denied_permissions']),
                'minimum_necessary_applied': True
            }
        )
        
        return access_control
    
    async def implement_audit_controls(
        self,
        system_component: str,
        audit_events: List[str]
    ) -> Dict[str, Any]:
        """Implement HIPAA audit controls and logging"""
        
        audit_configuration = {
            'system_component': system_component,
            'audit_events': audit_events,
            'log_retention_days': 2555,  # 7 years per HIPAA
            'log_format': 'structured_json',
            'real_time_monitoring': True,
            'automated_alerts': True,
            'compliance_requirement': 'HIPAA_164.312(b)'
        }
        
        # Configure audit logging
        await self._configure_audit_logging(audit_configuration)
        
        # Test audit system
        test_result = await self._test_audit_system(system_component)
        
        self.logger.info(
            f"HIPAA audit controls implemented",
            extra={
                'operation_type': 'hipaa_audit_controls',
                'system_component': system_component,
                'audit_events_count': len(audit_events),
                'test_passed': test_result['success']
            }
        )
        
        return {
            'configuration': audit_configuration,
            'test_result': test_result,
            'implementation_date': datetime.utcnow()
        }
    
    async def implement_integrity_controls(
        self,
        data_type: str,
        integrity_methods: List[str]
    ) -> Dict[str, Any]:
        """Implement data integrity controls for PHI"""
        
        integrity_config = {
            'data_type': data_type,
            'hash_algorithm': 'SHA-256',
            'digital_signatures': True,
            'version_control': True,
            'backup_integrity_checks': True,
            'real_time_validation': True,
            'compliance_requirement': 'HIPAA_164.312(c)(1)'
        }
        
        # Implement integrity checks
        for method in integrity_methods:
            await self._implement_integrity_method(data_type, method)
        
        self.logger.info(
            f"HIPAA data integrity controls implemented",
            extra={
                'operation_type': 'hipaa_integrity_controls',
                'data_type': data_type,
                'methods': integrity_methods
            }
        )
        
        return integrity_config
    
    async def implement_transmission_security(
        self,
        transmission_type: str,
        endpoints: List[str]
    ) -> Dict[str, Any]:
        """Implement secure transmission controls"""
        
        transmission_config = {
            'transmission_type': transmission_type,
            'encryption_standard': 'TLS 1.3',
            'endpoints': endpoints,
            'mutual_authentication': True,
            'certificate_validation': True,
            'perfect_forward_secrecy': True,
            'compliance_requirement': 'HIPAA_164.312(e)(1)'
        }
        
        # Validate all endpoints support required security
        for endpoint in endpoints:
            validation_result = await self._validate_endpoint_security(endpoint)
            if not validation_result['compliant']:
                raise HIPAAComplianceError(
                    f"Endpoint {endpoint} does not meet HIPAA transmission security requirements"
                )
        
        self.logger.info(
            f"HIPAA transmission security implemented",
            extra={
                'operation_type': 'hipaa_transmission_security',
                'transmission_type': transmission_type,
                'endpoints_count': len(endpoints)
            }
        )
        
        return transmission_config
```

## GDPR Compliance (for International Healthcare)

### 1. Data Subject Rights

```python
# ✅ CORRECT: GDPR Data Subject Rights Implementation
class GDPRDataSubjectRights:
    """Implementation of GDPR data subject rights for healthcare"""
    
    def __init__(self):
        self.logger = get_healthcare_logger('gdpr_compliance')
    
    async def handle_right_of_access(
        self,
        data_subject_id: str,
        requester_verification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle GDPR right of access requests"""
        
        # Verify identity of requester
        if not await self._verify_data_subject_identity(data_subject_id, requester_verification):
            raise GDPRComplianceError("Data subject identity verification failed")
        
        # Collect all personal data
        personal_data = await self._collect_all_personal_data(data_subject_id)
        
        # Prepare data export in machine-readable format
        data_export = {
            'data_subject_id': data_subject_id,
            'export_date': datetime.utcnow().isoformat(),
            'data_categories': {
                'identification_data': personal_data.get('identification', {}),
                'medical_data': personal_data.get('medical', {}),
                'contact_data': personal_data.get('contact', {}),
                'preference_data': personal_data.get('preferences', {})
            },
            'processing_purposes': await self._get_processing_purposes(data_subject_id),
            'third_parties': await self._get_third_party_sharing(data_subject_id),
            'retention_periods': await self._get_retention_periods(data_subject_id)
        }
        
        # Log access request
        self.logger.info(
            f"GDPR right of access fulfilled",
            extra={
                'operation_type': 'gdpr_right_of_access',
                'data_subject_id': data_subject_id,
                'data_categories_count': len(data_export['data_categories']),
                'compliance_requirement': 'GDPR_Article_15'
            }
        )
        
        return data_export
    
    async def handle_right_to_rectification(
        self,
        data_subject_id: str,
        correction_requests: List[Dict[str, Any]],
        requester_verification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle GDPR right to rectification"""
        
        # Verify identity
        if not await self._verify_data_subject_identity(data_subject_id, requester_verification):
            raise GDPRComplianceError("Data subject identity verification failed")
        
        rectification_results = []
        
        for correction in correction_requests:
            result = {
                'field': correction['field'],
                'old_value': '[REDACTED]',  # Don't log sensitive data
                'new_value': '[REDACTED]',
                'status': 'PENDING'
            }
            
            try:
                # Validate correction request
                if await self._validate_rectification_request(data_subject_id, correction):
                    # Apply correction with audit trail
                    await self._apply_data_correction(data_subject_id, correction)
                    result['status'] = 'COMPLETED'
                    result['completion_date'] = datetime.utcnow().isoformat()
                else:
                    result['status'] = 'REJECTED'
                    result['rejection_reason'] = 'Validation failed'
                    
            except Exception as e:
                result['status'] = 'ERROR'
                result['error_message'] = str(e)
            
            rectification_results.append(result)
        
        # Log rectification request
        self.logger.info(
            f"GDPR right to rectification processed",
            extra={
                'operation_type': 'gdpr_right_to_rectification',
                'data_subject_id': data_subject_id,
                'corrections_requested': len(correction_requests),
                'corrections_completed': len([r for r in rectification_results if r['status'] == 'COMPLETED']),
                'compliance_requirement': 'GDPR_Article_16'
            }
        )
        
        return {
            'data_subject_id': data_subject_id,
            'rectification_results': rectification_results,
            'processing_date': datetime.utcnow().isoformat()
        }
    
    async def handle_right_to_erasure(
        self,
        data_subject_id: str,
        erasure_grounds: str,
        requester_verification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle GDPR right to erasure (right to be forgotten)"""
        
        # Verify identity
        if not await self._verify_data_subject_identity(data_subject_id, requester_verification):
            raise GDPRComplianceError("Data subject identity verification failed")
        
        # Check if erasure is legally permissible
        erasure_assessment = await self._assess_erasure_request(data_subject_id, erasure_grounds)
        
        if not erasure_assessment['can_erase']:
            return {
                'data_subject_id': data_subject_id,
                'erasure_status': 'REJECTED',
                'rejection_reasons': erasure_assessment['rejection_reasons'],
                'legal_basis_for_retention': erasure_assessment['legal_basis']
            }
        
        # Perform erasure with audit trail
        erasure_results = await self._perform_data_erasure(data_subject_id)
        
        # Log erasure
        self.logger.info(
            f"GDPR right to erasure fulfilled",
            extra={
                'operation_type': 'gdpr_right_to_erasure',
                'data_subject_id': data_subject_id,
                'erasure_grounds': erasure_grounds,
                'records_erased': erasure_results['records_erased'],
                'compliance_requirement': 'GDPR_Article_17'
            }
        )
        
        return {
            'data_subject_id': data_subject_id,
            'erasure_status': 'COMPLETED',
            'erasure_results': erasure_results,
            'completion_date': datetime.utcnow().isoformat()
        }
```

### 2. Data Protection Impact Assessment (DPIA)

```python
# ✅ CORRECT: GDPR DPIA Implementation for Healthcare AI
class GDPRDataProtectionImpactAssessment:
    """GDPR Data Protection Impact Assessment for healthcare AI systems"""
    
    def __init__(self):
        self.logger = get_healthcare_logger('gdpr_dpia')
    
    async def conduct_dpia(
        self,
        processing_activity: str,
        ai_system_description: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Conduct comprehensive DPIA for healthcare AI processing"""
        
        dpia_report = {
            'dpia_id': str(uuid4()),
            'processing_activity': processing_activity,
            'ai_system': ai_system_description,
            'assessment_date': datetime.utcnow().isoformat(),
            'assessor': 'Healthcare AI Compliance Team',
            'sections': {}
        }
        
        # 1. Systematic Description of Processing
        dpia_report['sections']['processing_description'] = await self._describe_processing_operations(
            processing_activity, ai_system_description
        )
        
        # 2. Assessment of Necessity and Proportionality
        dpia_report['sections']['necessity_assessment'] = await self._assess_necessity_proportionality(
            processing_activity
        )
        
        # 3. Risk Assessment
        dpia_report['sections']['risk_assessment'] = await self._conduct_risk_assessment(
            ai_system_description
        )
        
        # 4. Measures to Address Risks
        dpia_report['sections']['risk_mitigation'] = await self._identify_mitigation_measures(
            dpia_report['sections']['risk_assessment']
        )
        
        # 5. Consultation with Data Subjects
        dpia_report['sections']['stakeholder_consultation'] = await self._document_stakeholder_consultation()
        
        # Overall DPIA conclusion
        dpia_report['conclusion'] = await self._generate_dpia_conclusion(dpia_report['sections'])
        
        # Log DPIA completion
        self.logger.info(
            f"GDPR DPIA completed for {processing_activity}",
            extra={
                'operation_type': 'gdpr_dpia_completion',
                'dpia_id': dpia_report['dpia_id'],
                'processing_activity': processing_activity,
                'risk_level': dpia_report['conclusion']['overall_risk_level'],
                'compliance_requirement': 'GDPR_Article_35'
            }
        )
        
        return dpia_report
    
    async def _conduct_risk_assessment(self, ai_system: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct detailed risk assessment for AI system"""
        
        risk_factors = [
            'automated_decision_making',
            'sensitive_data_processing',
            'large_scale_processing',
            'matching_combining_datasets',
            'vulnerable_data_subjects',
            'innovative_technology',
            'profiling_evaluation'
        ]
        
        identified_risks = []
        
        for factor in risk_factors:
            risk_assessment = await self._assess_risk_factor(ai_system, factor)
            if risk_assessment['present']:
                identified_risks.append(risk_assessment)
        
        # Calculate overall risk level
        overall_risk = self._calculate_overall_risk_level(identified_risks)
        
        return {
            'risk_factors_assessed': risk_factors,
            'identified_risks': identified_risks,
            'overall_risk_level': overall_risk,
            'high_risk_processing': overall_risk in ['HIGH', 'VERY_HIGH'],
            'dpo_consultation_required': overall_risk in ['HIGH', 'VERY_HIGH'],
            'supervisory_authority_consultation_required': overall_risk == 'VERY_HIGH'
        }
```

## FDA Compliance (for AI/ML Medical Devices)

### 1. Software as Medical Device (SaMD) Classification

```python
# ✅ CORRECT: FDA SaMD Classification and Quality Management
class FDASaMDCompliance:
    """FDA Software as Medical Device compliance for healthcare AI"""
    
    def __init__(self):
        self.logger = get_healthcare_logger('fda_samd_compliance')
    
    async def classify_samd(
        self,
        software_description: Dict[str, Any],
        intended_use: str,
        healthcare_situation: str,
        healthcare_decision: str
    ) -> Dict[str, Any]:
        """Classify Software as Medical Device per FDA guidance"""
        
        # Healthcare Situation Classification
        healthcare_situations = {
            'critical': 'Life-threatening or irreversible morbidity',
            'serious': 'Serious healthcare situations',
            'non_serious': 'Non-serious healthcare situations'
        }
        
        # Healthcare Decision Classification  
        healthcare_decisions = {
            'treat_diagnose': 'Treat or diagnose',
            'drive_clinical_management': 'Drive clinical management',
            'inform_clinical_management': 'Inform clinical management'
        }
        
        # SaMD Risk Classification Matrix
        risk_matrix = {
            ('critical', 'treat_diagnose'): 'Class III',
            ('critical', 'drive_clinical_management'): 'Class III', 
            ('critical', 'inform_clinical_management'): 'Class II',
            ('serious', 'treat_diagnose'): 'Class II',
            ('serious', 'drive_clinical_management'): 'Class II',
            ('serious', 'inform_clinical_management'): 'Class I',
            ('non_serious', 'treat_diagnose'): 'Class II',
            ('non_serious', 'drive_clinical_management'): 'Class I',
            ('non_serious', 'inform_clinical_management'): 'Class I'
        }
        
        classification = risk_matrix.get((healthcare_situation, healthcare_decision), 'Unclassified')
        
        samd_classification = {
            'classification_id': str(uuid4()),
            'software_description': software_description,
            'intended_use': intended_use,
            'healthcare_situation': healthcare_situation,
            'healthcare_decision': healthcare_decision,
            'samd_class': classification,
            'regulatory_requirements': self._get_regulatory_requirements(classification),
            'classification_date': datetime.utcnow().isoformat()
        }
        
        # Log classification
        self.logger.info(
            f"FDA SaMD classified as {classification}",
            extra={
                'operation_type': 'fda_samd_classification',
                'samd_class': classification,
                'healthcare_situation': healthcare_situation,
                'healthcare_decision': healthcare_decision,
                'compliance_requirement': 'FDA_SaMD_Guidance'
            }
        )
        
        return samd_classification
    
    def _get_regulatory_requirements(self, samd_class: str) -> List[str]:
        """Get regulatory requirements based on SaMD classification"""
        
        requirements = {
            'Class I': [
                'FDA Registration and Listing',
                'QSR (Quality System Regulation) compliance',
                'Labeling requirements',
                'Post-market surveillance'
            ],
            'Class II': [
                'FDA Registration and Listing',
                'QSR compliance',
                '510(k) Premarket Notification',
                'Special Controls compliance',
                'Labeling requirements', 
                'Post-market surveillance',
                'MDR (Medical Device Reporting)'
            ],
            'Class III': [
                'FDA Registration and Listing',
                'QSR compliance',
                'PMA (Premarket Approval)',
                'Clinical trials may be required',
                'Labeling requirements',
                'Post-market surveillance',
                'MDR compliance',
                'Post-market studies may be required'
            ]
        }
        
        return requirements.get(samd_class, [])
```

## Audit Trail and Compliance Monitoring

### 1. Comprehensive Audit System

```python
# ✅ CORRECT: Healthcare Compliance Audit System
class HealthcareComplianceAuditSystem:
    """Comprehensive audit system for healthcare compliance"""
    
    def __init__(self):
        self.logger = get_healthcare_logger('compliance_audit')
    
    async def generate_hipaa_audit_report(
        self,
        audit_period_start: datetime,
        audit_period_end: datetime
    ) -> Dict[str, Any]:
        """Generate comprehensive HIPAA compliance audit report"""
        
        audit_report = {
            'report_id': str(uuid4()),
            'report_type': 'HIPAA_COMPLIANCE_AUDIT',
            'audit_period': {
                'start_date': audit_period_start.isoformat(),
                'end_date': audit_period_end.isoformat()
            },
            'generation_date': datetime.utcnow().isoformat(),
            'sections': {}
        }
        
        # Administrative Safeguards Audit
        audit_report['sections']['administrative_safeguards'] = await self._audit_administrative_safeguards(
            audit_period_start, audit_period_end
        )
        
        # Physical Safeguards Audit
        audit_report['sections']['physical_safeguards'] = await self._audit_physical_safeguards(
            audit_period_start, audit_period_end
        )
        
        # Technical Safeguards Audit
        audit_report['sections']['technical_safeguards'] = await self._audit_technical_safeguards(
            audit_period_start, audit_period_end
        )
        
        # Access Control Audit
        audit_report['sections']['access_control'] = await self._audit_access_controls(
            audit_period_start, audit_period_end
        )
        
        # Breach Assessment
        audit_report['sections']['breach_assessment'] = await self._audit_security_incidents(
            audit_period_start, audit_period_end
        )
        
        # Overall Compliance Score
        audit_report['compliance_score'] = await self._calculate_compliance_score(
            audit_report['sections']
        )
        
        # Recommendations
        audit_report['recommendations'] = await self._generate_compliance_recommendations(
            audit_report['sections']
        )
        
        # Log audit report generation
        self.logger.info(
            f"HIPAA audit report generated",
            extra={
                'operation_type': 'hipaa_audit_report',
                'report_id': audit_report['report_id'],
                'compliance_score': audit_report['compliance_score'],
                'audit_period_days': (audit_period_end - audit_period_start).days
            }
        )
        
        return audit_report
    
    async def _audit_access_controls(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Audit access control compliance"""
        
        access_audit = {
            'total_access_attempts': 0,
            'successful_accesses': 0,
            'failed_accesses': 0,
            'unauthorized_attempts': 0,
            'minimum_necessary_violations': 0,
            'compliance_score': 0.0,
            'findings': []
        }
        
        # Query access logs for audit period
        access_logs = await self._get_access_logs(start_date, end_date)
        
        access_audit['total_access_attempts'] = len(access_logs)
        
        for log_entry in access_logs:
            if log_entry['access_granted']:
                access_audit['successful_accesses'] += 1
                
                # Check minimum necessary compliance
                if not await self._verify_minimum_necessary(log_entry):
                    access_audit['minimum_necessary_violations'] += 1
                    access_audit['findings'].append({
                        'type': 'MINIMUM_NECESSARY_VIOLATION',
                        'log_id': log_entry['log_id'],
                        'user_id': log_entry['user_id'],
                        'timestamp': log_entry['timestamp']
                    })
            else:
                access_audit['failed_accesses'] += 1
                
                # Check if failure was due to unauthorized attempt
                if log_entry['failure_reason'] == 'UNAUTHORIZED':
                    access_audit['unauthorized_attempts'] += 1
        
        # Calculate compliance score
        if access_audit['total_access_attempts'] > 0:
            access_audit['compliance_score'] = (
                (access_audit['successful_accesses'] - access_audit['minimum_necessary_violations']) /
                access_audit['total_access_attempts']
            ) * 100
        
        return access_audit
```

### 2. Automated Compliance Monitoring

```python
# ✅ CORRECT: Real-time Compliance Monitoring
class RealTimeComplianceMonitor:
    """Real-time monitoring for healthcare compliance violations"""
    
    def __init__(self):
        self.logger = get_healthcare_logger('compliance_monitor')
        self.alert_thresholds = {
            'failed_access_attempts': 5,
            'unauthorized_phi_access': 1,
            'data_breach_indicators': 1,
            'suspicious_activity_score': 80
        }
    
    async def monitor_phi_access_patterns(self, access_event: Dict[str, Any]) -> None:
        """Monitor PHI access patterns for compliance violations"""
        
        # Real-time pattern analysis
        suspicious_indicators = []
        
        # Check for unusual access patterns
        if await self._detect_unusual_access_time(access_event):
            suspicious_indicators.append('UNUSUAL_ACCESS_TIME')
        
        if await self._detect_bulk_data_access(access_event):
            suspicious_indicators.append('BULK_DATA_ACCESS')
        
        if await self._detect_unauthorized_data_combination(access_event):
            suspicious_indicators.append('UNAUTHORIZED_DATA_COMBINATION')
        
        # Calculate suspicion score
        suspicion_score = len(suspicious_indicators) * 25
        
        if suspicion_score >= self.alert_thresholds['suspicious_activity_score']:
            await self._trigger_compliance_alert(
                alert_type='SUSPICIOUS_PHI_ACCESS',
                severity='HIGH',
                access_event=access_event,
                indicators=suspicious_indicators,
                suspicion_score=suspicion_score
            )
    
    async def _trigger_compliance_alert(
        self,
        alert_type: str,
        severity: str,
        **alert_data
    ) -> None:
        """Trigger compliance alert with immediate notification"""
        
        alert = {
            'alert_id': str(uuid4()),
            'alert_type': alert_type,
            'severity': severity,
            'timestamp': datetime.utcnow().isoformat(),
            'alert_data': alert_data,
            'requires_immediate_action': severity in ['HIGH', 'CRITICAL']
        }
        
        # Log compliance alert
        self.logger.error(
            f"Compliance alert triggered: {alert_type}",
            extra={
                'operation_type': 'compliance_alert',
                'alert_id': alert['alert_id'],
                'alert_type': alert_type,
                'severity': severity,
                'requires_immediate_action': alert['requires_immediate_action']
            }
        )
        
        # Send immediate notifications for high-severity alerts
        if alert['requires_immediate_action']:
            await self._send_immediate_compliance_notification(alert)
        
        # Store alert for audit trail
        await self._store_compliance_alert(alert)
```

## Testing Compliance Implementation

### 1. Compliance Testing Framework

```python
# ✅ CORRECT: Healthcare Compliance Testing
import pytest
from unittest.mock import Mock, patch

@pytest.mark.asyncio
async def test_hipaa_access_control_compliance():
    """Test HIPAA access control compliance"""
    
    # Setup test environment
    safeguards = HIPAATechnicalSafeguards()
    
    # Test legitimate access request
    access_result = await safeguards.implement_access_controls(
        user_id='test_provider_001',
        requested_permissions=['read_patient_records', 'write_treatment_notes'],
        requesting_supervisor='supervisor_001',
        business_justification='Patient treatment and care coordination'
    )
    
    # Verify minimum necessary standard applied
    assert 'read_patient_records' in access_result['approved_permissions']
    assert 'write_treatment_notes' in access_result['approved_permissions']
    assert access_result['business_justification'] == 'Patient treatment and care coordination'
    
    # Test excessive access request (should be denied)
    excessive_access_result = await safeguards.implement_access_controls(
        user_id='test_provider_001',
        requested_permissions=['read_all_patient_records', 'admin_access', 'delete_records'],
        requesting_supervisor='supervisor_001', 
        business_justification='General access'
    )
    
    # Verify excessive permissions denied
    assert 'admin_access' in excessive_access_result['denied_permissions']
    assert 'delete_records' in excessive_access_result['denied_permissions']

@pytest.mark.asyncio 
async def test_gdpr_data_subject_rights():
    """Test GDPR data subject rights implementation"""
    
    # Setup test environment
    gdpr_rights = GDPRDataSubjectRights()
    
    # Mock identity verification
    with patch.object(gdpr_rights, '_verify_data_subject_identity', return_value=True):
        # Test right of access
        access_result = await gdpr_rights.handle_right_of_access(
            data_subject_id='test_subject_001',
            requester_verification={'id_document': 'verified', 'email_confirmation': 'verified'}
        )
        
        assert access_result['data_subject_id'] == 'test_subject_001'
        assert 'data_categories' in access_result
        assert 'processing_purposes' in access_result
        
        # Test right to rectification
        rectification_result = await gdpr_rights.handle_right_to_rectification(
            data_subject_id='test_subject_001',
            correction_requests=[{
                'field': 'email_address',
                'old_value': 'old@example.com',
                'new_value': 'new@example.com'
            }],
            requester_verification={'id_document': 'verified', 'email_confirmation': 'verified'}
        )
        
        assert rectification_result['data_subject_id'] == 'test_subject_001'
        assert len(rectification_result['rectification_results']) == 1
```

## Medical Disclaimer

**MEDICAL DISCLAIMER: This compliance instruction set provides regulatory compliance patterns and frameworks for healthcare administrative systems only. It assists healthcare technology professionals with HIPAA, GDPR, FDA, and other regulatory requirements for healthcare AI systems. It does not provide medical advice, diagnosis, or treatment recommendations. It does not constitute legal advice and should not replace consultation with qualified healthcare compliance attorneys and regulatory experts. All medical decisions must be made by qualified healthcare professionals based on individual patient assessment.**
