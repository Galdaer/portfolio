# Healthcare API Development Instructions

## Purpose

Comprehensive API development patterns for healthcare systems, covering FastAPI implementation, PHI-safe endpoints, HIPAA-compliant authentication, medical data validation, and healthcare-specific API security patterns.

## FastAPI Healthcare Foundation

### 1. Healthcare FastAPI Application Structure

```python
# ✅ CORRECT: Healthcare FastAPI Application with Compliance
from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
import asyncio
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

# Healthcare-specific imports
from core.dependencies import get_healthcare_services
from core.models.healthcare_models import PatientData, ProviderData, EncounterData
from config.healthcare_security import HIPAASecurityConfig
from src.healthcare_mcp.phi_detection import PHIDetector

@asynccontextmanager
async def healthcare_lifespan(app: FastAPI):
    """Healthcare application lifespan management"""
    
    # Startup: Initialize healthcare services
    healthcare_services = await get_healthcare_services()
    await healthcare_services.initialize_all_services()
    
    # Security initialization
    security_config = HIPAASecurityConfig()
    await security_config.initialize_hipaa_controls()
    
    # PHI detection initialization
    phi_detector = PHIDetector()
    await phi_detector.load_healthcare_patterns()
    
    print("🏥 Healthcare AI System initialized with HIPAA compliance")
    
    yield
    
    # Shutdown: Cleanup healthcare resources
    await healthcare_services.cleanup_all_services()
    print("🏥 Healthcare AI System shutdown complete")

# FastAPI application with healthcare compliance
app = FastAPI(
    title="Intelluxe Healthcare AI API",
    description="""
    **MEDICAL DISCLAIMER**: This API provides healthcare administrative and research assistance tools. 
    It does not provide medical advice, diagnosis, or treatment recommendations. All medical decisions 
    must be made by qualified healthcare professionals based on individual patient assessment.
    
    Features:
    - HIPAA-compliant patient data handling
    - PHI detection and protection
    - Medical literature research assistance  
    - Healthcare workflow optimization
    - Clinical documentation support
    """,
    version="1.0.0",
    lifespan=healthcare_lifespan,
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json"
)

# Healthcare-specific middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-healthcare-domain.com"],  # Restrict to healthcare domains
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["your-healthcare-domain.com", "localhost", "127.0.0.1"]
)

# Custom healthcare middleware
@app.middleware("http")
async def healthcare_security_middleware(request: Request, call_next):
    """Healthcare-specific security middleware"""
    
    start_time = datetime.utcnow()
    
    # PHI detection in request
    phi_detector = PHIDetector()
    request_body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else ""
    
    if request_body and await phi_detector.contains_phi(request_body.decode()):
        return JSONResponse(
            status_code=400,
            content={
                "error": "PHI_DETECTED_IN_REQUEST",
                "message": "Request contains potential PHI and cannot be processed"
            }
        )
    
    response = await call_next(request)
    
    # Add healthcare compliance headers
    response.headers["X-Healthcare-Compliance"] = "HIPAA-Compliant"
    response.headers["X-PHI-Safe"] = "true"
    response.headers["X-Response-Time"] = str((datetime.utcnow() - start_time).total_seconds())
    
    return response
```

### 2. Healthcare Authentication and Authorization

