"""
Comprehensive tests for sentinel_log_aggregator.logging_utils module.

Tests cover SentinelLoggerAdapter, performance_timer, log_performance decorator,
get_logger, configure_logging, LogContext and all logging functionality.
"""

import asyncio
import logging
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from io import StringIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from sentinel_log_aggregator.logging_utils import (
    LogContext,
    SentinelLoggerAdapter,
    configure_logging,
    get_logger,
    log_performance,
    performance_timer,
)


class TestSentinelLoggerAdapter:
    """Test SentinelLoggerAdapter functionality."""

    def test_adapter_initialization(self):
        """Test basic adapter initialization."""
        logger = logging.getLogger("test_logger")
        adapter = SentinelLoggerAdapter(logger)

        assert adapter.logger == logger
        assert isinstance(adapter.correlation_id, str)
        assert len(adapter.correlation_id) == 36  # UUID4 length
        assert adapter.extra == {}

    def test_adapter_initialization_with_extra(self):
        """Test adapter initialization with extra context."""
        logger = logging.getLogger("test_logger")
        extra = {"test_key": "test_value"}
        adapter = SentinelLoggerAdapter(logger, extra)

        assert adapter.extra == extra
        assert isinstance(adapter.correlation_id, str)

    def test_process_message_adds_context(self):
        """Test that process method adds correlation ID and timestamp."""
        logger = logging.getLogger("test_logger")
        adapter = SentinelLoggerAdapter(logger)

        msg = "test message"
        kwargs = {}

        processed_msg, processed_kwargs = adapter.process(msg, kwargs)

        assert processed_msg == msg
        assert "extra" in processed_kwargs
        assert "correlation_id" in processed_kwargs["extra"]
        assert "timestamp" in processed_kwargs["extra"]
        assert processed_kwargs["extra"]["correlation_id"] == adapter.correlation_id

    def test_process_message_preserves_existing_extra(self):
        """Test that process method preserves existing extra data."""
        logger = logging.getLogger("test_logger")
        adapter = SentinelLoggerAdapter(logger, {"initial": "value"})

        msg = "test message"
        kwargs = {"extra": {"existing": "data"}}

        processed_msg, processed_kwargs = adapter.process(msg, kwargs)

        extra = processed_kwargs["extra"]
        assert extra["initial"] == "value"
        assert extra["existing"] == "data"
        assert "correlation_id" in extra
        assert "timestamp" in extra

    def test_set_workspace_context(self):
        """Test setting workspace context."""
        logger = logging.getLogger("test_logger")
        adapter = SentinelLoggerAdapter(logger)

        workspace_id = "12345678-1234-1234-1234-123456789012"
        workspace_name = "test-workspace"

        adapter.set_workspace_context(workspace_id, workspace_name)

        assert adapter.extra["workspace_id"] == "12345678-1234-1234-1234-123456789012"
        assert adapter.extra["workspace_name"] == workspace_name

    def test_set_workspace_context_short_id(self):
        """Test setting workspace context with short ID."""
        logger = logging.getLogger("test_logger")
        adapter = SentinelLoggerAdapter(logger)

        workspace_id = "short"
        adapter.set_workspace_context(workspace_id)

        assert adapter.extra["workspace_id"] == "short"
        assert "workspace_name" not in adapter.extra

    def test_set_query_context(self):
        """Test setting query context."""
        logger = logging.getLogger("test_logger")
        adapter = SentinelLoggerAdapter(logger)

        query_name = "test_query"
        query_id = "query-123"

        adapter.set_query_context(query_name, query_id)

        assert adapter.extra["query_name"] == query_name
        assert adapter.extra["query_id"] == query_id

    def test_set_query_context_without_id(self):
        """Test setting query context without query ID."""
        logger = logging.getLogger("test_logger")
        adapter = SentinelLoggerAdapter(logger)

        query_name = "test_query"
        adapter.set_query_context(query_name)

        assert adapter.extra["query_name"] == query_name
        assert "query_id" not in adapter.extra

    def test_clear_context(self):
        """Test clearing context while preserving correlation ID."""
        logger = logging.getLogger("test_logger")
        adapter = SentinelLoggerAdapter(logger)

        # Set various context
        adapter.set_workspace_context("workspace-123", "test-ws")
        adapter.set_query_context("test_query", "query-123")
        adapter.extra["custom"] = "value"

        original_correlation_id = adapter.correlation_id

        adapter.clear_context()

        # Only correlation_id should remain
        assert len(adapter.extra) == 0
        assert adapter.correlation_id == original_correlation_id


