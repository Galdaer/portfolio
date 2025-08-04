"""
DeepEval Healthcare Testing Framework Configuration
Comprehensive AI evaluation framework for Intelluxe AI healthcare system
"""

import logging
import os
from dataclasses import dataclass
from typing import Any

import psycopg2
import redis
import requests
from deepeval import evaluate
from deepeval.metrics import (
    AnswerRelevancyMetric,
    BiasMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    FaithfulnessMetric,
    HallucinationMetric,
    ToxicityMetric,
)
from deepeval.test_case import LLMTestCase

# Configure logging for healthcare compliance
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/opt/intelluxe/logs/healthcare_evaluation.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class HealthcareEvaluationConfig:
    """Configuration for healthcare AI evaluation"""

    # Database connections
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "intelluxe"
    postgres_user: str = os.getenv("POSTGRES_USER", "intelluxe")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "intelluxe")

    # Redis connection
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # Ollama connection
    ollama_host: str = "localhost"
    ollama_port: int = 11434
    ollama_models: list[str] | None = None

    # Evaluation settings
    evaluation_threshold: float = 0.7
    max_test_cases: int = 100
    parallel_workers: int = 4

    # Healthcare-specific settings
    phi_detection_enabled: bool = True
    hipaa_compliance_mode: bool = True
    audit_logging_enabled: bool = True

    def __post_init__(self) -> None:
        if self.ollama_models is None:
            self.ollama_models = [
                "llama3.1:8b-instruct-q4_K_M",
                "mistral:7b-instruct-q4_K_M",
            ]


class HealthcareMetrics:
    """Healthcare-specific evaluation metrics for AI systems"""

    def __init__(self, config: HealthcareEvaluationConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.HealthcareMetrics")

    def get_core_metrics(self) -> list[Any]:
        """Get core evaluation metrics for healthcare AI"""
        return [
            AnswerRelevancyMetric(threshold=self.config.evaluation_threshold),
            FaithfulnessMetric(threshold=self.config.evaluation_threshold),
            ContextualPrecisionMetric(threshold=self.config.evaluation_threshold),
            ContextualRecallMetric(threshold=self.config.evaluation_threshold),
            HallucinationMetric(threshold=0.3),  # Stricter for healthcare
            BiasMetric(threshold=0.1),  # Very strict for healthcare
            ToxicityMetric(threshold=0.1),  # Very strict for healthcare
        ]

    def get_healthcare_specific_metrics(self) -> list[Any]:
        """Get healthcare-specific evaluation metrics"""
        # These would be custom metrics for healthcare scenarios
        return [
            # Medical accuracy metrics
            # Clinical reasoning metrics
            # Patient safety metrics
            # HIPAA compliance metrics
            # Drug interaction detection metrics
            # Diagnostic accuracy metrics
        ]


class HealthcareEvaluationFramework:
    """Main evaluation framework for healthcare AI systems"""

    def __init__(self, config: HealthcareEvaluationConfig | None = None):
        self.config = config or HealthcareEvaluationConfig()
        self.logger = logging.getLogger(f"{__name__}.HealthcareEvaluationFramework")
        self.metrics = HealthcareMetrics(self.config)

        # Initialize connections
        self._init_database_connections()
        self._init_ollama_connection()

    def _init_database_connections(self) -> None:
        """Initialize database connections"""
        try:
            # PostgreSQL connection
            self.postgres_conn = psycopg2.connect(
                host=self.config.postgres_host,
                port=self.config.postgres_port,
                database=self.config.postgres_db,
                user=self.config.postgres_user,
                password=self.config.postgres_password,
            )

            # Redis connection
            self.redis_conn = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                decode_responses=True,
            )

            self.logger.info("Database connections initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize database connections: {e}")
            raise

    def _init_ollama_connection(self) -> None:
        """Initialize Ollama connection and verify models"""
        try:
            ollama_url = f"http://{self.config.ollama_host}:{self.config.ollama_port}"

            # Check Ollama health
            response = requests.get(f"{ollama_url}/api/version", timeout=10)
            response.raise_for_status()

            # Verify models are available
            models_response = requests.get(f"{ollama_url}/api/tags", timeout=10)
            models_response.raise_for_status()

            available_models = [model["name"] for model in models_response.json().get("models", [])]

            if self.config.ollama_models:
                for model in self.config.ollama_models:
                    if model not in available_models:
                        self.logger.warning(f"Model {model} not available in Ollama")

            self.logger.info(f"Ollama connection initialized. Available models: {available_models}")

        except Exception as e:
            self.logger.error(f"Failed to initialize Ollama connection: {e}")
            raise

    def create_test_case(
        self,
        input_text: str,
        expected_output: str,
        context: list[str],
        retrieval_context: list[str],
        actual_output: str = "",
    ) -> LLMTestCase:
        """Create a test case for evaluation"""
        return LLMTestCase(
            input=input_text,
            actual_output=actual_output,
            expected_output=expected_output,
            context=context,
            retrieval_context=retrieval_context,
        )

    def evaluate_healthcare_ai(
        self,
        test_cases: list[LLMTestCase],
        model_name: str = "llama3.1:8b-instruct-q4_K_M",
    ) -> Any:
        """Evaluate healthcare AI system with comprehensive metrics"""

        self.logger.info(f"Starting healthcare AI evaluation with {len(test_cases)} test cases")

        # Get all metrics
        all_metrics = (
            self.metrics.get_core_metrics() + self.metrics.get_healthcare_specific_metrics()
        )

        # Run evaluation using the correct API
        results = evaluate(test_cases=test_cases, metrics=all_metrics)

        # Log results for audit trail
        if self.config.audit_logging_enabled:
            self._log_evaluation_results(results, model_name)

        return results

    def _log_evaluation_results(self, results: Any, model_name: str) -> None:
        """Log evaluation results for healthcare audit trail"""
        audit_entry = {
            "timestamp": "now()",
            "evaluation_type": "healthcare_ai_evaluation",
            "model_name": model_name,
            "results_summary": results,
            "compliance_status": "evaluated",
            "phi_detected": False,  # Would be set by PHI detection
        }

        # Store in PostgreSQL for audit trail
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO evaluation_audit_log
                    (timestamp, evaluation_type, model_name, results_summary, compliance_status, phi_detected)
                    VALUES (%(timestamp)s, %(evaluation_type)s, %(model_name)s, %(results_summary)s,
                           %(compliance_status)s, %(phi_detected)s)
                """,
                    audit_entry,
                )
                self.postgres_conn.commit()

        except Exception as e:
            self.logger.error(f"Failed to log evaluation results: {e}")

    def close_connections(self) -> None:
        """Close all database connections"""
        if hasattr(self, "postgres_conn"):
            self.postgres_conn.close()
        if hasattr(self, "redis_conn"):
            self.redis_conn.close()


# Global configuration instance
healthcare_eval_config = HealthcareEvaluationConfig()
