# Healthcare API Development Instructions

## FastAPI Healthcare Foundation

### 1. Healthcare FastAPI Application Structure

```python
# ✅ CORRECT: Healthcare FastAPI Application with Compliance
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Healthcare AI API", 
    description="**MEDICAL DISCLAIMER**: Administrative support only. No medical advice.",
    lifespan=healthcare_lifespan  # Initialize healthcare services, PHI detection, security
)

# Add healthcare middleware: CORS restrictions, PHI detection, compliance headers
@app.middleware("http")
async def healthcare_security_middleware(request: Request, call_next):
    # PHI detection in requests, compliance headers, audit logging
    pass
```

### 2. Healthcare Authentication and Authorization

```python
# ✅ CORRECT: HIPAA-Compliant Authentication
class HealthcareRole(str, Enum):
    HEALTHCARE_PROVIDER = "healthcare_provider"
    NURSE = "nurse"
    MEDICAL_ASSISTANT = "medical_assistant"

class HealthcareAuthManager:
    def __init__(self):
        # Short-lived tokens (15 min), MFA required, audit logging
        pass
    
    async def authenticate_healthcare_user(username, password, facility_id, mfa_token):
        # Database lookup, password verification, MFA validation
        # Log all authentication attempts for HIPAA compliance
        pass

async def get_current_healthcare_user(token = Depends(security)):
    # Validate JWT, check permissions, log access
    pass
```

### 3. Healthcare Data Models

```python
# ✅ CORRECT: Healthcare Pydantic Models
class PatientRequest(BaseModel):
    provider_id: str  # Non-PHI fields only
    appointment_type: str
    
class HealthcareResponse(BaseModel):
    success: bool
    message: str
    medical_disclaimer: str = "Administrative support only. No medical advice."
```

### 4. PHI-Safe Endpoints

```python
# ✅ CORRECT: Healthcare API Endpoints
@app.post("/api/v1/patients/intake")
async def patient_intake(
    request: PatientRequest,
    current_user = Depends(get_current_healthcare_user)
):
    # PHI detection, minimum necessary principle, audit logging
    # Process through intake agent with synthetic data validation
    pass

@app.get("/api/v1/health")
async def health_check():
    # Database connectivity, service health, compliance status
    return {"status": "healthy", "compliance": "HIPAA"}
```

### 5. Healthcare Error Handling

```python
### 5. Healthcare Error Handling

```python
# ✅ CORRECT: Healthcare-specific Error Responses
class HealthcareHTTPException(HTTPException):
    """Healthcare-compliant HTTP exceptions with audit logging."""
    pass

@app.exception_handler(HealthcareHTTPException)
async def healthcare_exception_handler(request: Request, exc: HealthcareHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "medical_disclaimer": "Administrative support only"}
    )
```

### 6. MCP Authentication Proxy Patterns

```python
# ✅ CORRECT: MCP-Open WebUI Authentication Proxy
class MCPAuthenticationProxy:
    """FastAPI proxy for MCP servers requiring Bearer token authentication."""
    
    async def verify_api_key(self, credentials: HTTPAuthorizationCredentials) -> str:
        # Validate against configured healthcare API key
        pass
    
    async def create_tool_endpoints(self, backend_url: str) -> None:
        # Dynamically register authenticated endpoints for each MCP tool
        pass
    
    @app.post("/tools/{tool_name}")
    async def proxy_tool_call(
        self, tool_name: str, request: Request, 
        api_key: str = Depends(verify_api_key)
    ):
        # Direct MCP tool execution with comprehensive audit logging
        pass
```

### 7. Healthcare Tool Integration

```python
# ✅ CORRECT: Conditional Tool Registration Based on API Availability
class ConditionalHealthcareTools:
    """Register healthcare tools based on available API keys and environment."""
    
    def register_public_tools(self) -> List[str]:
        # Always available: search-pubmed, search-trials, get-drug-info
        return ["search-pubmed", "search-trials", "get-drug-info"]
    
    def register_protected_tools(self) -> List[str]:
        # Require paid APIs: FHIR server, specialized medical databases
        if self.has_fhir_access():
            return ["find_patient", "get_patient_conditions", ...]
        return []
```
```

## Implementation Guidelines

### Healthcare API Best Practices

- **Medical Safety**: Always include medical disclaimers, never provide medical advice
- **PHI Protection**: Detect PHI in requests/responses, use minimum necessary principle
- **Audit Logging**: Log all healthcare operations with HIPAA compliance details
- **Authentication**: Short-lived tokens, MFA for healthcare providers, role-based access
- **Error Handling**: Generic error messages, no PHI in error responses
- **Data Validation**: Validate all healthcare data, use synthetic data for testing

---
