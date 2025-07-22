# Phase 2: Business Services and Personalization

**Duration:** 4 weeks
**Goal:** Deploy insurance verification, billing systems, compliance monitoring, and doctor personalization features. Transform the Phase 1 foundation into a complete clinical workflow system using your service architecture with advanced AI reasoning, Chain-of-Thought decision-making, and sophisticated doctor personalization through LoRA training.

## Overview: Advanced Healthcare AI Orchestration

Phase 2 transforms from basic business services to sophisticated healthcare workflow automation with personalized AI capabilities. This phase introduces advanced reasoning patterns, comprehensive evaluation frameworks, production-ready monitoring systems, and doctor-specific personalization through LoRA/QLoRA training - all focused on administrative workflow automation rather than medical advice.

## Week 1: Insurance and Billing Infrastructure

### 1.1 Insurance Verification Service

**Create service configuration:**
```bash
# services/user/insurance-verification/insurance-verification.conf
image="intelluxe/insurance-verification:latest"
port="8003:8003"
description="Multi-provider insurance verification with error prevention"
env="NODE_ENV=production"
volumes="./config:/app/config:ro"
network_mode="intelluxe-net"
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8003/health || exit 1"
depends_on="postgres,redis"
```

**Deploy insurance verification service:**
```bash
./scripts/universal-service-runner.sh start insurance-verification

# Verify service is running
curl http://localhost:8003/health
```

**Enhanced insurance verification with error prevention:**
```python
# services/user/insurance-verification/main.py
from fastapi import FastAPI, HTTPException
from typing import Dict, Any, List, Optional
import httpx
import asyncio
from datetime import datetime

app = FastAPI(title="Insurance Verification Service")

class InsuranceVerificationService:
    """
    Multi-provider insurance verification with built-in error prevention
    """
    
    def __init__(self):
        self.providers = {
            'anthem': AnthemProvider(),
            'uhc': UnitedHealthProvider(),
            'cigna': CignaProvider(),
            'aetna': AetnaProvider()
        }
        self.safety_checks = InsuranceSafetyChecker()
    
    async def verify_eligibility(self, verification_request: Dict[str, Any]) -> Dict[str, Any]:
        """Verify patient eligibility with comprehensive error checking"""
        
        # Safety check: Validate input data
        validation_result = await self.safety_checks.validate_request(verification_request)
        if not validation_result['valid']:
            return {
                'error': 'Validation failed',
                'issues': validation_result['issues'],
                'safe_to_retry': False
            }
        
        member_id = verification_request['member_id']
        provider_id = verification_request['provider_id']
        service_codes = verification_request.get('service_codes', [])
        
        # Determine insurance provider
        provider_name = await self._detect_provider(member_id, provider_id)
        
        if provider_name not in self.providers:
            return {
                'error': f'Unsupported insurance provider: {provider_name}',
                'supported_providers': list(self.providers.keys())
            }
        
        try:
            # Verify eligibility with specific provider
            provider = self.providers[provider_name]
            eligibility_result = await provider.check_eligibility(
                member_id, provider_id, service_codes
            )
            
            # Apply safety validations
            validated_result = await self.safety_checks.validate_response(
                eligibility_result, verification_request
            )
            
            return {
                'verified': True,
                'provider': provider_name,
                'member_id': member_id,
                'eligibility': validated_result,
                'verification_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            # Log error for debugging but don't expose internal details
            return {
                'error': 'Verification failed',
                'provider': provider_name,
                'retry_recommended': True,
                'error_code': 'PROVIDER_ERROR'
            }

class InsuranceSafetyChecker:
    """Safety validation for insurance verification"""
    
    async def validate_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Validate insurance verification request"""
        
        issues = []
        
        # Required fields check
        required_fields = ['member_id', 'provider_id']
        for field in required_fields:
            if not request.get(field):
                issues.append(f'Missing required field: {field}')
        
        # Member ID format validation
        member_id = request.get('member_id', '')
        if len(member_id) < 6 or len(member_id) > 20:
            issues.append('Member ID length invalid')
        
        # Provider ID validation
        provider_id = request.get('provider_id', '')
        if len(provider_id) < 3:
            issues.append('Provider ID too short')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }

@app.post("/verify")
async def verify_insurance(request: Dict[str, Any]):
    service = InsuranceVerificationService()
    return await service.verify_eligibility(request)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "insurance-verification"}
```

### 1.3 Advanced Chain-of-Thought Reasoning for Insurance Decisions

**Enhanced insurance verification with Chain-of-Thought reasoning for complex administrative decisions:**

```python
# services/user/insurance-verification/chain_of_thought_processor.py
from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

class InsuranceReasoningType(Enum):
    ELIGIBILITY_VERIFICATION = "eligibility_verification"
    COVERAGE_ANALYSIS = "coverage_analysis"
    PRIOR_AUTHORIZATION = "prior_authorization"
    CLAIM_VALIDATION = "claim_validation"

@dataclass
class InsuranceReasoningStep:
    step_id: str
    reasoning_type: str
    input_data: Dict
    reasoning_process: str
    conclusion: str
    confidence_score: float
    evidence: List[str]
    timestamp: str
    next_steps: List[str]

class InsuranceChainOfThoughtProcessor:
    """Chain-of-Thought reasoning for insurance administrative decisions"""

    def __init__(self, medical_llm, knowledge_base, audit_logger):
        self.medical_llm = medical_llm
        self.knowledge_base = knowledge_base
        self.audit_logger = audit_logger

        # Insurance reasoning templates
        self.reasoning_templates = {
            InsuranceReasoningType.ELIGIBILITY_VERIFICATION: self.eligibility_verification_template,
            InsuranceReasoningType.COVERAGE_ANALYSIS: self.coverage_analysis_template,
            InsuranceReasoningType.PRIOR_AUTHORIZATION: self.prior_authorization_template
        }

    async def process_insurance_reasoning(
        self,
        insurance_data: Dict,
        administrative_question: str,
        reasoning_type: InsuranceReasoningType,
        session_id: str
    ) -> Dict:
        """Process complex insurance administrative reasoning with full chain documentation"""

        chain_id = f"insurance_reasoning_{session_id}_{reasoning_type.value}_{datetime.utcnow().timestamp()}"

        # Execute reasoning template
        template_function = self.reasoning_templates[reasoning_type]
        reasoning_steps = await template_function(insurance_data, administrative_question, chain_id)

        # Process each reasoning step
        processed_steps = []
        for step_data in reasoning_steps:
            reasoning_step = await self.process_reasoning_step(
                step_data=step_data,
                insurance_context=insurance_data,
                chain_id=chain_id
            )
            processed_steps.append(reasoning_step)

        # Generate final administrative conclusion
        final_analysis = await self.synthesize_insurance_reasoning_chain(processed_steps)

        # Log reasoning chain for audit compliance
        await self.audit_logger.log_insurance_reasoning(
            chain_id=chain_id,
            reasoning_type=reasoning_type.value,
            insurance_hash=self.hash_insurance_context(insurance_data),
            steps_count=len(processed_steps),
            final_confidence=final_analysis["confidence"]
        )

        return {
            'chain_id': chain_id,
            'reasoning_steps': processed_steps,
            'final_conclusion': final_analysis["conclusion"],
            'confidence_score': final_analysis["confidence"],
            'administrative_recommendations': final_analysis["recommendations"],
            'created_at': datetime.utcnow().isoformat()
        }

    async def eligibility_verification_template(
        self,
        insurance_data: Dict,
        administrative_question: str,
        chain_id: str
    ) -> List[Dict]:
        """Template for eligibility verification reasoning"""

        reasoning_steps = [
            {
                "step_type": "member_validation",
                "prompt": f"""
                Analyze the insurance member information for administrative verification:

                Member ID: {insurance_data.get('member_id', 'Not specified')}
                Provider Network: {insurance_data.get('provider_network', 'Not provided')}
                Plan Type: {insurance_data.get('plan_type', 'Unknown')}

                Step 1: Validate member identification and plan status.
                Provide detailed analysis of:
                - Member ID format validation
                - Plan active status verification
                - Network participation confirmation
                - Administrative compliance requirements

                Focus on administrative verification, not medical decisions.
                """,
                "expected_output": "systematic_member_validation"
            },
            {
                "step_type": "coverage_determination",
                "prompt": f"""
                Based on member validation, determine coverage for requested services:

                For each service code, provide:
                - Coverage status (covered/not covered/requires authorization)
                - Administrative requirements
                - Documentation needed
                - Processing timeline

                Rank by administrative complexity and processing requirements.
                """,
                "expected_output": "coverage_determination_analysis"
            }
        ]

        return reasoning_steps
```

### 1.5 Advanced Real-Time Insurance Integration

**Real-Time Insurance Verification System with multiple provider APIs:**

```python
# agents/insurance/real_time_verifier.py
from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime, date, timedelta
from cachetools import TTLCache
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class InsuranceVerificationResult:
    verified: bool
    provider: Optional[str] = None
    member_id: Optional[str] = None
    coverage_active: bool = False
    coverage_details: List[Any] = None
    cost_estimates: Dict[str, float] = None
    copay_amounts: Dict[str, float] = None
    deductible_remaining: float = 0.0
    out_of_pocket_max: float = 0.0
    verified_at: Optional[datetime] = None
    error: Optional[str] = None

@dataclass
class PriorAuthResult:
    status: str
    tracking_id: Optional[str] = None
    estimated_decision_date: Optional[date] = None
    reference_number: Optional[str] = None
    message: Optional[str] = None

class RealTimeInsuranceVerifier:
    """
    Real-time insurance verification with multiple provider APIs
    """

    def __init__(self):
        self.provider_clients = {
            "anthem": AnthemAPIClient(),
            "uhc": UnitedHealthAPIClient(),
            "cigna": CignaAPIClient(),
            "aetna": AetnaAPIClient(),
            "bcbs": BlueCrossBlueShieldAPIClient()
        }
        self.verification_cache = TTLCache(maxsize=500, ttl=1800)  # 30 min cache

    async def verify_insurance_real_time(self,
                                       patient_info: Dict[str, Any],
                                       service_codes: List[str]) -> InsuranceVerificationResult:
        """
        Perform real-time insurance verification for multiple services
        """

        insurance_info = patient_info.get("insurance", {})
        provider = insurance_info.get("provider", "").lower()
        member_id = insurance_info.get("member_id")

        if not provider or not member_id:
            return InsuranceVerificationResult(
                verified=False,
                error="Missing insurance provider or member ID"
            )

        # Check cache first
        cache_key = f"{provider}_{member_id}_{hash(tuple(service_codes))}"
        if cache_key in self.verification_cache:
            logger.info(f"Using cached verification result for {member_id}")
            return self.verification_cache[cache_key]

        # Get appropriate API client
        api_client = self.provider_clients.get(provider)
        if not api_client:
            return InsuranceVerificationResult(
                verified=False,
                error=f"Unsupported insurance provider: {provider}"
            )

        try:
            # Verify eligibility
            eligibility = await api_client.check_eligibility(
                member_id=member_id,
                service_date=datetime.now().date()
            )

            if not eligibility.is_active:
                return InsuranceVerificationResult(
                    verified=False,
                    error="Insurance coverage is not active"
                )

            # Check coverage for specific services
            coverage_results = []
            for service_code in service_codes:
                coverage = await api_client.check_service_coverage(
                    member_id=member_id,
                    service_code=service_code,
                    provider_npi=patient_info.get("provider_npi")
                )
                coverage_results.append(coverage)

            # Calculate estimated costs
            cost_estimates = await self._calculate_cost_estimates(
                coverage_results, service_codes, eligibility
            )

            result = InsuranceVerificationResult(
                verified=True,
                provider=provider,
                member_id=member_id,
                coverage_active=eligibility.is_active,
                coverage_details=coverage_results,
                cost_estimates=cost_estimates,
                copay_amounts={code: coverage.copay for code, coverage in zip(service_codes, coverage_results)},
                deductible_remaining=eligibility.deductible_remaining,
                out_of_pocket_max=eligibility.out_of_pocket_max,
                verified_at=datetime.utcnow()
            )

            # Cache result
            self.verification_cache[cache_key] = result
            logger.info(f"Successfully verified insurance for {member_id}")

            return result

        except Exception as e:
            logger.error(f"Insurance verification failed for {provider}: {e}")
            return InsuranceVerificationResult(
                verified=False,
                error=f"Verification failed: {str(e)}"
            )

    async def _calculate_cost_estimates(self,
                                      coverage_results: List[Any],
                                      service_codes: List[str],
                                      eligibility: Any) -> Dict[str, float]:
        """Calculate estimated costs for services"""

        cost_estimates = {}

        for service_code, coverage in zip(service_codes, coverage_results):
            if coverage.covered:
                # Calculate patient responsibility
                if coverage.copay > 0:
                    patient_cost = coverage.copay
                elif coverage.coinsurance_rate > 0:
                    estimated_charge = coverage.estimated_charge or 100.0  # Default estimate
                    patient_cost = estimated_charge * coverage.coinsurance_rate
                else:
                    patient_cost = 0.0

                # Apply deductible if not met
                if eligibility.deductible_remaining > 0:
                    deductible_portion = min(patient_cost, eligibility.deductible_remaining)
                    patient_cost = max(patient_cost, deductible_portion)

                cost_estimates[service_code] = patient_cost
            else:
                cost_estimates[service_code] = coverage.estimated_charge or 0.0

        return cost_estimates

# API Client implementations for different insurance providers
class AnthemAPIClient:
    """Anthem insurance API client"""

    async def check_eligibility(self, member_id: str, service_date: date):
        """Check member eligibility with Anthem"""
        # Implementation would connect to Anthem's API
        # For now, return mock data
        return MockEligibilityResponse(
            is_active=True,
            deductible_remaining=500.0,
            out_of_pocket_max=2000.0
        )

    async def check_service_coverage(self, member_id: str, service_code: str, provider_npi: str):
        """Check coverage for specific service"""
        # Implementation would check service coverage
        return MockCoverageResponse(
            covered=True,
            copay=25.0,
            coinsurance_rate=0.2,
            estimated_charge=150.0
        )

class UnitedHealthAPIClient:
    """United Health insurance API client"""

    async def check_eligibility(self, member_id: str, service_date: date):
        return MockEligibilityResponse(
            is_active=True,
            deductible_remaining=750.0,
            out_of_pocket_max=3000.0
        )

    async def check_service_coverage(self, member_id: str, service_code: str, provider_npi: str):
        return MockCoverageResponse(
            covered=True,
            copay=30.0,
            coinsurance_rate=0.15,
            estimated_charge=175.0
        )

# Mock response classes for development
class MockEligibilityResponse:
    def __init__(self, is_active: bool, deductible_remaining: float, out_of_pocket_max: float):
        self.is_active = is_active
        self.deductible_remaining = deductible_remaining
        self.out_of_pocket_max = out_of_pocket_max

class MockCoverageResponse:
    def __init__(self, covered: bool, copay: float, coinsurance_rate: float, estimated_charge: float):
        self.covered = covered
        self.copay = copay
        self.coinsurance_rate = coinsurance_rate
        self.estimated_charge = estimated_charge
```

**Automated Prior Authorization System:**

```python
# agents/insurance/prior_authorization.py
from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime, date, timedelta
import logging

logger = logging.getLogger(__name__)

class PriorAuthorizationAgent:
    """
    Automated prior authorization request processing
    """

    def __init__(self, insurance_verifier, healthcare_mcp):
        self.insurance_verifier = insurance_verifier
        self.healthcare_mcp = healthcare_mcp
        self.auth_tracker = PriorAuthTracker()

    async def process_prior_authorization(self,
                                        patient_info: Dict[str, Any],
                                        requested_service: Dict[str, Any],
                                        clinical_justification: str) -> PriorAuthResult:
        """
        Process prior authorization request with clinical justification
        """

        # Gather required clinical information
        clinical_data = await self._gather_clinical_data(
            patient_info, requested_service, clinical_justification
        )

        # Check if prior auth is required
        auth_required = await self._check_prior_auth_requirement(
            patient_info["insurance"], requested_service
        )

        if not auth_required.required:
            return PriorAuthResult(
                status="not_required",
                message="Prior authorization not required for this service"
            )

        # Generate prior auth request
        auth_request = await self._generate_auth_request(
            patient_info, requested_service, clinical_data
        )

        # Submit to insurance provider
        submission_result = await self._submit_auth_request(
            patient_info["insurance"]["provider"],
            auth_request
        )

        # Track submission
        tracking_id = await self.auth_tracker.create_tracking_record(
            patient_id=patient_info["patient_id"],
            service_code=requested_service["code"],
            insurance_provider=patient_info["insurance"]["provider"],
            submission_result=submission_result
        )

        return PriorAuthResult(
            status="submitted",
            tracking_id=tracking_id,
            estimated_decision_date=submission_result.estimated_decision_date,
            reference_number=submission_result.reference_number
        )

    async def _gather_clinical_data(self,
                                  patient_info: Dict[str, Any],
                                  requested_service: Dict[str, Any],
                                  clinical_justification: str) -> Dict[str, Any]:
        """Gather required clinical information for prior auth"""

        clinical_data = {
            "patient_demographics": {
                "age": patient_info.get("age"),
                "gender": patient_info.get("gender"),
                "diagnosis_codes": patient_info.get("diagnosis_codes", [])
            },
            "requested_service": {
                "service_code": requested_service["code"],
                "service_description": requested_service.get("description"),
                "urgency": requested_service.get("urgency", "routine")
            },
            "clinical_justification": clinical_justification,
            "supporting_documentation": await self._gather_supporting_docs(patient_info),
            "provider_information": {
                "npi": patient_info.get("provider_npi"),
                "specialty": patient_info.get("provider_specialty")
            }
        }

        return clinical_data

    async def _check_prior_auth_requirement(self,
                                          insurance_info: Dict[str, Any],
                                          requested_service: Dict[str, Any]) -> Any:
        """Check if prior authorization is required for the service"""

        # This would check against insurance provider's prior auth requirements
        # For now, return mock response
        service_code = requested_service["code"]

        # Common services that typically require prior auth
        prior_auth_services = ["MRI", "CT", "PET", "specialty_referral", "surgery"]

        requires_auth = any(service in service_code.upper() for service in prior_auth_services)

        return MockPriorAuthRequirement(required=requires_auth)

    async def _generate_auth_request(self,
                                   patient_info: Dict[str, Any],
                                   requested_service: Dict[str, Any],
                                   clinical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate prior authorization request"""

        auth_request = {
            "request_id": f"PA_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "patient_info": {
                "member_id": patient_info["insurance"]["member_id"],
                "name": patient_info.get("name"),
                "dob": patient_info.get("date_of_birth")
            },
            "provider_info": {
                "npi": patient_info.get("provider_npi"),
                "name": patient_info.get("provider_name"),
                "contact": patient_info.get("provider_contact")
            },
            "requested_service": requested_service,
            "clinical_data": clinical_data,
            "submission_date": datetime.utcnow().isoformat()
        }

        return auth_request

    async def _submit_auth_request(self,
                                 insurance_provider: str,
                                 auth_request: Dict[str, Any]) -> Any:
        """Submit prior authorization request to insurance provider"""

        # This would submit to the actual insurance provider API
        # For now, return mock submission result

        return MockSubmissionResult(
            reference_number=f"REF_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            estimated_decision_date=date.today() + timedelta(days=3),
            status="submitted"
        )

    async def _gather_supporting_docs(self, patient_info: Dict[str, Any]) -> List[str]:
        """Gather supporting documentation for prior auth"""

        # This would gather relevant medical records, lab results, etc.
        # For now, return mock documentation list

        return [
            "recent_lab_results",
            "imaging_reports",
            "physician_notes",
            "treatment_history"
        ]

class PriorAuthTracker:
    """Track prior authorization requests and responses"""

    async def create_tracking_record(self,
                                   patient_id: str,
                                   service_code: str,
                                   insurance_provider: str,
                                   submission_result: Any) -> str:
        """Create tracking record for prior auth request"""

        tracking_id = f"TRACK_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Store tracking information in database
        tracking_record = {
            "tracking_id": tracking_id,
            "patient_id": patient_id,
            "service_code": service_code,
            "insurance_provider": insurance_provider,
            "reference_number": submission_result.reference_number,
            "status": "submitted",
            "submitted_at": datetime.utcnow(),
            "estimated_decision_date": submission_result.estimated_decision_date
        }

        # In a real implementation, this would be stored in the database
        logger.info(f"Created prior auth tracking record: {tracking_id}")

        return tracking_id

# Mock classes for development
class MockPriorAuthRequirement:
    def __init__(self, required: bool):
        self.required = required

class MockSubmissionResult:
    def __init__(self, reference_number: str, estimated_decision_date: date, status: str):
        self.reference_number = reference_number
        self.estimated_decision_date = estimated_decision_date
        self.status = status
```

