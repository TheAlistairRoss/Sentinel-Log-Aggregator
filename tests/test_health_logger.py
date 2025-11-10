"""
Tests for SentinelAggregatorHealthLogger functionality.

Validates health logging functionality, data structure, and Log Analytics integration.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions
from sentinel_log_aggregator.health_logger import SentinelAggregatorHealthLogger
from sentinel_log_aggregator.models import (
    QueryExecution,
    QueryStatus,
    UploadStatus,
    WorkspaceConfig,
)
from sentinel_log_aggregator.sentinel_client import SentinelAggregatorClient


@pytest.fixture
def mock_sentinel_client():
    """Create a mock SentinelAggregatorClient for testing."""
    client = Mock(spec=SentinelAggregatorClient)
    client.upload_logs = AsyncMock()
    return client


@pytest.fixture
def health_logger(mock_sentinel_client):
    """Create a SentinelAggregatorHealthLogger for testing."""
    return SentinelAggregatorHealthLogger(
        sentinel_client=mock_sentinel_client,
        enabled=True,
        health_to_sentinel=True,  # Enable Sentinel uploads for testing
    )


@pytest.fixture
def test_workspace_config():
    """Create a test workspace configuration."""
    return WorkspaceConfig(
        resource_id="/subscriptions/87654321-4321-4321-4321-210987654321/resourceGroups/test-rg/providers/Microsoft.OperationalInsights/workspaces/test-workspace",
        customer_id="87654321-4321-4321-4321-210987654321",
        queries_list=["query1", "query2"],
        parameters={"row_level_security_tag": "test-workspace"},
    )


@pytest.fixture
def test_query_execution():
    """Create a test query execution object."""
    return QueryExecution(
        job_correlation_id=str(uuid4()),
        execution_id="test_execution_123",
        workspace_id="87654321-4321-4321-4321-210987654321",
        query_name="test_query",
        destination_stream="Custom-TestReport_CL",
        start_time=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        query_status=QueryStatus.SUCCESS.value,
        upload_status=UploadStatus.SUCCESS.value,
        record_count=100,
        query_duration_seconds=5.5,
    )


class TestSentinelAggregatorHealthLogger:
    """Test cases for SentinelAggregatorHealthLogger."""

    def test_initialization_enabled(self, health_logger):
        """Test health logger initialization when enabled."""
        assert health_logger.enabled is True
        assert health_logger.health_stream_name == "Custom-SentinelAggregator_Health_CL"

    def test_initialization_disabled(self, mock_sentinel_client):
        """Test health logger initialization when disabled."""
        logger = SentinelAggregatorHealthLogger(sentinel_client=mock_sentinel_client, enabled=False)
        assert logger.enabled is False

    def test_initialization_missing_dcr_endpoint(self, mock_sentinel_client):
        """Test health logger initialization - DCR validation is now at client level."""
        # This test is no longer applicable since DCR validation is at client level
        logger = SentinelAggregatorHealthLogger(sentinel_client=mock_sentinel_client, enabled=True)
        assert logger.enabled is True

    @pytest.mark.asyncio
    async def test_log_job_start(self, health_logger, mock_sentinel_client):
        """Test logging job start event."""
        job_id = "test-job-123"

        await health_logger.log_job_start(
            job_id=job_id,
            job_type="test_batch",
            workspace_count=2,
            query_count=5,
            custom_property="test_value",
        )

        # Verify the upload call was made
        mock_sentinel_client.upload_logs.assert_called_once()

        # Verify the data structure
        call_args = mock_sentinel_client.upload_logs.call_args
        assert call_args[1]["stream_name"] == "Custom-SentinelAggregator_Health_CL"

        data = call_args[1]["data"]
        assert len(data) == 1

        record = data[0]
        assert record["OperationName"] == "JobStart"
        assert record["OperationStatus"] == "Started"
        assert record["JobId"] == job_id
        assert "TimeGenerated" in record

        # Verify extended properties
        extended_props = json.loads(record["ExtendedProperties"])
        assert extended_props["workspace_count"] == 2
        assert extended_props["query_count"] == 5
        assert extended_props["custom_property"] == "test_value"

    @pytest.mark.asyncio
    async def test_log_job_end_success(self, health_logger, mock_sentinel_client):
        """Test logging successful job end event."""
        job_id = "test-job-123"

        await health_logger.log_job_end(
            job_id=job_id,
            job_type="test_batch",
            success=True,
            total_records_processed=1000,
            total_duration_seconds=45.5,
        )

        # Verify the upload call was made
        mock_sentinel_client.upload_logs.assert_called_once()

        # Verify the data structure
        call_args = mock_sentinel_client.upload_logs.call_args
        data = call_args[1]["data"]
        record = data[0]

        assert record["OperationName"] == "JobEnd"
        assert record["OperationStatus"] == "Completed"
        assert record["JobId"] == job_id

        extended_props = json.loads(record["ExtendedProperties"])
        assert extended_props["total_records_processed"] == 1000
        assert extended_props["total_duration_seconds"] == 45.5

    @pytest.mark.asyncio
    async def test_log_job_end_failure(self, health_logger, mock_sentinel_client):
        """Test logging failed job end event."""
        job_id = "test-job-123"
        error_message = "Connection timeout"

        await health_logger.log_job_end(
            job_id=job_id, job_type="test_batch", success=False, error_message=error_message
        )

        # Verify the data structure
        call_args = mock_sentinel_client.upload_logs.call_args
        data = call_args[1]["data"]
        record = data[0]

        assert record["OperationStatus"] == "Failed"

        extended_props = json.loads(record["ExtendedProperties"])
        assert extended_props["error_message"] == error_message

    @pytest.mark.asyncio
    async def test_log_query_execution(
        self, health_logger, mock_sentinel_client, test_query_execution, test_workspace_config
    ):
        """Test logging query execution event."""
        job_id = "test-job-123"

        await health_logger.log_query_execution(
            job_id=job_id,
            query_execution=test_query_execution,
            workspace_config=test_workspace_config,
        )

        # Verify the upload call was made
        mock_sentinel_client.upload_logs.assert_called_once()

        # Verify the data structure
        call_args = mock_sentinel_client.upload_logs.call_args
        data = call_args[1]["data"]
        record = data[0]

        assert record["OperationName"] == "QueryExecution"
        assert record["OperationStatus"] == "Completed"
        assert record["JobId"] == job_id
        assert record["WorkspaceId"] == test_workspace_config.customer_id
        assert record["QueryName"] == test_query_execution.query_name

        extended_props = json.loads(record["ExtendedProperties"])
        assert extended_props["record_count"] == 100
        assert extended_props["duration_seconds"] == 5.5
        assert extended_props["workspace_name"] == test_workspace_config.workspace_name

    @pytest.mark.asyncio
    async def test_log_query_execution_failed(
        self, health_logger, mock_sentinel_client, test_workspace_config
    ):
        """Test logging failed query execution event."""
        failed_execution = QueryExecution(
            job_correlation_id=str(uuid4()),
            execution_id="failed_execution_123",
            workspace_id="87654321-4321-4321-4321-210987654321",
            query_name="failed_query",
            destination_stream="Custom-TestReport_CL",
            start_time=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            query_status=QueryStatus.FAILED.value,
            upload_status=UploadStatus.SKIPPED.value,
            query_error_message="Syntax error in KQL",
        )

        job_id = "test-job-123"

        await health_logger.log_query_execution(
            job_id=job_id, query_execution=failed_execution, workspace_config=test_workspace_config
        )

        # Verify the data structure
        call_args = mock_sentinel_client.upload_logs.call_args
        data = call_args[1]["data"]
        record = data[0]

        assert record["OperationStatus"] == "Failed"

        extended_props = json.loads(record["ExtendedProperties"])
        assert extended_props["error_message"] == "Syntax error in KQL"

    @pytest.mark.asyncio
    async def test_log_workspace_processing_start(
        self, health_logger, mock_sentinel_client, test_workspace_config
    ):
        """Test logging workspace processing start event."""
        job_id = "test-job-123"
        query_names = ["query1", "query2", "query3"]

        await health_logger.log_workspace_processing_start(
            job_id=job_id, workspace_config=test_workspace_config, query_names=query_names
        )

        # Verify the data structure
        call_args = mock_sentinel_client.upload_logs.call_args
        data = call_args[1]["data"]
        record = data[0]

        assert record["OperationName"] == "WorkspaceProcessingStart"
        assert record["OperationStatus"] == "Started"
        assert record["WorkspaceId"] == test_workspace_config.customer_id

        extended_props = json.loads(record["ExtendedProperties"])
        assert extended_props["query_names"] == query_names
        assert extended_props["query_count"] == 3
        assert extended_props["workspace_name"] == test_workspace_config.workspace_name

    @pytest.mark.asyncio
    async def test_log_workspace_processing_end(
        self, health_logger, mock_sentinel_client, test_workspace_config
    ):
        """Test logging workspace processing end event."""
        job_id = "test-job-123"

        await health_logger.log_workspace_processing_end(
            job_id=job_id,
            workspace_config=test_workspace_config,
            success=True,
            records_processed=500,
            duration_seconds=30.2,
        )

        # Verify the data structure
        call_args = mock_sentinel_client.upload_logs.call_args
        data = call_args[1]["data"]
        record = data[0]

        assert record["OperationName"] == "WorkspaceProcessingEnd"
        assert record["OperationStatus"] == "Completed"

        extended_props = json.loads(record["ExtendedProperties"])
        assert extended_props["records_processed"] == 500
        assert extended_props["duration_seconds"] == 30.2

    @pytest.mark.asyncio
    async def test_log_error(self, health_logger, mock_sentinel_client):
        """Test logging error event."""
        job_id = "test-job-123"

        await health_logger.log_error(
            job_id=job_id,
            error_type="AuthenticationError",
            error_message="Invalid credentials",
            workspace_id="test-workspace-id",
            query_name="test_query",
            additional_context="User authentication failed",
        )

        # Verify the data structure
        call_args = mock_sentinel_client.upload_logs.call_args
        data = call_args[1]["data"]
        record = data[0]

        assert record["OperationName"] == "Error"
        assert record["OperationStatus"] == "Failed"
        assert record["WorkspaceId"] == "test-workspace-id"
        assert record["QueryName"] == "test_query"

        extended_props = json.loads(record["ExtendedProperties"])
        assert extended_props["error_type"] == "AuthenticationError"
        assert extended_props["error_message"] == "Invalid credentials"
        assert extended_props["additional_context"] == "User authentication failed"

    @pytest.mark.asyncio
    async def test_log_watermark_update(self, health_logger, mock_sentinel_client):
        """Test logging watermark update event."""
        job_id = "test-job-123"
        workspace_id = "12345678-1234-1234-1234-123456789012"
        query_name = "test_query"
        watermark_timestamp = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        previous_watermark = datetime(2024, 1, 14, 12, 0, 0, tzinfo=timezone.utc)

        await health_logger.log_watermark_update(
            job_id=job_id,
            workspace_id=workspace_id,
            query_name=query_name,
            watermark_timestamp=watermark_timestamp,
            previous_watermark=previous_watermark,
        )

        # Verify the data structure
        call_args = mock_sentinel_client.upload_logs.call_args
        data = call_args[1]["data"]
        record = data[0]

        assert record["OperationName"] == "WatermarkUpdate"
        assert record["OperationStatus"] == "Completed"
        assert record["WorkspaceId"] == workspace_id
        assert record["QueryName"] == query_name

        extended_props = json.loads(record["ExtendedProperties"])
        assert extended_props["watermark_timestamp"] == watermark_timestamp.isoformat()
        assert extended_props["previous_watermark"] == previous_watermark.isoformat()
        assert extended_props["watermark_advance_seconds"] == 86400.0  # 24 hours

    @pytest.mark.asyncio
    async def test_disabled_logger_no_logging(self, mock_sentinel_client):
        """Test that disabled health logger doesn't make any log calls."""
        disabled_logger = SentinelAggregatorHealthLogger(
            sentinel_client=mock_sentinel_client, enabled=False
        )

        # Try to log various events
        await disabled_logger.log_job_start("test-job", "test_type", 1, 1)
        await disabled_logger.log_job_end("test-job", "test_type", True)
        await disabled_logger.log_error("test-job", "TestError", "Test error message")

        # Verify no upload calls were made
        mock_sentinel_client.upload_logs.assert_not_called()

    @pytest.mark.asyncio
    async def test_health_logging_error_handling(self, health_logger, mock_sentinel_client):
        """Test that health logging errors don't crash the application."""
        # Make the upload method raise an exception
        mock_sentinel_client.upload_logs.side_effect = Exception("Upload failed")

        # This should not raise an exception
        await health_logger.log_job_start("test-job", "test_type", 1, 1)

        # Verify the upload was attempted
        mock_sentinel_client.upload_logs.assert_called_once()

    def test_create_job_id(self, health_logger):
        """Test job ID creation."""
        job_id = health_logger.create_job_id()
        assert isinstance(job_id, str)
        assert len(job_id) > 0

        # Should create unique IDs
        job_id2 = health_logger.create_job_id()
        assert job_id != job_id2

    def test_create_disabled_logger(self):
        """Test creating a disabled health logger."""
        disabled_logger = SentinelAggregatorHealthLogger.create_disabled()
        assert disabled_logger.enabled is False

    @pytest.mark.asyncio
    async def test_extended_properties_json_serialization(
        self, health_logger, mock_sentinel_client
    ):
        """Test that extended properties with complex types are properly JSON serialized."""
        job_id = "test-job-123"

        # Include various data types that need JSON serialization
        await health_logger.log_job_start(
            job_id=job_id,
            job_type="test_batch",
            workspace_count=2,
            query_count=5,
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            list_data=["item1", "item2"],
            dict_data={"key": "value"},
        )

        # Verify the data was properly serialized
        call_args = mock_sentinel_client.upload_logs.call_args
        data = call_args[1]["data"]
        record = data[0]

        # Should be able to parse the extended properties JSON
        extended_props = json.loads(record["ExtendedProperties"])
        assert (
            extended_props["timestamp"] == "2024-01-01 12:00:00+00:00"
        )  # str() format, not isoformat()
        assert extended_props["list_data"] == ["item1", "item2"]
        assert extended_props["dict_data"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_send_test_event_success(self, health_logger, mock_sentinel_client):
        """Test sending a test health event successfully."""
        from sentinel_log_aggregator.responses import UploadResult, UploadStatus

        # Mock successful upload
        mock_sentinel_client.upload_logs.return_value = UploadResult(
            status=UploadStatus.SUCCESS,
            record_count=1,
            upload_time=0.1,
            stream_name="Custom-SentinelAggregator_Health_CL",
            dcr_immutable_id="dcr-test",
            error_message=None,
        )

        result = await health_logger.send_test_event(test_id="test-123")

        assert result["success"] is True
        assert result["test_id"] == "test-123"
        assert "Test ID: test-123" in result["message"]
        assert "error" not in result

        # Verify upload was called
        mock_sentinel_client.upload_logs.assert_called_once()
        call_args = mock_sentinel_client.upload_logs.call_args
        data = call_args[1]["data"]
        assert len(data) == 1
        assert data[0]["OperationName"] == "HealthTest"
        assert data[0]["JobId"] == "test-123"

    @pytest.mark.asyncio
    async def test_send_test_event_auto_generated_id(self, health_logger, mock_sentinel_client):
        """Test sending a test event with auto-generated ID."""
        from sentinel_log_aggregator.responses import UploadResult, UploadStatus

        mock_sentinel_client.upload_logs.return_value = UploadResult(
            status=UploadStatus.SUCCESS,
            record_count=1,
            upload_time=0.1,
            stream_name="Custom-SentinelAggregator_Health_CL",
            dcr_immutable_id="dcr-test",
            error_message=None,
        )

        result = await health_logger.send_test_event()

        assert result["success"] is True
        assert result["test_id"] is not None
        assert result["test_id"].startswith("health-test-")

    @pytest.mark.asyncio
    async def test_send_test_event_disabled(self, mock_sentinel_client):
        """Test sending test event when health logging is disabled."""
        disabled_logger = SentinelAggregatorHealthLogger(
            sentinel_client=mock_sentinel_client,
            enabled=False,
            health_to_sentinel=False,
        )

        result = await disabled_logger.send_test_event()

        assert result["success"] is False
        assert "disabled" in result["message"].lower()
        mock_sentinel_client.upload_logs.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_test_event_console_only(self, mock_sentinel_client):
        """Test sending test event when in console-only mode."""
        console_logger = SentinelAggregatorHealthLogger(
            sentinel_client=mock_sentinel_client,
            enabled=True,
            health_to_sentinel=False,  # Console-only mode
        )

        result = await console_logger.send_test_event()

        assert result["success"] is False
        assert "console-only" in result["message"].lower()
        mock_sentinel_client.upload_logs.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_test_event_upload_failure(self, health_logger, mock_sentinel_client):
        """Test sending test event when upload fails."""
        from sentinel_log_aggregator.responses import UploadResult, UploadStatus

        mock_sentinel_client.upload_logs.return_value = UploadResult(
            status=UploadStatus.FAILED,
            record_count=0,
            upload_time=0.1,
            stream_name="Custom-SentinelAggregator_Health_CL",
            dcr_immutable_id="dcr-test",
            error_message="Upload failed",
        )

        result = await health_logger.send_test_event(test_id="test-failed")

        assert result["success"] is False
        assert result["test_id"] == "test-failed"
        assert "failed" in result["message"].lower()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_send_test_event_with_custom_properties(
        self, health_logger, mock_sentinel_client
    ):
        """Test sending test event with custom properties."""
        from sentinel_log_aggregator.responses import UploadResult, UploadStatus

        mock_sentinel_client.upload_logs.return_value = UploadResult(
            status=UploadStatus.SUCCESS,
            record_count=1,
            upload_time=0.1,
            stream_name="Custom-SentinelAggregator_Health_CL",
            dcr_immutable_id="dcr-test",
            error_message=None,
        )

        result = await health_logger.send_test_event(
            test_id="test-custom",
            custom_field="custom_value",
            numeric_field=42,
        )

        assert result["success"] is True

        # Verify custom properties were included
        call_args = mock_sentinel_client.upload_logs.call_args
        data = call_args[1]["data"]
        extended_props = json.loads(data[0]["ExtendedProperties"])
        assert extended_props["custom_field"] == "custom_value"
        assert extended_props["numeric_field"] == 42
        assert extended_props["test_event"] is True

    @pytest.mark.asyncio
    async def test_verify_test_event_found(self, health_logger, mock_sentinel_client):
        """Test verifying a test event that is found."""
        from sentinel_log_aggregator.responses import QueryResult, QueryStatus

        # Mock successful query result
        mock_sentinel_client.query_workspace = AsyncMock()
        mock_sentinel_client.query_workspace.return_value = QueryResult(
            status=QueryStatus.SUCCESS,
            record_count=1,
            data=[
                {
                    "TimeGenerated": "2024-01-01T12:00:00Z",
                    "OperationName": "HealthTest",
                    "JobId": "test-123",
                }
            ],
            error_message=None,
        )

        result = await health_logger.verify_test_event(
            test_id="test-123",
            workspace_id="workspace-id",
            max_wait_seconds=60,
        )

        assert result["found"] is True
        assert result["test_id"] == "test-123"
        assert "found" in result["message"].lower()
        assert result["record"] is not None

    @pytest.mark.asyncio
    async def test_verify_test_event_not_found(self, health_logger, mock_sentinel_client):
        """Test verifying a test event that is not found."""
        from sentinel_log_aggregator.responses import QueryResult, QueryStatus

        # Mock empty query result
        mock_sentinel_client.query_workspace = AsyncMock()
        mock_sentinel_client.query_workspace.return_value = QueryResult(
            status=QueryStatus.SUCCESS,
            record_count=0,
            data=[],
            error_message=None,
        )

        result = await health_logger.verify_test_event(
            test_id="test-missing",
            workspace_id="workspace-id",
            max_wait_seconds=15,  # Short wait for testing
        )

        assert result["found"] is False
        assert result["test_id"] == "test-missing"
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_verify_test_event_disabled(self, mock_sentinel_client):
        """Test verifying test event when health logging is disabled."""
        disabled_logger = SentinelAggregatorHealthLogger(
            sentinel_client=mock_sentinel_client,
            enabled=False,
            health_to_sentinel=False,
        )

        result = await disabled_logger.verify_test_event(
            test_id="test-123",
            workspace_id="workspace-id",
        )

        assert result["found"] is False
        assert "not configured" in result["message"].lower()
        (
            mock_sentinel_client.query_workspace.assert_not_called()
            if hasattr(mock_sentinel_client, "query_workspace")
            else None
        )
