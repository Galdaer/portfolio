# Healthcare Domain Patterns

**WORKFLOW CONTROL**: All workflows are controlled by `copilot-instructions.md`. This file provides implementation patterns only.

## Medical Safety Patterns

```python
# Medical advice prevention
def validate_medical_request(request: str) -> bool:
    medical_keywords = ["diagnose", "treatment", "medication", "symptoms"]
    if any(keyword in request.lower() for keyword in medical_keywords):
        return False, "I cannot provide medical advice. Please consult with a healthcare professional."
    return True, None

# Medical disclaimer injection
MEDICAL_DISCLAIMER = """
This system provides information for healthcare professionals only.
Not intended for direct patient diagnosis or treatment decisions.
All medical decisions require licensed healthcare provider oversight.
"""

def add_medical_disclaimer(response: str) -> str:
    return f"{response}\n\n{MEDICAL_DISCLAIMER}"
```

## Financial Calculation Patterns

```python
from decimal import Decimal

# Safe division with zero protection
def safe_division(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        return Decimal('0')
    return numerator / denominator

# Convert to Decimal safely
def to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))  # Preserves precision
    raise ValueError(f"Cannot convert {type(value)} to Decimal")

# Insurance copay calculation
def calculate_copay(amount: Decimal, percentage: Decimal) -> Decimal:
    if percentage <= 0:
        return Decimal('0')
    return amount * (percentage / Decimal('100'))
```

### Healthcare AI Agent Reliability (Updated 2025-08-14)

```python
# ✅ CRITICAL: LangChain agent patterns for healthcare stability
class HealthcareAgentReliability:
    """Agent reliability patterns from critical bug fixes."""
    
    @staticmethod
    def create_stable_healthcare_agent(llm, tools):
        """Create LangChain agent with healthcare-specific stability patterns."""
        from langchain import hub
        from langchain.agents import create_react_agent, AgentExecutor
        
        # Use proven ReAct pattern - more stable than structured chat
        prompt = hub.pull("hwchase17/react")
        agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
        
        # CRITICAL: No memory parameter to prevent scratchpad conflicts
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            return_intermediate_steps=True,
            handle_parsing_errors="Check your output and make sure it conforms!",
            # NO memory - prevents "agent_scratchpad should be a list of base messages" error
            # NO early_stopping_method - not supported by ReAct agents
        )
        return executor
    
    @staticmethod
    def safe_agent_execution(executor, query: str) -> Dict[str, Any]:
        """Execute agent with healthcare-appropriate error handling."""
        try:
            # CRITICAL: Only pass input - let AgentExecutor manage scratchpad
            result = await executor.ainvoke({"input": query})
            
            return {
                "success": True,
                "response": result.get("output", ""),
                "steps": result.get("intermediate_steps", [])
            }
        except Exception as e:
            # Healthcare-appropriate error response
            return {
                "success": False,
                "response": "I encountered a technical issue. Please try rephrasing your question.",
                "error": str(e),  # For logging only
                "steps": []
            }
    
    @staticmethod
    def create_medical_tool_wrapper(async_tool_func):
        """Wrap async medical tools for LangChain compatibility."""
        import asyncio
        import json
        
        def sync_wrapper(*args, **kwargs) -> str:
            if asyncio.iscoroutinefunction(async_tool_func):
                try:
                    asyncio.get_running_loop()
                    # In async context - use thread executor
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, async_tool_func(*args, **kwargs))
                        result = future.result()
                except RuntimeError:
                    # No running loop - use asyncio.run directly
                    result = asyncio.run(async_tool_func(*args, **kwargs))
            else:
                result = async_tool_func(*args, **kwargs)
            
            # Always return string for LangChain compatibility
            if isinstance(result, dict):
                return json.dumps(result, indent=2)
            return str(result)
        
        return sync_wrapper
```

# ✅ CRITICAL: Database resource management patterns
class HealthcareDatabaseSafety:
    """Database connection safety patterns from production issues."""
    
    @asynccontextmanager
    async def get_connection_with_auto_release(self):
        """Proper database connection management."""
        conn = await self.pool.acquire()
        try:
            yield conn
        finally:
            await self.pool.release(conn)
    
    async def safe_database_operation(self, operation_func, *args, **kwargs):
        """Template for safe database operations."""
        async with self.get_connection_with_auto_release() as conn:
            return await operation_func(conn, *args, **kwargs)