```python
# ✅ CORRECT: HIPAA-Compliant Authentication System
from jose import JWTError, jwt
from passlib.context import CryptContext
from enum import Enum

class HealthcareRole(str, Enum):
    """HIPAA-compliant healthcare user roles"""
    SYSTEM_ADMIN = "system_admin"
    SECURITY_OFFICER = "security_officer"
    PRIVACY_OFFICER = "privacy_officer"
    HEALTHCARE_PROVIDER = "healthcare_provider"
    NURSE = "nurse"
    MEDICAL_ASSISTANT = "medical_assistant"
    BILLING_SPECIALIST = "billing_specialist"
    PATIENT = "patient"
    BUSINESS_ASSOCIATE = "business_associate"

class HealthcarePermission(str, Enum):
    """Granular healthcare permissions"""
    READ_PHI = "read_phi"
    WRITE_PHI = "write_phi"
    DELETE_PHI = "delete_phi"
    VIEW_PATIENT_LIST = "view_patient_list"
    SCHEDULE_APPOINTMENTS = "schedule_appointments"
    PROCESS_BILLING = "process_billing"
    GENERATE_REPORTS = "generate_reports"
    ADMIN_ACCESS = "admin_access"
    EMERGENCY_ACCESS = "emergency_access"

class HealthcareUserToken(BaseModel):
    """Healthcare user token model"""
    user_id: str
    username: str
    role: HealthcareRole
    permissions: List[HealthcarePermission]
    npi_number: Optional[str] = None  # National Provider Identifier
    facility_id: str
    session_id: str
    exp: datetime
    minimum_necessary_scope: Optional[List[str]] = None

class HealthcareAuthManager:
    """HIPAA-compliant authentication manager"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = self._get_jwt_secret()
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 15  # Short-lived for healthcare
        self.logger = get_healthcare_logger('healthcare_auth')
    
    async def authenticate_healthcare_user(
        self,
        username: str,
        password: str,
        facility_id: str,
        mfa_token: Optional[str] = None
    ) -> Optional[HealthcareUserToken]:
        """Authenticate healthcare user with MFA"""
        
        # Get user from database
        user = await self._get_user_by_username(username, facility_id)
        if not user or not self._verify_password(password, user.hashed_password):
            # Log failed authentication
            self.logger.warning(
                f"Failed authentication attempt",
                extra={
                    'operation_type': 'failed_authentication',
                    'username': username,
                    'facility_id': facility_id,
                    'ip_address': self._get_client_ip(),
                    'compliance_requirement': 'HIPAA_164.312(a)(2)(i)'
                }
            )
            return None
        
        # Verify MFA for healthcare users
        if user.role in [HealthcareRole.HEALTHCARE_PROVIDER, HealthcareRole.NURSE]:
            if not mfa_token or not await self._verify_mfa_token(user.user_id, mfa_token):
                self.logger.warning(
                    f"MFA verification failed",
                    extra={
                        'operation_type': 'mfa_verification_failed',
                        'user_id': user.user_id,
                        'username': username
                    }
                )
                return None
        
        # Create user token
        user_token = HealthcareUserToken(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            permissions=await self._get_user_permissions(user.user_id),
            npi_number=user.npi_number,
            facility_id=facility_id,
            session_id=str(uuid4()),
            exp=datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes),
            minimum_necessary_scope=await self._get_minimum_necessary_scope(user.user_id)
        )
        
        # Log successful authentication
        self.logger.info(
            f"Healthcare user authenticated",
            extra={
                'operation_type': 'successful_authentication',
                'user_id': user.user_id,
                'username': username,
                'role': user.role.value,
                'facility_id': facility_id
            }
        )
        
        return user_token
    
    def create_healthcare_access_token(self, user_token: HealthcareUserToken) -> str:
        """Create JWT access token for healthcare user"""
        
        token_data = {
            "sub": user_token.user_id,
            "username": user_token.username,
            "role": user_token.role.value,
            "permissions": [p.value for p in user_token.permissions],
            "npi_number": user_token.npi_number,
            "facility_id": user_token.facility_id,
            "session_id": user_token.session_id,
            "exp": user_token.exp,
            "minimum_necessary_scope": user_token.minimum_necessary_scope,
            "token_type": "healthcare_access"
        }
        
        return jwt.encode(token_data, self.secret_key, algorithm=self.algorithm)

# Authentication dependency
security = HTTPBearer()
auth_manager = HealthcareAuthManager()

async def get_current_healthcare_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> HealthcareUserToken:
    """Get current authenticated healthcare user"""
    
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate healthcare credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, auth_manager.secret_key, algorithms=[auth_manager.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
        # Reconstruct user token
        user_token = HealthcareUserToken(
            user_id=user_id,
            username=payload.get("username"),
            role=HealthcareRole(payload.get("role")),
            permissions=[HealthcarePermission(p) for p in payload.get("permissions", [])],
            npi_number=payload.get("npi_number"),
            facility_id=payload.get("facility_id"),
            session_id=payload.get("session_id"),
            exp=datetime.fromtimestamp(payload.get("exp")),
            minimum_necessary_scope=payload.get("minimum_necessary_scope")
        )
        
        # Verify token hasn't expired
        if user_token.exp < datetime.utcnow():
            raise credentials_exception
            
        return user_token
        
    except JWTError:
        raise credentials_exception

def require_healthcare_permission(required_permission: HealthcarePermission):
    """Decorator to require specific healthcare permission"""
    
    def permission_checker(current_user: HealthcareUserToken = Depends(get_current_healthcare_user)):
        if required_permission not in current_user.permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Healthcare permission required: {required_permission.value}"
            )
        return current_user
    
    return permission_checker
```

