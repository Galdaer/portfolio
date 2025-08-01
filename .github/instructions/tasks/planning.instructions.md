# Healthcare AI Planning Instructions

## Purpose

Specialized planning guidance for healthcare AI systems with focus on medical compliance, scalability, and patient safety throughout the development lifecycle.

## Healthcare AI Planning Framework

### Project Planning Patterns

```python
# ✅ CORRECT: Healthcare AI project planning structure
from dataclasses import dataclass
from typing import List, Dict, Optional, Enum
from datetime import datetime, timedelta

class ComplianceLevel(Enum):
    """Healthcare compliance levels for planning."""
    DEVELOPMENT = "development"
    HIPAA_READY = "hipaa_ready"
    PRODUCTION_READY = "production_ready"
    ENTERPRISE_CERTIFIED = "enterprise_certified"

@dataclass
class HealthcareFeaturePlan:
    """Plan structure for healthcare AI features."""
    feature_name: str
    description: str
    compliance_level: ComplianceLevel
    medical_safety_review: bool
    phi_handling_required: bool
    estimated_effort: timedelta
    dependencies: List[str]
    regulatory_considerations: List[str]
    testing_requirements: List[str]

    def validate_healthcare_readiness(self) -> List[str]:
        """Validate feature plan meets healthcare standards."""
        issues = []

        if self.phi_handling_required and self.compliance_level == ComplianceLevel.DEVELOPMENT:
            issues.append("PHI handling requires HIPAA_READY compliance level minimum")

        if not self.medical_safety_review and "medical" in self.feature_name.lower():
            issues.append("Medical-related features require safety review")

        if self.compliance_level == ComplianceLevel.PRODUCTION_READY and not self.testing_requirements:
            issues.append("Production features require comprehensive testing plan")

        return issues

class HealthcareProjectPlanner:
    """Planning framework for healthcare AI projects."""

    def __init__(self) -> None:
        self.planned_features: List[HealthcareFeaturePlan] = []
        self.compliance_gates: Dict[str, List[str]] = self._setup_compliance_gates()
        self.regulatory_requirements: Dict[str, List[str]] = self._load_regulatory_requirements()

    def plan_healthcare_feature(
        self,
        feature_request: Dict[str, any]
    ) -> HealthcareFeaturePlan:
        """Plan healthcare AI feature with compliance considerations."""

        # Analyze feature for healthcare implications
        compliance_analysis = self._analyze_compliance_requirements(feature_request)

        # Estimate effort with healthcare overhead
        base_effort = self._estimate_base_effort(feature_request)
        healthcare_overhead = self._calculate_healthcare_overhead(compliance_analysis)
        total_effort = base_effort + healthcare_overhead

        # Create comprehensive plan
        feature_plan = HealthcareFeaturePlan(
            feature_name=feature_request["name"],
            description=feature_request["description"],
            compliance_level=compliance_analysis["required_level"],
            medical_safety_review=compliance_analysis["needs_medical_review"],
            phi_handling_required=compliance_analysis["handles_phi"],
            estimated_effort=total_effort,
            dependencies=self._identify_dependencies(feature_request, compliance_analysis),
            regulatory_considerations=compliance_analysis["regulatory_requirements"],
            testing_requirements=self._plan_testing_requirements(compliance_analysis)
        )

        # Validate plan
        validation_issues = feature_plan.validate_healthcare_readiness()
        if validation_issues:
            raise HealthcarePlanningError(f"Feature plan validation failed: {validation_issues}")

        self.planned_features.append(feature_plan)
        return feature_plan
```

### Architecture Planning for Healthcare

