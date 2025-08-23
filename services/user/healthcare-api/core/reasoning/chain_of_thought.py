"""
Chain-of-Thought Reasoning Engine for Healthcare Administrative Decisions

This module provides structured reasoning capabilities for healthcare agents,
enabling transparent decision-making with full audit trails and compliance tracking.
"""

from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import logging
from abc import ABC, abstractmethod

from core.infrastructure.healthcare_logger import get_healthcare_logger, log_healthcare_event
from core.infrastructure.phi_monitor import phi_monitor_decorator, sanitize_healthcare_data

logger = get_healthcare_logger(__name__)

class ReasoningType(Enum):
    INSURANCE_ELIGIBILITY = "insurance_eligibility"
    COVERAGE_ANALYSIS = "coverage_analysis"
    PRIOR_AUTHORIZATION = "prior_authorization"
    CLAIM_VALIDATION = "claim_validation"
    BILLING_CODE_ANALYSIS = "billing_code_analysis"
    CLINICAL_DOCUMENTATION = "clinical_documentation"
    SCHEDULING_OPTIMIZATION = "scheduling_optimization"

@dataclass
class ReasoningStep:
    """Individual step in the chain of thought reasoning process"""
    step_id: str
    step_type: str
    reasoning_type: ReasoningType
    input_data: Dict[str, Any]
    reasoning_process: str
    conclusion: str
    confidence_score: float
    evidence: List[str]
    next_steps: List[str]
    timestamp: datetime
    phi_sanitized: bool = True

@dataclass
class ReasoningChainResult:
    """Complete chain of thought reasoning result"""
    chain_id: str
    reasoning_type: ReasoningType
    steps: List[ReasoningStep]
    final_conclusion: str
    overall_confidence: float
    recommendations: List[str]
    audit_trail: Dict[str, Any]
    created_at: datetime

class ReasoningTemplate(ABC):
    """Abstract base class for reasoning templates"""
    
    @abstractmethod
    async def generate_reasoning_steps(
        self, 
        input_data: Dict[str, Any], 
        question: str, 
        chain_id: str
    ) -> List[Dict[str, Any]]:
        """Generate reasoning steps for this template"""
        pass

class InsuranceEligibilityTemplate(ReasoningTemplate):
    """Template for insurance eligibility verification reasoning"""
    
    async def generate_reasoning_steps(
        self, 
        input_data: Dict[str, Any], 
        question: str, 
        chain_id: str
    ) -> List[Dict[str, Any]]:
        """Generate eligibility verification reasoning steps"""
        
        return [
            {
                "step_type": "member_identification",
                "prompt": f"""
                Analyze the insurance member information for administrative verification:
                
                Member ID: {input_data.get('member_id', 'Not specified')}
                Provider Network: {input_data.get('provider_network', 'Not provided')}
                Plan Type: {input_data.get('plan_type', 'Unknown')}
                Service Date: {input_data.get('service_date', 'Not specified')}
                
                Step 1: Validate member identification and plan status.
                Provide detailed analysis of:
                - Member ID format validation
                - Plan active status verification  
                - Network participation confirmation
                - Effective date coverage verification
                - Administrative compliance requirements
                
                Focus on administrative verification, not medical decisions.
                Provide specific reasoning for each validation point.
                """,
                "expected_output": "member_validation_analysis"
            },
            {
                "step_type": "coverage_determination",
                "prompt": f"""
                Based on member validation, determine coverage for requested services:
                
                Service Codes: {input_data.get('service_codes', [])}
                Provider NPI: {input_data.get('provider_npi', 'Not provided')}
                
                For each service code, analyze:
                - Coverage status (covered/not covered/requires authorization)
                - Benefit limitations and exclusions
                - Administrative requirements
                - Documentation needed
                - Processing timeline
                - Cost-sharing responsibilities
                
                Rank services by administrative complexity and provide reasoning.
                """,
                "expected_output": "coverage_determination_analysis"
            },
            {
                "step_type": "administrative_requirements",
                "prompt": f"""
                Determine administrative requirements and next steps:
                
                Based on coverage analysis, specify:
                - Required prior authorizations
                - Referral requirements
                - Documentation needed
                - Timeline for approvals
                - Alternative coverage options
                - Patient financial responsibility
                
                Provide clear administrative guidance with reasoning.
                """,
                "expected_output": "administrative_requirements_analysis"
            }
        ]

