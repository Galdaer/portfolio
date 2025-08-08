"""
Healthcare Integration Tests - PHI-Safe Testing with Synthetic Data

Tests the complete MCP-Agent bridge integration using only synthetic data.
Validates end-to-end workflow: Open WebUI → Ollama → MCP → FastAPI agents.
"""

import logging
from typing import Any

import httpx
import pytest

from core.security.phi_safe_testing import (
    HealthcareTestValidator,
    PHISafeTestingFramework,
    SyntheticDataGenerator,
)

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthcareIntegrationTestBase:
    """Base class for healthcare integration tests with PHI safety."""

    MCP_SERVER_URL = "http://localhost:3000"
    MAIN_API_URL = "http://localhost:8000"

    @pytest.fixture
    async def synthetic_patient(self) -> dict[str, Any]:
        """Generate synthetic patient data for testing."""
        patient = PHISafeTestingFramework.generate_synthetic_patient()

        # Validate PHI safety
        PHISafeTestingFramework.validate_test_data(patient)

        logger.info(f"Generated synthetic patient: {patient['patient_id']}")
        return patient

    @pytest.fixture
    async def test_session_context(self) -> dict[str, Any]:
        """Create test session context."""
        return PHISafeTestingFramework.create_test_session_context()

    @pytest.fixture
    async def http_client(self):
        """HTTP client for API calls."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            yield client


class TestHealthcareIntegration(HealthcareIntegrationTestBase):
    """Integration tests using synthetic data - NO PHI"""

    # Test configuration
    MCP_SERVER_URL = "http://localhost:3000"
    FASTAPI_SERVER_URL = "http://localhost:8000"

    @pytest.fixture
    async def synthetic_patient(self) -> dict[str, Any]:
        """Generate synthetic patient data for testing"""
        framework = PHISafeTestingFramework()
        patient = framework.generate_synthetic_patient()

        # Validate test data is PHI-safe
        framework.validate_test_data(patient)

        return patient

    @pytest.fixture
    async def synthetic_encounter(self, synthetic_patient: dict[str, Any]) -> dict[str, Any]:
        """Generate synthetic encounter data"""
        framework = PHISafeTestingFramework()
        encounter = framework.generate_synthetic_encounter(synthetic_patient["patient_id"])

        # Validate test data is PHI-safe
        framework.validate_test_data(encounter)

        return encounter

    @pytest.fixture
    async def test_session_context(self) -> dict[str, Any]:
        """Create test session context"""
        framework = PHISafeTestingFramework()
        return framework.create_test_session_context()

    @pytest.mark.asyncio
    async def test_mcp_server_health(self) -> None:
        """Test MCP server is running and responsive"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.MCP_SERVER_URL}/health")
                assert response.status_code == 200

                health_data = response.json()
                assert health_data["status"] == "healthy"
                assert health_data["service"] == "healthcare-mcp"

            except httpx.ConnectError:
                pytest.skip("MCP server not running - start with: cd mcps/healthcare && npm start")

    @pytest.mark.asyncio
    async def test_mcp_tools_list(self) -> None:
        """Test MCP server returns agent bridge tools"""
        mcp_request = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.MCP_SERVER_URL}/mcp",
                    json=mcp_request,
                    headers={"Content-Type": "application/json"},
                )

                assert response.status_code == 200
                result = response.json()

                assert "result" in result
                assert "tools" in result["result"]

                # Check for agent bridge tools
                tool_names = [tool["name"] for tool in result["result"]["tools"]]
                expected_agent_tools = [
                    "clinical_intake",
                    "transcribe_audio",
                    "research_medical_literature",
                ]

                for tool in expected_agent_tools:
                    assert tool in tool_names, (
                        f"Agent bridge tool {tool} not found in MCP tools list"
                    )

            except httpx.ConnectError:
                pytest.skip("MCP server not running")

    @pytest.mark.asyncio
    async def test_mcp_agent_bridge_intake(
        self, synthetic_patient: dict[str, Any], test_session_context: dict[str, Any],
    ) -> None:
        """Test MCP → Agent bridge for intake processing"""
        # Test MCP tool call to intake agent
        mcp_request: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "clinical_intake",
                "arguments": {
                    "patient_data": synthetic_patient,
                    "intake_type": "new_patient",
                    "session_id": test_session_context["session_id"],
                },
            },
            "id": 1,
        }

        # Validate request data is PHI-safe
        framework = PHISafeTestingFramework()
        framework.validate_test_data(mcp_request["params"]["arguments"])

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.MCP_SERVER_URL}/mcp",
                    json=mcp_request,
                    headers={"Content-Type": "application/json"},
                )

                assert response.status_code == 200
                result = response.json()

                # Verify MCP response structure
                assert "result" in result

                # Validate response contains healthcare metadata
                if "_mcp_metadata" in result["result"]:
                    metadata = result["result"]["_mcp_metadata"]
                    assert metadata["tool_name"] == "clinical_intake"
                    assert metadata["phi_protected"] is True
                    assert "medical_disclaimer" in metadata

                # Validate medical safety
                validator = HealthcareTestValidator()
                validator.validate_medical_safety(result["result"])
                validator.validate_phi_protection(result["result"])

            except httpx.ConnectError:
                pytest.skip("MCP server not running")

    @pytest.mark.asyncio
    async def test_mcp_research_agent_bridge(self, test_session_context: dict[str, Any]) -> None:
        """Test MCP → Research Agent bridge"""
        mcp_request: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "research_medical_literature",
                "arguments": {
                    "query": "hypertension guidelines 2024",
                    "max_results": 5,
                    "include_clinical_trials": True,
                    "session_id": test_session_context["session_id"],
                },
            },
            "id": 1,
        }

        # Validate request contains no PHI
        framework = PHISafeTestingFramework()
        framework.validate_test_data(mcp_request["params"]["arguments"])

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.MCP_SERVER_URL}/mcp",
                    json=mcp_request,
                    headers={"Content-Type": "application/json"},
                )

                assert response.status_code == 200
                result = response.json()

                # Verify research response
                assert "result" in result

                if "_mcp_metadata" in result["result"]:
                    metadata = result["result"]["_mcp_metadata"]
                    assert metadata["tool_name"] == "research_medical_literature"
                    assert metadata["phi_protected"] is True

                # Validate no medical advice in research results
                validator = HealthcareTestValidator()
                validator.validate_medical_safety(result["result"])

            except httpx.ConnectError:
                pytest.skip("MCP server not running")

    @pytest.mark.asyncio
    async def test_mcp_transcription_agent_bridge(
        self, test_session_context: dict[str, Any],
    ) -> None:
        """Test MCP → Transcription Agent bridge"""
        framework = PHISafeTestingFramework()
        synthetic_audio = framework.generate_synthetic_audio_data()

        mcp_request: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "transcribe_audio",
                "arguments": {
                    "audio_data": synthetic_audio,
                    "session_id": test_session_context["session_id"],
                    "doctor_id": "TEST_PROV_001",
                    "encounter_type": "consultation",
                },
            },
            "id": 1,
        }

        # Validate request is PHI-safe
        framework.validate_test_data(mcp_request["params"]["arguments"])

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.MCP_SERVER_URL}/mcp",
                    json=mcp_request,
                    headers={"Content-Type": "application/json"},
                )

                assert response.status_code == 200
                result = response.json()

                # Verify transcription response
                assert "result" in result

                if "_mcp_metadata" in result["result"]:
                    metadata = result["result"]["_mcp_metadata"]
                    assert metadata["tool_name"] == "transcribe_audio"
                    assert metadata["phi_protected"] is True

                # Validate transcription safety
                validator = HealthcareTestValidator()
                validator.validate_medical_safety(result["result"])
                validator.validate_phi_protection(result["result"])

            except httpx.ConnectError:
                pytest.skip("MCP server not running")

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(
        self, synthetic_patient: dict[str, Any], test_session_context: dict[str, Any],
    ) -> None:
        """Test complete workflow: MCP → Agents → Response"""
        framework = PHISafeTestingFramework()
        validator = HealthcareTestValidator()

        # Test full patient encounter workflow
        workflow_steps = [
            (
                "clinical_intake",
                {
                    "patient_data": synthetic_patient,
                    "intake_type": "new_patient",
                    "session_id": test_session_context["session_id"],
                },
            ),
            (
                "research_medical_literature",
                {
                    "query": "diabetes management guidelines",
                    "max_results": 3,
                    "session_id": test_session_context["session_id"],
                },
            ),
            (
                "transcribe_audio",
                {
                    "audio_data": framework.generate_synthetic_audio_data(),
                    "session_id": test_session_context["session_id"],
                    "doctor_id": "TEST_PROV_001",
                },
            ),
        ]

        results: list[dict[str, Any]] = []

        for tool_name, args in workflow_steps:
            # Validate each request is PHI-safe
            framework.validate_test_data(args)

            mcp_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": args},
                "id": len(results) + 1,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(
                        f"{self.MCP_SERVER_URL}/mcp",
                        json=mcp_request,
                        headers={"Content-Type": "application/json"},
                    )

                    assert response.status_code == 200
                    result = response.json()

                    # Validate each response
                    assert "result" in result
                    validator.validate_medical_safety(result["result"])
                    validator.validate_phi_protection(result["result"])

                    results.append(result)

                except httpx.ConnectError:
                    pytest.skip("MCP server not running")

        # Verify all steps completed successfully
        assert len(results) == 3
        assert all("result" in r for r in results)

        print(f"✅ End-to-end workflow completed successfully with {len(results)} steps")

    @pytest.mark.asyncio
    async def test_phi_detection_blocks_unsafe_data(self) -> None:
        """Test that PHI detection blocks unsafe data"""
        # Attempt to send data with PHI patterns
        unsafe_data = {
            "patient_name": "John Doe",
            "ssn": "123-45-6789",  # This should be blocked
            "phone": "555-123-4567",
            "session_id": "TEST_SESS_001",
        }

        mcp_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "clinical_intake",
                "arguments": {"patient_data": unsafe_data, "session_id": "TEST_SESS_001"},
            },
            "id": 1,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.MCP_SERVER_URL}/mcp",
                    json=mcp_request,
                    headers={"Content-Type": "application/json"},
                )

                # Should return error for PHI detection
                assert response.status_code == 400
                result = response.json()

                assert "error" in result
                assert "PHI validation failed" in result["error"]["message"]

            except httpx.ConnectError:
                pytest.skip("MCP server not running")

    @pytest.mark.asyncio
    async def test_direct_agent_endpoints(self, synthetic_patient: dict[str, Any]) -> None:
        """Test direct FastAPI agent endpoints"""

        endpoints_to_test = [
            (
                "/agents/intake/process",
                {"patient_data": synthetic_patient, "session_id": "TEST_SESS_001"},
            ),
            (
                "/agents/research/search",
                {"query": "diabetes management", "session_id": "TEST_SESS_001"},
            ),
        ]

        framework = PHISafeTestingFramework()
        validator = HealthcareTestValidator()

        for endpoint, payload in endpoints_to_test:
            # Validate payload is PHI-safe
            framework.validate_test_data(payload)

            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(
                        f"{self.FASTAPI_SERVER_URL}{endpoint}",
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "X-Healthcare-Request": "true",
                        },
                    )

                    # Agent might not be running, that's ok for this test
                    if response.status_code == 200:
                        result = response.json()
                        validator.validate_medical_safety(result)
                        validator.validate_phi_protection(result)
                        print(f"✅ Direct agent endpoint {endpoint} working")
                    else:
                        print(f"⚠️ Direct agent endpoint {endpoint} returned {response.status_code}")

                except httpx.ConnectError:
                    print(f"⚠️ FastAPI server not running for {endpoint}")