```python
# ✅ CORRECT: Healthcare AI architecture planning
class HealthcareArchitecturePlanner:
    """Plan healthcare AI architecture with compliance and scalability."""

    def __init__(self) -> None:
        self.architecture_components: Dict[str, Dict[str, any]] = {}
        self.data_flow_patterns: List[Dict[str, any]] = []
        self.security_requirements: Dict[str, List[str]] = {}

    def plan_healthcare_microservice(
        self,
        service_name: str,
        purpose: str,
        data_sensitivity: str
    ) -> Dict[str, any]:
        """Plan healthcare microservice architecture."""

        # Determine security requirements based on data sensitivity
        security_plan = self._plan_security_requirements(data_sensitivity)

        # Plan scalability requirements
        scalability_plan = self._plan_scalability_requirements(purpose)

        # Plan integration patterns
        integration_plan = self._plan_integration_patterns(service_name, purpose)

        service_architecture = {
            "service_name": service_name,
            "purpose": purpose,
            "data_sensitivity": data_sensitivity,
            "security_requirements": security_plan,
            "scalability_plan": scalability_plan,
            "integration_patterns": integration_plan,
            "compliance_frameworks": self._identify_compliance_frameworks(data_sensitivity),
            "monitoring_requirements": self._plan_monitoring_requirements(data_sensitivity),
            "deployment_strategy": self._plan_deployment_strategy(data_sensitivity)
        }

        self.architecture_components[service_name] = service_architecture
        return service_architecture

    def _plan_security_requirements(self, data_sensitivity: str) -> Dict[str, any]:
        """Plan security requirements based on data sensitivity."""

        security_levels = {
            "public": {
                "encryption_at_rest": False,
                "encryption_in_transit": True,
                "access_controls": "basic",
                "audit_logging": "standard"
            },
            "healthcare_sensitive": {
                "encryption_at_rest": True,
                "encryption_in_transit": True,
                "access_controls": "rbac",
                "audit_logging": "comprehensive",
                "data_minimization": True
            },
            "phi_restricted": {
                "encryption_at_rest": True,
                "encryption_in_transit": True,
                "access_controls": "zero_trust",
                "audit_logging": "hipaa_compliant",
                "data_minimization": True,
                "access_monitoring": "real_time",
                "breach_detection": "automated"
            }
        }

        return security_levels.get(data_sensitivity, security_levels["healthcare_sensitive"])

    def plan_data_flow(
        self,
        source: str,
        destination: str,
        data_type: str
    ) -> Dict[str, any]:
        """Plan healthcare data flow with compliance considerations."""

        data_flow = {
            "source": source,
            "destination": destination,
            "data_type": data_type,
            "encryption_required": self._requires_encryption(data_type),
            "audit_logging": self._requires_audit_logging(data_type),
            "data_validation": self._plan_data_validation(data_type),
            "error_handling": self._plan_error_handling(data_type),
            "performance_requirements": self._plan_performance_requirements(data_type)
        }

        self.data_flow_patterns.append(data_flow)
        return data_flow
```

### Sprint Planning for Healthcare AI

```python
# ✅ CORRECT: Healthcare AI sprint planning
class HealthcareSprintPlanner:
    """Plan healthcare AI development sprints with compliance integration."""

    def __init__(self) -> None:
        self.sprint_capacity: Dict[str, int] = {}
        self.compliance_overhead: float = 0.3  # 30% overhead for healthcare compliance
        self.medical_review_time: timedelta = timedelta(days=2)

    def plan_healthcare_sprint(
        self,
        sprint_duration: timedelta,
        team_capacity: Dict[str, int],
        feature_backlog: List[HealthcareFeaturePlan]
    ) -> Dict[str, any]:
        """Plan sprint with healthcare compliance considerations."""

        # Calculate effective capacity considering healthcare overhead
        effective_capacity = self._calculate_effective_capacity(team_capacity)

        # Prioritize features by healthcare importance
        prioritized_backlog = self._prioritize_healthcare_features(feature_backlog)

        # Plan sprint with compliance gates
        sprint_plan = {
            "sprint_duration": sprint_duration,
            "effective_capacity": effective_capacity,
            "planned_features": [],
            "compliance_activities": [],
            "medical_review_schedule": [],
            "testing_allocation": {},
            "risk_mitigation": []
        }

        remaining_capacity = effective_capacity["development"]

        for feature in prioritized_backlog:
            if self._can_fit_in_sprint(feature, remaining_capacity, sprint_duration):
                # Add feature to sprint
                sprint_plan["planned_features"].append(feature)
                remaining_capacity -= feature.estimated_effort.days

                # Plan compliance activities
                compliance_activities = self._plan_feature_compliance_activities(feature)
                sprint_plan["compliance_activities"].extend(compliance_activities)

                # Schedule medical review if needed
                if feature.medical_safety_review:
                    review_schedule = self._schedule_medical_review(feature, sprint_duration)
                    sprint_plan["medical_review_schedule"].append(review_schedule)

        # Plan testing allocation
        sprint_plan["testing_allocation"] = self._plan_testing_allocation(
            sprint_plan["planned_features"]
        )

        # Identify risks and mitigation strategies
        sprint_plan["risk_mitigation"] = self._identify_sprint_risks(sprint_plan)

        return sprint_plan

    def _prioritize_healthcare_features(
        self,
        features: List[HealthcareFeaturePlan]
    ) -> List[HealthcareFeaturePlan]:
        """Prioritize features by healthcare importance."""

        def healthcare_priority_score(feature: HealthcareFeaturePlan) -> int:
            score = 0

            # Medical safety is highest priority
            if feature.medical_safety_review:
                score += 100

            # PHI handling requires careful sequencing
            if feature.phi_handling_required:
                score += 50

            # Compliance level affects priority
            compliance_scores = {
                ComplianceLevel.PRODUCTION_READY: 40,
                ComplianceLevel.HIPAA_READY: 30,
                ComplianceLevel.DEVELOPMENT: 10
            }
            score += compliance_scores.get(feature.compliance_level, 0)

            # Dependencies affect sequencing
            score -= len(feature.dependencies) * 5

            return score

        return sorted(features, key=healthcare_priority_score, reverse=True)
```

