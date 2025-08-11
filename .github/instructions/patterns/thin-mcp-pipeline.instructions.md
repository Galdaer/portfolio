# Thin MCP Pipeline Implementation Patterns

## Strategic Purpose

**THIN COMMUNICATION LAYER**: MCP pipeline serves as minimal proxy forwarding requests to healthcare-api, which handles all routing, agent decisions, and tool selection.

**Architecture Flow**: Open WebUI → MCP Pipeline (thin proxy) → Healthcare API → Agents → MCP Tools

## Thin Pipeline Architecture Patterns

### Minimal Proxy Implementation

```python
# ✅ PATTERN: Thin MCP pipeline as simple HTTP proxy
import httpx
from typing import Dict, Any, Optional
import logging

class ThinMCPPipeline:
    def __init__(self):
        self.healthcare_api_base = "http://healthcare-api:8000"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def forward_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Forward request to healthcare-api without processing"""
        # Simple HTTP forwarding - no complex logic
        pass
    
    async def pipe(self, user_message: str, model_id: str, **kwargs) -> Iterator[str]:
        """Main pipeline entry point - forwards to healthcare-api"""
        # Minimal processing, forward to healthcare-api
        pass
```

### Request Forwarding Patterns

```python
# ✅ PATTERN: Simple request transformation and forwarding
class RequestForwarder:
    async def transform_openwebui_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Open WebUI format to healthcare-api format"""
        # Minimal transformation only
        pass
    
    async def forward_to_healthcare_api(self, transformed_request: Dict[str, Any]) -> Any:
        """Forward to healthcare-api with proper error handling"""
        # Simple HTTP POST with timeout handling
        pass
```

### Error Handling Patterns

```python
# ✅ PATTERN: Simple error handling for proxy layer
class PipelineErrorHandler:
    def handle_healthcare_api_error(self, error: Exception) -> Dict[str, Any]:
        """Handle healthcare-api connection errors"""
        # Return user-friendly error without exposing internals
        pass
    
    def handle_timeout_error(self) -> Dict[str, Any]:
        """Handle request timeout errors"""
        # Return timeout message with retry suggestion
        pass
```

## Implementation Guidelines

### What Pipeline SHOULD Do:
- Forward requests to healthcare-api
- Handle basic request/response transformation
- Provide simple error handling and timeouts
- Log request flow for debugging

### What Pipeline SHOULD NOT Do:
- Make AI model decisions
- Select which agents to use
- Call MCP tools directly
- Implement complex business logic
- Handle patient data processing

### Healthcare-API Responsibilities:
- All routing and agent selection
- MCP tool invocation
- Medical data processing
- PHI protection and compliance
- Complex workflow orchestration

## Service Configuration Patterns

### Docker Network Communication

```yaml
# ✅ PATTERN: Simple service-to-service communication
services:
  mcp-pipeline:
    environment:
      HEALTHCARE_API_URL: "http://healthcare-api:8000"
  
  healthcare-api:
    # Handles all complex logic
    environment:
      MCP_SERVER_URL: "http://healthcare-mcp:3001"
```

### Environment Variables

```bash
# MCP Pipeline (minimal configuration)
HEALTHCARE_API_URL=http://healthcare-api:8000
LOG_LEVEL=INFO
REQUEST_TIMEOUT=30

# Healthcare API (comprehensive configuration)
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
MCP_SERVER_URL=http://healthcare-mcp:3001
```

## Testing Patterns

### Pipeline Testing Focus

```python
# ✅ PATTERN: Test forwarding behavior, not business logic
def test_request_forwarding():
    """Test that requests are properly forwarded to healthcare-api"""
    pass

def test_error_handling():
    """Test error handling when healthcare-api is unavailable"""
    pass

def test_timeout_handling():
    """Test timeout behavior with slow healthcare-api responses"""
    pass
```

## Migration Strategy

### Phase 1: Remove Complex Logic
- Strip out AI model calling from pipeline
- Remove agent selection logic
- Remove MCP tool invocation
- Keep only HTTP forwarding

### Phase 2: Simplify Dependencies
- Remove unnecessary MCP imports
- Reduce to minimal FastAPI setup
- Simplify configuration management

### Phase 3: Optimize Performance
- Add connection pooling for healthcare-api calls
- Implement simple caching if needed
- Add basic request/response compression