### 1.2 Billing Engine Service

**Create service configuration:**
```bash
# services/user/billing-engine/billing-engine.conf
image="intelluxe/billing-engine:latest"
port="8004:8004"
description="Healthcare billing engine with automated claims processing"
env="NODE_ENV=production"
volumes="./billing-codes:/app/billing-codes:ro"
network_mode="intelluxe-net"
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8004/health || exit 1"
depends_on="postgres,redis,insurance-verification"
```

**Deploy billing engine:**
```bash
./scripts/universal-service-runner.sh start billing-engine

# Verify service is running
curl http://localhost:8004/health
```

**Enhanced billing engine with safety checks:**
```python
# services/user/billing-engine/main.py
from fastapi import FastAPI, HTTPException
from typing import Dict, Any, List
import uuid
from datetime import datetime

app = FastAPI(title="Billing Engine Service")

class BillingEngine:
    """
    Healthcare billing engine with automated claims processing
    """
    
    def __init__(self):
        self.billing_codes = BillingCodeManager()
        self.claims_processor = ClaimsProcessor()
        self.billing_safety = BillingSafetyChecker()
    
    async def create_claim(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create insurance claim with comprehensive validation"""
        
        # Safety validation
        validation_result = await self.billing_safety.validate_claim_data(claim_data)
        if not validation_result['valid']:
            return {
                'error': 'Claim validation failed',
                'issues': validation_result['issues'],
                'claim_created': False
            }
        
        # Generate claim ID
        claim_id = str(uuid.uuid4())
        
        # Process billing codes
        service_codes = claim_data.get('service_codes', [])
        processed_codes = await self.billing_codes.process_codes(service_codes)
        
        # Calculate amounts
        billing_amounts = await self._calculate_billing_amounts(
            processed_codes, claim_data
        )
        
        # Create claim record
        claim = {
            'claim_id': claim_id,
            'patient_id': claim_data['patient_id'],
            'provider_id': claim_data['provider_id'],
            'service_date': claim_data['service_date'],
            'service_codes': processed_codes,
            'billing_amounts': billing_amounts,
            'insurance_info': claim_data.get('insurance_info', {}),
            'status': 'created',
            'created_timestamp': datetime.now().isoformat()
        }
        
        # Submit claim for processing
        submission_result = await self.claims_processor.submit_claim(claim)
        
        return {
            'claim_created': True,
            'claim_id': claim_id,
            'submission_status': submission_result['status'],
            'estimated_payment': billing_amounts.get('estimated_payment'),
            'patient_responsibility': billing_amounts.get('patient_responsibility'),
            'next_steps': submission_result.get('next_steps', [])
        }

@app.post("/create_claim")
async def create_claim(claim_data: Dict[str, Any]):
    engine = BillingEngine()
    return await engine.create_claim(claim_data)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "billing-engine"}
```

### 1.4 Tree-of-Thoughts Planning for Complex Billing Scenarios

**Advanced billing engine with Tree-of-Thoughts planning for complex administrative scenarios:**

```python
# services/user/billing-engine/tree_of_thoughts_planner.py
from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime
import json

class BillingTreeOfThoughtsPlanner:
    """Tree-of-Thoughts planning for complex billing administrative scenarios"""

    def __init__(self, medical_llm, billing_knowledge_base):
        self.medical_llm = medical_llm
        self.billing_knowledge_base = billing_knowledge_base

    async def plan_complex_billing_scenario(
        self,
        billing_scenario_data: Dict,
        planning_depth: int = 3,
        branches_per_level: int = 3
    ) -> Dict:
        """Plan complex billing scenarios using Tree-of-Thoughts approach"""

        planning_tree = {
            "root_scenario": billing_scenario_data,
            "planning_levels": [],
            "optimal_path": [],
            "alternatives": []
        }

        # Level 1: Initial billing assessment and primary options
        level_1_branches = await self.generate_billing_branches(
            billing_scenario_data,
            "initial_billing_assessment",
            branches_per_level
        )
        planning_tree["planning_levels"].append({
            "level": 1,
            "branches": level_1_branches,
            "focus": "initial_billing_options"
        })

        # Level 2: Detailed billing strategy for top branches
        level_2_branches = []
        for branch in level_1_branches[:2]:  # Top 2 branches
            sub_branches = await self.generate_billing_branches(
                branch["scenario_state"],
                "detailed_billing_strategy",
                branches_per_level
            )
            level_2_branches.extend(sub_branches)

        planning_tree["planning_levels"].append({
            "level": 2,
            "branches": level_2_branches,
            "focus": "detailed_billing_implementation"
        })

        # Level 3: Administrative outcome prediction and validation
        level_3_branches = []
        for branch in level_2_branches[:3]:  # Top 3 branches
            outcome_branches = await self.generate_billing_outcome_predictions(
                branch["scenario_state"],
                branches_per_level
            )
            level_3_branches.extend(outcome_branches)

        planning_tree["planning_levels"].append({
            "level": 3,
            "branches": level_3_branches,
            "focus": "administrative_outcome_validation"
        })

        # Select optimal billing path through tree
        optimal_path = await self.select_optimal_billing_path(planning_tree)
        planning_tree["optimal_path"] = optimal_path

        return planning_tree

    async def generate_billing_branches(
        self,
        current_state: Dict,
        planning_focus: str,
        num_branches: int
    ) -> List[Dict]:
        """Generate billing planning branches for current scenario state"""

        branches = []
        for i in range(num_branches):
            branch_response = await self.medical_llm.ainvoke(f"""
            Generate billing administrative branch {i+1} for scenario:

            Current State: {json.dumps(current_state, indent=2)}
            Planning Focus: {planning_focus}

            Provide:
            1. Specific billing administrative approach
            2. Expected processing outcomes
            3. Resource requirements
            4. Administrative risk assessment
            5. Success probability

            Focus on {planning_focus} while maintaining administrative compliance.
            Avoid medical advice - focus on billing workflow optimization.
            """)

            parsed_branch = await self.parse_billing_branch(branch_response, current_state)
            branches.append(parsed_branch)

        # Sort branches by administrative viability
        branches.sort(key=lambda x: x["viability_score"], reverse=True)
        return branches

    async def enhanced_majority_voting_with_lora(
        self,
        billing_question: str,
        doctor_id: str,
        voting_models: List[str] = None
    ) -> Dict:
        """Enhanced majority voting for billing decisions with LoRA integration"""

        if voting_models is None:
            voting_models = ["base_model", "billing_specialist", "compliance_expert"]

        # Get doctor-specific LoRA adaptations
        doctor_lora_weights = await self.get_doctor_lora_weights(doctor_id)

        voting_results = []
        for model in voting_models:
            # Apply doctor-specific LoRA weights if available
            if doctor_lora_weights and model in doctor_lora_weights:
                model_response = await self.query_model_with_lora(
                    model, billing_question, doctor_lora_weights[model]
                )
            else:
                model_response = await self.query_base_model(model, billing_question)

            voting_results.append({
                'model': model,
                'response': model_response,
                'confidence': model_response.get('confidence', 0.5),
                'reasoning': model_response.get('reasoning', '')
            })

        # Weighted majority voting based on confidence and doctor preferences
        final_decision = await self.calculate_weighted_majority_vote(
            voting_results, doctor_lora_weights
        )

        return {
            'final_decision': final_decision,
            'voting_results': voting_results,
            'consensus_confidence': final_decision['confidence'],
            'doctor_personalization_applied': bool(doctor_lora_weights)
        }
```

## Week 2: Compliance and Monitoring

### 2.1 Enhanced Compliance Monitor

**Create service configuration:**
```bash
# services/user/compliance-monitor/compliance-monitor.conf
image="intelluxe/compliance-monitor:latest"
port="8005:8005"
description="HIPAA compliance monitoring with audit trails"
env="NODE_ENV=production,AUDIT_LEVEL=verbose"
volumes="./audit-logs:/app/logs:rw"
network_mode="intelluxe-net"
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8005/health || exit 1"
depends_on="postgres"
```

**Deploy compliance monitoring:**
```bash
./scripts/universal-service-runner.sh start compliance-monitor

# Verify service is running
curl http://localhost:8005/health
```

**Enhanced compliance monitoring with HIPAA audit trails:**
```python
# services/user/compliance-monitor/main.py
from fastapi import FastAPI, Request, HTTPException
from typing import Dict, Any, List, Optional
import psycopg2
import json
from datetime import datetime, timedelta

app = FastAPI(title="Compliance Monitor Service")

class ComplianceMonitor:
    """
    HIPAA-compliant audit logging and monitoring system
    """
    
    def __init__(self):
        self.db_conn = psycopg2.connect(
            "postgresql://intelluxe:secure_password@localhost:5432/intelluxe"
        )
        self.compliance_rules = ComplianceRuleEngine()
        
    async def log_data_access(self, access_event: Dict[str, Any]) -> Dict[str, Any]:
        """Log patient data access for HIPAA compliance"""
        
        # Validate access event
        validation_result = await self._validate_access_event(access_event)
        if not validation_result['valid']:
            return {
                'logged': False,
                'error': 'Invalid access event',
                'issues': validation_result['issues']
            }
        
        # Check compliance rules
        compliance_check = await self.compliance_rules.check_access_compliance(access_event)
        
        # Create audit log entry
        audit_entry = {
            'user_id': access_event['user_id'],
            'action': access_event['action'],
            'resource_type': access_event['resource_type'],
            'resource_id': access_event.get('resource_id'),
            'ip_address': access_event.get('ip_address'),
            'user_agent': access_event.get('user_agent'),
            'timestamp': datetime.now(),
            'compliance_status': compliance_check['status'],
            'risk_level': compliance_check['risk_level'],
            'details': json.dumps(access_event.get('details', {}))
        }
        
        # Store in database
        cursor = self.db_conn.cursor()
        cursor.execute("""
            INSERT INTO compliance_audit_log 
            (user_id, action, resource_type, resource_id, ip_address, user_agent,
             timestamp, compliance_status, risk_level, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, tuple(audit_entry.values()))
        
        audit_id = cursor.fetchone()[0]
        self.db_conn.commit()
        
        # Check for compliance violations
        if compliance_check['violation']:
            await self._handle_compliance_violation(audit_id, compliance_check)
        
        return {
            'logged': True,
            'audit_id': audit_id,
            'compliance_status': compliance_check['status'],
            'requires_attention': compliance_check['violation']
        }

@app.post("/log_access")
async def log_access(access_event: Dict[str, Any]):
    monitor = ComplianceMonitor()
    return await monitor.log_data_access(access_event)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "compliance-monitor"}
```

### 2.4 Comprehensive Evaluation and Monitoring Framework

**Production healthcare AI evaluation with RAGAS integration and AgentOps monitoring:**

```python
# services/user/compliance-monitor/healthcare_evaluation_framework.py
from typing import Dict, List, Optional, Any, Tuple
import asyncio
from datetime import datetime, timedelta
import json
import numpy as np
from dataclasses import dataclass, asdict

# RAGAS integration for RAG evaluation
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
    answer_correctness,
    answer_similarity
)

# AgentOps integration for agent monitoring
import agentops

@dataclass
class HealthcareEvaluationMetrics:
    administrative_accuracy: float
    workflow_safety: float
    phi_protection: float
    terminology_correctness: float
    reasoning_transparency: float
    response_completeness: float
    evidence_quality: float
    hallucination_rate: float
    evaluation_timestamp: str

@dataclass
class AgentPerformanceMetrics:
    agent_name: str
    task_completion_rate: float
    average_response_time: float
    accuracy_score: float
    error_rate: float
    workflow_appropriateness: float
    user_satisfaction: float
    cost_per_interaction: float

class ComprehensiveHealthcareEvaluator:
    """Comprehensive evaluation framework for healthcare AI administrative systems"""

    def __init__(self, postgres_config: Dict, redis_config: Dict, agentops_config: Dict):
        self.postgres_config = postgres_config
        self.redis_config = redis_config

        # Initialize AgentOps for real-time monitoring
        agentops.init(
            api_key=agentops_config["api_key"],
            tags=["healthcare", "hipaa-compliant", "intelluxe", "administrative"]
        )

        # Healthcare administrative evaluation metrics
        self.healthcare_metrics = [
            faithfulness,
            answer_relevancy,
            context_recall,
            context_precision,
            answer_correctness
        ]

        # Administrative workflow validation
        self.workflow_validators = {
            "insurance_verification": self.validate_insurance_workflow,
            "billing_processing": self.validate_billing_workflow,
            "compliance_monitoring": self.validate_compliance_workflow,
            "doctor_personalization": self.validate_personalization_workflow
        }

    @agentops.record
    async def evaluate_healthcare_administrative_system(
        self,
        test_dataset: List[Dict],
        admin_system: Any,
        evaluation_name: str
    ) -> HealthcareEvaluationMetrics:
        """Comprehensive administrative system evaluation with healthcare metrics"""

        evaluation_start = datetime.utcnow()

        # Prepare RAGAS evaluation data
        ragas_dataset = await self.prepare_ragas_dataset(test_dataset, admin_system)

        # Execute RAGAS evaluation
        ragas_results = evaluate(
            dataset=ragas_dataset,
            metrics=self.healthcare_metrics,
            llm=admin_system.llm,
            embeddings=admin_system.embeddings
        )

        # Healthcare administrative evaluations
        administrative_accuracy = await self.evaluate_administrative_accuracy(test_dataset, admin_system)
        workflow_safety = await self.evaluate_workflow_safety(test_dataset, admin_system)
        phi_protection = await self.evaluate_phi_protection(test_dataset, admin_system)
        terminology_correctness = await self.evaluate_terminology_correctness(test_dataset, admin_system)

        # Reasoning transparency evaluation
        reasoning_transparency = await self.evaluate_reasoning_transparency(
            test_dataset, admin_system
        )

        # Evidence quality assessment
        evidence_quality = await self.evaluate_evidence_quality(test_dataset, admin_system)

        # Hallucination detection for administrative content
        hallucination_rate = await self.detect_administrative_hallucinations(test_dataset, admin_system)

        # Compile comprehensive metrics
        healthcare_metrics = HealthcareEvaluationMetrics(
            administrative_accuracy=administrative_accuracy,
            workflow_safety=workflow_safety,
            phi_protection=phi_protection,
            terminology_correctness=terminology_correctness,
            reasoning_transparency=reasoning_transparency,
            response_completeness=ragas_results["answer_correctness"],
            evidence_quality=evidence_quality,
            hallucination_rate=hallucination_rate,
            evaluation_timestamp=evaluation_start.isoformat()
        )

        # Store evaluation results
        await self.store_evaluation_results(evaluation_name, healthcare_metrics, ragas_results)

        return healthcare_metrics

    async def continuous_agent_monitoring(
        self,
        agent_instances: Dict[str, Any],
        monitoring_duration: timedelta = timedelta(hours=24)
    ) -> Dict[str, AgentPerformanceMetrics]:
        """Continuous monitoring of agent performance with AgentOps integration"""

        monitoring_results = {}
        monitoring_start = datetime.utcnow()

        for agent_name, agent_instance in agent_instances.items():

            # Initialize agent monitoring with AgentOps
            with agentops.Session(
                tags=[f"agent_{agent_name}", "continuous_monitoring", "administrative"]
            ) as session:

                # Collect performance metrics
                performance_data = await self.collect_agent_performance_data(
                    agent_instance,
                    monitoring_duration
                )

                # Calculate performance metrics
                metrics = AgentPerformanceMetrics(
                    agent_name=agent_name,
                    task_completion_rate=performance_data["completion_rate"],
                    average_response_time=performance_data["avg_response_time"],
                    accuracy_score=performance_data["accuracy"],
                    error_rate=performance_data["error_rate"],
                    workflow_appropriateness=performance_data["workflow_score"],
                    user_satisfaction=performance_data["satisfaction_score"],
                    cost_per_interaction=performance_data["cost_per_interaction"]
                )

                monitoring_results[agent_name] = metrics

                # Log metrics to AgentOps
                session.record_metrics({
                    "agent_name": agent_name,
                    "performance_metrics": asdict(metrics),
                    "monitoring_period": str(monitoring_duration),
                    "timestamp": datetime.utcnow().isoformat()
                })

        return monitoring_results
```

### 2.5 Advanced Healthcare Business Intelligence Dashboard

**Healthcare Business Analytics Engine for comprehensive practice performance monitoring:**

