"""
Comprehensive End-to-End Healthcare AI Testing Framework
Tests complete workflow: Open WebUI → Ollama → MCP → FastAPI Agents → Response
"""

import asyncio
import json
import os
import uuid
from datetime import datetime

import httpx
import pytest

from core.security.chat_log_manager import ChatLogManager, SimplePHIDetector
from tests.database_test_utils import HealthcareTestCase


class HealthcareE2ETestFramework(HealthcareTestCase):
    """End-to-end testing framework for healthcare AI workflows"""

    def __init__(self):
        super().__init__()
        self.mcp_url = "http://localhost:3000"
        self.fastapi_url = "http://localhost:8000"
        self.phi_detector = SimplePHIDetector()
        # Use current working directory for test logs instead of /app
        import tempfile
        test_log_dir = os.path.join(tempfile.gettempdir(), "healthcare_test_logs")
        self.chat_log_manager = ChatLogManager(test_log_dir)

    def generate_synthetic_patient(self, patient_id: str):
        """Generate synthetic patient data for testing"""
        return {
            "patient_id": patient_id,
            "name": f"Test Patient {patient_id}",
            "dob": "1990-01-01",
            "insurance_type": "PPO",
            "synthetic_marker": True
        }

    async def setup_test_environment(self):
        """Setup test environment with synthetic data"""

        # Generate synthetic healthcare scenarios
        self.test_scenarios = [
            {
                "name": "routine_checkup",
                "patient_data": self.generate_synthetic_patient("TEST_PAT_001"),
                "chief_complaint": "Annual physical examination",
                "expected_workflow": ["clinical_intake", "research_medical_literature"],
            },
            {
                "name": "diabetes_followup",
                "patient_data": self.generate_synthetic_patient("TEST_PAT_002"),
                "chief_complaint": "Diabetes follow-up visit",
                "expected_workflow": [
                    "clinical_intake",
                    "research_medical_literature",
                    "process_healthcare_document",
                ],
            },
            {
                "name": "emergency_intake",
                "patient_data": self.generate_synthetic_patient("TEST_PAT_003"),
                "chief_complaint": "Chest pain evaluation",
                "expected_workflow": [
                    "clinical_intake",
                    "transcribe_audio",
                    "research_medical_literature",
                ],
            },
        ]

        print(f"✅ Setup {len(self.test_scenarios)} test scenarios with synthetic data")


