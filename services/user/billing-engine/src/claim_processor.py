"""
Claim Processing with Tree of Thoughts reasoning for complex billing decisions
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx
from models.billing_models import (
    BillingAnalytics,
    ClaimRequest,
    ClaimResult,
    ClaimStatus,
    ServiceLineItem,
)

logger = logging.getLogger(__name__)


class TreeOfThoughtsStep:
    """Individual step in Tree of Thoughts reasoning for billing"""
    
    def __init__(
        self,
        step_id: str,
        step_type: str,
        question: str,
        options: List[str],
        selected_option: str,
        reasoning: str,
        confidence: float,
        dependencies: List[str] = None
    ):
        self.step_id = step_id
        self.step_type = step_type
        self.question = question
        self.options = options
        self.selected_option = selected_option
        self.reasoning = reasoning
        self.confidence = confidence
        self.dependencies = dependencies or []
        self.timestamp = datetime.utcnow()


class BillingTreeOfThoughtsProcessor:
    """Tree of Thoughts reasoning for complex billing decisions"""
    
    def __init__(self, insurance_verification_url: str):
        self.insurance_verification_url = insurance_verification_url
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def process_claim_reasoning(
        self,
        claim_request: ClaimRequest,
        session_id: str
    ) -> Dict[str, Any]:
        """Process Tree of Thoughts reasoning for claim submission"""
        
        reasoning_id = f"claim_tot_{session_id}_{uuid4().hex[:8]}"
        
        # Define the decision tree for claim processing
        reasoning_steps = []
        
        # Step 1: Insurance Eligibility Assessment
        eligibility_step = await self._assess_insurance_eligibility(
            claim_request, reasoning_id
        )
        reasoning_steps.append(eligibility_step)
        
        # Step 2: Code Validation and Compliance
        validation_step = await self._validate_codes_and_compliance(
            claim_request, reasoning_id, eligibility_step
        )
        reasoning_steps.append(validation_step)
        
        # Step 3: Prior Authorization Requirements
        prior_auth_step = await self._check_prior_authorization_requirements(
            claim_request, reasoning_id, [eligibility_step, validation_step]
        )
        reasoning_steps.append(prior_auth_step)
        
        # Step 4: Billing Strategy Selection
        strategy_step = await self._select_billing_strategy(
            claim_request, reasoning_id, reasoning_steps
        )
        reasoning_steps.append(strategy_step)
        
        # Step 5: Risk Assessment
        risk_step = await self._assess_claim_risk(
            claim_request, reasoning_id, reasoning_steps
        )
        reasoning_steps.append(risk_step)
        
        # Synthesize final decision
        final_decision = await self._synthesize_claim_decision(reasoning_steps)
        
        return {
            "reasoning_id": reasoning_id,
            "reasoning_type": "tree_of_thoughts_billing",
            "decision_tree": [self._serialize_step(step) for step in reasoning_steps],
            "final_decision": final_decision,
            "processing_recommendations": final_decision["recommendations"],
            "confidence_score": final_decision["confidence"],
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def _assess_insurance_eligibility(
        self,
        claim_request: ClaimRequest,
        reasoning_id: str
    ) -> TreeOfThoughtsStep:
        """Assess insurance eligibility as first step in decision tree"""
        
        step_id = f"{reasoning_id}_eligibility"
        
        # Check insurance eligibility via insurance verification service
        eligibility_verified = await self._verify_insurance_eligibility(claim_request)
        
        options = [
            "proceed_with_active_coverage",
            "proceed_with_coverage_concerns", 
            "hold_for_eligibility_verification",
            "reject_due_to_no_coverage"
        ]
        
        if eligibility_verified.get("coverage_active", False):
            selected_option = "proceed_with_active_coverage"
            reasoning = f"""
            Insurance eligibility verified:
            - Coverage Status: Active
            - Member ID: {claim_request.member_id}
            - Benefits Available: Yes
            - Copay: ${eligibility_verified.get('copay_amount', 0)}
            - Deductible Remaining: ${eligibility_verified.get('deductible_remaining', 0)}
            
            Decision: Proceed with claim submission as coverage is active and benefits are available.
            """
            confidence = 0.9
        elif eligibility_verified.get("status") == "pending":
            selected_option = "hold_for_eligibility_verification"
            reasoning = f"""
            Insurance eligibility pending verification:
            - Verification Status: Pending
            - Member ID: {claim_request.member_id}
            - Issues: {eligibility_verified.get('verification_errors', [])}
            
            Decision: Hold claim submission until eligibility is confirmed.
            """
            confidence = 0.6
        else:
            selected_option = "reject_due_to_no_coverage"
            reasoning = f"""
            Insurance eligibility failed:
            - Coverage Status: Inactive/Unknown
            - Errors: {eligibility_verified.get('verification_errors', [])}
            
            Decision: Cannot proceed with claim submission without valid coverage.
            """
            confidence = 0.95
        
        return TreeOfThoughtsStep(
            step_id=step_id,
            step_type="insurance_eligibility",
            question="Should we proceed with claim submission based on insurance eligibility?",
            options=options,
            selected_option=selected_option,
            reasoning=reasoning,
            confidence=confidence
        )
    
    async def _validate_codes_and_compliance(
        self,
        claim_request: ClaimRequest,
        reasoning_id: str,
        eligibility_step: TreeOfThoughtsStep
    ) -> TreeOfThoughtsStep:
        """Validate medical codes and compliance requirements"""
        
        step_id = f"{reasoning_id}_validation"
        
        # Validate all service codes
        code_validation_results = []
        for line_item in claim_request.service_line_items:
            validation = await self._validate_service_code(line_item.service_code)
            code_validation_results.append({
                "code": line_item.service_code,
                "valid": validation["valid"],
                "issues": validation.get("issues", [])
            })
        
        # Check diagnosis code alignment
        diagnosis_alignment = await self._check_diagnosis_alignment(claim_request)
        
        options = [
            "proceed_all_codes_valid",
            "proceed_with_minor_corrections",
            "hold_for_code_review",
            "reject_invalid_codes"
        ]
        
        valid_codes = sum(1 for result in code_validation_results if result["valid"])
        total_codes = len(code_validation_results)
        
        if valid_codes == total_codes and diagnosis_alignment["aligned"]:
            selected_option = "proceed_all_codes_valid"
            reasoning = f"""
            Code validation successful:
            - Service Codes Valid: {valid_codes}/{total_codes}
            - Diagnosis Alignment: ✓ Appropriate
            - Compliance Check: ✓ Passed
            - Primary Diagnosis: {claim_request.primary_diagnosis}
            
            Decision: All codes are valid and appropriately aligned with diagnoses.
            """
            confidence = 0.95
        elif valid_codes >= total_codes * 0.8:
            selected_option = "proceed_with_minor_corrections"
            reasoning = f"""
            Code validation with minor issues:
            - Service Codes Valid: {valid_codes}/{total_codes}
            - Minor Issues: {[r for r in code_validation_results if not r['valid']]}
            - Diagnosis Alignment: {'✓' if diagnosis_alignment['aligned'] else '?'}
            
            Decision: Proceed with automatic corrections for minor issues.
            """
            confidence = 0.75
        else:
            selected_option = "hold_for_code_review"
            reasoning = f"""
            Code validation requires review:
            - Service Codes Valid: {valid_codes}/{total_codes}
            - Significant Issues Found: {[r for r in code_validation_results if not r['valid']]}
            - Diagnosis Alignment: {'✓' if diagnosis_alignment['aligned'] else '✗'}
            
            Decision: Hold for manual review due to significant code validation issues.
            """
            confidence = 0.8
        
        return TreeOfThoughtsStep(
            step_id=step_id,
            step_type="code_validation",
            question="Are the medical codes valid and compliant for claim submission?",
            options=options,
            selected_option=selected_option,
            reasoning=reasoning,
            confidence=confidence,
            dependencies=[eligibility_step.step_id]
        )
    
    async def _check_prior_authorization_requirements(
        self,
        claim_request: ClaimRequest,
        reasoning_id: str,
        previous_steps: List[TreeOfThoughtsStep]
    ) -> TreeOfThoughtsStep:
        """Check if prior authorization is required for any services"""
        
        step_id = f"{reasoning_id}_prior_auth"
        
        # Check which services require prior authorization
        auth_required_services = []
        for line_item in claim_request.service_line_items:
            if await self._requires_prior_authorization(line_item.service_code):
                auth_required_services.append(line_item.service_code)
        
        options = [
            "proceed_no_auth_required",
            "proceed_auth_verified",
            "request_prior_authorization",
            "hold_pending_authorization"
        ]
        
        if not auth_required_services:
            selected_option = "proceed_no_auth_required"
            reasoning = f"""
            Prior authorization assessment:
            - Services Requiring Auth: None
            - Total Services: {len(claim_request.service_line_items)}
            - Authorization Status: Not required
            
            Decision: No prior authorization required for any services.
            """
            confidence = 0.9
        else:
            # For now, assume we need to request authorization
            selected_option = "request_prior_authorization"
            reasoning = f"""
            Prior authorization assessment:
            - Services Requiring Auth: {auth_required_services}
            - Total Services: {len(claim_request.service_line_items)}
            - Authorization Status: Required but not verified
            
            Decision: Request prior authorization before claim submission.
            """
            confidence = 0.85
        
        return TreeOfThoughtsStep(
            step_id=step_id,
            step_type="prior_authorization",
            question="Is prior authorization handled appropriately for this claim?",
            options=options,
            selected_option=selected_option,
            reasoning=reasoning,
            confidence=confidence,
            dependencies=[step.step_id for step in previous_steps]
        )
    
    async def _select_billing_strategy(
        self,
        claim_request: ClaimRequest,
        reasoning_id: str,
        previous_steps: List[TreeOfThoughtsStep]
    ) -> TreeOfThoughtsStep:
        """Select optimal billing strategy based on previous assessments"""
        
        step_id = f"{reasoning_id}_strategy"
        
        # Analyze previous steps to determine best strategy
        eligibility_ok = any(
            step.selected_option == "proceed_with_active_coverage" 
            for step in previous_steps 
            if step.step_type == "insurance_eligibility"
        )
        
        codes_ok = any(
            step.selected_option in ["proceed_all_codes_valid", "proceed_with_minor_corrections"]
            for step in previous_steps 
            if step.step_type == "code_validation"
        )
        
        auth_ok = any(
            step.selected_option in ["proceed_no_auth_required", "proceed_auth_verified"]
            for step in previous_steps 
            if step.step_type == "prior_authorization"
        )
        
        options = [
            "submit_claim_immediately",
            "submit_with_corrections",
            "batch_submit_with_similar_claims",
            "hold_for_manual_review",
            "reject_claim_submission"
        ]
        
        if eligibility_ok and codes_ok and auth_ok:
            selected_option = "submit_claim_immediately"
            reasoning = f"""
            Billing strategy analysis:
            - Eligibility: ✓ Verified
            - Code Validation: ✓ Passed
            - Prior Authorization: ✓ Handled
            - Total Charges: ${claim_request.total_charges}
            - Risk Level: Low
            
            Decision: Submit claim immediately for optimal processing speed.
            """
            confidence = 0.9
        elif eligibility_ok and codes_ok:
            selected_option = "submit_with_corrections"
            reasoning = f"""
            Billing strategy analysis:
            - Eligibility: ✓ Verified
            - Code Validation: ✓ Passed (with corrections)
            - Prior Authorization: ? Pending
            - Risk Level: Medium
            
            Decision: Submit claim with automatic corrections applied.
            """
            confidence = 0.75
        else:
            selected_option = "hold_for_manual_review"
            reasoning = f"""
            Billing strategy analysis:
            - Eligibility: {'✓' if eligibility_ok else '✗'}
            - Code Validation: {'✓' if codes_ok else '✗'}
            - Prior Authorization: {'✓' if auth_ok else '✗'}
            - Risk Level: High
            
            Decision: Hold for manual review due to multiple issues.
            """
            confidence = 0.85
        
        return TreeOfThoughtsStep(
            step_id=step_id,
            step_type="billing_strategy",
            question="What is the optimal billing strategy for this claim?",
            options=options,
            selected_option=selected_option,
            reasoning=reasoning,
            confidence=confidence,
            dependencies=[step.step_id for step in previous_steps]
        )
    
    async def _assess_claim_risk(
        self,
        claim_request: ClaimRequest,
        reasoning_id: str,
        previous_steps: List[TreeOfThoughtsStep]
    ) -> TreeOfThoughtsStep:
        """Assess overall risk of claim denial or issues"""
        
        step_id = f"{reasoning_id}_risk"
        
        # Calculate risk factors
        risk_factors = []
        risk_score = 0.0
        
        # High charge amount increases risk
        if claim_request.total_charges > Decimal('1000'):
            risk_factors.append("High claim amount")
            risk_score += 0.2
        
        # Multiple services increase complexity risk
        if len(claim_request.service_line_items) > 5:
            risk_factors.append("Multiple services")
            risk_score += 0.1
        
        # Check previous step outcomes
        for step in previous_steps:
            if step.confidence < 0.8:
                risk_factors.append(f"Low confidence in {step.step_type}")
                risk_score += (0.8 - step.confidence)
        
        options = [
            "low_risk_proceed",
            "medium_risk_proceed_with_monitoring",
            "high_risk_additional_review",
            "very_high_risk_hold"
        ]
        
        if risk_score <= 0.2:
            selected_option = "low_risk_proceed"
            risk_level = "Low"
            confidence = 0.9
        elif risk_score <= 0.5:
            selected_option = "medium_risk_proceed_with_monitoring"
            risk_level = "Medium"
            confidence = 0.75
        elif risk_score <= 0.8:
            selected_option = "high_risk_additional_review"
            risk_level = "High"
            confidence = 0.8
        else:
            selected_option = "very_high_risk_hold"
            risk_level = "Very High"
            confidence = 0.85
        
        reasoning = f"""
        Risk assessment for claim submission:
        - Overall Risk Level: {risk_level}
        - Risk Score: {risk_score:.2f}
        - Risk Factors: {risk_factors or ['None identified']}
        - Claim Value: ${claim_request.total_charges}
        - Complexity Score: {len(claim_request.service_line_items)} services
        
        Decision: {selected_option.replace('_', ' ').title()}
        """
        
        return TreeOfThoughtsStep(
            step_id=step_id,
            step_type="risk_assessment",
            question="What is the risk level for this claim submission?",
            options=options,
            selected_option=selected_option,
            reasoning=reasoning,
            confidence=confidence,
            dependencies=[step.step_id for step in previous_steps]
        )
    
    async def _synthesize_claim_decision(
        self,
        reasoning_steps: List[TreeOfThoughtsStep]
    ) -> Dict[str, Any]:
        """Synthesize final claim processing decision from all reasoning steps"""
        
        # Extract key decisions from each step
        final_decisions = {}
        for step in reasoning_steps:
            final_decisions[step.step_type] = step.selected_option
        
        # Calculate overall confidence
        overall_confidence = sum(step.confidence for step in reasoning_steps) / len(reasoning_steps)
        
        # Determine final action
        if (final_decisions.get("billing_strategy") == "submit_claim_immediately" and
            final_decisions.get("risk_assessment") == "low_risk_proceed"):
            final_action = "SUBMIT_IMMEDIATELY"
            recommendations = [
                "Submit claim immediately for optimal processing",
                "Monitor for standard processing timeline",
                "No additional review required"
            ]
        elif final_decisions.get("billing_strategy") in ["submit_with_corrections", "submit_claim_immediately"]:
            final_action = "SUBMIT_WITH_MONITORING"
            recommendations = [
                "Submit claim with enhanced monitoring",
                "Review claim status in 48-72 hours",
                "Be prepared for potential follow-up questions"
            ]
        else:
            final_action = "HOLD_FOR_REVIEW"
            recommendations = [
                "Hold claim for manual review",
                "Address identified issues before submission",
                "Consider alternative billing strategies"
            ]
        
        return {
            "final_action": final_action,
            "confidence": overall_confidence,
            "recommendations": recommendations,
            "decision_summary": {
                "eligibility_status": final_decisions.get("insurance_eligibility"),
                "code_validation_status": final_decisions.get("code_validation"),
                "authorization_status": final_decisions.get("prior_authorization"),
                "billing_strategy": final_decisions.get("billing_strategy"),
                "risk_level": final_decisions.get("risk_assessment")
            }
        }
    
    # Helper methods for validations
    async def _verify_insurance_eligibility(self, claim_request: ClaimRequest) -> Dict[str, Any]:
        """Verify insurance eligibility via insurance verification service"""
        try:
            response = await self.client.post(
                f"{self.insurance_verification_url}/verify",
                json={
                    "member_id": claim_request.member_id,
                    "provider_id": claim_request.provider_id,
                    "service_codes": [item.service_code for item in claim_request.service_line_items]
                }
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("verification_result", {})
        except Exception as e:
            logger.error(f"Insurance verification failed: {e}")
        
        return {"coverage_active": False, "status": "verification_failed"}
    
    async def _validate_service_code(self, service_code: str) -> Dict[str, Any]:
        """Validate individual service code"""
        # Mock validation - in production, integrate with medical coding database
        if len(service_code) == 5 and service_code.isdigit():
            return {"valid": True}
        elif len(service_code) == 5 and service_code[0].isalpha():
            return {"valid": True}
        else:
            return {"valid": False, "issues": ["Invalid code format"]}
    
    async def _check_diagnosis_alignment(self, claim_request: ClaimRequest) -> Dict[str, Any]:
        """Check if diagnosis codes align with service codes"""
        # Mock alignment check - in production, use clinical decision support
        return {"aligned": True, "alignment_score": 0.9}
    
    async def _requires_prior_authorization(self, service_code: str) -> bool:
        """Check if service code requires prior authorization"""
        # Mock check - in production, integrate with payer-specific auth requirements
        high_cost_procedures = ["64483", "64484", "20610", "20611"]  # Example codes
        return service_code in high_cost_procedures
    
    def _serialize_step(self, step: TreeOfThoughtsStep) -> Dict[str, Any]:
        """Serialize reasoning step for API response"""
        return {
            "step_id": step.step_id,
            "step_type": step.step_type,
            "question": step.question,
            "options": step.options,
            "selected_option": step.selected_option,
            "reasoning": step.reasoning,
            "confidence": step.confidence,
            "dependencies": step.dependencies,
            "timestamp": step.timestamp.isoformat()
        }