class TestPerformanceTimer:
    """Test performance_timer context manager."""

    def test_performance_timer_success(self, caplog):
        """Test performance timer with successful operation."""
        logger = logging.getLogger("test_timer")
        logger.setLevel(logging.INFO)

        with performance_timer(logger, "test_operation"):
            time.sleep(0.01)  # Small delay

        records = [r for r in caplog.records if r.name == "test_timer"]
        assert len(records) == 2

        start_record = records[0]
        assert "Starting test_operation" in start_record.message

        end_record = records[1]
        assert "Completed test_operation" in end_record.message
        assert hasattr(end_record, "operation")
        assert hasattr(end_record, "duration_seconds")
        assert hasattr(end_record, "status")
        assert end_record.operation == "test_operation"
        assert end_record.status == "success"
        assert end_record.duration_seconds > 0

    def test_performance_timer_exception(self, caplog):
        """Test performance timer with exception."""
        logger = logging.getLogger("test_timer_error")
        logger.setLevel(logging.INFO)

        with pytest.raises(ValueError):
            with performance_timer(logger, "failing_operation"):
                raise ValueError("Test error")

        records = [r for r in caplog.records if r.name == "test_timer_error"]
        assert len(records) == 2

        start_record = records[0]
        assert "Starting failing_operation" in start_record.message

        error_record = records[1]
        assert "Failed failing_operation" in error_record.message
        assert hasattr(error_record, "operation")
        assert hasattr(error_record, "duration_seconds")
        assert hasattr(error_record, "status")
        assert hasattr(error_record, "error_type")
        assert error_record.operation == "failing_operation"
        assert error_record.status == "error"
        assert error_record.error_type == "ValueError"

    def test_performance_timer_with_adapter(self, caplog):
        """Test performance timer with SentinelLoggerAdapter."""
        base_logger = logging.getLogger("test_adapter_timer")
        base_logger.setLevel(logging.INFO)
        adapter = SentinelLoggerAdapter(base_logger)

        with performance_timer(adapter, "adapter_operation"):
            pass

        records = [r for r in caplog.records if r.name == "test_adapter_timer"]
        assert len(records) == 2

        # Check that correlation ID is included
        for record in records:
            assert hasattr(record, "correlation_id")


class TestLogPerformanceDecorator:
    """Test log_performance decorator."""

    def test_sync_function_decorator(self, caplog):
        """Test decorator on synchronous function."""

        @log_performance("sync_test")
        def sync_function(x, y):
            return x + y

        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        result = sync_function(2, 3)
        assert result == 5

        # Check logs
        records = [r for r in caplog.records if "sync_test" in r.message]
        assert len(records) == 2
        assert "Starting sync_test" in records[0].message
        assert "Completed sync_test" in records[1].message

    def test_sync_function_decorator_default_name(self, caplog):
        """Test decorator with default function name."""

        @log_performance()
        def test_function():
            return "result"

        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        result = test_function()
        assert result == "result"

        # Check logs use function name
        records = [r for r in caplog.records if "test_function" in r.message]
        assert len(records) == 2

    def test_async_function_decorator(self, caplog):
        """Test decorator on async function."""

        @log_performance("async_test")
        async def async_function(x):
            await asyncio.sleep(0.001)
            return x * 2

        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        async def run_test():
            result = await async_function(5)
            assert result == 10

        asyncio.run(run_test())

        # Check logs
        records = [r for r in caplog.records if "async_test" in r.message]
        assert len(records) == 2
        assert "Starting async_test" in records[0].message
        assert "Completed async_test" in records[1].message

    def test_sync_function_decorator_exception(self, caplog):
        """Test decorator with exception in sync function."""

        @log_performance("sync_error_test")
        def failing_function():
            raise RuntimeError("Test error")

        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        with pytest.raises(RuntimeError):
            failing_function()

        # Check error is logged
        records = [r for r in caplog.records if "sync_error_test" in r.message]
        assert len(records) == 2
        assert "Failed sync_error_test" in records[1].message

    def test_async_function_decorator_exception(self, caplog):
        """Test decorator with exception in async function."""

        @log_performance("async_error_test")
        async def failing_async_function():
            raise ValueError("Async test error")

        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        async def run_test():
            with pytest.raises(ValueError):
                await failing_async_function()

        asyncio.run(run_test())

        # Check error is logged
        records = [r for r in caplog.records if "async_error_test" in r.message]
        assert len(records) == 2
        assert "Failed async_error_test" in records[1].message


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_basic(self):
        """Test basic get_logger functionality."""
        adapter = get_logger("test.module")

        assert isinstance(adapter, SentinelLoggerAdapter)
        assert adapter.logger.name == "test.module"
        assert isinstance(adapter.correlation_id, str)

    def test_get_logger_with_correlation_id(self):
        """Test get_logger with custom correlation ID."""
        custom_id = "custom-correlation-id"
        adapter = get_logger("test.module", custom_id)

        assert adapter.correlation_id == custom_id

    def test_get_logger_generates_different_ids(self):
        """Test that different logger instances get different correlation IDs."""
        adapter1 = get_logger("test.module1")
        adapter2 = get_logger("test.module2")

        assert adapter1.correlation_id != adapter2.correlation_id