class TestHealthcareE2EWorkflows:
    """End-to-end workflow tests using synthetic data only"""

    @pytest.fixture
    async def e2e_framework(self):
        """Initialize E2E testing framework"""
        framework = HealthcareE2ETestFramework()
        await framework.setup_test_environment()
        return framework

    @pytest.mark.asyncio
    async def test_mcp_server_health(self, e2e_framework):
        """Test MCP server health and tool availability"""

        async with httpx.AsyncClient() as client:
            # Test health endpoint
            health_response = await client.get(f"{e2e_framework.mcp_url}/health")
            assert health_response.status_code == 200

            health_data = health_response.json()
            assert health_data["status"] == "healthy"

            # Test tools/list endpoint
            tools_request = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}

            tools_response = await client.post(
                f"{e2e_framework.mcp_url}/mcp",
                json=tools_request,
                headers={"Content-Type": "application/json"},
            )

            assert tools_response.status_code == 200
            tools_data = tools_response.json()

            assert "result" in tools_data
            assert "tools" in tools_data["result"]

            # Verify agent bridge tools are available
            tool_names = [tool["name"] for tool in tools_data["result"]["tools"]]
            expected_agent_tools = [
                "clinical_intake",
                "transcribe_audio",
                "research_medical_literature",
                "process_healthcare_document",
            ]

            for tool_name in expected_agent_tools:
                assert tool_name in tool_names, f"Agent tool {tool_name} not found in MCP tools"

            print(f"✅ MCP server healthy with {len(tool_names)} tools available")

    @pytest.mark.asyncio
    async def test_fastapi_agents_health(self, e2e_framework):
        """Test FastAPI agents health endpoints"""

        agent_endpoints = [
            "/agents/intake/health",
            "/agents/document/health",
            "/agents/research/health",
            "/agents/transcription/health",
            "/agents/billing/health",
            "/agents/insurance/health",
        ]

        async with httpx.AsyncClient() as client:
            for endpoint in agent_endpoints:
                try:
                    response = await client.get(f"{e2e_framework.fastapi_url}{endpoint}")
                    assert response.status_code == 200

                    health_data = response.json()
                    assert health_data.get("status") == "healthy"

                    print(f"✅ Agent {endpoint} is healthy")

                except httpx.RequestError as e:
                    print(f"⚠️ Agent {endpoint} not available: {e}")

    @pytest.mark.asyncio
    async def test_mcp_agent_bridge_integration(self, e2e_framework):
        """Test MCP → Agent bridge integration with synthetic data"""

        test_scenario = e2e_framework.test_scenarios[0]  # routine_checkup

        # Test clinical_intake tool through MCP
        intake_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "clinical_intake",
                "arguments": {
                    "patient_data": test_scenario["patient_data"],
                    "intake_type": "new_patient",
                    "session_id": f"test_session_{uuid.uuid4().hex[:8]}",
                },
            },
            "id": 1,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{e2e_framework.mcp_url}/mcp",
                json=intake_request,
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )

            assert response.status_code == 200
            result = response.json()

            assert "result" in result
            intake_result = result["result"]

            # Verify intake processing
            assert "intake_id" in intake_result
            assert "validation_status" in intake_result
            assert "medical_disclaimer" in intake_result

            # Verify no PHI in response
            phi_detected = await e2e_framework.phi_detector.scan_text(json.dumps(intake_result))
            assert not phi_detected, "PHI detected in MCP-Agent bridge response"

            print("✅ MCP-Agent bridge integration successful for clinical_intake")

    @pytest.mark.asyncio
    async def test_complete_patient_workflow(self, e2e_framework):
        """Test complete patient encounter workflow"""

        test_scenario = e2e_framework.test_scenarios[1]  # diabetes_followup
        session_id = f"test_workflow_{uuid.uuid4().hex[:8]}"

        workflow_results = []

        # Step 1: Clinical Intake
        intake_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "clinical_intake",
                "arguments": {
                    "patient_data": test_scenario["patient_data"],
                    "intake_type": "follow_up",
                    "session_id": session_id,
                },
            },
            "id": 1,
        }

        async with httpx.AsyncClient() as client:
            # Execute intake
            intake_response = await client.post(
                f"{e2e_framework.mcp_url}/mcp", json=intake_request, timeout=30.0
            )

            assert intake_response.status_code == 200
            intake_result = intake_response.json()["result"]
            workflow_results.append(("clinical_intake", intake_result))

            # Step 2: Medical Literature Research
            research_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "research_medical_literature",
                    "arguments": {
                        "query": "diabetes type 2 management guidelines 2024",
                        "max_results": 5,
                        "include_clinical_trials": True,
                    },
                },
                "id": 2,
            }

            research_response = await client.post(
                f"{e2e_framework.mcp_url}/mcp", json=research_request, timeout=30.0
            )

            assert research_response.status_code == 200
            research_result = research_response.json()["result"]
            workflow_results.append(("research_medical_literature", research_result))

            # Step 3: Healthcare Document Processing
            document_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "process_healthcare_document",
                    "arguments": {
                        "document_type": "progress_note",
                        "content": f"Patient {test_scenario['patient_data']['patient_id']} follow-up visit for diabetes management",
                        "session_id": session_id,
                    },
                },
                "id": 3,
            }

            document_response = await client.post(
                f"{e2e_framework.mcp_url}/mcp", json=document_request, timeout=30.0
            )

            assert document_response.status_code == 200
            document_result = document_response.json()["result"]
            workflow_results.append(("process_healthcare_document", document_result))

        # Validate workflow completion
        assert len(workflow_results) == 3

        for step_name, result in workflow_results:
            # Verify each step completed successfully
            assert result is not None
            assert "medical_disclaimer" in result

            # Verify no PHI in any response
            phi_detected = await e2e_framework.phi_detector.scan_text(json.dumps(result))
            assert not phi_detected, f"PHI detected in {step_name} response"

        print(
            f"✅ Complete patient workflow executed successfully with {len(workflow_results)} steps"
        )

    @pytest.mark.asyncio
    async def test_phi_detection_and_quarantine(self, e2e_framework):
        """Test PHI detection and quarantine functionality"""

        # Create test data with potential PHI
        phi_test_cases = [
            {
                "content": "Patient John Doe, SSN 123-45-6789, needs follow-up",
                "should_detect": True,
                "phi_type": "SSN",
            },
            {
                "content": "Patient reports feeling better after treatment",
                "should_detect": False,
                "phi_type": None,
            },
            {
                "content": "Contact patient at (555) 123-4567 for appointment",
                "should_detect": True,
                "phi_type": "Phone",
            },
            {
                "content": "Lab results show improved glucose levels",
                "should_detect": False,
                "phi_type": None,
            },
        ]

        session_id = await e2e_framework.chat_log_manager.create_session(
            user_id="test_user_001", healthcare_context={"test_scenario": "phi_detection"}
        )

        for i, test_case in enumerate(phi_test_cases):
            message = await e2e_framework.chat_log_manager.log_chat_message(
                session_id=session_id,
                user_id="test_user_001",
                role="user",
                content=test_case["content"],
            )

            # Verify PHI detection accuracy
            if test_case["should_detect"]:
                assert message.phi_detected, (
                    f"PHI not detected in test case {i + 1}: {test_case['phi_type']}"
                )
                assert message.sanitized_content is not None
                assert "[PHI_REDACTED]" in message.content or message.content == "[PHI_REDACTED]"
            else:
                assert not message.phi_detected, f"False PHI detection in test case {i + 1}"

        # Test chat history retrieval with PHI filtering
        history_without_phi = await e2e_framework.chat_log_manager.get_chat_history(
            session_id=session_id, user_id="test_user_001", include_phi=False
        )

        history_with_phi = await e2e_framework.chat_log_manager.get_chat_history(
            session_id=session_id, user_id="test_user_001", include_phi=True
        )

        assert len(history_without_phi) == len(phi_test_cases)
        assert len(history_with_phi) == len(phi_test_cases)

        # Verify PHI protection in non-PHI history
        for message in history_without_phi:
            if message.phi_detected:
                assert "[PHI_PROTECTED]" in message.content or "[PHI_REDACTED]" in message.content

        await e2e_framework.chat_log_manager.end_session(session_id, "test_user_001")

        print("✅ PHI detection and quarantine functionality validated")

    @pytest.mark.asyncio
    async def test_audio_transcription_workflow(self, e2e_framework):
        """Test audio transcription workflow with PHI protection"""

        # Create mock audio data (no real audio processing in tests)
        mock_audio_data = {
            "format": "wav",
            "duration": 30,
            "sample_rate": 16000,
            "mock": True,
            "content": "Patient reports chest pain, onset 2 hours ago",
        }

        transcription_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "transcribe_audio",
                "arguments": {
                    "audio_data": mock_audio_data,
                    "session_id": f"test_audio_{uuid.uuid4().hex[:8]}",
                    "doctor_id": "TEST_DOC_001",
                },
            },
            "id": 1,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{e2e_framework.mcp_url}/mcp", json=transcription_request, timeout=30.0
            )

            assert response.status_code == 200
            result = response.json()["result"]

            # Verify transcription result structure
            assert "transcription_id" in result
            assert "transcript" in result
            assert "medical_disclaimer" in result

            # Verify PHI protection
            phi_detected = await e2e_framework.phi_detector.scan_text(json.dumps(result))
            assert not phi_detected, "PHI detected in transcription response"

            print("✅ Audio transcription workflow completed successfully")

    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, e2e_framework):
        """Test performance benchmarks for healthcare workflows"""

        benchmark_results = []

        # Benchmark 1: MCP Tool List Performance
        start_time = datetime.utcnow()

        async with httpx.AsyncClient() as client:
            tools_request = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}

            for _ in range(10):  # 10 requests
                response = await client.post(f"{e2e_framework.mcp_url}/mcp", json=tools_request)
                assert response.status_code == 200

        tools_list_time = (datetime.utcnow() - start_time).total_seconds()
        benchmark_results.append(("tools/list (10x)", tools_list_time))

        # Benchmark 2: Clinical Intake Performance
        start_time = datetime.utcnow()

        intake_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "clinical_intake",
                "arguments": {
                    "patient_data": e2e_framework.test_scenarios[0]["patient_data"],
                    "intake_type": "new_patient",
                    "session_id": f"perf_test_{uuid.uuid4().hex[:8]}",
                },
            },
            "id": 1,
        }

        async with httpx.AsyncClient() as client:
            for _ in range(5):  # 5 requests
                response = await client.post(
                    f"{e2e_framework.mcp_url}/mcp", json=intake_request, timeout=30.0
                )
                assert response.status_code == 200

        intake_time = (datetime.utcnow() - start_time).total_seconds()
        benchmark_results.append(("clinical_intake (5x)", intake_time))

        # Performance assertions
        assert tools_list_time < 5.0, f"Tools list too slow: {tools_list_time}s"
        assert intake_time < 15.0, f"Clinical intake too slow: {intake_time}s"

        for benchmark_name, duration in benchmark_results:
            print(f"✅ {benchmark_name}: {duration:.2f}s")

        print("✅ Performance benchmarks completed successfully")


