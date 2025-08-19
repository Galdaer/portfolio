"""
Background Task Processing for Healthcare AI
Handles long-running medical analysis tasks asynchronously
"""

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncio

logger = logging.getLogger(__name__)


class HealthcareTaskManager:
    """
    Manages background processing for healthcare AI tasks

    Use Cases:
    - Medical literature analysis (can take 30+ seconds)
    - Comprehensive patient intake processing
    - Clinical decision support analysis
    - Insurance verification workflows
    """

    def __init__(self) -> None:
        self.active_tasks: dict[str, asyncio.Task] = {}

    async def process_medical_analysis(
        self,
        task_id: str,
        analysis_func: Callable,
        patient_data: dict[str, Any],
    ) -> None:
        """
        Process medical analysis in background with progress tracking

        Args:
            task_id: Unique identifier for this analysis task
            analysis_func: The medical analysis function to execute
            patient_data: Synthetic patient data for analysis
        """
        try:
            logger.info(f"Starting medical analysis task {task_id}")
            result = await analysis_func(patient_data)
            logger.info(f"Completed medical analysis task {task_id}")

            # Store result in Redis for later retrieval
            await self._store_task_result(task_id, result)

        except Exception as e:
            logger.exception(f"Medical analysis task {task_id} failed: {e}")
            await self._store_task_error(task_id, str(e))
        finally:
            self.active_tasks.pop(task_id, None)

    async def _store_task_result(self, task_id: str, result: Any) -> None:
        """Store completed task result in Redis for retrieval"""
        try:
            from core.dependencies import healthcare_services

            redis_client = healthcare_services.redis_client

            if redis_client:
                import json

                # Store with 1 hour expiration
                await redis_client.setex(
                    f"task_result:{task_id}",
                    3600,
                    json.dumps({"status": "completed", "result": result}),
                )
        except Exception as e:
            logger.warning(f"Failed to store task result {task_id}: {e}")

    async def _store_task_error(self, task_id: str, error: str) -> None:
        """Store task error in Redis for retrieval"""
        try:
            from core.dependencies import healthcare_services

            redis_client = healthcare_services.redis_client

            if redis_client:
                import json

                # Store with 1 hour expiration
                await redis_client.setex(
                    f"task_result:{task_id}",
                    3600,
                    json.dumps({"status": "error", "error": error}),
                )
        except Exception as e:
            logger.warning(f"Failed to store task error {task_id}: {e}")

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        """
        Get status of background task

        Returns:
            Dict with status information: {'status': 'running'|'completed'|'error', ...}
        """
        # Check if task is still running
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            return {
                "status": "running",
                "task_id": task_id,
                "done": task.done(),
            }

        # Check Redis for completed/error results
        try:
            from core.dependencies import healthcare_services

            redis_client = healthcare_services.redis_client

            if redis_client:
                import json

                result_data = await redis_client.get(f"task_result:{task_id}")
                if result_data:
                    from typing import cast

                    result: dict[str, Any] = cast("dict[str, Any]", json.loads(result_data))
                    return result
        except Exception as e:
            logger.warning(f"Failed to get task status {task_id}: {e}")

        # Task not found
        return {"status": "not_found", "task_id": task_id}