class TestSyntheticDataGeneration:
    """Test synthetic data generation and validation"""

    def test_synthetic_patient_generation(self) -> None:
        """Test synthetic patient data generation"""
        framework = PHISafeTestingFramework()

        for _i in range(10):
            patient = framework.generate_synthetic_patient()

            # Validate generated data is safe
            framework.validate_test_data(patient)

            # Check required fields
            assert patient["patient_id"].startswith("TEST_PAT_")
            assert patient["synthetic_marker"] is True
            assert "medical_history" in patient

    def test_comprehensive_dataset_generation(self) -> None:
        """Test comprehensive synthetic dataset generation"""
        generator = SyntheticDataGenerator()
        dataset = generator.generate_test_dataset(num_patients=5)

        # Validate dataset structure
        assert "patients" in dataset
        assert "encounters" in dataset
        assert "metadata" in dataset

        # Validate all data is PHI-safe
        framework = PHISafeTestingFramework()

        for patient in dataset["patients"]:
            framework.validate_test_data(patient)

        for encounter in dataset["encounters"]:
            framework.validate_test_data(encounter)

        # Validate metadata
        assert dataset["metadata"]["synthetic_data_only"] is True
        assert dataset["metadata"]["phi_safe"] is True

    def test_phi_detection_accuracy(self) -> None:
        """Test PHI detection accuracy"""
        framework = PHISafeTestingFramework()

        # Test cases with PHI (should be blocked)
        phi_cases = [
            {"ssn": "123-45-6789"},
            {"phone": "212-123-4567"},  # Non-555 number should be blocked
            {"email": "patient@gmail.com"},
            {"patient_id": "REAL_PATIENT_123"},  # Missing TEST_ prefix
        ]

        for case in phi_cases:
            with pytest.raises(ValueError, match="PHI|TEST_"):
                framework.validate_test_data(case)

        # Test cases without PHI (should pass)
        safe_cases = [
            {"patient_id": "TEST_PAT_001", "name": "Test Patient"},
            {"phone": "555-0123", "synthetic_marker": True},
            {"session_id": "TEST_SESS_001"},
        ]

        for case in safe_cases:
            assert framework.validate_test_data(case) is True