### 3. PHI-Safe Request/Response Models

```python
# ✅ CORRECT: PHI-Safe Pydantic Models for Healthcare APIs
from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
from enum import Enum
import re

class PHISafeBaseModel(BaseModel):
    """Base model with PHI detection and protection"""
    
    class Config:
        # Healthcare-specific serialization settings
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None
        }
        
        # Schema generation settings
        schema_extra = {
            "example": {
                "medical_disclaimer": "This API provides healthcare administrative support only and does not provide medical advice, diagnosis, or treatment recommendations."
            }
        }
    
    @root_validator
    def validate_no_phi(cls, values):
        """Validate that model doesn't contain PHI"""
        phi_detector = PHIDetector()
        
        for field_name, field_value in values.items():
            if isinstance(field_value, str) and phi_detector.contains_phi_sync(field_value):
                raise ValueError(f"Field '{field_name}' contains potential PHI")
        
        return values

class PatientIdentifierRequest(PHISafeBaseModel):
    """Request model for patient identification (PHI-safe)"""
    
    # Use medical record number instead of SSN
    medical_record_number: str = Field(
        ...,
        description="Hospital-assigned medical record number",
        regex=r"^MRN\d{6,10}$",
        example="MRN1234567"
    )
    
    # Date of birth for verification (not PHI when used for identification)
    date_of_birth: date = Field(
        ...,
        description="Patient date of birth for verification"
    )
    
    facility_id: str = Field(
        ...,
        description="Healthcare facility identifier",
        example="FACILITY_001"
    )
    
    @validator('medical_record_number')
    def validate_mrn_format(cls, v):
        """Validate medical record number format"""
        if not re.match(r'^MRN\d{6,10}$', v):
            raise ValueError('Medical record number must follow format MRN followed by 6-10 digits')
        return v

class MedicalLiteratureQuery(PHISafeBaseModel):
    """Request model for medical literature search"""
    
    search_terms: List[str] = Field(
        ...,
        description="Medical search terms (no patient-specific information)",
        example=["diabetes mellitus", "insulin resistance", "metformin"]
    )
    
    specialty_filter: Optional[str] = Field(
        None,
        description="Medical specialty filter",
        example="endocrinology"
    )
    
    publication_years: Optional[List[int]] = Field(
        None,
        description="Publication year range",
        example=[2020, 2021, 2022, 2023]
    )
    
    max_results: int = Field(
        10,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    )
    
    @validator('search_terms')
    def validate_no_patient_info(cls, v):
        """Ensure search terms don't contain patient information"""
        phi_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN pattern
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email pattern
            r'\b\d{3}-\d{3}-\d{4}\b',  # Phone pattern
        ]
        
        for term in v:
            for pattern in phi_patterns:
                if re.search(pattern, term):
                    raise ValueError(f"Search term '{term}' appears to contain personal information")
        
        return v

class DrugInteractionQuery(PHISafeBaseModel):
    """Request model for drug interaction checking"""
    
    medications: List[str] = Field(
        ...,
        description="List of medication names (generic names preferred)",
        example=["metformin", "lisinopril", "atorvastatin"]
    )
    
    check_type: str = Field(
        "all_interactions",
        description="Type of interaction check",
        regex="^(all_interactions|major_only|contraindications)$"
    )
    
    include_food_interactions: bool = Field(
        False,
        description="Include food and supplement interactions"
    )
    
    @validator('medications')
    def validate_medication_list(cls, v):
        """Validate medication list"""
        if len(v) < 2:
            raise ValueError("At least 2 medications required for interaction checking")
        if len(v) > 20:
            raise ValueError("Maximum 20 medications allowed per request")
        return v

class HealthcareDocumentationRequest(PHISafeBaseModel):
    """Request model for healthcare documentation assistance"""
    
    document_type: str = Field(
        ...,
        description="Type of healthcare document",
        regex="^(progress_note|discharge_summary|consultation|procedure_note)$"
    )
    
    template_parameters: Dict[str, Any] = Field(
        ...,
        description="Template parameters (PHI-free)"
    )
    
    specialty: Optional[str] = Field(
        None,
        description="Medical specialty context"
    )
    
    @validator('template_parameters')
    def validate_no_phi_in_parameters(cls, v):
        """Ensure template parameters don't contain PHI"""
        phi_detector = PHIDetector()
        
        for key, value in v.items():
            if isinstance(value, str) and phi_detector.contains_phi_sync(value):
                raise ValueError(f"Template parameter '{key}' contains potential PHI")
        
        return v

class HealthcareResponseBase(PHISafeBaseModel):
    """Base response model for healthcare APIs"""
    
    success: bool = Field(True, description="Response success status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    request_id: str = Field(..., description="Unique request identifier")
    
    medical_disclaimer: str = Field(
        default="This response provides healthcare administrative and research assistance only. "
                "It does not provide medical advice, diagnosis, or treatment recommendations. "
                "All medical decisions must be made by qualified healthcare professionals.",
        description="Required medical disclaimer"
    )

class MedicalLiteratureResponse(HealthcareResponseBase):
    """Response model for medical literature search"""
    
    search_results: List[Dict[str, Any]] = Field(
        ...,
        description="Medical literature search results"
    )
    
    total_results: int = Field(..., description="Total number of results found")
    search_duration_ms: int = Field(..., description="Search duration in milliseconds")
    
    sources: List[str] = Field(
        default=["PubMed", "Clinical Trials", "Medical Literature Database"],
        description="Data sources used for search"
    )

class DrugInteractionResponse(HealthcareResponseBase):
    """Response model for drug interaction checking"""
    
    interactions_found: List[Dict[str, Any]] = Field(
        ...,
        description="Drug interactions identified"
    )
    
    interaction_count: Dict[str, int] = Field(
        ...,
        description="Count of interactions by severity"
    )
    
    clinical_significance: str = Field(
        ...,
        description="Overall clinical significance assessment"
    )
```

