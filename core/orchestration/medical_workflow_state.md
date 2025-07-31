# core/orchestration/medical_workflow_state.py

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import asyncio

class MedicalWorkflowStep(Enum):
QUERY_ANALYSIS = "query_analysis"
INITIAL_SEARCH = "initial_search"
VALIDATION = "validation"
REFINEMENT = "refinement"
FINAL_SYNTHESIS = "final_synthesis"
TRUST_SCORING = "trust_scoring"

@dataclass
class MedicalWorkflowState:
"""State management for complex medical information workflows"""
step: MedicalWorkflowStep
query_id: str
original_query: str
current_query: str
iteration: int
max_iterations: int
results: List[Dict[str, Any]]
trust_scores: List[Dict[str, Any]]
errors: List[str]
context: Dict[str, Any]

class MedicalWorkflowOrchestrator:
"""Orchestrate complex medical information workflows with state management"""

    def __init__(self, query_engine, validator, llm_client):
        self.query_engine = query_engine
        self.validator = validator
        self.llm_client = llm_client

    async def execute_medical_workflow(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """Execute complete medical information workflow with state tracking"""

        state = MedicalWorkflowState(
            step=MedicalWorkflowStep.QUERY_ANALYSIS,
            query_id=self._generate_query_id(),
            original_query=query,
            current_query=query,
            iteration=0,
            max_iterations=max_iterations,
            results=[],
            trust_scores=[],
            errors=[],
            context=context or {}
        )

        try:
            # Step 1: Query Analysis
            state = await self._analyze_query(state)

            # Step 2-4: Iterative Search and Refinement
            while state.iteration < state.max_iterations:
                state.step = MedicalWorkflowStep.INITIAL_SEARCH
                state = await self._execute_search(state)

                state.step = MedicalWorkflowStep.VALIDATION
                state = await self._validate_results(state)

                # Check if trust score is good enough
                if state.trust_scores and state.trust_scores[-1]["overall_trust"] > 0.8:
                    break

                state.step = MedicalWorkflowStep.REFINEMENT
                state = await self._refine_query(state)
                state.iteration += 1

            # Step 5: Final Synthesis
            state.step = MedicalWorkflowStep.FINAL_SYNTHESIS
            state = await self._synthesize_final_response(state)

            return self._format_workflow_result(state)

        except Exception as e:
            state.errors.append(f"Workflow error: {str(e)}")
            return self._format_error_result(state)

    async def _validate_results(self, state: MedicalWorkflowState) -> MedicalWorkflowState:
        """Validate current results and add trust scores"""

        if not state.results:
            state.errors.append("No results to validate")
            return state

        latest_result = state.results[-1]

        trust_score = await self.validator.validate_medical_response(
            response=latest_result.get("response", ""),
            original_query=state.original_query,
            sources=latest_result.get("sources", []),
            query_type=latest_result.get("query_type", "general")
        )

        state.trust_scores.append({
            "iteration": state.iteration,
            "overall_trust": trust_score.overall_trust,
            "accuracy_score": trust_score.accuracy_score,
            "safety_score": trust_score.safety_score,
            "evidence_strength": trust_score.evidence_strength
        })

        return state
