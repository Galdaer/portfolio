# interfaces/streamlit_healthcare_interface.py

import streamlit as st
import asyncio
from typing import Dict, Any, Optional

class HealthcareStreamlitInterface:
"""Healthcare AI interface using Streamlit pattern from ultimate-ai-assistant"""

    def __init__(self):
        self.setup_page_config()
        self.initialize_session_state()

    def setup_page_config(self):
        """Configure Streamlit page for healthcare AI"""
        st.set_page_config(
            page_title="Intelluxe Healthcare AI Assistant",
            page_icon="🏥",
            layout="wide",
            initial_sidebar_state="expanded"
        )

    def initialize_session_state(self):
        """Initialize session state for healthcare conversations"""
        if "healthcare_messages" not in st.session_state:
            st.session_state.healthcare_messages = []

        if "clinical_context" not in st.session_state:
            st.session_state.clinical_context = {}

        if "healthcare_agent" not in st.session_state:
            st.session_state.healthcare_agent = None

    def render_sidebar_config(self):
        """Render healthcare-specific configuration sidebar"""
        with st.sidebar:
            st.header("Healthcare AI Configuration")

            # Healthcare MCP configuration
            st.subheader("Healthcare MCP Settings")
            mcp_host = st.text_input("MCP Host", value="localhost")
            mcp_port = st.number_input("MCP Port", value=8000)

            # Clinical context settings
            st.subheader("Clinical Context")
            patient_context = st.text_area(
                "Patient Context (No PHI)",
                placeholder="General medical context without identifying information...",
                help="Provide general clinical context without any PHI"
            )

            # Activate configuration
            if st.button("Activate Healthcare AI", type="primary"):
                success = self.activate_healthcare_config(mcp_host, mcp_port, patient_context)
                if success:
                    st.success("✅ Healthcare AI activated!")
                else:
                    st.error("❌ Failed to activate Healthcare AI")

    def activate_healthcare_config(self, host: str, port: int, context: str) -> bool:
        """Activate healthcare configuration similar to their config activation"""
        try:
            # Create healthcare agent configuration
            healthcare_config = {
                "mcpServers": {
                    "healthcare": {
                        "host": host,
                        "port": port,
                        "transport": "http",
                        "tools": ["fda_search", "pubmed_search", "clinical_trials", "phi_detection"]
                    }
                },
                "clinical_context": context,
                "safety_mode": "strict",
                "disclaimers_enabled": True
            }

            # Initialize healthcare agent (similar to their create_agent pattern)
            from core.medical.clinical_research_agent import ClinicalResearchAgent
            from core.orchestration.mcp_orchestrator import HealthcareMCPOrchestrator

            mcp_orchestrator = HealthcareMCPOrchestrator.from_config_dict(healthcare_config)

            # Create agent with MCP integration
            st.session_state.healthcare_agent = ClinicalResearchAgent(
                mcp_client=mcp_orchestrator,
                llm_client=None  # Will be initialized with Ollama
            )

            st.session_state.clinical_context = {"context": context}
            return True

        except Exception as e:
            st.error(f"Configuration error: {str(e)}")
            return False

    async def process_healthcare_query(self, query: str) -> str:
        """Process healthcare query using agent pattern from ultimate-ai-assistant"""
        try:
            if not st.session_state.healthcare_agent:
                return "❌ Please activate Healthcare AI configuration first"

            # Add medical disclaimers (unlike their general assistant)
            disclaimers = [
                "🏥 FOR INFORMATIONAL PURPOSES ONLY",
                "🩺 NOT A SUBSTITUTE FOR PROFESSIONAL MEDICAL ADVICE",
                "🚨 CONSULT YOUR HEALTHCARE PROVIDER FOR MEDICAL DECISIONS"
            ]

            # Process query through healthcare agent
            result = await st.session_state.healthcare_agent.process(
                input_data={
                    "query": query,
                    "query_type": "general_inquiry",
                    "clinical_context": st.session_state.clinical_context
                },
                session_id="streamlit_session"
            )

            # Format response with medical disclaimers
            formatted_response = "\n".join(disclaimers) + "\n\n" + str(result.get("response", "No response generated"))

            return formatted_response

        except Exception as e:
            return f"❌ Error processing healthcare query: {str(e)}"

    def render_chat_interface(self):
        """Render healthcare chat interface similar to their chat interface"""

        # Display chat messages with healthcare styling
        for message in st.session_state.healthcare_messages:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    # Add medical disclaimer styling for assistant messages
                    if "🏥 FOR INFORMATIONAL PURPOSES ONLY" in message["content"]:
                        st.markdown("---")
                        st.markdown("**MEDICAL DISCLAIMER:**")

                st.markdown(message["content"])

        # Healthcare-specific chat input with safety notice
        st.markdown("**⚠️ Safety Notice:** Do not share personal health information (PHI) in this chat.")

        if prompt := st.chat_input("Ask about medical information (no PHI)..."):
            # Add user message
            st.session_state.healthcare_messages.append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.markdown(prompt)

            # Process with healthcare agent
            with st.chat_message("assistant"):
                with st.spinner("🔬 Analyzing medical information..."):
                    try:
                        # Async processing like their example
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(self.process_healthcare_query(prompt))
                        loop.close()

                        st.markdown(result)
                        st.session_state.healthcare_messages.append({"role": "assistant", "content": result})

                    except Exception as e:
                        error_msg = f"❌ Healthcare processing error: {str(e)}"
                        st.error(error_msg)
                        st.session_state.healthcare_messages.append({"role": "assistant", "content": error_msg})

    def run(self):
        """Main interface runner"""
        st.markdown("# 🏥 Intelluxe Healthcare AI Assistant")
        st.markdown("**Privacy-first healthcare AI for clinical information and administrative support**")

        # Render components
        self.render_sidebar_config()
        self.render_chat_interface()

        # Footer with healthcare compliance info
        st.markdown("---")
        st.markdown("**🔒 Privacy-First Healthcare AI** | All data processed locally | HIPAA-compliant design")

# Entry point

if **name** == "**main**":
interface = HealthcareStreamlitInterface()
interface.run()
