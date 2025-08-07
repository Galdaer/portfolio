"""
Model Registry for Intelluxe AI

Manages local LLM models through Ollama integration with healthcare-specific
model configurations and fine-tuning support.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
import httpx
from config.app import config

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Registry for managing healthcare AI models through Ollama

    Provides model discovery, health checking, and configuration
    with support for future fine-tuned adapters.
    """

    def __init__(self) -> None:
        self.ollama_client: Optional[httpx.AsyncClient] = None
        self._available_models: List[Dict[str, Any]] = []
        self._performance_metrics: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    def log_performance(self, model_name: str, metrics: Dict[str, Any]) -> None:
        """Log performance metrics for a model or adapter"""
        self._performance_metrics[model_name] = metrics

    def get_performance_metrics(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for a model or adapter"""
        return self._performance_metrics.get(model_name)

    async def initialize(self) -> None:
        """Initialize Ollama client and discover available models"""
        try:
            self.ollama_client = httpx.AsyncClient(
                base_url=config.ollama_url,
                timeout=30.0
            )

            # Test connection and discover models
            await self._discover_models()
            self._initialized = True

            logger.info(f"Model registry initialized with {len(self._available_models)} models")

        except Exception as e:
            logger.error(f"Failed to initialize model registry: {e}")
            raise

    async def close(self) -> None:
        """Close Ollama client"""
        if self.ollama_client:
            await self.ollama_client.aclose()

        self._initialized = False
        logger.info("Model registry closed")

    async def health_check(self) -> Dict[str, Any]:
        """Check health of model serving"""
        if not self._initialized or self.ollama_client is None:
            return {"status": "not_initialized"}

        try:
            # Test Ollama connection
            response = await self.ollama_client.get("/api/tags")

            if response.status_code == 200:
                models = response.json().get("models", [])
                return {
                    "status": "healthy",
                    "ollama_connected": True,
                    "available_models": len(models),
                    "models": [model.get("name") for model in models]
                }
            else:
                return {
                    "status": "unhealthy",
                    "ollama_connected": False,
                    "error": f"HTTP {response.status_code}"
                }

        except Exception as e:
            logger.error(f"Model health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def _discover_models(self) -> None:
        """Discover available models from Ollama"""
        if self.ollama_client is None:
            logger.warning("Ollama client not initialized")
            return

        try:
            response = await self.ollama_client.get("/api/tags")
            response.raise_for_status()

            data = response.json()
            self._available_models = data.get("models", [])

            logger.info(f"Discovered {len(self._available_models)} models")

        except Exception as e:
            logger.warning(f"Failed to discover models: {e}")
            self._available_models = []

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models"""
        if not self._initialized:
            raise RuntimeError("Model registry not initialized")

        return self._available_models.copy()

    async def generate_completion(self, model: str, prompt: str, **kwargs: Any) -> str:
        """Generate completion using specified model"""
        if not self._initialized or self.ollama_client is None:
            raise RuntimeError("Model registry not initialized")

        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                **kwargs
            }

            response = await self.ollama_client.post("/api/generate", json=payload)
            response.raise_for_status()

            result = response.json()
            return str(result.get("response", ""))

        except Exception as e:
            logger.error(f"Failed to generate completion: {e}")
            raise

    async def chat_completion(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Generate chat completion using specified model"""
        if not self._initialized or self.ollama_client is None:
            raise RuntimeError("Model registry not initialized")

        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                **kwargs
            }

            response = await self.ollama_client.post("/api/chat", json=payload)
            response.raise_for_status()

            result = response.json()
            return str(result.get("message", {}).get("content", ""))

        except Exception as e:
            logger.error(f"Failed to generate chat completion: {e}")
            raise


# Global model registry instance
model_registry = ModelRegistry()
