"""
Enhanced error handling utilities for medical mirrors
"""

import logging
import time
import traceback
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class MedicalMirrorError(Exception):
    """Base exception for medical mirror errors"""


class ValidationError(MedicalMirrorError):
    """Error during data validation"""


class DatabaseError(MedicalMirrorError):
    """Error during database operations"""


class ParsingError(MedicalMirrorError):
    """Error during data parsing"""


class NetworkError(MedicalMirrorError):
    """Error during network operations"""


def retry_on_error(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    logger_name: str | None = None,
):
    """
    Decorator to retry function calls on specific exceptions

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for delay
        exceptions: Tuple of exception types to retry on
        logger_name: Name of logger to use for retry messages
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retry_logger = logging.getLogger(logger_name or func.__module__)

            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        retry_logger.exception(
                            f"Function {func.__name__} failed after {max_attempts} attempts: {e}",
                        )
                        raise

                    retry_delay = delay * (backoff ** attempt)
                    retry_logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                        f"Retrying in {retry_delay:.1f}s...",
                    )
                    time.sleep(retry_delay)

            # This should never be reached, but just in case
            raise last_exception

        return wrapper
    return decorator


def safe_parse(
    parser_func: Callable,
    data: Any,
    record_id: str | None = None,
    logger_name: str | None = None,
    default_return: Any = None,
) -> Any:
    """
    Safely execute a parser function with comprehensive error handling

    Args:
        parser_func: The parsing function to call
        data: Data to parse
        record_id: Optional ID for logging (e.g., PMID, NCT ID)
        logger_name: Name of logger to use
        default_return: Value to return on error

    Returns:
        Parsed data or default_return on error
    """
    parse_logger = logging.getLogger(logger_name or parser_func.__module__)

    try:
        return parser_func(data)
    except ValidationError as e:
        parse_logger.warning(f"Validation failed for record {record_id}: {e}")
        return default_return
    except ParsingError as e:
        parse_logger.warning(f"Parsing failed for record {record_id}: {e}")
        return default_return
    except Exception as e:
        parse_logger.exception(f"Unexpected error parsing record {record_id}: {e}")
        parse_logger.debug(f"Full traceback: {traceback.format_exc()}")
        return default_return


class ErrorCollector:
    """Collects and summarizes errors during batch processing"""

    def __init__(self, name: str):
        self.name = name
        self.errors = {
            "validation_errors": [],
            "parsing_errors": [],
            "database_errors": [],
            "network_errors": [],
            "other_errors": [],
        }
        self.counts = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
        }

    def record_success(self):
        """Record a successful operation"""
        self.counts["total_processed"] += 1
        self.counts["successful"] += 1

    def record_error(self, error: Exception, record_id: str | None = None, context: str | None = None):
        """Record an error with context"""
        self.counts["total_processed"] += 1
        self.counts["failed"] += 1

        error_info = {
            "record_id": record_id,
            "context": context,
            "error_type": type(error).__name__,
            "message": str(error),
            "timestamp": time.time(),
        }

        if isinstance(error, ValidationError):
            self.errors["validation_errors"].append(error_info)
        elif isinstance(error, ParsingError):
            self.errors["parsing_errors"].append(error_info)
        elif isinstance(error, DatabaseError):
            self.errors["database_errors"].append(error_info)
        elif isinstance(error, NetworkError):
            self.errors["network_errors"].append(error_info)
        else:
            self.errors["other_errors"].append(error_info)

    def get_summary(self) -> dict:
        """Get error summary statistics"""
        total_errors = sum(len(errors) for errors in self.errors.values())

        return {
            "name": self.name,
            "total_processed": self.counts["total_processed"],
            "successful": self.counts["successful"],
            "failed": self.counts["failed"],
            "success_rate": (
                self.counts["successful"] / self.counts["total_processed"]
                if self.counts["total_processed"] > 0 else 0
            ),
            "error_breakdown": {
                error_type: len(errors)
                for error_type, errors in self.errors.items()
                if errors
            },
            "total_errors": total_errors,
        }

    def log_summary(self, logger_instance: logging.Logger):
        """Log error summary"""
        summary = self.get_summary()

        logger_instance.info(f"Error Summary for {summary['name']}:")
        logger_instance.info(f"  Total processed: {summary['total_processed']}")
        logger_instance.info(f"  Successful: {summary['successful']}")
        logger_instance.info(f"  Failed: {summary['failed']}")
        logger_instance.info(f"  Success rate: {summary['success_rate']:.2%}")

        if summary["error_breakdown"]:
            logger_instance.info("  Error breakdown:")
            for error_type, count in summary["error_breakdown"].items():
                logger_instance.info(f"    {error_type}: {count}")

        # Log sample errors for each type
        for error_type, errors in self.errors.items():
            if errors:
                logger_instance.debug(f"Sample {error_type}:")
                for error in errors[:3]:  # Show first 3 errors
                    logger_instance.debug(f"  Record {error['record_id']}: {error['message']}")
                if len(errors) > 3:
                    logger_instance.debug(f"  ... and {len(errors) - 3} more")

    def get_failed_records(self) -> list:
        """Get list of record IDs that failed"""
        failed_records = []
        for error_list in self.errors.values():
            for error in error_list:
                if error["record_id"]:
                    failed_records.append(error["record_id"])
        return failed_records


def handle_database_errors(func: Callable) -> Callable:
    """
    Decorator to handle common database errors with appropriate retries
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        from sqlalchemy.exc import (
            DataError,
            DisconnectionError,
            IntegrityError,
            OperationalError,
            TimeoutError,
        )

        try:
            return func(*args, **kwargs)
        except (DisconnectionError, TimeoutError, OperationalError) as e:
            # Transient errors - these can be retried
            logger.warning(f"Database transient error in {func.__name__}: {e}")
            msg = f"Transient database error: {e}"
            raise DatabaseError(msg)
        except IntegrityError as e:
            # Data integrity issues - don't retry but log clearly
            logger.exception(f"Database integrity error in {func.__name__}: {e}")
            msg = f"Data integrity error: {e}"
            raise DatabaseError(msg)
        except DataError as e:
            # Data format/type errors - don't retry
            logger.exception(f"Database data error in {func.__name__}: {e}")
            msg = f"Data format error: {e}"
            raise DatabaseError(msg)
        except Exception as e:
            # Other database errors
            logger.exception(f"Unexpected database error in {func.__name__}: {e}")
            msg = f"Database error: {e}"
            raise DatabaseError(msg)

    return wrapper


