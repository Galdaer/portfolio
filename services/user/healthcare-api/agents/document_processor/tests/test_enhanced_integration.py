"""
Integration Tests for Enhanced Document Processor

Tests the integration of document parsing, PHI detection, medical entity extraction,
and storage using existing healthcare-api infrastructure.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from src.healthcare_mcp.phi_detection import PHIDetectionResult

from agents.document_processor.enhanced_document_processor import EnhancedDocumentProcessor
from agents.document_processor.handlers import DocumentMetadata, DocumentProcessingResult


class TestEnhancedDocumentProcessor:
    """Test suite for enhanced document processor integration"""

    @pytest.fixture
    async def processor(self):
        """Create processor instance with mocked dependencies"""
        with patch("agents.document_processor.enhanced_document_processor.MedicalEntityExtractor"), \
             patch("agents.document_processor.enhanced_document_processor.PHIRedactor"), \
             patch("agents.document_processor.enhanced_document_processor.DocumentStorage"):

            processor = EnhancedDocumentProcessor(
                mcp_client=AsyncMock(),
                llm_client=AsyncMock(),
            )

            # Mock the initialize_agent method
            processor.initialize_agent = AsyncMock()

            return processor

    @pytest.fixture
    def sample_document_result(self):
        """Create sample document processing result"""
        metadata = DocumentMetadata(
            file_name="test_document.pdf",
            file_size=1024,
            file_type="pdf",
            mime_type="application/pdf",
            content_hash="abc123",
            created_at=datetime.now(),
        )

        phi_result = PHIDetectionResult(
            phi_detected=True,
            phi_types=["name", "phone"],
            confidence_scores=[0.9, 0.8],
            masked_text="Patient [REDACTED] called at [REDACTED]",
            detection_details=[
                {"type": "name", "text": "John Doe", "start": 8, "end": 16, "confidence": 0.9},
                {"type": "phone", "text": "555-1234", "start": 27, "end": 35, "confidence": 0.8},
            ],
        )

        return DocumentProcessingResult(
            success=True,
            document_id="TEST_DOC_001",
            content_type="pdf_document",
            extracted_text="Patient John Doe called at 555-1234",
            structured_data={"content_preview": "Patient John Doe..."},
            metadata=metadata,
            phi_analysis=phi_result,
            medical_entities=[
                {"text": "Patient", "type": "PERSON", "confidence": 0.9},
            ],
            processing_warnings=[],
            processing_errors=[],
            redacted_content="Patient [REDACTED] called at [REDACTED]",
            processing_time_ms=150,
        )

    @pytest.mark.asyncio
    async def test_processor_initialization(self, processor):
        """Test processor initialization with service health checks"""
        # Mock health check responses
        processor._check_scispacy_health = AsyncMock(return_value={"available": True})
        processor._check_storage_health = AsyncMock(return_value={"available": True})

        await processor.initialize()

        # Verify initialization
        processor.initialize_agent.assert_called_once()
        processor._check_scispacy_health.assert_called_once()
        processor._check_storage_health.assert_called_once()

    @pytest.mark.asyncio
    async def test_document_processing_integration(self, processor, sample_document_result):
        """Test integrated document processing workflow"""
        # Mock file processing
        with patch.object(processor, "_process_document_file", return_value=sample_document_result):
            request = {
                "operation": "process_document",
                "file_path": "/test/document.pdf",
                "options": {"store_document": True},
                "session_id": "test_session",
            }

            result = await processor._handle_document_processing(request, "test_session")

            # Verify processing result
            assert result["processing_success"] is True
            assert result["document_id"] == "TEST_DOC_001"
            assert result["content_type"] == "pdf_document"
            assert "phi_analysis" in result
            assert "medical_entities" in result
            assert result["disclaimers"] is not None

    @pytest.mark.asyncio
    async def test_batch_processing(self, processor, sample_document_result):
        """Test batch document processing"""
        # Mock batch processing
        with patch.object(processor, "_process_document_file", return_value=sample_document_result):
            request = {
                "operation": "batch_process",
                "file_paths": ["/test/doc1.pdf", "/test/doc2.pdf"],
                "options": {"store_document": False},
                "session_id": "batch_session",
            }

            result = await processor._handle_batch_processing(request, "batch_session")

            # Verify batch result
            assert result["total_documents"] == 2
            assert result["successful"] == 2
            assert result["failed"] == 0
            assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_phi_analysis(self, processor):
        """Test PHI analysis functionality"""
        # Mock PHI redactor
        phi_result = PHIDetectionResult(
            phi_detected=True,
            phi_types=["name", "phone"],
            confidence_scores=[0.9, 0.8],
            masked_text="Patient [REDACTED] called at [REDACTED]",
            detection_details=[],
        )

        processor.phi_redactor.analyze_phi = AsyncMock(return_value=phi_result)
        processor.phi_redactor.get_phi_summary = AsyncMock(return_value={"phi_detected": True})

        request = {
            "operation": "analyze_phi",
            "content": "Patient John Doe called at 555-1234",
            "session_id": "phi_test",
        }

        result = await processor._handle_phi_analysis(request, "phi_test")

        # Verify PHI analysis
        assert result["phi_detected"] is True
        assert result["phi_types"] == ["name", "phone"]
        assert "phi_summary" in result

    @pytest.mark.asyncio
    async def test_entity_extraction(self, processor):
        """Test medical entity extraction"""
        # Mock entity extractor
        entities = [
            {"text": "hypertension", "type": "PATHOLOGICAL_FORMATION", "confidence": 0.9},
            {"text": "aspirin", "type": "SIMPLE_CHEMICAL", "confidence": 0.8},
        ]

        processor.entity_extractor.extract_medical_entities = AsyncMock(return_value=entities)
        processor.entity_extractor.get_clinical_summary = AsyncMock(return_value={
            "has_medical_content": True,
            "entity_summary": {"medications": {"count": 1}},
        })

        request = {
            "operation": "extract_entities",
            "content": "Patient has hypertension, prescribed aspirin",
            "session_id": "entity_test",
        }

        result = await processor._handle_entity_extraction(request, "entity_test")

        # Verify entity extraction
        assert result["entity_count"] == 2
        assert len(result["entities"]) == 2
        assert "clinical_summary" in result

    @pytest.mark.asyncio
    async def test_document_search(self, processor):
        """Test document search functionality"""
        # Mock document storage search
        search_results = [
            {"document_id": "DOC_001", "file_name": "report1.pdf", "highlight": "...patient..."},
            {"document_id": "DOC_002", "file_name": "report2.pdf", "highlight": "...diagnosis..."},
        ]

        processor.document_storage.search_documents = AsyncMock(return_value=search_results)

        request = {
            "operation": "search_documents",
            "query": "patient diagnosis",
            "filters": {"content_type": "pdf_document"},
            "session_id": "search_test",
        }

        result = await processor._handle_document_search(request, "search_test")

        # Verify search results
        assert result["result_count"] == 2
        assert len(result["results"]) == 2
        assert result["query"] == "patient diagnosis"

    @pytest.mark.asyncio
    async def test_processing_statistics(self, processor):
        """Test processing statistics retrieval"""
        # Mock health checks
        processor._check_scispacy_health = AsyncMock(return_value={"available": True})
        processor._check_storage_health = AsyncMock(return_value={"available": True})

        stats = await processor.get_processing_statistics()

        # Verify statistics structure
        assert "processing_stats" in stats
        assert "handlers_available" in stats
        assert "service_health" in stats
        assert "disclaimers" in stats

    @pytest.mark.asyncio
    async def test_error_handling(self, processor):
        """Test error handling in document processing"""
        # Test with invalid request
        request = {
            "operation": "process_document",
            # Missing required fields
            "session_id": "error_test",
        }

        result = await processor._handle_document_processing(request, "error_test")

        # Should return error response
        assert result["success"] is False
        assert "error" in result
        assert result["agent_type"] == "enhanced_document_processor"


class TestDocumentHandlers:
    """Test document handlers integration"""

    def test_handler_registration(self):
        """Test that handlers are properly registered"""
        with patch("agents.document_processor.enhanced_document_processor.MedicalEntityExtractor"), \
             patch("agents.document_processor.enhanced_document_processor.PHIRedactor"), \
             patch("agents.document_processor.enhanced_document_processor.DocumentStorage"):

            processor = EnhancedDocumentProcessor(
                mcp_client=AsyncMock(),
                llm_client=AsyncMock(),
            )

            # Verify handlers are registered
            assert "pdf" in processor.handlers
            assert "docx" in processor.handlers
            assert "image" in processor.handlers

    @pytest.mark.asyncio
    async def test_text_handler_creation(self):
        """Test dynamic text handler creation"""
        with patch("agents.document_processor.enhanced_document_processor.MedicalEntityExtractor"), \
             patch("agents.document_processor.enhanced_document_processor.PHIRedactor"), \
             patch("agents.document_processor.enhanced_document_processor.DocumentStorage"):

            processor = EnhancedDocumentProcessor(
                mcp_client=AsyncMock(),
                llm_client=AsyncMock(),
            )

            # Mock document processing result
            sample_result = DocumentProcessingResult(
                success=True,
                document_id="TEXT_DOC_001",
                content_type="text_document",
                extracted_text="Sample text content",
                structured_data={},
                metadata=DocumentMetadata(
                    file_name="test.txt",
                    file_size=100,
                    file_type="text",
                    mime_type="text/plain",
                    content_hash="xyz789",
                    created_at=datetime.now(),
                ),
                phi_analysis=None,
                medical_entities=[],
                processing_warnings=[],
                processing_errors=[],
                processing_time_ms=50,
            )

            with patch("agents.document_processor.enhanced_document_processor.TextDocumentHandler") as mock_handler:
                mock_handler.return_value.process_document = AsyncMock(return_value=sample_result)

                result = await processor._process_document_content("Sample text content", {})

                assert result.success is True
                assert result.document_id == "TEXT_DOC_001"


@pytest.mark.integration
class TestServiceIntegration:
    """Integration tests with actual services"""

    @pytest.mark.asyncio
    async def test_scispacy_integration(self):
        """Test integration with SciSpacy service (requires service running)"""
        from agents.document_processor.extractors.entity_extractor import MedicalEntityExtractor

        extractor = MedicalEntityExtractor()
        health = await extractor.health_check()

        # This will pass if SciSpacy service is running
        if health["available"]:
            entities = await extractor.extract_medical_entities(
                "Patient diagnosed with hypertension, prescribed lisinopril",
            )
            assert isinstance(entities, list)
        else:
            pytest.skip("SciSpacy service not available for integration test")

    @pytest.mark.asyncio
    async def test_phi_detection_integration(self):
        """Test integration with PHI detection system"""
        from agents.document_processor.extractors.phi_redactor import PHIRedactor

        redactor = PHIRedactor()

        # Test PHI detection
        result = await redactor.analyze_phi("Patient John Doe, DOB: 01/15/1980")

        assert isinstance(result, PHIDetectionResult)
        # PHI detection should work even with basic patterns
        assert isinstance(result.phi_detected, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