### Risk Planning for Healthcare AI

```python
# ✅ CORRECT: Healthcare AI risk planning
class HealthcareRiskPlanner:
    """Plan and mitigate risks in healthcare AI development."""

    def __init__(self) -> None:
        self.risk_categories = {
            "medical_safety": ["medical_advice_generation", "misdiagnosis_risk", "treatment_interference"],
            "phi_exposure": ["data_breach", "unauthorized_access", "logging_exposure"],
            "compliance_failure": ["hipaa_violation", "audit_failure", "regulatory_non_compliance"],
            "technical_failure": ["system_downtime", "data_corruption", "integration_failure"],
            "operational_risk": ["staff_training_gaps", "workflow_disruption", "vendor_dependency"]
        }

        self.mitigation_strategies: Dict[str, List[str]] = {}

    def assess_project_risks(
        self,
        project_plan: Dict[str, any]
    ) -> Dict[str, any]:
        """Assess healthcare AI project risks comprehensively."""

        risk_assessment = {
            "identified_risks": [],
            "risk_matrix": {},
            "mitigation_plan": {},
            "monitoring_plan": {},
            "contingency_plans": {}
        }

        # Assess risks by category
        for category, risk_types in self.risk_categories.items():
            category_risks = self._assess_category_risks(project_plan, category, risk_types)
            risk_assessment["identified_risks"].extend(category_risks)

        # Create risk matrix (probability vs impact)
        risk_assessment["risk_matrix"] = self._create_risk_matrix(
            risk_assessment["identified_risks"]
        )

        # Plan mitigation strategies
        risk_assessment["mitigation_plan"] = self._plan_risk_mitigation(
            risk_assessment["identified_risks"]
        )

        # Plan risk monitoring
        risk_assessment["monitoring_plan"] = self._plan_risk_monitoring(
            risk_assessment["identified_risks"]
        )

        # Plan contingency responses
        risk_assessment["contingency_plans"] = self._plan_contingency_responses(
            risk_assessment["identified_risks"]
        )

        return risk_assessment

    def _assess_category_risks(
        self,
        project_plan: Dict[str, any],
        category: str,
        risk_types: List[str]
    ) -> List[Dict[str, any]]:
        """Assess risks for a specific category."""

        identified_risks = []

        for risk_type in risk_types:
            risk_probability = self._calculate_risk_probability(project_plan, risk_type)
            risk_impact = self._calculate_risk_impact(project_plan, risk_type)

            if risk_probability > 0.1 or risk_impact > 0.3:  # Threshold for concern
                risk = {
                    "category": category,
                    "type": risk_type,
                    "probability": risk_probability,
                    "impact": risk_impact,
                    "risk_score": risk_probability * risk_impact,
                    "description": self._get_risk_description(risk_type),
                    "potential_consequences": self._get_risk_consequences(risk_type)
                }
                identified_risks.append(risk)

        return identified_risks
```

### Planning Documentation Templates

