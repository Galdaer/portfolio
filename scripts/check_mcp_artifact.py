"""
Check for MCP build artifact and print guidance.
Run: python3 scripts/check_mcp_artifact.py
"""

from pathlib import Path

MCP_STDIO = Path("services/user/healthcare-mcp/build/stdio_entry.js")

if MCP_STDIO.exists():
    print("✅ MCP stdio_entry.js found:", MCP_STDIO)
else:
    print("❌ MCP stdio_entry.js not found at:", MCP_STDIO)
    print("Hint: Build the healthcare-mcp project to enable MCP tools.")
    print(" - See docs/DOCKER_MCP_INSTRUCTIONS.md or services/user/healthcare-mcp/README.md")
