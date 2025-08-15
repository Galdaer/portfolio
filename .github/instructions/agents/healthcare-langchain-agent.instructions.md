# Healthcare LangChain Agent Instructions

## CRITICAL UPDATE (2025-08-14): Agent Scratchpad Fix

**BREAKING CHANGE**: Structured chat agents with ConversationSummaryBufferMemory cause scratchpad type errors in LangChain 0.3.x.

**NEW VALIDATED PATTERN**: Use ReAct agent without memory for stability.

```python
# ✅ WORKING PATTERN (VERIFIED 2025-08-14)
from langchain import hub
from langchain.agents import create_react_agent, AgentExecutor

# Use proven ReAct prompt from hub - no custom prompt needed
prompt = hub.pull("hwchase17/react")
agent = create_react_agent(llm=self.llm, tools=self.tools, prompt=prompt)

self.executor = AgentExecutor(
    agent=agent,
    tools=self.tools,
    verbose=True,
    return_intermediate_steps=True,
    handle_parsing_errors="Check your output and make sure it conforms!",
    # CRITICAL: NO memory parameter - prevents scratchpad conflicts
    # CRITICAL: NO early_stopping_method="generate" - not supported by ReAct
)

# ONLY pass input - AgentExecutor manages agent_scratchpad internally
result = await self.executor.ainvoke({"input": query})
```

## Contracts
- Inputs: user input (string), tools (LangChain tools), MCP client
- Outputs: final answer string, intermediate_steps [(AgentAction, observation)]
- Error modes: tool execution errors, Ollama connectivity, MCP tool failures
- Success: valid ReAct loop with tool use; final answer or graceful error

## DEPRECATED PATTERNS (DO NOT USE)
```python
# ❌ BROKEN: Structured chat with memory causes scratchpad errors
self.executor = AgentExecutor(
    agent=agent,
    tools=self.tools,
    memory=self.memory,  # CAUSES: "agent_scratchpad should be a list of base messages, got str"
    return_intermediate_steps=True
)

# ❌ BROKEN: Passing additional variables to ainvoke
result = await self.executor.ainvoke({
    "input": query,
    "chat_history": history,  # Don't pass this - causes conflicts
    "agent_scratchpad": []    # NEVER pass this manually
})
```

## Model configuration (Ollama)
- Default to `llama3.1:8b` from `services/user/healthcare-api/config/models.yml` under `primary_models.healthcare_llm`.
- Honor `OLLAMA_BASE_URL` (default http://localhost:11434) and context size via `num_ctx`.
- Do not invent model names (e.g., do not use llama3.2).

## MCP tools integration
- Tools must return strings for LangChain compatibility (use `json.dumps()` for complex data)
- Async MCP tools need sync wrappers using `asyncio.iscoroutinefunction()` detection
- Handle broken pipe errors gracefully - common with container-to-container MCP communication
- Public tools (e.g., PubMed) must bypass OAuth; no patientId required
- Normalize tool names (hyphen vs underscore) consistently in tool registration and usage

## Troubleshooting

### Agent Scratchpad Errors (RESOLVED 2025-08-14)
- **Error**: `variable agent_scratchpad should be a list of base messages, got str`
- **Solution**: Use ReAct agent without memory, never pass memory to AgentExecutor
- **Prevention**: Only pass `{"input": query}` to `ainvoke()`, let AgentExecutor manage scratchpad

### MCP Connection Issues
- **Error**: `[Errno 32] Broken pipe` in tool calls
- **Investigation**: Check MCP server container logs, verify stdio streams, test resource limits
- **Workaround**: Agent handles tool failures gracefully and continues execution

### Async/Sync Compatibility  
- **Error**: `coroutine was never awaited` warnings
- **Solution**: Use `_safe_tool_wrapper` with proper async detection
- **Pattern**: All LangChain tools must be sync functions returning strings

## Gotchas and Acceptance Checks
- **CRITICAL**: Never add memory parameter to AgentExecutor - causes scratchpad conflicts
- **CRITICAL**: Use ReAct agent, not structured chat agent for stability
- Returns `output` string and `intermediate_steps` list
- Agent gracefully handles tool failures and continues execution
- Local inference only; do not transmit PHI externally

## Executor Tuning (Updated for ReAct)
- `max_iterations`: default 5 for ReAct agents
- **DO NOT USE** `early_stopping_method="generate"` - not supported by ReAct agents  
- `handle_parsing_errors`: use descriptive string like "Check your output and make sure it conforms!"
- `return_intermediate_steps=True`: required for debugging and tool chain analysis

## Compliance
- Local inference only; do not transmit PHI externally
- Strong typing; avoid `# type: ignore` in healthcare modules
- All tool responses logged at INFO level (PHI-safe)
