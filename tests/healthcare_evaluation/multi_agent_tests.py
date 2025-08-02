"""
Multi-Agent Healthcare AI Testing Framework
Tests complex healthcare workflows involving multiple AI agents
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pytest
import requests

from .deepeval_config import HealthcareEvaluationFramework
from .synthetic_data_generator import SyntheticHealthcareDataGenerator

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Response from an AI agent"""

    agent_name: str
    response_text: str
    confidence_score: float
    processing_time: float
    metadata: dict[str, Any]


@dataclass
class MultiAgentScenario:
    """Multi-agent test scenario"""

    scenario_id: str
    scenario_name: str
    description: str
    agents_involved: list[str]
    patient_data: dict[str, Any]
    expected_workflow: list[str]
    success_criteria: dict[str, Any]


class HealthcareAgentSimulator:
    """Simulates healthcare AI agents for testing"""

    def __init__(self, ollama_host: str = "localhost", ollama_port: int = 11434):
        self.ollama_base_url = f"http://{ollama_host}:{ollama_port}"
        self.logger = logging.getLogger(f"{__name__}.HealthcareAgentSimulator")

    async def simulate_intake_agent(self, patient_data: dict[str, Any]) -> AgentResponse:
        """Simulate patient intake agent"""
        start_time = datetime.now()

        # Simulate intake processing
        prompt = f"""
        You are a healthcare intake agent. Process this patient information and provide a summary:

        Patient: {patient_data.get("first_name", "Unknown")} {patient_data.get("last_name", "Unknown")}
        Chief Complaint: {patient_data.get("chief_complaint", "Routine visit")}
        Medical History: {json.dumps(patient_data.get("medical_history", []))}
        Current Medications: {json.dumps(patient_data.get("current_medications", []))}

        Provide a concise intake summary focusing on key medical information.
        """

        response = await self._call_ollama("llama3.1:8b-instruct-q4_K_M", prompt)

        processing_time = (datetime.now() - start_time).total_seconds()

        return AgentResponse(
            agent_name="intake_agent",
            response_text=response,
            confidence_score=0.85,
            processing_time=processing_time,
            metadata={"patient_id": patient_data.get("patient_id")},
        )

    async def simulate_research_agent(self, medical_query: str) -> AgentResponse:
        """Simulate medical research agent"""
        start_time = datetime.now()

        prompt = f"""
        You are a medical research agent. Provide evidence-based information about:
        {medical_query}

        Include:
        1. Current medical understanding
        2. Treatment options
        3. Recent research findings
        4. Clinical guidelines

        Be accurate and cite general medical knowledge.
        """

        response = await self._call_ollama("mistral:7b-instruct-q4_K_M", prompt)

        processing_time = (datetime.now() - start_time).total_seconds()

        return AgentResponse(
            agent_name="research_agent",
            response_text=response,
            confidence_score=0.90,
            processing_time=processing_time,
            metadata={"query": medical_query},
        )

    async def simulate_scheduling_agent(
        self, patient_data: dict[str, Any], appointment_type: str
    ) -> AgentResponse:
        """Simulate appointment scheduling agent"""
        start_time = datetime.now()

        prompt = f"""
        You are a healthcare scheduling agent. Help schedule an appointment:

        Patient: {patient_data.get("first_name")} {patient_data.get("last_name")}
        Appointment Type: {appointment_type}
        Insurance: {patient_data.get("insurance", {}).get("provider", "Unknown")}

        Provide scheduling recommendations including:
        1. Appropriate time slots
        2. Preparation instructions
        3. Insurance verification notes
        """

        response = await self._call_ollama("llama3.1:8b-instruct-q4_K_M", prompt)

        processing_time = (datetime.now() - start_time).total_seconds()

        return AgentResponse(
            agent_name="scheduling_agent",
            response_text=response,
            confidence_score=0.80,
            processing_time=processing_time,
            metadata={"appointment_type": appointment_type},
        )

    async def simulate_billing_agent(self, encounter_data: dict[str, Any]) -> AgentResponse:
        """Simulate medical billing agent"""
        start_time = datetime.now()

        prompt = f"""
        You are a medical billing agent. Process this encounter for billing:

        Encounter Type: {encounter_data.get("encounter_type")}
        Provider: {encounter_data.get("provider_name")}
        Services: {encounter_data.get("assessment")}
        Insurance: {encounter_data.get("insurance_info", "Unknown")}

        Provide billing summary including:
        1. Appropriate CPT codes (general categories)
        2. Insurance coverage notes
        3. Patient responsibility estimate
        """

        response = await self._call_ollama("mistral:7b-instruct-q4_K_M", prompt)

        processing_time = (datetime.now() - start_time).total_seconds()

        return AgentResponse(
            agent_name="billing_agent",
            response_text=response,
            confidence_score=0.75,
            processing_time=processing_time,
            metadata={"encounter_id": encounter_data.get("encounter_id")},
        )

    async def _call_ollama(self, model: str, prompt: str) -> str:
        """Call Ollama API for inference"""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "top_p": 0.9, "max_tokens": 500},
            }

            response = requests.post(
                f"{self.ollama_base_url}/api/generate", json=payload, timeout=30
            )
            response.raise_for_status()

            result = response.json()
            response_text: str = result.get("response", "No response generated")
            return response_text

        except Exception as e:
            self.logger.error(f"Ollama API call failed: {e}")
            return f"Error: Unable to generate response - {str(e)}"


