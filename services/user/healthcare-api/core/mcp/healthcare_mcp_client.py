"""
Healthcare MCP Client for stdio communication with healthcare-mcp server
Stateless wrapper that opens a short-lived stdio session per call to avoid AnyIO
cancel-scope issues on __aexit__ and to ensure clean shutdown without Ctrl+C.

Logs are routed through the healthcare-compliant logger so they appear in logs/.
"""
from typing import Any

from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("infrastructure.mcp")


class HealthcareMCPClient:
    """Lightweight MCP client using short-lived stdio sessions per request."""

    def __init__(self, server_command: str | None = None):
        # Import here to keep symbols bound even if library isn't installed at import-time
        try:
            from mcp import StdioServerParameters  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"MCP library not available: {e}")

        # NEW: Use subprocess spawning for single-container architecture
        import os
        mcp_server_path = os.getenv("MCP_SERVER_PATH", "/app/mcp-server/build/index.js")
        
        # Check if we're in combined container mode
        if os.path.exists(mcp_server_path):
            # Single container: spawn MCP server as subprocess
            logger.info(f"Using single-container MCP server at {mcp_server_path}")
            command = "node"
            args = [mcp_server_path]
            
            # Use the same environment variables as the original healthcare-mcp.conf
            env = {
                "MCP_TRANSPORT": "stdio-only",
                "NO_COLOR": "1",
                "FHIR_BASE_URL": os.getenv("FHIR_BASE_URL", "http://172.20.0.13:5432"),
                "PUBMED_API_KEY": os.getenv("PUBMED_API_KEY", "test"),
                "CLINICALTRIALS_API_KEY": os.getenv("CLINICALTRIALS_API_KEY", "test"),
                # Inherit additional environment variables from container
                "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "postgresql"),
                "REDIS_HOST": os.getenv("REDIS_HOST", "redis"),
                "ENVIRONMENT": os.getenv("ENVIRONMENT", "development"),
                "LOG_LEVEL": os.getenv("LOG_LEVEL", "info")
            }
            logger.info(f"MCP environment configured with API keys and service URLs: {list(env.keys())}")
        else:
            # Fallback to docker exec for backwards compatibility
            logger.warning("MCP server not found locally, falling back to docker exec")
            mode = (server_command or "docker").strip().lower()
            if mode in {"host", "host-node", "node", "bash"}:
                # Only use host-node direct mode if explicitly requested
                command = "bash"
                sh_cmd = """
                set -e
                docker cp healthcare-mcp:/app/build/stdio_entry.js /tmp/stdio_entry_temp.js 2>/dev/null || true
                export MCP_TRANSPORT=stdio-only
                export NO_COLOR=1
                node /tmp/stdio_entry_temp.js 2>/tmp/mcp_direct.err
                """
                args = ["-c", sh_cmd]
                env = {"NO_COLOR": "1"}
            else:
                # Real server inside docker container
                command = "docker"
                sh_cmd = "node /app/build/stdio_entry.js 2> /app/logs/mcp_stdio_entry.err"
                args = [
                    "exec",
                    "-i",
                    "-u",
                    "node",
                    "-e",
                    "MCP_TRANSPORT=stdio-only",
                    "-e",
                    "NO_COLOR=1",
                    "healthcare-mcp",
                    "sh",
                    "-c",
                    sh_cmd,
                ]
                env = {"NO_COLOR": "1"}

        self.params = StdioServerParameters(command=command, args=args, env=env)
        # Compatibility attribute so existing code won't try to lazy-connect
        self.session = True  # truthy sentinel

    async def _ensure_connected(self) -> None:
        """Compatibility no-op: sessions are established per-call."""
        await self.connect()

    async def connect(self) -> None:
        """No-op connect for compatibility (sessions are created per call)."""
        logger.info(
            "MCP stateless client ready (per-call sessions)",
            extra={
                "healthcare_context": {
                    "operation_type": "mcp_connect",
                    "command": self.params.command,
                    "args": self.params.args,
                    "env_keys": sorted(list(getattr(self.params, "env", {}).keys())),
                },
            },
        )

    async def get_available_tools(self) -> list[dict[str, Any]]:
        """List available tools using a short-lived session with timeouts."""
        import asyncio
        logger.info("Listing MCP tools via short-lived session")
        tools: list[dict[str, Any]] = []
        # Open, list, close in the same task to avoid cancel-scope issues
        from mcp import ClientSession  # type: ignore
        from mcp.client.stdio import stdio_client  # type: ignore
        try:
            async with stdio_client(self.params) as (read_stream, write_stream):
                session = ClientSession(read_stream, write_stream)
                # Guard initialization and list with timeouts to avoid hangs
                await asyncio.wait_for(session.initialize(), timeout=45)
                tools_response = await asyncio.wait_for(session.list_tools(), timeout=45)
                if hasattr(tools_response, "tools"):
                    tools = tools_response.tools  # type: ignore[assignment]
                elif isinstance(tools_response, dict):
                    tools = tools_response.get("tools", [])  # type: ignore[assignment]
            logger.info(f"Discovered {len(tools)} MCP tools")
        except TimeoutError:
            logger.error(
                "Timeout while listing MCP tools (possible stdout banner contamination). Ensure the MCP stdio server does not print human-readable logs to stdout; use stderr for banners.",
                extra={
                    "healthcare_context": {
                        "operation_type": "mcp_list_tools_timeout",
                        "hint": "Move any 'STDIO server ready...' or startup banners to stderr when MCP_TRANSPORT=stdio",
                    },
                },
            )
        except Exception as e:  # pragma: no cover
            logger.exception(
                f"Error listing MCP tools: {e}",
                extra={"healthcare_context": {"operation_type": "mcp_list_tools_error", "error": str(e)}},
            )
        return tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Call a tool using a short-lived session and return a wrapped result."""
        import asyncio
        import subprocess
        import tempfile
        import os
        args = arguments or {}
        logger.info(f"MCP call start: tool={tool_name} args_keys={list(args.keys())}")

        # CRITICAL DEBUG: Check our environment and paths
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Environment PATH: {os.environ.get('PATH', 'NOT_SET')}")
        logger.info("Node.js availability check...")
        
        # Test Node.js availability
        try:
            node_test = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
            logger.info(f"Node.js version: {node_test.stdout.strip()}")
            if node_test.returncode != 0:
                logger.error(f"Node.js test failed with return code {node_test.returncode}")
                logger.error(f"Node.js stderr: {node_test.stderr}")
        except Exception as e:
            logger.error(f"Node.js not available: {e}")
            
        # Test MCP server file existence
        mcp_server_path = os.getenv("MCP_SERVER_PATH", "/app/mcp-server/build/index.js")
        logger.info(f"Checking MCP server at: {mcp_server_path}")
        if os.path.exists(mcp_server_path):
            logger.info(f"MCP server file exists, size: {os.path.getsize(mcp_server_path)} bytes")
            try:
                with open(mcp_server_path, 'r') as f:
                    first_line = f.readline().strip()
                    logger.info(f"MCP server first line: {first_line}")
            except Exception as e:
                logger.error(f"Cannot read MCP server file: {e}")
        else:
            logger.error(f"MCP server file not found at {mcp_server_path}")
            # List the directory contents
            try:
                parent_dir = os.path.dirname(mcp_server_path)
                if os.path.exists(parent_dir):
                    contents = os.listdir(parent_dir)
                    logger.info(f"Contents of {parent_dir}: {contents}")
                else:
                    logger.error(f"Parent directory {parent_dir} does not exist")
            except Exception as e:
                logger.error(f"Cannot list directory: {e}")

        max_retries = 3
        last_exception = None

        for attempt in range(max_retries):
            logger.info(f"MCP attempt {attempt + 1}/{max_retries}: command='{self.params.command}' args={self.params.args}")
            logger.info(f"MCP environment variables: {self.params.env}")
            
            # Test basic subprocess startup
            test_process = None
            try:
                logger.info(f"Testing subprocess spawn: {self.params.command} {' '.join(self.params.args)}")
                
                # Build full environment
                full_env = {**os.environ, **(self.params.env or {})}
                logger.info(f"Full environment for subprocess: {list(full_env.keys())}")
                
                test_process = subprocess.Popen(
                    [self.params.command] + self.params.args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=full_env,
                    text=True,
                    cwd=os.getcwd()
                )
                
                logger.info(f"Subprocess PID: {test_process.pid}")
                
                # Give it 3 seconds to start and check status
                await asyncio.sleep(3)
                return_code = test_process.poll()
                
                if return_code is not None:
                    # Process exited - capture output
                    try:
                        stdout, stderr = test_process.communicate(timeout=10)
                        logger.error(f"MCP subprocess exited with code {return_code}")
                        logger.error(f"MCP stdout: {stdout[:1000]}...")  # First 1000 chars
                        logger.error(f"MCP stderr: {stderr[:1000]}...")  # First 1000 chars
                    except subprocess.TimeoutExpired:
                        logger.error("Failed to get subprocess output (timeout)")
                        test_process.kill()
                else:
                    logger.info("MCP subprocess started successfully and is running")
                    # Kill the test process
                    test_process.terminate()
                    try:
                        test_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        test_process.kill()
                        
            except Exception as e:
                logger.error(f"Failed to test subprocess startup: {e}")
                import traceback
                logger.error(f"Subprocess startup traceback: {traceback.format_exc()}")
            finally:
                if test_process and test_process.poll() is None:
                    try:
                        test_process.terminate()
                        test_process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        try:
                            test_process.kill()
                        except Exception:
                            pass

            try:
                from mcp import ClientSession  # type: ignore
                from mcp.client.stdio import stdio_client  # type: ignore
                
                logger.info(f"Starting MCP stdio client with env: {self.params.env}")
                async with stdio_client(self.params) as (read_stream, write_stream):
                    logger.info("MCP stdio streams established")
                    session = ClientSession(read_stream, write_stream)
                    logger.info("MCP session created, initializing...")
                    await asyncio.wait_for(session.initialize(), timeout=45)
                    logger.info(f"MCP session initialized, calling tool {tool_name} with args: {args}")
                    result = await asyncio.wait_for(session.call_tool(tool_name, args), timeout=90)
                    logger.info(f"MCP tool call completed, result type: {type(result)}")
                    
                    # Log result details
                    if isinstance(result, dict):
                        logger.info(f"MCP result keys: {list(result.keys())}")
                        if 'error' in result:
                            logger.error(f"MCP tool returned error: {result.get('error')}")
                    else:
                        logger.info(f"MCP result: {str(result)[:200]}...")  # First 200 chars

                # After context closes cleanly, log a compact preview
                preview = None
                try:
                    if isinstance(result, dict):
                        preview = {k: (len(v) if isinstance(v, list) else type(v).__name__) for k, v in result.items() if k in ("articles", "count", "status")}
                    else:
                        preview = str(type(result))
                except Exception:
                    preview = "unavailable"

                logger.info(f"MCP call done: tool={tool_name} preview={preview} attempt={attempt + 1}")
                return {"status": "success", "result": result}

            except TimeoutError as e:
                last_exception = e
                logger.error(
                    f"Timeout calling tool {tool_name} on attempt {attempt + 1}/{max_retries}. Retrying...",
                    extra={
                        "healthcare_context": {
                            "operation_type": "mcp_call_timeout",
                            "tool": tool_name,
                            "hint": "No human-readable logs on stdout in stdio mode",
                            "attempt": attempt + 1,
                        },
                    },
                )
            except Exception as e:  # pragma: no cover
                last_exception = e
                # This will catch the WriteUnixTransport error
                logger.exception(
                    f"Failed to call tool {tool_name} on attempt {attempt + 1}/{max_retries}: {e}. Retrying...",
                    extra={"healthcare_context": {"operation_type": "mcp_call_error", "tool": tool_name, "error": str(e), "attempt": attempt + 1}},
                )

            if attempt < max_retries - 1:
                await asyncio.sleep(2)  # Wait 2 seconds before retrying

        logger.error(f"MCP call failed after {max_retries} attempts for tool {tool_name}.", extra={"healthcare_context": {"operation_type": "mcp_call_failed", "tool": tool_name, "final_error": str(last_exception)}})

        if isinstance(last_exception, asyncio.TimeoutError):
            return {"status": "error", "error": "timeout"}

        return {"status": "error", "error": str(last_exception)}

    async def call_healthcare_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Healthcare convenience wrapper returning raw result or error payload."""
        result = await self.call_tool(tool_name, arguments)
        if result.get("status") == "success":
            return result.get("result", {})
        return {"error": result.get("error", "Unknown error"), "status": "error"}

    async def disconnect(self) -> None:
        """No-op disconnect for compatibility (nothing persistent to close)."""
        logger.info("MCP stateless client disconnect (no persistent session)")
