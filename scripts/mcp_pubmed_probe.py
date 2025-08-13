"""
Quick MCP connectivity and logging probe.

Actions:
- Initializes healthcare logging (writes to logs/healthcare_system.log).
- Connects to the healthcare MCP stdio server using HealthcareMCPClient.
- Lists available tools and prints a compact summary.
- If a PubMed-like tool is found (name contains "pubmed"), calls it with a tiny query.

This is a non-production diagnostic helper.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
import shutil
import subprocess
import traceback


def add_project_path() -> None:
    # Ensure we can import from services/user/healthcare-api
    repo_root = Path(__file__).resolve().parents[1]
    api_path = repo_root / "services" / "user" / "healthcare-api"
    if str(api_path) not in sys.path:
        sys.path.insert(0, str(api_path))


async def main() -> int:
    add_project_path()
    from core.infrastructure.healthcare_logger import setup_healthcare_logging, logging
    from core.mcp.healthcare_mcp_client import HealthcareMCPClient

    # Initialize logging to logs/
    setup_healthcare_logging(Path("logs"))
    log = logging.getLogger("healthcare.diag.mcp_probe")

    log.info("Starting MCP connectivity probe", extra={"healthcare_context": {"operation_type": "mcp_probe_start"}})

    # Preflight: Docker available and container running
    docker_path = shutil.which("docker")
    if not docker_path:
        msg = "Docker not found in PATH; cannot exec healthcare-mcp"
        log.error(msg)
        print(f"PRECHECK ERROR: {msg}")
        return 2

    try:
        ps = subprocess.run([docker_path, "ps", "--format", "{{.Names}}"], capture_output=True, text=True, timeout=6)
        names = ps.stdout.strip().splitlines() if ps.returncode == 0 else []
        if "healthcare-mcp" not in names:
            msg = "Container 'healthcare-mcp' is not running"
            log.error(msg, extra={"healthcare_context": {"docker_ps_rc": ps.returncode, "stdout": ps.stdout[-400:], "stderr": ps.stderr[-400:]}})
            print(f"PRECHECK ERROR: {msg}")
            return 2
    except Exception as e:
        log.error("Docker preflight failed", extra={"healthcare_context": {"error": str(e)}})
        print(f"PRECHECK ERROR: {e}")
        return 2

    try:
        client = HealthcareMCPClient()
    except Exception as e:
        log.error("Failed to initialize HealthcareMCPClient", extra={"healthcare_context": {"error": str(e)}})
        print(f"INIT ERROR: {e}")
        return 2

    try:
        await client.connect()
    except Exception as e:
        log.error("Failed to connect to MCP server", extra={"healthcare_context": {"error": str(e)}})
        print(f"CONNECT ERROR: {e}")
        return 3

    try:
        # Apply an upper-bound timeout around discovery to avoid hanging
        tools = await asyncio.wait_for(client.get_available_tools(), timeout=60)
        names = [getattr(t, "name", str(t)) for t in tools]
        print(f"TOOLS ({len(names)}): {names}")
        if len(names) == 0:
            print("No tools discovered; showing recent healthcare-mcp logs for diagnostics...")
            try:
                out = subprocess.run([docker_path, "logs", "--since", "2m", "--tail", "200", "healthcare-mcp"], capture_output=True, text=True, timeout=8)
                print("---- healthcare-mcp recent logs ----")
                print(out.stdout[-4000:])
                if out.stderr:
                    print("---- healthcare-mcp recent errors ----")
                    print(out.stderr[-2000:])
            except Exception as log_err:
                print(f"WARN: failed to fetch container logs: {log_err}")
        log.info("Tool discovery complete", extra={"healthcare_context": {"operation_type": "mcp_probe_tools", "tool_count": len(names)}})
        # Try to find a PubMed-like tool
        pubmed_tool = next((n for n in names if isinstance(n, str) and "pubmed" in n.lower()), None)
        if pubmed_tool:
            print(f"Calling tool: {pubmed_tool}")
            res = await asyncio.wait_for(
                client.call_healthcare_tool(pubmed_tool, {"query": "asthma risk factors", "max_results": 3}),
                timeout=60,
            )
            preview = res
            if isinstance(res, dict):
                preview = {k: (len(v) if isinstance(v, list) else type(v).__name__) for k, v in res.items() if k in ("articles", "count", "status")}
            print(f"RESULT PREVIEW: {preview}")
    except asyncio.TimeoutError as e:
        log.error("Probe timeout", extra={"healthcare_context": {"error": str(e)}})
        print("ERROR: Probe timed out while communicating with MCP.")
        traceback.print_exception(type(e), e, e.__traceback__)
        # Tail container logs for hints
        try:
            out = subprocess.run([docker_path, "logs", "--since", "2m", "--tail", "200", "healthcare-mcp"], capture_output=True, text=True, timeout=8)
            print("---- healthcare-mcp recent logs ----")
            print(out.stdout[-4000:])
            if out.stderr:
                print("---- healthcare-mcp recent errors ----")
                print(out.stderr[-2000:])
        except Exception as log_err:
            print(f"WARN: failed to fetch container logs: {log_err}")
    except BaseException as e:
        # Catch-all with rich diagnostics, including ExceptionGroup-like structures
        ctx = {"error": str(e), "type": type(e).__name__}
        if hasattr(e, "exceptions") and isinstance(getattr(e, "exceptions"), list):
            ctx["exception_count"] = str(len(getattr(e, "exceptions")))
        log.error("Probe failed", extra={"healthcare_context": ctx})
        print(f"ERROR: {type(e).__name__}: {e}")
        traceback.print_exception(type(e), e, e.__traceback__)
        # If it's a grouped error, print inner ones
        inner = getattr(e, "exceptions", None)
        if isinstance(inner, list):
            for i, ex in enumerate(inner, 1):
                print(f"-- Sub-exception {i}: {type(ex).__name__}: {ex}")
                traceback.print_exception(type(ex), ex, ex.__traceback__)
        # Tail container logs for hints
        try:
            out = subprocess.run([docker_path, "logs", "--since", "2m", "--tail", "200", "healthcare-mcp"], capture_output=True, text=True, timeout=8)
            print("---- healthcare-mcp recent logs ----")
            print(out.stdout[-4000:])
            if out.stderr:
                print("---- healthcare-mcp recent errors ----")
                print(out.stderr[-2000:])
        except Exception as log_err:
            print(f"WARN: failed to fetch container logs: {log_err}")
    finally:
        await client.disconnect()
        log.info("Probe complete", extra={"healthcare_context": {"operation_type": "mcp_probe_end"}})

    return 0


if __name__ == "__main__":
    try:
        code = asyncio.run(main())
    except KeyboardInterrupt:
        code = 130
    sys.exit(code)