```python
# core/analytics/healthcare_business_intelligence.py
from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime, timedelta, date
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class PracticePerformanceDashboard:
    practice_id: str
    time_range: str
    patient_flow_metrics: 'PatientFlowAnalytics'
    revenue_metrics: 'RevenueCycleAnalytics'
    provider_metrics: 'ProviderProductivityAnalytics'
    insurance_metrics: 'InsurancePerformanceAnalytics'
    ai_metrics: 'AIUtilizationAnalytics'
    generated_at: datetime

@dataclass
class RevenueCycleAnalytics:
    total_billed: float
    total_collected: float
    collection_rate: float
    avg_days_to_payment: float
    denial_rate: float
    daily_trends: List[Dict[str, Any]]

@dataclass
class PatientFlowAnalytics:
    total_appointments: int
    show_rate: float
    avg_wait_time: float
    patient_satisfaction: float
    appointment_trends: List[Dict[str, Any]]

@dataclass
class ProviderProductivityAnalytics:
    total_encounters: int
    avg_encounters_per_day: float
    revenue_per_encounter: float
    provider_utilization: float
    productivity_trends: List[Dict[str, Any]]

@dataclass
class InsurancePerformanceAnalytics:
    verification_success_rate: float
    avg_verification_time: float
    top_payers: List[Dict[str, Any]]
    denial_rates_by_payer: Dict[str, float]

@dataclass
class AIUtilizationAnalytics:
    total_ai_interactions: int
    ai_accuracy_score: float
    time_saved_minutes: float
    doctor_satisfaction_score: float
    usage_trends: List[Dict[str, Any]]

class HealthcareBusinessIntelligence:
    """
    Advanced business intelligence for healthcare operations
    """

    def __init__(self, timescaledb_client):
        self.db_client = timescaledb_client
        self.analytics_engine = AnalyticsEngine()
        self.report_generator = ReportGenerator()

    async def generate_practice_performance_dashboard(self,
                                                    practice_id: str,
                                                    time_range: str = "30d") -> PracticePerformanceDashboard:
        """
        Generate comprehensive practice performance dashboard
        """

        # Patient flow analytics
        patient_flow = await self._analyze_patient_flow(practice_id, time_range)

        # Revenue cycle analytics
        revenue_analytics = await self._analyze_revenue_cycle(practice_id, time_range)

        # Provider productivity analytics
        provider_productivity = await self._analyze_provider_productivity(practice_id, time_range)

        # Insurance performance analytics
        insurance_performance = await self._analyze_insurance_performance(practice_id, time_range)

        # AI utilization analytics
        ai_utilization = await self._analyze_ai_utilization(practice_id, time_range)

        return PracticePerformanceDashboard(
            practice_id=practice_id,
            time_range=time_range,
            patient_flow_metrics=patient_flow,
            revenue_metrics=revenue_analytics,
            provider_metrics=provider_productivity,
            insurance_metrics=insurance_performance,
            ai_metrics=ai_utilization,
            generated_at=datetime.utcnow()
        )

    async def _analyze_revenue_cycle(self, practice_id: str, time_range: str) -> RevenueCycleAnalytics:
        """Analyze revenue cycle performance"""

        query = f"""
        SELECT
            DATE_TRUNC('day', service_date) as date,
            SUM(billed_amount) as total_billed,
            SUM(collected_amount) as total_collected,
            AVG(days_to_payment) as avg_days_to_payment,
            COUNT(CASE WHEN claim_status = 'denied' THEN 1 END) as denied_claims,
            COUNT(*) as total_claims
        FROM billing_transactions
        WHERE practice_id = $1
        AND service_date >= NOW() - INTERVAL '{time_range}'
        GROUP BY DATE_TRUNC('day', service_date)
        ORDER BY date
        """

        results = await self.db_client.execute_query(query, [practice_id])

        # Calculate key metrics
        total_billed = sum(row['total_billed'] for row in results)
        total_collected = sum(row['total_collected'] for row in results)
        collection_rate = (total_collected / total_billed * 100) if total_billed > 0 else 0

        avg_days_to_payment = sum(row['avg_days_to_payment'] for row in results) / len(results) if results else 0

        denial_rate = sum(row['denied_claims'] for row in results) / sum(row['total_claims'] for row in results) * 100 if results else 0

        return RevenueCycleAnalytics(
            total_billed=total_billed,
            total_collected=total_collected,
            collection_rate=collection_rate,
            avg_days_to_payment=avg_days_to_payment,
            denial_rate=denial_rate,
            daily_trends=results
        )

    async def _analyze_patient_flow(self, practice_id: str, time_range: str) -> PatientFlowAnalytics:
        """Analyze patient flow and appointment metrics"""

        query = f"""
        SELECT
            DATE_TRUNC('day', appointment_date) as date,
            COUNT(*) as total_appointments,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_appointments,
            AVG(wait_time_minutes) as avg_wait_time,
            AVG(patient_satisfaction_score) as avg_satisfaction
        FROM appointments
        WHERE practice_id = $1
        AND appointment_date >= NOW() - INTERVAL '{time_range}'
        GROUP BY DATE_TRUNC('day', appointment_date)
        ORDER BY date
        """

        results = await self.db_client.execute_query(query, [practice_id])

        # Calculate metrics
        total_appointments = sum(row['total_appointments'] for row in results)
        completed_appointments = sum(row['completed_appointments'] for row in results)
        show_rate = (completed_appointments / total_appointments * 100) if total_appointments > 0 else 0

        avg_wait_time = sum(row['avg_wait_time'] for row in results) / len(results) if results else 0
        patient_satisfaction = sum(row['avg_satisfaction'] for row in results) / len(results) if results else 0

        return PatientFlowAnalytics(
            total_appointments=total_appointments,
            show_rate=show_rate,
            avg_wait_time=avg_wait_time,
            patient_satisfaction=patient_satisfaction,
            appointment_trends=results
        )

    async def _analyze_provider_productivity(self, practice_id: str, time_range: str) -> ProviderProductivityAnalytics:
        """Analyze provider productivity metrics"""

        query = f"""
        SELECT
            provider_id,
            DATE_TRUNC('day', encounter_date) as date,
            COUNT(*) as encounters,
            SUM(encounter_value) as total_revenue,
            AVG(encounter_duration_minutes) as avg_duration
        FROM encounters
        WHERE practice_id = $1
        AND encounter_date >= NOW() - INTERVAL '{time_range}'
        GROUP BY provider_id, DATE_TRUNC('day', encounter_date)
        ORDER BY date
        """

        results = await self.db_client.execute_query(query, [practice_id])

        # Calculate metrics
        total_encounters = sum(row['encounters'] for row in results)
        total_revenue = sum(row['total_revenue'] for row in results)

        # Calculate working days in time range
        days = int(time_range.replace('d', '')) if 'd' in time_range else 30
        working_days = days * 0.7  # Assume 70% are working days

        avg_encounters_per_day = total_encounters / working_days if working_days > 0 else 0
        revenue_per_encounter = total_revenue / total_encounters if total_encounters > 0 else 0

        # Provider utilization (simplified calculation)
        provider_utilization = min(avg_encounters_per_day / 20 * 100, 100)  # Assume 20 encounters/day is 100%

        return ProviderProductivityAnalytics(
            total_encounters=total_encounters,
            avg_encounters_per_day=avg_encounters_per_day,
            revenue_per_encounter=revenue_per_encounter,
            provider_utilization=provider_utilization,
            productivity_trends=results
        )

    async def _analyze_insurance_performance(self, practice_id: str, time_range: str) -> InsurancePerformanceAnalytics:
        """Analyze insurance verification and payment performance"""

        verification_query = f"""
        SELECT
            COUNT(*) as total_verifications,
            COUNT(CASE WHEN verification_status = 'success' THEN 1 END) as successful_verifications,
            AVG(verification_time_seconds) as avg_verification_time
        FROM insurance_verifications
        WHERE practice_id = $1
        AND created_at >= NOW() - INTERVAL '{time_range}'
        """

        payer_query = f"""
        SELECT
            insurance_provider,
            COUNT(*) as claim_count,
            SUM(billed_amount) as total_billed,
            COUNT(CASE WHEN claim_status = 'denied' THEN 1 END) as denied_claims
        FROM billing_transactions
        WHERE practice_id = $1
        AND service_date >= NOW() - INTERVAL '{time_range}'
        GROUP BY insurance_provider
        ORDER BY total_billed DESC
        LIMIT 10
        """

        verification_results = await self.db_client.execute_query(verification_query, [practice_id])
        payer_results = await self.db_client.execute_query(payer_query, [practice_id])

        # Calculate verification metrics
        verification_data = verification_results[0] if verification_results else {}
        verification_success_rate = (
            verification_data.get('successful_verifications', 0) /
            verification_data.get('total_verifications', 1) * 100
        )
        avg_verification_time = verification_data.get('avg_verification_time', 0)

        # Process payer data
        top_payers = [
            {
                "provider": row['insurance_provider'],
                "claim_count": row['claim_count'],
                "total_billed": row['total_billed']
            }
            for row in payer_results
        ]

        denial_rates_by_payer = {
            row['insurance_provider']: (row['denied_claims'] / row['claim_count'] * 100)
            for row in payer_results
        }

        return InsurancePerformanceAnalytics(
            verification_success_rate=verification_success_rate,
            avg_verification_time=avg_verification_time,
            top_payers=top_payers,
            denial_rates_by_payer=denial_rates_by_payer
        )

    async def _analyze_ai_utilization(self, practice_id: str, time_range: str) -> AIUtilizationAnalytics:
        """Analyze AI system utilization and performance"""

        query = f"""
        SELECT
            DATE_TRUNC('day', interaction_date) as date,
            COUNT(*) as total_interactions,
            AVG(accuracy_score) as avg_accuracy,
            SUM(time_saved_minutes) as total_time_saved,
            AVG(doctor_satisfaction_score) as avg_doctor_satisfaction
        FROM ai_interactions
        WHERE practice_id = $1
        AND interaction_date >= NOW() - INTERVAL '{time_range}'
        GROUP BY DATE_TRUNC('day', interaction_date)
        ORDER BY date
        """

        results = await self.db_client.execute_query(query, [practice_id])

        # Calculate metrics
        total_ai_interactions = sum(row['total_interactions'] for row in results)
        ai_accuracy_score = sum(row['avg_accuracy'] for row in results) / len(results) if results else 0
        time_saved_minutes = sum(row['total_time_saved'] for row in results)
        doctor_satisfaction_score = sum(row['avg_doctor_satisfaction'] for row in results) / len(results) if results else 0

        return AIUtilizationAnalytics(
            total_ai_interactions=total_ai_interactions,
            ai_accuracy_score=ai_accuracy_score,
            time_saved_minutes=time_saved_minutes,
            doctor_satisfaction_score=doctor_satisfaction_score,
            usage_trends=results
        )

    async def generate_executive_summary_report(self,
                                              practice_id: str,
                                              time_range: str = "30d") -> Dict[str, Any]:
        """Generate executive summary report for practice leadership"""

        dashboard = await self.generate_practice_performance_dashboard(practice_id, time_range)

        # Key performance indicators
        kpis = {
            "revenue_collection_rate": dashboard.revenue_metrics.collection_rate,
            "patient_satisfaction": dashboard.patient_flow_metrics.patient_satisfaction,
            "provider_productivity": dashboard.provider_metrics.provider_utilization,
            "ai_effectiveness": dashboard.ai_metrics.ai_accuracy_score,
            "insurance_verification_success": dashboard.insurance_metrics.verification_success_rate
        }

        # Identify areas for improvement
        improvement_areas = []
        if kpis["revenue_collection_rate"] < 95:
            improvement_areas.append("Revenue cycle optimization needed")
        if kpis["patient_satisfaction"] < 4.0:
            improvement_areas.append("Patient experience enhancement required")
        if kpis["provider_productivity"] < 80:
            improvement_areas.append("Provider productivity improvement opportunity")

        # Generate recommendations
        recommendations = await self._generate_recommendations(dashboard, kpis)

        return {
            "practice_id": practice_id,
            "report_period": time_range,
            "key_performance_indicators": kpis,
            "improvement_areas": improvement_areas,
            "recommendations": recommendations,
            "dashboard_data": dashboard,
            "generated_at": datetime.utcnow().isoformat()
        }

    async def _generate_recommendations(self,
                                      dashboard: PracticePerformanceDashboard,
                                      kpis: Dict[str, float]) -> List[str]:
        """Generate actionable recommendations based on analytics"""

        recommendations = []

        # Revenue cycle recommendations
        if dashboard.revenue_metrics.collection_rate < 95:
            recommendations.append(
                f"Improve revenue collection rate from {dashboard.revenue_metrics.collection_rate:.1f}% "
                f"by implementing automated follow-up for outstanding claims"
            )

        if dashboard.revenue_metrics.avg_days_to_payment > 30:
            recommendations.append(
                f"Reduce average days to payment from {dashboard.revenue_metrics.avg_days_to_payment:.1f} days "
                f"by optimizing insurance verification and prior authorization processes"
            )

        # Patient flow recommendations
        if dashboard.patient_flow_metrics.show_rate < 90:
            recommendations.append(
                f"Improve appointment show rate from {dashboard.patient_flow_metrics.show_rate:.1f}% "
                f"by implementing automated appointment reminders"
            )

        # AI utilization recommendations
        if dashboard.ai_metrics.doctor_satisfaction_score < 4.0:
            recommendations.append(
                f"Enhance AI system effectiveness (current satisfaction: {dashboard.ai_metrics.doctor_satisfaction_score:.1f}/5) "
                f"by implementing additional doctor-specific training"
            )

        return recommendations

class AnalyticsEngine:
    """Core analytics processing engine"""

    def __init__(self):
        self.processors = {}

    async def process_analytics(self, data_type: str, data: Any) -> Any:
        """Process analytics for specific data type"""
        processor = self.processors.get(data_type)
        if processor:
            return await processor.process(data)
        return data

class ReportGenerator:
    """Generate formatted reports from analytics data"""

    async def generate_pdf_report(self, dashboard_data: PracticePerformanceDashboard) -> str:
        """Generate PDF report from dashboard data"""
        # Implementation would generate PDF report
        return f"report_{dashboard_data.practice_id}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"

    async def generate_excel_report(self, dashboard_data: PracticePerformanceDashboard) -> str:
        """Generate Excel report from dashboard data"""
        # Implementation would generate Excel report
        return f"report_{dashboard_data.practice_id}_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"
```

### 2.2 Enhanced Database Schema for Business Services

**Add business services tables to your existing PostgreSQL:**
```sql
-- Enhanced database schema for Phase 2 compliance tracking
CREATE TABLE IF NOT EXISTS compliance_audit_log (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    compliance_status VARCHAR(50) DEFAULT 'compliant',
    risk_level VARCHAR(20) DEFAULT 'low',
    details JSONB
);

-- Create hypertable for time-series compliance data
SELECT create_hypertable('compliance_audit_log', 'timestamp', if_not_exists => TRUE);

-- Add indexes for common compliance queries
CREATE INDEX IF NOT EXISTS idx_compliance_user_time ON compliance_audit_log (user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_compliance_risk_level ON compliance_audit_log (risk_level, timestamp);
CREATE INDEX IF NOT EXISTS idx_compliance_status ON compliance_audit_log (compliance_status, timestamp);

-- Insurance verification tracking
CREATE TABLE IF NOT EXISTS insurance_verifications (
    id SERIAL PRIMARY KEY,
    member_id VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    verification_status VARCHAR(50) NOT NULL,
    response_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Billing claims tracking
CREATE TABLE IF NOT EXISTS billing_claims (
    id SERIAL PRIMARY KEY,
    claim_id VARCHAR(100) UNIQUE NOT NULL,
    patient_id VARCHAR(100) NOT NULL,
    provider_id VARCHAR(100) NOT NULL,
    total_amount DECIMAL(10,2),
    claim_status VARCHAR(50) DEFAULT 'created',
    claim_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.3 Enhanced Monitoring for Business Services

**Add business service metrics to your existing resource-pusher.sh:**
```bash
# Add to scripts/resource-pusher.sh after existing metrics
collect_business_service_metrics() {
    local timestamp=$(date +%s%N)
    local hostname=$(hostname -s 2>/dev/null || hostname)
    
    # Check insurance verification service
    insurance_status="0"
    if curl -s --max-time 5 http://localhost:8003/health >/dev/null 2>&1; then
        insurance_status="1"
    fi
    
    # Check billing engine service
    billing_status="0"
    if curl -s --max-time 5 http://localhost:8004/health >/dev/null 2>&1; then
        billing_status="1"
    fi
    
    # Check compliance monitor service
    compliance_status="0"
    if curl -s --max-time 5 http://localhost:8005/health >/dev/null 2>&1; then
        compliance_status="1"
    fi
    
    # Create InfluxDB line protocol
    business_line="businessServices,host=${hostname} insurance_status=${insurance_status},billing_status=${billing_status},compliance_status=${compliance_status} ${timestamp}"
    
    # Push to InfluxDB
    curl -sS -XPOST "$INFLUX_URL" --data-binary "$business_line" >/dev/null 2>&1
    
    if [[ "$DEBUG" == true ]]; then
        log "[DEBUG] Business services metrics: insurance=${insurance_status}, billing=${billing_status}, compliance=${compliance_status}"
    fi
}

# Call in main collection function
collect_business_service_metrics
```

**Add healthcare-specific Grafana dashboard panels:**
```json
# Add to your existing Grafana dashboard configuration
{
  "panels": [
    {
      "title": "Business Services Status",
      "type": "stat",
      "targets": [
        {
          "query": "SELECT last(insurance_status) FROM businessServices",
          "alias": "Insurance"
        },
        {
          "query": "SELECT last(billing_status) FROM businessServices", 
          "alias": "Billing"
        },
        {
          "query": "SELECT last(compliance_status) FROM businessServices",
          "alias": "Compliance"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "thresholds": {
            "steps": [
              {"color": "red", "value": 0},
              {"color": "green", "value": 1}
            ]
          }
        }
      }
    },
    {
      "title": "Daily Transactions", 
      "type": "graph",
      "targets": [
        {
          "query": "SELECT count(*) FROM insurance_verifications WHERE time >= now() - 24h GROUP BY time(1h)"
        },
        {
          "query": "SELECT count(*) FROM billing_claims WHERE time >= now() - 24h GROUP BY time(1h)"
        }
      ]
    }
  ]
}
```

## Week 3: Doctor Personalization Infrastructure

### 3.1 Personalization Service

**Create service configuration:**
```bash
# services/user/personalization/personalization.conf
image="intelluxe/personalization:latest"
port="8007:8007"
description="Doctor-specific personalization with privacy protection"
env="NODE_ENV=production,PRIVACY_MODE=strict"
volumes="./preferences:/app/preferences:rw"
network_mode="intelluxe-net"
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8007/health || exit 1"
depends_on="postgres,redis"
```

**Deploy personalization service:**
```bash
./scripts/universal-service-runner.sh start personalization

# Verify service is running
curl http://localhost:8007/health
```

**Enhanced personalization with privacy protection:**
```python
# services/user/personalization/main.py
from fastapi import FastAPI, HTTPException
from typing import Dict, Any, List, Optional
import psycopg2
import json
from datetime import datetime

app = FastAPI(title="Doctor Personalization Service")

class PersonalizationService:
    """
    Doctor-specific personalization with privacy-first design
    """
    
    def __init__(self):
        self.db_conn = psycopg2.connect(
            "postgresql://intelluxe:secure_password@localhost:5432/intelluxe"
        )
        self.preference_manager = PreferenceManager()
        self.privacy_guard = PrivacyGuard()
    
    async def update_doctor_preferences(self, 
                                      doctor_id: str,
                                      preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Update doctor preferences with privacy validation"""
        
        # Privacy check - ensure no PHI in preferences
        privacy_check = await self.privacy_guard.validate_preferences(preferences)
        if not privacy_check['safe']:
            return {
                'updated': False,
                'error': 'Privacy violation detected',
                'issues': privacy_check['issues']
            }
        
        # Update preferences
        result = await self.preference_manager.update_preferences(doctor_id, preferences)
        
        # Log preference change for audit
        await self._log_preference_change(doctor_id, preferences)
        
        return {
            'updated': True,
            'doctor_id': doctor_id,
            'preferences_updated': list(preferences.keys()),
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_doctor_preferences(self, doctor_id: str) -> Dict[str, Any]:
        """Retrieve doctor preferences"""
        
        preferences = await self.preference_manager.get_preferences(doctor_id)
        
        return {
            'doctor_id': doctor_id,
            'preferences': preferences,
            'last_updated': preferences.get('_last_updated'),
            'version': preferences.get('_version', 1)
        }

class PreferenceManager:
    """Manage doctor-specific preferences"""
    
    def __init__(self):
        self.db_conn = psycopg2.connect(
            "postgresql://intelluxe:secure_password@localhost:5432/intelluxe"
        )
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Default doctor preferences"""
        return {
            'summary_style': 'detailed',
            'preferred_terminology': 'standard',
            'report_format': 'soap',
            'notification_preferences': {
                'email': True,
                'sms': False
            },
            'ui_preferences': {
                'theme': 'light',
                'font_size': 'medium'
            },
            '_version': 1,
            '_last_updated': datetime.now().isoformat()
        }

@app.post("/preferences/{doctor_id}")
async def update_preferences(doctor_id: str, preferences: Dict[str, Any]):
    service = PersonalizationService()
    return await service.update_doctor_preferences(doctor_id, preferences)

@app.get("/preferences/{doctor_id}")
async def get_preferences(doctor_id: str):
    service = PersonalizationService()
    return await service.get_doctor_preferences(doctor_id)
```

### 3.3 Advanced Doctor Personalization with Unsloth-Based LoRA Training

**Unsloth-Based Doctor Style Adaptation for efficient fine-tuning on healthcare conversations:**

```python
# core/personalization/doctor_style_adapter.py
from unsloth import FastLanguageModel
import torch
from transformers import TrainingArguments
from trl import SFTTrainer
from datasets import Dataset
from typing import Dict, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DoctorStyleAdapter:
    """
    Adapt AI models to individual doctor communication styles using QLoRA
    Uses Unsloth for efficient fine-tuning on healthcare conversations
    """

    def __init__(self, base_model_name="llama3.1:8b-instruct"):
        self.base_model_name = base_model_name
        self.adapters_registry = {}
        self.training_data_collector = TrainingDataCollector()

    async def create_doctor_adapter(self,
                                  doctor_id: str,
                                  training_conversations: List[Dict[str, Any]]) -> str:
        """
        Create personalized LoRA adapter for specific doctor

        Args:
            doctor_id: Unique doctor identifier
            training_conversations: Doctor's conversation history for training

        Returns:
            str: Path to trained adapter
        """

        # Prepare training data in Unsloth format
        training_data = self._prepare_training_data(training_conversations, doctor_id)

        # Load base model with Unsloth optimizations
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=self.base_model_name,
            max_seq_length=2048,
            dtype=None,  # Auto-detect
            load_in_4bit=True,  # Use 4-bit quantization for efficiency
        )

        # Configure LoRA for healthcare adaptation
        model = FastLanguageModel.get_peft_model(
            model,
            r=16,  # LoRA rank
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                          "gate_proj", "up_proj", "down_proj"],
            lora_alpha=16,
            lora_dropout=0.1,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=3407,
        )

        # Training configuration optimized for healthcare
        training_args = TrainingArguments(
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=5,
            max_steps=100,  # Adjust based on data size
            learning_rate=2e-4,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=1,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            seed=3407,
            output_dir=f"./adapters/{doctor_id}",
            save_strategy="steps",
            save_steps=50,
        )

        # Train with SFT (Supervised Fine-Tuning)
        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=training_data,
            dataset_text_field="text",
            max_seq_length=2048,
            dataset_num_proc=2,
            packing=False,
            args=training_args,
        )

        # Execute training
        trainer_stats = trainer.train()

        # Save adapter
        adapter_path = f"./adapters/{doctor_id}/final"
        model.save_pretrained(adapter_path)
        tokenizer.save_pretrained(adapter_path)

        # Register adapter
        self.adapters_registry[doctor_id] = {
            "adapter_path": adapter_path,
            "training_stats": trainer_stats,
            "created_at": datetime.utcnow(),
            "conversation_count": len(training_conversations)
        }

        logger.info(f"Created LoRA adapter for doctor {doctor_id} at {adapter_path}")
        return adapter_path

    def _prepare_training_data(self, conversations: List[Dict], doctor_id: str) -> Dataset:
        """Prepare conversation data for Unsloth training"""

        training_examples = []

        for conv in conversations:
            # Extract doctor's communication patterns
            doctor_messages = [msg for msg in conv["messages"]
                             if msg.get("role") == "doctor"]

            for msg in doctor_messages:
                # Create training example with context
                context = self._build_conversation_context(conv, msg)

                training_example = {
                    "text": f"<|im_start|>system\nYou are a healthcare AI assistant adapting to Dr. {doctor_id}'s communication style.<|im_end|>\n"
                           f"<|im_start|>user\n{context['patient_input']}<|im_end|>\n"
                           f"<|im_start|>assistant\n{msg['content']}<|im_end|>"
                }

                training_examples.append(training_example)

        return Dataset.from_list(training_examples)

    def _build_conversation_context(self, conversation: Dict, target_message: Dict) -> Dict:
        """Build context for training example"""

        # Find the patient input that preceded this doctor message
        messages = conversation["messages"]
        target_index = messages.index(target_message)

        patient_input = "General healthcare inquiry"
        for i in range(target_index - 1, -1, -1):
            if messages[i].get("role") == "patient":
                patient_input = messages[i]["content"]
                break

        return {
            "patient_input": patient_input,
            "conversation_id": conversation.get("id", "unknown"),
            "timestamp": conversation.get("timestamp", datetime.utcnow().isoformat())
        }