### 4. Healthcare API Endpoints

```python
# ✅ CORRECT: Healthcare API Endpoints with Compliance
@app.get("/", response_model=Dict[str, str])
async def healthcare_api_root():
    """Healthcare API root endpoint with medical disclaimer"""
    return {
        "message": "Intelluxe Healthcare AI API",
        "version": "1.0.0",
        "medical_disclaimer": "This API provides healthcare administrative and research assistance only. "
                            "It does not provide medical advice, diagnosis, or treatment recommendations. "
                            "All medical decisions must be made by qualified healthcare professionals.",
        "compliance": "HIPAA-Compliant",
        "documentation": "/api/v1/docs"
    }

@app.post("/api/v1/medical-literature/search", response_model=MedicalLiteratureResponse)
async def search_medical_literature(
    request: MedicalLiteratureQuery,
    current_user: HealthcareUserToken = Depends(require_healthcare_permission(HealthcarePermission.READ_PHI)),
    healthcare_services = Depends(get_healthcare_services)
) -> MedicalLiteratureResponse:
    """
    Search medical literature for research assistance
    
    **Medical Disclaimer**: Provides medical literature research assistance only.
    Does not provide medical advice, diagnosis, or treatment recommendations.
    """
    
    request_id = str(uuid4())
    start_time = datetime.utcnow()
    
    try:
        # Log API request
        logger = get_healthcare_logger('medical_literature_api')
        logger.info(
            f"Medical literature search requested",
            extra={
                'operation_type': 'medical_literature_search',
                'user_id': current_user.user_id,
                'request_id': request_id,
                'search_terms_count': len(request.search_terms),
                'specialty_filter': request.specialty_filter
            }
        )
        
        # Perform search using healthcare services
        search_results = await healthcare_services.research_assistant.search_medical_literature(
            search_terms=request.search_terms,
            specialty_filter=request.specialty_filter,
            publication_years=request.publication_years,
            max_results=request.max_results
        )
        
        # Calculate search duration
        search_duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return MedicalLiteratureResponse(
            request_id=request_id,
            search_results=search_results['results'],
            total_results=search_results['total_count'],
            search_duration_ms=search_duration,
            sources=search_results['sources_used']
        )
        
    except Exception as e:
        logger.error(
            f"Medical literature search failed",
            extra={
                'operation_type': 'medical_literature_search_error',
                'user_id': current_user.user_id,
                'request_id': request_id,
                'error': str(e)
            }
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "MEDICAL_LITERATURE_SEARCH_FAILED",
                "message": "Medical literature search encountered an error",
                "request_id": request_id
            }
        )

@app.post("/api/v1/drug-interactions/check", response_model=DrugInteractionResponse)
async def check_drug_interactions(
    request: DrugInteractionQuery,
    current_user: HealthcareUserToken = Depends(require_healthcare_permission(HealthcarePermission.READ_PHI)),
    healthcare_services = Depends(get_healthcare_services)
) -> DrugInteractionResponse:
    """
    Check for drug interactions and contraindications
    
    **Medical Disclaimer**: Provides drug interaction information for reference only.
    Does not replace clinical judgment or pharmaceutical consultation.
    """
    
    request_id = str(uuid4())
    
    try:
        # Log API request
        logger = get_healthcare_logger('drug_interaction_api')
        logger.info(
            f"Drug interaction check requested",
            extra={
                'operation_type': 'drug_interaction_check',
                'user_id': current_user.user_id,
                'request_id': request_id,
                'medication_count': len(request.medications),
                'check_type': request.check_type
            }
        )
        
        # Perform drug interaction check
        interaction_results = await healthcare_services.research_assistant.check_drug_interactions(
            medications=request.medications,
            check_type=request.check_type,
            include_food_interactions=request.include_food_interactions
        )
        
        return DrugInteractionResponse(
            request_id=request_id,
            interactions_found=interaction_results['interactions'],
            interaction_count=interaction_results['interaction_count'],
            clinical_significance=interaction_results['clinical_significance']
        )
        
    except Exception as e:
        logger.error(
            f"Drug interaction check failed",
            extra={
                'operation_type': 'drug_interaction_check_error',
                'user_id': current_user.user_id,
                'request_id': request_id,
                'error': str(e)
            }
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DRUG_INTERACTION_CHECK_FAILED",
                "message": "Drug interaction check encountered an error",
                "request_id": request_id
            }
        )

@app.post("/api/v1/documentation/generate")
async def generate_healthcare_documentation(
    request: HealthcareDocumentationRequest,
    background_tasks: BackgroundTasks,
    current_user: HealthcareUserToken = Depends(require_healthcare_permission(HealthcarePermission.WRITE_PHI)),
    healthcare_services = Depends(get_healthcare_services)
) -> Dict[str, Any]:
    """
    Generate healthcare documentation templates
    
    **Medical Disclaimer**: Provides documentation templates and assistance only.
    All clinical content must be reviewed and validated by qualified healthcare professionals.
    """
    
    request_id = str(uuid4())
    
    try:
        # Validate minimum necessary access
        if not await _validate_minimum_necessary_access(current_user, request.document_type):
            raise HTTPException(
                status_code=403,
                detail="Access denied: Minimum necessary standard not met for document type"
            )
        
        # Log documentation request
        logger = get_healthcare_logger('documentation_api')
        logger.info(
            f"Healthcare documentation requested",
            extra={
                'operation_type': 'healthcare_documentation',
                'user_id': current_user.user_id,
                'request_id': request_id,
                'document_type': request.document_type,
                'specialty': request.specialty
            }
        )
        
        # Generate documentation using document processor agent
        documentation_task = await healthcare_services.document_processor.generate_healthcare_document(
            document_type=request.document_type,
            template_parameters=request.template_parameters,
            specialty=request.specialty,
            provider_id=current_user.user_id
        )
        
        # Add background task for audit logging
        background_tasks.add_task(
            _log_documentation_generation,
            current_user.user_id,
            request_id,
            request.document_type
        )
        
        return {
            "success": True,
            "request_id": request_id,
            "task_id": documentation_task['task_id'],
            "status": "processing",
            "message": "Healthcare documentation generation initiated",
            "estimated_completion": "2-5 minutes",
            "medical_disclaimer": "Generated documentation templates require review and validation by qualified healthcare professionals."
        }
        
    except Exception as e:
        logger.error(
            f"Healthcare documentation generation failed",
            extra={
                'operation_type': 'documentation_generation_error',
                'user_id': current_user.user_id,
                'request_id': request_id,
                'error': str(e)
            }
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "DOCUMENTATION_GENERATION_FAILED",
                "message": "Healthcare documentation generation encountered an error",
                "request_id": request_id
            }
        )
```

