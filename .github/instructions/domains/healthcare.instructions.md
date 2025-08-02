# Healthcare AI Domain Instructions

## Purpose

Comprehensive guidance for AI development in healthcare domains, emphasizing medical compliance, patient safety, and healthcare-specific technical patterns.

## Core Healthcare AI Principles

### Medical Safety Framework

```python
# ✅ CRITICAL: Healthcare AI safety principles
class HealthcareAISafetyFramework:
    """Framework ensuring AI safety in healthcare contexts."""

    PROHIBITED_ACTIONS = [
        "autonomous_medical_diagnosis",
        "unsupervised_treatment_recommendations",
        "medication_dosage_decisions",
        "replacing_clinical_judgment",
        "emergency_response_decisions"
    ]

    ALLOWED_ACTIONS = [
        "clinical_decision_support",
        "medical_research_assistance",
        "documentation_analysis",
        "administrative_documentation",
        "data_organization",
        "workflow_optimization",
        "compliance_checking",
        "scheduling_assistance",
        "literature_review_support",
        "patient_data_analysis"
    ]

    @staticmethod
    def validate_ai_action(action: str, context: Dict[str, Any]) -> bool:
        """Validate AI action against healthcare safety principles."""

        if action in HealthcareAISafetyFramework.PROHIBITED_ACTIONS:
            logger.critical(
                f"PROHIBITED AI ACTION ATTEMPTED: {action}",
                extra={
                    "action": action,
                    "context": context,
                    "requires_escalation": True
                }
            )
            return False

        if action in HealthcareAISafetyFramework.ALLOWED_ACTIONS:
            logger.info(f"Approved AI action: {action}")
            return True

        # Unknown actions require review
        logger.warning(f"Unknown AI action requires review: {action}")
        return False

    @staticmethod
    def generate_medical_disclaimer() -> str:
        """Generate standard medical disclaimer for AI outputs."""
        return """
        ⚠️ HEALTHCARE PROVIDER SUPPORT SYSTEM:
        This AI system supports clinical decision-making for healthcare providers.
        It does not replace clinical judgment or professional medical expertise.
        All medical decisions remain the responsibility of qualified healthcare professionals.
        """
```

### Healthcare Compliance Framework

```python
# ✅ CORRECT: HIPAA compliance patterns
class HIPAAComplianceFramework:
    """Framework for HIPAA-compliant AI development."""

    PHI_CATEGORIES = {
        "identifiers": ["name", "address", "ssn", "phone", "email"],
        "dates": ["birth_date", "admission_date", "discharge_date"],
        "medical": ["medical_record_number", "account_number", "diagnosis"],
        "biometric": ["fingerprints", "voice_patterns", "full_face_photos"],
        "device": ["device_identifiers", "serial_numbers", "ip_addresses"]
    }

    @staticmethod
    def classify_data_sensitivity(data: Dict[str, Any]) -> str:
        """Classify data sensitivity level for compliance."""

        phi_detected = []
        for category, fields in HIPAAComplianceFramework.PHI_CATEGORIES.items():
            for field in fields:
                if field in data or any(field in str(value) for value in data.values()):
                    phi_detected.append(category)

        if phi_detected:
            return "PHI_RESTRICTED"
        elif any(keyword in str(data).lower() for keyword in ["medical", "patient", "healthcare"]):
            return "HEALTHCARE_SENSITIVE"
        else:
            return "GENERAL"

    @staticmethod
    def apply_data_minimization(data: Dict[str, Any], purpose: str) -> Dict[str, Any]:
        """Apply HIPAA data minimization principle."""

        # Define purpose-specific data requirements
        purpose_requirements = {
            "scheduling": ["patient_id", "appointment_time", "provider_id"],
            "billing": ["patient_id", "procedure_codes", "insurance_info"],
            "documentation": ["patient_id", "encounter_id", "note_content"],
            "analytics": ["anonymized_demographics", "outcome_measures"]
        }

        required_fields = purpose_requirements.get(purpose, list(data.keys()))

        # Return only necessary fields
        minimized_data = {
            field: data[field] for field in required_fields if field in data
        }

        logger.info(
            f"Data minimization applied for purpose: {purpose}",
            extra={
                "original_fields": len(data),
                "minimized_fields": len(minimized_data),
                "purpose": purpose
            }
        )

        return minimized_data
```

