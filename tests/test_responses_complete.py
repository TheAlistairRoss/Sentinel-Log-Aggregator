"""
Comprehensive tests for responses.py to achieve 100% coverage.
Targets missing lines: 89, 94, 99, 142, 147, 175-177, 223, 228, 233, 238-239, 244-246, 285
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from sentinel_log_aggregator.responses import (
    BatchExecutionResult,
    BatchStatus,
    QueryResult,
    QueryStatus,
    ServiceProperties,
    UploadResult,
    UploadStatus,
    WorkspaceQueryExecution,
)

"""
Comprehensive tests for responses.py to achieve 100% coverage.
Targets missing lines: 89, 94, 99, 142, 147, 175-177, 223, 228, 233, 238-239, 244-246, 285
"""
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from sentinel_log_aggregator.responses import (
    BatchExecutionResult,
    BatchStatus,
    QueryResult,
    QueryStatus,
    ServiceProperties,
    UploadResult,
    UploadStatus,
    WorkspaceQueryExecution,
)


class TestResponsesComplete:
    """Tests to achieve 100% coverage for responses.py"""

    def test_query_result_properties_lines_89_94_99(self):
        """Test QueryResult properties: succeeded, failed, workspace_alias (lines 89, 94, 99)"""

        # Test succeeded property (line 89)
        success_result = QueryResult(
            status=QueryStatus.SUCCESS,
            data=[{"field": "value"}],
            record_count=100,
            execution_time=1.5,
            workspace_id="test-workspace-12345",
            query="TestQuery",
        )
        assert success_result.succeeded == True

        # Test failed property (line 94)
        failed_result = QueryResult(
            status=QueryStatus.FAILED,
            data=[],
            record_count=0,
            execution_time=0.5,
            workspace_id="test-workspace-12345",
            query="TestQuery",
            error_message="Query failed",
        )
        assert failed_result.failed == True

        # Test workspace_alias property (line 99)
        result_with_alias = QueryResult(
            status=QueryStatus.SUCCESS,
            data=[{"field": "value"}],
            record_count=50,
            execution_time=1.0,
            workspace_id="test-workspace-12345678901234567890",
            query="TestQuery",
        )
        assert result_with_alias.workspace_alias == "test-wor..."

        result_empty_workspace = QueryResult(
            status=QueryStatus.SUCCESS,
            data=[],
            record_count=0,
            execution_time=1.0,
            workspace_id="",
            query="TestQuery",
        )
        assert result_empty_workspace.workspace_alias == "unknown"

    def test_upload_result_properties_lines_142_147(self):
        """Test UploadResult properties: succeeded, failed (lines 142, 147)"""

        # Test succeeded property (line 142)
        success_upload = UploadResult(
            status=UploadStatus.SUCCESS,
            record_count=100,
            upload_time=2.0,
            stream_name="stream_test",
            dcr_rule_id="dcr-rule-123",
        )
        assert success_upload.succeeded == True

        # Test failed property (line 147)
        failed_upload = UploadResult(
            status=UploadStatus.FAILED,
            record_count=0,
            upload_time=1.0,
            stream_name="stream_test",
            dcr_rule_id="dcr-rule-123",
            error_message="Upload failed",
        )
        assert failed_upload.failed == True

    def test_workspace_query_execution_lines_175_177(self):
        """Test WorkspaceQueryExecution.succeeded property (lines 175-177)"""

        # Create a successful query result
        success_query_result = QueryResult(
            status=QueryStatus.SUCCESS,
            data=[{"field": "value"}],
            record_count=50,
            execution_time=1.0,
            workspace_id="test-workspace-12345",
            query="TestQuery",
        )

        # Create a successful upload result
        success_upload_result = UploadResult(
            status=UploadStatus.SUCCESS,
            record_count=50,
            upload_time=1.5,
            stream_name="stream_test",
            dcr_rule_id="dcr-rule-123",
        )

        # Test successful execution (should trigger lines 175-177)
        workspace_execution = WorkspaceQueryExecution(
            workspace_id="test-workspace-id",
            workspace_alias="test_workspace",
            query_result=success_query_result,
            upload_result=success_upload_result,
            correlation_id="test-correlation-123",
        )

        # This triggers lines 175-177 in the succeeded property
        assert workspace_execution.succeeded == True

        # Test with failed query (line 175)
        failed_query_result = QueryResult(
            status=QueryStatus.FAILED,
            data=[],
            record_count=0,
            execution_time=0.5,
            workspace_id="test-workspace-12345",
            query="TestQuery",
            error_message="Query failed",
        )

        failed_workspace_execution = WorkspaceQueryExecution(
            workspace_id="test-workspace-id",
            workspace_alias="test_workspace",
            query_result=failed_query_result,
            upload_result=success_upload_result,
        )

        # This should trigger line 175-176 and return False
        assert failed_workspace_execution.succeeded == False

        # Test with no upload result (line 176-177)
        no_upload_execution = WorkspaceQueryExecution(
            workspace_id="test-workspace-id",
            workspace_alias="test_workspace",
            query_result=success_query_result,
            upload_result=None,
        )

        # This should trigger line 176-177 (upload_ok = True if no upload_result)
        assert no_upload_execution.succeeded == True

    def test_batch_execution_result_properties_lines_223_228_233(self):
        """Test BatchExecutionResult basic properties"""

        # Create sample workspace executions
        query_result1 = QueryResult(
            status=QueryStatus.SUCCESS,
            data=[{"field": "value"}],
            record_count=100,
            execution_time=1.0,
            workspace_id="workspace1-id",
            query="TestQuery",
        )

        query_result2 = QueryResult(
            status=QueryStatus.FAILED,
            data=[],
            record_count=0,
            execution_time=0.5,
            workspace_id="workspace2-id",
            query="TestQuery",
            error_message="Query failed",
        )

        workspace_executions = [
            WorkspaceQueryExecution(
                workspace_id="workspace1-id",
                workspace_alias="workspace1",
                query_result=query_result1,
            ),
            WorkspaceQueryExecution(
                workspace_id="workspace2-id",
                workspace_alias="workspace2",
                query_result=query_result2,
            ),
        ]

        batch_result = BatchExecutionResult(
            status=BatchStatus.SUCCESS,
            workspace_results=workspace_executions,
            total_records=100,
            total_execution_time=1.5,
            job_correlation_id="test-job-123",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            successful_workspaces=1,
            failed_workspaces=1,
        )

        # Test basic properties
        assert batch_result.succeeded == True
        assert batch_result.failed == False
        assert batch_result.partial_success == False
        assert batch_result.success_rate == 50.0
        assert batch_result.duration is not None

    def test_batch_execution_result_upload_properties_lines_238_244_246(self):
        """Test BatchExecutionResult properties with uploads"""

        # Create workspace executions with upload results
        upload_result1 = UploadResult(
            status=UploadStatus.SUCCESS,
            record_count=100,
            upload_time=1.0,
            stream_name="stream1",
            dcr_rule_id="dcr-rule-123",
        )

        upload_result2 = UploadResult(
            status=UploadStatus.SUCCESS,
            record_count=50,
            upload_time=0.8,
            stream_name="stream2",
            dcr_rule_id="dcr-rule-123",
        )

        upload_result3 = UploadResult(
            status=UploadStatus.FAILED,
            record_count=0,
            upload_time=0.5,
            stream_name="stream3",
            dcr_rule_id="dcr-rule-123",
            error_message="Upload failed",
        )

        query_result = QueryResult(
            status=QueryStatus.SUCCESS,
            data=[{"field": "value"}],
            record_count=100,
            execution_time=1.0,
            workspace_id="test-workspace-id",
            query="TestQuery",
        )

        workspace_executions = [
            WorkspaceQueryExecution(
                workspace_id="workspace1-id",
                workspace_alias="workspace1",
                query_result=query_result,
                upload_result=upload_result1,
            ),
            WorkspaceQueryExecution(
                workspace_id="workspace2-id",
                workspace_alias="workspace2",
                query_result=query_result,
                upload_result=upload_result2,
            ),
            WorkspaceQueryExecution(
                workspace_id="workspace3-id",
                workspace_alias="workspace3",
                query_result=query_result,
                upload_result=upload_result3,
            ),
        ]

        batch_result = BatchExecutionResult(
            status=BatchStatus.PARTIAL_SUCCESS,
            workspace_results=workspace_executions,
            total_records=300,
            total_execution_time=3.0,
            job_correlation_id="test-job-123",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            successful_workspaces=2,
            failed_workspaces=1,
        )

        # Test partial success property
        assert batch_result.partial_success == True
        assert batch_result.succeeded == False
        assert batch_result.failed == False

    def test_batch_execution_result_duration_none_line_246(self):
        """Test BatchExecutionResult.duration returning None (line 246)"""

        # Create a batch result without end_time to trigger line 246
        batch_result_no_end = BatchExecutionResult(
            status=BatchStatus.RUNNING,
            workspace_results=[],
            total_records=0,
            total_execution_time=0.0,
            job_correlation_id="test-job-123",
            start_time=datetime.now(timezone.utc),
            end_time=None,  # This should trigger line 246 in duration property
            successful_workspaces=0,
            failed_workspaces=0,
        )

        # This should trigger line 246: return None
        assert batch_result_no_end.duration is None

        # Verify the property works with end_time set
        now = datetime.now(timezone.utc)
        batch_result_with_end = BatchExecutionResult(
            status=BatchStatus.SUCCESS,
            workspace_results=[],
            total_records=0,
            total_execution_time=0.0,
            job_correlation_id="test-job-123",
            start_time=now,
            end_time=now,
            successful_workspaces=0,
            failed_workspaces=0,
        )

        # This should calculate the duration (not trigger line 246)
        assert batch_result_with_end.duration == 0.0

    def test_service_properties_line_285(self):
        """Test ServiceProperties creation and __post_init__ (line 285)"""

        # Test ServiceProperties creation with last_check_time provided
        specific_time = datetime.now(timezone.utc)
        service_props_with_time = ServiceProperties(
            service_version="1.0.0",
            connectivity_status="connected",
            authentication_status="authenticated",
            dcr_endpoint="https://example.dce.endpoint",
            dcr_rule_id="dcr-rule-123",
            workspace_count=5,
            available_queries=10,
            available_reports=3,
            last_check_time=specific_time,
        )

        assert service_props_with_time.service_version == "1.0.0"
        assert service_props_with_time.last_check_time == specific_time

        # Test ServiceProperties creation without last_check_time (should trigger line 285)
        service_props_auto_time = ServiceProperties(
            service_version="1.0.0",
            connectivity_status="connected",
            authentication_status="authenticated",
            dcr_endpoint="https://example.dce.endpoint",
            dcr_rule_id="dcr-rule-123",
            workspace_count=5,
            available_queries=10,
            available_reports=3,
            last_check_time=None,  # This should trigger __post_init__ line 285
        )

        # This should trigger the __post_init__ method and set last_check_time to now
        assert service_props_auto_time.last_check_time is not None
        assert isinstance(service_props_auto_time.last_check_time, datetime)

        # Test ServiceProperties creation with default None (triggers line 285)
        service_props_default = ServiceProperties(
            service_version="1.0.0",
            connectivity_status="connected",
            authentication_status="authenticated",
            dcr_endpoint="https://example.dce.endpoint",
            dcr_rule_id="dcr-rule-123",
            workspace_count=5,
            available_queries=10,
            available_reports=3,
            # last_check_time defaults to None, should trigger line 285
        )

        assert service_props_default.last_check_time is not None
        assert isinstance(service_props_default.last_check_time, datetime)

    def test_comprehensive_edge_cases(self):
        """Test edge cases and boundary conditions"""

        # Test empty results
        empty_query_result = QueryResult(
            status=QueryStatus.SUCCESS,
            data=[],
            record_count=0,
            execution_time=0.1,
            workspace_id="test-workspace-id",
            query="TestQuery",
        )
        assert empty_query_result.workspace_alias == "test-wor..."
        assert empty_query_result.succeeded == True

        # Test WorkspaceQueryExecution with minimal data
        minimal_workspace_execution = WorkspaceQueryExecution(
            workspace_id="minimal-id",
            workspace_alias="minimal_workspace",
            query_result=empty_query_result,
        )
        assert minimal_workspace_execution.upload_result is None
        assert minimal_workspace_execution.correlation_id is None

        # Test BatchExecutionResult with empty workspace executions
        empty_batch_result = BatchExecutionResult(
            status=BatchStatus.SUCCESS,
            workspace_results=[],
            total_records=0,
            total_execution_time=0.0,
            job_correlation_id="empty-job",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            successful_workspaces=0,
            failed_workspaces=0,
        )
        assert empty_batch_result.success_rate == 0.0
        assert empty_batch_result.succeeded == True


class TestResponsesStatusEnums:
    """Test status enum behaviors"""

    def test_query_status_values(self):
        """Test QueryStatus enum values"""
        assert QueryStatus.PENDING == "pending"
        assert QueryStatus.SUCCESS == "success"
        assert QueryStatus.COMPLETED == "success"  # Alias for SUCCESS
        assert QueryStatus.FAILED == "failed"
        assert QueryStatus.TIMEOUT == "timeout"
        assert QueryStatus.CANCELLED == "cancelled"

    def test_upload_status_values(self):
        """Test UploadStatus enum values"""
        assert UploadStatus.PENDING == "pending"
        assert UploadStatus.SUCCESS == "success"
        assert UploadStatus.FAILED == "failed"
        assert UploadStatus.SKIPPED == "skipped"

    def test_batch_status_values(self):
        """Test BatchStatus enum values"""
        assert BatchStatus.PENDING == "pending"
        assert BatchStatus.RUNNING == "running"
        assert BatchStatus.SUCCESS == "success"
        assert BatchStatus.FAILED == "failed"
        assert BatchStatus.CANCELLED == "cancelled"
        assert BatchStatus.PARTIAL_SUCCESS == "partial_success"
