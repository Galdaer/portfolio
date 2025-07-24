# Healthcare Development Patterns - Updated

## Current Development Status (Phase 1)

### Active Implementation Areas
- **Core AI Infrastructure**: Ollama, MCP, PostgreSQL, Redis integration
- **Security Foundation**: PHI detection, audit logging, encryption management
- **Agent Framework**: Base agent classes with healthcare compliance
- **Memory Management**: Clinical context retention with performance tracking

### Type Safety Requirements
- **Pydantic Models**: All healthcare data models must use explicit field definitions
- **Optional Parameters**: Use Optional[Type] for nullable parameters
- **Method Signatures**: Match exact signatures for audit logging and security methods
- **Request Handling**: FastAPI Request objects must be properly typed as Optional

### Healthcare Security Patterns
- **PHI Detection**: Always convert detection results to dictionaries before logging
- **Audit Logging**: Use synchronous methods for security events, async for request logging
- **Error Messages**: Generic messages in production, detailed in development
- **Authentication**: Handle None values gracefully in all auth methods

## Phase 1 Completion Criteria
- [ ] All Pylance/type errors resolved
- [ ] Security middleware properly integrated
- [ ] MCP server with healthcare tools functional
- [ ] Agent framework with memory management
- [ ] Comprehensive test coverage for security patterns

## Development Anti-Patterns to Avoid
1. **Positional arguments** in Pydantic constructors
2. **Direct None assignment** to typed parameters
3. **Missing error/result parameters** in response models
4. **Unhandled Optional types** in FastAPI endpoints
5. **Inconsistent async/sync patterns** in security methods