### Medical Workflow Integration

```python
# ✅ CORRECT: Healthcare workflow patterns
class HealthcareWorkflowManager:
    """Manage healthcare workflows with AI integration."""

    def __init__(self, workflow_config: Dict[str, Any]) -> None:
        self.workflow_config = workflow_config
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.compliance_validator = HIPAAComplianceFramework()

    async def initiate_patient_intake(
        self,
        patient_data: Dict[str, Any],
        intake_type: str
    ) -> Dict[str, Any]:
        """Initiate patient intake workflow with AI assistance."""

        # Validate medical safety
        if not HealthcareAISafetyFramework.validate_ai_action("administrative_documentation", patient_data):
            raise HealthcareComplianceError("AI action not approved for patient intake")

        # Apply data minimization
        minimized_data = self.compliance_validator.apply_data_minimization(
            patient_data, "scheduling"
        )

        # Create workflow instance
        workflow_id = f"intake_{hashlib.sha256(str(minimized_data).encode()).hexdigest()[:8]}"

        workflow_instance = {
            "workflow_id": workflow_id,
            "type": intake_type,
            "status": "initiated",
            "steps_completed": [],
            "patient_hash": hashlib.sha256(patient_data.get("patient_id", "").encode()).hexdigest()[:8],
            "created_at": datetime.now(),
            "ai_assistance_level": "administrative_only"
        }

        self.active_workflows[workflow_id] = workflow_instance

        # Process intake steps
        return await self._process_intake_steps(workflow_id, minimized_data)

    async def _process_intake_steps(
        self,
        workflow_id: str,
        patient_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process intake steps with AI assistance."""

        intake_steps = [
            "validate_demographics",
            "verify_insurance",
            "collect_medical_history",
            "schedule_appointment",
            "generate_intake_summary"
        ]

        workflow = self.active_workflows[workflow_id]
        results = {}

        for step in intake_steps:
            try:
                # AI-assisted step processing (administrative only)
                step_result = await self._execute_intake_step(step, patient_data)
                workflow["steps_completed"].append(step)
                results[step] = step_result

                logger.info(
                    f"Intake step completed: {step}",
                    extra={
                        "workflow_id": workflow_id,
                        "step": step,
                        "patient_hash": workflow["patient_hash"]
                    }
                )

            except Exception as e:
                logger.error(
                    f"Intake step failed: {step}",
                    extra={
                        "workflow_id": workflow_id,
                        "step": step,
                        "error": str(e),
                        "patient_hash": workflow["patient_hash"]
                    }
                )
                results[step] = {"status": "failed", "error": str(e)}

        workflow["status"] = "completed"
        workflow["completed_at"] = datetime.now()

        return {
            "workflow_id": workflow_id,
            "status": workflow["status"],
            "results": results,
            "medical_disclaimer": HealthcareAISafetyFramework.generate_medical_disclaimer()
        }
```

### Healthcare AI Agent Coordination

