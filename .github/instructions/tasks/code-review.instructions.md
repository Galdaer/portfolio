````instructions
# Healthcare AI Code Review Instructions

**WORKFLOW CONTROL**: All workflows are controlled by `copilot-instructions.md`. This file provides implementation patterns only.

## Purpose

Code review guidance for healthcare AI systems emphasizing medical compliance, PHI protection, and healthcare-specific patterns.

## Healthcare Code Review Checklist

### Medical Safety & Compliance
- **Medical advice prevention**: Check for inappropriate medical recommendations
- **Disclaimer requirements**: Ensure proper medical disclaimers are present
- **PHI protection**: Verify no patient data is hardcoded or logged inappropriately
- **HIPAA compliance**: Review data handling and access control patterns

### Financial Calculation Safety (Based on PR #31)
- **Decimal vs Float**: Use Decimal for financial calculations, not float
- **Division by zero**: Check for proper zero-division protection
- **Method signatures**: Ensure consistent parameter types across methods
- **Null handling**: Verify proper handling of None values in calculations

### Database Resource Management (Based on PR #31)
- **Connection cleanup**: Verify proper database connection release
- **Context managers**: Use async context managers for database operations
- **Error handling**: Ensure database connections are cleaned up in exception scenarios
- **Resource leaks**: Check for missing connection.close() or pool.release() calls

### Code Duplication Detection (Based on PR #31)
- **Utility methods**: Look for duplicate helper methods across files
- **Import statements**: Check for redundant imports
- **Constants**: Consolidate magic numbers into shared constants
- **Patterns**: Identify repeated code patterns that should be abstracted

### Security Review Patterns
- **API key exposure**: Check for hardcoded credentials or API keys
- **CORS configuration**: Verify CORS settings are production-appropriate
- **Input validation**: Ensure proper sanitization of user inputs
- **Error messages**: Check that errors don't expose sensitive information

### Performance Considerations
- **Database queries**: Review for N+1 query problems
- **Memory usage**: Check for potential memory leaks in long-running processes
- **Async patterns**: Verify proper async/await usage
- **Caching**: Look for opportunities to cache expensive operations

### Healthcare-Specific Patterns
- **Synthetic data usage**: Ensure test data is synthetic, not real patient data
- **Audit logging**: Verify proper logging for compliance requirements
- **Access control**: Review role-based permissions and authentication
- **Data minimization**: Check that only necessary data is processed
 
## Orchestrator Alignment Checklist (2025-08-14)

- Routing
	- [ ] Exactly one agent selected per request (no implicit helpers)
	- [ ] No always-on medical_search; invoked only when selected
- Provenance
	- [ ] Human responses include agent provenance header when enabled
	- [ ] Agent payloads include `agent_name` when available
- Fallback
	- [ ] Base fallback path returns safe, non-medical response with disclaimers
	- [ ] No business logic in pipeline; fallback handled by healthcare-api
- Timeouts & Resilience
	- [ ] `timeouts.per_agent_default` respected; `per_agent_hard_cap` enforced
	- [ ] Metrics/logging are non-blocking
- Formatting & Contracts
	- [ ] Agents prefer `formatted_summary` for human UI
	- [ ] JSON contracts unchanged; human formatting added at API layer
- Configuration
	- [ ] `services/user/healthcare-api/config/orchestrator.yml` is the source of truth
	- [ ] PRs document any changes to routing/timeouts/provenance/fallback keys
````