### 5. Real-Time Healthcare Streaming

```python
# ✅ CORRECT: Server-Sent Events for Healthcare Real-Time Updates
from fastapi.responses import StreamingResponse
import json
import asyncio

@app.get("/api/v1/clinical-reasoning/stream")
async def stream_clinical_reasoning(
    reasoning_request: str,
    current_user: HealthcareUserToken = Depends(require_healthcare_permission(HealthcarePermission.READ_PHI)),
    healthcare_services = Depends(get_healthcare_services)
) -> StreamingResponse:
    """
    Stream clinical reasoning process in real-time
    
    **Medical Disclaimer**: Provides clinical reasoning assistance and medical literature analysis only.
    Does not provide medical advice, diagnosis, or treatment recommendations.
    """
    
    async def clinical_reasoning_stream():
        """Generate clinical reasoning stream"""
        
        request_id = str(uuid4())
        logger = get_healthcare_logger('clinical_reasoning_stream')
        
        try:
            # Initialize reasoning session
            yield f"data: {json.dumps({'type': 'session_start', 'request_id': request_id, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            
            # Stream medical disclaimer
            yield f"data: {json.dumps({'type': 'medical_disclaimer', 'content': 'This clinical reasoning assistance provides medical literature analysis and research support only. It does not provide medical advice, diagnosis, or treatment recommendations. All clinical decisions must be made by qualified healthcare professionals.'})}\n\n"
            
            # Stream reasoning steps
            async for reasoning_step in healthcare_services.reasoning_engine.process_clinical_query_stream(
                query=reasoning_request,
                user_id=current_user.user_id,
                session_id=request_id
            ):
                yield f"data: {json.dumps({'type': 'reasoning_step', 'content': reasoning_step, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                
                # Add small delay to prevent overwhelming the client
                await asyncio.sleep(0.1)
            
            # Stream completion
            yield f"data: {json.dumps({'type': 'session_complete', 'request_id': request_id, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            
            # Log successful streaming session
            logger.info(
                f"Clinical reasoning stream completed",
                extra={
                    'operation_type': 'clinical_reasoning_stream_complete',
                    'user_id': current_user.user_id,
                    'request_id': request_id
                }
            )
            
        except Exception as e:
            # Stream error information
            yield f"data: {json.dumps({'type': 'error', 'error': 'CLINICAL_REASONING_ERROR', 'message': 'Clinical reasoning stream encountered an error', 'request_id': request_id})}\n\n"
            
            logger.error(
                f"Clinical reasoning stream failed",
                extra={
                    'operation_type': 'clinical_reasoning_stream_error',
                    'user_id': current_user.user_id,
                    'request_id': request_id,
                    'error': str(e)
                }
            )
    
    return StreamingResponse(
        clinical_reasoning_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Healthcare-Compliance": "HIPAA-Compliant",
            "X-PHI-Safe": "true"
        }
    )
```