class TestConfigureLogging:
    """Test configure_logging function."""

    def test_configure_logging_default(self):
        """Test configure_logging with default parameters."""
        with patch("logging.basicConfig") as mock_basic_config:
            configure_logging()

            mock_basic_config.assert_called_once()
            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs["level"] == logging.INFO
            assert "correlation_id" in call_kwargs["format"]

    def test_configure_logging_custom_level(self):
        """Test configure_logging with custom level."""
        with patch("logging.basicConfig") as mock_basic_config:
            configure_logging(level="DEBUG")

            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs["level"] == logging.DEBUG

    def test_configure_logging_custom_format(self):
        """Test configure_logging with custom format."""
        custom_format = "%(levelname)s - %(message)s"

        with patch("logging.basicConfig") as mock_basic_config:
            configure_logging(format_string=custom_format)

            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs["format"] == custom_format

    def test_configure_logging_no_structured(self):
        """Test configure_logging with structured logging disabled."""
        with patch("logging.basicConfig") as mock_basic_config:
            configure_logging(enable_structured=False)

            call_kwargs = mock_basic_config.call_args[1]
            assert "correlation_id" not in call_kwargs["format"]

    def test_configure_logging_sets_azure_logger_level(self):
        """Test that Azure logger level is configured."""
        with patch("logging.basicConfig"), patch("logging.getLogger") as mock_get_logger:

            mock_azure_logger = Mock()
            mock_urllib3_logger = Mock()

            def get_logger_side_effect(name):
                if name == "azure":
                    return mock_azure_logger
                elif name == "urllib3":
                    return mock_urllib3_logger
                return Mock()

            mock_get_logger.side_effect = get_logger_side_effect

            configure_logging()

            mock_azure_logger.setLevel.assert_called_with(logging.WARNING)
            mock_urllib3_logger.setLevel.assert_called_with(logging.WARNING)


