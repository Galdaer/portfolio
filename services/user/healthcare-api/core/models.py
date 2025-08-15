"""
Healthcare Model Registry
Placeholder implementation for healthcare model management
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Placeholder model registry for healthcare AI models"""

    def __init__(self) -> None:
        self._initialized = False
        self._models: dict[str, Any] = {}

    async def initialize(self) -> None:
        """Initialize model registry"""
        self._initialized = True
        logger.info("Model registry initialized (placeholder)")

    async def get_available_models(self) -> list[dict[str, Any]]:
        """Get available models - returns locally available Ollama models"""
        if not self._initialized:
            await self.initialize()

        # Get real Ollama models - no fallbacks to expose connection issues
        import ollama
        client = ollama.Client(host="http://172.20.0.10:11434")
        models = client.list()

        available_models = []
        for model in models.get("models", []):
            available_models.append({
                "id": model.get("name", "unknown"),
                "name": model.get("name", "Unknown Model"),
                "type": "text_generation",
                "status": "available",
                "size": model.get("size", 0),
                "modified_at": model.get("modified_at", ""),
            })

        logger.info(f"Retrieved {len(available_models)} models from Ollama")
        return available_models

    def log_performance(self, model_id: str, metrics: dict[str, Any]) -> None:
        """Log model performance metrics"""
        logger.info(f"Performance logged for {model_id}: {metrics}")


# Global registry instance
model_registry = ModelRegistry()