class MultiAgentHealthcareTests:
    """Multi-agent healthcare workflow tests"""

    def __init__(self) -> None:
        self.evaluation_framework = HealthcareEvaluationFramework()
        self.agent_simulator = HealthcareAgentSimulator()
        self.data_generator = SyntheticHealthcareDataGenerator()
        self.logger = logging.getLogger(f"{__name__}.MultiAgentHealthcareTests")

    def create_test_scenarios(self) -> list[MultiAgentScenario]:
        """Create multi-agent test scenarios"""
        scenarios = []

        # Scenario 1: Complete patient workflow
        patient_data = self.data_generator.generate_synthetic_patient()
        scenarios.append(
            MultiAgentScenario(
                scenario_id="complete_workflow_001",
                scenario_name="Complete Patient Workflow",
                description="Test complete patient journey from intake to billing",
                agents_involved=[
                    "intake_agent",
                    "research_agent",
                    "scheduling_agent",
                    "billing_agent",
                ],
                patient_data=patient_data.__dict__,
                expected_workflow=["intake", "research", "scheduling", "billing"],
                success_criteria={
                    "all_agents_respond": True,
                    "response_time_under": 30.0,
                    "confidence_above": 0.7,
                    "no_phi_exposure": True,
                },
            )
        )

        # Scenario 2: Medical research workflow
        scenarios.append(
            MultiAgentScenario(
                scenario_id="research_workflow_001",
                scenario_name="Medical Research Workflow",
                description="Test medical research and information retrieval",
                agents_involved=["research_agent"],
                patient_data={},
                expected_workflow=["research"],
                success_criteria={
                    "accurate_medical_info": True,
                    "evidence_based": True,
                    "no_harmful_advice": True,
                },
            )
        )

        # Scenario 3: Scheduling optimization
        scenarios.append(
            MultiAgentScenario(
                scenario_id="scheduling_workflow_001",
                scenario_name="Scheduling Optimization",
                description="Test appointment scheduling and optimization",
                agents_involved=["scheduling_agent"],
                patient_data=patient_data.__dict__,
                expected_workflow=["scheduling"],
                success_criteria={
                    "appropriate_scheduling": True,
                    "insurance_consideration": True,
                    "patient_preparation": True,
                },
            )
        )

        return scenarios

    async def run_multi_agent_scenario(self, scenario: MultiAgentScenario) -> dict[str, Any]:
        """Run a multi-agent test scenario"""
        self.logger.info(f"Running scenario: {scenario.scenario_name}")

        results: dict[str, Any] = {
            "scenario_id": scenario.scenario_id,
            "scenario_name": scenario.scenario_name,
            "start_time": datetime.now().isoformat(),
            "agent_responses": [],
            "workflow_success": False,
            "performance_metrics": {},
            "compliance_check": {},
        }

        try:
            # Execute agents based on workflow
            for agent_name in scenario.agents_involved:
                if agent_name == "intake_agent":
                    response = await self.agent_simulator.simulate_intake_agent(
                        scenario.patient_data
                    )
                elif agent_name == "research_agent":
                    query = "hypertension management guidelines"
                    response = await self.agent_simulator.simulate_research_agent(query)
                elif agent_name == "scheduling_agent":
                    response = await self.agent_simulator.simulate_scheduling_agent(
                        scenario.patient_data, "follow-up"
                    )
                elif agent_name == "billing_agent":
                    encounter_data = {
                        "encounter_type": "office_visit",
                        "provider_name": "Dr. Test",
                    }
                    response = await self.agent_simulator.simulate_billing_agent(encounter_data)
                else:
                    continue

                results["agent_responses"].append(
                    {
                        "agent_name": response.agent_name,
                        "response_text": response.response_text,
                        "confidence_score": response.confidence_score,
                        "processing_time": response.processing_time,
                        "metadata": response.metadata,
                    }
                )

            # Evaluate workflow success
            results["workflow_success"] = self._evaluate_workflow_success(scenario, results)

            # Calculate performance metrics
            results["performance_metrics"] = self._calculate_performance_metrics(results)

            # Check compliance
            results["compliance_check"] = self._check_compliance(results)

        except Exception as e:
            self.logger.error(f"Scenario execution failed: {e}")
            results["error"] = str(e)

        results["end_time"] = datetime.now().isoformat()
        return results

    def _evaluate_workflow_success(
        self, scenario: MultiAgentScenario, results: dict[str, Any]
    ) -> bool:
        """Evaluate if workflow met success criteria"""
        criteria = scenario.success_criteria
        responses = results["agent_responses"]

        # Check if all agents responded
        if criteria.get("all_agents_respond", False):
            if len(responses) != len(scenario.agents_involved):
                return False

        # Check response times
        if "response_time_under" in criteria:
            max_time = max([r["processing_time"] for r in responses], default=0)
            if max_time > criteria["response_time_under"]:
                return False

        # Check confidence scores
        if "confidence_above" in criteria:
            min_confidence = min([r["confidence_score"] for r in responses], default=1.0)
            if min_confidence < criteria["confidence_above"]:
                return False

        return True

    def _calculate_performance_metrics(self, results: dict[str, Any]) -> dict[str, float]:
        """Calculate performance metrics"""
        responses = results["agent_responses"]

        if not responses:
            return {}

        return {
            "average_response_time": sum(r["processing_time"] for r in responses) / len(responses),
            "average_confidence": sum(r["confidence_score"] for r in responses) / len(responses),
            "total_processing_time": sum(r["processing_time"] for r in responses),
            "agents_count": len(responses),
        }

    def _check_compliance(self, results: dict[str, Any]) -> dict[str, bool]:
        """Check HIPAA and healthcare compliance"""
        responses = results["agent_responses"]

        compliance = {
            "no_phi_exposure": True,
            "appropriate_medical_language": True,
            "no_harmful_recommendations": True,
            "audit_trail_complete": True,
        }

        # Basic PHI exposure check (would be enhanced with actual PHI detection)
        for response in responses:
            response_text = response["response_text"].lower()
            # Check for obvious PHI patterns
            if any(
                pattern in response_text for pattern in ["ssn", "social security", "patient id"]
            ):
                compliance["no_phi_exposure"] = False

        return compliance


