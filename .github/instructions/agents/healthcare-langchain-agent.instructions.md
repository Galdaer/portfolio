# Healthcare LangChain Agent Instructions

## Purpose
Patterns for building and operating the healthcare LangChain agent with local-only LLMs (Ollama), MCP tools, and HIPAA-aware behavior.

## Contracts
- Inputs: user input (string), chat_history (list of BaseMessages), tools (LangChain tools), MCP client
- Outputs: final answer string, intermediate_steps [(AgentAction, observation)], optional citations list
- Error modes: prompt variable errors, tool parsing errors, Ollama connectivity, MCP tool failures
- Success: valid structured chat loop with tool use; final answer or graceful error

## Validated Pattern (LangChain 0.3.x)
- Use `create_structured_chat_agent(llm, tools, prompt)` and `AgentExecutor`.
- Prompt variables required: `tools`, `tool_names`, `input`, `agent_scratchpad`.
- Prompt shape:
  - system: rules + JSON examples; escape JSON braces with `{{` and `}}`.
  - MessagesPlaceholder("chat_history", optional=True)
  - human: "{input}"
  - MessagesPlaceholder("agent_scratchpad")

Example skeleton:

```
prompt = ChatPromptTemplate.from_messages([
  ("system", "Respond ... tools: {tools} ... Valid \"action\" values: {tool_names} ... Example: ```\n{{\n  \"action\": $TOOL_NAME,\n  \"action_input\": $INPUT\n}}\n``` ... Final Answer example ..."),
  MessagesPlaceholder("chat_history", optional=True),
  ("human", "{input}"),
  MessagesPlaceholder("agent_scratchpad"),
])
agent = create_structured_chat_agent(llm=llm, tools=tools, prompt=prompt)
executor = AgentExecutor(
  agent=agent,
  tools=tools,
  verbose=True,
  max_iterations=5,
  return_intermediate_steps=True,
  handle_parsing_errors=True,
)
```

## agent_scratchpad rules
- Must be a list of BaseMessages. Never inject a string in `{agent_scratchpad}`.
- Let AgentExecutor populate from `intermediate_steps`.

## Model configuration (Ollama)
- Default to `llama3.1:8b` from `services/user/healthcare-api/config/models.yml` under `primary_models.healthcare_llm`.
- Honor `OLLAMA_BASE_URL` (default http://localhost:11434) and context size via `num_ctx`.
- Do not invent model names (e.g., do not use llama3.2).

## MCP tools integration
- Public tools (e.g., PubMed) must bypass OAuth; no patientId required.
- Normalize tool names (hyphen vs underscore) consistently both in tool registration and usage.

## Troubleshooting
- INVALID_PROMPT_INPUT complaining about `"action"` → escape JSON braces with `{{` and `}}` in system examples.
- `agent_scratchpad should be a list of base messages` → add `MessagesPlaceholder("agent_scratchpad")` and remove string usage.
- Ollama connection errors → confirm service reachable on `OLLAMA_BASE_URL`, correct model pulled (`ollama pull llama3.1:8b`).
- MCP tool failures → verify server starts in same container and tool names match normalization.

## Gotchas and Acceptance Checks
- Never include `{agent_scratchpad}` inside the human message; use a MessagesPlaceholder after the human turn.
- Ensure prompt variables include `{tools}` and `{tool_names}`; forgetting `{tool_names}` leads to invalid action validation.
- Agent output acceptance:
  - Returns `output` string and `intermediate_steps` list.
  - Builds a user-facing `formatted_summary` (upstream orchestrator may post-process for UI header and sources).
  - When citations are present, downstream orchestrator can append a "Sources:" section.

## Executor Tuning
- `max_iterations`: start 3–5; high values may mask MCP transport issues.
- `early_stopping_method="generate"`: helps finish gracefully when tool loop stalls.
- `handle_parsing_errors=True`: lets the agent recover from minor JSON formatting slips.

## Compliance
- Local inference only; do not transmit PHI externally.
- Strong typing; avoid `# type: ignore` in healthcare modules.