class TestLogContext:
    """Test LogContext context manager."""

    def test_log_context_basic(self):
        """Test basic LogContext functionality."""
        logger = logging.getLogger("test_context")
        adapter = SentinelLoggerAdapter(logger)

        original_extra = adapter.extra.copy()

        with LogContext(adapter, test_key="test_value", workspace="ws123") as ctx_logger:
            assert ctx_logger == adapter
            assert adapter.extra["test_key"] == "test_value"
            assert adapter.extra["workspace"] == "ws123"

        # Context should be restored
        assert adapter.extra == original_extra

    def test_log_context_preserves_existing_context(self):
        """Test that LogContext preserves existing context."""
        logger = logging.getLogger("test_context")
        adapter = SentinelLoggerAdapter(logger, {"existing": "value"})

        with LogContext(adapter, new_key="new_value"):
            assert adapter.extra["existing"] == "value"
            assert adapter.extra["new_key"] == "new_value"

        # Should restore to original state
        assert adapter.extra == {"existing": "value"}

    def test_log_context_exception_handling(self):
        """Test LogContext restores context even with exceptions."""
        logger = logging.getLogger("test_context")
        adapter = SentinelLoggerAdapter(logger, {"original": "data"})

        try:
            with LogContext(adapter, temp_key="temp_value"):
                assert adapter.extra["temp_key"] == "temp_value"
                raise ValueError("Test error")
        except ValueError:
            pass

        # Context should be restored despite exception
        assert adapter.extra == {"original": "data"}
        assert "temp_key" not in adapter.extra

    def test_log_context_nested(self):
        """Test nested LogContext managers."""
        logger = logging.getLogger("test_context")
        adapter = SentinelLoggerAdapter(logger, {"base": "value"})

        with LogContext(adapter, level1="value1"):
            assert adapter.extra["level1"] == "value1"

            with LogContext(adapter, level2="value2"):
                assert adapter.extra["level1"] == "value1"
                assert adapter.extra["level2"] == "value2"

            # Inner context should be restored
            assert adapter.extra["level1"] == "value1"
            assert "level2" not in adapter.extra

        # All context should be restored
        assert adapter.extra == {"base": "value"}


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple logging features."""

    def test_full_logging_workflow(self, caplog):
        """Test complete logging workflow with context and performance timing."""
        logger = get_logger(__name__)
        logger.logger.setLevel(logging.INFO)

        with LogContext(logger, workspace_id="ws-123", query_name="test_query"):
            with performance_timer(logger, "complete_workflow"):
                logger.info("Processing data")
                time.sleep(0.001)

        # Check that all context is properly included
        records = [r for r in caplog.records if r.name == __name__]
        assert len(records) >= 3  # start, info, complete

        # Find the info record
        info_records = [r for r in records if "Processing data" in r.message]
        assert len(info_records) == 1

        info_record = info_records[0]
        assert hasattr(info_record, "correlation_id")
        assert hasattr(info_record, "workspace_id")
        assert hasattr(info_record, "query_name")

    def test_decorator_with_context(self, caplog):
        """Test performance decorator with logging context."""

        @log_performance("decorated_operation")
        def operation_with_context():
            logger = get_logger(__name__)
            logger.logger.setLevel(logging.INFO)
            logger.info("Inside decorated function")
            return "result"

        result = operation_with_context()
        assert result == "result"

        # Check both decorator and function logs are present
        records = [r for r in caplog.records]
        operation_records = [r for r in records if "decorated_operation" in r.message]
        function_records = [r for r in records if "Inside decorated function" in r.message]

        assert len(operation_records) == 2  # start and complete
        assert len(function_records) == 1

    def test_multiple_adapters_different_correlation_ids(self):
        """Test that different adapters maintain separate correlation IDs."""
        adapter1 = get_logger("module1")
        adapter2 = get_logger("module2")

        adapter1.set_workspace_context("ws1", "workspace1")
        adapter2.set_workspace_context("ws2", "workspace2")

        # Each adapter should maintain its own context
        assert adapter1.extra["workspace_name"] == "workspace1"
        assert adapter2.extra["workspace_name"] == "workspace2"
        assert adapter1.correlation_id != adapter2.correlation_id


class TestErrorHandling:
    """Test error handling in logging utilities."""

    def test_adapter_with_none_extra(self):
        """Test adapter handles None extra gracefully."""
        logger = logging.getLogger("test")
        adapter = SentinelLoggerAdapter(logger, None)

        msg, kwargs = adapter.process("test", {})
        assert "extra" in kwargs
        assert "correlation_id" in kwargs["extra"]

    def test_performance_timer_with_none_logger(self):
        """Test performance timer with invalid logger."""
        with pytest.raises(AttributeError):
            with performance_timer(None, "test"):
                pass

    def test_log_context_initialization(self):
        """Test LogContext initialization edge cases."""
        logger = logging.getLogger("test")
        adapter = SentinelLoggerAdapter(logger)

        # Test with empty context
        context_mgr = LogContext(adapter)
        assert context_mgr.context == {}

        # Test with None values
        context_mgr = LogContext(adapter, key=None)
        assert context_mgr.context == {"key": None}
