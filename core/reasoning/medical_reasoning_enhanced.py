"""
Enhanced Medical Reasoning Engine
Provides medical reasoning capabilities with safety boundaries
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ReasoningType(Enum):
    """Types of medical reasoning supported"""

    DIFFERENTIAL_DIAGNOSIS = "differential_diagnosis"
    DRUG_INTERACTION = "drug_interaction"
    SYMPTOM_ANALYSIS = "symptom_analysis"
    TREATMENT_OPTIONS = "treatment_options"
    GENERAL_INQUIRY = "general_inquiry"


@dataclass
class ReasoningStep:
    """Single step in medical reasoning chain"""

    step_number: int
    reasoning_type: str
    query: str
    analysis: Dict[str, Any]
    confidence: float
    sources: List[str]
    disclaimers: List[str]
    timestamp: datetime

    def get(self, key: str, default=None):
        """Dict-like access for backward compatibility"""
        return getattr(self, key, default)


@dataclass
class ReasoningResult:
    """Result of medical reasoning process"""

    reasoning_id: str
    reasoning_type: ReasoningType
    steps: List[ReasoningStep]
    final_analysis: Dict[str, Any]
    overall_confidence: float
    medical_disclaimers: List[str]
    sources_consulted: List[str]
    generated_at: datetime
    # Additional attributes expected by clinical research agent
    final_assessment: Dict[str, Any]
    confidence_score: float
    clinical_recommendations: List[str]
    evidence_sources: List[Dict[str, Any]]
    disclaimers: List[str]
    final_assessment: Dict[str, Any]
    confidence_score: float
    clinical_recommendations: List[str]
    evidence_sources: List[Dict[str, Any]]
    disclaimers: List[str]


class EnhancedMedicalReasoning:
    """
    Enhanced medical reasoning engine with safety boundaries

    MEDICAL DISCLAIMER: This provides educational information only,
    not medical advice, diagnosis, or treatment recommendations.
    Always consult qualified healthcare professionals for medical decisions.
    """

    def __init__(self, query_engine, llm_client):
        self.query_engine = query_engine
        self.llm_client = llm_client

        # Standard medical disclaimers
        self.medical_disclaimers = [
            "This information is for educational purposes only and is not medical advice.",
            "Clinical decisions require professional medical judgment and patient evaluation.",
            "Please verify all information with original medical sources.",
            "For medical emergencies, contact emergency services immediately.",
            "This system does not replace consultation with healthcare professionals.",
        ]

    async def reason_with_dynamic_knowledge(
        self,
        clinical_scenario: Dict[str, Any],
        reasoning_type: str,
        max_iterations: int = 3,
    ) -> ReasoningResult:
        """
        Perform medical reasoning with dynamic knowledge retrieval

        Args:
            clinical_scenario: Clinical context and information
            reasoning_type: Type of reasoning to perform (string)
            max_iterations: Maximum reasoning iterations

        Returns:
            ReasoningResult with analysis and disclaimers

        Note:
            All results include appropriate medical disclaimers
            and are for educational purposes only.
        """
        try:
            # Convert string to enum if needed
            reasoning_type_enum = ReasoningType(reasoning_type)

            reasoning_id = f"reasoning_{datetime.now().isoformat()}"
            steps = []

            # Perform iterative reasoning
            for iteration in range(max_iterations):
                step = await self._perform_reasoning_step(
                    clinical_scenario, reasoning_type_enum, iteration + 1
                )
                steps.append(step)

            # Generate final analysis
            final_analysis = await self._generate_final_analysis(steps, reasoning_type_enum)

            # Collect evidence sources from steps
            evidence_sources = self._collect_evidence_sources(steps)

            # Generate clinical recommendations
            clinical_recommendations = self._generate_clinical_recommendations(final_analysis)

            return ReasoningResult(
                reasoning_id=reasoning_id,
                reasoning_type=reasoning_type_enum,
                steps=steps,
                final_analysis=final_analysis,
                overall_confidence=self._calculate_overall_confidence(steps),
                medical_disclaimers=self.medical_disclaimers,
                sources_consulted=self._collect_sources(steps),
                generated_at=datetime.now(),
                # Additional attributes for clinical research agent compatibility
                final_assessment=final_analysis,
                confidence_score=self._calculate_overall_confidence(steps),
                clinical_recommendations=clinical_recommendations,
                evidence_sources=evidence_sources,
                disclaimers=self.medical_disclaimers,
            )

        except Exception as e:
            # Return error with medical disclaimers
            return ReasoningResult(
                reasoning_id=f"error_{datetime.now().isoformat()}",
                reasoning_type=ReasoningType.GENERAL_INQUIRY,  # Default for errors
                steps=[],
                final_analysis={"error": str(e), "success": False},
                overall_confidence=0.0,
                medical_disclaimers=self.medical_disclaimers,
                sources_consulted=[],
                generated_at=datetime.now(),
                # Additional attributes for error case
                final_assessment={"error": str(e), "success": False},
                confidence_score=0.0,
                clinical_recommendations=["Consult healthcare professional due to system error"],
                evidence_sources=[],
                disclaimers=self.medical_disclaimers,
            )

    async def _perform_reasoning_step(
        self, clinical_scenario: Dict[str, Any], reasoning_type: ReasoningType, step_number: int
    ) -> ReasoningStep:
        """
        Perform a single reasoning step

        TODO: Implement actual reasoning logic
        This is a mock implementation for Phase 0 development
        """
        # Mock analysis for now
        mock_analysis = {
            "step_type": reasoning_type.value,
            "scenario_summary": str(clinical_scenario),
            "mock_reasoning": f"Step {step_number} reasoning for {reasoning_type.value}",
            "most_likely_diagnoses": (
                [
                    {"name": "Mock Diagnosis 1", "confidence": 0.7},
                    {"name": "Mock Diagnosis 2", "confidence": 0.5},
                ]
                if reasoning_type == ReasoningType.DIFFERENTIAL_DIAGNOSIS
                else []
            ),
            "recommendations": "Mock recommendations - consult healthcare professional",
            "confidence_factors": ["Clinical presentation", "Medical history"],
        }

        return ReasoningStep(
            step_number=step_number,
            reasoning_type=reasoning_type.value,
            query=f"Step {step_number} query for {reasoning_type.value}",
            analysis=mock_analysis,
            confidence=0.6,  # Mock confidence
            sources=["Mock Medical Source 1", "Mock Clinical Guidelines"],
            disclaimers=self.medical_disclaimers,
            timestamp=datetime.now(),
        )

    async def _generate_final_analysis(
        self, steps: List[ReasoningStep], reasoning_type: ReasoningType
    ) -> Dict[str, Any]:
        """
        Generate final analysis from reasoning steps

        TODO: Implement comprehensive analysis logic
        This is a mock implementation for Phase 0 development
        """
        return {
            "reasoning_summary": f"Mock final analysis for {reasoning_type.value}",
            "steps_completed": len(steps),
            "key_findings": "Mock key findings - educational purposes only",
            "confidence_assessment": "Moderate confidence in mock analysis",
            "next_steps": "Consult qualified healthcare professional for medical advice;Review additional literature;Consider specialist referral",
            "medical_disclaimer": "This analysis is for educational purposes only and not medical advice",
        }

    def _calculate_overall_confidence(self, steps: List[ReasoningStep]) -> float:
        """Calculate overall confidence from reasoning steps"""
        if not steps:
            return 0.0

        confidences = [step.confidence for step in steps]
        return sum(confidences) / len(confidences)

    def _collect_sources(self, steps: List[ReasoningStep]) -> List[str]:
        """Collect all sources from reasoning steps"""
        all_sources = []
        for step in steps:
            all_sources.extend(step.sources)

        # Remove duplicates while preserving order
        return list(dict.fromkeys(all_sources))

    def _collect_evidence_sources(self, steps: List[ReasoningStep]) -> List[Dict[str, Any]]:
        """Collect evidence sources in structured format for clinical research agent"""
        evidence_sources = []
        for step in steps:
            for source in step.sources:
                evidence_sources.append(
                    {
                        "source": source,
                        "step": step.step_number,
                        "confidence": step.confidence,
                        "reasoning_type": step.reasoning_type,
                    }
                )
        return evidence_sources

    def _generate_clinical_recommendations(self, final_analysis: Dict[str, Any]) -> List[str]:
        """Generate clinical recommendations from final analysis"""
        next_steps = final_analysis.get("next_steps", "")
        if isinstance(next_steps, str) and ";" in next_steps:
            return [step.strip() for step in next_steps.split(";") if step.strip()]

        # Default recommendations
        return [
            "Consult qualified healthcare professional for medical advice",
            "Verify findings with additional clinical evaluation",
            "Consider patient-specific factors in decision making",
        ]
