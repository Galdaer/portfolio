"""
Base classes for Intelluxe AI Healthcare Agents

Provides common functionality for all healthcare AI agents including
logging, memory management, and safety boundaries.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from core.memory import memory_manager
from core.models import model_registry
from core.tools import tool_registry

logger = logging.getLogger(__name__)


class BaseHealthcareAgent(ABC):
    """
    Base class for all healthcare AI agents
    
    Provides common functionality while enforcing safety boundaries:
    - NO medical advice, diagnosis, or treatment recommendations
    - Focus ONLY on administrative and documentation support
    - All interactions logged for compliance
    """
    
    def __init__(self, agent_name: str, agent_type: str):
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.logger = logging.getLogger(f"agents.{agent_name}")
        self._session_id: Optional[str] = None
    
    async def initialize_session(self, user_id: str, session_data: Optional[Dict[str, Any]] = None) -> str:
        """Initialize a new session for the agent"""
        self._session_id = str(uuid.uuid4())
        
        session_info = {
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "session_data": session_data or {}
        }
        
        await memory_manager.store_session(self._session_id, session_info)
        
        self.logger.info(f"Session {self._session_id} initialized for user {user_id}")
        return self._session_id
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a request with safety checks and logging
        
        All agent implementations must use this method to ensure:
        - Proper logging and audit trails
        - Safety boundary enforcement
        - Consistent response format
        """
        request_id = str(uuid.uuid4())
        
        try:
            # Log the request (with PII protection)
            await self._log_interaction("request", request_id, request)
            
            # Check safety boundaries
            safety_check = await self._check_safety_boundaries(request)
            if not safety_check["safe"]:
                response = {
                    "success": False,
                    "error": "Safety boundary violation",
                    "message": safety_check["message"],
                    "request_id": request_id
                }
                await self._log_interaction("safety_violation", request_id, response)
                return response
            
            # Process the request
            response = await self._process_implementation(request)
            response["request_id"] = request_id
            response["agent_name"] = self.agent_name
            
            # Log the response
            await self._log_interaction("response", request_id, response)
            
            return response
            
        except Exception as e:
            error_response = {
                "success": False,
                "error": str(e),
                "request_id": request_id,
                "agent_name": self.agent_name
            }
            
            await self._log_interaction("error", request_id, error_response)
            self.logger.error(f"Request {request_id} failed: {e}")
            
            return error_response
    
    @abstractmethod
    async def _process_implementation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement agent-specific processing logic
        
        This method should be overridden by each agent implementation.
        """
        pass
    
    async def _check_safety_boundaries(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if request violates healthcare safety boundaries
        
        Returns dict with "safe" boolean and optional "message"
        """
        # Basic safety checks
        request_text = str(request).lower()
        
        # Flag medical advice requests
        medical_advice_flags = [
            "diagnose", "diagnosis", "treatment", "prescribe", "medication",
            "surgery", "medical advice", "what should i do", "am i sick",
            "is this cancer", "should i see a doctor"
        ]
        
        for flag in medical_advice_flags:
            if flag in request_text:
                return {
                    "safe": False,
                    "message": "I cannot provide medical advice, diagnosis, or treatment recommendations. Please consult a healthcare professional."
                }
        
        return {"safe": True}
    
    async def _log_interaction(self, interaction_type: str, request_id: str, data: Dict[str, Any]) -> None:
        """Log agent interaction for audit purposes"""
        try:
            log_entry = {
                "interaction_type": interaction_type,
                "request_id": request_id,
                "agent_name": self.agent_name,
                "agent_type": self.agent_type,
                "session_id": self._session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": self._sanitize_for_logging(data)
            }
            
            # Store in session cache for immediate access
            if self._session_id:
                session_data = await memory_manager.get_session(self._session_id) or {}
                interactions = session_data.get("interactions", [])
                interactions.append(log_entry)
                session_data["interactions"] = interactions[-50:]  # Keep last 50 interactions
                await memory_manager.store_session(self._session_id, session_data)
            
        except Exception as e:
            self.logger.error(f"Failed to log interaction: {e}")
    
    def _sanitize_for_logging(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove or redact sensitive information for logging"""
        # Basic PII redaction - this would be enhanced in production
        import re
        sanitized = {}
        pii_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b\d{3}-\d{3}-\d{4}\b",  # Phone
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b\d{1,2}/\d{1,2}/\d{4}\b",  # DOB
            r"\bMRN\s*:?\s*\d+\b"  # Medical Record Number
        ]
        for key, value in data.items():
            if isinstance(value, str):
                redacted = value
                for pattern in pii_patterns:
                    redacted = re.sub(pattern, "[REDACTED]", redacted)
                sanitized[key] = redacted
            else:
                sanitized[key] = value
        return sanitized


class DocumentProcessingAgent(BaseHealthcareAgent):
    """Template for document processing agent"""
    
    def __init__(self):
        super().__init__("document_processor", "document_processing")
    
    async def _process_implementation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process document-related requests"""
        # Template implementation - will be enhanced in Phase 1
        return {
            "success": True,
            "message": "Document processing agent is ready for Phase 1 implementation",
            "capabilities": [
                "form_extraction",
                "document_classification",
                "pii_redaction",
                "content_organization"
            ]
        }


class ResearchAssistantAgent(BaseHealthcareAgent):
    """Template for research assistant agent"""
    
    def __init__(self):
        super().__init__("research_assistant", "research")
    
    async def _process_implementation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process research-related requests"""
        # Template implementation - will be enhanced in Phase 1
        return {
            "success": True,
            "message": "Research assistant agent is ready for Phase 1 implementation",
            "capabilities": [
                "pubmed_search",
                "fda_lookup",
                "clinical_trials_search",
                "citation_management"
            ]
        }


# Global agent instances (for templates)
document_agent = DocumentProcessingAgent()
research_agent = ResearchAssistantAgent()
