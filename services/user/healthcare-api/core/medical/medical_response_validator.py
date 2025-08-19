# core/medical/medical_response_validator.py

"""
Medical Response Validator
Validates medical responses for accuracy and safety

MEDICAL DISCLAIMER: This system provides medical research validation and safety analysis only.
It assists healthcare professionals by validating medical information accuracy and identifying
potential safety concerns. It does not provide medical diagnosis, treatment recommendations,
or replace clinical judgment. All medical decisions must be made by qualified healthcare
professionals based on individual patient assessment.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

from core.config.models import MODEL_CONFIG


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

    def __init__(self, llm_client: Any) -> None:
        self.llm_client = llm_client

    async def validate_medical_response(
        self,
        response: str,
        original_query: str,
        sources: list[dict[str, Any]],
        query_type: str,
    ) -> MedicalTrustScore:
        """
        Validate medical response for accuracy, safety, and appropriateness
        Uses multiple validation techniques similar to Cleanlab approach

        RUNTIME PHI PROTECTION: Monitors response content for PHI exposure
        """
        import hashlib

        # Runtime PHI monitoring - check response for PHI patterns
        phi_detected = self._monitor_runtime_phi(response, "medical_response_validation")
        if phi_detected:
            response_hash = hashlib.sha256(response.encode()).hexdigest()[:8]
            print(
                f"🚨 PHI detected in medical response validation {response_hash} - flagging for review",
            )

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

    async def _check_medical_accuracy(self, response: str, sources: list[dict]) -> float:
        """Check if response aligns with provided medical sources"""
        if not sources:
            return 0.5  # Neutral if no sources

        # Create validation prompt
        source_summaries = "\n".join(
            [
                f"Source {i + 1}: {source.get('title', 'Unknown')} - {source.get('summary', '')[:200]}"
                for i, source in enumerate(sources[:5])
            ],
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
                model=MODEL_CONFIG.get_model_for_task("medical_analysis"),
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
                model=MODEL_CONFIG.get_model_for_task("medical_analysis"),
                options={"temperature": 0.1, "max_tokens": 10},
            )

            score_text = result.get("response", "0.5").strip()
            return float(score_text) if score_text.replace(".", "").isdigit() else 0.5

        except Exception:
            return 0.5

    async def _check_evidence_alignment(self, response: str, sources: list[dict]) -> float:
        """Check how well the response aligns with evidence from sources"""
        if not sources:
            return 0.5  # Neutral if no sources

        evidence_prompt = f"""
        Medical Response: {response}

        Available Sources: {len(sources)} medical sources provided

        Evidence Alignment Check:
        - Does the response cite or reference the provided sources?
        - Are claims in the response supported by the evidence?
        - Is the strength of claims appropriate for the evidence level?

        Rate evidence alignment (0.0-1.0):
        - 1.0: Perfect alignment, well-cited, appropriate strength
        - 0.8: Good alignment, mostly supported
        - 0.6: Fair alignment, some unsupported claims
        - 0.4: Poor alignment, weak evidence support
        - 0.2: Very poor alignment
        - 0.0: No alignment with evidence

        Return only the numerical score.
        """

        try:
            result = await self.llm_client.generate(
                prompt=evidence_prompt,
                model=MODEL_CONFIG.get_model_for_task("medical_analysis"),
                options={"temperature": 0.1, "max_tokens": 10},
            )

            score_text = result.get("response", "0.5").strip()
            return float(score_text) if score_text.replace(".", "").isdigit() else 0.5

        except Exception:
            return 0.5

    async def _check_scope_appropriateness(self, response: str, original_query: str) -> float:
        """Check if response scope is appropriate for the query"""

        scope_prompt = f"""
        Original Query: {original_query}
        Medical Response: {response}

        Scope Appropriateness Check:
        - Does the response address the original query appropriately?
        - Is the response within appropriate bounds for an AI system?
        - Does it avoid overstepping into areas requiring professional medical judgment?
        - Are appropriate disclaimers and limitations mentioned?

        Rate scope appropriateness (0.0-1.0):
        - 1.0: Perfect scope, addresses query appropriately with disclaimers
        - 0.8: Good scope, mostly appropriate
        - 0.6: Fair scope, some concerns
        - 0.4: Poor scope, overstepping or under-addressing
        - 0.2: Very poor scope
        - 0.0: Completely inappropriate scope

        Return only the numerical score.
        """

        try:
            result = await self.llm_client.generate(
                prompt=scope_prompt,
                model=MODEL_CONFIG.get_model_for_task("clinical"),
                options={"temperature": 0.1, "max_tokens": 10},
            )

            score_text = result.get("response", "0.5").strip()
            return float(score_text) if score_text.replace(".", "").isdigit() else 0.5

        except Exception:
            return 0.5

    def _monitor_runtime_phi(self, content: str, context_type: str) -> bool:
        """
        Runtime PHI monitoring for medical response validation.

        This monitors actual runtime content for PHI patterns, not static code.
        Returns True if potential PHI is detected.
        """
        import hashlib
        import re

        # Critical PHI patterns that should never appear in medical responses
        phi_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN patterns
            r"\b\d{9}\b.*SSN",  # Raw SSN numbers
            r"\(\d{3}\)\s*\d{3}-\d{4}",  # Phone patterns (excluding 555)
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email patterns
            r"MRN.*\d{6,}",  # Medical record numbers
        ]

        # Safe synthetic patterns (don't flag these)
        safe_patterns = [
            r"PAT\d{3}",  # PAT001 patient IDs
            r"555-\d{3}-\d{4}",  # 555 test phone numbers
            r"XXX-XX-XXXX",  # Masked SSN patterns
            r".*@example\.(com|test)",  # Test domain emails
            r"01/01/1990",  # Standard test DOB
        ]

        # Check if content contains safe synthetic patterns first
        for safe_pattern in safe_patterns:
            if re.search(safe_pattern, content, re.IGNORECASE):
                return False  # It's safe synthetic data

        # Check for PHI patterns
        for phi_pattern in phi_patterns:
            if re.search(phi_pattern, content, re.IGNORECASE):
                # Log the detection (without exposing actual content)
                content_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
                print(
                    f"🚨 Runtime PHI detection: {context_type} contains potential PHI (hash: {content_hash})",
                )
                return True

        return False