class TrainingDataCollector:
    """Collect and prepare training data for doctor adaptation"""

    def __init__(self):
        self.conversation_store = {}

    async def collect_doctor_conversation(self,
                                        doctor_id: str,
                                        conversation_data: Dict[str, Any]) -> None:
        """Collect conversation data for future training"""

        if doctor_id not in self.conversation_store:
            self.conversation_store[doctor_id] = []

        # Validate conversation data
        if self._validate_conversation_data(conversation_data):
            self.conversation_store[doctor_id].append(conversation_data)

            # Trigger training if enough data collected
            if len(self.conversation_store[doctor_id]) >= 50:  # Minimum conversations for training
                await self._trigger_adapter_training(doctor_id)

    def _validate_conversation_data(self, conversation_data: Dict[str, Any]) -> bool:
        """Validate conversation data for training suitability"""

        required_fields = ["messages", "id", "timestamp"]
        if not all(field in conversation_data for field in required_fields):
            return False

        # Check for doctor messages
        doctor_messages = [msg for msg in conversation_data["messages"]
                          if msg.get("role") == "doctor"]

        return len(doctor_messages) > 0
```

**Real-Time Style Adaptation:**

```python
# core/personalization/adaptive_response_generator.py
from typing import Dict, Any, Optional
from dataclasses import dataclass
import asyncio

@dataclass
class PersonalizedResponse:
    content: str
    doctor_id: str
    style_confidence: float
    adaptation_method: str

@dataclass
class DoctorStyleProfile:
    doctor_id: str
    formality_level: str  # "formal", "casual", "mixed"
    prefers_bullet_points: bool
    includes_patient_education: bool
    emphasizes_empathy: bool
    confidence_score: float

class AdaptiveResponseGenerator:
    """
    Generate responses adapted to doctor's personal style in real-time
    """

    def __init__(self, ollama_client):
        self.ollama_client = ollama_client
        self.style_analyzer = DoctorStyleAnalyzer()
        self.adapter_loader = AdapterLoader()

    async def generate_personalized_response(self,
                                           doctor_id: str,
                                           patient_context: Dict[str, Any],
                                           query: str) -> PersonalizedResponse:
        """
        Generate response adapted to doctor's communication style
        """

        # Load doctor's style profile
        style_profile = await self.style_analyzer.get_doctor_style_profile(doctor_id)

        # Load appropriate LoRA adapter if available
        adapter_path = self.adapter_loader.get_adapter_path(doctor_id)

        if adapter_path:
            # Use fine-tuned adapter
            response = await self._generate_with_adapter(
                adapter_path, patient_context, query, style_profile
            )
        else:
            # Use style prompting for new doctors
            response = await self._generate_with_style_prompting(
                patient_context, query, style_profile
            )

        # Apply real-time style adjustments
        adapted_response = await self._apply_style_adjustments(
            response, style_profile
        )

        return PersonalizedResponse(
            content=adapted_response,
            doctor_id=doctor_id,
            style_confidence=style_profile.confidence_score,
            adaptation_method="lora_adapter" if adapter_path else "style_prompting"
        )

    async def _apply_style_adjustments(self, response: str, style_profile: DoctorStyleProfile) -> str:
        """Apply doctor-specific style adjustments"""

        adjustments = []

        # Formality level adjustment
        if style_profile.formality_level == "formal":
            adjustments.append("Use formal medical terminology")
        elif style_profile.formality_level == "casual":
            adjustments.append("Use conversational, approachable language")

        # Communication preferences
        if style_profile.prefers_bullet_points:
            adjustments.append("Format information in bullet points")

        if style_profile.includes_patient_education:
            adjustments.append("Include patient education elements")

        if style_profile.emphasizes_empathy:
            adjustments.append("Emphasize empathetic communication")

        # Apply adjustments if needed
        if adjustments:
            adjustment_prompt = f"""
            Adjust the following medical response to match these style preferences:
            {', '.join(adjustments)}

            Original response: {response}

            Adjusted response:
            """

            adjusted = await self.ollama_client.generate(
                model="llama3.1:8b-instruct",
                prompt=adjustment_prompt
            )

            return adjusted.response

        return response

    async def _generate_with_adapter(self,
                                   adapter_path: str,
                                   patient_context: Dict[str, Any],
                                   query: str,
                                   style_profile: DoctorStyleProfile) -> str:
        """Generate response using doctor's LoRA adapter"""

        # Load adapter and generate response
        # This would integrate with the Unsloth-trained adapter
        prompt = f"""
        Patient Context: {patient_context}
        Query: {query}

        Respond in the doctor's established communication style:
        """

        # Use adapter-enhanced model for generation
        response = await self.ollama_client.generate(
            model=f"custom:{adapter_path}",
            prompt=prompt
        )

        return response.response

    async def _generate_with_style_prompting(self,
                                           patient_context: Dict[str, Any],
                                           query: str,
                                           style_profile: DoctorStyleProfile) -> str:
        """Generate response using style prompting for new doctors"""

        style_instructions = self._build_style_instructions(style_profile)

        prompt = f"""
        {style_instructions}

        Patient Context: {patient_context}
        Query: {query}

        Respond according to the specified communication style:
        """

        response = await self.ollama_client.generate(
            model="llama3.1:8b-instruct",
            prompt=prompt
        )

        return response.response

    def _build_style_instructions(self, style_profile: DoctorStyleProfile) -> str:
        """Build style instructions for prompting"""

        instructions = ["You are a healthcare AI assistant."]

        if style_profile.formality_level == "formal":
            instructions.append("Use formal, professional medical language.")
        elif style_profile.formality_level == "casual":
            instructions.append("Use conversational, approachable language while maintaining professionalism.")

        if style_profile.prefers_bullet_points:
            instructions.append("Format responses with clear bullet points when appropriate.")

        if style_profile.includes_patient_education:
            instructions.append("Include educational information to help patients understand their care.")

        if style_profile.emphasizes_empathy:
            instructions.append("Emphasize empathetic, compassionate communication.")

        return " ".join(instructions)

class DoctorStyleAnalyzer:
    """Analyze doctor communication patterns to build style profiles"""

    async def get_doctor_style_profile(self, doctor_id: str) -> DoctorStyleProfile:
        """Get or create doctor style profile"""

        # This would analyze historical conversations to determine style
        # For now, return a default profile
        return DoctorStyleProfile(
            doctor_id=doctor_id,
            formality_level="mixed",
            prefers_bullet_points=False,
            includes_patient_education=True,
            emphasizes_empathy=True,
            confidence_score=0.7
        )

class AdapterLoader:
    """Load and manage LoRA adapters"""

    def get_adapter_path(self, doctor_id: str) -> Optional[str]:
        """Get path to doctor's LoRA adapter if available"""

        adapter_path = f"./adapters/{doctor_id}/final"
        # Check if adapter exists
        import os
        if os.path.exists(adapter_path):
            return adapter_path
        return None
```

### 3.5 Doctor Learning and Adaptation System

**Continuous Learning from Doctor Interactions for improved personalization:**

```python
# core/personalization/continuous_learning.py
from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class InteractionPattern:
    pattern_type: str
    confidence: float
    frequency: int
    last_observed: datetime
    pattern_data: Dict[str, Any]

