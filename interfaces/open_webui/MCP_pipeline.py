"""
MCP Pipeline for Open WebUI Integration
Adapted from open-webui-tools/MCP_pipeline.py

This pipeline enables Open WebUI to communicate with MCP servers using the MCP protocol.
Place this file in your Open WebUI Pipelines directory.
"""

import asyncio
import json
import logging
import subprocess
import time
from typing import List, Union, Generator, Iterator, Dict, Any, Optional
from contextlib import asynccontextmanager

from pydantic import BaseModel

# MCP Protocol imports
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("MCP library not available. Install with: pip install mcp")


class Pipeline:
    class Valves(BaseModel):
        """Configuration for the MCP Pipeline"""

        MCP_CONFIG_PATH: str = "/home/intelluxe/interfaces/open_webui/mcp_config.json"
        DEFAULT_MCP_SERVER: str = "healthcare_server"
        RESPONSE_TIMEOUT: int = 30
        LOG_LEVEL: str = "INFO"
        ENABLE_STREAMING: bool = True

    def __init__(self):
        self.type = "manifold"
        self.id = "mcp_pipeline"
        self.name = "MCP Pipeline"
        self.valves = self.Valves()
        self.servers = {}
        self.sessions = {}

        # Set up logging
        logging.basicConfig(
            level=getattr(logging, self.valves.LOG_LEVEL),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    async def on_startup(self):
        """Initialize MCP servers on startup"""
        if not MCP_AVAILABLE:
            self.logger.error("MCP library not available")
            return

        self.logger.info("Starting MCP Pipeline...")
        await self.load_mcp_config()
        await self.initialize_servers()

    async def on_shutdown(self):
        """Clean up MCP servers on shutdown"""
        self.logger.info("Shutting down MCP Pipeline...")
        for server_name, session in self.sessions.items():
            try:
                await session.close()
                self.logger.info(f"Closed session for {server_name}")
            except Exception as e:
                self.logger.error(f"Error closing session {server_name}: {e}")

    async def load_mcp_config(self):
        """Load MCP server configurations"""
        try:
            with open(self.valves.MCP_CONFIG_PATH, "r") as f:
                config = json.load(f)
            self.servers = config.get("mcpServers", {})
            self.logger.info(f"Loaded configuration for {len(self.servers)} MCP servers")
        except FileNotFoundError:
            self.logger.error(f"MCP config file not found: {self.valves.MCP_CONFIG_PATH}")
            self.servers = {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in MCP config: {e}")
            self.servers = {}

    async def initialize_servers(self):
        """Initialize connections to MCP servers"""
        for server_name, server_config in self.servers.items():
            try:
                await self.connect_to_server(server_name, server_config)
                self.logger.info(f"Connected to MCP server: {server_name}")
            except Exception as e:
                self.logger.error(f"Failed to connect to {server_name}: {e}")

    async def connect_to_server(self, server_name: str, server_config: dict):
        """Connect to a specific MCP server"""
        command = server_config.get("command")
        args = server_config.get("args", [])
        env = server_config.get("env", {})

        if not command:
            raise ValueError(f"No command specified for server {server_name}")

        # Create server parameters
        server_params = StdioServerParameters(command=command, args=args, env=env)

        # Connect using stdio
        session = await stdio_client(server_params)
        self.sessions[server_name] = session

        # Initialize the session
        await session.initialize()

    def pipelines(self) -> List[dict]:
        """Return available pipeline models"""
        return [
            {
                "id": "mcp-healthcare",
                "name": "Healthcare MCP Tools",
                "description": "Access to healthcare tools via MCP protocol",
            },
            {
                "id": "mcp-general",
                "name": "General MCP Tools",
                "description": "General purpose MCP tool access",
            },
        ]

    async def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        """Main pipeline processing function"""
        self.logger.info(f"Processing request for model: {model_id}")

        if not MCP_AVAILABLE:
            return "MCP library not available. Please install with: pip install mcp"

        if not self.sessions:
            return "No MCP servers available. Please check configuration."

        # Select server based on model_id
        server_name = self.select_server(model_id)
        if server_name not in self.sessions:
            return f"MCP server '{server_name}' not available"

        session = self.sessions[server_name]

        try:
            # Determine if this requires tool usage
            if await self.should_use_tools(user_message):
                return await self.process_with_tools(session, user_message, messages)
            else:
                return await self.process_simple_query(session, user_message)

        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            return f"Error processing request: {str(e)}"

    def select_server(self, model_id: str) -> str:
        """Select appropriate MCP server based on model ID"""
        if "healthcare" in model_id.lower():
            return "healthcare_server"
        elif self.valves.DEFAULT_MCP_SERVER in self.servers:
            return self.valves.DEFAULT_MCP_SERVER
        elif self.servers:
            return list(self.servers.keys())[0]
        else:
            return "healthcare_server"  # fallback

    async def should_use_tools(self, message: str) -> bool:
        """Determine if the message requires tool usage"""
        tool_keywords = [
            "search",
            "find",
            "lookup",
            "get",
            "fetch",
            "retrieve",
            "pubmed",
            "clinical trial",
            "drug",
            "fda",
            "medical",
            "research",
            "study",
            "treatment",
            "medication",
        ]

        message_lower = message.lower()
        return any(keyword in message_lower for keyword in tool_keywords)

    async def process_with_tools(
        self, session: ClientSession, user_message: str, messages: List[dict]
    ) -> str:
        """Process request that requires MCP tools"""
        try:
            # List available tools
            tools_response = await session.list_tools()
            available_tools = {tool.name: tool for tool in tools_response.tools}

            if not available_tools:
                return "No tools available from MCP server"

            # Select appropriate tool based on message content
            tool_name = self.select_tool(user_message, available_tools)

            if not tool_name:
                return "No appropriate tool found for this request"

            # Prepare tool arguments
            tool_args = self.prepare_tool_arguments(user_message, tool_name)

            # Call the tool
            self.logger.info(f"Calling tool: {tool_name} with args: {tool_args}")
            tool_result = await session.call_tool(tool_name, tool_args)

            # Format the response
            return self.format_tool_response(tool_result, tool_name)

        except Exception as e:
            self.logger.error(f"Tool processing error: {e}")
            return f"Error using tools: {str(e)}"

    async def process_simple_query(self, session: ClientSession, user_message: str) -> str:
        """Process simple queries without tools"""
        return f"Healthcare MCP server received: {user_message}\n\nThis appears to be a general query. For healthcare-specific searches, try queries like:\n- 'Search PubMed for diabetes research'\n- 'Find clinical trials for cancer treatment'\n- 'Get FDA drug information for aspirin'"

    def select_tool(self, message: str, available_tools: dict) -> Optional[str]:
        """Select the most appropriate tool for the message"""
        message_lower = message.lower()

        # Healthcare-specific tool selection
        if any(word in message_lower for word in ["pubmed", "research", "study", "literature"]):
            return "search-pubmed" if "search-pubmed" in available_tools else None
        elif any(word in message_lower for word in ["clinical trial", "trial", "study"]):
            return "search-trials" if "search-trials" in available_tools else None
        elif any(word in message_lower for word in ["drug", "medication", "fda"]):
            return "get-drug-info" if "get-drug-info" in available_tools else None

        # Fallback to first available tool
        return list(available_tools.keys())[0] if available_tools else None

    def prepare_tool_arguments(self, message: str, tool_name: str) -> dict:
        """Prepare arguments for tool calls based on the message"""
        # Extract key terms from the message
        if tool_name == "search-pubmed":
            # Extract search terms for PubMed
            return {"query": message, "max_results": 10}
        elif tool_name == "search-trials":
            # Extract search terms for clinical trials
            return {"condition": message, "status": "recruiting"}
        elif tool_name == "get-drug-info":
            # Extract drug name
            words = message.split()
            drug_words = [
                w for w in words if w.lower() not in ["get", "info", "about", "drug", "medication"]
            ]
            drug_name = " ".join(drug_words) if drug_words else message
            return {"drug_name": drug_name}
        else:
            return {"query": message}

    def format_tool_response(self, tool_result: Any, tool_name: str) -> str:
        """Format the tool response for display"""
        try:
            if hasattr(tool_result, "content") and tool_result.content:
                content = (
                    tool_result.content[0]
                    if isinstance(tool_result.content, list)
                    else tool_result.content
                )

                if hasattr(content, "text"):
                    return content.text
                elif isinstance(content, str):
                    return content
                else:
                    return str(content)
            else:
                return f"Tool {tool_name} completed successfully but returned no content"

        except Exception as e:
            self.logger.error(f"Error formatting response: {e}")
            return f"Tool {tool_name} completed but response formatting failed: {str(e)}"


# Required for Open WebUI Pipelines
def main():
    return Pipeline()


if __name__ == "__main__":
    # For testing purposes
    pipeline = Pipeline()
    print(f"MCP Pipeline initialized: {pipeline.name}")
    print(f"Available models: {pipeline.pipelines()}")
