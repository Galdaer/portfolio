"""
Simple MCP Test Pipeline for Open WebUI
"""

class Pipeline:
    def __init__(self):
        self.type = "manifold"  
        self.id = "simple_mcp_test"
        self.name = "Simple MCP Test"
        
    async def on_startup(self):
        print("MCP Test Pipeline started")
        
    async def on_shutdown(self):
        print("MCP Test Pipeline stopped")
        
    def pipe(self, user_message: str, model_id: str, messages: list, body: dict) -> str:
        # Simple test - just echo back
        return f"MCP Test received: {user_message}"
