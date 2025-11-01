"""
Enhanced logging utilities for Microsoft Sentinel Log Aggregator.

Provides structured logging with correlation IDs, performance metrics,
and Azure SDK-compliant logging patterns.
"""

import logging
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Dict, Optional, Union


class SentinelLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds context information to all log messages.

    Automatically includes correlation IDs, workspace information, and timing data.
    """

    def __init__(self, logger: logging.Logger, extra: Optional[Dict[str, Any]] = None):
        super().__init__(logger, extra or {})
        self.correlation_id = str(uuid.uuid4())

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process log message to include context information."""
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        extra["correlation_id"] = self.correlation_id
        extra["timestamp"] = datetime.now(timezone.utc).isoformat()
        kwargs["extra"] = extra
        return msg, kwargs

    def set_workspace_context(self, workspace_id: str, workspace_name: str = None):
        """Set workspace context for all subsequent log messages."""
        self.extra["workspace_id"] = (
            workspace_id[:8] + "..." if len(workspace_id) > 8 else workspace_id
        )
        if workspace_name:
            self.extra["workspace_name"] = workspace_name

    def set_query_context(self, query_name: str, query_id: Optional[str] = None):
        """Set query context for all subsequent log messages."""
        self.extra["query_name"] = query_name
        if query_id:
            self.extra["query_id"] = query_id

    def clear_context(self):
        """Clear all context information."""
        keys_to_remove = [k for k in self.extra.keys() if k not in ["correlation_id"]]
        for key in keys_to_remove:
            del self.extra[key]


@contextmanager
def performance_timer(logger: Union[logging.Logger, SentinelLoggerAdapter], operation_name: str):
    """
    Context manager for timing operations and logging performance metrics.

    Args:
        logger: Logger instance to use for metrics
        operation_name: Name of the operation being timed

    Example:
        with performance_timer(logger, "query_execution"):
            # Perform query operation
            pass
    """
    start_time = time.perf_counter()
    logger.info(f"🚀 Starting {operation_name}")

    try:
        yield
        duration = time.perf_counter() - start_time
        logger.info(
            f"✅ Completed {operation_name}",
            extra={
                "operation": operation_name,
                "duration_seconds": round(duration, 3),
                "status": "success",
            },
        )
    except Exception as e:
        duration = time.perf_counter() - start_time
        logger.error(
            f"❌ Failed {operation_name}: {str(e)}",
            extra={
                "operation": operation_name,
                "duration_seconds": round(duration, 3),
                "status": "error",
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise


def log_performance(operation_name: Optional[str] = None):
    """
    Decorator for logging function performance.

    Args:
        operation_name: Optional custom name for the operation

    Example:
        @log_performance("data_processing")
        async def process_data():
            pass
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            name = operation_name or f"{func.__name__}"

            with performance_timer(logger, name):
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            name = operation_name or f"{func.__name__}"

            with performance_timer(logger, name):
                return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def get_logger(name: str, correlation_id: Optional[str] = None) -> SentinelLoggerAdapter:
    """
    Get a logger adapter with enhanced context capabilities.

    Args:
        name: Logger name (typically __name__)
        correlation_id: Optional correlation ID for request tracking

    Returns:
        Enhanced logger adapter with context support
    """
    base_logger = logging.getLogger(name)
    adapter = SentinelLoggerAdapter(base_logger)

    if correlation_id:
        adapter.correlation_id = correlation_id

    return adapter


def configure_logging(
    level: str = "INFO", format_string: Optional[str] = None, enable_structured: bool = True
) -> None:
    """
    Configure logging for the Sentinel Log Aggregator.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        format_string: Custom format string
        enable_structured: Whether to enable structured logging
    """
    if format_string is None:
        if enable_structured:
            format_string = (
                "%(asctime)s | %(levelname)s | %(name)s | " "%(correlation_id)s | %(message)s"
            )
        else:
            format_string = "%(asctime)s | %(levelname)s | %(message)s"

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()), format=format_string, datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Configure Azure SDK logging
    azure_logger = logging.getLogger("azure")
    azure_logger.setLevel(logging.WARNING)

    # Configure urllib3 logging (used by requests/aiohttp)
    urllib3_logger = logging.getLogger("urllib3")
    urllib3_logger.setLevel(logging.WARNING)


class LogContext:
    """
    Context manager for temporary logging context.

    Example:
        logger = get_logger(__name__)
        with LogContext(logger, workspace_id="ws123", query_name="incidents"):
            logger.info("Processing query")  # Will include context
    """

    def __init__(self, logger: SentinelLoggerAdapter, **context):
        self.logger = logger
        self.context = context
        self.original_extra = None

    def __enter__(self):
        self.original_extra = self.logger.extra.copy()
        self.logger.extra.update(self.context)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.extra = self.original_extra
