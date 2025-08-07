# Healthcare MCP Auth Proxy Development Patterns

## Overview
Patterns for developing and maintaining the Healthcare MCP authentication proxy that bridges Open WebUI with Healthcare MCP server via stdio JSON-RPC communication.

## Architecture Pattern

### Dual Interface Design
```python
# FastAPI HTTP proxy (port 3001) ← Open WebUI
# ↓ stdio/JSON-RPC communication 
# Healthcare MCP Server (TypeScript, subprocess)
```

### Optional API Key Pattern
**Problem**: Free medical APIs (PubMed, ClinicalTrials, FDA) should work without API keys
**Solution**: Optional constructor parameters with fallback behavior

```typescript
// ✅ CORRECT: Optional API key constructor
constructor(
    pubmedAPIKey?: string,
    trialsAPIKey?: string, 
    fdaAPIKey?: string
) {
    this.pubmedAPIKey = pubmedAPIKey;
    this.trialsAPIKey = trialsAPIKey;
    this.fdaAPIKey = fdaAPIKey;
}

// ✅ CORRECT: Fallback to free tier
if (!this.fdaAPIKey && this.isRateLimited()) {
    throw new Error("FDA API rate limit reached. Consider getting free API key at https://...");
}
```

## Type Safety Patterns

### Subprocess Stream Safety
**Problem**: `subprocess.Popen` streams can be `None`, causing "can't concat NoneType to bytes"
**Solution**: Proper null checks before stream operations

```python
# ❌ WRONG: Direct stream access
response_line = mcp_process.stdout.readline().strip()

# ✅ CORRECT: Null-safe stream access  
if mcp_process and mcp_process.stdout:
    raw_response = mcp_process.stdout.readline()
    response_line = raw_response.strip() if raw_response else ""
    if response_line:
        # Process response
```

### Type Annotation Pattern
```python
# ✅ CORRECT: Proper subprocess typing
import subprocess
from typing import Optional

mcp_process: Optional[subprocess.Popen[bytes]] = None

def start_mcp_server() -> bool:
    global mcp_process
    try:
        mcp_process = subprocess.Popen(
            ["node", "dist/index.js"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=False  # Use bytes mode
        )
        return mcp_process is not None
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        return False
```

### Select Module Import Pattern
```python
# ✅ CORRECT: Import at module level
import select
import json
import subprocess
from typing import Optional, Dict, Any

# Later in function - no redundant imports needed
ready, _, _ = select.select([mcp_process.stdout], [], [], timeout)
```

## Error Handling Patterns

### Graceful MCP Communication Failures
```python
# ✅ CORRECT: Comprehensive error handling
async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not mcp_process or mcp_process.poll() is not None:
        raise HTTPException(status_code=503, detail="Healthcare MCP server unavailable")
    
    try:
        # Send request with null checks
        if mcp_process.stdin:
            mcp_process.stdin.write(json.dumps(request).encode() + b"\n")
            mcp_process.stdin.flush()
        else:
            raise HTTPException(status_code=503, detail="MCP stdin unavailable")
            
        # Read response with timeout and null checks
        if mcp_process.stdout:
            ready, _, _ = select.select([mcp_process.stdout], [], [], 10.0)
            if ready:
                raw_response = mcp_process.stdout.readline()
                if raw_response:
                    response = json.loads(raw_response.decode().strip())
                    return response.get("result", {})
                    
        raise HTTPException(status_code=504, detail="MCP server timeout")
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Invalid MCP response")
    except Exception as e:
        logger.error(f"MCP communication error: {e}")
        raise HTTPException(status_code=500, detail="MCP server error")
```

## Medical API Integration Patterns

### Rate Limiting with Graceful Degradation
```typescript
// ✅ CORRECT: Rate limiting with helpful errors
class FDAConnector {
    private requestCount = 0;
    private lastRequestTime = 0;
    private readonly maxRequestsPerMinute = 240; // Free tier limit
    
    private async isRateLimited(): Promise<boolean> {
        const now = Date.now();
        if (now - this.lastRequestTime > 60000) {
            this.requestCount = 0; // Reset counter every minute
            this.lastRequestTime = now;
        }
        return this.requestCount >= this.maxRequestsPerMinute;
    }
    
    async searchDrugs(query: string): Promise<any> {
        if (!this.apiKey && await this.isRateLimited()) {
            throw new Error(
                "FDA API rate limit reached (240/min). " +
                "Consider getting free API key at https://open.fda.gov/apis/authentication/"
            );
        }
        this.requestCount++;
        // Make request...
    }
}
```

## Testing Patterns

### Auth Proxy Testing
```python
# ✅ CORRECT: Test MCP communication with mocks
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_mcp_process():
    mock_process = Mock()
    mock_process.stdin = Mock()
    mock_process.stdout = Mock()
    mock_process.stderr = Mock()
    mock_process.poll.return_value = None  # Process running
    return mock_process

async def test_mcp_tool_call_success(mock_mcp_process):
    with patch('auth_proxy.mcp_process', mock_mcp_process):
        # Mock successful response
        mock_mcp_process.stdout.readline.return_value = b'{"result": {"status": "success"}}\n'
        
        result = await call_mcp_tool("search-pubmed", {"query": "diabetes"})
        assert result["status"] == "success"
```

## Deployment Patterns

### Docker Integration
```dockerfile
# ✅ CORRECT: Multi-stage build with proper permissions
FROM node:20-slim

# Install Python for auth proxy
RUN apt-get update && apt-get install -y python3 python3-pip

# Copy and build TypeScript MCP server
COPY src/ ./src/
RUN npm install && npm run build

# Copy auth proxy
COPY auth_proxy.py ./
COPY auth_proxy_requirements.txt ./
RUN python3 -m pip install -r auth_proxy_requirements.txt

# Set proper user for healthcare compliance
USER 1000:1001

CMD ["/app/start_services.sh"]
```

## Future Enhancements

### Local API Mirroring (Phase 2)
Consider implementing local mirrors of medical APIs to eliminate rate limits:

- **PubMed Mirror**: Download and index PMC articles locally
- **ClinicalTrials Mirror**: Sync ClinicalTrials.gov data to local database  
- **FDA Mirror**: Cache drug information in local search index

**Benefits**: No rate limits, faster responses, offline capability
**Implementation**: Separate microservice with daily sync jobs

## Troubleshooting

### Common Issues
1. **"can't concat NoneType to bytes"** → Missing null checks on subprocess streams
2. **"readline() is not a known attribute of None"** → Need proper type annotations and guards
3. **"MCP server unavailable"** → Check subprocess startup and stdio configuration
4. **Rate limit errors** → Verify optional API key pattern implementation

### Debug Commands
```bash
# Check MCP server logs
docker logs healthcare-mcp

# Verify auth proxy endpoint
curl -H "Authorization: Bearer healthcare-mcp-2025" http://localhost:3001/openapi.json

# Test direct MCP communication
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | docker exec -i healthcare-mcp node dist/index.js
```

---

*These patterns ensure robust Healthcare MCP auth proxy development with proper type safety, error handling, and medical API integration.*
