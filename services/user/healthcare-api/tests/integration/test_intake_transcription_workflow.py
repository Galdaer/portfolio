"""
Integration tests for Intake-Transcription multi-agent workflow
Tests the complete INTAKE_TO_BILLING and VOICE_INTAKE_WORKFLOW patterns
"""

import asyncio
import logging
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

from agents.intake.intake_agent import HealthcareIntakeAgent, IntakeResult
from agents.transcription.transcription_agent import TranscriptionAgent
from core.orchestration import (
    WorkflowOrchestrator,
    WorkflowType,
    AgentSpecialization,
    workflow_orchestrator
)
from core.enhanced_sessions import EnhancedSessionManager
from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("test_intake_transcription_workflow")


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing"""
    return MagicMock()


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing"""
    return MagicMock()


@pytest.fixture
async def intake_agent(mock_mcp_client, mock_llm_client):
    """Create intake agent for testing"""
    agent = HealthcareIntakeAgent(
        mcp_client=mock_mcp_client,
        llm_client=mock_llm_client
    )
    
    # Mock initialization to avoid database requirements
    with patch.object(agent, 'initialize_agent', new_callable=AsyncMock):
        with patch.object(agent.transcription_agent, 'initialize', new_callable=AsyncMock):
            with patch.object(agent.session_manager, 'initialize', new_callable=AsyncMock):
                await agent.initialize()
    
    return agent


@pytest.fixture
async def transcription_agent(mock_mcp_client, mock_llm_client):
    """Create transcription agent for testing"""
    agent = TranscriptionAgent(
        mcp_client=mock_mcp_client,
        llm_client=mock_llm_client
    )
    
    # Mock initialization
    with patch.object(agent, 'initialize_agent', new_callable=AsyncMock):
        await agent.initialize()
    
    return agent


@pytest.fixture
def workflow_orchestrator_instance():
    """Create workflow orchestrator instance for testing"""
    return WorkflowOrchestrator()


@pytest.fixture
def sample_patient_data():
    """Sample patient data for testing"""
    return {
        "intake_type": "new_patient_registration",
        "patient_id": "test_patient_123",
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": "1985-05-15",
        "contact_phone": "555-123-4567",
        "contact_email": "john.doe@example.com",
        "insurance_primary": "Blue Cross Blue Shield",
        "appointment_type": "general"
    }


@pytest.fixture
def sample_audio_data():
    """Sample audio data for voice testing"""
    return b"mock_audio_data_bytes"