### 6. Healthcare API Error Handling

```python
# ✅ CORRECT: Healthcare-Specific Error Handling
from fastapi import HTTPException
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException

class HealthcareAPIException(Exception):
    """Base exception for healthcare API errors"""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class PHIDetectionException(HealthcareAPIException):
    """Exception for PHI detection in API requests/responses"""
    
    def __init__(self, message: str = "PHI detected in request"):
        super().__init__("PHI_DETECTED", message)

class HIPAAComplianceException(HealthcareAPIException):
    """Exception for HIPAA compliance violations"""
    
    def __init__(self, message: str, compliance_requirement: str):
        super().__init__(
            "HIPAA_COMPLIANCE_VIOLATION", 
            message, 
            {"compliance_requirement": compliance_requirement}
        )

@app.exception_handler(HealthcareAPIException)
async def healthcare_api_exception_handler(request: Request, exc: HealthcareAPIException):
    """Handle healthcare-specific API exceptions"""
    
    logger = get_healthcare_logger('api_errors')
    
    # Log healthcare API error
    logger.error(
        f"Healthcare API error: {exc.error_code}",
        extra={
            'operation_type': 'healthcare_api_error',
            'error_code': exc.error_code,
            'error_message': exc.message,
            'error_details': exc.details,
            'request_path': str(request.url),
            'request_method': request.method
        }
    )
    
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "timestamp": datetime.utcnow().isoformat(),
            "medical_disclaimer": "This error response is part of a healthcare administrative system and does not constitute medical advice."
        }
    )

@app.exception_handler(PHIDetectionException)
async def phi_detection_exception_handler(request: Request, exc: PHIDetectionException):
    """Handle PHI detection exceptions with enhanced security"""
    
    logger = get_healthcare_logger('phi_detection_errors')
    
    # Log PHI detection with enhanced security details
    logger.error(
        f"PHI detected in API request",
        extra={
            'operation_type': 'phi_detection_violation',
            'request_path': str(request.url),
            'request_method': request.method,
            'ip_address': request.client.host,
            'user_agent': request.headers.get('user-agent', 'unknown'),
            'security_incident': True,
            'requires_investigation': True
        }
    )
    
    return JSONResponse(
        status_code=400,
        content={
            "error": "PHI_DETECTED",
            "message": "Request contains potential Protected Health Information and cannot be processed",
            "security_notice": "This incident has been logged for security review",
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

### 7. Healthcare API Testing

```python
# ✅ CORRECT: Healthcare API Testing Patterns
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