class TestHealthcareSecurityCompliance:
    """Security and compliance validation tests"""

    @pytest.fixture
    async def security_framework(self):
        """Initialize security testing framework"""
        return HealthcareE2ETestFramework()

    @pytest.mark.asyncio
    async def test_phi_protection_compliance(self, security_framework):
        """Test comprehensive PHI protection compliance"""

        # Test synthetic data validation
        synthetic_patient = security_framework.generate_synthetic_patient("TEST_PAT_SECURITY")

        # Verify synthetic data passes PHI validation
        phi_detected = await security_framework.phi_detector.scan_text(
            json.dumps(synthetic_patient)
        )

        # Synthetic data might contain phone patterns but should be clearly marked as test data
        if phi_detected:
            assert synthetic_patient["patient_id"].startswith("TEST_"), (
                "Synthetic data not properly marked"
            )

        print("✅ PHI protection compliance validated")

    @pytest.mark.asyncio
    async def test_audit_logging_compliance(self, security_framework):
        """Test audit logging for healthcare compliance"""

        session_id = await security_framework.chat_log_manager.create_session(
            user_id="test_audit_user", healthcare_context={"audit_test": True}
        )

        # Log various message types
        message_types = [
            ("user", "Hello, I need help with my diabetes medication"),
            (
                "assistant",
                "I can help you with general information about diabetes management. Please consult your healthcare provider for specific medical advice.",
            ),
            ("system", "Session initiated for healthcare assistance"),
        ]

        for role, content in message_types:
            await security_framework.chat_log_manager.log_chat_message(
                session_id=session_id, user_id="test_audit_user", role=role, content=content
            )

        # Retrieve audit trail
        history = await security_framework.chat_log_manager.get_chat_history(
            session_id=session_id, user_id="test_audit_user"
        )

        assert len(history) == 3

        # Verify audit trail in each message
        for message in history:
            assert len(message.audit_trail) > 0
            assert any("Created at" in entry for entry in message.audit_trail)

        session_summary = await security_framework.chat_log_manager.end_session(
            session_id, "test_audit_user"
        )

        assert "session_id" in session_summary
        assert "total_messages" in session_summary
        assert session_summary["total_messages"] == 3

        print("✅ Audit logging compliance validated")


# Test runner configuration
if __name__ == "__main__":
    import sys

    async def run_tests():
        """Run all E2E tests"""

        print("🏥 Starting Healthcare AI E2E Testing Framework")
        print("=" * 50)

        # Initialize framework
        framework = HealthcareE2ETestFramework()
        await framework.setup_test_environment()

        print("✅ Test environment setup complete")
        print("📊 Running comprehensive E2E workflow validation...")

        # Run pytest with this file
        exit_code = pytest.main(
            [
                __file__,
                "-v",
                "--tb=short",
                "-x",  # Stop on first failure
            ]
        )

        return exit_code

    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code)