```python
# ✅ CORRECT: Multi-agent healthcare coordination
class HealthcareAgentOrchestrator:
    """Orchestrate multiple healthcare AI agents safely."""

    def __init__(self) -> None:
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.agent_communications: List[Dict[str, Any]] = []
        self.safety_framework = HealthcareAISafetyFramework()

    def register_healthcare_agent(
        self,
        agent_name: str,
        capabilities: List[str],
        compliance_level: str
    ) -> None:
        """Register healthcare AI agent with safety validation."""

        # Validate agent capabilities against safety framework
        approved_capabilities = []
        for capability in capabilities:
            if self.safety_framework.validate_ai_action(capability, {}):
                approved_capabilities.append(capability)
            else:
                logger.warning(f"Agent capability not approved: {capability}")

        self.registered_agents[agent_name] = {
            "capabilities": approved_capabilities,
            "compliance_level": compliance_level,
            "registered_at": datetime.now(),
            "status": "active"
        }

        logger.info(
            f"Healthcare agent registered: {agent_name}",
            extra={
                "agent": agent_name,
                "approved_capabilities": len(approved_capabilities),
                "compliance_level": compliance_level
            }
        )

    async def coordinate_patient_workflow(
        self,
        patient_context: Dict[str, Any],
        required_agents: List[str]
    ) -> Dict[str, Any]:
        """Coordinate multiple agents for patient workflow."""

        coordination_id = f"coord_{hashlib.sha256(str(patient_context).encode()).hexdigest()[:8]}"

        # Validate all required agents are registered and compliant
        for agent_name in required_agents:
            if agent_name not in self.registered_agents:
                raise ValueError(f"Agent not registered: {agent_name}")

            agent_info = self.registered_agents[agent_name]
            if agent_info["compliance_level"] != "HIPAA_COMPLIANT":
                raise HealthcareComplianceError(f"Agent not compliant: {agent_name}")

        # Coordinate agent execution with safety monitoring
        coordination_results = {}

        for agent_name in required_agents:
            try:
                # Execute agent with safety monitoring
                agent_result = await self._execute_agent_safely(
                    agent_name, patient_context, coordination_id
                )
                coordination_results[agent_name] = agent_result

            except Exception as e:
                logger.error(
                    f"Agent execution failed: {agent_name}",
                    extra={
                        "coordination_id": coordination_id,
                        "agent": agent_name,
                        "error": str(e)
                    }
                )
                coordination_results[agent_name] = {"status": "failed", "error": str(e)}

        return {
            "coordination_id": coordination_id,
            "results": coordination_results,
            "safety_validated": True,
            "compliance_verified": True,
            "medical_disclaimer": self.safety_framework.generate_medical_disclaimer()
        }

    async def _execute_agent_safely(
        self,
        agent_name: str,
        context: Dict[str, Any],
        coordination_id: str
    ) -> Dict[str, Any]:
        """Execute agent with comprehensive safety monitoring."""

        agent_info = self.registered_agents[agent_name]

        # Pre-execution safety check
        for capability in agent_info["capabilities"]:
            if not self.safety_framework.validate_ai_action(capability, context):
                raise HealthcareComplianceError(f"Unsafe AI action: {capability}")

        # Execute with monitoring
        execution_start = datetime.now()

        try:
            # Simulate agent execution (replace with actual agent calls)
            result = await self._call_healthcare_agent(agent_name, context)

            execution_time = (datetime.now() - execution_start).total_seconds()

            # Post-execution validation
            self._validate_agent_output(result, agent_name)

            # Log successful execution
            self.agent_communications.append({
                "coordination_id": coordination_id,
                "agent": agent_name,
                "execution_time": execution_time,
                "status": "success",
                "timestamp": datetime.now()
            })

            return {
                "status": "success",
                "result": result,
                "execution_time": execution_time,
                "safety_validated": True
            }

        except Exception as e:
            # Log failed execution
            self.agent_communications.append({
                "coordination_id": coordination_id,
                "agent": agent_name,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now()
            })
            raise

    def _validate_agent_output(self, output: Dict[str, Any], agent_name: str) -> None:
        """Validate agent output for healthcare compliance."""

        # Check for medical advice in output
        output_text = str(output).lower()
        medical_advice_patterns = [
            "you should take",
            "recommended treatment",
            "my diagnosis is",
            "take this medication"
        ]

        for pattern in medical_advice_patterns:
            if pattern in output_text:
                raise HealthcareComplianceError(
                    f"Agent {agent_name} provided medical advice: {pattern}"
                )

        # Check for PHI exposure
        phi_patterns = [
            r'\d{3}-\d{2}-\d{4}',  # SSN
            r'\(\d{3}\)\s*\d{3}-\d{4}',  # Phone
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # Email
        ]

        for pattern in phi_patterns:
            if re.search(pattern, output_text):
                raise PHIExposureError(
                    f"Agent {agent_name} exposed PHI pattern",
                    phi_type=pattern
                )
```

## Healthcare Domain Integration Patterns

### EHR Integration with AI Safety