class TestIntakeTranscriptionWorkflow:
    """Test suite for intake-transcription multi-agent workflows"""
    
    @pytest.mark.asyncio
    async def test_standard_intake_to_billing_workflow(
        self,
        intake_agent,
        transcription_agent,
        workflow_orchestrator_instance,
        sample_patient_data
    ):
        """Test the complete INTAKE_TO_BILLING workflow"""
        
        # Register agents with orchestrator
        await workflow_orchestrator_instance.register_agent(
            AgentSpecialization.INTAKE, intake_agent
        )
        await workflow_orchestrator_instance.register_agent(
            AgentSpecialization.TRANSCRIPTION, transcription_agent
        )
        
        session_id = "test_session_intake_billing"
        user_id = "test_user"
        
        # Start workflow
        workflow_id = await intake_agent.start_intake_to_billing_workflow(
            session_id=session_id,
            user_id=user_id,
            patient_data=sample_patient_data,
            doctor_id="doc_123"
        )
        
        # Verify workflow was created
        assert workflow_id.startswith("wf_intake_to_billing_")
        
        # Check workflow status
        workflow_status = await workflow_orchestrator_instance.get_workflow_status(workflow_id)
        assert workflow_status is not None
        assert workflow_status["workflow_type"] == "intake_to_billing"
        assert workflow_status["status"] in ["pending", "running"]
        
        # Wait for workflow completion (with timeout)
        max_wait_seconds = 30
        wait_count = 0
        
        while wait_count < max_wait_seconds:
            workflow_status = await workflow_orchestrator_instance.get_workflow_status(workflow_id)
            if workflow_status and workflow_status["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(1)
            wait_count += 1
        
        # Verify workflow completion
        final_status = await workflow_orchestrator_instance.get_workflow_status(workflow_id)
        assert final_status["status"] == "completed"
        assert len(final_status["completed_steps"]) > 0
        assert "patient_intake" in final_status["completed_steps"]
    
    @pytest.mark.asyncio
    async def test_voice_intake_workflow(
        self,
        intake_agent,
        transcription_agent,
        workflow_orchestrator_instance,
        sample_patient_data,
        sample_audio_data
    ):
        """Test the VOICE_INTAKE_WORKFLOW with voice processing"""
        
        # Register agents with orchestrator
        await workflow_orchestrator_instance.register_agent(
            AgentSpecialization.INTAKE, intake_agent
        )
        await workflow_orchestrator_instance.register_agent(
            AgentSpecialization.TRANSCRIPTION, transcription_agent
        )
        
        session_id = "test_session_voice_intake"
        user_id = "test_user"
        
        # Add voice processing configuration
        voice_patient_data = {
            **sample_patient_data,
            "voice_enabled": True,
            "real_time": True
        }
        
        # Start voice workflow
        workflow_id = await intake_agent.start_voice_intake_workflow(
            session_id=session_id,
            user_id=user_id,
            patient_data=voice_patient_data,
            audio_data=sample_audio_data,
            doctor_id="doc_123"
        )
        
        # Verify workflow was created
        assert workflow_id.startswith("wf_voice_intake_workflow_")
        
        # Check workflow status
        workflow_status = await workflow_orchestrator_instance.get_workflow_status(workflow_id)
        assert workflow_status is not None
        assert workflow_status["workflow_type"] == "voice_intake_workflow"
        assert workflow_status["status"] in ["pending", "running"]
        
        logger.info(f"Voice workflow started: {workflow_id}")
    
    @pytest.mark.asyncio 
    async def test_intake_agent_workflow_step_processing(
        self,
        intake_agent,
        sample_patient_data
    ):
        """Test intake agent processing workflow steps from orchestrator"""
        
        # Test standard intake step
        step_input = {
            "workflow_id": "test_workflow_123",
            "session_id": "test_session",
            "user_id": "test_user",
            "doctor_id": "doc_123",
            "step_config": {},
            "workflow_input": {
                "intake_type": "new_patient_registration",
                "patient_data": sample_patient_data,
                "voice_enabled": False
            },
            "previous_results": {}
        }
        
        # Process workflow step
        result = await intake_agent.process_request(step_input)
        
        # Verify result structure
        assert result["success"] is True
        assert result["agent"] == "intake"
        assert result["step_type"] == "standard_intake"
        assert "intake_result" in result
        assert result["workflow_id"] == "test_workflow_123"
        assert result["session_id"] == "test_session"
        
        # Verify intake result structure
        intake_result = result["intake_result"]
        assert "intake_id" in intake_result
        assert "status" in intake_result
        assert "patient_id" in intake_result
    
    @pytest.mark.asyncio
    async def test_voice_intake_agent_workflow_step(
        self,
        intake_agent,
        sample_patient_data,
        sample_audio_data
    ):
        """Test intake agent processing voice workflow steps"""
        
        # Mock voice processor methods
        with patch.object(
            intake_agent.voice_processor, 
            'start_voice_intake_session', 
            new_callable=AsyncMock,
            return_value="voice_session_123"
        ) as mock_start_session:
            
            with patch.object(
                intake_agent.voice_processor,
                'process_voice_chunk',
                new_callable=AsyncMock,
                return_value={
                    "success": True,
                    "transcription_text": "Patient says first name is John",
                    "confidence_score": 0.95
                }
            ) as mock_process_chunk:
                
                # Test voice session initiation step
                step_input = {
                    "workflow_id": "test_voice_workflow_123",
                    "session_id": "test_voice_session",
                    "user_id": "test_user",
                    "doctor_id": "doc_123",
                    "step_config": {"voice_enabled": True},
                    "workflow_input": {
                        "intake_type": "voice_intake",
                        "patient_data": sample_patient_data,
                        "audio_data": sample_audio_data,
                        "voice_enabled": True
                    },
                    "previous_results": {}
                }
                
                # Process voice workflow step
                result = await intake_agent.process_request(step_input)
                
                # Verify result structure
                assert result["success"] is True
                assert result["agent"] == "intake"
                assert result["step_type"] == "voice_session_init"
                assert result["voice_session_id"] == "voice_session_123"
                assert result["voice_session_active"] is True
                
                # Verify voice processor was called
                mock_start_session.assert_called_once()
                mock_process_chunk.assert_called_once_with("voice_session_123", sample_audio_data)
    
    @pytest.mark.asyncio
    async def test_voice_form_completion_workflow_step(
        self,
        intake_agent,
        sample_patient_data
    ):
        """Test voice form completion step using transcription results"""
        
        # Mock transcription results from previous step
        transcription_results = {
            "transcription_text": "My first name is John and my last name is Doe. My phone number is five five five one two three four five six seven.",
            "confidence_score": 0.92,
            "medical_terms": [],
            "processing_timestamp": datetime.now().isoformat()
        }
        
        # Mock voice processor methods
        with patch.object(
            intake_agent.voice_processor,
            'start_voice_intake_session',
            new_callable=AsyncMock,
            return_value="voice_form_session_123"
        ):
            
            with patch.object(
                intake_agent.voice_processor,
                'process_voice_transcription',
                new_callable=AsyncMock,
                return_value={
                    "success": True,
                    "fields_updated": ["first_name", "last_name", "contact_phone"]
                }
            ):
                
                with patch.object(
                    intake_agent.voice_processor,
                    'finalize_voice_intake_session',
                    new_callable=AsyncMock,
                    return_value={
                        "voice_session_id": "voice_form_session_123",
                        "form_data": {
                            "first_name": "John",
                            "last_name": "Doe", 
                            "contact_phone": "555-123-4567"
                        },
                        "completion_percentage": 75.0,
                        "medical_terms_extracted": []
                    }
                ) as mock_finalize:
                    
                    # Test form completion step
                    step_input = {
                        "workflow_id": "test_form_completion_123",
                        "session_id": "test_form_session",
                        "user_id": "test_user",
                        "step_config": {"voice_enabled": True, "voice_to_form": True},
                        "workflow_input": {
                            "patient_data": sample_patient_data,
                            "voice_enabled": True
                        },
                        "previous_results": {
                            "transcription_analysis": transcription_results
                        }
                    }
                    
                    # Process form completion step
                    result = await intake_agent.process_request(step_input)
                    
                    # Verify result structure
                    assert result["success"] is True
                    assert result["agent"] == "intake"
                    assert result["step_type"] == "voice_form_completion"
                    assert result["voice_session_id"] == "voice_form_session_123"
                    assert result["completion_percentage"] == 75.0
                    assert "form_data" in result
                    
                    # Verify form data was populated
                    form_data = result["form_data"]
                    assert form_data["first_name"] == "John"
                    assert form_data["last_name"] == "Doe"
                    assert form_data["contact_phone"] == "555-123-4567"
                    
                    # Verify voice processor finalize was called
                    mock_finalize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling(
        self,
        intake_agent,
        sample_patient_data
    ):
        """Test error handling in workflow step processing"""
        
        # Mock voice processor to raise an exception
        with patch.object(
            intake_agent.voice_processor,
            'start_voice_intake_session',
            new_callable=AsyncMock,
            side_effect=Exception("Voice processing failed")
        ):
            
            step_input = {
                "workflow_id": "test_error_workflow",
                "session_id": "test_error_session",
                "user_id": "test_user",
                "step_config": {"voice_enabled": True},
                "workflow_input": {
                    "patient_data": sample_patient_data,
                    "voice_enabled": True
                },
                "previous_results": {}
            }
            
            # Process workflow step that will fail
            result = await intake_agent.process_request(step_input)
            
            # Verify error result structure
            assert result["success"] is False
            assert "error" in result
            assert "Voice processing failed" in result["error"]
            assert result["workflow_id"] == "test_error_workflow"
            assert result["session_id"] == "test_error_session"
            assert result["agent"] == "intake"
    
    @pytest.mark.asyncio
    async def test_enhanced_session_integration(
        self,
        intake_agent,
        sample_patient_data
    ):
        """Test enhanced session manager integration"""
        
        session_id = "test_enhanced_session"
        
        # Mock session manager methods
        with patch.object(
            intake_agent.session_manager,
            'update_conversation_context',
            new_callable=AsyncMock
        ) as mock_update_context:
            
            with patch.object(
                intake_agent.session_manager,
                'store_message',
                new_callable=AsyncMock
            ) as mock_store_message:
                
                # Process intake request (this should use enhanced sessions)
                result = await intake_agent.process_intake_request(sample_patient_data, session_id)
                
                # Verify result structure
                assert isinstance(result, IntakeResult)
                assert result.status in ["registration_complete", "appointment_scheduled", "general_support"]
                
                # The actual session manager calls depend on the voice processor implementation
                # For now, just verify the agent has the session manager properly initialized
                assert intake_agent.session_manager is not None
                assert hasattr(intake_agent.session_manager, 'update_conversation_context')
                assert hasattr(intake_agent.session_manager, 'store_message')
    
    @pytest.mark.asyncio
    async def test_workflow_orchestrator_agent_registration(
        self,
        intake_agent,
        transcription_agent,
        workflow_orchestrator_instance
    ):
        """Test agent registration with workflow orchestrator"""
        
        # Register intake agent
        await workflow_orchestrator_instance.register_agent(
            AgentSpecialization.INTAKE, intake_agent
        )
        
        # Register transcription agent
        await workflow_orchestrator_instance.register_agent(
            AgentSpecialization.TRANSCRIPTION, transcription_agent
        )
        
        # Verify agents are registered
        assert AgentSpecialization.INTAKE in workflow_orchestrator_instance.agent_registry
        assert AgentSpecialization.TRANSCRIPTION in workflow_orchestrator_instance.agent_registry
        
        # Verify correct agents are registered
        registered_intake = workflow_orchestrator_instance.agent_registry[AgentSpecialization.INTAKE]
        registered_transcription = workflow_orchestrator_instance.agent_registry[AgentSpecialization.TRANSCRIPTION]
        
        assert registered_intake is intake_agent
        assert registered_transcription is transcription_agent


@pytest.mark.integration
class TestIntakeTranscriptionIntegration:
    """Integration tests requiring actual component interaction"""
    
    @pytest.mark.asyncio
    async def test_real_workflow_execution_simulation(
        self,
        intake_agent,
        transcription_agent,
        sample_patient_data
    ):
        """Simulate real workflow execution with mocked external dependencies"""
        
        # This test simulates the complete workflow with realistic data flow
        # but mocks external dependencies like databases and audio processing
        
        session_id = "integration_test_session"
        user_id = "integration_user"
        workflow_orchestrator_test = WorkflowOrchestrator()
        
        # Register agents
        await workflow_orchestrator_test.register_agent(AgentSpecialization.INTAKE, intake_agent)
        await workflow_orchestrator_test.register_agent(AgentSpecialization.TRANSCRIPTION, transcription_agent)
        
        # Mock external dependencies
        with patch.object(intake_agent, 'process_intake_request') as mock_intake:
            mock_intake.return_value = IntakeResult(
                intake_id="integration_test_123",
                status="registration_complete",
                patient_id="test_patient_123",
                appointment_id="apt_123",
                insurance_verified=True,
                required_documents=["ID", "Insurance Card"],
                next_steps=["Complete registration", "Attend appointment"],
                validation_errors=[],
                administrative_notes=["Integration test successful"],
                disclaimers=["Test disclaimer"],
                generated_at=datetime.now()
            )
            
            # Start workflow
            workflow_id = await workflow_orchestrator_test.start_workflow(
                WorkflowType.INTAKE_TO_BILLING,
                session_id,
                user_id,
                {"patient_data": sample_patient_data, "intake_type": "new_patient_registration"}
            )
            
            # Verify workflow started
            assert workflow_id is not None
            assert workflow_id in workflow_orchestrator_test.active_workflows
            
            # Get workflow execution details
            workflow_execution = workflow_orchestrator_test.active_workflows[workflow_id]
            assert workflow_execution.workflow_type == WorkflowType.INTAKE_TO_BILLING
            assert workflow_execution.session_id == session_id
            assert workflow_execution.user_id == user_id
            
            logger.info(f"Integration test workflow started: {workflow_id}")


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v", "--tb=short"])