#!/usr/bin/env python3
"""
Minimal LangChain Agent Test - Nuclear Option
"""
import asyncio
import sys
import os

# Add the healthcare-api to the path
sys.path.insert(0, '/home/intelluxe/services/user/healthcare-api')

async def test_minimal_agent():
    """Test with the minimal nuclear option agent"""
    try:
        from langchain.agents import AgentExecutor, create_structured_chat_agent
        from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_ollama import ChatOllama
        from langchain.tools import Tool
        import logging
        
        logger = logging.getLogger(__name__)
        
        print("🧪 Testing Minimal LangChain Agent (Nuclear Option)...")
        
        # Minimal LLM setup
        llm = ChatOllama(
            model="llama3.1:8b",
            temperature=0.7,
            base_url="http://172.20.0.10:11434"
        )
        
        # Minimal tools - just mock tools to avoid MCP issues
        tools = [
            Tool(
                name="search-pubmed",
                func=lambda x: f"Mock PubMed results for: {x}",
                description="Search medical literature"
            )
        ]
        
        # Minimal prompt - NO chat_history
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a medical assistant. Tools: {tools}. Valid actions: {tool_names}"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create agent
        agent = create_structured_chat_agent(
            llm=llm,
            tools=tools,
            prompt=prompt
        )
        
        # Create executor - NO memory
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            return_intermediate_steps=True
        )
        
        print("✅ Minimal agent initialized successfully")
        
        # Test simple query
        test_query = "What are the symptoms of diabetes?"
        print(f"🔍 Testing query: {test_query}")
        
        # ONLY pass input
        result = await executor.ainvoke({"input": test_query})
        
        print("✅ Agent processing successful!")
        print(f"📄 Response: {result.get('output', 'No output')}")
        print(f"🔧 Intermediate steps: {len(result.get('intermediate_steps', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Check if it's the specific scratchpad error
        error_msg = str(e).lower()
        if 'agent_scratchpad' in error_msg and 'list of base messages' in error_msg:
            print("🔴 CRITICAL: The agent_scratchpad error is still occurring!")
            return False
        else:
            print("🟡 Different error - not the scratchpad issue")
            return False

if __name__ == "__main__":
    success = asyncio.run(test_minimal_agent())
    if success:
        print("\n🎉 SUCCESS: Minimal LangChain agent is working!")
        sys.exit(0)
    else:
        print("\n💥 FAILURE: Even minimal agent has issues")
        sys.exit(1)