```python
# ✅ CORRECT: Safe EHR integration patterns
class SafeEHRIntegration:
    """EHR integration with healthcare AI safety controls."""

    def __init__(self, ehr_config: Dict[str, Any]) -> None:
        self.ehr_config = ehr_config
        self.safety_framework = HealthcareAISafetyFramework()
        self.audit_logger = self._setup_audit_logging()

    async def ai_assisted_documentation(
        self,
        provider_notes: str,
        patient_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """AI-assisted clinical documentation with safety controls."""

        # Validate AI assistance is administrative only
        if not self.safety_framework.validate_ai_action("administrative_documentation", patient_context):
            raise HealthcareComplianceError("AI documentation assistance not approved")

        # Process documentation with AI assistance
        documentation_result = {
            "original_notes": provider_notes,
            "structured_format": await self._structure_provider_notes(provider_notes),
            "completeness_check": await self._check_documentation_completeness(provider_notes),
            "formatting_suggestions": await self._suggest_formatting_improvements(provider_notes),
            "medical_disclaimer": self.safety_framework.generate_medical_disclaimer()
        }

        # Audit AI assistance
        await self._audit_ai_documentation_assistance(patient_context, documentation_result)

        return documentation_result

    async def _structure_provider_notes(self, notes: str) -> Dict[str, str]:
        """Structure provider notes without medical interpretation."""

        # AI assists with formatting only, not medical content
        structured_notes = {
            "chief_complaint": self._extract_section(notes, "chief complaint"),
            "history_present_illness": self._extract_section(notes, "history of present illness"),
            "physical_examination": self._extract_section(notes, "physical exam"),
            "assessment_plan": self._extract_section(notes, "assessment and plan")
        }

        return {k: v for k, v in structured_notes.items() if v}

    async def _check_documentation_completeness(self, notes: str) -> Dict[str, Any]:
        """Check documentation completeness (administrative review only)."""

        required_sections = [
            "chief complaint",
            "history of present illness",
            "physical examination",
            "assessment and plan"
        ]

        completeness_report = {
            "sections_present": [],
            "sections_missing": [],
            "completeness_score": 0.0
        }

        notes_lower = notes.lower()
        for section in required_sections:
            if section in notes_lower:
                completeness_report["sections_present"].append(section)
            else:
                completeness_report["sections_missing"].append(section)

        completeness_report["completeness_score"] = (
            len(completeness_report["sections_present"]) / len(required_sections)
        )

        return completeness_report
```

### Clinical Decision Support Integration

```python
# ✅ CORRECT: AI-assisted clinical decision support (administrative only)
class ClinicalDecisionSupportAssistant:
    """AI assistant for clinical decision support - administrative functions only."""

    def __init__(self) -> None:
        self.safety_framework = HealthcareAISafetyFramework()
        self.knowledge_base = self._load_clinical_knowledge_base()

    async def assist_clinical_documentation(
        self,
        clinical_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assist with clinical documentation organization."""

        # CRITICAL: Only administrative assistance, no clinical decisions
        assistance_result = {
            "documentation_structure": await self._suggest_documentation_structure(clinical_context),
            "coding_assistance": await self._assist_medical_coding(clinical_context),
            "compliance_reminders": await self._generate_compliance_reminders(clinical_context),
            "workflow_optimization": await self._suggest_workflow_improvements(clinical_context),
            "medical_disclaimer": "This system provides administrative support only. All clinical decisions must be made by qualified healthcare professionals."
        }

        return assistance_result

    async def _assist_medical_coding(self, clinical_context: Dict[str, Any]) -> Dict[str, Any]:
        """Assist with medical coding (administrative support only)."""

        coding_assistance = {
            "potential_icd_codes": await self._suggest_icd_codes(clinical_context),
            "potential_cpt_codes": await self._suggest_cpt_codes(clinical_context),
            "coding_completeness": await self._check_coding_completeness(clinical_context),
            "coding_disclaimer": "Code suggestions are for administrative review only. Final coding decisions require qualified medical coding professionals."
        }

        return coding_assistance

    async def _generate_compliance_reminders(self, clinical_context: Dict[str, Any]) -> List[str]:
        """Generate healthcare compliance reminders."""

        reminders = []

        # HIPAA compliance reminders
        if "phi_present" in clinical_context:
            reminders.append("Ensure PHI is properly protected and access is logged")

        # Documentation compliance
        if "incomplete_documentation" in clinical_context:
            reminders.append("Complete all required documentation sections")

        # Quality measure reminders
        if "quality_measures" in clinical_context:
            reminders.append("Review applicable quality measures for this encounter")

        return reminders
```