def log_function_performance(func: Callable) -> Callable:
    """
    Decorator to log function performance metrics
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_logger = logging.getLogger(func.__module__)
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Log performance for slow functions
            if execution_time > 1.0:  # More than 1 second
                func_logger.info(f"Function {func.__name__} completed in {execution_time:.2f}s")
            elif execution_time > 10.0:  # More than 10 seconds
                func_logger.warning(f"Slow function {func.__name__} took {execution_time:.2f}s")

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            func_logger.exception(f"Function {func.__name__} failed after {execution_time:.2f}s: {e}")
            raise

    return wrapper


# Convenience function for common retry scenarios
def retry_database_operation(func: Callable) -> Callable:
    """Retry decorator specifically for database operations"""
    return retry_on_error(
        max_attempts=3,
        delay=1.0,
        backoff=2.0,
        exceptions=(DatabaseError, ConnectionError, TimeoutError),
        logger_name="database_retry",
    )(handle_database_errors(func))


def retry_network_operation(func: Callable) -> Callable:
    """Retry decorator specifically for network operations"""
    import requests

    return retry_on_error(
        max_attempts=5,
        delay=2.0,
        backoff=1.5,
        exceptions=(requests.exceptions.RequestException, NetworkError, ConnectionError),
        logger_name="network_retry",
    )(func)
