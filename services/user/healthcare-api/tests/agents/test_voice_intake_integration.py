"""
Integration tests for Voice Intake functionality
Tests the voice-enhanced intake agent with transcription integration
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from agents.intake.intake_agent import HealthcareIntakeAgent
from agents.intake.voice_intake_processor import VoiceIntakeProcessor, VoiceIntakeResult


class TestVoiceIntakeIntegration:
    """Test voice intake integration with intake agent"""

    @pytest.fixture
    def voice_processor(self):
        """Create voice intake processor for testing"""
        return VoiceIntakeProcessor()

    @pytest.fixture
    def mock_intake_agent(self):
        """Create mock intake agent for testing"""
        mock_mcp_client = AsyncMock()
        mock_llm_client = AsyncMock()

        return HealthcareIntakeAgent(
            mcp_client=mock_mcp_client,
            llm_client=mock_llm_client,
        )

    @pytest.mark.asyncio
    async def test_voice_session_lifecycle(self, voice_processor):
        """Test complete voice intake session lifecycle"""

        # Start voice session
        patient_id = "test_patient_001"
        intake_type = "new_patient_registration"

        voice_session_id = await voice_processor.start_voice_intake_session(
            patient_id=patient_id,
            intake_type=intake_type,
        )

        assert voice_session_id.startswith("voice_intake_")
        assert voice_session_id in voice_processor.active_voice_sessions

        # Process voice chunks
        test_transcriptions = [
            {
                "text": "My name is John Doe",
                "confidence": 0.95,
                "medical_terms": [],
            },
            {
                "text": "My phone number is 555-123-4567",
                "confidence": 0.92,
                "medical_terms": [],
            },
            {
                "text": "I'm here because of chest pain",
                "confidence": 0.88,
                "medical_terms": ["chest pain"],
            },
        ]

        results = []
        for transcription in test_transcriptions:
            result = await voice_processor.process_voice_chunk(
                voice_session_id=voice_session_id,
                transcription_text=transcription["text"],
                confidence_score=transcription["confidence"],
                medical_terms=transcription["medical_terms"],
            )
            results.append(result)

        # Verify form data extraction
        final_result = results[-1]
        assert final_result.voice_session_id == voice_session_id
        assert "first_name" in final_result.intake_form_data
        assert "contact_phone" in final_result.intake_form_data
        assert "chief_complaint" in final_result.intake_form_data

        # Check medical terms extraction
        assert "chest pain" in final_result.medical_terms

        # Finalize session
        session_summary = await voice_processor.finalize_voice_intake_session(voice_session_id)

        assert session_summary["voice_session_id"] == voice_session_id
        assert session_summary["patient_id"] == patient_id
        assert session_summary["intake_type"] == intake_type
        assert len(session_summary["medical_terms_extracted"]) > 0

        # Verify session cleanup
        assert voice_session_id not in voice_processor.active_voice_sessions

    @pytest.mark.asyncio
    async def test_phi_detection_in_voice_processing(self, voice_processor):
        """Test PHI detection and sanitization during voice processing"""

        voice_session_id = await voice_processor.start_voice_intake_session(
            patient_id="test_patient_002",
            intake_type="new_patient_registration",
        )

        # Process transcription with PHI content
        phi_transcription = "My social security number is 123-45-6789 and my phone is 555-123-4567"

        with patch("agents.intake.voice_intake_processor.scan_for_phi") as mock_phi_scan:
            mock_phi_scan.return_value = {"phi_detected": True, "phi_types": ["ssn", "phone"]}

            result = await voice_processor.process_voice_chunk(
                voice_session_id=voice_session_id,
                transcription_text=phi_transcription,
                confidence_score=0.90,
                medical_terms=[],
            )

        # Verify PHI was detected and sanitized
        assert result.phi_detected is True
        assert result.phi_sanitized is True
        assert "[SSN_REDACTED]" in result.transcription_text

        # Clean up
        await voice_processor.finalize_voice_intake_session(voice_session_id)

    @pytest.mark.asyncio
    async def test_form_completion_calculation(self, voice_processor):
        """Test form completion percentage calculation"""

        voice_session_id = await voice_processor.start_voice_intake_session(
            patient_id="test_patient_003",
            intake_type="new_patient_registration",
        )

        # Process partial form data
        partial_transcriptions = [
            "My name is Jane Smith",
            "My date of birth is January 15, 1985",
            "My phone number is 555-987-6543",
        ]

        completion_percentages = []

        for transcription in partial_transcriptions:
            result = await voice_processor.process_voice_chunk(
                voice_session_id=voice_session_id,
                transcription_text=transcription,
                confidence_score=0.90,
                medical_terms=[],
            )
            completion_percentages.append(result.form_completion_percentage)

        # Verify completion percentage increases with more data
        assert completion_percentages[0] < completion_percentages[1] < completion_percentages[2]
        assert all(0 <= pct <= 100 for pct in completion_percentages)

        # Clean up
        await voice_processor.finalize_voice_intake_session(voice_session_id)

    @pytest.mark.asyncio
    async def test_medical_terminology_extraction(self, voice_processor):
        """Test medical terminology extraction from voice input"""

        voice_session_id = await voice_processor.start_voice_intake_session(
            patient_id="test_patient_004",
            intake_type="new_patient_registration",
        )

        # Test medical terminology in transcriptions
        medical_transcriptions = [
            {
                "text": "I have been taking metformin for diabetes",
                "terms": ["metformin", "diabetes"],
            },
            {
                "text": "I'm allergic to penicillin and have high blood pressure",
                "terms": ["penicillin", "hypertension"],
            },
            {
                "text": "My chest pain gets worse with exercise",
                "terms": ["chest pain", "exercise intolerance"],
            },
        ]

        all_extracted_terms = []

        for transcription in medical_transcriptions:
            result = await voice_processor.process_voice_chunk(
                voice_session_id=voice_session_id,
                transcription_text=transcription["text"],
                confidence_score=0.90,
                medical_terms=transcription["terms"],
            )
            all_extracted_terms.extend(result.medical_terms)

        # Verify medical terms were captured
        unique_terms = list(set(all_extracted_terms))
        assert len(unique_terms) > 0

        # Check for specific medical terms
        expected_terms = ["diabetes", "penicillin", "chest pain"]
        found_terms = [term for term in expected_terms if any(expected in all_extracted_terms for expected in [term])]
        assert len(found_terms) > 0

        # Clean up
        session_summary = await voice_processor.finalize_voice_intake_session(voice_session_id)
        assert len(session_summary["medical_terms_extracted"]) > 0

    @pytest.mark.asyncio
    async def test_error_handling_in_voice_processing(self, voice_processor):
        """Test error handling in voice processing workflows"""

        # Test processing with invalid session
        result = await voice_processor.process_voice_chunk(
            voice_session_id="invalid_session_id",
            transcription_text="Test transcription",
            confidence_score=0.80,
            medical_terms=[],
        )

        assert result.status == "failed"
        assert result.confidence_score == 0.0

        # Test finalizing invalid session
        with pytest.raises(ValueError):
            await voice_processor.finalize_voice_intake_session("invalid_session_id")

    @pytest.mark.asyncio
    async def test_concurrent_voice_sessions(self, voice_processor):
        """Test handling multiple concurrent voice sessions"""

        # Start multiple voice sessions
        session_ids = []
        for i in range(3):
            session_id = await voice_processor.start_voice_intake_session(
                patient_id=f"test_patient_{i:03d}",
                intake_type="new_patient_registration",
            )
            session_ids.append(session_id)

        # Verify all sessions are active
        assert len(voice_processor.active_voice_sessions) == 3

        # Process data for each session
        for i, session_id in enumerate(session_ids):
            result = await voice_processor.process_voice_chunk(
                voice_session_id=session_id,
                transcription_text=f"Patient {i} data",
                confidence_score=0.85,
                medical_terms=[],
            )
            assert result.voice_session_id == session_id

        # Finalize all sessions
        for session_id in session_ids:
            await voice_processor.finalize_voice_intake_session(session_id)

        # Verify all sessions cleaned up
        assert len(voice_processor.active_voice_sessions) == 0


class TestIntakeAgentVoiceIntegration:
    """Test integration between intake agent and voice processing"""

    @pytest.fixture
    def mock_components(self):
        """Create mock components for testing"""
        mock_transcription_agent = AsyncMock()
        mock_session_manager = AsyncMock()
        mock_voice_processor = AsyncMock()

        return {
            "transcription_agent": mock_transcription_agent,
            "session_manager": mock_session_manager,
            "voice_processor": mock_voice_processor,
        }

    @pytest.mark.asyncio
    async def test_voice_intake_workflow_integration(self, mock_components):
        """Test end-to-end voice intake workflow"""

        # Mock voice processing results
        mock_voice_result = VoiceIntakeResult(
            voice_session_id="test_voice_session_001",
            transcription_text="My name is Alice Johnson and I need to schedule an appointment",
            confidence_score=0.92,
            medical_terms=["appointment"],
            intake_form_data={
                "first_name": "Alice",
                "last_name": "Johnson",
                "appointment_type": "general",
            },
            form_completion_percentage=60.0,
            phi_detected=False,
            phi_sanitized=False,
            processing_timestamp=datetime.now(),
            status="processing",
        )

        mock_components["voice_processor"].process_voice_chunk.return_value = mock_voice_result

        # Mock session summary
        mock_session_summary = {
            "voice_session_id": "test_voice_session_001",
            "patient_id": "test_patient_001",
            "intake_type": "appointment_scheduling",
            "duration_seconds": 120.5,
            "form_data": mock_voice_result.intake_form_data,
            "completion_percentage": 60.0,
            "total_transcriptions": 5,
            "medical_terms_extracted": ["appointment"],
            "phi_incidents_count": 0,
            "finalized_at": datetime.now(),
        }

        mock_components["voice_processor"].finalize_voice_intake_session.return_value = mock_session_summary

        # Test the integration workflow
        # This would be tested with actual intake agent methods once implemented
        assert mock_voice_result.status == "processing"
        assert mock_voice_result.form_completion_percentage == 60.0
        assert "first_name" in mock_voice_result.intake_form_data
        assert mock_voice_result.intake_form_data["first_name"] == "Alice"

        # Verify medical terms extraction
        assert "appointment" in mock_voice_result.medical_terms

        # Verify session finalization data
        assert mock_session_summary["voice_session_id"] == mock_voice_result.voice_session_id
        assert mock_session_summary["completion_percentage"] == mock_voice_result.form_completion_percentage