@pytest.fixture
def healthcare_test_client():
    """Test client for healthcare API"""
    return TestClient(app)

@pytest.fixture
def mock_healthcare_services():
    """Mock healthcare services for testing"""
    with patch('core.dependencies.get_healthcare_services') as mock_services:
        mock_services.return_value = Mock()
        yield mock_services.return_value

@pytest.fixture
def valid_healthcare_token():
    """Generate valid healthcare JWT token for testing"""
    auth_manager = HealthcareAuthManager()
    
    test_user = HealthcareUserToken(
        user_id="test_provider_001",
        username="test_provider",
        role=HealthcareRole.HEALTHCARE_PROVIDER,
        permissions=[HealthcarePermission.READ_PHI, HealthcarePermission.WRITE_PHI],
        npi_number="1234567890",
        facility_id="TEST_FACILITY",
        session_id="test_session_001",
        exp=datetime.utcnow() + timedelta(minutes=30)
    )
    
    return auth_manager.create_healthcare_access_token(test_user)

def test_medical_literature_search_success(healthcare_test_client, mock_healthcare_services, valid_healthcare_token):
    """Test successful medical literature search"""
    
    # Mock research assistant response
    mock_healthcare_services.research_assistant.search_medical_literature.return_value = {
        'results': [
            {
                'title': 'Diabetes Management in Primary Care',
                'authors': ['Smith, J.', 'Jones, A.'],
                'journal': 'Journal of Medical Practice',
                'year': 2023,
                'abstract': 'Study on diabetes management approaches...'
            }
        ],
        'total_count': 125,
        'sources_used': ['PubMed', 'Clinical Trials']
    }
    
    # Test request
    response = healthcare_test_client.post(
        "/api/v1/medical-literature/search",
        json={
            "search_terms": ["diabetes mellitus", "insulin resistance"],
            "specialty_filter": "endocrinology",
            "max_results": 10
        },
        headers={"Authorization": f"Bearer {valid_healthcare_token}"}
    )
    
    assert response.status_code == 200
    response_data = response.json()
    
    assert response_data["success"] is True
    assert "medical_disclaimer" in response_data
    assert len(response_data["search_results"]) == 1
    assert response_data["total_results"] == 125
    assert "PubMed" in response_data["sources"]

