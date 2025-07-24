# Python Type Safety Patterns for Healthcare AI

## Critical Type Safety Rules

### Pydantic Model Constructor Patterns
- **ALWAYS provide all required fields** explicitly in Pydantic model constructors
- **Use keyword arguments** for clarity and type safety
- **Provide None for optional fields** when not used

```python
# ✅ CORRECT: Explicit keyword arguments
return MCPResponse(result=result_data, error=None, id=request.id)

# ❌ WRONG: Positional arguments or missing fields
return MCPResponse(result_data, request.id)  # Missing error parameter
```

### Optional Type Annotations
- **Use Optional[Type]** for parameters that can be None
- **Never use Type = None** in function signatures

```python
# ✅ CORRECT: Optional type annotation
async def endpoint(client_request: Optional[Request] = None):

# ❌ WRONG: Direct None assignment
async def endpoint(client_request: Request = None):
```

### Method Parameter Validation
- **Always check method signatures** before calling
- **Provide all required parameters** even if None
- **Use hasattr() checks** for dynamic method calls

### FastAPI Request Handling
- **Request objects must be Optional** when they might not be provided
- **Always check for None** before accessing Request attributes
- **Use mock objects** for testing when real Request unavailable

## Healthcare-Specific Type Safety

### Security Method Signatures
- **Audit logging methods** must match expected signatures exactly
- **PHI detection results** must be converted to proper types before logging
- **Authentication methods** must handle None values gracefully

### Error Handling Patterns
- **Generic error messages** for production (no config exposure)
- **Detailed errors** for development with feature flags
- **Type-safe error response models** with all required fields