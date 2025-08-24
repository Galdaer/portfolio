"""
Enhanced Agent Logging Utilities

Provides standardized logging utilities specifically for healthcare agents with:
- Step-by-step process logging with timestamps
- Performance metrics tracking
- PHI-safe parameter logging
- Method timing and context tracking
- Structured workflow logging

MEDICAL DISCLAIMER: These logging utilities support healthcare administrative functions.
They do not provide medical advice, diagnosis, or treatment recommendations.
All medical decisions must be made by qualified healthcare professionals.
"""

import functools
import hashlib
import logging
import time
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    log_healthcare_event,
)
from core.infrastructure.phi_monitor import sanitize_healthcare_data


class AgentWorkflowLogger:
    """
    Enhanced logging utility for healthcare agents with workflow tracking.

    Provides structured logging for complex agent workflows with:
    - Step-by-step process tracking
    - Execution timing
    - Parameter sanitization
    - Performance metrics
    """

    def __init__(self, agent_name: str, session_id: str | None = None):
        self.agent_name = agent_name
        self.session_id = session_id or self._generate_session_id()
        self.logger = get_healthcare_logger(f"agent.{agent_name}")
        self.workflow_start_time: float | None = None
        self.step_counter = 0
        self.performance_metrics: dict[str, Any] = {}

    def _generate_session_id(self) -> str:
        """Generate a unique session ID for tracking workflows."""
        timestamp = str(int(time.time() * 1000000))  # microseconds
        return f"{self.agent_name}_{timestamp}"

    def start_workflow(self, workflow_name: str, parameters: dict[str, Any] = None) -> None:
        """
        Start a new workflow with logging and timing.

        Args:
            workflow_name: Name of the workflow being started
            parameters: Input parameters (will be PHI-sanitized)
        """
        self.workflow_start_time = time.time()
        self.step_counter = 0

        sanitized_params = sanitize_healthcare_data(parameters or {})

        log_healthcare_event(
            self.logger,
            logging.INFO,
            f"🚀 Starting workflow: {workflow_name}",
            context={
                "workflow": workflow_name,
                "session_id": self.session_id,
                "agent": self.agent_name,
                "parameters": sanitized_params,
                "start_time": datetime.now(UTC).isoformat(),
            },
            operation_type="workflow_start",
        )

    def log_step(self, step_name: str, details: dict[str, Any] = None, level: int = logging.INFO) -> None:
        """
        Log a workflow step with timing and context.

        Args:
            step_name: Name of the current step
            details: Step details (will be PHI-sanitized)
            level: Logging level
        """
        self.step_counter += 1
        current_time = time.time()
        elapsed_time = (current_time - self.workflow_start_time) if self.workflow_start_time else 0

        sanitized_details = sanitize_healthcare_data(details or {})

        log_healthcare_event(
            self.logger,
            level,
            f"📋 Step {self.step_counter}: {step_name}",
            context={
                "step": step_name,
                "step_number": self.step_counter,
                "session_id": self.session_id,
                "agent": self.agent_name,
                "elapsed_time_ms": round(elapsed_time * 1000, 2),
                "timestamp": datetime.now(UTC).isoformat(),
                "details": sanitized_details,
            },
            operation_type="workflow_step",
        )

    def log_performance_metric(self, metric_name: str, value: Any, unit: str = None) -> None:
        """
        Log a performance metric for monitoring and optimization.

        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement (optional)
        """
        self.performance_metrics[metric_name] = {
            "value": value,
            "unit": unit,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        log_healthcare_event(
            self.logger,
            logging.INFO,
            f"📊 Performance metric: {metric_name} = {value}" + (f" {unit}" if unit else ""),
            context={
                "metric_name": metric_name,
                "metric_value": value,
                "metric_unit": unit,
                "session_id": self.session_id,
                "agent": self.agent_name,
            },
            operation_type="performance_metric",
        )

    def log_external_call(self, service_name: str, operation: str, duration_ms: float,
                         success: bool, details: dict[str, Any] = None) -> None:
        """
        Log external service calls with timing and success tracking.

        Args:
            service_name: Name of external service (e.g., "MCP", "LLM", "Database")
            operation: Operation performed
            duration_ms: Duration in milliseconds
            success: Whether the call succeeded
            details: Additional details (will be PHI-sanitized)
        """
        sanitized_details = sanitize_healthcare_data(details or {})

        log_healthcare_event(
            self.logger,
            logging.INFO if success else logging.WARNING,
            f"🔗 External call: {service_name}.{operation} ({'✅' if success else '❌'}) in {duration_ms:.2f}ms",
            context={
                "service": service_name,
                "operation": operation,
                "duration_ms": duration_ms,
                "success": success,
                "session_id": self.session_id,
                "agent": self.agent_name,
                "details": sanitized_details,
            },
            operation_type="external_call",
        )

    def finish_workflow(self, status: str = "completed", results: dict[str, Any] = None,
                       error: Exception = None) -> None:
        """
        Finish the workflow with summary logging.

        Args:
            status: Final status ("completed", "failed", "partial")
            results: Final results (will be PHI-sanitized)
            error: Exception if workflow failed
        """
        total_time = (time.time() - self.workflow_start_time) if self.workflow_start_time else 0

        sanitized_results = sanitize_healthcare_data(results or {})

        context = {
            "status": status,
            "total_steps": self.step_counter,
            "total_time_ms": round(total_time * 1000, 2),
            "session_id": self.session_id,
            "agent": self.agent_name,
            "end_time": datetime.now(UTC).isoformat(),
            "results": sanitized_results,
            "performance_metrics": self.performance_metrics,
        }

        if error:
            context["error"] = {
                "type": type(error).__name__,
                "message": str(error)[:200],  # Truncated for safety
            }

        level = logging.INFO if status == "completed" else logging.ERROR
        emoji = "✅" if status == "completed" else "❌"

        log_healthcare_event(
            self.logger,
            level,
            f"{emoji} Workflow finished: {status} in {total_time:.2f}s with {self.step_counter} steps",
            context=context,
            operation_type="workflow_end",
        )


def enhanced_agent_method(
    operation_type: str = "agent_operation",
    phi_risk_level: str = "medium",
    track_performance: bool = True,
    log_parameters: bool = True,
    log_results: bool = True,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Enhanced decorator for agent methods with comprehensive logging.

    Args:
        operation_type: Type of operation for logging categorization
        phi_risk_level: PHI risk level (low, medium, high)
        track_performance: Whether to track execution time and performance
        log_parameters: Whether to log method parameters (PHI-sanitized)
        log_results: Whether to log method results (PHI-sanitized)
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract agent info from first argument (self)
            agent_self = args[0] if args else None
            agent_name = getattr(agent_self, "agent_name", "unknown")

            logger = get_healthcare_logger(f"agent.{agent_name}")
            method_name = f"{func.__qualname__}"
            start_time = time.time()

            # Create session-specific logger
            session_id = f"{agent_name}_{int(time.time() * 1000000)}"

            try:
                # Log method entry
                entry_context = {
                    "method": method_name,
                    "operation_type": operation_type,
                    "phi_risk_level": phi_risk_level,
                    "session_id": session_id,
                    "entry_time": datetime.now(UTC).isoformat(),
                }

                if log_parameters and (args or kwargs):
                    # Sanitize parameters for logging
                    sanitized_params = {
                        "args_count": len(args) - 1,  # Exclude self
                        "kwargs": sanitize_healthcare_data(kwargs),
                    }
                    entry_context["parameters"] = sanitized_params

                log_healthcare_event(
                    logger,
                    logging.INFO,
                    f"🔄 Method entry: {method_name}",
                    context=entry_context,
                    operation_type="method_entry",
                )

                # Execute the method
                if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:  # CO_COROUTINE
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Calculate performance metrics
                execution_time = time.time() - start_time

                # Log successful completion
                success_context = {
                    "method": method_name,
                    "session_id": session_id,
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "success": True,
                    "completion_time": datetime.now(UTC).isoformat(),
                }

                if log_results and result is not None:
                    success_context["results"] = sanitize_healthcare_data({
                        "result_type": type(result).__name__,
                        "result_summary": str(result)[:100] if result else None,
                    })

                if track_performance:
                    success_context["performance"] = {
                        "execution_time_category": (
                            "fast" if execution_time < 1.0 else
                            "medium" if execution_time < 5.0 else
                            "slow"
                        ),
                    }

                log_healthcare_event(
                    logger,
                    logging.INFO,
                    f"✅ Method success: {method_name} in {execution_time:.2f}s",
                    context=success_context,
                    operation_type="method_success",
                )

                return result

            except Exception as e:
                execution_time = time.time() - start_time

                # Log error with context
                error_context = {
                    "method": method_name,
                    "session_id": session_id,
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "success": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e)[:200],
                    "error_time": datetime.now(UTC).isoformat(),
                }

                # Add stack trace in development
                import os
                if os.getenv("ENVIRONMENT", "").lower() in ["development", "dev"]:
                    error_context["stack_trace"] = traceback.format_exc()[-500:]  # Last 500 chars

                log_healthcare_event(
                    logger,
                    logging.ERROR,
                    f"❌ Method error: {method_name}: {str(e)}",
                    context=error_context,
                    operation_type="method_error",
                )

                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Similar logic for sync methods - simplified version
            agent_self = args[0] if args else None
            agent_name = getattr(agent_self, "agent_name", "unknown")
            logger = get_healthcare_logger(f"agent.{agent_name}")
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                log_healthcare_event(
                    logger,
                    logging.INFO,
                    f"✅ Method success: {func.__qualname__} in {execution_time:.2f}s",
                    context={
                        "method": func.__qualname__,
                        "execution_time_ms": round(execution_time * 1000, 2),
                        "success": True,
                    },
                    operation_type="method_success",
                )

                return result

            except Exception as e:
                execution_time = time.time() - start_time

                log_healthcare_event(
                    logger,
                    logging.ERROR,
                    f"❌ Method error: {func.__qualname__}: {str(e)}",
                    context={
                        "method": func.__qualname__,
                        "execution_time_ms": round(execution_time * 1000, 2),
                        "error_type": type(e).__name__,
                        "error_message": str(e)[:200],
                    },
                    operation_type="method_error",
                )

                raise

        # Return appropriate wrapper based on function type
        if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        return sync_wrapper

    return decorator


def log_agent_query(agent_name: str, query: str, query_type: str = "search") -> str:
    """
    Log and return a sanitized query hash for tracking.

    Args:
        agent_name: Name of the agent processing the query
        query: The query string (will be PHI-sanitized)
        query_type: Type of query (search, analysis, etc.)

    Returns:
        Query hash for tracking purposes
    """
    logger = get_healthcare_logger(f"agent.{agent_name}")

    # Create query hash for tracking without exposing content
    query_hash = hashlib.sha256(query.encode()).hexdigest()[:12]

    # Sanitize query for logging
    sanitized_query = sanitize_healthcare_data({"query": query})

    log_healthcare_event(
        logger,
        logging.INFO,
        f"🔍 Query received: {query_type} query (hash: {query_hash})",
        context={
            "query_type": query_type,
            "query_hash": query_hash,
            "query_length": len(query),
            "agent": agent_name,
            "sanitized_query": sanitized_query,
        },
        operation_type="query_received",
    )

    return query_hash


def log_agent_cache_event(agent_name: str, cache_key: str, hit: bool,
                         operation: str = "lookup") -> None:
    """
    Log cache hit/miss events for performance tracking.

    Args:
        agent_name: Name of the agent
        cache_key: Cache key (will be hashed for logging)
        hit: Whether cache hit occurred
        operation: Cache operation (lookup, store, invalidate)
    """
    logger = get_healthcare_logger(f"agent.{agent_name}")

    # Hash cache key for privacy
    key_hash = hashlib.sha256(cache_key.encode()).hexdigest()[:8]

    log_healthcare_event(
        logger,
        logging.INFO,
        f"💾 Cache {operation}: {'HIT' if hit else 'MISS'} (key: {key_hash})",
        context={
            "cache_operation": operation,
            "cache_hit": hit,
            "cache_key_hash": key_hash,
            "agent": agent_name,
        },
        operation_type="cache_event",
    )
