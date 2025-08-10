"""Healthcare MCP Pipeline logic.

Dynamic stdio MCP client that:
 - Loads server definitions from mcp_config.json
 - Connects to each MCP server over stdio
 - Discovers available tools ("tools/list")
 - Exposes tool metadata for FastAPI layer
 - Invokes tools ("tools/call") when requested

All functionality is PHI-safe: only tool metadata and invocation results flow
through this layer; underlying servers enforce data access policies.
"""

import asyncio
import json
import logging
import os
import uuid
from typing import List, Union, Generator, Iterator, Any, Optional, Dict, Tuple

from pydantic import BaseModel

try:  # Optional dependency
    from mcp import ClientSession, StdioServerParameters  # type: ignore
    from mcp.client.stdio import stdio_client  # type: ignore
    MCP_AVAILABLE = True
except Exception:  # pragma: no cover
    MCP_AVAILABLE = False
    logging.warning("MCP library not available. Install with: pip install mcp")
    class StdioServerParameters:  # type: ignore
        def __init__(self, *_, **__):
            pass
    def stdio_client(*_, **__):  # type: ignore
        raise RuntimeError("MCP stdio client unavailable")


class Pipeline:
    class Valves(BaseModel):
        MCP_CONFIG_PATH: str = "/app/data/mcp_config.json"
        DEFAULT_MCP_SERVER: str = "healthcare_server"
        RESPONSE_TIMEOUT: int = 30
        LOG_LEVEL: str = "INFO"
        ENABLE_STREAMING: bool = True

    def __init__(self) -> None:
        self.type = "manifold"
        self.id = "mcp_pipeline"
        self.name = "MCP Pipeline"
        self.valves = self.Valves()
        self.mcp_config_path = os.getenv("MCP_CONFIG_PATH", self.valves.MCP_CONFIG_PATH)
        self.servers: dict[str, dict] = {}
        self.sessions: dict[str, Any] = {}
        # Track raw context managers so we can close them cleanly (avoid anyio cancel scope errors)
        self._client_contexts: dict[str, Any] = {}
        # tool registries
        self._tools_by_server: dict[str, List[Dict[str, Any]]] = {}
        self._tool_index: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        # Allow runtime override of log level for deep debugging (e.g., MCP_PIPELINE_LOG_LEVEL=DEBUG)
        override_level = os.getenv("MCP_PIPELINE_LOG_LEVEL") or self.valves.LOG_LEVEL
        logging.basicConfig(
            level=getattr(logging, override_level, logging.INFO),
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger("mcp-pipeline")

    async def on_startup(self) -> None:
        if not MCP_AVAILABLE:
            self.logger.warning("MCP library unavailable; running in degraded mode")
            return
        await self.load_mcp_config()
        await self.initialize_servers()
        await self.discover_all_tools()

    async def on_shutdown(self) -> None:
        # Gracefully close sessions and their underlying context managers
        for name, session in list(self.sessions.items()):
            try:
                if hasattr(session, "close"):
                    await session.close()  # type: ignore[attr-defined]
            except Exception as e:  # pragma: no cover
                self.logger.debug(f"Error closing session {name}: {e}")
            # Exit the context manager to release background tasks
            ctx = self._client_contexts.get(name)
            if ctx is not None:
                try:
                    await ctx.__aexit__(None, None, None)  # type: ignore[attr-defined]
                except Exception as e:  # pragma: no cover
                    self.logger.debug(f"Context exit failed for {name}: {e}")
        self.sessions.clear()
        self._client_contexts.clear()

    async def load_mcp_config(self) -> None:
        try:
            with open(self.mcp_config_path, "r") as f:
                cfg = json.load(f)
            self.servers = cfg.get("mcpServers", {}) or {}
            self.logger.info(f"Loaded {len(self.servers)} MCP server definitions")
        except FileNotFoundError:
            self.logger.warning(f"MCP config not found: {self.mcp_config_path}")
        except Exception as e:  # pragma: no cover
            self.logger.error(f"Config load error: {e}")

    async def initialize_servers(self) -> None:
        for name, cfg in self.servers.items():
            try:
                await self.connect_to_server(name, cfg)
            except Exception as e:  # pragma: no cover
                self.logger.error(f"Failed to init server {name}: {e}")

    async def connect_to_server(self, name: str, cfg: dict) -> None:
        """Establish stdio connection and initialize MCP session.

        Uses proper async context manager retention so background I/O tasks remain
        active until on_shutdown triggers a clean __aexit__.
        """
        if not MCP_AVAILABLE:
            return
        if name in self.sessions:
            return  # Already connected
        cmd = cfg.get("command")
        if not cmd:
            raise ValueError(f"No command for MCP server {name}")
        params = StdioServerParameters(command=cmd, args=cfg.get("args", []), env=cfg.get("env", {}))
        client_cm = stdio_client(params)  # async context manager
        # Enter context manager and retain reference for later exit
        session = await client_cm.__aenter__()  # type: ignore[attr-defined]
        self._client_contexts[name] = client_cm
        try:
            if hasattr(session, "initialize"):
                await session.initialize()  # type: ignore[attr-defined]
                # Debug: if HTTP fallback disabled, immediately probe tools/list raw
                if os.getenv("DISABLE_HTTP_FALLBACK", "0") in ("1", "true", "TRUE") and hasattr(session, "rpc"):
                    try:
                        raw_probe = await session.rpc.request("tools/list", {})  # type: ignore[attr-defined]
                        self.logger.debug(f"Raw stdio tools/list probe response: {raw_probe}")
                    except Exception as probe_err:  # pragma: no cover
                        self.logger.debug(f"Raw stdio tools/list probe error: {probe_err}")
        except Exception as e:  # pragma: no cover
            self.logger.error(f"Initialization call failed for {name}: {e}")
        self.sessions[name] = session
        self.logger.info(f"Connected to MCP server '{name}'")

    # ----------------------- Tool Discovery / Invocation -------------------- #
    async def discover_all_tools(self) -> None:
        """Discover tools from every connected MCP server.

        Populates internal registries mapping tool ids -> (server, tool_meta).
        Tool ID strategy:
          - Prefer provided 'name' field
          - If duplicate across servers, prefix with '{server}:' to disambiguate
        """
        if not self.sessions:
            return
        seen: Dict[str, int] = {}
        for server, session in self.sessions.items():
            try:
                tools = await self._list_tools(session)
                if tools:
                    self.logger.debug(f"Stdio tool discovery succeeded for {server} with {len(tools)} tools")
                else:
                    if os.getenv("DISABLE_HTTP_FALLBACK", "0") in ("1", "true", "TRUE"):
                        self.logger.warning(f"HTTP fallback disabled; zero tools from stdio for {server}")
                    else:
                        self.logger.debug(f"No tools via stdio for {server}; attempting HTTP fallback")
                        http_tools = await self._http_list_tools(server)
                        if http_tools:
                            self.logger.debug(f"HTTP fallback returned {len(http_tools)} tools for {server}")
                            tools = http_tools
            except Exception as e:  # pragma: no cover
                self.logger.error(f"Failed listing tools for {server}: {e}")
                continue
            normalized: List[Dict[str, Any]] = []
            for raw in tools:
                raw_id = raw.get("name") or raw.get("id") or raw.get("tool") or "unknown_tool"
                base_id = raw_id.replace(" ", "_")
                count = seen.get(base_id, 0)
                final_id = base_id if count == 0 else f"{server}:{base_id}"
                seen[base_id] = count + 1
                meta = {
                    "id": final_id,
                    "name": raw.get("label") or raw.get("name") or raw_id,
                    "description": raw.get("description", ""),
                    "category": raw.get("category") or "general",
                    "server": server,
                    "raw": raw,
                }
                normalized.append(meta)
                self._tool_index[final_id] = (server, meta)
            self._tools_by_server[server] = normalized
        self.logger.info(
            "Discovered %d tools across %d servers", sum(len(v) for v in self._tools_by_server.values()), len(self._tools_by_server)
        )

    async def _list_tools(self, session: Any) -> List[Dict[str, Any]]:
        """Call the MCP server to list tools.

        Supports both high-level session.list_tools() and raw rpc fallback.
        """
        if hasattr(session, "list_tools"):
            response = await session.list_tools()  # type: ignore[attr-defined]
            # Accept either list or dict structure
            if isinstance(response, list):  # legacy/simple
                return response  # type: ignore[return-value]
            if isinstance(response, dict):
                # Typical MCP python client returns {"tools": [...]}.
                for key in ("tools", "data", "items"):
                    if key in response and isinstance(response[key], list):
                        return response[key]  # type: ignore[return-value]
                # Some client libs may wrap actual result as {"result": {"tools": [...]}}
                inner = response.get("result") if isinstance(response.get("result"), dict) else None
                if inner and isinstance(inner.get("tools"), list):
                    return inner["tools"]  # type: ignore[return-value]
                self.logger.debug(f"Unexpected list_tools() response shape: {response}")
                return []
        # Fallback raw RPC
        if hasattr(session, "rpc"):
            try:
                resp = await session.rpc.request("tools/list", {})  # type: ignore[attr-defined]
                # The low-level rpc.request may return the *result* portion OR a full envelope.
                if isinstance(resp, dict):
                    # Direct result dict case {"tools": [...]}:
                    if isinstance(resp.get("tools"), list):
                        return resp.get("tools", [])  # type: ignore[return-value]
                    # Full envelope case {"jsonrpc":"2.0", "id":1, "result": {"tools": [...]}}
                    result_section = resp.get("result")
                    if isinstance(result_section, dict) and isinstance(result_section.get("tools"), list):
                        return result_section.get("tools", [])  # type: ignore[return-value]
                    self.logger.debug(f"Unexpected raw tools/list response shape: {resp}")
                if isinstance(resp, list):
                    return resp  # type: ignore[return-value]
            except Exception as e:  # pragma: no cover
                self.logger.debug(f"Raw tools/list failed: {e}")
        return []

    async def _http_list_tools(self, server: str) -> List[Dict[str, Any]]:
        """HTTP JSON-RPC fallback: POST to server's /mcp endpoint if reachable.

        Only used when stdio tool listing returns zero results (likely due to
        transport mismatch). Assumes container name == server container id.
        """
        import httpx  # local import to avoid overhead if unused
        base_host = os.getenv("HEALTHCARE_MCP_HTTP_HOST") or os.getenv("HEALTHCARE_MCP_CONTAINER", "healthcare-mcp-stdio")
        port = os.getenv("HEALTHCARE_MCP_HTTP_PORT", "3000")
        url = f"http://{base_host}:{port}/mcp"
        self.logger.debug(f"HTTP fallback request -> {url} (server={server})")
        try:
            payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.post(url, json=payload)
                if r.status_code == 200:
                    data = r.json()
                    tools = data.get("result", {}).get("tools", []) if isinstance(data, dict) else []
                    self.logger.debug(f"HTTP fallback response {len(tools)} tools for {server}")
                    return tools  # type: ignore[return-value]
                self.logger.debug(f"HTTP fallback non-200 {r.status_code} for {url}")
        except Exception as e:  # pragma: no cover
            self.logger.debug(f"HTTP fallback failed: {e}")
        return []

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return flattened tool list for external API layer."""
        result: List[Dict[str, Any]] = []
        for server_list in self._tools_by_server.values():
            result.extend(server_list)
        return result

    async def invoke_tool(self, tool_id: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Invoke a tool by id and return structured result."""
        if tool_id not in self._tool_index:
            raise ValueError(f"Unknown tool id: {tool_id}")
        
        server, meta = self._tool_index[tool_id]
        session = self.sessions.get(server)
        if not session:
            raise RuntimeError(f"Server session not found: {server}")
        
        # Get the actual tool name from the raw metadata
        raw_tool = meta["raw"]
        tool_name = raw_tool.get("name") or raw_tool.get("function", {}).get("name") or tool_id
        args_payload = arguments or {}
        
        self.logger.debug(f"Invoking tool {tool_name} on server {server} with args: {args_payload}")
        
        try:
            # Try MCP client method first
            if hasattr(session, "call_tool"):
                result = await session.call_tool(tool_name, args_payload)
                return self._normalize_tool_result(tool_id, result)
            
            # Try direct RPC call
            if hasattr(session, "request"):
                result = await session.request("tools/call", {
                    "name": tool_name,
                    "arguments": args_payload
                })
                return self._normalize_tool_result(tool_id, result)
                
            # Try session.rpc.request fallback
            if hasattr(session, "rpc") and hasattr(session.rpc, "request"):
                result = await session.rpc.request("tools/call", {
                    "name": tool_name, 
                    "arguments": args_payload
                })
                return self._normalize_tool_result(tool_id, result)
                
            # HTTP fallback for tool invocation
            return await self._http_invoke_tool(server, tool_name, args_payload, tool_id)
            
        except Exception as e:
            self.logger.error(f"Tool invocation failed for {tool_id}: {e}")
            # Try HTTP fallback
            try:
                return await self._http_invoke_tool(server, tool_name, args_payload, tool_id)
            except Exception as fallback_error:
                raise RuntimeError(f"Tool invocation failed on both stdio and HTTP: {e}, {fallback_error}")

    async def _http_invoke_tool(self, server: str, tool_name: str, arguments: Dict[str, Any], tool_id: str) -> Dict[str, Any]:
        """HTTP fallback for tool invocation"""
        import httpx
        
        base_host = os.getenv("HEALTHCARE_MCP_HTTP_HOST") or os.getenv("HEALTHCARE_MCP_CONTAINER", "healthcare-mcp-stdio")
        port = os.getenv("HEALTHCARE_MCP_HTTP_PORT", "3000")
        url = f"http://{base_host}:{port}/mcp"
        
        self.logger.debug(f"HTTP tool invocation fallback -> {url} (tool={tool_name})")
        
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    result = data.get("result", data)
                    self.logger.debug(f"HTTP tool invocation successful for {tool_name}")
                    return self._normalize_tool_result(tool_id, result)
                else:
                    raise RuntimeError(f"HTTP tool invocation failed: {response.status_code} {response.text}")
                    
        except Exception as e:
            self.logger.error(f"HTTP tool invocation failed: {e}")
            raise

    def _normalize_tool_result(self, tool_id: str, raw: Any) -> Dict[str, Any]:
        """Normalize tool result into a consistent envelope."""
        return {
            "tool_id": tool_id,
            "status": "success",
            "raw": raw,
        }

    def pipelines(self) -> List[dict]:
        return [
            {"id": "mcp-healthcare", "name": "Healthcare MCP Tools", "description": "Healthcare tools via MCP"},
            {"id": "mcp-general", "name": "General MCP Tools", "description": "General purpose MCP tool access"},
        ]

    async def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        if not MCP_AVAILABLE or not self.sessions:
            return "MCP backend not ready; tools unavailable right now."
        
        # Create healthcare session for audit trail
        healthcare_session_id = str(uuid.uuid4())
        await self._create_healthcare_session(healthcare_session_id, user_message, body)
        
        server = self.select_server(model_id)
        session = self.sessions.get(server)
        if not session:
            return f"Server '{server}' not connected"
        try:
            return await self.process_simple_query(session, user_message, healthcare_session_id)
        except Exception as e:  # pragma: no cover
            return f"Pipeline error: {e}"

    async def _create_healthcare_session(self, session_id: str, user_message: str, body: dict) -> None:
        """Create healthcare session for HIPAA audit trail"""
        try:
            import asyncpg
            import os
            from datetime import datetime
            import uuid
            
            # Connect to healthcare database using actual config
            db_host = os.getenv("POSTGRES_HOST", "172.20.0.13")
            db_port = os.getenv("POSTGRES_PORT", "5432")
            db_name = os.getenv("DATABASE_NAME", "intelluxe")
            db_user = os.getenv("POSTGRES_USER", "intelluxe")
            db_password = os.getenv("POSTGRES_PASSWORD", "secure_password_here")
            
            conn = await asyncpg.connect(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password
            )
            
            # Insert session into audit_logs table using actual schema
            log_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()
            
            await conn.execute(
                """
                INSERT INTO audit_logs (
                    log_id, user_id, user_type, action, resource_type, resource_id,
                    ip_address, user_agent, timestamp, success, session_id, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                log_id, body.get("user_id", "mcp_user"), "mcp_pipeline", "healthcare_query",
                "medical_literature", session_id, body.get("client_ip", "172.20.0.17"),
                "MCP Pipeline Healthcare AI", timestamp, True, session_id, timestamp
            )
            
            await conn.close()
            self.logger.info(f"Healthcare session {session_id} stored in audit_logs table")
            
        except Exception as e:
            self.logger.error(f"Failed to create healthcare session in database: {e}")
            # Fallback to logging for audit trail
            self.logger.info(f"AUDIT: Healthcare session {session_id} for query: {user_message[:50]}...")

    def select_server(self, model_id: str) -> str:
        if "health" in model_id.lower() and "healthcare_server" in self.servers:
            return "healthcare_server"
        if self.valves.DEFAULT_MCP_SERVER in self.servers:
            return self.valves.DEFAULT_MCP_SERVER
        return next(iter(self.servers.keys()), "healthcare_server")

    async def process_simple_query(self, session: Any, user_message: str, healthcare_session_id: str) -> str:  # noqa: D401
        """Process user query with AI-powered tool selection and invocation"""
        
        # Get available tools
        available_tools = self.list_tools()
        if not available_tools:
            return f"MCP pipeline received: {user_message}\n(No tools available)"
        
        try:
            # Use AI to select and invoke appropriate tools
            result = await self._ai_tool_invocation(user_message, available_tools, healthcare_session_id)
            return result
        except Exception as e:
            self.logger.error(f"AI tool invocation failed: {e}")
            # Fallback to tool listing
            tool_list = "\n".join([f"- {t['id']}: {t.get('description', 'No description')}" for t in available_tools[:10]])
            return f"""MCP pipeline received: {user_message}

I have {len(available_tools)} healthcare tools available:

{tool_list}

Error during AI tool selection: {e}"""

    async def _ai_tool_invocation(self, user_message: str, available_tools: List[Dict[str, Any]], session_id: str) -> str:
        """Use AI model to select and invoke appropriate tools"""
        
        # Create tool descriptions for the AI
        tool_descriptions = []
        for tool in available_tools:
            desc = f"- {tool['id']}: {tool.get('description', 'No description')}"
            if 'inputSchema' in tool:
                params = tool['inputSchema'].get('properties', {})
                if params:
                    param_names = list(params.keys())
                    desc += f" (parameters: {', '.join(param_names)})"
            tool_descriptions.append(desc)
        
        tools_text = "\n".join(tool_descriptions)
        
        # Create prompt for AI tool selection
        system_prompt = f"""You are a healthcare AI assistant with access to medical tools. 
Given a user query, select the most appropriate tool(s) and provide the parameters.

Available tools:
{tools_text}

Instructions:
1. Analyze the user's healthcare query
2. Select the most relevant tool(s) 
3. Extract appropriate parameters from the query
4. Return ONLY a JSON response with tool invocations - no markdown, no explanations, just pure JSON

Response format (JSON ONLY):
{{
    "reasoning": "Brief explanation of tool selection",
    "tools": [
        {{
            "tool_id": "selected_tool_name", 
            "parameters": {{"param1": "value1", "param2": "value2"}}
        }}
    ]
}}

If no tools are relevant, return: {{"reasoning": "explanation", "tools": []}}

IMPORTANT: Return only valid JSON, no code blocks, no markdown formatting."""

        # Try to get AI response (simplified - you might want to use your actual LLM setup)
        try:
            ai_response = await self._call_ai_model(system_prompt, user_message)
            tool_plan = json.loads(ai_response)
            
            if not tool_plan.get("tools"):
                return f"AI Analysis: {tool_plan.get('reasoning', 'No specific tools needed for this query')}\n\nOriginal query: {user_message}"
            
            # Execute the selected tools
            results = []
            for tool_call in tool_plan["tools"]:
                tool_id = tool_call["tool_id"]
                parameters = tool_call.get("parameters", {})
                
                # Add required healthcare compliance parameters
                if tool_id in ["search-pubmed", "research_medical_literature", "clinical_intake",
                               "transcribe_audio", "process_healthcare_document"]:
                    parameters["session_id"] = f"mcp_session_{hash(user_message) % 10000:04d}"

                if tool_id in ["clinical_intake", "transcribe_audio", "process_healthcare_document"]:
                    parameters["provider_id"] = "MCP_PIPELINE_AI"

                try:
                    tool_result = await self.invoke_tool(tool_id, parameters)
                    results.append(f"**{tool_id}**: {tool_result}")
                except Exception as e:
                    results.append(f"**{tool_id}** (failed): {e}")
            
            reasoning = tool_plan.get("reasoning", "Selected healthcare tools")
            combined_results = "\n\n".join(results)
            
            return f"**AI Analysis**: {reasoning}\n\n{combined_results}"
            
        except json.JSONDecodeError as e:
            return f"AI tool selection failed (JSON error): {e}\n\nFallback: Use /tools/{{tool_id}}/invoke for manual tool access"
        except Exception as e:
            return f"AI tool selection failed: {e}\n\nFallback: Use /tools/{{tool_id}}/invoke for manual tool access"

    async def _call_ai_model(self, system_prompt: str, user_message: str) -> str:
        """Call AI model for tool selection - implement your preferred LLM here"""
        
        # Option 1: Use Ollama if available locally
        try:
            import httpx
            
            # Try to call local Ollama (common healthcare AI setup)
            ollama_url = "http://172.20.0.10:11434/api/generate"  # Use Docker static IP
            
            prompt = f"{system_prompt}\n\nUser Query: {user_message}"
            
            payload = {
                "model": "llama3.1:8b",  # Use whatever model you have
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent tool selection
                    "top_p": 0.9
                }
            }
            
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(ollama_url, json=payload)
                if response.status_code == 200:
                    result = response.json()
                    raw_response = result.get("response", "")
                    # Clean up the response - remove markdown code blocks if present
                    cleaned_response = raw_response.strip()
                    if cleaned_response.startswith('```') and cleaned_response.endswith('```'):
                        cleaned_response = cleaned_response[3:-3].strip()
                    if cleaned_response.startswith('json'):
                        cleaned_response = cleaned_response[4:].strip()
                    if cleaned_response.startswith('`') and cleaned_response.endswith('`'):
                        cleaned_response = cleaned_response[1:-1].strip()
                    return cleaned_response
                    
        except Exception as e:
            self.logger.debug(f"Ollama call failed: {e}")
        
        # Option 2: Fallback to simple heuristics if no LLM available
        return await self._fallback_tool_selection(user_message, self.list_tools())

    async def _fallback_tool_selection(self, user_message: str, available_tools: List[Dict[str, Any]]) -> str:
        """Fallback tool selection using simple heuristics when no LLM is available"""
        
        query_lower = user_message.lower()
        
        # Medical literature search
        if any(keyword in query_lower for keyword in ["article", "research", "study", "paper", "literature", "cardiovascular"]):
            pubmed_tools = [t for t in available_tools if "pubmed" in t["id"].lower()]
            if pubmed_tools:
                search_terms = " ".join([word for word in user_message.split() if len(word) > 3])[:50]
                return json.dumps({
                    "reasoning": "Detected literature search request",
                    "tools": [{"tool_id": pubmed_tools[0]["id"], "parameters": {"query": search_terms, "max_results": 5}}]
                })
        
        # Drug information
        if any(keyword in query_lower for keyword in ["drug", "medication", "medicine"]):
            drug_tools = [t for t in available_tools if "drug" in t["id"].lower()]
            if drug_tools:
                # Try to extract drug name
                words = user_message.split()
                drug_name = words[-1] if words else "aspirin"
                return json.dumps({
                    "reasoning": "Detected drug information request",
                    "tools": [{"tool_id": drug_tools[0]["id"], "parameters": {"drug_name": drug_name}}]
                })
        
        # No specific tool detected
        return json.dumps({
            "reasoning": "No specific healthcare tools needed for this general query",
            "tools": []
        })


def main():  # Required entry point for Open WebUI
    return Pipeline()


if __name__ == "__main__":  # Manual smoke test
    import asyncio as _asyncio
    p = Pipeline()
    print(p.pipelines())
