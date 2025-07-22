"""
Secure Healthcare MCP Server
FastMCP-based server with security hardening, PHI detection, and audit logging
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import psycopg2
import redis
import requests
import jwt

from ..security.environment_detector import EnvironmentDetector
from pydantic import BaseModel, Field

from .phi_detection import PHIDetector
from .audit_logger import HealthcareAuditLogger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/healthcare_mcp.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Security configuration
security = HTTPBearer()

class HealthcareConfig:
    """Healthcare MCP server configuration"""
    
    def __init__(self):
        # Security settings
        self.security_mode = os.getenv("MCP_SECURITY_MODE", "healthcare")
        self.phi_detection_enabled = os.getenv("PHI_DETECTION_ENABLED", "true").lower() == "true"
        self.audit_logging_level = os.getenv("AUDIT_LOGGING_LEVEL", "comprehensive")
        self.hipaa_compliance_mode = os.getenv("HIPAA_COMPLIANCE_MODE", "strict").lower() == "strict"
        
        # Database connections
        self.postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        self.postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.postgres_db = os.getenv("POSTGRES_DB", "intelluxe")
        self.postgres_user = os.getenv("POSTGRES_USER", "intelluxe")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", "intelluxe")
        
        # Redis connection
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        
        # Ollama connection
        self.ollama_host = os.getenv("OLLAMA_HOST", "localhost")
        self.ollama_port = int(os.getenv("OLLAMA_PORT", "11434"))
        
        # Server settings
        self.server_host = "0.0.0.0"
        self.server_port = 8000

class MCPRequest(BaseModel):
    """MCP request model"""
    method: str = Field(..., description="MCP method name")
    params: Dict[str, Any] = Field(default_factory=dict, description="Method parameters")
    id: Optional[str] = Field(None, description="Request ID")

class MCPResponse(BaseModel):
    """MCP response model"""
    result: Optional[Dict[str, Any]] = Field(None, description="Method result")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information")
    id: Optional[str] = Field(None, description="Request ID")

class HealthcareMCPServer:
    """Secure Healthcare MCP Server with PHI protection and audit logging"""
    
    def __init__(self, config: HealthcareConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.HealthcareMCPServer")

        # Rate limiting for development warnings
        self._dev_auth_warning_logged = False

        # Initialize security components
        self.phi_detector = PHIDetector() if config.phi_detection_enabled else None
        self.audit_logger = HealthcareAuditLogger(config)

        # Validate configuration at startup
        self._validate_startup_configuration()

        # Initialize connections
        self._init_database_connections()
        self._init_app()

    def _validate_startup_configuration(self):
        """Validate critical configuration at startup to prevent runtime failures"""
        from .environment_detector import EnvironmentDetector

        # First validate environment configuration
        environment = self._validate_environment_config()

        if EnvironmentDetector.is_production():
            # Validate JWT_SECRET configuration in production
            jwt_secret = os.getenv("JWT_SECRET")
            if not jwt_secret:
                self.logger.error("JWT_SECRET not configured for production environment")
                raise RuntimeError(
                    "JWT_SECRET must be configured for production deployment. "
                    "Application cannot start without proper authentication configuration."
                )

            if len(jwt_secret) < 32:
                self.logger.error("JWT_SECRET is too short for production use")
                raise RuntimeError(
                    "JWT_SECRET must be at least 32 characters for production security. "
                    "Please configure a stronger secret."
                )

            self.logger.info("Production authentication configuration validated")
        else:
            self.logger.info(f"{environment} environment - JWT_SECRET validation skipped")

    def _validate_environment_config(self):
        """
        Validate environment configuration at startup

        Validates that ENVIRONMENT variable is properly set and prevents
        unexpected authentication behavior from misconfiguration.

        Returns:
            str: Validated environment name

        Raises:
            RuntimeError: If environment configuration is invalid
        """
        environment = os.getenv('ENVIRONMENT')
        valid_environments = {"production", "development", "testing", "staging"}

        if not environment:
            self.logger.error("ENVIRONMENT variable not set")
            raise RuntimeError(
                "Server misconfiguration: ENVIRONMENT variable required. "
                "Set ENVIRONMENT to one of: production, development, testing, staging"
            )

        # Normalize to lowercase for comparison
        environment_lower = environment.lower()

        if environment_lower not in valid_environments:
            self.logger.error(f"Invalid ENVIRONMENT value: {environment}")
            raise RuntimeError(
                f"Server misconfiguration: invalid environment '{environment}'. "
                f"Valid values are: {', '.join(sorted(valid_environments))}"
            )

        # Log validated environment
        self.logger.info(f"Environment validated: {environment_lower}")

        # Additional validation for production environment
        if environment_lower == "production":
            self._validate_production_environment_requirements()

        return environment_lower

    def _validate_production_environment_requirements(self):
        """
        Validate additional requirements for production environment

        Ensures all critical configuration is present for production deployment.
        """
        # Check for development-only configurations that should not be in production
        dev_only_vars = [
            'PERSIST_DEV_KEYS',
            'RBAC_DEFAULT_PATIENT_ACCESS',
            'DEBUG',
            'DEVELOPMENT_MODE'
        ]

        for var in dev_only_vars:
            if os.getenv(var):
                self.logger.warning(f"Development configuration {var} found in production environment")

        # Validate required production configurations
        required_prod_vars = [
            'JWT_SECRET',
            'MCP_ENCRYPTION_KEY'
        ]

        missing_vars = []
        for var in required_prod_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            self.logger.error(f"Missing required production configuration: {', '.join(missing_vars)}")
            raise RuntimeError(
                f"Production deployment requires: {', '.join(missing_vars)}. "
                "Please configure all required variables before starting in production."
            )

        self.logger.info("Production environment requirements validated")

    def _init_database_connections(self):
        """Initialize database connections"""
        try:
            # PostgreSQL connection
            self.postgres_conn = psycopg2.connect(
                host=self.config.postgres_host,
                port=self.config.postgres_port,
                database=self.config.postgres_db,
                user=self.config.postgres_user,
                password=self.config.postgres_password
            )
            
            # Redis connection
            self.redis_conn = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                decode_responses=True
            )
            
            self.logger.info("Database connections initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database connections: {e}")
            raise
    
    def _init_app(self):
        """Initialize FastAPI application"""
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            self.logger.info("Healthcare MCP Server starting up")
            yield
            # Shutdown
            self.logger.info("Healthcare MCP Server shutting down")
            self._cleanup()
        
        self.app = FastAPI(
            title="Healthcare MCP Server",
            description="Secure healthcare MCP server with PHI protection and audit logging",
            version="1.0.0",
            lifespan=lifespan
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:*"],  # Restrict to localhost
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
        
        # Add security middleware
        @self.app.middleware("http")
        async def security_middleware(request: Request, call_next):
            # Log all requests for audit trail
            start_time = datetime.now()
            
            # Process request
            response = await call_next(request)
            
            # Log response for audit trail
            processing_time = (datetime.now() - start_time).total_seconds()
            await self.audit_logger.log_request(request, response, processing_time)
            
            return response
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self):
        """Register API routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "security_mode": self.config.security_mode,
                "phi_detection": self.config.phi_detection_enabled,
                "hipaa_compliance": self.config.hipaa_compliance_mode
            }
        
        @self.app.post("/mcp", response_model=MCPResponse)
        async def mcp_endpoint(
            request: MCPRequest,
            credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            """Main MCP endpoint with security validation"""
            
            # Validate authentication (basic implementation)
            if not self._validate_credentials(credentials):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            # Process MCP request
            try:
                result = await self._process_mcp_request(request)
                return MCPResponse(result=result, id=request.id)
                
            except Exception as e:
                self.logger.error(f"MCP request processing failed: {e}")
                error = {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e) if not self.config.hipaa_compliance_mode else "Processing error"
                }
                return MCPResponse(error=error, id=request.id)
        
        @self.app.get("/tools")
        async def list_tools(credentials: HTTPAuthorizationCredentials = Depends(security)):
            """List available healthcare tools"""
            
            if not self._validate_credentials(credentials):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            return {
                "tools": [
                    {
                        "name": "patient_lookup",
                        "description": "Look up patient information (synthetic data only)",
                        "parameters": {
                            "patient_id": {"type": "string", "description": "Patient identifier"}
                        }
                    },
                    {
                        "name": "medical_research",
                        "description": "Research medical information",
                        "parameters": {
                            "query": {"type": "string", "description": "Medical research query"}
                        }
                    },
                    {
                        "name": "drug_interaction_check",
                        "description": "Check for drug interactions",
                        "parameters": {
                            "medications": {"type": "array", "description": "List of medications"}
                        }
                    }
                ]
            }
    
    def _validate_credentials(self, credentials: HTTPAuthorizationCredentials) -> bool:
        """Validate authentication credentials with secure environment detection and failure logging"""
        token = credentials.credentials
        auth_result = False

        if EnvironmentDetector.is_production():
            auth_result = self._validate_jwt_token(token)
        elif EnvironmentDetector.is_development():
            # Development mode - basic validation with rate-limited warning
            if len(token) > 0:
                if not self._dev_auth_warning_logged:
                    self.logger.warning("Using basic token validation - NOT SUITABLE FOR PRODUCTION")
                    self._dev_auth_warning_logged = True
                auth_result = True
            else:
                auth_result = False
        else:
            # Testing/staging - use JWT validation for security
            auth_result = self._validate_jwt_token(token)

        # Log authentication failures for security monitoring
        if not auth_result:
            # Extract client info for security logging (without exposing sensitive data)
            token_preview = token[:8] + "..." if len(token) > 8 else "empty"
            self.logger.warning(
                f"Authentication failed - Token preview: {token_preview}, "
                f"Environment: {os.getenv('ENVIRONMENT', 'unknown')}"
            )

            # TODO: Add rate limiting and IP blocking for repeated failures
            # TODO: Integrate with security monitoring system

        return auth_result

    def _validate_jwt_token(self, token: str) -> bool:
        """
        Validate JWT token for production use with graceful error handling

        Note: JWT_SECRET validation is performed at startup to prevent runtime failures.
        This method provides graceful fallback for authentication failures.
        """
        try:
            # Get JWT secret from environment or config
            jwt_secret = os.getenv("JWT_SECRET")
            if not jwt_secret:
                # This should not happen if startup validation passed
                self.logger.error("JWT_SECRET not available during authentication - configuration error")
                return False

            # Decode and validate JWT
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                options={"require_exp": True}
            )

            # Additional validation
            if payload.get("iss") != "intelluxe-healthcare":
                self.logger.warning("Invalid JWT issuer")
                return False

            # Check user permissions
            user_id = payload.get("sub")
            if not user_id:
                self.logger.warning("JWT missing user ID")
                return False

            self.logger.info(f"JWT validation successful for user {user_id}")
            return True

        except jwt.ExpiredSignatureError:
            self.logger.warning("JWT token expired - authentication failed")
            return False
        except jwt.InvalidTokenError as e:
            self.logger.warning(f"Invalid JWT token - authentication failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"JWT validation error - authentication failed: {e}")
            return False
    
    async def _process_mcp_request(self, request: MCPRequest) -> Dict[str, Any]:
        """Process MCP request with PHI detection and security"""
        
        # Check for PHI in request
        if self.phi_detector:
            phi_detected = await self.phi_detector.detect_phi(json.dumps(request.params))
            if phi_detected:
                await self.audit_logger.log_phi_detection(request, phi_detected)
                if self.config.hipaa_compliance_mode:
                    raise HTTPException(status_code=400, detail="PHI detected in request")
        
        # Route to appropriate handler
        method = request.method
        params = request.params
        
        if method == "patient_lookup":
            return await self._handle_patient_lookup(params)
        elif method == "medical_research":
            return await self._handle_medical_research(params)
        elif method == "drug_interaction_check":
            return await self._handle_drug_interaction_check(params)
        else:
            raise ValueError(f"Unknown method: {method}")
    
    async def _handle_patient_lookup(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle patient lookup (synthetic data only)"""
        patient_id = params.get("patient_id")
        
        if not patient_id:
            raise ValueError("patient_id is required")
        
        # Only return synthetic data
        return {
            "patient_id": patient_id,
            "data_type": "synthetic",
            "message": "Patient lookup completed with synthetic data only",
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_medical_research(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle medical research query"""
        query = params.get("query")
        
        if not query:
            raise ValueError("query is required")
        
        # Use Ollama for medical research
        try:
            ollama_url = f"http://{self.config.ollama_host}:{self.config.ollama_port}"
            
            prompt = f"""
            You are a medical research assistant. Provide evidence-based information about: {query}
            
            Focus on:
            1. Current medical understanding
            2. Evidence-based treatments
            3. Clinical guidelines
            4. Safety considerations
            
            Provide accurate, general medical information only.
            """
            
            payload = {
                "model": "llama3.1:8b-instruct-q4_K_M",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            }
            
            response = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            research_response = result.get("response", "No response generated")
            
            return {
                "query": query,
                "research_result": research_response,
                "source": "ollama_llama3.1",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Medical research failed: {e}")
            raise ValueError(f"Research query failed: {str(e)}")
    
    async def _handle_drug_interaction_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle drug interaction check"""
        medications = params.get("medications", [])
        
        if not medications:
            raise ValueError("medications list is required")
        
        # Basic drug interaction check (would be enhanced with real database)
        return {
            "medications": medications,
            "interactions_found": [],
            "message": "Drug interaction check completed (basic implementation)",
            "timestamp": datetime.now().isoformat()
        }
    
    def _cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'postgres_conn'):
            self.postgres_conn.close()
        if hasattr(self, 'redis_conn'):
            self.redis_conn.close()
    
    async def start_server(self):
        """Start the MCP server"""
        config = uvicorn.Config(
            self.app,
            host=self.config.server_host,
            port=self.config.server_port,
            log_level="info",
            access_log=True
        )
        
        server = uvicorn.Server(config)
        await server.serve()

# Main entry point
async def main():
    """Main entry point for the healthcare MCP server"""
    config = HealthcareConfig()
    server = HealthcareMCPServer(config)
    
    logger.info(f"Starting Healthcare MCP Server on {config.server_host}:{config.server_port}")
    logger.info(f"Security mode: {config.security_mode}")
    logger.info(f"PHI detection: {config.phi_detection_enabled}")
    logger.info(f"HIPAA compliance: {config.hipaa_compliance_mode}")
    
    await server.start_server()

if __name__ == "__main__":
    asyncio.run(main())
