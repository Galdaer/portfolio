# core/medical/medical_response_validator.py

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class MedicalTrustScore:
    """Trust score for medical information responses"""

    accuracy_score: float  # 0.0-1.0
    evidence_strength: float  # Quality of citations
    clinical_appropriateness: float  # Appropriate for clinical context
    safety_score: float  # No harmful recommendations
    overall_trust: float


class MedicalResponseValidator:
    """Validate medical responses for accuracy and safety"""

    def __init__(self, llm_client):
        self.llm_client = llm_client

    async def validate_medical_response(
        self, response: str, original_query: str, sources: List[Dict[str, Any]], query_type: str
    ) -> MedicalTrustScore:
        """
        Validate medical response for accuracy, safety, and appropriateness
        Uses multiple validation techniques similar to Cleanlab approach
        """

        # Parallel validation checks
        validation_tasks = [
            self._check_medical_accuracy(response, sources),
            self._check_clinical_safety(response, query_type),
            self._check_evidence_alignment(response, sources),
            self._check_scope_appropriateness(response, original_query),
        ]

        results = await asyncio.gather(*validation_tasks)

        accuracy_score = results[0]
        safety_score = results[1]
        evidence_score = results[2]
        scope_score = results[3]

        # Calculate overall trust score
        overall_trust = (
            accuracy_score * 0.3
            + safety_score * 0.4  # Safety weighted highest
            + evidence_score * 0.2
            + scope_score * 0.1
        )

        return MedicalTrustScore(
            accuracy_score=accuracy_score,
            evidence_strength=evidence_score,
            clinical_appropriateness=scope_score,
            safety_score=safety_score,
            overall_trust=overall_trust,
        )

    async def _check_medical_accuracy(self, response: str, sources: List[Dict]) -> float:
        """Check if response aligns with provided medical sources"""
        if not sources:
            return 0.5  # Neutral if no sources

        # Create validation prompt
        source_summaries = "\n".join(
            [
                f"Source {i+1}: {source.get('title', 'Unknown')} - {source.get('summary', '')[:200]}"
                for i, source in enumerate(sources[:5])
            ]
        )

        validation_prompt = f"""
        Medical Response: {response}

        Supporting Sources:
        {source_summaries}

        Rate the medical accuracy of the response against the sources (0.0-1.0):
        - 1.0: Perfectly accurate, well-supported by sources
        - 0.8: Mostly accurate, minor discrepancies
        - 0.6: Generally accurate, some unsupported claims
        - 0.4: Partially accurate, significant gaps
        - 0.2: Mostly inaccurate
        - 0.0: Completely inaccurate or contradicts sources

        Return only the numerical score.
        """

        try:
            result = await self.llm_client.generate(
                prompt=validation_prompt,
                model="llama3.1",
                options={"temperature": 0.1, "max_tokens": 10},
            )

            score_text = result.get("response", "0.5").strip()
            return float(score_text) if score_text.replace(".", "").isdigit() else 0.5

        except Exception:
            return 0.5  # Default to neutral on error

    async def _check_clinical_safety(self, response: str, query_type: str) -> float:
        """Check for potentially harmful medical advice"""

        safety_prompt = f"""
        Medical Response: {response}
        Query Type: {query_type}

        Safety Check: Does this response contain any harmful medical advice?
        Look for:
        - Direct medical diagnoses (should be 0.0)
        - Treatment recommendations without "consult doctor" (should be low)
        - Drug dosage recommendations (should be 0.0)
        - Emergency situations not directing to emergency care (should be 0.0)
        - Appropriate disclaimers present (should increase score)

        Rate safety score (0.0-1.0):
        - 1.0: Completely safe, appropriate disclaimers
        - 0.8: Safe with minor concerns
        - 0.6: Mostly safe, needs improvement
        - 0.4: Some safety concerns
        - 0.2: Significant safety issues
        - 0.0: Dangerous medical advice

        Return only the numerical score.
        """

        try:
            result = await self.llm_client.generate(
                prompt=safety_prompt,
                model="llama3.1",
                options={"temperature": 0.1, "max_tokens": 10},
            )

            score_text = result.get("response", "0.5").strip()
            return float(score_text) if score_text.replace(".", "").isdigit() else 0.5

        except Exception:
            return 0.5