```python
# ✅ CORRECT: Healthcare AI planning documentation
class HealthcarePlanningDocuments:
    """Generate planning documents for healthcare AI projects."""

    @staticmethod
    def generate_feature_planning_template() -> str:
        """Generate template for healthcare feature planning."""
        return """
# Healthcare AI Feature Planning Document

## Feature Overview
- **Feature Name**: [Name]
- **Description**: [Detailed description]
- **Business Value**: [Healthcare value proposition]
- **Compliance Level**: [DEVELOPMENT/HIPAA_READY/PRODUCTION_READY]

## Healthcare Considerations
- **PHI Handling**: [Yes/No - describe PHI requirements]
- **Medical Safety Review**: [Required/Not Required]
- **Regulatory Compliance**: [List applicable regulations]
- **Audit Requirements**: [Describe audit logging needs]

## Technical Planning
- **Architecture Approach**: [Technical approach]
- **Dependencies**: [List all dependencies]
- **Testing Strategy**: [Comprehensive testing plan]
- **Performance Requirements**: [Performance criteria]

## Risk Assessment
- **Identified Risks**: [List potential risks]
- **Mitigation Strategies**: [Risk mitigation plans]
- **Contingency Plans**: [Backup approaches]

## Implementation Plan
- **Development Phases**: [Break down into phases]
- **Timeline**: [Realistic timeline with healthcare overhead]
- **Resource Requirements**: [Team and infrastructure needs]
- **Success Criteria**: [Clear acceptance criteria]

## Medical Disclaimer
This feature provides administrative and technical support only.
It does not provide medical advice or make clinical decisions.
All medical interpretations require qualified healthcare professionals.
        """

    @staticmethod
    def generate_architecture_planning_template() -> str:
        """Generate template for healthcare architecture planning."""
        return """
# Healthcare AI Architecture Planning Document

## System Overview
- **System Purpose**: [Healthcare function]
- **Data Sensitivity Level**: [PUBLIC/HEALTHCARE_SENSITIVE/PHI_RESTRICTED]
- **Compliance Requirements**: [HIPAA, state regulations, etc.]

## Architecture Components
- **Core Services**: [List microservices]
- **Data Storage**: [Database and storage patterns]
- **Integration Points**: [EHR, external systems]
- **Security Layer**: [Authentication, authorization, encryption]

## Data Flow Design
- **Data Sources**: [Patient data, clinical systems]
- **Processing Pipeline**: [Data transformation steps]
- **Output Destinations**: [Reports, dashboards, EHR]
- **Audit Trail**: [Comprehensive logging strategy]

## Security Architecture
- **Encryption Strategy**: [At rest and in transit]
- **Access Controls**: [RBAC, zero trust principles]
- **Network Security**: [VPN, firewalls, segmentation]
- **Monitoring**: [Security monitoring and alerting]

## Scalability Planning
- **Performance Requirements**: [Response times, throughput]
- **Scaling Strategy**: [Horizontal/vertical scaling]
- **Resource Planning**: [Infrastructure requirements]
- **Disaster Recovery**: [Backup and recovery procedures]

## Compliance Integration
- **HIPAA Compliance**: [Technical safeguards]
- **Audit Logging**: [Comprehensive audit strategy]
- **Data Governance**: [Data lifecycle management]
- **Risk Management**: [Security risk mitigation]
        """
```

## Planning Best Practices for Healthcare AI

### Modern Development Integration

```python
# ✅ CORRECT: Modern tools integration in planning
class ModernHealthcarePlanning:
    """Integrate modern development tools into healthcare planning."""

    def plan_with_modern_tools(self, project_requirements: Dict[str, any]) -> Dict[str, any]:
        """Plan project with modern development tools integration."""

        development_plan = {
            "python_modernization": {
                "ruff_integration": "Ultra-fast linting and formatting",
                "mypy_configuration": "Comprehensive type checking",
                "pre_commit_hooks": "Automated compliance validation",
                "performance_targets": "10-100x faster development cycles"
            },
            "ai_development_workflow": {
                "copilot_instructions": "Context-aware AI assistance",
                "specialized_instructions": "Task and domain-specific guidance",
                "automated_code_review": "Healthcare compliance validation",
                "ai_pair_programming": "Enhanced development productivity"
            },
            "healthcare_compliance_automation": {
                "phi_detection": "Automated PHI exposure prevention",
                "hipaa_validation": "Continuous compliance checking",
                "audit_automation": "Comprehensive audit logging",
                "security_scanning": "Automated security validation"
            },
            "quality_assurance": {
                "synthetic_data_testing": "Safe testing with realistic data",
                "compliance_testing": "Automated compliance validation",
                "performance_testing": "Healthcare-specific load testing",
                "security_testing": "Penetration testing and vulnerability assessment"
            }
        }

        return development_plan
```

### Planning Checklist Template

```markdown
## Healthcare AI Planning Checklist

### Pre-Planning Phase

- [ ] Medical safety requirements identified
- [ ] PHI handling requirements documented
- [ ] Compliance frameworks identified (HIPAA, state regulations)
- [ ] Regulatory review completed
- [ ] Risk assessment conducted

### Feature Planning Phase

- [ ] Feature compliance level determined
- [ ] Medical review requirements identified
- [ ] Testing strategy planned
- [ ] Dependencies mapped
- [ ] Success criteria defined

### Architecture Planning Phase

- [ ] Security architecture designed
- [ ] Data flow patterns planned
- [ ] Integration points identified
- [ ] Scalability requirements documented
- [ ] Disaster recovery planned

### Implementation Planning Phase

- [ ] Sprint capacity calculated (with healthcare overhead)
- [ ] Compliance activities scheduled
- [ ] Medical review timeline planned
- [ ] Testing phases scheduled
- [ ] Risk mitigation strategies planned

### Modern Development Integration

- [ ] Ruff configuration planned for ultra-fast development
- [ ] MyPy integration for healthcare type safety
- [ ] AI instruction files configured for enhanced assistance
- [ ] Pre-commit hooks with healthcare compliance validation
- [ ] Automated testing with synthetic healthcare data
```

Remember: Healthcare AI planning requires balancing development velocity with strict medical compliance, patient safety, and regulatory requirements. Always plan for healthcare-specific overhead and compliance validation throughout the development lifecycle.
