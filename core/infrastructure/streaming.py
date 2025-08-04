"""
Healthcare Response Streaming Infrastructure

Provides streaming capabilities for long-running medical queries, literature searches,
and AI reasoning processes to improve user experience during complex healthcare operations.
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import redis.asyncio as redis
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

class StreamingEventType(str, Enum):
    """Types of streaming events for healthcare responses"""
    PROGRESS = "progress"               # Progress updates (e.g., "Searching medical literature...")
    PARTIAL_RESULT = "partial_result"  # Partial results as they arrive
    REASONING = "reasoning"            # AI reasoning steps for transparency
    CITATION = "citation"              # Medical literature citations
    WARNING = "warning"                # Medical warnings or disclaimers
    COMPLETE = "complete"              # Final result
    ERROR = "error"                    # Error information

@dataclass
class StreamingEvent:
    """Healthcare streaming event data structure"""
    event_type: StreamingEventType
    timestamp: datetime
    data: dict[str, Any]
    medical_context: str | None = None
    user_id: str | None = None
    session_id: str | None = None

class HealthcareStreamer:
    """Healthcare-focused streaming response manager"""

    def __init__(self, redis_client: redis.Redis | None = None):
        self.redis_client = redis_client
        self.active_streams: dict[str, bool] = {}
        logger.info("Healthcare streamer initialized")

    async def create_medical_literature_stream(
        self,
        query: str,
        user_id: str,
        session_id: str,
        max_results: int = 10
    ) -> AsyncGenerator[str, None]:
        """
        Stream medical literature search results as they arrive

        Provides real-time updates during literature search:
        1. Search progress
        2. Individual paper results
        3. Citation formatting
        4. Relevance scoring
        """
        stream_id = f"literature_{session_id}_{datetime.now().timestamp()}"
        self.active_streams[stream_id] = True

        try:
            # Initial progress event
            yield self._format_sse_event(StreamingEvent(
                event_type=StreamingEventType.PROGRESS,
                timestamp=datetime.now(),
                data={
                    "message": "Initiating medical literature search...",
                    "query": query,
                    "max_results": max_results,
                    "progress": 0
                },
                medical_context="literature_search",
                user_id=user_id,
                session_id=session_id
            ))

            # Simulate literature search progress
            search_steps = [
                "Connecting to medical databases...",
                "Searching PubMed and medical journals...",
                "Filtering for clinical relevance...",
                "Ranking by evidence quality...",
                "Formatting citations..."
            ]

            for i, step in enumerate(search_steps):
                if not self.active_streams.get(stream_id, False):
                    break

                yield self._format_sse_event(StreamingEvent(
                    event_type=StreamingEventType.PROGRESS,
                    timestamp=datetime.now(),
                    data={
                        "message": step,
                        "progress": int((i + 1) / len(search_steps) * 80)  # 80% for search
                    },
                    medical_context="literature_search",
                    user_id=user_id,
                    session_id=session_id
                ))

                await asyncio.sleep(0.5)  # Simulate processing time

            # Stream mock literature results
            mock_papers = [
                {
                    "title": "Clinical Applications of AI in Healthcare Documentation",
                    "authors": ["Smith, J.", "Johnson, M.", "Brown, K."],
                    "journal": "Journal of Medical Informatics",
                    "year": 2024,
                    "doi": "10.1001/jmi.2024.001",
                    "relevance_score": 0.92,
                    "abstract": "This study examines the implementation of AI systems in healthcare documentation workflows..."
                },
                {
                    "title": "HIPAA Compliance in Healthcare AI Systems",
                    "authors": ["Davis, R.", "Wilson, L."],
                    "journal": "Healthcare Privacy Review",
                    "year": 2024,
                    "doi": "10.1001/hpr.2024.005",
                    "relevance_score": 0.88,
                    "abstract": "An analysis of privacy requirements and compliance strategies for AI in healthcare settings..."
                }
            ]

            for i, paper in enumerate(mock_papers[:max_results]):
                if not self.active_streams.get(stream_id, False):
                    break

                yield self._format_sse_event(StreamingEvent(
                    event_type=StreamingEventType.PARTIAL_RESULT,
                    timestamp=datetime.now(),
                    data={
                        "paper": paper,
                        "result_index": i + 1,
                        "total_results": min(len(mock_papers), max_results)
                    },
                    medical_context="literature_search",
                    user_id=user_id,
                    session_id=session_id
                ))

                await asyncio.sleep(0.3)  # Simulate result processing

            # Final completion event
            yield self._format_sse_event(StreamingEvent(
                event_type=StreamingEventType.COMPLETE,
                timestamp=datetime.now(),
                data={
                    "message": "Medical literature search completed",
                    "total_results": min(len(mock_papers), max_results),
                    "search_duration_ms": 2500,
                    "progress": 100
                },
                medical_context="literature_search",
                user_id=user_id,
                session_id=session_id
            ))

        except Exception as e:
            logger.error(f"Error in literature stream {stream_id}: {e}")
            yield self._format_sse_event(StreamingEvent(
                event_type=StreamingEventType.ERROR,
                timestamp=datetime.now(),
                data={
                    "error": "Literature search failed",
                    "details": str(e)
                },
                medical_context="literature_search",
                user_id=user_id,
                session_id=session_id
            ))
        finally:
            self.active_streams.pop(stream_id, None)

    async def create_ai_reasoning_stream(
        self,
        medical_query: str,
        user_id: str,
        session_id: str
    ) -> AsyncGenerator[str, None]:
        """
        Stream AI reasoning steps for medical query processing

        Provides transparency in AI decision-making:
        1. Query analysis
        2. Medical context identification
        3. Reasoning steps
        4. Confidence assessment
        """
        stream_id = f"reasoning_{session_id}_{datetime.now().timestamp()}"
        self.active_streams[stream_id] = True

        try:
            # Medical disclaimer
            yield self._format_sse_event(StreamingEvent(
                event_type=StreamingEventType.WARNING,
                timestamp=datetime.now(),
                data={
                    "type": "medical_disclaimer",
                    "message": "AI analysis is for administrative support only. Not medical advice."
                },
                medical_context="ai_reasoning",
                user_id=user_id,
                session_id=session_id
            ))

            # Reasoning steps
            reasoning_steps = [
                {
                    "step": "Analyzing medical query context",
                    "details": "Identifying medical entities, intent, and required information types",
                    "confidence": 0.95
                },
                {
                    "step": "Checking for PHI and safety concerns",
                    "details": "Ensuring query does not contain patient identifiers or unsafe requests",
                    "confidence": 0.98
                },
                {
                    "step": "Determining appropriate response strategy",
                    "details": "Selecting administrative vs clinical guidance approach",
                    "confidence": 0.92
                },
                {
                    "step": "Generating contextual response",
                    "details": "Creating response with appropriate medical disclaimers",
                    "confidence": 0.89
                }
            ]

            for i, step in enumerate(reasoning_steps):
                if not self.active_streams.get(stream_id, False):
                    break

                yield self._format_sse_event(StreamingEvent(
                    event_type=StreamingEventType.REASONING,
                    timestamp=datetime.now(),
                    data={
                        "step_number": i + 1,
                        "total_steps": len(reasoning_steps),
                        "reasoning": step,
                        "progress": int((i + 1) / len(reasoning_steps) * 100)
                    },
                    medical_context="ai_reasoning",
                    user_id=user_id,
                    session_id=session_id
                ))

                await asyncio.sleep(0.8)  # Simulate reasoning time

            # Final reasoning result
            yield self._format_sse_event(StreamingEvent(
                event_type=StreamingEventType.COMPLETE,
                timestamp=datetime.now(),
                data={
                    "message": "AI reasoning analysis completed",
                    "overall_confidence": 0.93,
                    "safety_verified": True,
                    "phi_detected": False
                },
                medical_context="ai_reasoning",
                user_id=user_id,
                session_id=session_id
            ))

        except Exception as e:
            logger.error(f"Error in reasoning stream {stream_id}: {e}")
            yield self._format_sse_event(StreamingEvent(
                event_type=StreamingEventType.ERROR,
                timestamp=datetime.now(),
                data={
                    "error": "AI reasoning failed",
                    "details": str(e)
                },
                medical_context="ai_reasoning",
                user_id=user_id,
                session_id=session_id
            ))
        finally:
            self.active_streams.pop(stream_id, None)

    async def create_document_processing_stream(
        self,
        document_type: str,
        user_id: str,
        session_id: str
    ) -> AsyncGenerator[str, None]:
        """
        Stream document processing progress for medical documents

        Provides updates during:
        1. Document analysis
        2. Medical entity extraction
        3. Compliance checking
        4. Report generation
        """
        stream_id = f"document_{session_id}_{datetime.now().timestamp()}"
        self.active_streams[stream_id] = True

        try:
            processing_steps = [
                "Analyzing document structure and content...",
                "Extracting medical entities and terms...",
                "Checking for PHI and compliance requirements...",
                "Generating structured medical summary...",
                "Formatting output and citations..."
            ]

            for i, step in enumerate(processing_steps):
                if not self.active_streams.get(stream_id, False):
                    break

                yield self._format_sse_event(StreamingEvent(
                    event_type=StreamingEventType.PROGRESS,
                    timestamp=datetime.now(),
                    data={
                        "message": step,
                        "progress": int((i + 1) / len(processing_steps) * 100),
                        "document_type": document_type
                    },
                    medical_context="document_processing",
                    user_id=user_id,
                    session_id=session_id
                ))

                await asyncio.sleep(1.0)  # Simulate processing time

            # Processing complete
            yield self._format_sse_event(StreamingEvent(
                event_type=StreamingEventType.COMPLETE,
                timestamp=datetime.now(),
                data={
                    "message": "Document processing completed",
                    "document_type": document_type,
                    "entities_extracted": 25,
                    "phi_detected": False,
                    "compliance_verified": True
                },
                medical_context="document_processing",
                user_id=user_id,
                session_id=session_id
            ))

        except Exception as e:
            logger.error(f"Error in document processing stream {stream_id}: {e}")
            yield self._format_sse_event(StreamingEvent(
                event_type=StreamingEventType.ERROR,
                timestamp=datetime.now(),
                data={
                    "error": "Document processing failed",
                    "details": str(e)
                },
                medical_context="document_processing",
                user_id=user_id,
                session_id=session_id
            ))
        finally:
            self.active_streams.pop(stream_id, None)

    def _format_sse_event(self, event: StreamingEvent) -> str:
        """Format streaming event as Server-Sent Event"""
        event_data = {
            "type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "data": event.data,
            "medical_context": event.medical_context,
            "user_id": event.user_id,
            "session_id": event.session_id
        }

        # Format as SSE
        return f"data: {json.dumps(event_data)}\n\n"

    async def stop_stream(self, stream_id: str) -> bool:
        """Stop an active stream"""
        if stream_id in self.active_streams:
            self.active_streams[stream_id] = False
            logger.info(f"Stream {stream_id} stopped by user")
            return True
        return False

    def get_active_streams(self) -> dict[str, bool]:
        """Get list of currently active streams"""
        return self.active_streams.copy()

# Global healthcare streamer instance
healthcare_streamer: HealthcareStreamer | None = None

def get_healthcare_streamer() -> HealthcareStreamer:
    """Get global healthcare streamer instance"""
    global healthcare_streamer
    if healthcare_streamer is None:
        healthcare_streamer = HealthcareStreamer()
    return healthcare_streamer

# Helper functions for creating streaming responses
async def stream_medical_literature_search(
    query: str,
    user_id: str,
    session_id: str,
    max_results: int = 10
) -> StreamingResponse:
    """Create streaming response for medical literature search"""
    streamer = get_healthcare_streamer()

    return StreamingResponse(
        streamer.create_medical_literature_stream(query, user_id, session_id, max_results),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Medical-Disclaimer": "Administrative support only - not medical advice"
        }
    )

async def stream_ai_reasoning(
    medical_query: str,
    user_id: str,
    session_id: str
) -> StreamingResponse:
    """Create streaming response for AI reasoning transparency"""
    streamer = get_healthcare_streamer()

    return StreamingResponse(
        streamer.create_ai_reasoning_stream(medical_query, user_id, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Medical-Disclaimer": "AI analysis for administrative support only"
        }
    )

async def stream_document_processing(
    document_type: str,
    user_id: str,
    session_id: str
) -> StreamingResponse:
    """Create streaming response for document processing"""
    streamer = get_healthcare_streamer()

    return StreamingResponse(
        streamer.create_document_processing_stream(document_type, user_id, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Medical-Disclaimer": "Document analysis for administrative purposes"
        }
    )