# ✅ CRITICAL: Avoid code duplication patterns
class HealthcareCodeOrganization:
    """Code organization patterns to prevent duplication."""
    
    # Common utilities should be in shared modules:
    # - domains/healthcare_utils.py for financial utilities
    # - core/utils/type_conversion.py for type safety utilities  
    # - core/utils/database_helpers.py for connection management
    
    @staticmethod
    def identify_duplicate_methods() -> List[str]:
        """Methods commonly duplicated across healthcare modules."""
        return [
            "_ensure_decimal",
            "_get_negotiated_rate", 
            "_get_patient_coverage_data",
            "_validate_database_connection"
        ]
```

### Healthcare Compliance Patterns

```python
# ✅ CORRECT: Comprehensive healthcare logging and PHI monitoring
class HealthcareLoggingPatterns:
    def __init__(self):
        # Setup HIPAA-compliant logging with PHI detection
        pass

class PHIMonitor:
    def detect_phi(self, data: str) -> bool:
        # Detect SSN, DOB, medical record numbers, phone numbers
        pass
    
    def anonymize_for_logging(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Remove/hash PHI for safe logging
        pass

@healthcare_log_method
def process_patient_intake(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
    # Process healthcare data with automatic audit logging
    return processed_data
```

### Medical Workflow Integration

```python
# ✅ CORRECT: Healthcare workflow patterns
class HealthcareWorkflowManager:
    def process_soap_note(self, soap_data: Dict[str, Any]) -> Dict[str, Any]:
        # Process SOAP notes with medical compliance validation
        pass
    
    def schedule_appointment(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # Administrative scheduling without medical decision-making
        pass
```

### Healthcare AI Agent Coordination

```python
# ✅ CORRECT: Multi-agent healthcare coordination
class HealthcareAgentOrchestrator:
    def coordinate_intake_workflow(self, patient_request: Dict[str, Any]):
        # Route through: intake → document_processor → clinical_research_agent
        pass
    
    def handle_emergency_scenario(self, emergency_data: Dict[str, Any]):
        # Escalate to human healthcare providers immediately
        pass
```

## Healthcare Domain Integration Patterns

### EHR Integration with AI Safety

```python
# ✅ CORRECT: Safe EHR integration patterns
class SafeEHRIntegration:
    def fetch_patient_data(self, patient_id: str, required_fields: List[str]):
        # Minimum necessary principle, audit logging, PHI protection
        pass
    
    def update_patient_record(self, patient_id: str, updates: Dict[str, Any]):
        # Validate updates don't contain medical advice or diagnosis
        pass
```

### Clinical Decision Support Integration

```python
# ✅ CORRECT: AI-assisted clinical decision support (administrative only)
class ClinicalDecisionSupportAssistant:
    def suggest_documentation_improvements(self, note: str):
        # Suggest documentation completeness, not medical decisions
        pass
    
    def validate_coding_accuracy(self, diagnosis_codes: List[str]):
        # Administrative coding validation, not medical interpretation
        pass
```

## PHI-Safe Development Patterns

- **Never expose real patient data** in logs, tests, or API calls
- **Use synthetic data generators** for all healthcare scenarios
- **Document all endpoints** with compliance disclaimers
- **Validate all external API calls** for PHI safety before deployment
- **Medical Safety**: Always redirect medical advice requests to healthcare professionals

## Updated PHI Handling (2025-08-14)

- Literature authorship and publication metadata are not PHI and should be preserved.
- Error logs must not include patient identifiers; use DIAGNOSTIC markers and previews capped to 200 chars.
- Minimum Necessary still applies to EHR data; not applicable to public literature metadata.

## Medical Data Processing Patterns (2025-08-14)

- Normalize literature sources with DOI/PMID/URL keys; deduplicate on that precedence.
- Provide DOI link first, then PubMed link; include year, journal, and abstract snippet when present.
- Always return a disclaimer and a readable summary even on timeouts or upstream errors.

---