class ClaimValidationTemplate(ReasoningTemplate):
    """Template for claim validation reasoning"""
    
    async def generate_reasoning_steps(
        self, 
        input_data: Dict[str, Any], 
        question: str, 
        chain_id: str
    ) -> List[Dict[str, Any]]:
        """Generate claim validation reasoning steps"""
        
        return [
            {
                "step_type": "claim_data_validation",
                "prompt": f"""
                Validate claim data for completeness and accuracy:
                
                Claim Data: {json.dumps(input_data.get('claim_data', {}), indent=2)}
                
                Analyze:
                - Required field completion
                - Data format compliance
                - Code validity (ICD-10, CPT, HCPCS)
                - Date consistency
                - Provider information accuracy
                
                Identify any data issues with specific reasoning.
                """,
                "expected_output": "claim_data_validation_analysis"
            },
            {
                "step_type": "billing_compliance_check",
                "prompt": f"""
                Check billing compliance and coding accuracy:
                
                Evaluate:
                - Coding accuracy for services provided
                - Modifier usage appropriateness
                - Unbundling/bundling compliance
                - Medical necessity documentation
                - Billing rule compliance
                
                Provide reasoning for compliance assessment.
                """,
                "expected_output": "billing_compliance_analysis"
            }
        ]

class ChainOfThoughtProcessor:
    """Main processor for chain of thought reasoning in healthcare contexts"""
    
    def __init__(self, llm_client, audit_logger=None):
        self.llm_client = llm_client
        self.audit_logger = audit_logger or logger
        
        # Register reasoning templates
        self.templates = {
            ReasoningType.INSURANCE_ELIGIBILITY: InsuranceEligibilityTemplate(),
            ReasoningType.CLAIM_VALIDATION: ClaimValidationTemplate(),
            # Add more templates as needed
        }
    
    @phi_monitor_decorator
    async def process_reasoning_chain(
        self,
        input_data: Dict[str, Any],
        question: str,
        reasoning_type: ReasoningType,
        session_id: str,
        user_id: str = None
    ) -> ReasoningChainResult:
        """Process a complete chain of thought reasoning sequence"""
        
        # Generate unique chain ID
        chain_id = f"{reasoning_type.value}_{session_id}_{datetime.utcnow().timestamp()}"
        
        # Sanitize input data for PHI protection
        sanitized_data = sanitize_healthcare_data(input_data)
        
        # Get appropriate reasoning template
        template = self.templates.get(reasoning_type)
        if not template:
            raise ValueError(f"No template available for reasoning type: {reasoning_type}")
        
        # Generate reasoning steps
        reasoning_step_templates = await template.generate_reasoning_steps(
            sanitized_data, question, chain_id
        )
        
        # Process each reasoning step
        processed_steps = []
        for i, step_template in enumerate(reasoning_step_templates):
            step = await self._process_reasoning_step(
                step_template=step_template,
                step_index=i,
                chain_id=chain_id,
                reasoning_type=reasoning_type,
                context_data=sanitized_data
            )
            processed_steps.append(step)
        
        # Generate final synthesis
        final_analysis = await self._synthesize_reasoning_chain(
            processed_steps, reasoning_type, sanitized_data, question
        )
        
        # Create result
        result = ReasoningChainResult(
            chain_id=chain_id,
            reasoning_type=reasoning_type,
            steps=processed_steps,
            final_conclusion=final_analysis["conclusion"],
            overall_confidence=final_analysis["confidence"],
            recommendations=final_analysis["recommendations"],
            audit_trail=self._create_audit_trail(
                chain_id, reasoning_type, processed_steps, user_id
            ),
            created_at=datetime.utcnow()
        )
        
        # Log reasoning chain for audit compliance
        await self._log_reasoning_chain(result, user_id, session_id)
        
        return result
    
    async def _process_reasoning_step(
        self,
        step_template: Dict[str, Any],
        step_index: int,
        chain_id: str,
        reasoning_type: ReasoningType,
        context_data: Dict[str, Any]
    ) -> ReasoningStep:
        """Process an individual reasoning step"""
        
        step_id = f"{chain_id}_step_{step_index}"
        
        # Execute reasoning with LLM
        try:
            reasoning_response = await self.llm_client.ainvoke(step_template["prompt"])
            
            # Parse reasoning response
            parsed_response = await self._parse_reasoning_response(
                reasoning_response, step_template["expected_output"]
            )
            
            return ReasoningStep(
                step_id=step_id,
                step_type=step_template["step_type"],
                reasoning_type=reasoning_type,
                input_data=context_data,
                reasoning_process=parsed_response.get("process", ""),
                conclusion=parsed_response.get("conclusion", ""),
                confidence_score=parsed_response.get("confidence", 0.5),
                evidence=parsed_response.get("evidence", []),
                next_steps=parsed_response.get("next_steps", []),
                timestamp=datetime.utcnow(),
                phi_sanitized=True
            )
            
        except Exception as e:
            logger.error(f"Error processing reasoning step {step_id}: {e}")
            # Return error step
            return ReasoningStep(
                step_id=step_id,
                step_type=step_template["step_type"],
                reasoning_type=reasoning_type,
                input_data=context_data,
                reasoning_process=f"Error in processing: {str(e)}",
                conclusion="Step processing failed",
                confidence_score=0.0,
                evidence=[],
                next_steps=["Review step inputs and retry"],
                timestamp=datetime.utcnow(),
                phi_sanitized=True
            )
    
    async def _synthesize_reasoning_chain(
        self,
        steps: List[ReasoningStep],
        reasoning_type: ReasoningType,
        context_data: Dict[str, Any],
        original_question: str
    ) -> Dict[str, Any]:
        """Synthesize the complete reasoning chain into final conclusion"""
        
        # Prepare synthesis prompt
        steps_summary = []
        for step in steps:
            steps_summary.append({
                "step_type": step.step_type,
                "conclusion": step.conclusion,
                "confidence": step.confidence_score,
                "evidence": step.evidence[:3]  # Top 3 evidence items
            })
        
        synthesis_prompt = f"""
        Synthesize the following reasoning steps for {reasoning_type.value}:
        
        Original Question: {original_question}
        
        Reasoning Steps:
        {json.dumps(steps_summary, indent=2)}
        
        Provide:
        1. Final conclusion integrating all reasoning steps
        2. Overall confidence score (0.0-1.0)
        3. Key recommendations for next actions
        4. Summary of supporting evidence
        
        Focus on administrative decisions, not medical advice.
        """
        
        try:
            synthesis_response = await self.llm_client.ainvoke(synthesis_prompt)
            
            # Parse synthesis response
            parsed_synthesis = await self._parse_synthesis_response(synthesis_response)
            
            # Calculate overall confidence as weighted average
            total_weight = sum(step.confidence_score for step in steps)
            if total_weight > 0:
                weighted_confidence = total_weight / len(steps)
            else:
                weighted_confidence = 0.0
            
            return {
                "conclusion": parsed_synthesis.get("conclusion", "Unable to reach conclusion"),
                "confidence": min(weighted_confidence, parsed_synthesis.get("confidence", 0.5)),
                "recommendations": parsed_synthesis.get("recommendations", []),
                "evidence_summary": parsed_synthesis.get("evidence_summary", [])
            }
            
        except Exception as e:
            logger.error(f"Error synthesizing reasoning chain: {e}")
            return {
                "conclusion": "Error in reasoning chain synthesis",
                "confidence": 0.0,
                "recommendations": ["Review reasoning steps and retry"],
                "evidence_summary": []
            }
    
    async def _parse_reasoning_response(
        self, 
        response: str, 
        expected_output: str
    ) -> Dict[str, Any]:
        """Parse LLM reasoning response into structured format"""
        
        # Simple parsing - in production, use more sophisticated parsing
        return {
            "process": response[:500] + "..." if len(response) > 500 else response,
            "conclusion": f"Analysis completed for {expected_output}",
            "confidence": 0.7,  # Default confidence
            "evidence": ["LLM analysis", "Data validation", "Rule compliance"],
            "next_steps": ["Proceed to next reasoning step"]
        }
    
    async def _parse_synthesis_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM synthesis response into structured format"""
        
        # Simple parsing - in production, use more sophisticated parsing
        return {
            "conclusion": response[:300] + "..." if len(response) > 300 else response,
            "confidence": 0.7,
            "recommendations": ["Follow administrative guidelines", "Document decisions"],
            "evidence_summary": ["Multiple reasoning steps validated"]
        }
    
    def _create_audit_trail(
        self,
        chain_id: str,
        reasoning_type: ReasoningType,
        steps: List[ReasoningStep],
        user_id: str = None
    ) -> Dict[str, Any]:
        """Create comprehensive audit trail for reasoning chain"""
        
        return {
            "chain_id": chain_id,
            "user_id": user_id,
            "reasoning_type": reasoning_type.value,
            "total_steps": len(steps),
            "average_confidence": sum(step.confidence_score for step in steps) / len(steps) if steps else 0,
            "processing_time_seconds": (steps[-1].timestamp - steps[0].timestamp).total_seconds() if len(steps) > 1 else 0,
            "phi_sanitized": all(step.phi_sanitized for step in steps),
            "step_summary": [
                {
                    "step_id": step.step_id,
                    "step_type": step.step_type,
                    "confidence": step.confidence_score,
                    "timestamp": step.timestamp.isoformat()
                }
                for step in steps
            ]
        }
    
    async def _log_reasoning_chain(
        self,
        result: ReasoningChainResult,
        user_id: str = None,
        session_id: str = None
    ):
        """Log reasoning chain for audit compliance"""
        
        await log_healthcare_event(
            logger,
            logging.INFO,
            "Chain of thought reasoning completed",
            context={
                "chain_id": result.chain_id,
                "reasoning_type": result.reasoning_type.value,
                "user_id": user_id,
                "session_id": session_id,
                "total_steps": len(result.steps),
                "overall_confidence": result.overall_confidence,
                "phi_sanitized": result.audit_trail.get("phi_sanitized", True)
            },
            operation_type="chain_of_thought_reasoning"
        )