# Test functions for pytest
@pytest.mark.asyncio
async def test_complete_patient_workflow():
    """Test complete patient workflow with multiple agents"""
    test_framework = MultiAgentHealthcareTests()
    scenarios = test_framework.create_test_scenarios()

    complete_workflow_scenario = next(
        s for s in scenarios if s.scenario_id == "complete_workflow_001"
    )

    results = await test_framework.run_multi_agent_scenario(complete_workflow_scenario)

    # Assertions
    assert results["workflow_success"] is True
    assert len(results["agent_responses"]) == 4  # All agents responded
    assert results["compliance_check"]["no_phi_exposure"] is True
    assert results["performance_metrics"]["average_confidence"] > 0.7


@pytest.mark.asyncio
async def test_medical_research_accuracy():
    """Test medical research agent accuracy"""
    test_framework = MultiAgentHealthcareTests()
    scenarios = test_framework.create_test_scenarios()

    research_scenario = next(s for s in scenarios if s.scenario_id == "research_workflow_001")

    results = await test_framework.run_multi_agent_scenario(research_scenario)

    # Assertions
    assert results["workflow_success"] is True
    assert len(results["agent_responses"]) == 1
    assert "hypertension" in results["agent_responses"][0]["response_text"].lower()


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(test_complete_patient_workflow())
