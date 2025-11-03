"""
Comprehensive tests for the logging formatter module.

Tests cover message formatting, structured logging, context handling,
and proper integration with Python's logging system.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

from sentinel_log_aggregator.logging_formatter import (
    ContextualLogger,
    LogEventType,
    SentinelLogFormatter,
)


class TestLogEventType:
    """Test LogEventType enum."""

    def test_all_event_types_exist(self):
        """Test that all expected event types are defined."""
        expected_types = [
            "BATCH_START",
            "BATCH_END",
            "QUERY_START",
            "QUERY_END",
            "UPLOAD_START",
            "UPLOAD_END",
            "WORKSPACE_CONFIG",
            "ERROR",
            "PROGRESS",
            "SUMMARY",
        ]

        for event_type in expected_types:
            assert hasattr(LogEventType, event_type)
            assert LogEventType[event_type].value == event_type

    def test_event_type_values(self):
        """Test that event types have correct string values."""
        assert LogEventType.BATCH_START.value == "BATCH_START"
        assert LogEventType.ERROR.value == "ERROR"
        assert LogEventType.PROGRESS.value == "PROGRESS"


class TestSentinelLogFormatter:
    """Test SentinelLogFormatter static methods."""

    def test_format_batch_start(self):
        """Test batch start message formatting."""
        result = SentinelLogFormatter.format_batch_start(
            job_id="test-job-123", total_days=7, batch_hours=24, workspace_count=5
        )

        expected = "[BATCH_START] Job: test-job-123 | Range: 7d (24h batches) | Workspaces: 5"
        assert result == expected

    def test_format_batch_end(self):
        """Test batch end message formatting."""
        summary = {
            "successful_queries": 8,
            "total_queries": 10,
            "successful_uploads": 7,
            "total_uploads": 8,
            "total_records": 15000,
            "total_uploaded": 14500,
            "total_duration": 120.5,
        }

        result = SentinelLogFormatter.format_batch_end("test-job-123", summary)

        expected = (
            "[BATCH_END] Job: test-job-123 | "
            "Queries: 8/10 | "
            "Uploads: 7/8 | "
            "Records: 15,000 retrieved, 14,500 uploaded | "
            "Duration: 120.5s"
        )
        assert result == expected

    def test_format_batch_end_with_missing_values(self):
        """Test batch end formatting with missing summary values."""
        summary = {"total_duration": 60.0}  # Missing other values

        result = SentinelLogFormatter.format_batch_end("test-job-456", summary)

        expected = (
            "[BATCH_END] Job: test-job-456 | "
            "Queries: 0/0 | "
            "Uploads: 0/0 | "
            "Records: 0 retrieved, 0 uploaded | "
            "Duration: 60.0s"
        )
        assert result == expected

    def test_format_query_start(self):
        """Test query start message formatting."""
        result = SentinelLogFormatter.format_query_start(
            job_id="test-job-789",
            query_name="incident_summary",
            workspace_alias="workspace-alpha",
            time_range="2024-01-01 to 2024-01-02",
        )

        expected = (
            "[QUERY_START] Job: test-job-789 | "
            "Query: incident_summary | "
            "Workspace: workspace-alpha | "
            "TimeRange: 2024-01-01 to 2024-01-02"
        )
        assert result == expected

    def test_format_query_end_success(self):
        """Test successful query end message formatting."""
        result = SentinelLogFormatter.format_query_end(
            job_id="test-job-789",
            query_name="incident_summary",
            workspace_alias="workspace-alpha",
            record_count=1250,
            duration=15.75,
            success=True,
        )

        expected = (
            "[QUERY_END] Job: test-job-789 | "
            "Query: incident_summary | "
            "Workspace: workspace-alpha | "
            "Status: SUCCESS | "
            "Records: 1,250 | "
            "Duration: 15.75s"
        )
        assert result == expected

    def test_format_query_end_failure(self):
        """Test failed query end message formatting."""
        result = SentinelLogFormatter.format_query_end(
            job_id="test-job-789",
            query_name="incident_summary",
            workspace_alias="workspace-alpha",
            record_count=0,
            duration=5.25,
            success=False,
        )

        expected = (
            "[QUERY_END] Job: test-job-789 | "
            "Query: incident_summary | "
            "Workspace: workspace-alpha | "
            "Status: FAILED | "
            "Records: 0 | "
            "Duration: 5.25s"
        )
        assert result == expected

    def test_format_query_end_with_mock_objects(self):
        """Test query end formatting with MagicMock objects."""
        mock_duration = MagicMock()
        mock_duration.__str__ = Mock(return_value="mock_duration")

        mock_count = MagicMock()
        mock_count.__str__ = Mock(return_value="mock_count")

        result = SentinelLogFormatter.format_query_end(
            job_id="test-job",
            query_name="test_query",
            workspace_alias="test_workspace",
            record_count=mock_count,
            duration=mock_duration,
            success=True,
        )

        assert "mock_duration" in result
        assert "mock_count" in result
        assert "SUCCESS" in result

    def test_format_upload_start(self):
        """Test upload start message formatting."""
        result = SentinelLogFormatter.format_upload_start(
            job_id="test-job-upload",
            query_name="alert_summary",
            workspace_alias="workspace-beta",
            record_count=750,
        )

        expected = (
            "[UPLOAD_START] Job: test-job-upload | "
            "Query: alert_summary | "
            "Workspace: workspace-beta | "
            "Records: 750"
        )
        assert result == expected

    def test_format_upload_start_with_mock_count(self):
        """Test upload start formatting with MagicMock record count."""
        mock_count = MagicMock()
        mock_count.__str__ = Mock(return_value="mock_record_count")

        result = SentinelLogFormatter.format_upload_start(
            job_id="test-job",
            query_name="test_query",
            workspace_alias="test_workspace",
            record_count=mock_count,
        )

        assert "mock_record_count" in result

    def test_format_upload_end_success(self):
        """Test successful upload end message formatting."""
        result = SentinelLogFormatter.format_upload_end(
            job_id="test-job-upload",
            query_name="alert_summary",
            workspace_alias="workspace-beta",
            uploaded_count=750,
            duration=8.5,
            success=True,
        )

        expected = (
            "[UPLOAD_END] Job: test-job-upload | "
            "Query: alert_summary | "
            "Workspace: workspace-beta | "
            "Status: SUCCESS | "
            "Uploaded: 750 | "
            "Duration: 8.50s"
        )
        assert result == expected

    def test_format_upload_end_failure(self):
        """Test failed upload end message formatting."""
        result = SentinelLogFormatter.format_upload_end(
            job_id="test-job-upload",
            query_name="alert_summary",
            workspace_alias="workspace-beta",
            uploaded_count=0,
            duration=2.1,
            success=False,
        )

        expected = (
            "[UPLOAD_END] Job: test-job-upload | "
            "Query: alert_summary | "
            "Workspace: workspace-beta | "
            "Status: FAILED | "
            "Uploaded: 0 | "
            "Duration: 2.10s"
        )
        assert result == expected

    def test_format_upload_end_with_mock_objects(self):
        """Test upload end formatting with MagicMock objects."""
        mock_count = MagicMock()
        mock_count.__str__ = Mock(return_value="mock_uploaded")

        mock_duration = MagicMock()
        mock_duration.__str__ = Mock(return_value="mock_duration")

        result = SentinelLogFormatter.format_upload_end(
            job_id="test-job",
            query_name="test_query",
            workspace_alias="test_workspace",
            uploaded_count=mock_count,
            duration=mock_duration,
            success=True,
        )

        assert "mock_uploaded" in result
        assert "mock_duration" in result

    def test_format_error_minimal(self):
        """Test error formatting with minimal context."""
        result = SentinelLogFormatter.format_error(
            job_id="error-job-123", component="QueryEngine", error_message="Connection timeout"
        )

        expected = "Job: error-job-123 | Component: QueryEngine | Message: Connection timeout"
        assert result == expected

    def test_format_error_full_context(self):
        """Test error formatting with full context."""
        result = SentinelLogFormatter.format_error(
            job_id="error-job-456",
            component="DataUploader",
            query_name="incident_summary",
            workspace_alias="prod-workspace",
            error_message="Invalid schema",
            error_type="ValidationError",
        )

        expected = (
            "Job: error-job-456 | "
            "Component: DataUploader | "
            "Query: incident_summary | "
            "Workspace: prod-workspace | "
            "ErrorType: ValidationError | "
            "Message: Invalid schema"
        )
        assert result == expected

    def test_format_error_partial_context(self):
        """Test error formatting with partial context."""
        result = SentinelLogFormatter.format_error(
            job_id="error-job-789",
            component="ConfigLoader",
            query_name="alert_summary",
            error_message="Missing required field",
            error_type="ConfigurationError",
        )

        expected = (
            "Job: error-job-789 | "
            "Component: ConfigLoader | "
            "Query: alert_summary | "
            "ErrorType: ConfigurationError | "
            "Message: Missing required field"
        )
        assert result == expected

    def test_format_progress(self):
        """Test progress message formatting."""
        result = SentinelLogFormatter.format_progress(
            job_id="progress-job-123", completed=7, total=10
        )

        expected = "[PROGRESS] Job: progress-job-123 | Completed: 7/10 (70.0%)"
        assert result == expected

    def test_format_progress_with_additional_info(self):
        """Test progress formatting with additional information."""
        result = SentinelLogFormatter.format_progress(
            job_id="progress-job-456",
            completed=3,
            total=8,
            additional_info="Processing workspace-gamma",
        )

        expected = (
            "[PROGRESS] Job: progress-job-456 | "
            "Completed: 3/8 (37.5%) | "
            "Processing workspace-gamma"
        )
        assert result == expected

    def test_format_progress_zero_total(self):
        """Test progress formatting with zero total."""
        result = SentinelLogFormatter.format_progress(
            job_id="progress-job-zero", completed=0, total=0
        )

        expected = "[PROGRESS] Job: progress-job-zero | Completed: 0/0 (0.0%)"
        assert result == expected

    def test_format_workspace_config_valid(self):
        """Test workspace config formatting when valid."""
        result = SentinelLogFormatter.format_workspace_config(
            workspace_count=15, report_count=8, subscription_count=3, error_count=0
        )

        expected = (
            "[WORKSPACE_CONFIG] Status: VALID | " "Workspaces: 15 | Reports: 8 | Subscriptions: 3"
        )
        assert result == expected

    def test_format_workspace_config_with_errors(self):
        """Test workspace config formatting with errors."""
        result = SentinelLogFormatter.format_workspace_config(
            workspace_count=12, report_count=6, subscription_count=2, error_count=3
        )

        expected = (
            "[WORKSPACE_CONFIG] Status: ERRORS (3) | "
            "Workspaces: 12 | Reports: 6 | Subscriptions: 2"
        )
        assert result == expected

    def test_format_config_validation_valid(self):
        """Test config validation formatting when valid."""
        result = SentinelLogFormatter.format_config_validation(
            component="AzureCredentials",
            is_valid=True,
            details="All required environment variables present",
        )

        expected = (
            "[CONFIG_VALIDATION] Component: AzureCredentials | "
            "Status: VALID | "
            "Details: All required environment variables present"
        )
        assert result == expected

    def test_format_config_validation_invalid(self):
        """Test config validation formatting when invalid."""
        result = SentinelLogFormatter.format_config_validation(
            component="WorkspaceConfig", is_valid=False, details="Missing workspace_id field"
        )

        expected = (
            "[CONFIG_VALIDATION] Component: WorkspaceConfig | "
            "Status: INVALID | "
            "Details: Missing workspace_id field"
        )
        assert result == expected

    def test_format_config_validation_no_details(self):
        """Test config validation formatting without details."""
        result = SentinelLogFormatter.format_config_validation(
            component="DatabaseConnection", is_valid=True
        )

        expected = "[CONFIG_VALIDATION] Component: DatabaseConnection | Status: VALID"
        assert result == expected

    def test_format_batch_summary(self):
        """Test batch summary formatting."""
        summary_data = {
            "overview": {
                "total_workspaces": 5,
                "total_unique_queries": 12,
                "total_duration_seconds": 245.7,
                "total_records_downloaded": 25000,
                "total_records_uploaded": 24800,
            }
        }

        result = SentinelLogFormatter.format_batch_summary("summary-job-123", summary_data)

        expected = (
            "[BATCH_SUMMARY] Job: summary-job-123 | "
            "Workspaces: 5 | "
            "Queries: 12 | "
            "Duration: 245.7s | "
            "Downloaded: 25000 | "
            "Uploaded: 24800"
        )
        assert result == expected

    def test_format_batch_summary_missing_overview(self):
        """Test batch summary formatting with missing overview."""
        summary_data = {}

        result = SentinelLogFormatter.format_batch_summary("summary-job-456", summary_data)

        expected = (
            "[BATCH_SUMMARY] Job: summary-job-456 | "
            "Workspaces: 0 | "
            "Queries: 0 | "
            "Duration: 0.0s | "
            "Downloaded: 0 | "
            "Uploaded: 0"
        )
        assert result == expected

    def test_format_workspace_query_detail(self):
        """Test workspace query detail formatting."""
        workspace_query = {
            "workspaceId": "ws-12345678",
            "query": "incident_summary",
            "logsDownloaded": 1500,
            "uploadSuccess": 1450,
            "uploadFailure": 50,
            "avgQueryTime": 12.5,
            "totalQueryTime": 125.0,
            "queryExecutions": 10,
            "startTimeRange": "2024-01-01T00:00:00Z",
            "endTimeRange": "2024-01-02T00:00:00Z",
        }

        result = SentinelLogFormatter.format_workspace_query_detail(workspace_query)

        expected_parts = [
            "workspaceId=ws-12345678",
            "query=incident_summary",
            "logsDownloaded=1500",
            "uploadSuccess=1450",
            "uploadFailure=50",
            "avgQueryTime=12.50s",
            "totalQueryTime=125.00s",
            "queryExecutions=10",
            "startTimeRange=2024-01-01T00:00:00Z",
            "endTimeRange=2024-01-02T00:00:00Z",
        ]
        expected = " | ".join(expected_parts)
        assert result == expected

    def test_format_workspace_query_detail_missing_values(self):
        """Test workspace query detail formatting with missing values."""
        workspace_query = {"query": "alert_summary"}

        result = SentinelLogFormatter.format_workspace_query_detail(workspace_query)

        expected_parts = [
            "workspaceId=unknown",
            "query=alert_summary",
            "logsDownloaded=0",
            "uploadSuccess=0",
            "uploadFailure=0",
            "avgQueryTime=0.00s",
            "totalQueryTime=0.00s",
            "queryExecutions=0",
            "startTimeRange=unknown",
            "endTimeRange=unknown",
        ]
        expected = " | ".join(expected_parts)
        assert result == expected


class TestContextualLogger:
    """Test ContextualLogger class."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing."""
        return Mock(spec=logging.Logger)

    @pytest.fixture
    def contextual_logger(self, mock_logger):
        """Create a ContextualLogger instance for testing."""
        return ContextualLogger(mock_logger, "test-job-123")

    def test_initialization_with_job_id(self, mock_logger):
        """Test ContextualLogger initialization with job ID."""
        logger = ContextualLogger(mock_logger, "init-job-456")

        assert logger.logger == mock_logger
        assert logger.job_id == "init-job-456"
        assert isinstance(logger.formatter, SentinelLogFormatter)

    def test_initialization_without_job_id(self, mock_logger):
        """Test ContextualLogger initialization without job ID."""
        logger = ContextualLogger(mock_logger)

        assert logger.logger == mock_logger
        assert logger.job_id is None
        assert isinstance(logger.formatter, SentinelLogFormatter)

    def test_set_job_id(self, contextual_logger):
        """Test setting job ID."""
        contextual_logger.set_job_id("new-job-789")

        assert contextual_logger.job_id == "new-job-789"

    def test_batch_start(self, contextual_logger, mock_logger):
        """Test batch start logging."""
        contextual_logger.batch_start(total_days=5, batch_hours=12, workspace_count=3)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "[BATCH_START]" in call_args
        assert "test-job-123" in call_args
        assert "5d" in call_args
        assert "12h batches" in call_args
        assert "Workspaces: 3" in call_args

    def test_batch_start_no_job_id(self, mock_logger):
        """Test batch start logging without job ID."""
        logger = ContextualLogger(mock_logger)
        logger.batch_start(total_days=7, batch_hours=24, workspace_count=2)

        mock_logger.info.assert_not_called()

    def test_batch_end(self, contextual_logger, mock_logger):
        """Test batch end logging."""
        summary = {"successful_queries": 5, "total_queries": 6, "total_records": 1000}

        contextual_logger.batch_end(summary)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "[BATCH_END]" in call_args
        assert "test-job-123" in call_args
        assert "5/6" in call_args

    def test_query_start(self, contextual_logger, mock_logger):
        """Test query start logging."""
        contextual_logger.query_start(
            query_name="test_query",
            workspace_alias="test_workspace",
            time_range="2024-01-01 to 2024-01-02",
        )

        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0][0]
        assert "[QUERY_START]" in call_args
        assert "test_query" in call_args
        assert "test_workspace" in call_args

    def test_query_end_success(self, contextual_logger, mock_logger):
        """Test successful query end logging."""
        contextual_logger.query_end(
            query_name="test_query",
            workspace_alias="test_workspace",
            record_count=500,
            duration=10.5,
            success=True,
        )

        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0][0]
        assert "[QUERY_END]" in call_args
        assert "SUCCESS" in call_args
        assert "500" in call_args

    def test_query_end_failure(self, contextual_logger, mock_logger):
        """Test failed query end logging."""
        contextual_logger.query_end(
            query_name="test_query",
            workspace_alias="test_workspace",
            record_count=0,
            duration=5.0,
            success=False,
        )

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        assert "[QUERY_END]" in call_args
        assert "FAILED" in call_args

    def test_upload_start(self, contextual_logger, mock_logger):
        """Test upload start logging."""
        contextual_logger.upload_start(
            query_name="test_query", workspace_alias="test_workspace", record_count=300
        )

        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0][0]
        assert "[UPLOAD_START]" in call_args
        assert "300" in call_args

    def test_upload_end_success(self, contextual_logger, mock_logger):
        """Test successful upload end logging."""
        contextual_logger.upload_end(
            query_name="test_query",
            workspace_alias="test_workspace",
            uploaded_count=300,
            duration=3.5,
            success=True,
        )

        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0][0]
        assert "[UPLOAD_END]" in call_args
        assert "SUCCESS" in call_args

    def test_upload_end_failure(self, contextual_logger, mock_logger):
        """Test failed upload end logging."""
        contextual_logger.upload_end(
            query_name="test_query",
            workspace_alias="test_workspace",
            uploaded_count=0,
            duration=1.0,
            success=False,
        )

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        assert "[UPLOAD_END]" in call_args
        assert "FAILED" in call_args

    def test_error_minimal(self, contextual_logger, mock_logger):
        """Test error logging with minimal context."""
        contextual_logger.error(component="TestComponent", error_message="Test error")

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        assert "TestComponent" in call_args
        assert "Test error" in call_args

    def test_error_with_exc_info(self, contextual_logger, mock_logger):
        """Test error logging with exception info."""
        contextual_logger.error(
            component="TestComponent", error_message="Test error", exc_info=True
        )

        mock_logger.error.assert_called_once()
        _, kwargs = mock_logger.error.call_args
        assert kwargs.get("exc_info") is True

    def test_error_full_context(self, contextual_logger, mock_logger):
        """Test error logging with full context."""
        contextual_logger.error(
            component="DataUploader",
            error_message="Upload failed",
            query_name="test_query",
            workspace_alias="test_workspace",
            error_type="UploadError",
        )

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        assert "DataUploader" in call_args
        assert "Upload failed" in call_args
        assert "test_query" in call_args
        assert "UploadError" in call_args

    def test_progress(self, contextual_logger, mock_logger):
        """Test progress logging."""
        contextual_logger.progress(completed=4, total=10, additional_info="Processing data")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "[PROGRESS]" in call_args
        assert "4/10" in call_args
        assert "Processing data" in call_args

    def test_workspace_config(self, contextual_logger, mock_logger):
        """Test workspace config logging."""
        contextual_logger.workspace_config(
            workspace_count=8, report_count=4, subscription_count=2, error_count=0
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "[WORKSPACE_CONFIG]" in call_args
        assert "VALID" in call_args
        assert "Workspaces: 8" in call_args

    def test_config_validation_valid(self, contextual_logger, mock_logger):
        """Test valid config validation logging."""
        contextual_logger.config_validation(
            component="TestConfig", is_valid=True, details="All checks passed"
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "VALID" in call_args
        assert "All checks passed" in call_args

    def test_config_validation_invalid(self, contextual_logger, mock_logger):
        """Test invalid config validation logging."""
        contextual_logger.config_validation(
            component="TestConfig", is_valid=False, details="Missing required field"
        )

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        assert "INVALID" in call_args
        assert "Missing required field" in call_args

    def test_batch_summary(self, contextual_logger, mock_logger):
        """Test batch summary logging."""
        summary_data = {
            "overview": {
                "total_workspaces": 3,
                "total_unique_queries": 6,
                "total_duration_seconds": 120.0,
            }
        }

        contextual_logger.batch_summary(summary_data)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "[BATCH_SUMMARY]" in call_args
        assert "Workspaces: 3" in call_args

    def test_workspace_query_details(self, contextual_logger, mock_logger):
        """Test workspace query details logging."""
        details = [
            {"workspaceId": "ws-123", "query": "test_query", "logsDownloaded": 100},
            {"workspaceId": "ws-456", "query": "other_query", "logsDownloaded": 200},
        ]

        contextual_logger.workspace_query_details(details)

        assert mock_logger.info.call_count == 2

        # Check first call
        first_call = mock_logger.info.call_args_list[0][0][0]
        assert "[WORKSPACE_QUERY_DETAIL]" in first_call
        assert "ws-123" in first_call
        assert "test_query" in first_call

        # Check second call
        second_call = mock_logger.info.call_args_list[1][0][0]
        assert "ws-456" in second_call
        assert "other_query" in second_call

    def test_convenience_methods(self, contextual_logger, mock_logger):
        """Test convenience logging methods."""
        contextual_logger.info("Info message")
        contextual_logger.warning("Warning message")
        contextual_logger.debug("Debug message")

        mock_logger.info.assert_called_with("Info message")
        mock_logger.warning.assert_called_with("Warning message")
        mock_logger.debug.assert_called_with("Debug message")

    def test_methods_without_job_id(self, mock_logger):
        """Test that methods requiring job_id do nothing when job_id is None."""
        logger = ContextualLogger(mock_logger)  # No job_id

        # These methods should not call the underlying logger
        logger.batch_start(total_days=7, batch_hours=24, workspace_count=1)
        logger.batch_end({})
        logger.query_start("query", "workspace", "range")
        logger.query_end("query", "workspace", 100, 10.0)
        logger.upload_start("query", "workspace", 100)
        logger.upload_end("query", "workspace", 100, 5.0)
        logger.error("component", "message")
        logger.progress(1, 10)
        logger.batch_summary({})
        logger.workspace_query_details([])

        # Only convenience methods should be called
        mock_logger.info.assert_not_called()
        mock_logger.debug.assert_not_called()
        mock_logger.error.assert_not_called()


class TestIntegrationScenarios:
    """Test integration scenarios with real logging behavior."""

    def test_complete_batch_logging_scenario(self):
        """Test a complete batch execution logging scenario."""
        # Create a real logger with string capture
        import io
        import logging

        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(logging.Formatter("%(message)s"))

        real_logger = logging.getLogger("test_batch_scenario")
        real_logger.addHandler(handler)
        real_logger.setLevel(logging.DEBUG)

        contextual_logger = ContextualLogger(real_logger, "integration-test-job")

        # Simulate batch execution
        contextual_logger.batch_start(total_days=1, batch_hours=24, workspace_count=2)
        contextual_logger.query_start("test_query", "workspace1", "2024-01-01 to 2024-01-02")
        contextual_logger.query_end("test_query", "workspace1", 500, 10.5, success=True)
        contextual_logger.upload_start("test_query", "workspace1", 500)
        contextual_logger.upload_end("test_query", "workspace1", 500, 3.2, success=True)

        summary = {
            "successful_queries": 1,
            "total_queries": 1,
            "total_records": 500,
            "total_uploaded": 500,
        }
        contextual_logger.batch_end(summary)

        # Verify log output
        log_output = log_stream.getvalue()

        assert "[BATCH_START]" in log_output
        assert "[QUERY_START]" in log_output
        assert "[QUERY_END]" in log_output
        assert "[UPLOAD_START]" in log_output
        assert "[UPLOAD_END]" in log_output
        assert "[BATCH_END]" in log_output
        assert "integration-test-job" in log_output

        # Clean up
        real_logger.removeHandler(handler)

    def test_error_scenario_logging(self):
        """Test error scenario logging."""
        import io
        import logging

        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

        real_logger = logging.getLogger("test_error_scenario")
        real_logger.addHandler(handler)
        real_logger.setLevel(logging.DEBUG)

        contextual_logger = ContextualLogger(real_logger, "error-test-job")

        # Simulate error scenarios
        contextual_logger.query_end("failed_query", "workspace1", 0, 5.0, success=False)
        contextual_logger.upload_end("failed_query", "workspace1", 0, 1.0, success=False)
        contextual_logger.error(
            component="QueryEngine",
            error_message="Connection timeout",
            query_name="failed_query",
            workspace_alias="workspace1",
            error_type="TimeoutError",
        )

        # Verify error logging
        log_output = log_stream.getvalue()

        assert "ERROR:" in log_output
        assert "FAILED" in log_output
        assert "Connection timeout" in log_output
        assert "TimeoutError" in log_output

        # Clean up
        real_logger.removeHandler(handler)