## Healthcare AI Development Standards

### Development Workflow Integration

```python
# ✅ CORRECT: Healthcare AI development patterns
class HealthcareAIDevelopmentFramework:
    """Framework for healthcare AI development standards."""

    DEVELOPMENT_PHASES = {
        "design": {
            "safety_review": True,
            "compliance_validation": True,
            "medical_review": True
        },
        "implementation": {
            "phi_protection": True,
            "audit_logging": True,
            "error_handling": True
        },
        "testing": {
            "synthetic_data_only": True,
            "compliance_testing": True,
            "safety_validation": True
        },
        "deployment": {
            "security_hardening": True,
            "monitoring_setup": True,
            "incident_response": True
        }
    }

    @staticmethod
    def validate_development_phase(phase: str, requirements: Dict[str, Any]) -> bool:
        """Validate development phase meets healthcare standards."""

        phase_requirements = HealthcareAIDevelopmentFramework.DEVELOPMENT_PHASES.get(phase, {})

        for requirement, required in phase_requirements.items():
            if required and not requirements.get(requirement, False):
                logger.error(f"Healthcare development requirement not met: {requirement}")
                return False

        return True

    @staticmethod
    def generate_healthcare_ai_checklist(phase: str) -> List[str]:
        """Generate development checklist for healthcare AI."""

        base_checklist = [
            "Medical safety principles implemented",
            "PHI protection mechanisms in place",
            "Audit logging configured",
            "Compliance validation included",
            "Medical disclaimers present",
            "Error handling comprehensive",
            "Testing with synthetic data only",
            "Documentation complete and accurate"
        ]

        phase_specific = {
            "design": [
                "Medical professional consultation completed",
                "Safety framework design reviewed",
                "Compliance requirements identified"
            ],
            "implementation": [
                "Type safety implemented",
                "Modern Python patterns used (Ruff, MyPy)",
                "Healthcare-specific error handling",
                "Integration patterns validated"
            ],
            "testing": [
                "Synthetic data generation verified",
                "Compliance testing automated",
                "Safety validation comprehensive",
                "Performance testing completed"
            ],
            "deployment": [
                "Security hardening applied",
                "Monitoring and alerting configured",
                "Incident response procedures documented",
                "Rollback procedures tested"
            ]
        }

        return base_checklist + phase_specific.get(phase, [])
```

## Healthcare AI Compliance Validation

### Automated Compliance Checking

```python
# ✅ CORRECT: Automated healthcare compliance validation
class HealthcareComplianceValidator:
    """Automated validation of healthcare AI compliance."""

    def __init__(self) -> None:
        self.compliance_rules = self._load_compliance_rules()
        self.violation_logger = self._setup_violation_logging()

    async def validate_ai_system_compliance(self, system_config: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive compliance validation for healthcare AI systems."""

        validation_results = {
            "hipaa_compliance": await self._validate_hipaa_compliance(system_config),
            "medical_safety": await self._validate_medical_safety(system_config),
            "data_protection": await self._validate_data_protection(system_config),
            "audit_requirements": await self._validate_audit_requirements(system_config),
            "technical_standards": await self._validate_technical_standards(system_config)
        }

        # Calculate overall compliance score
        compliance_score = self._calculate_compliance_score(validation_results)

        return {
            "validation_results": validation_results,
            "compliance_score": compliance_score,
            "certification_ready": compliance_score >= 0.95,
            "improvement_recommendations": self._generate_improvement_recommendations(validation_results),
            "validation_timestamp": datetime.now().isoformat()
        }

    def _calculate_compliance_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall compliance score."""

        scores = []
        for category, result in results.items():
            if isinstance(result, dict) and "score" in result:
                scores.append(result["score"])

        return sum(scores) / len(scores) if scores else 0.0
```

Remember: Healthcare AI development requires strict adherence to medical safety principles, comprehensive PHI protection, and continuous compliance validation throughout the development lifecycle.
