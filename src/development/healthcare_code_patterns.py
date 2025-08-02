"""
Healthcare Code Patterns and Best Practices
Standardized patterns for healthcare AI development with HIPAA compliance
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

# Configure logging
logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of healthcare code patterns"""

    SECURITY = "security"
    COMPLIANCE = "compliance"
    MEDICAL = "medical"
    DATA_HANDLING = "data_handling"
    API = "api"
    TESTING = "testing"


@dataclass
class CodePattern:
    """Healthcare code pattern definition"""

    name: str
    pattern_type: PatternType
    description: str
    template: str
    required_imports: list[str]
    compliance_notes: list[str]
    security_considerations: list[str]


class HealthcareCodePatterns:
    """Repository of healthcare-specific code patterns"""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.patterns = self._initialize_patterns()

    def _initialize_patterns(self) -> dict[str, CodePattern]:
        """Initialize healthcare code patterns"""
        patterns = {}

        # Security Patterns
        patterns["secure_api_endpoint"] = CodePattern(
            name="Secure API Endpoint",
            pattern_type=PatternType.SECURITY,
            description="HIPAA-compliant API endpoint with authentication and audit logging",
            template='''
@app.post("/api/v1/patient/{patient_id}")
@require_authentication
@require_authorization("patient_data", "read")
async def get_patient_data(
    patient_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve patient data with HIPAA compliance

    Args:
        patient_id: Patient identifier
        request: HTTP request object
        current_user: Authenticated user

    Returns:
        Patient data with PHI protection
    """
    try:
        # Audit log the access attempt
        await audit_logger.log_phi_access(
            user_id=current_user.user_id,
            patient_id=patient_id,
            action="read_patient_data",
            granted=True,
            request_context={
                "ip_address": request.client.host,
                "user_agent": request.headers.get("user-agent"),
                "reason": "patient_care"
            }
        )

        # Retrieve patient data
        patient_data = await patient_service.get_patient(patient_id)

        # Apply minimum necessary principle
        filtered_data = apply_minimum_necessary_filter(
            patient_data,
            current_user.role,
            purpose="patient_care"
        )

        # Detect and mask PHI if needed
        phi_result = await phi_detector.detect_phi(json.dumps(filtered_data))
        if phi_result.phi_detected:
            filtered_data = phi_result.masked_data

        return {
            "patient_data": filtered_data,
            "access_timestamp": datetime.now().isoformat(),
            "accessed_by": current_user.user_id,
            "data_classification": "PHI"
        }

    except Exception as e:
        # Log security incident
        await security_logger.log_security_event(
            event_type="data_access_error",
            severity="high",
            user_id=current_user.user_id,
            details={"error": str(e), "patient_id": patient_id}
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve patient data"
        )
''',
            required_imports=[
                "from fastapi import HTTPException, Depends, Request",
                "from src.security.healthcare_security import require_authentication, require_authorization",
                "from src.healthcare_mcp.audit_logger import audit_logger",
                "from src.healthcare_mcp.phi_detection import phi_detector",
            ],
            compliance_notes=[
                "Implements HIPAA minimum necessary principle",
                "Includes comprehensive audit logging",
                "PHI detection and masking",
                "Proper error handling without information disclosure",
            ],
            security_considerations=[
                "Authentication required for all access",
                "Authorization based on user role and resource",
                "All access attempts logged for audit",
                "PHI automatically detected and protected",
            ],
        )

        patterns["encrypted_data_storage"] = CodePattern(
            name="Encrypted Data Storage",
            pattern_type=PatternType.SECURITY,
            description="Secure storage of healthcare data with encryption",
            template='''
class SecureHealthcareDataStore:
    """Secure storage for healthcare data with encryption"""

    def __init__(self, encryption_manager: HealthcareEncryptionManager):
        self.encryption_manager = encryption_manager
        self.logger = logging.getLogger(__name__)

    async def store_patient_data(self, patient_data: Dict[str, Any],
                               user_id: str) -> str:
        """
        Store patient data with encryption and audit trail

        Args:
            patient_data: Patient data to store
            user_id: User storing the data

        Returns:
            Storage reference ID
        """
        try:
            # Validate data contains PHI
            phi_result = await phi_detector.detect_phi(json.dumps(patient_data))

            # Encrypt based on data sensitivity
            if phi_result.phi_detected:
                encrypted_package = self.encryption_manager.encrypt_phi_data(
                    patient_data, user_id
                )
                data_classification = "PHI"
            else:
                encrypted_package = self.encryption_manager.encrypt_basic_data(
                    patient_data, user_id
                )
                data_classification = "healthcare_data"

            # Store encrypted data
            storage_id = await self._store_encrypted_data(
                encrypted_package,
                data_classification,
                user_id
            )

            # Audit log the storage
            await audit_logger.log_audit_event(AuditEvent(
                event_id=generate_event_id(),
                timestamp=datetime.now().isoformat(),
                event_type=AuditEventType.DATA_MODIFICATION,
                user_id=user_id,
                action_performed="store_patient_data",
                outcome="success",
                details={
                    "storage_id": storage_id,
                    "data_classification": data_classification,
                    "encryption_level": encrypted_package["encryption_level"]
                },
                phi_involved=phi_result.phi_detected,
                compliance_status="compliant",
                risk_level="medium"
            ))

            return storage_id

        except Exception as e:
            self.logger.error(f"Failed to store patient data: {e}")

            # Log security incident
            await security_logger.log_security_event(
                event_type="data_storage_error",
                severity="high",
                user_id=user_id,
                details={"error": str(e)}
            )

            raise

    async def retrieve_patient_data(self, storage_id: str,
                                  user_id: str) -> Dict[str, Any]:
        """
        Retrieve and decrypt patient data

        Args:
            storage_id: Storage reference ID
            user_id: User retrieving the data

        Returns:
            Decrypted patient data
        """
        try:
            # Retrieve encrypted package
            encrypted_package = await self._get_encrypted_data(storage_id)

            if not encrypted_package:
                raise ValueError(f"Data not found: {storage_id}")

            # Decrypt data
            decrypted_data = self.encryption_manager.decrypt_data(
                encrypted_package, user_id
            )

            # Audit log the retrieval
            await audit_logger.log_audit_event(AuditEvent(
                event_id=generate_event_id(),
                timestamp=datetime.now().isoformat(),
                event_type=AuditEventType.DATA_ACCESS,
                user_id=user_id,
                action_performed="retrieve_patient_data",
                outcome="success",
                details={
                    "storage_id": storage_id,
                    "data_classification": encrypted_package.get("data_classification")
                },
                phi_involved=True,
                compliance_status="compliant",
                risk_level="medium"
            ))

            return decrypted_data

        except Exception as e:
            self.logger.error(f"Failed to retrieve patient data: {e}")

            # Log security incident
            await security_logger.log_security_event(
                event_type="data_retrieval_error",
                severity="high",
                user_id=user_id,
                details={"error": str(e), "storage_id": storage_id}
            )

            raise

    async def _store_encrypted_data(self, encrypted_package: Dict[str, Any],
                                  data_classification: str, user_id: str) -> str:
        """Store encrypted data in database"""
        # Implementation for database storage
        pass

    async def _get_encrypted_data(self, storage_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve encrypted data from database"""
        # Implementation for database retrieval
        pass
''',
            required_imports=[
                "from src.security.encryption_manager import HealthcareEncryptionManager",
                "from src.healthcare_mcp.phi_detection import phi_detector",
                "from src.healthcare_mcp.audit_logger import audit_logger, AuditEvent, AuditEventType",
            ],
            compliance_notes=[
                "Automatic PHI detection and appropriate encryption",
                "Comprehensive audit trail for all operations",
                "Data classification based on sensitivity",
                "Secure error handling",
            ],
            security_considerations=[
                "Different encryption levels based on data sensitivity",
                "All operations logged for compliance",
                "Secure key management",
                "Error handling without information disclosure",
            ],
        )

        # Medical Patterns
        patterns["medical_ai_agent"] = CodePattern(
            name="Medical AI Agent",
            pattern_type=PatternType.MEDICAL,
            description="AI agent for medical tasks with safety checks",
            template='''
class MedicalAIAgent:
    """AI agent for medical tasks with built-in safety checks"""

    def __init__(self, ollama_client, medical_knowledge_base):
        self.ollama_client = ollama_client
        self.medical_knowledge_base = medical_knowledge_base
        self.logger = logging.getLogger(__name__)

        # Medical safety components
        self.contraindication_checker = ContraindicationChecker()
        self.drug_interaction_checker = DrugInteractionChecker()
        self.medical_disclaimer_generator = MedicalDisclaimerGenerator()

    async def analyze_symptoms(self, symptoms: List[str],
                             patient_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze symptoms with medical AI

        Args:
            symptoms: List of patient symptoms
            patient_context: Optional patient context (age, gender, medical history)

        Returns:
            Analysis results with medical disclaimers
        """
        try:
            # Validate input for safety
            if not self._validate_symptom_input(symptoms):
                return {
                    "error": "Invalid symptom input",
                    "recommendation": "Please provide valid symptom descriptions"
                }

            # Check for emergency indicators
            emergency_indicators = self._check_emergency_symptoms(symptoms)
            if emergency_indicators:
                return {
                    "emergency_alert": True,
                    "message": "Symptoms may indicate a medical emergency",
                    "recommendation": "Seek immediate medical attention or call 911",
                    "emergency_symptoms": emergency_indicators
                }

            # Generate medical analysis
            analysis_prompt = self._create_medical_analysis_prompt(symptoms, patient_context)

            ai_response = await self.ollama_client.generate(
                model="llama3.1:8b-instruct-q4_K_M",
                prompt=analysis_prompt,
                options={
                    "temperature": 0.2,  # Low temperature for medical accuracy
                    "max_tokens": 800,
                    "top_p": 0.9
                }
            )

            # Apply medical safety filters
            filtered_response = self._apply_medical_safety_filters(ai_response["response"])

            # Add medical disclaimers
            final_response = self.medical_disclaimer_generator.add_disclaimers(
                filtered_response, "symptom_analysis"
            )

            # Log medical AI usage
            await self._log_medical_ai_usage(
                "symptom_analysis", symptoms, final_response
            )

            return final_response

        except Exception as e:
            self.logger.error(f"Medical AI analysis failed: {e}")
            return {
                "error": "Unable to analyze symptoms",
                "recommendation": "Please consult with a healthcare professional",
                "disclaimer": "This AI system is not a substitute for professional medical advice"
            }

    def _validate_symptom_input(self, symptoms: List[str]) -> bool:
        """Validate symptom input for safety"""
        if not symptoms or not isinstance(symptoms, list):
            return False

        # Check for valid symptom descriptions
        for symptom in symptoms:
            if not isinstance(symptom, str) or len(symptom.strip()) < 3:
                return False

        return True

    def _check_emergency_symptoms(self, symptoms: List[str]) -> List[str]:
        """Check for emergency symptom indicators"""
        emergency_keywords = [
            "chest pain", "difficulty breathing", "severe headache",
            "loss of consciousness", "severe bleeding", "stroke symptoms",
            "heart attack", "allergic reaction", "severe abdominal pain"
        ]

        emergency_found = []
        symptoms_text = " ".join(symptoms).lower()

        for keyword in emergency_keywords:
            if keyword in symptoms_text:
                emergency_found.append(keyword)

        return emergency_found

    def _create_medical_analysis_prompt(self, symptoms: List[str],
                                      context: Optional[Dict[str, Any]]) -> str:
        """Create prompt for medical analysis"""
        context_str = ""
        if context:
            context_str = f"Patient context: {json.dumps(context)}"

        return f"""
        You are a medical information assistant. Analyze the following symptoms and provide
        educational information only. Do not provide specific diagnoses or treatment recommendations.

        Symptoms: {', '.join(symptoms)}
        {context_str}

        Please provide:
        1. General information about possible conditions associated with these symptoms
        2. When to seek medical attention
        3. General health recommendations
        4. Important disclaimers

        Remember:
        - This is for educational purposes only
        - Always recommend consulting healthcare professionals
        - Do not provide specific diagnoses
        - Include appropriate medical disclaimers
        """

    def _apply_medical_safety_filters(self, response: str) -> str:
        """Apply safety filters to medical AI response"""
        # Remove any specific diagnostic language
        filtered_response = re.sub(
            r'\b(you have|diagnosed with|you are suffering from)\b',
            'symptoms may be associated with',
            response,
            flags=re.IGNORECASE
        )

        # Remove treatment recommendations
        filtered_response = re.sub(
            '\\\\b(take|use|apply|administer)\\\\s+\\\\w+\\\\s+(medication|drug|medicine)\\\\b',
            'consult a healthcare provider about appropriate treatment',
            filtered_response,
            flags=re.IGNORECASE
        )

        return filtered_response

    async def _log_medical_ai_usage(self, analysis_type: str,
                                  input_data: Any, output_data: Any):
        """Log medical AI usage for audit"""
        await audit_logger.log_audit_event(AuditEvent(
            event_id=generate_event_id(),
            timestamp=datetime.now().isoformat(),
            event_type=AuditEventType.AI_USAGE,
            user_id="system",
            action_performed=f"medical_ai_{analysis_type}",
            outcome="success",
            details={
                "analysis_type": analysis_type,
                "input_summary": str(input_data)[:100],
                "output_summary": str(output_data)[:100]
            },
            phi_involved=False,
            compliance_status="compliant",
            risk_level="low"
        ))
''',
            required_imports=[
                "import re",
                "import json",
                "from typing import List, Dict, Any, Optional",
                "from src.healthcare_mcp.audit_logger import audit_logger, AuditEvent, AuditEventType",
            ],
            compliance_notes=[
                "Medical disclaimers automatically added",
                "Emergency symptom detection",
                "Educational information only",
                "No specific diagnoses or treatments",
            ],
            security_considerations=[
                "Input validation for safety",
                "Emergency detection and alerts",
                "Medical safety filters applied",
                "Comprehensive audit logging",
            ],
        )

        return patterns

    def get_pattern(self, pattern_name: str) -> CodePattern | None:
        """Get a specific code pattern"""
        return self.patterns.get(pattern_name)

    def list_patterns(self, pattern_type: PatternType | None = None) -> list[str]:
        """List available patterns, optionally filtered by type"""
        if pattern_type:
            return [
                name
                for name, pattern in self.patterns.items()
                if pattern.pattern_type == pattern_type
            ]
        return list(self.patterns.keys())

    def validate_code_against_patterns(self, code: str) -> dict[str, Any]:
        """Validate code against healthcare patterns"""
        validation_results: dict[str, Any] = {
            "patterns_detected": [],
            "compliance_score": 0.0,
            "recommendations": [],
            "security_issues": [],
        }

        # Check for security patterns
        security_checks = {
            "authentication": any(
                keyword in code for keyword in ["@require_authentication", "authenticate", "login"]
            ),
            "authorization": any(
                keyword in code for keyword in ["@require_authorization", "authorize", "permission"]
            ),
            "encryption": any(keyword in code for keyword in ["encrypt", "decrypt", "cipher"]),
            "audit_logging": any(
                keyword in code for keyword in ["audit_logger", "log_audit", "audit_event"]
            ),
            "phi_detection": any(
                keyword in code for keyword in ["phi_detector", "detect_phi", "PHI"]
            ),
        }

        # Check for medical patterns
        medical_checks = {
            "medical_disclaimers": any(
                keyword in code
                for keyword in [
                    "disclaimer",
                    "educational purposes",
                    "consult healthcare",
                ]
            ),
            "emergency_detection": any(
                keyword in code for keyword in ["emergency", "911", "immediate medical"]
            ),
            "safety_filters": any(
                keyword in code for keyword in ["safety_filter", "medical_safety", "validate_input"]
            ),
        }

        # Calculate compliance score
        all_checks = {**security_checks, **medical_checks}
        compliance_score = sum(all_checks.values()) / len(all_checks)
        validation_results["compliance_score"] = compliance_score

        # Generate recommendations with proper type casting
        recommendations = validation_results["recommendations"]
        if isinstance(recommendations, list):
            if not security_checks["authentication"]:
                recommendations.append("Add authentication requirements")

            if not security_checks["audit_logging"]:
                recommendations.append("Implement audit logging")

            if not medical_checks["medical_disclaimers"]:
                recommendations.append("Add medical disclaimers")

        # Detect security issues with proper type casting
        security_issues = validation_results["security_issues"]
        if isinstance(security_issues, list):
            if "password" in code.lower() and "hash" not in code.lower():
                security_issues.append("Potential plaintext password usage")

            if "sql" in code.lower() and "prepare" not in code.lower():
                security_issues.append("Potential SQL injection vulnerability")

        return validation_results


# Global instance
healthcare_patterns = HealthcareCodePatterns()
