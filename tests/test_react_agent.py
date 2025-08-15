#!/usr/bin/env python3
"""
ReAct Agent Test - Alternative to structured chat agent
"""
import asyncio
import sys
import os

# Add the healthcare-api to the path
sys.path.insert(0, '/home/intelluxe/services/user/healthcare-api')

async def test_react_agent():
    """Test with ReAct agent instead of structured chat agent"""
    try:
        from langchain.agents import AgentExecutor, create_react_agent
        from langchain.prompts import PromptTemplate
        from langchain_ollama import ChatOllama
        from langchain.tools import Tool
        
        print("🧪 Testing ReAct LangChain Agent...")
        
        # Minimal LLM setup
        llm = ChatOllama(
            model="llama3.1:8b",
            temperature=0.7,
            base_url="http://localhost:11434"
        )
        
        # Minimal tools
        tools = [
            Tool(
                name="search_pubmed",
                func=lambda x: f"Mock PubMed results for: {x}",
                description="Search medical literature"
            )
        ]
        
        # ReAct prompt template (simpler format)
        prompt = PromptTemplate.from_template("""Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}""")
        
        # Create ReAct agent
        agent = create_react_agent(
            llm=llm,
            tools=tools,
            prompt=prompt
        )
        
        # Create executor with parsing error handling
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            return_intermediate_steps=True,
            max_iterations=3,
            handle_parsing_errors=True  # This allows the agent to recover from parsing errors
        )
        
        print("✅ ReAct agent initialized successfully")
        
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
    success = asyncio.run(test_react_agent())
    if success:
        print("\n🎉 SUCCESS: ReAct LangChain agent is working!")
        sys.exit(0)
    else:
        print("\n💥 FAILURE: ReAct agent has issues")
        sys.exit(1)
