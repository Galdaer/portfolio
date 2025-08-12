#!/usr/bin/env python3
"""
Intelluxe AI - Healthcare AI System Stdio Bridge

Privacy-First Healthcare AI System built for on-premise clinical deployment.
Focus: Administrative/documentation support, NOT medical advice.

MEDICAL DISCLAIMER: This system provides administrative and documentation support only.
It does not provide medical advice, diagnosis, or treatment recommendations.
All medical decisions should be made by qualified healthcare professionals.
"""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path

from config.app import config
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    log_healthcare_event,
    setup_healthcare_logging,
)

# Setup healthcare-compliant logging infrastructure
setup_healthcare_logging(log_level=config.log_level.upper())

# Get healthcare logger for main application
logger = get_healthcare_logger("main")


async def stdio_bridge():
    """Stdio bridge to delegate requests to existing agents."""
    logger.info("Starting healthcare-api stdio bridge")
    
    # Initialize agents dynamically
    try:
        import importlib
        import inspect
        from pathlib import Path
        from agents import BaseHealthcareAgent
        from core.dependencies import HealthcareServices, get_mcp_client
        
        # Initialize healthcare services
        healthcare_services = HealthcareServices()
        await healthcare_services.initialize()
        
        # Get real MCP client and LLM client from healthcare services
        mcp_client = await get_mcp_client()
        llm_client = healthcare_services.llm_client
        
        # Dynamically discover and load all healthcare agents
        agents_dir = Path(__file__).parent / "agents"
        discovered_agents = {}
        
        for agent_module_dir in agents_dir.iterdir():
            if agent_module_dir.is_dir() and not agent_module_dir.name.startswith("__"):
                # Look for agent files in each subdirectory
                for agent_file in agent_module_dir.glob("*agent*.py"):
                    if agent_file.name.startswith("__"):
                        continue
                        
                    try:
                        # Import the module dynamically
                        module_path = f"agents.{agent_module_dir.name}.{agent_file.stem}"
                        module = importlib.import_module(module_path)
                        
                        # Find all classes that inherit from BaseHealthcareAgent
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if (issubclass(obj, BaseHealthcareAgent)
                                and obj != BaseHealthcareAgent
                                and hasattr(obj, '__module__')
                                and obj.__module__ == module_path):
                                
                                # Instantiate the agent
                                agent_instance = obj(mcp_client, llm_client)
                                agent_name = getattr(agent_instance, 'agent_name', name.lower())
                                discovered_agents[agent_name] = agent_instance
                                logger.info(f"Discovered and loaded agent: {agent_name}")
                                
                    except Exception as e:
                        logger.warning(f"Failed to load agent from {agent_file}: {e}")
        
        if not discovered_agents:
            logger.warning("No agents discovered, falling back to manual imports")
            # Fallback to manual imports if discovery fails
            from agents.intake.intake_agent import HealthcareIntakeAgent
            from agents.document_processor.document_processor import HealthcareDocumentProcessor
            from agents.research_assistant.clinical_research_agent import ClinicalResearchAgent
            
            discovered_agents = {
                "intake": HealthcareIntakeAgent(mcp_client, llm_client),
                "document_processor": HealthcareDocumentProcessor(mcp_client, llm_client),
                "research_assistant": ClinicalResearchAgent(mcp_client, llm_client)
            }
        
        logger.info(f"Healthcare agents initialized: {list(discovered_agents.keys())}")
        
    except Exception as e:
        logger.error(f"Failed to initialize agents: {e}")
        return
    
    logger.info("Healthcare-api stdio bridge ready - waiting for requests")
    
    while True:
        try:
            # Read JSON-RPC request from stdin
            line = sys.stdin.readline()
            if not line:
                # Don't exit on EOF - keep waiting for new connections
                await asyncio.sleep(0.1)
                continue
                
            request = json.loads(line.strip())
            method = request.get("method", "")
            params = request.get("params", {})
            request_id = request.get("id")
            
            logger.info(f"Processing stdio request: method={method}, id={request_id}")
            
            # AI-powered intelligent routing - let AI decide everything
            result = None
            if method == "process_message":
                # Extract message and context
                message = params.get("message", "") if isinstance(params, dict) else str(params)
                user_id = params.get("user_id", "stdio_user") if isinstance(params, dict) else "stdio_user"
                session_id = params.get("session_id", "stdio_session") if isinstance(params, dict) else "stdio_session"
                
                # Use AI LLM to determine which agent and method to use
                available_agents = list(discovered_agents.keys())
                routing_prompt = f"""
                Analyze this healthcare message and determine the best agent to handle it:
                
                Message: "{message}"
                
                Available agents: {available_agents}
                
                Agent capabilities:
                - research_assistant: medical research, literature, clinical trials, drug info
                - intake: patient intake, symptoms, medical history, triage
                - document_processor: document processing, analysis, extraction
                - insurance_verification: insurance verification, benefits, prior auth (if available)
                
                Respond with only the agent name (e.g., "research_assistant")
                """
                
                try:
                    # Get all available methods for all agents dynamically
                    agent_methods = {}
                    for agent_name, agent in discovered_agents.items():
                        methods = [
                            method for method in dir(agent)
                            if callable(getattr(agent, method))
                            and not method.startswith('_')
                            and method not in ['log_agent_performance', 'initialize_agent', 'cleanup']
                        ]
                        agent_methods[agent_name] = methods
                    
                    # Use real LLM client for AI routing decisions
                    routing_prompt = f"""
                    Analyze this healthcare message and determine the best agent and method to handle it:
                    
                    Message: "{message}"
                    
                    Available agents and their methods: {agent_methods}
                    
                    Respond with only: agent_name.method_name (e.g., "research_assistant.process_research_query")
                    """
                    
                    # Use healthcare-api's LLM client for routing decisions
                    try:
                        completion = await llm_client.chat(
                            model="llama3.1:8b",
                            messages=[
                                {"role": "system", "content": "You are an AI routing assistant for healthcare agents. Respond with only the agent_name.method_name format."},
                                {"role": "user", "content": routing_prompt}
                            ],
                            options={
                                "temperature": 0.1,
                                "num_predict": 50
                            }
                        )
                        routing_decision = completion['message']['content'].strip()
                        logger.info(f"AI routing decision: {routing_decision}")
                    except Exception as e:
                        logger.error(f"LLM routing failed: {e}, using fallback")
                        routing_decision = f"{list(discovered_agents.keys())[0]}.process_request"
                    
                    # Parse agent and method from AI response
                    if '.' in routing_decision:
                        selected_agent_name, selected_method = routing_decision.split('.', 1)
                    else:
                        # Fallback: assume it's just agent name, use first available method
                        selected_agent_name = routing_decision
                        if selected_agent_name in agent_methods and agent_methods[selected_agent_name]:
                            selected_method = agent_methods[selected_agent_name][0]
                        else:
                            selected_method = "process_request"  # Fallback method
                    
                    # Execute the AI's routing decision dynamically
                    if selected_agent_name in discovered_agents:
                        selected_agent = discovered_agents[selected_agent_name]
                        
                        if hasattr(selected_agent, selected_method):
                            method_func = getattr(selected_agent, selected_method)
                            
                            # Dynamically determine method signature and call appropriately
                            import inspect
                            sig = inspect.signature(method_func)
                            params_list = list(sig.parameters.keys())
                            
                            # Smart parameter mapping based on method signature
                            if 'query' in params_list:
                                result = await method_func(message, user_id, session_id)
                            elif 'request' in params_list:
                                result = await method_func({
                                    "message": message,
                                    "user_id": user_id,
                                    "session_id": session_id
                                })
                            elif len(params_list) >= 3:  # Assume message, user_id, session_id
                                result = await method_func(message, user_id, session_id)
                            elif len(params_list) >= 1:  # Assume single parameter
                                result = await method_func({
                                    "message": message,
                                    "user_id": user_id,
                                    "session_id": session_id
                                })
                            else:
                                result = await method_func()
                        else:
                            result = {"error": f"Agent {selected_agent_name} has no method {selected_method}"}
                    else:
                        # Fallback to first available agent and method
                        fallback_agent_name = next(iter(discovered_agents.keys()))
                        fallback_agent = discovered_agents[fallback_agent_name]
                        fallback_method = agent_methods[fallback_agent_name][0] if agent_methods[fallback_agent_name] else "process_request"
                        
                        if hasattr(fallback_agent, fallback_method):
                            method_func = getattr(fallback_agent, fallback_method)
                            import inspect
                            sig = inspect.signature(method_func)
                            params_list = list(sig.parameters.keys())
                            
                            if 'query' in params_list or len(params_list) >= 3:
                                result = await method_func(message, user_id, session_id)
                            else:
                                result = await method_func({
                                    "message": message,
                                    "user_id": user_id,
                                    "session_id": session_id
                                })
                        else:
                            result = {"error": "No compatible methods found"}
                        
                except Exception as e:
                    logger.error(f"AI routing failed: {e}, falling back to first available agent")
                    # Emergency fallback
                    fallback_agent = next(iter(discovered_agents.values()))
                    fallback_methods = [
                        method for method in dir(fallback_agent)
                        if callable(getattr(fallback_agent, method))
                        and not method.startswith('_')
                    ]
                    
                    if fallback_methods:
                        fallback_method = fallback_methods[0]
                        try:
                            method_func = getattr(fallback_agent, fallback_method)
                            result = await method_func({
                                "message": message,
                                "user_id": user_id,
                                "session_id": session_id
                            })
                        except Exception:
                            result = {"error": f"Complete routing failure: {str(e)}"}
                    else:
                        result = {"error": f"No methods available: {str(e)}"}
            else:
                result = {"error": f"Unknown method: {method}. Use 'process_message' for AI routing."}
            
            # Send JSON-RPC response to stdout
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            print(json.dumps(response), flush=True)
            logger.info(f"Sent response for request {request_id}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in stdio request: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"}
            }
            print(json.dumps(error_response), flush=True)
            
        except Exception as e:
            logger.error(f"Error processing stdio request: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if 'request' in locals() else None,
                "error": {"code": -1, "message": str(e)}
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Healthcare AI Stdio Bridge")
    parser.add_argument("--stdio", action="store_true", help="Run as stdio bridge (default)")
    args = parser.parse_args()

    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)

    # Always run as stdio bridge (no HTTP mode)
    asyncio.run(stdio_bridge())