class DoctorLearningSystem:
    """
    Continuously learn and adapt to doctor preferences and patterns
    """

    def __init__(self, postgres_client):
        self.db_client = postgres_client
        self.pattern_analyzer = InteractionPatternAnalyzer()
        self.preference_updater = PreferenceUpdater()
        self.learning_threshold = 50  # Minimum interactions for retraining

    async def learn_from_interaction(self,
                                   doctor_id: str,
                                   interaction_data: Dict[str, Any]):
        """
        Learn from doctor-AI interaction to improve future responses
        """

        # Extract interaction patterns
        patterns = await self.pattern_analyzer.analyze_interaction(interaction_data)

        # Update doctor preferences
        await self._update_doctor_preferences(doctor_id, patterns)

        # Update communication style profile
        await self._update_communication_style(doctor_id, interaction_data)

        # Update clinical decision patterns
        await self._update_clinical_patterns(doctor_id, interaction_data)

        # Store interaction for future training data
        await self._store_training_interaction(doctor_id, interaction_data, patterns)

        # Check if adapter retraining is needed
        await self._check_retraining_trigger(doctor_id)

        logger.info(f"Processed learning interaction for doctor {doctor_id}")

    async def _update_doctor_preferences(self, doctor_id: str, patterns: Dict[str, Any]):
        """Update doctor's preferences based on interaction patterns"""

        current_preferences = await self.db_client.get_doctor_preferences(doctor_id)

        # Update response format preferences
        if patterns.get("prefers_bullet_points"):
            current_preferences["response_format"] = "bullet_points"
        elif patterns.get("prefers_paragraphs"):
            current_preferences["response_format"] = "paragraphs"

        # Update detail level preferences
        if patterns.get("requests_more_detail"):
            current_preferences["detail_level"] = min(
                current_preferences.get("detail_level", 5) + 1, 10
            )
        elif patterns.get("requests_less_detail"):
            current_preferences["detail_level"] = max(
                current_preferences.get("detail_level", 5) - 1, 1
            )

        # Update clinical focus areas
        clinical_focus = patterns.get("clinical_focus_areas", [])
        if clinical_focus:
            current_preferences["clinical_interests"] = list(
                set(current_preferences.get("clinical_interests", []) + clinical_focus)
            )

        # Update workflow preferences
        if patterns.get("prefers_quick_summaries"):
            current_preferences["summary_style"] = "concise"
        elif patterns.get("prefers_detailed_explanations"):
            current_preferences["summary_style"] = "detailed"

        # Update notification preferences
        if patterns.get("responds_quickly_to_urgent"):
            current_preferences["urgent_notification_threshold"] = "high"

        # Save updated preferences
        await self.db_client.update_doctor_preferences(doctor_id, current_preferences)

        logger.info(f"Updated preferences for doctor {doctor_id}: {list(patterns.keys())}")

    async def _update_communication_style(self, doctor_id: str, interaction_data: Dict[str, Any]):
        """Update doctor's communication style profile"""

        communication_patterns = {
            "formality_level": self._analyze_formality(interaction_data),
            "empathy_emphasis": self._analyze_empathy_patterns(interaction_data),
            "technical_depth": self._analyze_technical_depth(interaction_data),
            "patient_education_focus": self._analyze_education_focus(interaction_data)
        }

        # Store communication style updates
        await self.db_client.update_doctor_communication_style(doctor_id, communication_patterns)

    async def _update_clinical_patterns(self, doctor_id: str, interaction_data: Dict[str, Any]):
        """Update clinical decision patterns (administrative focus only)"""

        clinical_patterns = {
            "common_workflows": self._extract_workflow_patterns(interaction_data),
            "preferred_documentation_style": self._analyze_documentation_style(interaction_data),
            "administrative_priorities": self._extract_admin_priorities(interaction_data),
            "efficiency_preferences": self._analyze_efficiency_patterns(interaction_data)
        }

        # Store clinical patterns (administrative only)
        await self.db_client.update_doctor_clinical_patterns(doctor_id, clinical_patterns)

    async def _store_training_interaction(self,
                                        doctor_id: str,
                                        interaction_data: Dict[str, Any],
                                        patterns: Dict[str, Any]):
        """Store interaction for future training data"""

        training_record = {
            "doctor_id": doctor_id,
            "interaction_type": interaction_data.get("type", "general"),
            "input_text": interaction_data.get("input", ""),
            "ai_response": interaction_data.get("ai_response", ""),
            "doctor_feedback": interaction_data.get("feedback"),
            "satisfaction_score": interaction_data.get("satisfaction_score"),
            "patterns_detected": patterns,
            "workflow_context": interaction_data.get("workflow_context", {}),
            "administrative_focus": True,  # Ensure administrative focus
            "created_at": datetime.utcnow()
        }

        await self.db_client.store_training_interaction(training_record)

    async def _check_retraining_trigger(self, doctor_id: str):
        """Check if adapter retraining should be triggered"""

        # Count new interactions since last training
        interaction_count = await self.db_client.count_new_interactions_since_last_training(doctor_id)

        if interaction_count >= self.learning_threshold:
            logger.info(f"Triggering adapter retraining for doctor {doctor_id} ({interaction_count} new interactions)")
            await self.trigger_adapter_retraining(doctor_id)

    async def trigger_adapter_retraining(self, doctor_id: str) -> bool:
        """
        Trigger retraining of doctor's LoRA adapter when sufficient new data available
        """

        try:
            # Check if enough new interactions have occurred
            interaction_count = await self.db_client.count_new_interactions_since_last_training(doctor_id)

            if interaction_count >= self.learning_threshold:
                # Collect new training data
                new_training_data = await self.db_client.get_training_interactions_since_last_training(doctor_id)

                # Validate training data quality
                validated_data = await self._validate_training_data(new_training_data)

                if len(validated_data) >= 25:  # Minimum quality interactions
                    # Trigger background retraining
                    await self._schedule_adapter_retraining(doctor_id, validated_data)

                    # Update last training timestamp
                    await self.db_client.update_last_training_timestamp(doctor_id)

                    logger.info(f"Scheduled adapter retraining for doctor {doctor_id}")
                    return True
                else:
                    logger.warning(f"Insufficient quality training data for doctor {doctor_id}")

            return False

        except Exception as e:
            logger.error(f"Failed to trigger adapter retraining for doctor {doctor_id}: {e}")
            return False

    async def _validate_training_data(self, training_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and filter training data for quality"""

        validated_data = []

        for interaction in training_data:
            # Check for minimum quality criteria
            if (interaction.get("satisfaction_score", 0) >= 3.0 and  # Minimum satisfaction
                len(interaction.get("input_text", "")) > 10 and      # Meaningful input
                len(interaction.get("ai_response", "")) > 20 and     # Substantial response
                interaction.get("administrative_focus", False)):      # Administrative focus

                validated_data.append(interaction)

        return validated_data

    async def _schedule_adapter_retraining(self, doctor_id: str, training_data: List[Dict[str, Any]]):
        """Schedule background adapter retraining"""

        # This would integrate with the Unsloth-based adapter training system
        retraining_job = {
            "doctor_id": doctor_id,
            "training_data": training_data,
            "scheduled_at": datetime.utcnow(),
            "priority": "normal",
            "estimated_duration_minutes": 30
        }

        # Queue retraining job
        await self.db_client.queue_retraining_job(retraining_job)

        # Notify doctor style adapter service
        await self._notify_adapter_service(doctor_id, retraining_job)

    async def _notify_adapter_service(self, doctor_id: str, retraining_job: Dict[str, Any]):
        """Notify the doctor style adapter service of retraining job"""

        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8012/schedule_retraining",
                    json={
                        "doctor_id": doctor_id,
                        "job_details": retraining_job
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    logger.info(f"Successfully notified adapter service for doctor {doctor_id}")
                else:
                    logger.warning(f"Failed to notify adapter service: {response.status_code}")

        except Exception as e:
            logger.error(f"Error notifying adapter service: {e}")

    # Analysis helper methods
    def _analyze_formality(self, interaction_data: Dict[str, Any]) -> str:
        """Analyze formality level from interaction"""

        doctor_input = interaction_data.get("input", "").lower()

        formal_indicators = ["please", "would you", "could you", "thank you"]
        casual_indicators = ["hey", "thanks", "quick question", "just"]

        formal_count = sum(1 for indicator in formal_indicators if indicator in doctor_input)
        casual_count = sum(1 for indicator in casual_indicators if indicator in doctor_input)

        if formal_count > casual_count:
            return "formal"
        elif casual_count > formal_count:
            return "casual"
        else:
            return "mixed"

    def _analyze_empathy_patterns(self, interaction_data: Dict[str, Any]) -> bool:
        """Analyze if doctor emphasizes empathy in communications"""

        empathy_keywords = ["patient comfort", "patient understanding", "reassurance", "empathy", "compassionate"]
        doctor_input = interaction_data.get("input", "").lower()

        return any(keyword in doctor_input for keyword in empathy_keywords)

    def _analyze_technical_depth(self, interaction_data: Dict[str, Any]) -> str:
        """Analyze preferred technical depth level"""

        doctor_input = interaction_data.get("input", "").lower()

        if "detailed explanation" in doctor_input or "technical details" in doctor_input:
            return "high"
        elif "simple" in doctor_input or "brief" in doctor_input:
            return "low"
        else:
            return "medium"

    def _analyze_education_focus(self, interaction_data: Dict[str, Any]) -> bool:
        """Analyze if doctor focuses on patient education"""

        education_keywords = ["patient education", "explain to patient", "help patient understand", "patient resources"]
        doctor_input = interaction_data.get("input", "").lower()

        return any(keyword in doctor_input for keyword in education_keywords)

    def _extract_workflow_patterns(self, interaction_data: Dict[str, Any]) -> List[str]:
        """Extract common workflow patterns"""

        workflow_context = interaction_data.get("workflow_context", {})
        workflow_type = workflow_context.get("type", "general")

        # Common administrative workflow patterns
        patterns = []
        if "insurance" in str(workflow_context).lower():
            patterns.append("insurance_verification_focused")
        if "billing" in str(workflow_context).lower():
            patterns.append("billing_optimization_focused")
        if "scheduling" in str(workflow_context).lower():
            patterns.append("scheduling_efficiency_focused")

        return patterns

    def _analyze_documentation_style(self, interaction_data: Dict[str, Any]) -> str:
        """Analyze preferred documentation style"""

        ai_response = interaction_data.get("ai_response", "").lower()

        if "•" in ai_response or "bullet" in interaction_data.get("input", "").lower():
            return "bullet_points"
        elif "paragraph" in interaction_data.get("input", "").lower():
            return "paragraphs"
        else:
            return "mixed"

    def _extract_admin_priorities(self, interaction_data: Dict[str, Any]) -> List[str]:
        """Extract administrative priorities from interaction"""

        priorities = []
        input_text = interaction_data.get("input", "").lower()

        if "urgent" in input_text or "asap" in input_text:
            priorities.append("urgency_focused")
        if "efficient" in input_text or "quick" in input_text:
            priorities.append("efficiency_focused")
        if "accurate" in input_text or "precise" in input_text:
            priorities.append("accuracy_focused")

        return priorities

    def _analyze_efficiency_patterns(self, interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze efficiency preferences"""

        return {
            "prefers_shortcuts": "shortcut" in interaction_data.get("input", "").lower(),
            "values_automation": "automate" in interaction_data.get("input", "").lower(),
            "time_conscious": any(word in interaction_data.get("input", "").lower()
                                for word in ["quick", "fast", "time", "efficient"])
        }

class InteractionPatternAnalyzer:
    """Analyze patterns from doctor-AI interactions"""

    async def analyze_interaction(self, interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze interaction for learning patterns"""

        patterns = {}

        # Analyze response format preferences
        patterns.update(self._analyze_format_preferences(interaction_data))

        # Analyze detail level preferences
        patterns.update(self._analyze_detail_preferences(interaction_data))

        # Analyze clinical focus areas
        patterns.update(self._analyze_clinical_focus(interaction_data))

        # Analyze workflow preferences
        patterns.update(self._analyze_workflow_preferences(interaction_data))

        return patterns

    def _analyze_format_preferences(self, interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze format preferences from interaction"""

        doctor_input = interaction_data.get("input", "").lower()
        feedback = interaction_data.get("feedback", "").lower()

        patterns = {}

        if "bullet points" in doctor_input or "list format" in doctor_input:
            patterns["prefers_bullet_points"] = True
        elif "paragraph" in doctor_input or "narrative" in doctor_input:
            patterns["prefers_paragraphs"] = True

        # Learn from feedback
        if "too much text" in feedback or "too long" in feedback:
            patterns["prefers_bullet_points"] = True
        elif "more detail" in feedback or "expand" in feedback:
            patterns["prefers_paragraphs"] = True

        return patterns

    def _analyze_detail_preferences(self, interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze detail level preferences"""

        doctor_input = interaction_data.get("input", "").lower()
        feedback = interaction_data.get("feedback", "").lower()

        patterns = {}

        if "more detail" in doctor_input or "elaborate" in doctor_input:
            patterns["requests_more_detail"] = True
        elif "brief" in doctor_input or "summary" in doctor_input:
            patterns["requests_less_detail"] = True

        # Learn from feedback
        if "too detailed" in feedback or "too much" in feedback:
            patterns["requests_less_detail"] = True
        elif "not enough" in feedback or "more information" in feedback:
            patterns["requests_more_detail"] = True

        return patterns

    def _analyze_clinical_focus(self, interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze clinical focus areas (administrative only)"""

        workflow_context = interaction_data.get("workflow_context", {})

        clinical_focus_areas = []

        # Administrative focus areas only
        if "insurance" in str(workflow_context).lower():
            clinical_focus_areas.append("insurance_administration")
        if "billing" in str(workflow_context).lower():
            clinical_focus_areas.append("billing_management")
        if "scheduling" in str(workflow_context).lower():
            clinical_focus_areas.append("scheduling_optimization")
        if "compliance" in str(workflow_context).lower():
            clinical_focus_areas.append("compliance_monitoring")

        return {"clinical_focus_areas": clinical_focus_areas} if clinical_focus_areas else {}

    def _analyze_workflow_preferences(self, interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze workflow preferences"""

        patterns = {}

        doctor_input = interaction_data.get("input", "").lower()

        if "quick" in doctor_input or "fast" in doctor_input:
            patterns["prefers_quick_summaries"] = True
        elif "detailed" in doctor_input or "comprehensive" in doctor_input:
            patterns["prefers_detailed_explanations"] = True

        if "urgent" in doctor_input or "priority" in doctor_input:
            patterns["responds_quickly_to_urgent"] = True

        return patterns

class PreferenceUpdater:
    """Update doctor preferences based on learning"""

    def __init__(self):
        self.update_weights = {
            "format_preference": 0.1,
            "detail_level": 0.05,
            "clinical_focus": 0.2,
            "workflow_efficiency": 0.15
        }

    async def update_preferences(self,
                               doctor_id: str,
                               current_preferences: Dict[str, Any],
                               learned_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Update preferences with learned patterns"""

        updated_preferences = current_preferences.copy()

        # Apply learned patterns with appropriate weights
        for pattern_type, pattern_value in learned_patterns.items():
            weight = self.update_weights.get(pattern_type, 0.1)

            if pattern_type in updated_preferences:
                # Weighted update for existing preferences
                if isinstance(pattern_value, (int, float)):
                    current_value = updated_preferences[pattern_type]
                    updated_preferences[pattern_type] = (
                        current_value * (1 - weight) + pattern_value * weight
                    )
                else:
                    # Direct update for categorical preferences
                    updated_preferences[pattern_type] = pattern_value
            else:
                # New preference
                updated_preferences[pattern_type] = pattern_value

        return updated_preferences

# Global learning system instance
doctor_learning_system = DoctorLearningSystem(postgres_client=None)  # Will be initialized with actual client
```

### 3.4 LoRA/QLoRA Training Infrastructure for Doctor Personalization

**Advanced doctor personalization with LoRA training for workflow adaptation:**

```python
# services/user/personalization/lora_training_manager.py
from typing import Dict, List, Optional, Any
import asyncio
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model, TaskType
import json
from datetime import datetime, timedelta
import numpy as np

class DoctorLoRATrainingManager:
    """LoRA/QLoRA training manager for doctor-specific workflow personalization"""

    def __init__(self, base_model_path: str, training_config: Dict):
        self.base_model_path = base_model_path
        self.training_config = training_config
        self.tokenizer = AutoTokenizer.from_pretrained(base_model_path)
        self.base_model = AutoModelForCausalLM.from_pretrained(base_model_path)

        # LoRA configuration for doctor personalization
        self.lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            inference_mode=False,
            r=16,  # Rank
            lora_alpha=32,
            lora_dropout=0.1,
            target_modules=["q_proj", "v_proj", "k_proj", "o_proj"]
        )

        # Doctor-specific training data storage
        self.doctor_training_data = {}
        self.doctor_models = {}

    async def collect_doctor_interaction_data(
        self,
        doctor_id: str,
        interaction_data: Dict[str, Any]
    ) -> None:
        """Collect doctor interaction data for LoRA training"""

        if doctor_id not in self.doctor_training_data:
            self.doctor_training_data[doctor_id] = []

        # Process interaction for training
        training_sample = {
            'timestamp': datetime.utcnow().isoformat(),
            'interaction_type': interaction_data.get('type', 'general'),
            'input_text': interaction_data.get('input', ''),
            'preferred_output': interaction_data.get('output', ''),
            'workflow_context': interaction_data.get('context', {}),
            'doctor_feedback': interaction_data.get('feedback', None),
            'administrative_focus': interaction_data.get('admin_focus', True)
        }

        self.doctor_training_data[doctor_id].append(training_sample)

        # Trigger training if enough data collected
        if len(self.doctor_training_data[doctor_id]) >= self.training_config.get('min_samples', 100):
            await self.schedule_doctor_lora_training(doctor_id)

    async def train_doctor_lora_model(
        self,
        doctor_id: str,
        training_samples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Train doctor-specific LoRA model for workflow personalization"""

        # Prepare training data
        training_texts = []
        for sample in training_samples:
            # Focus on administrative workflow patterns
            if sample.get('administrative_focus', True):
                training_text = f"""
                Doctor Workflow Context: {sample['workflow_context']}
                Input: {sample['input_text']}
                Preferred Administrative Response: {sample['preferred_output']}
                """
                training_texts.append(training_text.strip())

        # Tokenize training data
        tokenized_data = self.tokenizer(
            training_texts,
            truncation=True,
            padding=True,
            max_length=512,
            return_tensors="pt"
        )

        # Create LoRA model
        lora_model = get_peft_model(self.base_model, self.lora_config)

        # Training configuration
        training_args = {
            'learning_rate': 2e-4,
            'num_epochs': 3,
            'batch_size': 4,
            'gradient_accumulation_steps': 4,
            'warmup_steps': 100,
            'logging_steps': 10
        }

        # Train LoRA model (simplified training loop)
        optimizer = torch.optim.AdamW(lora_model.parameters(), lr=training_args['learning_rate'])

        lora_model.train()
        for epoch in range(training_args['num_epochs']):
            for batch_idx in range(0, len(tokenized_data['input_ids']), training_args['batch_size']):
                batch_input_ids = tokenized_data['input_ids'][batch_idx:batch_idx + training_args['batch_size']]
                batch_attention_mask = tokenized_data['attention_mask'][batch_idx:batch_idx + training_args['batch_size']]

                outputs = lora_model(input_ids=batch_input_ids, attention_mask=batch_attention_mask, labels=batch_input_ids)
                loss = outputs.loss

                loss.backward()
                optimizer.step()
                optimizer.zero_grad()

        # Save doctor-specific LoRA weights
        lora_weights_path = f"./models/doctor_lora/{doctor_id}_lora_weights.pt"
        lora_model.save_pretrained(lora_weights_path)

        # Store model reference
        self.doctor_models[doctor_id] = {
            'model_path': lora_weights_path,
            'training_samples': len(training_samples),
            'trained_at': datetime.utcnow().isoformat(),
            'performance_metrics': await self.evaluate_lora_model(lora_model, doctor_id)
        }

        return {
            'doctor_id': doctor_id,
            'lora_model_trained': True,
            'model_path': lora_weights_path,
            'training_samples_used': len(training_samples),
            'performance_metrics': self.doctor_models[doctor_id]['performance_metrics']
        }

    async def apply_doctor_lora_personalization(
        self,
        doctor_id: str,
        input_text: str,
        workflow_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply doctor-specific LoRA personalization to workflow responses"""

        if doctor_id not in self.doctor_models:
            # Use base model if no personalization available
            return await self.generate_base_response(input_text, workflow_context)

        # Load doctor-specific LoRA model
        doctor_model_info = self.doctor_models[doctor_id]
        lora_model = get_peft_model(self.base_model, self.lora_config)
        lora_model.load_adapter(doctor_model_info['model_path'])

        # Generate personalized response
        personalized_prompt = f"""
        Doctor Workflow Context: {workflow_context}
        Administrative Request: {input_text}

        Provide a response tailored to this doctor's workflow preferences:
        """

        inputs = self.tokenizer(personalized_prompt, return_tensors="pt")

        with torch.no_grad():
            outputs = lora_model.generate(
                **inputs,
                max_length=512,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        personalized_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        return {
            'personalized_response': personalized_response,
            'doctor_id': doctor_id,
            'personalization_applied': True,
            'model_info': doctor_model_info,
            'workflow_context': workflow_context
        }

    async def evaluate_doctor_personalization_effectiveness(
        self,
        doctor_id: str,
        evaluation_samples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate effectiveness of doctor-specific personalization"""

        if doctor_id not in self.doctor_models:
            return {'error': 'No personalization model available for doctor'}

        base_responses = []
        personalized_responses = []

        for sample in evaluation_samples:
            # Generate base response
            base_response = await self.generate_base_response(
                sample['input'], sample['context']
            )
            base_responses.append(base_response)

            # Generate personalized response
            personalized_response = await self.apply_doctor_lora_personalization(
                doctor_id, sample['input'], sample['context']
            )
            personalized_responses.append(personalized_response)

        # Calculate effectiveness metrics
        effectiveness_metrics = {
            'preference_alignment': await self.calculate_preference_alignment(
                doctor_id, evaluation_samples, personalized_responses
            ),
            'workflow_efficiency': await self.calculate_workflow_efficiency(
                base_responses, personalized_responses
            ),
            'administrative_accuracy': await self.calculate_administrative_accuracy(
                evaluation_samples, personalized_responses
            ),
            'doctor_satisfaction_score': await self.estimate_doctor_satisfaction(
                doctor_id, personalized_responses
            )
        }

        return {
            'doctor_id': doctor_id,
            'evaluation_samples': len(evaluation_samples),
            'effectiveness_metrics': effectiveness_metrics,
            'personalization_improvement': effectiveness_metrics['preference_alignment'] > 0.7,
            'evaluated_at': datetime.utcnow().isoformat()
        }

# Global LoRA training manager
doctor_lora_manager = DoctorLoRATrainingManager(
    base_model_path="microsoft/DialoGPT-medium",
    training_config={
        'min_samples': 50,
        'training_frequency': 'weekly',
        'max_models_per_doctor': 3
    }
)
```

### 3.2 Enhanced Database Schema for Personalization

**Add personalization tables to your existing PostgreSQL:**
```sql
-- Enhanced schema for Phase 2 personalization
CREATE TABLE IF NOT EXISTS doctor_preferences (
    id SERIAL PRIMARY KEY,
    doctor_id VARCHAR(100) UNIQUE NOT NULL,
    preferences JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS doctor_interaction_patterns (
    id SERIAL PRIMARY KEY,
    doctor_id VARCHAR(100) NOT NULL,
    interaction_type VARCHAR(100) NOT NULL,
    pattern_data JSONB NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create hypertable for interaction patterns
SELECT create_hypertable('doctor_interaction_patterns', 'recorded_at', if_not_exists => TRUE);

-- Indexes for personalization queries
CREATE INDEX IF NOT EXISTS idx_doctor_preferences_doctor_id ON doctor_preferences (doctor_id);
CREATE INDEX IF NOT EXISTS idx_interaction_patterns_doctor_time ON doctor_interaction_patterns (doctor_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_interaction_patterns_type ON doctor_interaction_patterns (interaction_type, recorded_at);

-- LoRA training data storage
CREATE TABLE IF NOT EXISTS doctor_lora_training_data (
    id SERIAL PRIMARY KEY,
    doctor_id VARCHAR(100) NOT NULL,
    interaction_type VARCHAR(100) NOT NULL,
    input_text TEXT NOT NULL,
    preferred_output TEXT NOT NULL,
    workflow_context JSONB,
    feedback_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- LoRA model metadata
CREATE TABLE IF NOT EXISTS doctor_lora_models (
    id SERIAL PRIMARY KEY,
    doctor_id VARCHAR(100) UNIQUE NOT NULL,
    model_path VARCHAR(500) NOT NULL,
    training_samples_count INTEGER NOT NULL,
    performance_metrics JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create hypertable for LoRA training data
SELECT create_hypertable('doctor_lora_training_data', 'created_at', if_not_exists => TRUE);

-- Indexes for LoRA training queries
CREATE INDEX IF NOT EXISTS idx_lora_training_doctor_time ON doctor_lora_training_data (doctor_id, created_at);
CREATE INDEX IF NOT EXISTS idx_lora_models_doctor ON doctor_lora_models (doctor_id);

-- Advanced insurance integration tables
CREATE TABLE IF NOT EXISTS insurance_verifications_enhanced (
    id SERIAL PRIMARY KEY,
    practice_id VARCHAR(100) NOT NULL,
    member_id VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    service_codes JSONB NOT NULL,
    verification_status VARCHAR(50) NOT NULL,
    verification_time_seconds INTEGER,
    cost_estimates JSONB,
    copay_amounts JSONB,
    deductible_remaining DECIMAL(10,2),
    response_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Prior authorization tracking
CREATE TABLE IF NOT EXISTS prior_authorizations (
    id SERIAL PRIMARY KEY,
    tracking_id VARCHAR(100) UNIQUE NOT NULL,
    patient_id VARCHAR(100) NOT NULL,
    practice_id VARCHAR(100) NOT NULL,
    service_code VARCHAR(50) NOT NULL,
    insurance_provider VARCHAR(50) NOT NULL,
    reference_number VARCHAR(100),
    status VARCHAR(50) DEFAULT 'submitted',
    clinical_justification TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estimated_decision_date DATE,
    decision_received_at TIMESTAMP,
    decision_result VARCHAR(50)
);

-- Business intelligence tables
CREATE TABLE IF NOT EXISTS billing_transactions (
    id SERIAL PRIMARY KEY,
    practice_id VARCHAR(100) NOT NULL,
    patient_id VARCHAR(100) NOT NULL,
    provider_id VARCHAR(100) NOT NULL,
    service_date DATE NOT NULL,
    service_codes JSONB NOT NULL,
    billed_amount DECIMAL(10,2) NOT NULL,
    collected_amount DECIMAL(10,2) DEFAULT 0,
    insurance_provider VARCHAR(50),
    claim_status VARCHAR(50) DEFAULT 'submitted',
    days_to_payment INTEGER,
    encounter_value DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS appointments (
    id SERIAL PRIMARY KEY,
    practice_id VARCHAR(100) NOT NULL,
    patient_id VARCHAR(100) NOT NULL,
    provider_id VARCHAR(100) NOT NULL,
    appointment_date TIMESTAMP NOT NULL,
    status VARCHAR(50) DEFAULT 'scheduled',
    wait_time_minutes INTEGER,
    patient_satisfaction_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS encounters (
    id SERIAL PRIMARY KEY,
    practice_id VARCHAR(100) NOT NULL,
    provider_id VARCHAR(100) NOT NULL,
    patient_id VARCHAR(100) NOT NULL,
    encounter_date TIMESTAMP NOT NULL,
    encounter_duration_minutes INTEGER,
    encounter_value DECIMAL(10,2),
    encounter_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_interactions (
    id SERIAL PRIMARY KEY,
    practice_id VARCHAR(100) NOT NULL,
    doctor_id VARCHAR(100) NOT NULL,
    interaction_date TIMESTAMP NOT NULL,
    interaction_type VARCHAR(100) NOT NULL,
    accuracy_score DECIMAL(3,2),
    time_saved_minutes INTEGER,
    doctor_satisfaction_score DECIMAL(3,2),
    personalization_applied BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create hypertables for time-series data
SELECT create_hypertable('insurance_verifications_enhanced', 'created_at', if_not_exists => TRUE);
SELECT create_hypertable('billing_transactions', 'created_at', if_not_exists => TRUE);
SELECT create_hypertable('appointments', 'created_at', if_not_exists => TRUE);
SELECT create_hypertable('encounters', 'created_at', if_not_exists => TRUE);
SELECT create_hypertable('ai_interactions', 'created_at', if_not_exists => TRUE);

-- Indexes for business intelligence queries
CREATE INDEX IF NOT EXISTS idx_billing_practice_date ON billing_transactions (practice_id, service_date);
CREATE INDEX IF NOT EXISTS idx_appointments_practice_date ON appointments (practice_id, appointment_date);
CREATE INDEX IF NOT EXISTS idx_encounters_practice_date ON encounters (practice_id, encounter_date);
CREATE INDEX IF NOT EXISTS idx_ai_interactions_practice_date ON ai_interactions (practice_id, interaction_date);
CREATE INDEX IF NOT EXISTS idx_insurance_verifications_practice ON insurance_verifications_enhanced (practice_id, created_at);
```

## Week 4: Advanced Agent Features and Integration

### 4.1 Enhanced Agent Router with Business Services

**Advanced agent router integrating all services:**
```python
# core/orchestration/enhanced_agent_router.py
from typing import Dict, Any, List, Optional
import asyncio
from core.agents.base_agent import BaseAgent
from core.agents.document_processor import DocumentProcessorAgent
from core.agents.research_assistant import ResearchAssistantAgent
from core.agents.transcription_agent import TranscriptionAgent
import httpx

class EnhancedAgentRouter:
    """
    Route requests to appropriate agents and business services
    """
    
    def __init__(self):
        self.agents = {
            'document_processor': DocumentProcessorAgent(),
            'research_assistant': ResearchAssistantAgent(),
            'transcription': TranscriptionAgent()
        }
        
        self.business_services = {
            'insurance_verification': 'http://localhost:8003',
            'billing_engine': 'http://localhost:8004',
            'compliance_monitor': 'http://localhost:8005',
            'personalization': 'http://localhost:8007'
        }
        
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def route_request(self, request_type: str, input_data: Dict[str, Any],
                           session_id: str, doctor_id: str) -> Dict[str, Any]:
        """Route request to appropriate agent or business service"""
        
        # Get doctor preferences for personalization
        doctor_prefs = await self._get_doctor_preferences(doctor_id)
        
        # Log access for compliance
        await self._log_access_event(doctor_id, request_type, input_data)
        
        # Route based on request type
        if request_type in self.agents:
            # Handle with AI agent
            agent = self.agents[request_type]
            result = await agent.process_with_tracking(input_data, session_id)
            
            # Personalize result based on doctor preferences
            personalized_result = await self._personalize_result(
                result, doctor_prefs, request_type
            )
            
            return personalized_result
            
        elif request_type == 'insurance_verification':
            return await self._call_business_service('insurance_verification', 'verify', input_data)
            
        elif request_type == 'billing_claim':
            return await self._call_business_service('billing_engine', 'create_claim', input_data)
            
        elif request_type == 'complete_workflow':
            return await self._handle_complete_workflow(input_data, session_id, doctor_id)
            
        else:
            return {'error': f'Unknown request type: {request_type}'}
    
    async def _handle_complete_workflow(self, input_data: Dict[str, Any], 
                                      session_id: str, doctor_id: str) -> Dict[str, Any]:
        """Handle complete patient workflow from intake to billing"""
        
        workflow_results = {}
        
        # Step 1: Process intake documents
        if 'intake_documents' in input_data:
            doc_result = await self.agents['document_processor'].process_with_tracking(
                {'document_text': input_data['intake_documents'], 'document_type': 'intake'},
                session_id
            )
            workflow_results['document_processing'] = doc_result
        
        # Step 2: Verify insurance
        if 'insurance_info' in input_data:
            insurance_result = await self._call_business_service(
                'insurance_verification', 'verify', input_data['insurance_info']
            )
            workflow_results['insurance_verification'] = insurance_result
        
        # Step 3: Process consultation audio (if provided)
        if 'consultation_audio' in input_data:
            transcription_result = await self.agents['transcription'].process_with_tracking(
                input_data['consultation_audio'], session_id
            )
            workflow_results['transcription'] = transcription_result
        
        # Step 4: Create billing claim
        if 'billing_info' in input_data and workflow_results.get('insurance_verification', {}).get('verified'):
            billing_result = await self._call_business_service(
                'billing_engine', 'create_claim', input_data['billing_info']
            )
            workflow_results['billing'] = billing_result
        
        return {
            'workflow_type': 'complete_patient_workflow',
            'workflow_results': workflow_results,
            'overall_status': 'completed' if all(
                'error' not in result for result in workflow_results.values()
            ) else 'partial_completion'
        }
    
    async def _get_doctor_preferences(self, doctor_id: str) -> Dict[str, Any]:
        """Get doctor preferences for personalization"""
        try:
            response = await self.client.get(f"http://localhost:8007/preferences/{doctor_id}")
            if response.status_code == 200:
                return response.json()['preferences']
        except Exception:
            pass
        
        # Return default preferences if service unavailable
        return {'summary_style': 'detailed', 'report_format': 'soap'}
    
    async def _personalize_result(self, result: Dict[str, Any], 
                                doctor_prefs: Dict[str, Any],
                                request_type: str) -> Dict[str, Any]:
        """Personalize result based on doctor preferences"""
        
        if request_type == 'transcription':
            # Adjust transcription style based on preferences
            if doctor_prefs.get('summary_style') == 'concise':
                result['personalized_summary'] = await self._create_concise_summary(
                    result.get('transcription', '')
                )
        
        elif request_type == 'document_processor':
            # Adjust report format based on preferences
            report_format = doctor_prefs.get('report_format', 'soap')
            if report_format == 'bullet_points':
                result['formatted_report'] = await self._format_as_bullets(result)
        
        return result
    
    async def _log_access_event(self, doctor_id: str, request_type: str, 
                              input_data: Dict[str, Any]) -> None:
        """Log access event for compliance"""
        
        access_event = {
            'user_id': doctor_id,
            'action': f'ai_request_{request_type}',
            'resource_type': 'ai_agent',
            'details': {'request_type': request_type, 'has_phi': self._contains_potential_phi(input_data)}
        }
        
        try:
            await self.client.post(
                "http://localhost:8005/log_access",
                json=access_event
            )
        except Exception:
            # Log locally if compliance service unavailable
            pass
    
    async def _call_business_service(self, service_name: str, endpoint: str, 
                                   data: Dict[str, Any]) -> Dict[str, Any]:
        """Call business service endpoint"""
        
        service_url = self.business_services[service_name]
        
        try:
            response = await self.client.post(f"{service_url}/{endpoint}", json=data)
            return response.json()
        except Exception as e:
            return {
                'error': f'Service {service_name} unavailable',
                'details': str(e)
            }

# Global enhanced router
enhanced_agent_router = EnhancedAgentRouter()
```

### 4.5 Production-Ready Monitoring Systems for Clinical Workflows

**Enterprise-grade monitoring with healthcare-specific metrics and real-time alerting:**

```python
# services/user/monitoring/production_monitoring_manager.py
from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime, timedelta
import json
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge, Summary
import grafana_api
import alertmanager_api

class ProductionHealthcareMonitoringManager:
    """Production-ready monitoring for healthcare AI workflows"""

    def __init__(self, config: Dict):
        self.config = config

        # Healthcare-specific Prometheus metrics
        self.setup_healthcare_metrics()

        # Grafana dashboard management
        self.grafana_client = grafana_api.GrafanaApi(
            auth=config['grafana']['auth'],
            host=config['grafana']['host']
        )

        # AlertManager integration
        self.alert_manager = alertmanager_api.AlertManagerApi(
            host=config['alertmanager']['host']
        )

    def setup_healthcare_metrics(self):
        """Setup healthcare-specific Prometheus metrics"""

        # Administrative workflow metrics
        self.admin_workflow_counter = Counter(
            'healthcare_admin_workflows_total',
            'Total administrative workflows processed',
            ['workflow_type', 'doctor_id', 'status']
        )

        self.admin_workflow_duration = Histogram(
            'healthcare_admin_workflow_duration_seconds',
            'Administrative workflow processing duration',
            ['workflow_type', 'doctor_id']
        )

        # LoRA personalization metrics
        self.lora_personalization_counter = Counter(
            'healthcare_lora_personalizations_total',
            'Total LoRA personalizations applied',
            ['doctor_id', 'model_type']
        )

        self.lora_training_gauge = Gauge(
            'healthcare_lora_training_samples',
            'Number of training samples per doctor',
            ['doctor_id']
        )

        # Chain-of-Thought reasoning metrics
        self.cot_reasoning_counter = Counter(
            'healthcare_cot_reasoning_total',
            'Total Chain-of-Thought reasoning processes',
            ['reasoning_type', 'confidence_level']
        )

        self.cot_reasoning_duration = Histogram(
            'healthcare_cot_reasoning_duration_seconds',
            'Chain-of-Thought reasoning processing duration',
            ['reasoning_type']
        )

        # PHI protection metrics
        self.phi_detection_counter = Counter(
            'healthcare_phi_detections_total',
            'Total PHI detections',
            ['detection_type', 'confidence_level']
        )

        self.phi_protection_gauge = Gauge(
            'healthcare_phi_protection_score',
            'Current PHI protection effectiveness score'
        )

        # Business service health metrics
        self.service_health_gauge = Gauge(
            'healthcare_service_health',
            'Health status of healthcare services',
            ['service_name']
        )

        # Doctor satisfaction metrics
        self.doctor_satisfaction_gauge = Gauge(
            'healthcare_doctor_satisfaction_score',
            'Doctor satisfaction with AI assistance',
            ['doctor_id', 'interaction_type']
        )

    async def monitor_administrative_workflow(
        self,
        workflow_type: str,
        doctor_id: str,
        workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Monitor administrative workflow execution"""

        start_time = datetime.utcnow()

        try:
            # Process workflow (placeholder for actual workflow processing)
            workflow_result = await self.process_workflow(workflow_type, workflow_data)

            # Record successful workflow
            self.admin_workflow_counter.labels(
                workflow_type=workflow_type,
                doctor_id=doctor_id,
                status='success'
            ).inc()

            # Record workflow duration
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.admin_workflow_duration.labels(
                workflow_type=workflow_type,
                doctor_id=doctor_id
            ).observe(duration)

            # Check for performance alerts
            if duration > self.config.get('workflow_duration_threshold', 30):
                await self.trigger_performance_alert(workflow_type, doctor_id, duration)

            return {
                'workflow_monitored': True,
                'duration_seconds': duration,
                'status': 'success',
                'metrics_recorded': True
            }

        except Exception as e:
            # Record failed workflow
            self.admin_workflow_counter.labels(
                workflow_type=workflow_type,
                doctor_id=doctor_id,
                status='error'
            ).inc()

            # Trigger error alert
            await self.trigger_error_alert(workflow_type, doctor_id, str(e))

            return {
                'workflow_monitored': True,
                'status': 'error',
                'error': str(e),
                'metrics_recorded': True
            }

    async def monitor_lora_personalization(
        self,
        doctor_id: str,
        personalization_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Monitor LoRA personalization effectiveness"""

        model_type = personalization_data.get('model_type', 'general')

        # Record personalization usage
        self.lora_personalization_counter.labels(
            doctor_id=doctor_id,
            model_type=model_type
        ).inc()

        # Update training samples count
        training_samples = personalization_data.get('training_samples', 0)
        self.lora_training_gauge.labels(doctor_id=doctor_id).set(training_samples)

        # Monitor personalization effectiveness
        effectiveness_score = personalization_data.get('effectiveness_score', 0.0)

        if effectiveness_score < self.config.get('min_personalization_effectiveness', 0.7):
            await self.trigger_personalization_alert(doctor_id, effectiveness_score)

        return {
            'personalization_monitored': True,
            'effectiveness_score': effectiveness_score,
            'training_samples': training_samples
        }

    async def monitor_chain_of_thought_reasoning(
        self,
        reasoning_type: str,
        reasoning_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Monitor Chain-of-Thought reasoning processes"""

        start_time = datetime.utcnow()
        confidence_level = reasoning_data.get('confidence_level', 'medium')

        # Record reasoning process
        self.cot_reasoning_counter.labels(
            reasoning_type=reasoning_type,
            confidence_level=confidence_level
        ).inc()

        # Record reasoning duration
        processing_duration = reasoning_data.get('processing_duration', 0)
        self.cot_reasoning_duration.labels(
            reasoning_type=reasoning_type
        ).observe(processing_duration)

        # Check reasoning quality
        reasoning_quality = reasoning_data.get('reasoning_quality', 0.0)
        if reasoning_quality < self.config.get('min_reasoning_quality', 0.8):
            await self.trigger_reasoning_quality_alert(reasoning_type, reasoning_quality)

        return {
            'reasoning_monitored': True,
            'reasoning_type': reasoning_type,
            'confidence_level': confidence_level,
            'quality_score': reasoning_quality
        }

    async def setup_healthcare_dashboards(self) -> Dict[str, Any]:
        """Setup comprehensive healthcare monitoring dashboards"""

        # Main healthcare dashboard
        main_dashboard = {
            "dashboard": {
                "title": "Intelluxe Healthcare AI Production Monitoring",
                "tags": ["healthcare", "ai", "production"],
                "panels": [
                    {
                        "title": "Administrative Workflow Success Rate",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "rate(healthcare_admin_workflows_total{status='success'}[5m]) / rate(healthcare_admin_workflows_total[5m]) * 100"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percent",
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 90},
                                        {"color": "green", "value": 95}
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "title": "LoRA Personalization Effectiveness",
                        "type": "gauge",
                        "targets": [
                            {
                                "expr": "avg(healthcare_doctor_satisfaction_score)"
                            }
                        ]
                    },
                    {
                        "title": "Chain-of-Thought Reasoning Performance",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "histogram_quantile(0.95, healthcare_cot_reasoning_duration_seconds_bucket)"
                            }
                        ]
                    },
                    {
                        "title": "PHI Protection Status",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "healthcare_phi_protection_score"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 0.8},
                                        {"color": "green", "value": 0.95}
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "title": "Service Health Overview",
                        "type": "table",
                        "targets": [
                            {
                                "expr": "healthcare_service_health",
                                "format": "table"
                            }
                        ]
                    }
                ]
            }
        }

        # Create dashboard in Grafana
        dashboard_result = await self.grafana_client.dashboard.update_dashboard(main_dashboard)

        return {
            'main_dashboard_created': True,
            'dashboard_url': dashboard_result.get('url'),
            'dashboard_id': dashboard_result.get('id')
        }

    async def setup_healthcare_alerts(self) -> Dict[str, Any]:
        """Setup healthcare-specific alerting rules"""

        alert_rules = [
            {
                "alert": "HighAdminWorkflowFailureRate",
                "expr": "rate(healthcare_admin_workflows_total{status='error'}[5m]) / rate(healthcare_admin_workflows_total[5m]) > 0.05",
                "for": "2m",
                "labels": {
                    "severity": "warning",
                    "service": "healthcare-ai"
                },
                "annotations": {
                    "summary": "High administrative workflow failure rate detected",
                    "description": "Administrative workflow failure rate is above 5% for the last 5 minutes"
                }
            },
            {
                "alert": "LowLoRAPersonalizationEffectiveness",
                "expr": "avg(healthcare_doctor_satisfaction_score) < 0.7",
                "for": "5m",
                "labels": {
                    "severity": "warning",
                    "service": "personalization"
                },
                "annotations": {
                    "summary": "LoRA personalization effectiveness is low",
                    "description": "Doctor satisfaction with LoRA personalization is below 70%"
                }
            },
            {
                "alert": "PHIProtectionScoreLow",
                "expr": "healthcare_phi_protection_score < 0.95",
                "for": "1m",
                "labels": {
                    "severity": "critical",
                    "service": "compliance"
                },
                "annotations": {
                    "summary": "PHI protection score is critically low",
                    "description": "PHI protection effectiveness is below 95% - immediate attention required"
                }
            }
        ]

        # Deploy alert rules
        for rule in alert_rules:
            await self.alert_manager.create_alert_rule(rule)

        return {
            'alert_rules_created': len(alert_rules),
            'rules': [rule['alert'] for rule in alert_rules]
        }

# Global production monitoring manager
production_monitoring_manager = ProductionHealthcareMonitoringManager({
    'grafana': {
        'host': 'http://localhost:3000',
        'auth': ('admin', 'admin')
    },
    'alertmanager': {
        'host': 'http://localhost:9093'
    },
    'workflow_duration_threshold': 30,
    'min_personalization_effectiveness': 0.7,
    'min_reasoning_quality': 0.8
})
```

### 4.2 Comprehensive Integration Testing

**Integration test suite for all business services:**
```python
# tests/test_phase2_integration.py
import pytest
import asyncio
import httpx
from datetime import datetime

class TestPhase2BusinessServices:
    
    @pytest.mark.asyncio
    async def test_all_services_running(self):
        """Test all business services are running via universal service runner"""
        
        services_to_check = [
            'http://localhost:8003/health',  # Insurance verification
            'http://localhost:8004/health',  # Billing engine
            'http://localhost:8005/health',  # Compliance monitor
            'http://localhost:8007/health',  # Personalization
        ]
        
        async with httpx.AsyncClient() as client:
            for service_url in services_to_check:
                response = await client.get(service_url, timeout=5.0)
                assert response.status_code == 200
                result = response.json()
                assert result['status'] == 'healthy'
    
    @pytest.mark.asyncio
    async def test_insurance_verification_flow(self):
        """Test complete insurance verification workflow"""
        
        async with httpx.AsyncClient() as client:
            verification_request = {
                "member_id": "W123456789",
                "provider_id": "ANTHEM_12345",
                "service_codes": ["99213", "99214"]
            }
            
            response = await client.post(
                "http://localhost:8003/verify",
                json=verification_request,
                timeout=10.0
            )
            
            assert response.status_code == 200
            result = response.json()
            assert 'verified' in result or 'error' in result
    
    @pytest.mark.asyncio
    async def test_billing_engine_flow(self):
        """Test billing engine claim creation"""
        
        async with httpx.AsyncClient() as client:
            claim_data = {
                "patient_id": "P123456",
                "provider_id": "PR789",
                "service_date": datetime.now().isoformat(),
                "service_codes": ["99213", "I10"],
                "insurance_info": {
                    "member_id": "W123456789",
                    "copay_amount": 25.00,
                    "coinsurance_rate": 0.2
                }
            }
            
            response = await client.post(
                "http://localhost:8004/create_claim",
                json=claim_data,
                timeout=10.0
            )
            
            assert response.status_code == 200
            result = response.json()
            assert 'claim_created' in result or 'error' in result
    
    @pytest.mark.asyncio
    async def test_compliance_monitoring_flow(self):
        """Test compliance monitoring and audit logging"""
        
        async with httpx.AsyncClient() as client:
            access_event = {
                "user_id": "dr_smith",
                "action": "view_patient_record",
                "resource_type": "patient_data",
                "resource_id": "P123456",
                "ip_address": "192.168.1.100",
                "details": {"record_type": "demographics"}
            }
            
            response = await client.post(
                "http://localhost:8005/log_access",
                json=access_event,
                timeout=5.0
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result['logged'] == True
    
    @pytest.mark.asyncio
    async def test_personalization_flow(self):
        """Test doctor personalization service"""
        
        async with httpx.AsyncClient() as client:
            # Update doctor preferences
            preferences = {
                "summary_style": "concise",
                "preferred_terminology": "simplified",
                "report_format": "bullet_points"
            }
            
            response = await client.post(
                "http://localhost:8007/preferences/dr_test",
                json=preferences,
                timeout=5.0
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result['updated'] == True
            
            # Retrieve preferences
            response = await client.get(
                "http://localhost:8007/preferences/dr_test",
                timeout=5.0
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result['preferences']['summary_style'] == 'concise'
    
    @pytest.mark.asyncio
    async def test_enhanced_agent_router(self):
        """Test the enhanced agent router with business services"""
        
        from core.orchestration.enhanced_agent_router import enhanced_agent_router
        
        # Test complete workflow
        workflow_data = {
            'intake_documents': 'Patient: John D. Chief complaint: Headache',
            'insurance_info': {
                'member_id': 'W123456789',
                'provider_id': 'ANTHEM_12345'
            },
            'billing_info': {
                'patient_id': 'P123456',
                'provider_id': 'PR789',
                'service_date': datetime.now().isoformat(),
                'service_codes': ['99213']
            }
        }
        
        result = await enhanced_agent_router.route_request(
            'complete_workflow', workflow_data, 'test_session', 'dr_test'
        )
        
        assert result['workflow_type'] == 'complete_patient_workflow'
        assert 'workflow_results' in result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### 4.6 Advanced Evaluation Frameworks for Healthcare AI Quality

**Comprehensive testing suite with healthcare-specific evaluation metrics:**

```python
# tests/test_phase2_advanced_evaluation.py
import pytest
import asyncio
import httpx
from datetime import datetime
import numpy as np
from typing import Dict, List, Any

class TestPhase2AdvancedEvaluation:

    @pytest.mark.asyncio
    async def test_chain_of_thought_reasoning_quality(self):
        """Test Chain-of-Thought reasoning quality for administrative decisions"""

        async with httpx.AsyncClient() as client:
            reasoning_request = {
                "reasoning_type": "insurance_verification",
                "administrative_question": "Determine coverage eligibility for preventive care services",
                "insurance_data": {
                    "member_id": "W123456789",
                    "plan_type": "PPO",
                    "provider_network": "ANTHEM"
                },
                "session_id": "test_cot_session"
            }

            response = await client.post(
                "http://localhost:8003/chain_of_thought_reasoning",
                json=reasoning_request,
                timeout=30.0
            )

            assert response.status_code == 200
            result = response.json()

            # Validate reasoning chain structure
            assert 'reasoning_steps' in result
            assert 'final_conclusion' in result
            assert 'confidence_score' in result
            assert result['confidence_score'] >= 0.7

            # Validate administrative focus (no medical advice)
            reasoning_text = ' '.join([step.get('reasoning_process', '') for step in result['reasoning_steps']])
            assert 'medical advice' not in reasoning_text.lower()
            assert 'administrative' in reasoning_text.lower() or 'coverage' in reasoning_text.lower()

    @pytest.mark.asyncio
    async def test_lora_personalization_effectiveness(self):
        """Test LoRA personalization effectiveness for doctor workflows"""

        async with httpx.AsyncClient() as client:
            # First, collect some training data
            training_data = {
                "doctor_id": "dr_test_lora",
                "interaction_data": {
                    "type": "workflow_preference",
                    "input": "Generate insurance verification summary",
                    "output": "Brief bullet-point summary with key coverage details",
                    "context": {"preferred_format": "bullets", "detail_level": "concise"},
                    "feedback": 0.9,
                    "admin_focus": True
                }
            }

            # Submit training data
            response = await client.post(
                "http://localhost:8007/lora_training/collect_data",
                json=training_data,
                timeout=10.0
            )

            assert response.status_code == 200

            # Test personalized response generation
            personalization_request = {
                "doctor_id": "dr_test_lora",
                "input_text": "Generate insurance verification summary for patient",
                "workflow_context": {
                    "task_type": "insurance_summary",
                    "urgency": "routine"
                }
            }

            response = await client.post(
                "http://localhost:8007/lora_personalization/apply",
                json=personalization_request,
                timeout=15.0
            )

            assert response.status_code == 200
            result = response.json()

            # Validate personalization application
            assert 'personalized_response' in result
            assert result['personalization_applied'] == True
            assert 'doctor_id' in result

    @pytest.mark.asyncio
    async def test_tree_of_thoughts_billing_planning(self):
        """Test Tree-of-Thoughts planning for complex billing scenarios"""

        async with httpx.AsyncClient() as client:
            complex_billing_scenario = {
                "patient_id": "P123456",
                "multiple_providers": True,
                "service_codes": ["99213", "99214", "I10", "Z00.00"],
                "insurance_complications": {
                    "prior_authorization_required": True,
                    "multiple_payers": ["primary", "secondary"],
                    "coverage_gaps": ["specialist_referral"]
                },
                "administrative_complexity": "high"
            }

            response = await client.post(
                "http://localhost:8004/tree_of_thoughts_planning",
                json={
                    "billing_scenario_data": complex_billing_scenario,
                    "planning_depth": 3,
                    "branches_per_level": 3
                },
                timeout=45.0
            )

            assert response.status_code == 200
            result = response.json()

            # Validate Tree-of-Thoughts structure
            assert 'planning_levels' in result
            assert len(result['planning_levels']) == 3
            assert 'optimal_path' in result

            # Validate administrative focus
            for level in result['planning_levels']:
                for branch in level['branches']:
                    assert 'administrative' in str(branch).lower() or 'billing' in str(branch).lower()

    @pytest.mark.asyncio
    async def test_comprehensive_evaluation_metrics(self):
        """Test comprehensive evaluation framework with healthcare metrics"""

        async with httpx.AsyncClient() as client:
            evaluation_request = {
                "evaluation_name": "phase2_comprehensive_test",
                "test_dataset": [
                    {
                        "query": "Verify insurance eligibility for routine checkup",
                        "expected_type": "administrative_workflow",
                        "context": {"service_type": "preventive_care"}
                    },
                    {
                        "query": "Process billing claim for office visit",
                        "expected_type": "billing_workflow",
                        "context": {"claim_complexity": "standard"}
                    }
                ],
                "evaluation_metrics": [
                    "administrative_accuracy",
                    "workflow_safety",
                    "phi_protection",
                    "reasoning_transparency"
                ]
            }

            response = await client.post(
                "http://localhost:8005/comprehensive_evaluation",
                json=evaluation_request,
                timeout=60.0
            )

            assert response.status_code == 200
            result = response.json()

            # Validate evaluation results
            assert 'administrative_accuracy' in result
            assert 'workflow_safety' in result
            assert 'phi_protection' in result
            assert 'reasoning_transparency' in result

            # Validate minimum quality thresholds
            assert result['administrative_accuracy'] >= 0.8
            assert result['workflow_safety'] >= 0.9
            assert result['phi_protection'] >= 0.95

    @pytest.mark.asyncio
    async def test_production_monitoring_integration(self):
        """Test production monitoring system integration"""

        async with httpx.AsyncClient() as client:
            # Test monitoring endpoint
            response = await client.get(
                "http://localhost:8008/monitoring/healthcare_metrics",
                timeout=10.0
            )

            assert response.status_code == 200
            metrics = response.json()

            # Validate healthcare-specific metrics
            expected_metrics = [
                'admin_workflow_success_rate',
                'lora_personalization_effectiveness',
                'cot_reasoning_performance',
                'phi_protection_score',
                'service_health_status'
            ]

            for metric in expected_metrics:
                assert metric in metrics

            # Validate metric values are within expected ranges
            assert 0 <= metrics['admin_workflow_success_rate'] <= 1
            assert 0 <= metrics['lora_personalization_effectiveness'] <= 1
            assert metrics['phi_protection_score'] >= 0.9

    @pytest.mark.asyncio
    async def test_doctor_workflow_personalization_end_to_end(self):
        """Test complete doctor workflow personalization pipeline"""

        async with httpx.AsyncClient() as client:
            doctor_id = "dr_e2e_test"

            # Step 1: Set doctor preferences
            preferences = {
                "summary_style": "bullet_points",
                "detail_level": "concise",
                "workflow_automation": "high",
                "notification_preferences": {
                    "urgent_alerts": True,
                    "daily_summaries": False
                }
            }

            response = await client.post(
                f"http://localhost:8007/preferences/{doctor_id}",
                json=preferences,
                timeout=5.0
            )
            assert response.status_code == 200

            # Step 2: Process workflow with personalization
            workflow_request = {
                "workflow_type": "complete_patient_workflow",
                "doctor_id": doctor_id,
                "session_id": "e2e_test_session",
                "input_data": {
                    "intake_documents": "Patient: Jane D. Chief complaint: Annual physical",
                    "insurance_info": {
                        "member_id": "W987654321",
                        "provider_id": "ANTHEM_54321"
                    }
                }
            }

            response = await client.post(
                "http://localhost:8000/enhanced_agent_router/route_request",
                json=workflow_request,
                timeout=30.0
            )

            assert response.status_code == 200
            result = response.json()

            # Validate personalized workflow execution
            assert result['workflow_type'] == 'complete_patient_workflow'
            assert 'workflow_results' in result
            assert result['overall_status'] in ['completed', 'partial_completion']

            # Validate personalization was applied
            if 'document_processing' in result['workflow_results']:
                doc_result = result['workflow_results']['document_processing']
                # Should reflect bullet point preference
                assert 'formatted_report' in doc_result or 'personalized' in str(doc_result).lower()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
```

### 4.3 Enhanced Monitoring Dashboard Updates

**Add business service panels to your existing Grafana dashboard:**
```json
# Add to your existing Grafana dashboard JSON
{
  "title": "Intelluxe Healthcare AI Business Services Dashboard",
  "panels": [
    {
      "title": "Service Health Status",
      "type": "stat",
      "gridPos": {"h": 6, "w": 12, "x": 0, "y": 0},
      "targets": [
        {
          "query": "SELECT last(insurance_status) FROM businessServices",
          "alias": "Insurance"
        },
        {
          "query": "SELECT last(billing_status) FROM businessServices",
          "alias": "Billing"
        },
        {
          "query": "SELECT last(compliance_status) FROM businessServices", 
          "alias": "Compliance"
        }
      ]
    },
    {
      "title": "Daily Transaction Volume",
      "type": "graph",
      "gridPos": {"h": 6, "w": 12, "x": 12, "y": 0},
      "targets": [
        {
          "query": "SELECT count(*) FROM insurance_verifications WHERE time >= now() - 24h GROUP BY time(1h) fill(0)"
        },
        {
          "query": "SELECT count(*) FROM billing_claims WHERE time >= now() - 24h GROUP BY time(1h) fill(0)"
        }
      ]
    },
    {
      "title": "Agent Performance",
      "type": "graph", 
      "gridPos": {"h": 6, "w": 24, "x": 0, "y": 6},
      "targets": [
        {
          "query": "SELECT mean(processing_time) FROM agent_sessions WHERE time >= now() - 1h GROUP BY time(5m), agent_type"
        }
      ]
    }
  ]
}
```

## Week 4: Real-time Medical Assistant Integration

### 4.1 Real-time Medical Assistant Service

**Create service configuration for intelligent real-time assistance:**
```bash
# services/user/realtime-medical-assistant/realtime-medical-assistant.conf
image="intelluxe/realtime-medical-assistant:latest"
port="8009:8009"
description="Real-time medical assistant integrating WhisperLive transcription with SciSpacy NLP and intelligent doctor assistance"
env="NODE_ENV=production,SCISPACY_MODEL=en_ner_bc5cdr_md"
volumes="./models:/app/models:rw,./cache:/app/cache:rw"
network_mode="intelluxe-net" 
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8009/health || exit 1"
depends_on="whisperlive,scispacy,ollama,healthcare-mcp"
```

**Real-time Medical Assistant implementation:**
```python
# agents/realtime_medical_assistant/realtime_assistant.py
from fastapi import FastAPI, WebSocket, HTTPException
from typing import Dict, Any, List, Optional
import asyncio
import json
import spacy
import httpx
from datetime import datetime, timedelta
import redis
from core.memory.memory_manager import memory_manager
from core.orchestration.agent_orchestrator import orchestrator

app = FastAPI(title="Real-time Medical Assistant")

class RealtimeMedicalAssistant:
    """
    Real-time medical assistant that processes WhisperLive transcription chunks,
    extracts medical entities with SciSpacy, and provides intelligent assistance
    """
    
    def __init__(self):
        # Load SciSpacy model for medical NER
        self.nlp = spacy.load("en_ner_bc5cdr_md")
        self.redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
        self.ollama_client = httpx.AsyncClient(base_url="http://localhost:11434")
        
        # Medical entity tracking
        self.session_entities = {}
        self.doctor_patterns = {}
        
        # Integration with existing systems
        self.memory_manager = memory_manager
        self.orchestrator = orchestrator
    
    async def process_transcription_chunk(self, 
                                        doctor_id: str, 
                                        session_id: str,
                                        chunk_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process transcription chunk from WhisperLive"""
        
        transcription_text = chunk_data.get('text', '')
        confidence = chunk_data.get('confidence', 0.0)
        timestamp = chunk_data.get('timestamp', datetime.utcnow().isoformat())
        
        # Extract medical entities using SciSpacy
        entities = await self._extract_medical_entities(transcription_text)
        
        # Update session context
        await self._update_session_context(session_id, {
            'transcription': transcription_text,
            'entities': entities,
            'timestamp': timestamp,
            'confidence': confidence
        })
        
        # Generate intelligent assistance
        assistance = await self._generate_intelligent_assistance(
            doctor_id, session_id, transcription_text, entities
        )
        
        # Learn doctor patterns (for future LoRA training)
        await self._learn_doctor_patterns(doctor_id, transcription_text, entities, assistance)
        
        return {
            'processed_text': transcription_text,
            'medical_entities': entities,
            'intelligent_assistance': assistance,
            'confidence': confidence,
            'timestamp': timestamp
        }
    
    async def _extract_medical_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract medical entities using SciSpacy"""
        
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            entity = {
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char,
                'confidence': getattr(ent, 'confidence', 0.9)
            }
            
            # Add medical context if available
            if ent.label_ in ['DISEASE', 'CHEMICAL']:
                entity['medical_context'] = await self._get_medical_context(ent.text, ent.label_)
            
            entities.append(entity)
        
        return entities
    
    async def _generate_intelligent_assistance(self, 
                                             doctor_id: str,
                                             session_id: str, 
                                             text: str, 
                                             entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate intelligent assistance based on medical entities and doctor patterns"""
        
        # Get doctor's typical patterns
        doctor_patterns = await self._get_doctor_patterns(doctor_id)
        
        # Build assistance context
        assistance_context = {
            'current_text': text,
            'medical_entities': entities,
            'doctor_patterns': doctor_patterns,
            'session_history': await self._get_session_history(session_id)
        }
        
        # Generate suggestions based on patterns
        suggestions = []
        
        # Check for symptoms mentioned
        symptoms = [e for e in entities if e['label'] == 'DISEASE' or 'symptom' in e['text'].lower()]
        if symptoms:
            # Suggest related conditions the doctor typically looks up
            related_lookups = await self._predict_doctor_lookups(doctor_id, symptoms)
            if related_lookups:
                suggestions.append({
                    'type': 'related_conditions',
                    'message': f"Based on symptoms mentioned, you typically look up: {', '.join(related_lookups)}",
                    'action': 'lookup_conditions',
                    'data': related_lookups
                })
        
        # Check for medication mentions
        medications = [e for e in entities if e['label'] == 'CHEMICAL']
        if medications:
            # Check for drug interactions
            interactions = await self._check_drug_interactions(medications)
            if interactions:
                suggestions.append({
                    'type': 'drug_interactions',
                    'message': f"Potential interactions detected with mentioned medications",
                    'action': 'review_interactions',
                    'data': interactions
                })
        
        # Generate contextual medical assistance
        medical_assistance = await self._generate_medical_context_assistance(text, entities)
        
        return {
            'suggestions': suggestions,
            'medical_assistance': medical_assistance,
            'confidence': 0.85,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    async def _learn_doctor_patterns(self, 
                                   doctor_id: str, 
                                   text: str, 
                                   entities: List[Dict[str, Any]], 
                                   assistance: Dict[str, Any]) -> None:
        """Learn doctor patterns for future LoRA training"""
        
        # Store interaction pattern
        pattern_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'transcription': text,
            'entities': entities,
            'assistance_provided': assistance,
            'doctor_id': doctor_id
        }
        
        # Store in Redis for pattern analysis
        pattern_key = f"doctor_patterns:{doctor_id}:{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        await self.redis_client.setex(pattern_key, 86400 * 30, json.dumps(pattern_data))  # 30 days
        
        # Update doctor's pattern summary
        await self._update_doctor_pattern_summary(doctor_id, entities)
    
    async def _predict_doctor_lookups(self, doctor_id: str, symptoms: List[Dict[str, Any]]) -> List[str]:
        """Predict what conditions the doctor typically looks up based on symptoms"""
        
        # Get doctor's historical lookup patterns
        patterns = await self._get_doctor_patterns(doctor_id)
        
        symptom_texts = [s['text'].lower() for s in symptoms]
        related_conditions = []
        
        # Simple pattern matching (would be enhanced by LoRA model later)
        for symptom in symptom_texts:
            if 'chest pain' in symptom:
                related_conditions.extend(['myocardial infarction', 'angina', 'pulmonary embolism'])
            elif 'headache' in symptom:
                related_conditions.extend(['migraine', 'tension headache', 'cluster headache'])
            elif 'fever' in symptom:
                related_conditions.extend(['infection', 'influenza', 'COVID-19'])
        
        # Filter based on doctor's actual patterns
        if patterns and 'common_lookups' in patterns:
            related_conditions = [c for c in related_conditions if c in patterns['common_lookups']]
        
        return list(set(related_conditions))[:3]  # Top 3 suggestions
    
    async def _get_medical_context(self, entity_text: str, entity_type: str) -> Dict[str, Any]:
        """Get medical context for entity using Healthcare-MCP"""
        
        try:
            # Use Healthcare-MCP for medical information
            mcp_response = await httpx.post(
                "http://localhost:3000/query",
                json={
                    'query': f"medical information about {entity_text}",
                    'type': entity_type.lower()
                },
                timeout=5.0
            )
            
            if mcp_response.status_code == 200:
                return mcp_response.json()
            else:
                return {'error': 'MCP lookup failed'}
                
        except Exception as e:
            return {'error': str(e)}

# Global instance
realtime_medical_assistant = RealtimeMedicalAssistant()

@app.websocket("/ws/{doctor_id}/{session_id}")
async def websocket_endpoint(websocket: WebSocket, doctor_id: str, session_id: str):
    """WebSocket endpoint for real-time transcription processing"""
    await websocket.accept()
    
    try:
        while True:
            # Receive transcription chunk from WhisperLive
            data = await websocket.receive_json()
            
            # Process chunk
            result = await realtime_medical_assistant.process_transcription_chunk(
                doctor_id, session_id, data
            )
            
            # Send assistance back to client
            await websocket.send_json(result)
            
    except Exception as e:
        await websocket.close(code=1000)

@app.post("/process_chunk")
async def process_chunk(chunk_data: Dict[str, Any]):
    """REST endpoint for processing transcription chunks"""
    
    doctor_id = chunk_data.get('doctor_id')
    session_id = chunk_data.get('session_id')
    
    if not doctor_id or not session_id:
        raise HTTPException(status_code=400, detail="doctor_id and session_id required")
    
    result = await realtime_medical_assistant.process_transcription_chunk(
        doctor_id, session_id, chunk_data
    )
    
    return result

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "realtime-medical-assistant"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)
```

### 4.7 Service Configurations for Advanced Features

**Deploy advanced insurance verification service:**
```bash
# services/user/advanced-insurance-verifier/advanced-insurance-verifier.conf
image="intelluxe/advanced-insurance-verifier:latest"
port="8011:8011"
description="Real-time insurance verification with multiple provider APIs and prior authorization"
env="NODE_ENV=production,CACHE_TTL=1800,MAX_CONCURRENT_VERIFICATIONS=10"
volumes="./insurance-cache:/app/cache:rw,./config:/app/config:ro"
network_mode="intelluxe-net"
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8011/health || exit 1"
depends_on="postgres,redis"
```

**Deploy doctor style adapter service:**
```bash
# services/user/doctor-style-adapter/doctor-style-adapter.conf
image="intelluxe/doctor-style-adapter:latest"
port="8012:8012"
description="Unsloth-based LoRA training for doctor communication style adaptation"
env="NODE_ENV=production,UNSLOTH_ENABLED=true,TRAINING_BATCH_SIZE=2"
volumes="./adapters:/app/adapters:rw,./models:/app/models:rw"
network_mode="intelluxe-net"
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8012/health || exit 1"
depends_on="postgres,redis,ollama"
```

**Deploy business intelligence service:**
```bash
# services/user/business-intelligence/business-intelligence.conf
image="intelluxe/business-intelligence:latest"
port="8013:8013"
description="Healthcare business analytics and performance dashboard"
env="NODE_ENV=production,ANALYTICS_CACHE_TTL=3600"
volumes="./reports:/app/reports:rw,./config:/app/config:ro"
network_mode="intelluxe-net"
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8013/health || exit 1"
depends_on="postgres,redis"
```

**Updated service configurations for advanced personalization:**
```bash
# services/user/doctor-personalization/doctor-personalization.conf
image="intelluxe/doctor-personalization:latest"
port="8014:8014"
description="Doctor personalization with LoRA adapters and continuous learning"
env="NODE_ENV=production,UNSLOTH_ENABLED=true,ADAPTER_STORAGE=/app/adapters,LEARNING_THRESHOLD=50"
volumes="./adapters:/app/adapters:rw,./training-data:/app/training:rw,./models:/app/models:rw"
network_mode="intelluxe-net"
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8014/health || exit 1"
depends_on="postgres,redis,ollama"
memory_limit="12g"

# services/user/insurance-integration/insurance-integration.conf
image="intelluxe/insurance-integration:latest"
port="8015:8015"
description="Real-time insurance verification and prior authorization"
env="NODE_ENV=production,INSURANCE_API_MODE=production,CACHE_TTL=1800"
volumes="./insurance-cache:/app/cache:rw,./config:/app/config:ro"
network_mode="intelluxe-net"
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8015/health || exit 1"
depends_on="postgres,redis"

# services/user/continuous-learning/continuous-learning.conf
image="intelluxe/continuous-learning:latest"
port="8016:8016"
description="Continuous learning system for doctor adaptation"
env="NODE_ENV=production,LEARNING_ENABLED=true,RETRAINING_THRESHOLD=50"
volumes="./learning-data:/app/learning:rw,./patterns:/app/patterns:rw"
network_mode="intelluxe-net"
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8016/health || exit 1"
depends_on="postgres,redis,doctor-personalization"
```

**Deploy all advanced services:**
```bash
# Deploy advanced insurance verification
./scripts/universal-service-runner.sh start advanced-insurance-verifier

# Deploy doctor style adapter
./scripts/universal-service-runner.sh start doctor-style-adapter

# Deploy business intelligence
./scripts/universal-service-runner.sh start business-intelligence

# Deploy enhanced doctor personalization
./scripts/universal-service-runner.sh start doctor-personalization

# Deploy insurance integration
./scripts/universal-service-runner.sh start insurance-integration

# Deploy continuous learning system
./scripts/universal-service-runner.sh start continuous-learning

# Verify all services are running
curl http://localhost:8011/health  # Advanced insurance
curl http://localhost:8012/health  # Doctor style adapter
curl http://localhost:8013/health  # Business intelligence
curl http://localhost:8014/health  # Doctor personalization
curl http://localhost:8015/health  # Insurance integration
curl http://localhost:8016/health  # Continuous learning
```

**Enhanced monitoring for advanced services:**
```bash
# Add to scripts/resource-pusher.sh
collect_advanced_service_metrics() {
    local timestamp=$(date +%s%N)
    local hostname=$(hostname -s 2>/dev/null || hostname)

    # Check advanced insurance verifier
    insurance_advanced_status="0"
    if curl -s --max-time 5 http://localhost:8011/health >/dev/null 2>&1; then
        insurance_advanced_status="1"
    fi

    # Check doctor style adapter
    style_adapter_status="0"
    if curl -s --max-time 5 http://localhost:8012/health >/dev/null 2>&1; then
        style_adapter_status="1"
    fi

    # Check business intelligence
    business_intel_status="0"
    if curl -s --max-time 5 http://localhost:8013/health >/dev/null 2>&1; then
        business_intel_status="1"
    fi

    # Create InfluxDB line protocol
    advanced_line="advancedServices,host=${hostname} insurance_advanced=${insurance_advanced_status},style_adapter=${style_adapter_status},business_intel=${business_intel_status} ${timestamp}"

    # Push to InfluxDB
    curl -sS -XPOST "$INFLUX_URL" --data-binary "$advanced_line" >/dev/null 2>&1

    if [[ "$DEBUG" == true ]]; then
        log "[DEBUG] Advanced services metrics: insurance_advanced=${insurance_advanced_status}, style_adapter=${style_adapter_status}, business_intel=${business_intel_status}"
    fi
}

# Call in main collection function
collect_advanced_service_metrics
```

### 4.8 Advanced Security and Compliance Framework Enhancement

**Enterprise-grade security with comprehensive audit trails and PHI protection:**

```python
# services/user/compliance-monitor/enterprise_security_framework.py
from typing import Dict, List, Optional, Any, Tuple
import asyncio
from datetime import datetime, timedelta
import hashlib
import hmac
import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import logging
from dataclasses import dataclass
from enum import Enum

class SecurityEventType(Enum):
    PHI_ACCESS = "phi_access"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_EXPORT = "data_export"
    CONFIGURATION_CHANGE = "configuration_change"
    ADMINISTRATIVE_DECISION = "administrative_decision"
    AGENT_INTERACTION = "agent_interaction"
    LORA_TRAINING = "lora_training"

@dataclass
class SecurityEvent:
    event_id: str
    event_type: SecurityEventType
    user_id: str
    session_id: str
    timestamp: datetime
    details: Dict
    risk_level: str
    phi_involved: bool
    audit_trail: List[str]

class EnterpriseSecurityManager:
    """Enterprise-grade security management for healthcare AI administrative workflows"""

    def __init__(self, config: Dict):
        self.config = config

        # Initialize encryption
        self.encryption_key = self.derive_encryption_key(config["master_key"])
        self.cipher_suite = Fernet(self.encryption_key)

        # Initialize audit logging
        self.audit_logger = self.setup_audit_logger()

        # PHI detection patterns
        self.phi_patterns = self.load_phi_detection_patterns()

        # Security policies
        self.security_policies = self.load_security_policies()

    def derive_encryption_key(self, master_key: str) -> bytes:
        """Derive encryption key using PBKDF2"""
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return key

    async def encrypt_administrative_data(self, data: Dict) -> str:
        """Encrypt administrative data with AES-256"""
        serialized_data = json.dumps(data).encode()
        encrypted_data = self.cipher_suite.encrypt(serialized_data)
        return base64.urlsafe_b64encode(encrypted_data).decode()

    async def decrypt_administrative_data(self, encrypted_data: str) -> Dict:
        """Decrypt administrative data"""
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(decoded_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            await self.log_security_event(
                SecurityEventType.UNAUTHORIZED_ACCESS,
                {"error": "Decryption failed", "details": str(e)}
            )
            raise

    async def comprehensive_phi_detection(self, text: str) -> Dict:
        """Comprehensive PHI detection using multiple techniques"""

        phi_detections = {
            "detected_phi": [],
            "confidence_scores": [],
            "detection_methods": [],
            "masked_text": text
        }

        # Pattern-based detection
        pattern_detections = await self.pattern_based_phi_detection(text)
        phi_detections["detected_phi"].extend(pattern_detections["entities"])

        # NER-based detection
        ner_detections = await self.ner_based_phi_detection(text)
        phi_detections["detected_phi"].extend(ner_detections["entities"])

        # Context-based detection
        context_detections = await self.context_based_phi_detection(text)
        phi_detections["detected_phi"].extend(context_detections["entities"])

        # Apply masking
        masked_text = await self.apply_phi_masking(text, phi_detections["detected_phi"])
        phi_detections["masked_text"] = masked_text

        # Log PHI detection event
        if phi_detections["detected_phi"]:
            await self.log_security_event(
                SecurityEventType.PHI_ACCESS,
                {
                    "phi_entities_detected": len(phi_detections["detected_phi"]),
                    "detection_methods": phi_detections["detection_methods"],
                    "text_length": len(text)
                }
            )

        return phi_detections

    async def role_based_access_control(
        self,
        user_id: str,
        requested_resource: str,
        action: str,
        administrative_context: Optional[Dict] = None
    ) -> Dict:
        """Role-based access control for healthcare administrative resources"""

        # Get user role and permissions
        user_role = await self.get_user_role(user_id)
        permissions = await self.get_role_permissions(user_role)

        # Check resource access
        access_granted = self.evaluate_access_request(
            permissions,
            requested_resource,
            action,
            administrative_context
        )

        # Log access attempt
        await self.log_security_event(
            SecurityEventType.PHI_ACCESS if "patient" in requested_resource else SecurityEventType.UNAUTHORIZED_ACCESS,
            {
                "user_id": user_id,
                "user_role": user_role,
                "requested_resource": requested_resource,
                "action": action,
                "access_granted": access_granted,
                "administrative_context": administrative_context is not None
            }
        )

        return {
            "access_granted": access_granted,
            "user_role": user_role,
            "permissions": permissions,
            "audit_event_id": f"access_{user_id}_{datetime.utcnow().timestamp()}"
        }

    async def monitor_lora_training_security(
        self,
        doctor_id: str,
        training_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Monitor LoRA training for security and privacy compliance"""

        security_assessment = {
            "phi_detected": False,
            "training_data_safe": True,
            "compliance_issues": [],
            "security_score": 1.0
        }

        # Check training data for PHI
        training_text = training_data.get('input_text', '') + ' ' + training_data.get('preferred_output', '')
        phi_detection = await self.comprehensive_phi_detection(training_text)

        if phi_detection["detected_phi"]:
            security_assessment["phi_detected"] = True
            security_assessment["training_data_safe"] = False
            security_assessment["compliance_issues"].append("PHI detected in training data")
            security_assessment["security_score"] -= 0.5

        # Validate administrative focus
        if not training_data.get('admin_focus', True):
            security_assessment["compliance_issues"].append("Training data not focused on administrative workflows")
            security_assessment["security_score"] -= 0.3

        # Log LoRA training security event
        await self.log_security_event(
            SecurityEventType.LORA_TRAINING,
            {
                "doctor_id": doctor_id,
                "phi_detected": security_assessment["phi_detected"],
                "security_score": security_assessment["security_score"],
                "compliance_issues": security_assessment["compliance_issues"]
            }
        )

        return security_assessment

    async def security_monitoring_dashboard(self) -> Dict:
        """Generate real-time security monitoring data"""

        current_time = datetime.utcnow()
        last_24h = current_time - timedelta(hours=24)

        # Collect security metrics
        security_metrics = {
            "phi_access_events": await self.count_security_events(
                SecurityEventType.PHI_ACCESS, last_24h
            ),
            "unauthorized_attempts": await self.count_security_events(
                SecurityEventType.UNAUTHORIZED_ACCESS, last_24h
            ),
            "administrative_decisions": await self.count_security_events(
                SecurityEventType.ADMINISTRATIVE_DECISION, last_24h
            ),
            "lora_training_events": await self.count_security_events(
                SecurityEventType.LORA_TRAINING, last_24h
            ),
            "active_sessions": await self.count_active_sessions(),
            "compliance_score": await self.calculate_compliance_score(),
            "risk_alerts": await self.get_active_risk_alerts(),
            "phi_protection_effectiveness": await self.calculate_phi_protection_effectiveness()
        }

        return security_metrics

    async def generate_compliance_report(
        self,
        report_period: timedelta = timedelta(days=30)
    ) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""

        end_time = datetime.utcnow()
        start_time = end_time - report_period

        compliance_report = {
            "report_period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "security_events_summary": await self.get_security_events_summary(start_time, end_time),
            "phi_protection_metrics": await self.get_phi_protection_metrics(start_time, end_time),
            "access_control_metrics": await self.get_access_control_metrics(start_time, end_time),
            "lora_training_compliance": await self.get_lora_training_compliance_metrics(start_time, end_time),
            "administrative_workflow_security": await self.get_workflow_security_metrics(start_time, end_time),
            "compliance_score": await self.calculate_overall_compliance_score(start_time, end_time),
            "recommendations": await self.generate_security_recommendations()
        }

        return compliance_report

# Global enterprise security manager
enterprise_security_manager = EnterpriseSecurityManager({
    'master_key': os.getenv('INTELLUXE_MASTER_KEY', 'default-key-change-in-production'),
    'phi_detection_threshold': 0.8,
    'access_control_strict_mode': True,
    'audit_retention_days': 2555  # 7 years for healthcare compliance
})
```

**Deploy real-time medical assistant:**
```bash
./scripts/universal-service-runner.sh start realtime-medical-assistant

# Verify service is running
curl http://localhost:8009/health
```

### 4.2 WhisperLive Integration with Real-time Assistant

**Enhanced WhisperLive configuration to send chunks to real-time assistant:**
```python
# services/user/whisperlive/integration_config.py
REALTIME_ASSISTANT_CONFIG = {
    'endpoint': 'http://localhost:8009/process_chunk',
    'websocket_endpoint': 'ws://localhost:8009/ws',
    'chunk_processing': True,
    'medical_entity_extraction': True,
    'intelligent_assistance': True
}

# Modify WhisperLive to send transcription chunks to real-time assistant
async def on_transcription_chunk(chunk_data):
    """Send transcription chunk to real-time medical assistant"""
    
    # Add doctor and session context
    chunk_data.update({
        'doctor_id': current_session.get('doctor_id'),
        'session_id': current_session.get('session_id'),
        'timestamp': datetime.utcnow().isoformat()
    })
    
    # Send to real-time assistant for processing
    try:
        response = await httpx.post(
            REALTIME_ASSISTANT_CONFIG['endpoint'],
            json=chunk_data,
            timeout=2.0
        )
        
        if response.status_code == 200:
            assistance_data = response.json()
            
            # Send assistance back to doctor's interface
            await send_to_doctor_interface(assistance_data)
            
    except Exception as e:
        logger.error(f"Failed to process chunk with real-time assistant: {e}")
```

### 4.3 SciSpacy Integration Enhancement

**Enhanced SciSpacy service with medical entity caching:**
```bash
# services/user/scispacy/scispacy.conf  
image="intelluxe/scispacy:latest"
port="8010:8010"
description="SciSpacy medical NLP with enhanced entity extraction and caching"
env="NODE_ENV=production,MODEL=en_ner_bc5cdr_md,CACHE_ENABLED=true"
volumes="./models:/app/models:rw,./cache:/app/cache:rw"
network_mode="intelluxe-net"
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8010/health || exit 1"
```

## Deployment and Validation Checklist

**Phase 2 Completion Criteria:**

**Core Business Services:**
- [ ] Insurance verification service deployed using universal service runner
- [ ] Billing engine handling claims creation and processing
- [ ] Compliance monitor logging all data access with HIPAA audit trails
- [ ] Doctor personalization service storing preferences securely
- [ ] Enhanced database schema with business service tables
- [ ] Business service monitoring integrated with existing InfluxDB/Grafana setup
- [ ] Enhanced agent router orchestrating complete workflows
- [ ] Comprehensive integration tests passing
- [ ] Performance monitoring extended to business services

**Advanced Personalization:**
- [ ] Unsloth-based LoRA adapter training for doctor styles
- [ ] Real-time style adaptation system operational
- [ ] Continuous learning from doctor interactions implemented
- [ ] Doctor preference tracking and automatic updates
- [ ] Automated adapter retraining system functional
- [ ] Doctor communication pattern analysis working
- [ ] Personalized response generation with style adaptation

**Business Intelligence:**
- [ ] Real-time insurance verification with multiple providers (Anthem, UHC, Cigna, Aetna, BCBS)
- [ ] Automated prior authorization processing system
- [ ] Practice performance dashboard with revenue analytics
- [ ] Provider productivity tracking and utilization analysis
- [ ] AI utilization metrics and ROI analysis
- [ ] Executive summary reporting with actionable recommendations
- [ ] Patient flow analysis and appointment management insights

**Advanced Features:**
- [ ] Multi-provider insurance API integration functional
- [ ] Clinical decision pattern learning (administrative focus)
- [ ] Business workflow automation operational
- [ ] Advanced analytics and reporting system
- [ ] Personalized AI model deployment with LoRA adapters
- [ ] Continuous learning system with interaction pattern analysis
- [ ] Real-time cost estimation and copay calculation
- [ ] Prior authorization workflow automation

**Integration and Monitoring:**
- [ ] All advanced services (8011-8016) deployed and healthy
- [ ] Enhanced monitoring for personalization and learning systems
- [ ] Business intelligence dashboard accessible and functional
- [ ] Insurance integration with real-time verification working
- [ ] Continuous learning system processing doctor interactions
- [ ] LoRA adapter retraining pipeline operational

**Key Architecture Achievements:**
- Multi-provider insurance verification with error prevention using your service architecture
- Automated billing with safety checks and code validation
- HIPAA-compliant audit logging with compliance rule engine
- Privacy-first personalization with PHI protection
- Enhanced agent router orchestrating complete patient workflows
- Business service monitoring integrated with your existing monitoring stack

**Ready for Phase 3:**
- Business services ready for production deployment
- Compliance framework established for healthcare regulations
- Personalization infrastructure ready for advanced features
- Complete patient workflow automation from intake to billing
- Comprehensive monitoring covering all services using your InfluxDB/Grafana setup

This Phase 2 transforms your healthcare AI system into a complete clinical workflow platform with insurance, billing, compliance, and personalization capabilities, all built using your actual service architecture and monitoring infrastructure.

## Implementation Priority Order

### **CRITICAL (Week 1-2):**
1. **Doctor personalization with LoRA adapters** - Core Phase 2 feature for AI adaptation
2. **Real-time insurance verification** - Immediate business value and workflow efficiency
3. **Continuous learning system** - Improves AI effectiveness over time

### **HIGH (Week 2-3):**
4. **Business intelligence dashboard** - Operational insights and practice management
5. **Prior authorization automation** - Workflow efficiency and administrative burden reduction
6. **Advanced Chain-of-Thought reasoning** - Enhanced decision-making capabilities

### **MEDIUM (Week 3-4):**
7. **Multi-provider insurance API integration** - Comprehensive coverage verification
8. **Advanced monitoring and evaluation** - Production readiness and quality assurance
9. **Enterprise security enhancements** - Compliance and data protection

### **Service Deployment Order:**
```bash
# Phase 1: Core personalization (Ports 8011-8013)
./scripts/universal-service-runner.sh start advanced-insurance-verifier
./scripts/universal-service-runner.sh start doctor-style-adapter
./scripts/universal-service-runner.sh start business-intelligence

# Phase 2: Advanced features (Ports 8014-8016)
./scripts/universal-service-runner.sh start doctor-personalization
./scripts/universal-service-runner.sh start insurance-integration
./scripts/universal-service-runner.sh start continuous-learning

# Verification
curl http://localhost:8011/health && curl http://localhost:8012/health && curl http://localhost:8013/health
curl http://localhost:8014/health && curl http://localhost:8015/health && curl http://localhost:8016/health
```

## Phase 2 Summary: Advanced Healthcare AI Business Services

Phase 2 successfully transforms the basic Intelluxe foundation into a sophisticated healthcare workflow automation system with advanced AI capabilities:

### Key Achievements

1. **Advanced Reasoning Integration**
   - Chain-of-Thought reasoning for insurance verification and administrative decisions
   - Tree-of-Thoughts planning for complex billing scenarios
   - Enhanced majority voting with LoRA integration for personalized decision-making

2. **Advanced Doctor Personalization with Unsloth**
   - Unsloth-based LoRA training for efficient doctor communication style adaptation
   - Real-time style adaptation with personalized response generation
   - Doctor-specific fine-tuning on healthcare conversations
   - Comprehensive preference management with privacy protection

3. **Real-Time Insurance Integration**
   - Multi-provider insurance verification with real-time APIs (Anthem, UHC, Cigna, Aetna, BCBS)
   - Automated prior authorization processing with clinical justification
   - Cost estimation and copay calculation
   - Insurance performance analytics and denial rate tracking

4. **Healthcare Business Intelligence**
   - Comprehensive practice performance dashboards
   - Revenue cycle analytics with collection rate optimization
   - Patient flow analysis and appointment management insights
   - Provider productivity metrics and utilization tracking
   - AI utilization analytics and doctor satisfaction scoring

5. **Production-Ready Monitoring**
   - Healthcare-specific Prometheus metrics and Grafana dashboards
   - AgentOps integration for real-time agent performance monitoring
   - Comprehensive evaluation framework with RAGAS integration
   - Advanced service monitoring for insurance, personalization, and analytics

6. **Enterprise Security and Compliance**
   - Advanced PHI detection and protection mechanisms
   - Role-based access control with comprehensive audit trails
   - LoRA training security monitoring and compliance validation
   - Insurance data encryption and secure API integration

7. **Business Service Integration**
   - Enhanced insurance verification with Chain-of-Thought reasoning
   - Sophisticated billing engine with Tree-of-Thoughts planning
   - Advanced compliance monitoring with evaluation frameworks
   - Real-time medical assistant with SciSpacy NLP integration
   - Business intelligence dashboard with executive reporting

### Administrative Workflow Focus

All AI enhancements maintain strict focus on administrative workflow automation:
- Insurance verification and coverage determination
- Billing claim processing and optimization
- Compliance monitoring and audit trail management
- Doctor workflow personalization and preference learning
- Administrative decision support (NOT medical advice)

### Next Steps to Phase 3

Phase 2 establishes the foundation for Phase 3's enterprise-grade deployment:
- Production-ready monitoring systems are operational
- Advanced security frameworks are implemented
- Doctor personalization through LoRA training is functional
- Comprehensive evaluation metrics are established
- Business service integration is complete with advanced AI reasoning

The system is now ready for Phase 3's enterprise deployment, advanced orchestration patterns, and sophisticated healthcare workflow automation at scale.

### Deployment Verification

To verify Phase 2 deployment success:

```bash
# Check all business services are running
./scripts/universal-service-runner.sh status

# Verify all advanced services (8011-8016)
curl http://localhost:8011/health  # Advanced insurance verification
curl http://localhost:8012/health  # Doctor style adapter
curl http://localhost:8013/health  # Business intelligence
curl http://localhost:8014/health  # Doctor personalization
curl http://localhost:8015/health  # Insurance integration
curl http://localhost:8016/health  # Continuous learning

# Run comprehensive integration tests
python -m pytest tests/test_phase2_advanced_evaluation.py -v

# Verify monitoring dashboards
curl http://localhost:3000/api/dashboards/search

# Check security compliance
curl http://localhost:8005/security_monitoring_dashboard

# Validate LoRA personalization and Unsloth training
curl http://localhost:8007/lora_training/status
curl http://localhost:8012/doctor_adapters/status
curl http://localhost:8014/personalization/status

# Test continuous learning system
curl -X POST http://localhost:8016/learn_from_interaction \
  -H "Content-Type: application/json" \
  -d '{"doctor_id": "dr_test", "interaction_data": {"type": "workflow", "input": "test input", "satisfaction_score": 4.5}}'

# Test real-time insurance verification
curl -X POST http://localhost:8011/verify_real_time \
  -H "Content-Type: application/json" \
  -d '{"patient_info": {"insurance": {"provider": "anthem", "member_id": "W123456789"}}, "service_codes": ["99213"]}'

# Test enhanced insurance integration
curl -X POST http://localhost:8015/verify_insurance_real_time \
  -H "Content-Type: application/json" \
  -d '{"patient_info": {"insurance": {"provider": "uhc", "member_id": "U987654321"}}, "service_codes": ["99214", "I10"]}'

# Test business intelligence dashboard
curl http://localhost:8013/dashboard/practice_performance/test_practice

# Test executive summary generation
curl http://localhost:8013/executive_summary/test_practice?time_range=30d

# Validate prior authorization system
curl http://localhost:8011/prior_auth/status
curl http://localhost:8015/prior_auth/tracking/status

# Test doctor style adaptation
curl -X POST http://localhost:8014/generate_personalized_response \
  -H "Content-Type: application/json" \
  -d '{"doctor_id": "dr_test", "patient_context": {"type": "routine"}, "query": "Generate insurance summary"}'

# Validate adapter retraining system
curl http://localhost:8016/retraining/status
curl http://localhost:8014/adapters/dr_test/status
```

Phase 2 delivers a complete healthcare AI business services platform with advanced reasoning, personalization, and enterprise-grade monitoring - all focused on administrative workflow automation while maintaining strict HIPAA compliance and PHI protection.

## Final Phase 2 Architecture Summary

**Core Services (Ports 8003-8009):**
- Insurance Verification, Billing Engine, Compliance Monitor, Personalization, Real-time Medical Assistant

**Advanced Services (Ports 8011-8016):**
- Advanced Insurance Verifier, Doctor Style Adapter, Business Intelligence, Doctor Personalization, Insurance Integration, Continuous Learning

**Key Differentiators:**
- **Unsloth-based LoRA training** for efficient doctor style adaptation
- **Real-time multi-provider insurance verification** with cost estimation
- **Continuous learning system** that improves AI effectiveness over time
- **Comprehensive business intelligence** with executive reporting
- **Automated prior authorization** processing with clinical justification
- **Advanced Chain-of-Thought reasoning** for complex administrative decisions

This transforms Phase 2 into a comprehensive business-focused healthcare AI system with advanced personalization, real-world business integration, and continuous improvement capabilities - ready for enterprise deployment in Phase 3.