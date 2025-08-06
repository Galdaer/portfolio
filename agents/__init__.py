"""
Base classes for Intelluxe AI Healthcare Agents

Provides common functionality for all healthcare AI agents including
logging, memory management, database connectivity, and safety boundaries.
"""

import logging
import uuid
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from core.dependencies import get_database_connection, DatabaseConnectionError
from core.infrastructure.healthcare_logger import get_healthcare_logger, log_healthcare_event
from core.infrastructure.phi_monitor import sanitize_healthcare_data
from core.memory import memory_manager
from core.models import model_registry
from core.tools import tool_registry

logger = get_healthcare_logger("agents")


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
        self.logger = get_healthcare_logger(f"agent.{agent_name}")
        self._session_id: str | None = None
        self._db_connection: Any = None

        # Register agent with performance tracking
        self._performance_metrics: dict[str, Any] = {}

        # Log agent creation with healthcare context
        log_healthcare_event(
            self.logger,
            logging.INFO,
            f"Healthcare agent created: {agent_name}",
            context={
                "agent_name": agent_name,
                "agent_type": agent_type,
                "healthcare_compliance": True,
                "phi_protection": True,
                "database_required": True,
            },
            operation_type="agent_creation",
        )

    async def initialize_agent(self) -> None:
        """Initialize agent with model and tool registries and database connectivity"""
        try:
            # CRITICAL: Validate database connectivity first
            await self._validate_database_connectivity()
            
            # Initialize registries if needed
            if not model_registry._initialized:
                await model_registry.initialize()
            if not tool_registry._initialized:
                await tool_registry.initialize()

            self.logger.info(f"Agent {self.agent_name} initialized with database and registries")
        except DatabaseConnectionError:
            # Re-raise database connection errors with agent context
            self.logger.critical(
                f"Agent {self.agent_name} requires database connectivity for healthcare operations",
                extra={
                    "agent": self.agent_name,
                    "error_type": "database_required",
                    "setup_guidance": "Run 'make setup' to initialize database or verify DATABASE_URL environment variable."
                }
            )
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize agent {self.agent_name}: {e}")
            raise

    def _is_development_environment(self) -> bool:
        """Check if running in development environment"""
        env = os.getenv("ENVIRONMENT", "").lower()
        return env in ["development", "dev", "local"] or os.getenv("DEV_MODE", "").lower() == "true"
    
    def _is_production_environment(self) -> bool:
        """Check if running in production environment"""
        env = os.getenv("ENVIRONMENT", "").lower()
        return env in ["production", "prod"] or os.getenv("PRODUCTION", "").lower() == "true"
    
    def _is_testing_environment(self) -> bool:
        """Check if running in testing environment"""
        env = os.getenv("ENVIRONMENT", "").lower()
        return env in ["test", "testing"] or os.getenv("PYTEST_CURRENT_TEST") is not None

    async def _validate_database_connectivity(self) -> None:
        """Database-first validation with graceful fallbacks for development"""
        try:
            self._db_connection = await get_database_connection()
            
            # Test database connectivity
            await self._db_connection.execute("SELECT 1")
            
            self.logger.info(f"Database connectivity validated for agent {self.agent_name}")
        except Exception as e:
            # Database-first pattern: try database first, fallback based on environment
            if self._is_production_environment():
                # Production: database required, no fallbacks
                raise DatabaseConnectionError(
                    f"Agent {self.agent_name} requires database connectivity in production. "
                    f"Error: {e}. "
                    "Verify DATABASE_URL environment variable and database availability."
                ) from e
            elif self._is_development_environment():
                # Development: log warning but allow operation with synthetic data
                self.logger.warning(
                    f"Database unavailable for agent {self.agent_name} in development. "
                    f"Error: {e}. "
                    "Using synthetic data fallbacks. Run 'make setup' for full database functionality."
                )
                self._db_connection = None  # Signal to use fallbacks
            else:
                # Testing or unknown environment: require database for consistency
                raise DatabaseConnectionError(
                    f"Agent {self.agent_name} requires database connectivity for healthcare operations. "
                    f"Error: {e}. "
                    "Run 'make setup' to initialize database or verify DATABASE_URL environment variable."
                ) from e

    async def get_available_models(self) -> list[dict[str, Any]]:
        """Get available models from registry"""
        result = await model_registry.get_available_models()
        final_result: list[dict[str, Any]] = result if result is not None else []
        return final_result

    async def get_available_tools(self) -> list[dict[str, Any]]:
        """Get available tools from registry"""
        return await tool_registry.get_available_tools()

    def log_agent_performance(self, metrics: dict[str, Any]) -> None:
        """Log performance metrics for this agent"""
        self._performance_metrics.update(metrics)
        model_registry.log_performance(f"agent_{self.agent_name}", metrics)

    async def initialize_session(
        self, user_id: str, session_data: dict[str, Any] | None = None
    ) -> str:
        """Initialize a new session for the agent"""
        self._session_id = str(uuid.uuid4())

        session_info = {
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "session_data": session_data or {},
        }

        await memory_manager.store_session(self._session_id, session_info)

        self.logger.info(f"Session {self._session_id} initialized for user {user_id}")
        return self._session_id

    async def process_request(self, request: dict[str, Any]) -> dict[str, Any]:
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
                    "request_id": request_id,
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
                "agent_name": self.agent_name,
            }

            await self._log_interaction("error", request_id, error_response)
            self.logger.error(f"Request {request_id} failed: {e}")

            return error_response

    @abstractmethod
    async def _process_implementation(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Implement agent-specific processing logic

        This method should be overridden by each agent implementation.
        """
        pass

    async def _check_safety_boundaries(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Check if request violates healthcare safety boundaries

        Returns dict with "safe" boolean and optional "message"
        """
        # Basic safety checks
        request_text = str(request).lower()

        # Flag medical advice requests
        medical_advice_flags = [
            "diagnose",
            "diagnosis",
            "treatment",
            "prescribe",
            "medication",
            "surgery",
            "medical advice",
            "what should i do",
            "am i sick",
            "is this cancer",
            "should i see a doctor",
        ]

        for flag in medical_advice_flags:
            if flag in request_text:
                return {
                    "safe": False,
                    "message": "I cannot provide medical advice, diagnosis, or treatment recommendations. Please consult a healthcare professional.",
                }

        return {"safe": True}

    async def _log_interaction(
        self, interaction_type: str, request_id: str, data: dict[str, Any]
    ) -> None:
        """Log agent interaction for audit purposes with PHI protection"""
        try:
            # Sanitize data for PHI protection
            sanitized_data = sanitize_healthcare_data(data)

            log_entry = {
                "interaction_type": interaction_type,
                "request_id": request_id,
                "agent_name": self.agent_name,
                "agent_type": self.agent_type,
                "session_id": self._session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": sanitized_data,
            }

            # Log with healthcare context
            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Agent interaction logged: {interaction_type}",
                context=log_entry,
                operation_type="agent_interaction",
            )

            # Store in session cache for immediate access
            if self._session_id:
                session_data = await memory_manager.get_session(self._session_id) or {}
                interactions = session_data.get("interactions", [])
                interactions.append(log_entry)
                session_data["interactions"] = interactions[-50:]  # Keep last 50 interactions
                await memory_manager.store_session(self._session_id, session_data)

        except Exception as e:
            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Failed to log agent interaction: {e}",
                context={"error": str(e), "interaction_type": interaction_type},
                operation_type="logging_error",
            )

    def _sanitize_for_logging(self, data: dict[str, Any]) -> dict[str, Any]:
        """Remove or redact sensitive information for logging - DEPRECATED: Use phi_monitor instead"""
        # Use the new PHI monitor for sanitization
        return sanitize_healthcare_data(data)


class DocumentProcessingAgent(BaseHealthcareAgent):
    """Template for document processing agent"""

    def __init__(self) -> None:
        super().__init__("document_processor", "document_processing")

    async def _process_implementation(self, request: dict[str, Any]) -> dict[str, Any]:
        """Process document-related requests"""
        # Template implementation - will be enhanced in Phase 1
        return {
            "success": True,
            "message": "Document processing agent is ready for Phase 1 implementation",
            "capabilities": [
                "form_extraction",
                "document_classification",
                "pii_redaction",
                "content_organization",
            ],
        }


class ResearchAssistantAgent(BaseHealthcareAgent):
    """Template for research assistant agent"""

    def __init__(self) -> None:
        super().__init__("research_assistant", "research")

    async def _process_implementation(self, request: dict[str, Any]) -> dict[str, Any]:
        """Process research-related requests"""
        # Template implementation - will be enhanced in Phase 1
        return {
            "success": True,
            "message": "Research assistant agent is ready for Phase 1 implementation",
            "capabilities": [
                "pubmed_search",
                "fda_lookup",
                "clinical_trials_search",
                "citation_management",
            ],
        }


# Global agent instances (for templates)
document_agent = DocumentProcessingAgent()
research_agent = ResearchAssistantAgent()