def test_phi_detection_in_request(healthcare_test_client, valid_healthcare_token):
    """Test PHI detection in API request"""
    
    # Request with potential PHI (SSN pattern)
    response = healthcare_test_client.post(
        "/api/v1/medical-literature/search",
        json={
            "search_terms": ["diabetes 123-45-6789"],  # Contains SSN pattern
            "max_results": 10
        },
        headers={"Authorization": f"Bearer {valid_healthcare_token}"}
    )
    
    assert response.status_code == 400
    response_data = response.json()
    
    assert response_data["error"] == "PHI_DETECTED_IN_REQUEST"
    assert "PHI" in response_data["message"]

def test_unauthorized_access(healthcare_test_client):
    """Test unauthorized API access"""
    
    response = healthcare_test_client.post(
        "/api/v1/medical-literature/search",
        json={
            "search_terms": ["diabetes mellitus"],
            "max_results": 10
        }
    )
    
    assert response.status_code == 401
    assert "Could not validate healthcare credentials" in response.json()["detail"]

def test_insufficient_permissions(healthcare_test_client):
    """Test access with insufficient healthcare permissions"""
    
    # Create token with limited permissions
    auth_manager = HealthcareAuthManager()
    limited_user = HealthcareUserToken(
        user_id="test_user_001",
        username="test_user",
        role=HealthcareRole.PATIENT,
        permissions=[],  # No PHI read permission
        facility_id="TEST_FACILITY",
        session_id="test_session_002",
        exp=datetime.utcnow() + timedelta(minutes=30)
    )
    
    limited_token = auth_manager.create_healthcare_access_token(limited_user)
    
    response = healthcare_test_client.post(
        "/api/v1/medical-literature/search",
        json={
            "search_terms": ["diabetes mellitus"],
            "max_results": 10
        },
        headers={"Authorization": f"Bearer {limited_token}"}
    )
    
    assert response.status_code == 403
    assert "Healthcare permission required" in response.json()["detail"]
```

## Medical Disclaimer

**MEDICAL DISCLAIMER: This API development instruction set provides patterns for healthcare administrative and research assistance systems only. It assists developers in creating HIPAA-compliant APIs that support medical literature research, drug interaction checking, and clinical documentation assistance. It does not provide medical advice, diagnosis, or treatment recommendations. All APIs developed using these patterns must include appropriate medical disclaimers and ensure that all clinical decisions are made by qualified healthcare professionals based on individual patient assessment.**
