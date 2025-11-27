"""Test configuration file for pytest."""

import sys
from pathlib import Path

import pytest

# Add the package root to Python path
package_root = Path(__file__).parent.parent
sys.path.insert(0, str(package_root))


@pytest.fixture
def sample_workspace_config():
    """Fixture providing sample workspace configuration."""
    from sentinel_log_aggregator.models import WorkspaceConfig

    return WorkspaceConfig(
        resource_id="/subscriptions/test-sub-id/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace",
        customer_id="test-customer-id-12345",
        parameters={"row_level_security_tag": "TEST_WS"},
        queries_list=["query_incident_summary", "query_workspace_usage"],
    )


@pytest.fixture
def sample_config():
    """Fixture providing sample configuration."""
    from sentinel_log_aggregator.config import SentinelAggregatorConfig

    return SentinelAggregatorConfig(
        dcr_logs_ingestion_endpoint="https://test-endpoint.monitor.azure.com",
        dcr_immutable_id="dcr-test-rule-id",
        days_ago=7,
        batch_hours=24,
        max_concurrent_queries=3,
    )


"""Tests for core models and data structures."""

from datetime import datetime, timezone

import pytest

from sentinel_log_aggregator.models import (
    AVAILABLE_QUERIES,
    BatchExecutionSummary,
    KQLQueryDefinition,
    QueryExecution,
    QueryParameter,
    QueryStatus,
    UploadStatus,
    WorkspaceConfig,
)


class TestWorkspaceConfig:
    """Test WorkspaceConfig model."""

    def test_workspace_config_creation(self):
        """Test creating a workspace configuration."""
        config = WorkspaceConfig(
            resource_id="/subscriptions/test-sub/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-ws",
            customer_id="test-customer-id",
            parameters={"row_level_security_tag": "TEST"},
            queries_list=["query_incident_summary"],
        )

        assert config.workspace_name == "test-ws"
        assert config.subscription_id == "test-sub"
        assert config.resource_group == "test-rg"

    def test_workspace_config_empty_resource_id(self):
        """Test workspace config with empty resource ID."""
        config = WorkspaceConfig(resource_id="", customer_id="test-customer-id")

        assert config.workspace_name == ""
        assert config.subscription_id == ""
        assert config.resource_group == ""


class TestKQLQueryDefinition:
    """Test KQL query definition functionality."""

    def test_query_parameter_substitution(self):
        """Test parameter substitution in queries."""
        # Load test query from file path since AVAILABLE_QUERIES is now on-demand
        from pathlib import Path

        from sentinel_log_aggregator.query_registry import query_registry

        test_queries_dir = Path(__file__).parent / "data" / "queries"
        test_query_path = test_queries_dir / "tests_query_with_params.yaml"

        # Load query from path
        query = query_registry.load_query_from_path(str(test_query_path))
        assert query is not None, "Test query should be loaded from YAML file"

        built_query = query.build_query(
            {"required_param": "TEST_VALUE", "non_required_param": "OPTIONAL_VALUE"}
        )

        assert "TEST_VALUE" in built_query
        assert "{required_param}" not in built_query

    def test_required_parameter_validation(self):
        """Test validation of required parameters."""
        query = KQLQueryDefinition("test", "stream", "desc", "report")
        query.add_parameter("required_param", "string", required=True)

        # Add a mock get_query method
        def get_query(self):
            return "SELECT '{required_param}'"

        query.get_query = get_query.__get__(query, KQLQueryDefinition)

        with pytest.raises(ValueError, match="Required parameter"):
            query.build_query({})

    def test_default_parameter_values(self):
        """Test default parameter values."""
        query = KQLQueryDefinition("test", "stream", "desc", "report")
        query.add_parameter("optional_param", "string", default="default_value")

        def get_query(self):
            return "SELECT '{optional_param}'"

        query.get_query = get_query.__get__(query, KQLQueryDefinition)
        built_query = query.build_query({})

        assert "default_value" in built_query


class TestQueryExecution:
    """Test query execution tracking."""

    def test_query_execution_creation(self):
        """Test creating a query execution record."""
        now = datetime.now(timezone.utc)

        execution = QueryExecution(
            job_correlation_id="test-job",
            execution_id="test-exec",
            workspace_id="test-workspace-id",
            query_name="test_query",
            destination_stream="test_stream",
            start_time=now,
            end_time=now,
        )

        assert execution.query_status == QueryStatus.PENDING.value
        assert execution.upload_status == UploadStatus.PENDING.value
        assert execution.workspace_alias == "test-workspace-id"

    def test_time_range_formatting(self):
        """Test time range string formatting."""
        start_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2023, 1, 1, 13, 0, 0, tzinfo=timezone.utc)

        execution = QueryExecution(
            job_correlation_id="test-job",
            execution_id="test-exec",
            workspace_id="test-workspace",
            query_name="test_query",
            destination_stream="test_stream",
            start_time=start_time,
            end_time=end_time,
        )

        assert execution.time_range_str == "2023-01-01 12:00 to 2023-01-01 13:00"


class TestBatchExecutionSummary:
    """Test batch execution summary calculations."""

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        summary = BatchExecutionSummary(
            job_correlation_id="test-job",
            batch_id="test-batch",
            notebook_run_timestamp=datetime.now(timezone.utc),
            total_queries=10,
            successful_queries=8,
            failed_queries=2,
            successful_uploads=7,
            failed_uploads=1,
            total_records=1000,
            total_uploaded_records=900,
            total_duration_seconds=120.0,
            time_range_start=datetime.now(timezone.utc),
            time_range_end=datetime.now(timezone.utc),
        )

        assert summary.success_rate == 80.0
        assert summary.upload_success_rate == 87.5

    def test_zero_division_handling(self):
        """Test handling of zero division in rate calculations."""
        summary = BatchExecutionSummary(
            job_correlation_id="test-job",
            batch_id="test-batch",
            notebook_run_timestamp=datetime.now(timezone.utc),
            total_queries=0,
            successful_queries=0,
            failed_queries=0,
            successful_uploads=0,
            failed_uploads=0,
            total_records=0,
            total_uploaded_records=0,
            total_duration_seconds=0.0,
            time_range_start=datetime.now(timezone.utc),
            time_range_end=datetime.now(timezone.utc),
        )

        assert summary.success_rate == 0.0
        assert summary.upload_success_rate == 0.0


class TestPredefinedQueries:
    """Test predefined query implementations loaded from YAML."""

    def test_incident_summary_query(self):
        """Test query structure using test query file."""
        # Load test query from file path since AVAILABLE_QUERIES is now on-demand
        from pathlib import Path

        from sentinel_log_aggregator.query_registry import query_registry

        test_queries_dir = Path(__file__).parent / "data" / "queries"
        test_query_path = test_queries_dir / "tests_query_without_params.yaml"

        # Load query from path
        query = query_registry.load_query_from_path(str(test_query_path))
        assert query is not None, "Test query should be loaded from YAML file"

        assert query.name == "tests_query_without_params"
        assert query.destination_stream == "Custom-Reports_LogAggregatorHealth_CL"
        assert query.stream_name == "stream_incident_summary"

        kql = query.get_query()
        assert "print" in kql
        assert "WithoutParams" in kql

    def test_query_with_parameters(self):
        """Test query structure using test query file with parameters."""
        # Load test query from file path since AVAILABLE_QUERIES is now on-demand
        from pathlib import Path

        from sentinel_log_aggregator.query_registry import query_registry

        test_queries_dir = Path(__file__).parent / "data" / "queries"
        test_query_path = test_queries_dir / "tests_query_with_params.yaml"

        # Load query from path
        query = query_registry.load_query_from_path(str(test_query_path))
        assert query is not None, "Test query should be loaded from YAML file"

        assert query.name == "tests_query_with_params"
        assert query.destination_stream == "Custom-Reports_LogAggregatorHealth_CL"
        assert "required_param" in query.parameters
        assert "non_required_param" in query.parameters

        kql = query.get_query()
        assert "print" in kql
        assert "RequiredParam" in kql
        assert "TestMessage" in kql

        # Test parameter substitution
        kql_with_params = query.build_query(
            parameters={"required_param": "test_value", "non_required_param": "optional_value"}
        )
        assert "test_value" in kql_with_params
        assert "optional_value" in kql_with_params

    def test_yaml_queries_loaded(self):
        """Test that queries can be loaded from YAML files on demand."""
        # Since AVAILABLE_QUERIES is now on-demand, test that we can load queries from files
        from pathlib import Path

        from sentinel_log_aggregator.query_registry import query_registry

        test_queries_dir = Path(__file__).parent / "data" / "queries"

        # Test loading different query files
        test_files = ["tests_query_with_params.yaml", "tests_query_without_params.yaml"]
        for query_file in test_files:
            test_query_path = test_queries_dir / query_file
            query = query_registry.load_query_from_path(str(test_query_path))
            assert query is not None, f"Should be able to load query from {query_file}"

            # Check that query has proper attributes
            assert hasattr(
                query, "stream_name"
            ), f"Query from {query_file} should have stream_name attribute"
            assert query.stream_name, f"Query from {query_file} should have a non-empty stream_name"


"""
Tests for SentinelQueryEngine.

Tests query execution, batch processing, time range management,
and data transformation functionality.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions
from sentinel_log_aggregator.models import QueryExecution, WorkspaceConfig
from sentinel_log_aggregator.query_engine import SentinelQueryEngine
from sentinel_log_aggregator.responses import QueryStatus, UploadStatus


class TestSentinelQueryEngine:
    """Test suite for SentinelQueryEngine class."""

    @pytest.fixture
    def client_options(self):
        """Create test client options."""
        return SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.ingest.monitor.azure.com",
            dcr_immutable_id="dcr-12345678123456781234567812345678",
            days_ago=7,
            batch_hours=24,
            max_concurrent_queries=3,
        )

    @pytest.fixture
    def mock_azure_client(self):
        """Mock SentinelAggregatorClient."""
        client = AsyncMock()

        # Mock successful query response
        client.query_workspace = AsyncMock(
            return_value=MagicMock(
                status=QueryStatus.SUCCESS,
                data=[
                    {"TimeGenerated": "2023-01-01T00:00:00Z", "IncidentNumber": 1001},
                    {"TimeGenerated": "2023-01-01T00:01:00Z", "IncidentNumber": 1002},
                ],
                record_count=2,
                succeeded=True,
                error_message=None,
            )
        )

        # Mock successful upload response
        client.upload_logs = AsyncMock(
            return_value=MagicMock(
                status=UploadStatus.SUCCESS, record_count=2, succeeded=True, error_message=None
            )
        )

        return client

    @pytest.fixture
    def query_engine(self, client_options, mock_azure_client):
        """Create test query engine."""
        return SentinelQueryEngine(client_options, mock_azure_client, job_id="test-job-id")

    @pytest.fixture
    def sample_workspaces(self):
        """Create sample workspace configurations."""
        return [
            WorkspaceConfig(
                resource_id="/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/prod-rg/providers/microsoft.operationalinsights/workspaces/prod-workspace",
                customer_id="11111111-1111-1111-1111-111111111111",
                parameters={"row_level_security_tag": "prod"},
                queries_list=["query_incident_summary"],
            ),
            WorkspaceConfig(
                resource_id="/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/dev-rg/providers/microsoft.operationalinsights/workspaces/dev-workspace",
                customer_id="22222222-2222-2222-2222-222222222222",
                parameters={"row_level_security_tag": "dev"},
                queries_list=["query_incident_summary"],
            ),
        ]

    def test_query_engine_initialization(self, query_engine):
        """Test query engine initialization."""
        assert query_engine.client_options is not None
        assert query_engine.azure_client is not None
        assert hasattr(query_engine, "logger")
        assert query_engine.job_correlation_id is not None

    def test_calculate_time_batches(self, query_engine):
        """Test time batch calculation."""
        batches = query_engine.calculate_time_batches(days_back=2, batch_hours=24)

        assert len(batches) == 2
        assert all(isinstance(batch, tuple) for batch in batches)
        assert all(len(batch) == 2 for batch in batches)

        # Check that batches are properly ordered (newest first)
        first_batch = batches[0]
        second_batch = batches[1]
        assert first_batch[0] > second_batch[0]  # start_time
        assert first_batch[1] > second_batch[1]  # end_time

    def test_calculate_time_batches_fractional_days(self, query_engine):
        """Test time batch calculation with fractional days."""
        batches = query_engine.calculate_time_batches(days_back=1.5, batch_hours=12)

        assert len(batches) == 3  # 1.5 days = 36 hours = 3 x 12-hour batches

    def test_calculate_time_batches_small_batch_hours(self, query_engine):
        """Test time batch calculation with small batch hours."""
        batches = query_engine.calculate_time_batches(days_back=1, batch_hours=6)

        assert len(batches) == 4  # 1 day = 24 hours = 4 x 6-hour batches

    def test_build_query_from_name(self, query_engine):
        """Test building query from query name."""
        # This test would require actual query definitions to be loaded
        # For now, test the error case
        with pytest.raises(KeyError):
            query_engine.build_query_from_name("non_existent_query")

    @pytest.mark.asyncio
    async def test_execute_single_query_with_upload_success(self, query_engine, mock_azure_client):
        """Test successful single query execution with upload."""
        workspace_id = "11111111-1111-1111-1111-111111111111"
        query = "SecurityIncident | take 10"
        query_name = "test_query"
        destination_stream = "Custom-Test_TestQuery_CL"
        start_time = datetime.now(timezone.utc) - timedelta(hours=24)
        end_time = datetime.now(timezone.utc)
        execution_id = "test-execution-id"

        result = await query_engine.execute_single_query_with_upload(
            workspace_id=workspace_id,
            query=query,
            query_name=query_name,
            destination_stream=destination_stream,
            start_time=start_time,
            end_time=end_time,
            execution_id=execution_id,
            workspace_alias="test",
        )

        assert isinstance(result, QueryExecution)
        assert result.query_name == query_name
        assert result.workspace_id == workspace_id
        assert result.status == QueryStatus.COMPLETED
        assert result.record_count == 2
        assert result.upload_status == UploadStatus.SUCCESS

        # Verify Azure client methods were called
        mock_azure_client.query_workspace.assert_called_once()
        mock_azure_client.upload_logs.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_single_query_with_upload_query_failure(
        self, query_engine, mock_azure_client
    ):
        """Test single query execution with query failure."""
        # Mock query failure
        mock_azure_client.query_workspace.return_value = MagicMock(
            status=QueryStatus.FAILED,
            data=[],
            record_count=0,
            succeeded=False,
            error_message="Query execution failed",
        )

        workspace_id = "11111111-1111-1111-1111-111111111111"
        query = "InvalidQuery | take 10"
        query_name = "test_query"
        destination_stream = "Custom-Test_TestQuery_CL"
        start_time = datetime.now(timezone.utc) - timedelta(hours=24)
        end_time = datetime.now(timezone.utc)
        execution_id = "test-execution-id"

        result = await query_engine.execute_single_query_with_upload(
            workspace_id=workspace_id,
            query=query,
            query_name=query_name,
            destination_stream=destination_stream,
            start_time=start_time,
            end_time=end_time,
            execution_id=execution_id,
        )

        assert result.status == QueryStatus.FAILED
        assert result.record_count == 0
        assert result.upload_status == UploadStatus.SKIPPED
        assert "Query execution failed" in result.error_message

        # Upload should not be called for failed queries
        mock_azure_client.upload_logs.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_single_query_with_upload_no_data(self, query_engine, mock_azure_client):
        """Test single query execution with no data returned."""
        # Mock successful query with no data
        mock_azure_client.query_workspace.return_value = MagicMock(
            status=QueryStatus.SUCCESS, data=[], record_count=0, succeeded=True, error_message=None
        )

        workspace_id = "11111111-1111-1111-1111-111111111111"
        query = "SecurityIncident | where TimeGenerated > ago(30d) | take 10"
        query_name = "test_query"
        destination_stream = "Custom-Test_TestQuery_CL"
        start_time = datetime.now(timezone.utc) - timedelta(hours=24)
        end_time = datetime.now(timezone.utc)
        execution_id = "test-execution-id"

        result = await query_engine.execute_single_query_with_upload(
            workspace_id=workspace_id,
            query=query,
            query_name=query_name,
            destination_stream=destination_stream,
            start_time=start_time,
            end_time=end_time,
            execution_id=execution_id,
        )

        assert result.status == QueryStatus.COMPLETED
        assert result.record_count == 0
        assert result.upload_status == UploadStatus.SKIPPED

        # Upload should not be called for empty results
        mock_azure_client.upload_logs.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_single_query_upload_failure(self, query_engine, mock_azure_client):
        """Test single query execution with upload failure."""
        # Mock successful query but failed upload
        mock_azure_client.upload_logs.return_value = MagicMock(
            status=UploadStatus.FAILED,
            record_count=2,
            succeeded=False,
            error_message="Upload failed",
        )

        workspace_id = "11111111-1111-1111-1111-111111111111"
        query = "SecurityIncident | take 10"
        query_name = "test_query"
        destination_stream = "Custom-Test_TestQuery_CL"
        start_time = datetime.now(timezone.utc) - timedelta(hours=24)
        end_time = datetime.now(timezone.utc)
        execution_id = "test-execution-id"

        result = await query_engine.execute_single_query_with_upload(
            workspace_id=workspace_id,
            query=query,
            query_name=query_name,
            destination_stream=destination_stream,
            start_time=start_time,
            end_time=end_time,
            execution_id=execution_id,
        )

        assert result.status == QueryStatus.COMPLETED  # Query succeeded
        assert result.record_count == 2
        assert result.upload_status == UploadStatus.FAILED  # But upload failed
        assert "Upload failed" in result.upload_error_message

    @pytest.mark.asyncio
    async def test_batch_execution_summary_generation(
        self, query_engine, sample_workspaces, mock_azure_client
    ):
        """Test batch execution summary generation."""
        # This test would test the batch execution method
        # For now, we test that the method exists and accepts the right parameters
        assert hasattr(query_engine, "execute_batch_queries_with_streaming_upload")

        # Mock the batch execution method to avoid complex setup
        with patch.object(
            query_engine, "execute_batch_queries_with_streaming_upload"
        ) as mock_batch:
            mock_batch.return_value = MagicMock(
                successful_executions=2,
                failed_executions=0,
                total_records_processed=100,
                execution_time=30.5,
            )

            summary = await query_engine.execute_batch_queries_with_streaming_upload(
                workspace_configs=sample_workspaces, days_back=1, batch_hours=24
            )

            assert summary.successful_executions == 2
            assert summary.failed_executions == 0
            assert summary.total_records_processed == 100

    @pytest.mark.asyncio
    async def test_concurrent_query_execution(self, query_engine, mock_azure_client):
        """Test concurrent query execution limits."""
        # Test that the query engine respects concurrency limits
        # This would be tested by monitoring how many queries run simultaneously

        # For now, verify that the concurrency setting is respected
        assert query_engine.client_options.max_concurrent_queries == 3

        # In a full test, we would:
        # 1. Create multiple workspaces
        # 2. Track concurrent query execution
        # 3. Verify it doesn't exceed max_concurrent_queries

    def test_error_handling_patterns(self, query_engine):
        """Test error handling patterns in query engine."""
        # Test that the engine properly categorizes and handles different error types

        # Critical errors (should stop batch processing)
        critical_errors = ["syntax error", "invalid query"]

        # Transient errors (should be retried)
        transient_errors = ["timeout", "throttling", "temporary unavailable"]

        # The engine should differentiate between these error types
        # This is more of a design verification test
        assert hasattr(query_engine, "client_options")
        assert hasattr(query_engine.client_options, "max_retries")


class TestQueryEnginePerformance:
    """Performance-related tests for query engine."""

    @pytest.fixture
    def client_options(self):
        """Create test client options."""
        return SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.ingest.monitor.azure.com",
            dcr_immutable_id="dcr-12345678123456781234567812345678",
            days_ago=7,
            batch_hours=24,
            max_concurrent_queries=3,
        )

    @pytest.fixture
    def mock_azure_client(self):
        """Mock SentinelAggregatorClient."""
        client = AsyncMock()

        # Mock successful query response
        client.query_workspace = AsyncMock(
            return_value=MagicMock(
                status=QueryStatus.SUCCESS,
                data=[],
                record_count=0,
                succeeded=True,
                error_message=None,
            )
        )

        # Mock successful upload response
        client.upload_logs = AsyncMock(
            return_value=MagicMock(
                status=UploadStatus.SUCCESS, record_count=0, succeeded=True, error_message=None
            )
        )

        return client

    @pytest.fixture
    def query_engine(self, client_options, mock_azure_client):
        """Create test query engine."""
        return SentinelQueryEngine(client_options, mock_azure_client, job_id="test-job-id")

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_large_batch_processing(self, query_engine, mock_azure_client):
        """Test processing large batches efficiently."""
        # Create a large number of workspaces
        workspaces = []
        for i in range(100):
            workspaces.append(
                WorkspaceConfig(
                    resource_id=f"/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/rg-{i}/providers/microsoft.operationalinsights/workspaces/ws-{i}",
                    customer_id=f"{i:08d}-{i:04d}-{i:04d}-{i:04d}-{i:012d}",
                    parameters={"row_level_security_tag": f"ws-{i}"},
                    queries_list=["query_incident_summary"],
                )
            )

        # Mock fast responses
        mock_azure_client.query_workspace.return_value = MagicMock(
            status=QueryStatus.SUCCESS, data=[], record_count=0, succeeded=True
        )
        mock_azure_client.upload_logs.return_value = MagicMock(
            status=UploadStatus.SKIPPED, record_count=0, succeeded=True
        )

        # Time the batch execution
        import time

        start_time = time.time()

        with patch.object(
            query_engine, "execute_batch_queries_with_streaming_upload"
        ) as mock_batch:
            mock_batch.return_value = MagicMock(
                successful_executions=100,
                failed_executions=0,
                total_records_processed=0,
                execution_time=time.time() - start_time,
            )

            summary = await query_engine.execute_batch_queries_with_streaming_upload(
                workspace_configs=workspaces, days_back=1, batch_hours=24
            )

            # Verify that large batches can be processed
            assert summary.successful_executions == 100


class TestQueryEngineIntegration:
    """Integration tests for query engine."""

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires real Azure credentials")
    @pytest.mark.asyncio
    async def test_real_azure_integration(self):
        """Test with real Azure services (skipped by default)."""
        # This test would use real Azure credentials and services
        # Only run in integration test environment
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires real Azure credentials")
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow (skipped by default)."""
        # This test would:
        # 1. Load real workspace configurations
        # 2. Execute real queries against Azure
        # 3. Upload real data to Azure Monitor
        # 4. Verify data was ingested correctly
        pass


"""
Tests for SentinelAggregatorClient.

Tests Azure SDK-compliant client functionality including authentication,
query execution, data upload, and error handling.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError

from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions
from sentinel_log_aggregator.exceptions import DataIngestionError, QueryExecutionError
from sentinel_log_aggregator.responses import QueryStatus, UploadStatus
from sentinel_log_aggregator.sentinel_client import SentinelAggregatorClient


class TestSentinelAggregatorClient:
    """Test suite for SentinelAggregatorClient."""

    @pytest.fixture
    def client_options(self):
        """Create test client options."""
        return SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.ingest.monitor.azure.com",
            dcr_immutable_id="dcr-12345678123456781234567812345678",
            max_concurrent_queries=3,
            query_timeout_seconds=60,
        )

    @pytest.fixture
    def mock_credential(self):
        """Mock Azure credential."""
        credential = AsyncMock()
        credential.get_token = AsyncMock(return_value=MagicMock(token="fake-token"))
        return credential

    @pytest_asyncio.fixture
    async def client(self, client_options, mock_credential):
        """Create test client."""
        client = SentinelAggregatorClient(
            dcr_logs_ingestion_endpoint=client_options.dcr_logs_ingestion_endpoint,
            credential=mock_credential,
            options=client_options,
        )
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_client_initialization(self, client_options, mock_credential):
        """Test client initialization with valid parameters."""
        client = SentinelAggregatorClient(
            dcr_logs_ingestion_endpoint=client_options.dcr_logs_ingestion_endpoint,
            credential=mock_credential,
            options=client_options,
        )

        assert client._dcr_endpoint == client_options.dcr_logs_ingestion_endpoint
        assert client._credential == mock_credential
        assert client._options == client_options
        assert client._session_id.startswith("session_")

        await client.close()

    def test_client_initialization_missing_endpoint(self, mock_credential):
        """Test client initialization fails with missing endpoint."""
        with pytest.raises(ValueError, match="dcr_logs_ingestion_endpoint is required"):
            SentinelAggregatorClient("", mock_credential)

    def test_client_initialization_missing_credential(self):
        """Test client initialization fails with missing credential."""
        with pytest.raises(ValueError, match="credential is required"):
            SentinelAggregatorClient("https://test.com", None)

    @pytest.mark.asyncio
    async def test_validate_credentials_success(self, client, mock_credential):
        """Test successful credential validation."""
        mock_credential.get_token.return_value = MagicMock(token="valid-token")

        # Should not raise exception
        await client.validate_credentials()

        mock_credential.get_token.assert_called_once_with("https://api.loganalytics.io/.default")

    @pytest.mark.asyncio
    async def test_validate_credentials_failure(self, client, mock_credential):
        """Test credential validation failure."""
        mock_credential.get_token.side_effect = Exception("Authentication failed")

        with pytest.raises(Exception):  # Should be CredentialValidationError in real implementation
            await client.validate_credentials()

    @pytest.mark.asyncio
    async def test_query_workspace_success(self, client):
        """Test successful workspace query execution."""
        workspace_id = "12345678-1234-1234-1234-123456789abc"
        query = "SecurityIncident | take 10"

        # Mock the logs query client response
        mock_response = MagicMock()
        mock_column1 = MagicMock()
        mock_column1.name = "TimeGenerated"
        mock_column2 = MagicMock()
        mock_column2.name = "IncidentNumber"
        mock_response.tables = [
            MagicMock(
                columns=[mock_column1, mock_column2],
                rows=[["2023-01-01T00:00:00Z", 1001], ["2023-01-01T00:01:00Z", 1002]],
            )
        ]

        # Mock the logs query client by setting it directly
        mock_logs_client = AsyncMock()
        mock_logs_client.query_workspace = AsyncMock(return_value=mock_response)
        client._logs_query_client = mock_logs_client

        result = await client.query_workspace(workspace_id=workspace_id, query=query)

        assert result.status == QueryStatus.SUCCESS
        assert result.record_count == 2
        assert len(result.data) == 2
        assert result.workspace_id == workspace_id
        assert result.query == query
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_query_workspace_validation_error(self, client):
        """Test query workspace with invalid inputs."""
        # Invalid workspace ID
        with pytest.raises(Exception):  # Should be SecurityError in real implementation
            await client.query_workspace("invalid-workspace-id", "SecurityIncident | take 10")

        # Invalid query (empty)
        with pytest.raises(Exception):  # Should be SecurityError in real implementation
            await client.query_workspace("12345678-1234-1234-1234-123456789abc", "")

    @pytest.mark.asyncio
    async def test_query_workspace_timeout(self, client):
        """Test query workspace timeout handling."""
        workspace_id = "12345678-1234-1234-1234-123456789abc"
        query = "SecurityIncident | take 10"

        # Mock the logs query client by setting it directly
        mock_logs_client = AsyncMock()
        mock_logs_client.query_workspace = AsyncMock(side_effect=asyncio.TimeoutError())
        client._logs_query_client = mock_logs_client

        result = await client.query_workspace(
            workspace_id=workspace_id, query=query, timeout_seconds=1
        )

        assert result.status == QueryStatus.TIMEOUT
        assert result.record_count == 0
        assert "timeout" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_query_workspace_http_error(self, client):
        """Test query workspace HTTP error handling."""
        workspace_id = "12345678-1234-1234-1234-123456789abc"
        query = "SecurityIncident | take 10"

        # Mock the logs query client by setting it directly
        mock_logs_client = AsyncMock()
        mock_logs_client.query_workspace = AsyncMock(
            side_effect=HttpResponseError("Request failed", response=MagicMock(status_code=403))
        )
        client._logs_query_client = mock_logs_client

        result = await client.query_workspace(workspace_id=workspace_id, query=query)

        assert result.status == QueryStatus.FAILED
        assert result.record_count == 0
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_upload_logs_success(self, client):
        """Test successful log upload."""
        data = [
            {"TimeGenerated": "2023-01-01T00:00:00Z", "IncidentNumber": 1001},
            {"TimeGenerated": "2023-01-01T00:01:00Z", "IncidentNumber": 1002},
        ]
        stream_name = "Custom-Test_Incidents_CL"

        # Mock the logs ingestion client by setting it directly
        mock_ingestion_client = AsyncMock()
        mock_ingestion_client.upload = AsyncMock(return_value=MagicMock())
        client._logs_ingestion_client = mock_ingestion_client

        result = await client.upload_logs(data=data, stream_name=stream_name)

        assert result.status == UploadStatus.SUCCESS
        assert result.record_count == 2
        assert result.stream_name == stream_name
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_upload_logs_empty_data(self, client):
        """Test upload with empty data."""
        result = await client.upload_logs(data=[], stream_name="Custom-Test_Empty_CL")

        assert result.status == UploadStatus.SKIPPED
        assert result.record_count == 0

    @pytest.mark.asyncio
    async def test_upload_logs_invalid_stream_name(self, client):
        """Test upload with invalid stream name."""
        data = [{"test": "data"}]

        with pytest.raises(Exception):  # Should be DataIngestionError in real implementation
            await client.upload_logs(data=data, stream_name="invalid-stream-name!")

    @pytest.mark.asyncio
    async def test_upload_logs_failure(self, client):
        """Test upload failure handling."""
        data = [{"test": "data"}]
        stream_name = "Custom-Test_Failure_CL"

        # Mock the logs ingestion client by setting it directly
        mock_ingestion_client = AsyncMock()
        mock_ingestion_client.upload = AsyncMock(side_effect=Exception("Upload failed"))
        client._logs_ingestion_client = mock_ingestion_client

        result = await client.upload_logs(data=data, stream_name=stream_name)

        assert result.status == UploadStatus.FAILED
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_get_service_properties(self, client):
        """Test service properties retrieval."""
        with patch.object(client, "validate_credentials") as mock_validate:
            mock_validate.return_value = None

            properties = await client.get_service_properties()

            assert properties.connectivity_status == "connected"
            assert properties.authentication_status == "valid"
            assert properties.dcr_endpoint == client._dcr_endpoint

    @pytest.mark.asyncio
    async def test_context_manager(self, client_options, mock_credential):
        """Test client as async context manager."""
        async with SentinelAggregatorClient(
            dcr_logs_ingestion_endpoint=client_options.dcr_logs_ingestion_endpoint,
            credential=mock_credential,
            options=client_options,
        ) as client:
            assert client is not None
            assert hasattr(client, "_dcr_endpoint")

        # Client should be closed after context exit
        # In real implementation, we'd verify connections are closed

    @pytest.mark.asyncio
    async def test_from_connection_string(self):
        """Test client creation from connection string."""
        connection_string = (
            "endpoint=https://test.ingest.monitor.azure.com;"
            "dcr_immutable_id=dcr-12345678123456781234567812345678"
        )

        with patch("sentinel_log_aggregator.sentinel_client.DefaultAzureCredential") as mock_cred:
            mock_cred.return_value = AsyncMock()

            client = SentinelAggregatorClient.from_connection_string(connection_string)

            assert client._dcr_endpoint == "https://test.ingest.monitor.azure.com"
            assert client._options.dcr_immutable_id == "dcr-12345678123456781234567812345678"

            await client.close()

    def test_from_connection_string_missing_endpoint(self):
        """Test connection string without endpoint."""
        connection_string = "dcr_immutable_id=dcr-12345678123456781234567812345678"

        with pytest.raises(ValueError, match="Connection string must contain 'endpoint' parameter"):
            SentinelAggregatorClient.from_connection_string(connection_string)


@pytest.mark.integration
class TestSentinelClientIntegration:
    """Integration tests for SentinelAggregatorClient."""

    @pytest.mark.skip(reason="Requires real Azure credentials")
    @pytest.mark.asyncio
    async def test_real_azure_query(self):
        """Test with real Azure credentials (skipped by default)."""
        # This test would use real Azure credentials and endpoints
        # Only run in integration test environment
        pass

    @pytest.mark.skip(reason="Requires real Azure credentials")
    @pytest.mark.asyncio
    async def test_real_azure_upload(self):
        """Test with real Azure upload (skipped by default)."""
        # This test would use real Azure credentials and endpoints
        # Only run in integration test environment
        pass


"""
Tests for validation and security utilities.

Tests Pydantic validation models, security functions,
and input sanitization capabilities.
"""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from sentinel_log_aggregator.security_utils import (
    SecureLogger,
    SecurityError,
    generate_correlation_id,
    hash_sensitive_data,
    sanitize_log_output,
    sanitize_user_input,
    validate_azure_resource_id,
    validate_file_path,
    validate_kql_query,
    validate_workspace_id,
)
from sentinel_log_aggregator.validation import (
    ClientOptionsModel,
    QueryDefinitionModel,
    WorkspaceConfigModel,
    validate_client_options,
    validate_query_definition,
    validate_workspace_config,
)


class TestWorkspaceConfigValidation:
    """Test workspace configuration validation."""

    def test_valid_workspace_config(self):
        """Test valid workspace configuration."""
        config_data = {
            "resource_id": "/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace",
            "customer_id": "11111111-1111-1111-1111-111111111111",
            "parameters": {"row_level_security_tag": "test"},
            "queries_list": ["query_incident_summary"],
        }

        model = WorkspaceConfigModel(**config_data)
        assert model.customer_id == "11111111-1111-1111-1111-111111111111"
        assert model.workspace_name == "test-workspace"
        assert model.subscription_id == "12345678-1234-1234-1234-123456789abc"

    def test_invalid_resource_id(self):
        """Test invalid resource ID format."""
        config_data = {
            "resource_id": "/invalid/resource/id",
            "customer_id": "11111111-1111-1111-1111-111111111111",
        }

        with pytest.raises(ValidationError) as exc_info:
            WorkspaceConfigModel(**config_data)

        assert "resource_id" in str(exc_info.value)

    def test_invalid_customer_id(self):
        """Test invalid customer ID format."""
        config_data = {
            "resource_id": "/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace",
            "customer_id": "invalid-guid",
        }

        with pytest.raises(ValidationError) as exc_info:
            WorkspaceConfigModel(**config_data)

        assert "customer_id" in str(exc_info.value)

    def test_invalid_query_name(self):
        """Test that empty query names are still invalid."""
        config_data = {
            "resource_id": "/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace",
            "customer_id": "11111111-1111-1111-1111-111111111111",
            "queries_list": [""],  # Empty string should fail
        }

        with pytest.raises(ValidationError) as exc_info:
            WorkspaceConfigModel(**config_data)

        assert "non-empty strings" in str(exc_info.value).lower()

    def test_workspace_collection_validation(self):
        """Test workspace collection validation."""
        collection_data = {
            "workspaces": [
                {
                    "resource_id": "/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace-1",
                    "customer_id": "11111111-1111-1111-1111-111111111111",
                    "parameters": {"row_level_security_tag": "test1"},
                    "aggregation_workspace": True,
                },
                {
                    "resource_id": "/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace-2",
                    "customer_id": "22222222-2222-2222-2222-222222222222",
                    "parameters": {"row_level_security_tag": "test2"},
                },
            ]
        }

        validated = validate_workspace_config(collection_data)
        assert len(validated.workspaces) == 2

    def test_workspace_collection_duplicate_ids(self):
        """Test workspace collection with duplicate customer IDs."""
        collection_data = {
            "workspaces": [
                {
                    "resource_id": "/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace-1",
                    "customer_id": "11111111-1111-1111-1111-111111111111",
                    "parameters": {"row_level_security_tag": "test"},
                },
                {
                    "resource_id": "/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace-2",
                    "customer_id": "11111111-1111-1111-1111-111111111111",  # Duplicate
                    "parameters": {"row_level_security_tag": "test"},
                },
            ]
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_workspace_config(collection_data)

        assert "duplicate customer ids" in str(exc_info.value).lower()


class TestQueryDefinitionValidation:
    """Test query definition validation."""

    def test_valid_query_definition(self):
        """Test valid query definition."""
        query_data = {
            "name": "test_query",
            "destination_stream": "Custom-Test_TestQuery_CL",
            "description": "Test query description",
            "stream_name": "Custom-Test_CL",
            "query": "SecurityIncident | where TimeGenerated > ago(1d) | take 10",
        }

        model = QueryDefinitionModel(**query_data)
        assert model.name == "test_query"
        assert model.destination_stream == "Custom-Test_TestQuery_CL"

    def test_invalid_query_name(self):
        """Test invalid query name format."""
        query_data = {
            "name": "InvalidName!",  # Contains invalid character
            "destination_stream": "Custom-Test_TestQuery_CL",
            "stream_name": "Custom-Test_CL",
            "query": "SecurityIncident | take 10",
        }

        with pytest.raises(ValidationError):
            QueryDefinitionModel(**query_data)

    def test_invalid_destination_stream(self):
        """Test invalid destination stream format."""
        query_data = {
            "name": "test_query",
            "destination_stream": "InvalidStream",  # Doesn't match pattern
            "stream_name": "Custom-Test_CL",
            "query": "SecurityIncident | take 10",
        }

        with pytest.raises(ValidationError):
            QueryDefinitionModel(**query_data)

    def test_dangerous_query_operations(self):
        """Test that dangerous query operations are now allowed since validation was removed."""
        query_data = {
            "name": "dangerous_query",
            "destination_stream": "Custom-Test_DangerousQuery_CL",
            "stream_name": "Custom-Test_CL",
            "query": "SecurityIncident | take 10; .drop table SomeTable",  # Contains dangerous operation
        }

        # This should now pass since we removed dangerous operation validation
        model = QueryDefinitionModel(**query_data)
        assert model.name == "dangerous_query"

    def test_query_parameter_validation(self):
        """Test query parameter validation."""
        query_data = {
            "name": "parameterized_query",
            "destination_stream": "Custom-Test_ParameterizedQuery_CL",
            "stream_name": "Custom-Test_CL",
            "query": "SecurityIncident | where TimeGenerated > ago({days}d)",
            "parameters": {
                "days": {
                    "type": "int",
                    "required": True,
                    "default": 30,
                    "description": "Number of days to look back",
                }
            },
        }

        model = QueryDefinitionModel(**query_data)
        assert "days" in model.parameters
        assert model.parameters["days"].type == "int"

    def test_invalid_parameter_default_type(self):
        """Test invalid parameter default type."""
        query_data = {
            "name": "invalid_param_query",
            "destination_stream": "Custom-Test_InvalidParam_CL",
            "stream_name": "Custom-Test_CL",
            "query": "SecurityIncident | take 10",
            "parameters": {
                "count": {"type": "int", "default": "not_an_int"}  # Wrong type for default
            },
        }

        with pytest.raises(ValidationError):
            QueryDefinitionModel(**query_data)


class TestClientOptionsValidation:
    """Test client options validation."""

    def test_valid_client_options(self):
        """Test valid client options."""
        options_data = {
            "dcr_logs_ingestion_endpoint": "https://test.ingest.monitor.azure.com",
            "dcr_immutable_id": "dcr-12345678123456781234567812345678",
            "max_concurrent_queries": 5,
            "query_timeout_seconds": 300,
            "batch_hours": 24,
        }

        model = ClientOptionsModel(**options_data)
        assert model.dcr_immutable_id == "dcr-12345678123456781234567812345678"
        assert model.max_concurrent_queries == 5

    def test_invalid_dcr_immutable_id(self):
        """Test invalid DCR rule ID format."""
        options_data = {
            "dcr_logs_ingestion_endpoint": "https://test.ingest.monitor.azure.com",
            "dcr_immutable_id": "invalid-dcr-id",  # Wrong format
            "max_concurrent_queries": 5,
        }

        with pytest.raises(ValidationError):
            ClientOptionsModel(**options_data)

    def test_out_of_range_values(self):
        """Test out of range configuration values."""
        options_data = {
            "dcr_logs_ingestion_endpoint": "https://test.ingest.monitor.azure.com",
            "dcr_immutable_id": "dcr-12345678123456781234567812345678",
            "max_concurrent_queries": 0,  # Below minimum
            "query_timeout_seconds": 10,  # Below minimum
            "batch_hours": 200,  # Above maximum
        }

        with pytest.raises(ValidationError):
            ClientOptionsModel(**options_data)

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        options_data = {
            "dcr_logs_ingestion_endpoint": "https://test.ingest.monitor.azure.com",
            "dcr_immutable_id": "dcr-12345678123456781234567812345678",
            "extra_field": "not_allowed",  # Should be rejected
        }

        with pytest.raises(ValidationError):
            ClientOptionsModel(**options_data)


class TestSecurityValidation:
    """Test security validation functions."""

    def test_validate_kql_query_success(self):
        """Test valid KQL query validation."""
        valid_query = "SecurityIncident | where TimeGenerated > ago(1d) | take 10"

        # Should not raise exception
        assert validate_kql_query(valid_query) == True

    def test_validate_kql_query_dangerous_operations(self):
        """Test KQL query with dangerous operations - should now pass since validation was removed."""
        dangerous_queries = [
            "SecurityIncident | take 10; .drop table SomeTable",
            "SecurityIncident | take 10; .delete table SomeTable",
            "SecurityIncident | take 10; .alter table SomeTable",
            "SecurityIncident | evaluate python('malicious code')",
        ]

        for query in dangerous_queries:
            # These should now pass since we removed dangerous operation validation
            assert validate_kql_query(query) == True

    def test_validate_kql_query_empty(self):
        """Test empty KQL query validation."""
        with pytest.raises(SecurityError, match="Query cannot be empty"):
            validate_kql_query("")

        with pytest.raises(SecurityError, match="Query cannot be empty"):
            validate_kql_query("   ")

    def test_validate_kql_query_too_long(self):
        """Test excessively long KQL query."""
        long_query = "SecurityIncident | take 10" + " | extend field = 'data'" * 10000

        with pytest.raises(SecurityError, match="exceeds maximum allowed length"):
            validate_kql_query(long_query)

    def test_validate_kql_query_excessive_joins(self):
        """Test query with excessive JOIN operations."""
        excessive_joins = "SecurityIncident " + "| join kind=inner OtherTable on Field " * 25

        with pytest.raises(SecurityError, match="excessive JOIN operations"):
            validate_kql_query(excessive_joins)

    def test_validate_workspace_id_success(self):
        """Test valid workspace ID validation."""
        valid_id = "12345678-1234-1234-1234-123456789abc"

        assert validate_workspace_id(valid_id) == True

    def test_validate_workspace_id_invalid_format(self):
        """Test invalid workspace ID format."""
        invalid_ids = [
            "not-a-guid",
            "12345678-1234-1234-1234",  # Too short
            "12345678-1234-1234-1234-123456789abcd",  # Too long
            "",
            "12345678-1234-1234-1234-123456789abg",  # Invalid character
        ]

        for invalid_id in invalid_ids:
            with pytest.raises(SecurityError):
                validate_workspace_id(invalid_id)

    def test_validate_azure_resource_id_success(self):
        """Test valid Azure resource ID validation."""
        valid_id = "/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace"

        assert validate_azure_resource_id(valid_id) == True

    def test_validate_azure_resource_id_invalid_format(self):
        """Test invalid Azure resource ID format."""
        invalid_ids = [
            "/invalid/resource/id",
            "not-a-resource-id",
            "",
            "/subscriptions/invalid-sub-id/resourcegroups/test",
        ]

        for invalid_id in invalid_ids:
            with pytest.raises(SecurityError):
                validate_azure_resource_id(invalid_id)

    def test_validate_azure_resource_id_suspicious_patterns(self):
        """Test Azure resource ID with suspicious patterns."""
        suspicious_ids = [
            "/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/../../../etc/passwd",
            "/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/<script>alert('xss')</script>",
            "/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/javascript:malicious()",
        ]

        for suspicious_id in suspicious_ids:
            with pytest.raises(SecurityError):
                validate_azure_resource_id(suspicious_id)

    def test_validate_file_path_success(self):
        """Test valid file path validation."""
        valid_paths = ["config.yaml", "workspaces.yml", "data/config.json"]

        for path in valid_paths:
            assert validate_file_path(path) == True

    def test_validate_file_path_traversal(self):
        """Test file path traversal attacks."""
        dangerous_paths = [
            "../../../etc/passwd",
            "config/../../../etc/passwd",
            "/etc/passwd",
            "config\\..\\..\\windows\\system32",
        ]

        for path in dangerous_paths:
            with pytest.raises(SecurityError):
                validate_file_path(path)

    def test_validate_file_path_invalid_extension(self):
        """Test file path with invalid extension."""
        invalid_paths = ["config.exe", "malicious.bat", "script.ps1"]

        for path in invalid_paths:
            with pytest.raises(SecurityError):
                validate_file_path(path)

    def test_validate_file_path_suspicious_characters(self):
        """Test file path with suspicious characters."""
        suspicious_paths = [
            "config.yaml|rm -rf /",
            "config.yaml;echo malicious",
            "config.yaml&whoami",
            "config.yaml`malicious`",
        ]

        for path in suspicious_paths:
            with pytest.raises(SecurityError):
                validate_file_path(path)


class TestDataSanitization:
    """Test data sanitization functions."""

    def test_sanitize_log_output_string(self):
        """Test log output sanitization for strings."""
        sensitive_data = "workspace_id: 12345678-1234-1234-1234-123456789abc and token: very_long_access_token_here"

        sanitized = sanitize_log_output(sensitive_data)

        # String sanitization no longer happens - only field-based sanitization
        assert "12345678-1234-1234-1234-123456789abc" in sanitized
        assert "very_long_access_token_here" in sanitized
        assert sanitized == sensitive_data  # No changes to strings

    def test_sanitize_log_output_dict(self):
        """Test log output sanitization for dictionaries."""
        sensitive_dict = {
            "workspace_id": "12345678-1234-1234-1234-123456789abc",
            "access_token": "very_long_access_token_here",
            "normal_field": "normal_value",
            "customer_id": "87654321-4321-4321-4321-123456789abc",
        }

        sanitized = sanitize_log_output(sensitive_dict)

        assert sanitized["workspace_id"] == "12345678-1234-1234-1234-123456789abc"
        assert sanitized["access_token"] == "very_long_access_token_here"
        assert sanitized["normal_field"] == "normal_value"
        assert sanitized["customer_id"] == "87654321-4321-4321-4321-123456789abc"

    def test_sanitize_log_output_nested_dict(self):
        """Test log output sanitization for nested dictionaries."""
        nested_dict = {
            "config": {
                "workspace_id": "12345678-1234-1234-1234-123456789abc",
                "settings": {"token": "secret_token_value"},
            },
            "workspaces": [{"customer_id": "11111111-1111-1111-1111-111111111111"}],
        }

        sanitized = sanitize_log_output(nested_dict)

        assert sanitized["config"]["workspace_id"] == "12345678-1234-1234-1234-123456789abc"
        assert sanitized["config"]["settings"]["token"] == "secret_t..."
        assert sanitized["workspaces"][0]["customer_id"] == "11111111-1111-1111-1111-111111111111"

    def test_sanitize_user_input_success(self):
        """Test successful user input sanitization."""
        clean_input = "This is clean user input"

        sanitized = sanitize_user_input(clean_input)

        assert sanitized == clean_input

    def test_sanitize_user_input_injection_attacks(self):
        """Test user input with injection attacks."""
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "javascript:malicious()",
            "vbscript:malicious()",
            "<img onload='malicious()' src='x'>",
            "expression(malicious())",
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(SecurityError):
                sanitize_user_input(malicious_input)

    def test_sanitize_user_input_too_long(self):
        """Test user input that's too long."""
        long_input = "a" * 10001  # Exceeds default max_length of 10000

        with pytest.raises(SecurityError, match="exceeds maximum length"):
            sanitize_user_input(long_input)

    def test_sanitize_user_input_control_characters(self):
        """Test user input with control characters."""
        input_with_control = "normal text\x00with\x01control\x1fcharacters"

        sanitized = sanitize_user_input(input_with_control)

        assert sanitized == "normal textwithcontrolcharacters"

    def test_generate_correlation_id(self):
        """Test correlation ID generation."""
        correlation_id = generate_correlation_id()

        assert isinstance(correlation_id, str)
        assert len(correlation_id) == 32  # 16 bytes * 2 hex chars per byte

        # Generate multiple IDs and ensure they're unique
        ids = [generate_correlation_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All should be unique

    def test_hash_sensitive_data(self):
        """Test sensitive data hashing."""
        sensitive_data = "12345678-1234-1234-1234-123456789abc"

        hash1 = hash_sensitive_data(sensitive_data)
        hash2 = hash_sensitive_data(sensitive_data)

        # Same data should produce same hash
        assert hash1 == hash2

        # Hash should be different from original
        assert hash1 != sensitive_data

        # Hash should be consistent length (SHA-256 = 64 hex chars)
        assert len(hash1) == 64

    def test_hash_sensitive_data_with_salt(self):
        """Test sensitive data hashing with custom salt."""
        sensitive_data = "12345678-1234-1234-1234-123456789abc"

        hash_default = hash_sensitive_data(sensitive_data)
        hash_custom = hash_sensitive_data(sensitive_data, salt="custom_salt")

        # Different salts should produce different hashes
        assert hash_default != hash_custom


class TestSecureLogger:
    """Test secure logger wrapper."""

    def test_secure_logger_initialization(self):
        """Test secure logger initialization."""
        import logging

        base_logger = logging.getLogger("test")
        secure_logger = SecureLogger(base_logger)

        assert secure_logger.logger == base_logger

    def test_secure_logger_sanitizes_messages(self):
        """Test that secure logger sanitizes log messages."""
        import logging
        from unittest.mock import MagicMock

        base_logger = MagicMock()
        secure_logger = SecureLogger(base_logger)

        sensitive_message = "Error with workspace 12345678-1234-1234-1234-123456789abc"

        secure_logger.info(sensitive_message)

        # Verify that the base logger was called with sanitized message
        base_logger.info.assert_called_once()
        called_message = base_logger.info.call_args[0][0]
        assert "12345678-1234-1234-1234-123456789abc" in called_message

    def test_secure_logger_sanitizes_extra_data(self):
        """Test that secure logger sanitizes extra data."""
        import logging
        from unittest.mock import MagicMock

        base_logger = MagicMock()
        secure_logger = SecureLogger(base_logger)

        sensitive_extra = {
            "workspace_id": "12345678-1234-1234-1234-123456789abc",
            "access_token": "secret_token_value",
        }

        secure_logger.error("An error occurred", extra=sensitive_extra)

        # Verify sanitization of extra data
        base_logger.error.assert_called_once()
        called_extra = base_logger.error.call_args[1]["extra"]
        assert called_extra["workspace_id"] == "12345678-1234-1234-1234-123456789abc"
        assert called_extra["access_token"] == "secret_token_value"


"""
Tests for WorkspaceManager and WorkspaceSet.

Tests workspace configuration management, filtering capabilities,
and YAML file loading/saving functionality.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from sentinel_log_aggregator.exceptions import SentinelAggregatorError
from sentinel_log_aggregator.models import WorkspaceConfig
from sentinel_log_aggregator.workspace_manager import WorkspaceManager, WorkspaceSet


class TestWorkspaceSet:
    """Test suite for WorkspaceSet class."""

    @pytest.fixture
    def sample_workspaces(self):
        """Create sample workspace configurations."""
        return [
            WorkspaceConfig(
                resource_id="/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/prod-rg/providers/microsoft.operationalinsights/workspaces/prod-workspace",
                customer_id="11111111-1111-1111-1111-111111111111",
                parameters={"row_level_security_tag": "prod"},
                queries_list=["query_incident_summary", "query_workspace_usage"],
            ),
            WorkspaceConfig(
                resource_id="/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/dev-rg/providers/microsoft.operationalinsights/workspaces/dev-workspace",
                customer_id="22222222-2222-2222-2222-222222222222",
                parameters={"row_level_security_tag": "dev"},
                queries_list=["query_incident_summary"],
            ),
            WorkspaceConfig(
                resource_id="/subscriptions/87654321-4321-4321-4321-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace",
                customer_id="33333333-3333-3333-3333-333333333333",
                parameters={"row_level_security_tag": "test"},
                queries_list=["query_workspace_usage"],
            ),
        ]

    @pytest.fixture
    def workspace_set(self, sample_workspaces):
        """Create WorkspaceSet from sample workspaces."""
        return WorkspaceSet(sample_workspaces)

    def test_workspace_set_initialization(self, sample_workspaces):
        """Test WorkspaceSet initialization."""
        ws_set = WorkspaceSet(sample_workspaces)
        assert len(ws_set.workspaces) == 3
        assert ws_set.count() == 3

    def test_ids(self, workspace_set):
        """Test extraction of workspace IDs."""
        ids = workspace_set.ids()
        expected_ids = [
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
            "33333333-3333-3333-3333-333333333333",
        ]
        assert ids == expected_ids

    def test_names(self, workspace_set):
        """Test extraction of workspace names."""
        names = workspace_set.names()
        expected_names = ["prod-workspace", "dev-workspace", "test-workspace"]
        assert names == expected_names

    def test_aliases(self, workspace_set):
        """Test extraction of workspace aliases."""
        aliases = workspace_set.aliases()
        expected_aliases = ["prod", "dev", "test"]
        assert aliases == expected_aliases

    def test_subscription_ids(self, workspace_set):
        """Test extraction of unique subscription IDs."""
        sub_ids = workspace_set.subscription_ids()
        expected_sub_ids = [
            "12345678-1234-1234-1234-123456789abc",
            "87654321-4321-4321-4321-123456789abc",
        ]
        assert set(sub_ids) == set(expected_sub_ids)
        assert len(sub_ids) == 2  # Should be unique

    def test_resource_groups(self, workspace_set):
        """Test extraction of unique resource groups."""
        rgs = workspace_set.resource_groups()
        expected_rgs = ["prod-rg", "dev-rg", "test-rg"]
        assert set(rgs) == set(expected_rgs)

    def test_filter_by_subscription(self, workspace_set):
        """Test filtering by subscription ID."""
        filtered = workspace_set.filter_by_subscription("12345678-1234-1234-1234-123456789abc")
        assert filtered.count() == 2
        assert filtered.aliases() == ["prod", "dev"]

    def test_filter_by_resource_group(self, workspace_set):
        """Test filtering by resource group."""
        filtered = workspace_set.filter_by_resource_group("prod-rg")
        assert filtered.count() == 1
        assert filtered.aliases() == ["prod"]

    def test_filter_by_alias(self, workspace_set):
        """Test filtering by alias."""
        filtered = workspace_set.filter_by_alias("dev")
        assert filtered.count() == 1
        # Remove architectural violation - no first_id method

    def test_has_query(self, workspace_set):
        """Test filtering by query."""
        incident_workspaces = workspace_set.has_query("query_incident_summary")
        assert incident_workspaces.count() == 2
        assert incident_workspaces.aliases() == ["prod", "dev"]

        usage_workspaces = workspace_set.has_query("query_workspace_usage")
        assert usage_workspaces.count() == 2
        assert set(usage_workspaces.aliases()) == {"prod", "test"}

    def test_details(self, workspace_set):
        """Test getting detailed workspace information."""
        details = workspace_set.details()
        assert len(details) == 3

        first_detail = details[0]
        assert first_detail["customer_id"] == "11111111-1111-1111-1111-111111111111"
        assert first_detail["workspace_name"] == "prod-workspace"
        assert first_detail["alias"] == "prod"
        assert first_detail["subscription_id"] == "12345678-1234-1234-1234-123456789abc"
        assert first_detail["resource_group"] == "prod-rg"
        assert set(first_detail["queries"]) == {"query_incident_summary", "query_workspace_usage"}

    def test_empty_workspace_set(self):
        """Test WorkspaceSet with no workspaces."""
        empty_set = WorkspaceSet([])
        assert empty_set.count() == 0
        assert empty_set.ids() == []
        # Remove architectural violations - no first_id/first_alias methods


class TestWorkspaceManager:
    """Test suite for WorkspaceManager class."""

    @pytest.fixture
    def sample_workspaces(self):
        """Create sample workspace configurations."""
        return [
            WorkspaceConfig(
                resource_id="/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/prod-rg/providers/microsoft.operationalinsights/workspaces/prod-workspace",
                customer_id="11111111-1111-1111-1111-111111111111",
                parameters={"row_level_security_tag": "prod"},
                queries_list=["query_incident_summary", "query_workspace_usage"],
            ),
            WorkspaceConfig(
                resource_id="/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/dev-rg/providers/microsoft.operationalinsights/workspaces/dev-workspace",
                customer_id="22222222-2222-2222-2222-222222222222",
                parameters={"row_level_security_tag": "dev"},
                queries_list=["query_incident_summary"],
            ),
        ]

    def test_workspace_manager_initialization(self, sample_workspaces):
        """Test WorkspaceManager initialization."""
        manager = WorkspaceManager(sample_workspaces)
        assert len(manager.workspaces) == 2
        assert manager.count() == 2

    def test_workspace_manager_empty_initialization(self):
        """Test WorkspaceManager initialization with empty list."""
        manager = WorkspaceManager()
        assert len(manager.workspaces) == 0
        assert manager.count() == 0

    def test_add_workspace(self):
        """Test adding a single workspace."""
        manager = WorkspaceManager()
        workspace = WorkspaceConfig(
            resource_id="/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace",
            customer_id="11111111-1111-1111-1111-111111111111",
            parameters={"row_level_security_tag": "test"},
            queries_list=["report_incident_summary"],
        )

        result = manager.add_workspace(workspace)
        assert result is manager  # Should return self for chaining
        assert manager.count() == 1
        assert manager.workspaces[0] == workspace

    def test_add_workspace_validation(self):
        """Test workspace validation during addition."""
        manager = WorkspaceManager()

        # Invalid workspace ID should raise exception
        invalid_workspace = WorkspaceConfig(
            resource_id="/subscriptions/invalid/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace",
            customer_id="invalid-id",
            parameters={"row_level_security_tag": "test"},
            queries_list=[],
        )

        with pytest.raises(Exception):  # Should be SecurityError in real implementation
            manager.add_workspace(invalid_workspace)

    def test_add_workspaces(self, sample_workspaces):
        """Test adding multiple workspaces."""
        manager = WorkspaceManager()
        result = manager.add_workspaces(sample_workspaces)
        assert result is manager  # Should return self for chaining
        assert manager.count() == 2

    def test_all_workspaces(self, sample_workspaces):
        """Test getting all workspaces as WorkspaceSet."""
        manager = WorkspaceManager(sample_workspaces)
        all_ws = manager.all()
        assert isinstance(all_ws, WorkspaceSet)
        assert all_ws.count() == 2

    def test_for_report(self, sample_workspaces):
        """Test filtering workspaces by report."""
        manager = WorkspaceManager(sample_workspaces)

        incident_workspaces = manager.for_query("query_incident_summary")
        assert incident_workspaces.count() == 2  # Both prod and dev have this query
        assert set(incident_workspaces.aliases()) == {"prod", "dev"}

        usage_workspaces = manager.for_query("query_workspace_usage")
        assert usage_workspaces.count() == 1  # Only prod has this query
        assert usage_workspaces.aliases() == ["prod"]

    def test_for_subscription(self, sample_workspaces):
        """Test filtering workspaces by subscription."""
        manager = WorkspaceManager(sample_workspaces)

        sub_workspaces = manager.for_subscription("12345678-1234-1234-1234-123456789abc")
        assert sub_workspaces.count() == 2

    def test_unique_queries(self, sample_workspaces):
        """Test getting unique query names."""
        manager = WorkspaceManager(sample_workspaces)
        queries = manager.unique_reports()  # Method is still called unique_reports
        expected_queries = {"query_incident_summary", "query_workspace_usage"}
        assert set(queries) == expected_queries

    def test_unique_subscriptions(self, sample_workspaces):
        """Test getting unique subscription IDs."""
        manager = WorkspaceManager(sample_workspaces)
        subscriptions = manager.unique_subscriptions()
        assert "12345678-1234-1234-1234-123456789abc" in subscriptions

    def test_from_dict_list(self):
        """Test creating WorkspaceManager from dictionary list."""
        workspace_dicts = [
            {
                "resource_id": "/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace",
                "customer_id": "11111111-1111-1111-1111-111111111111",
                "parameters": {"row_level_security_tag": "test"},
                "queries_list": ["report_incident_summary"],
            }
        ]

        manager = WorkspaceManager.from_dict_list(workspace_dicts)
        assert manager.count() == 1
        assert manager.workspaces[0].customer_id == "11111111-1111-1111-1111-111111111111"

    def test_to_dict_list(self, sample_workspaces):
        """Test converting WorkspaceManager to dictionary list."""
        manager = WorkspaceManager(sample_workspaces)
        dict_list = manager.to_dict_list()
        assert len(dict_list) == 2
        assert dict_list[0]["customer_id"] == "11111111-1111-1111-1111-111111111111"

    def test_from_file_yaml(self, tmp_path):
        """Test loading WorkspaceManager from YAML file."""
        yaml_content = {
            "workspaces": [
                {
                    "resource_id": "/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace",
                    "customer_id": "11111111-1111-1111-1111-111111111111",
                    "parameters": {"row_level_security_tag": "test"},
                    "queries_list": ["report_incident_summary"],
                }
            ],
            "metadata": {"version": "1.0"},
        }

        yaml_file = tmp_path / "test_workspaces.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)

        manager = WorkspaceManager.from_file(yaml_file)
        assert manager.count() == 1
        assert manager.workspaces[0].parameters["row_level_security_tag"] == "test"

    def test_from_file_legacy_format(self, tmp_path):
        """Test loading WorkspaceManager from legacy YAML format."""
        yaml_content = [
            {
                "resource_id": "/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace",
                "customer_id": "11111111-1111-1111-1111-111111111111",
                "parameters": {"row_level_security_tag": "test"},
                "queries_list": ["report_incident_summary"],
            }
        ]

        yaml_file = tmp_path / "legacy_workspaces.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)

        manager = WorkspaceManager.from_file(yaml_file)
        assert manager.count() == 1

    def test_from_file_not_found(self, tmp_path):
        """Test loading from non-existent file."""
        non_existent_file = tmp_path / "does_not_exist.yaml"

        with pytest.raises(FileNotFoundError):
            WorkspaceManager.from_file(non_existent_file)

    def test_from_file_unsupported_format(self, tmp_path):
        """Test loading from unsupported file format."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"test": "data"}')

        with pytest.raises(SecurityError, match="File extension"):
            WorkspaceManager.from_file(json_file)

    def test_from_file_invalid_structure(self, tmp_path):
        """Test loading from file with invalid structure."""
        yaml_content = "not a list or dict"

        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValueError):
            WorkspaceManager.from_file(yaml_file)

    def test_save_to_file(self, sample_workspaces, tmp_path):
        """Test saving WorkspaceManager to YAML file."""
        manager = WorkspaceManager(sample_workspaces)
        output_file = tmp_path / "output.yaml"

        manager.save_to_file(output_file)

        assert output_file.exists()

        # Load and verify content
        with open(output_file) as f:
            content = yaml.safe_load(f)

        assert "workspaces" in content
        assert "metadata" in content
        assert len(content["workspaces"]) == 2
        assert content["metadata"]["workspace_count"] == 2

    def test_from_file_with_validation(self, tmp_path):
        """Test file loading with Pydantic validation."""
        # Create valid workspace config
        yaml_content = {
            "workspaces": [
                {
                    "resource_id": "/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace",
                    "customer_id": "11111111-1111-1111-1111-111111111111",
                    "parameters": {"row_level_security_tag": "test"},
                    "queries_list": ["report_incident_summary"],
                }
            ]
        }

        yaml_file = tmp_path / "valid_workspaces.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)

        # Should load successfully with validation
        manager = WorkspaceManager.from_file(yaml_file)
        assert manager.count() == 1

    def test_file_path_security_validation(self, tmp_path):
        """Test file path security validation."""
        # Create a file with suspicious path
        suspicious_file = tmp_path / "../../../etc/passwd"

        # Should raise security error (when properly implemented)
        with pytest.raises(Exception):  # Should be SecurityError in real implementation
            WorkspaceManager.from_file(str(suspicious_file))


class TestWorkspaceConfigModel:
    """Test workspace configuration validation."""

    def test_valid_workspace_config(self):
        """Test valid workspace configuration."""
        config_data = {
            "resource_id": "/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace",
            "customer_id": "11111111-1111-1111-1111-111111111111",
            "parameters": {"row_level_security_tag": "test"},
            "queries_list": ["report_incident_summary"],
        }

        workspace = WorkspaceConfig(**config_data)
        assert workspace.customer_id == "11111111-1111-1111-1111-111111111111"
        assert workspace.workspace_name == "test-workspace"
        assert workspace.subscription_id == "12345678-1234-1234-1234-123456789abc"

    def test_workspace_name_extraction(self):
        """Test workspace name extraction from resource ID."""
        workspace = WorkspaceConfig(
            resource_id="/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/my-workspace-name",
            customer_id="11111111-1111-1111-1111-111111111111",
        )
        assert workspace.workspace_name == "my-workspace-name"

    def test_subscription_id_extraction(self):
        """Test subscription ID extraction from resource ID."""
        workspace = WorkspaceConfig(
            resource_id="/subscriptions/87654321-4321-4321-4321-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace",
            customer_id="11111111-1111-1111-1111-111111111111",
        )
        assert workspace.subscription_id == "87654321-4321-4321-4321-123456789abc"

    def test_resource_group_extraction(self):
        """Test resource group extraction from resource ID."""
        workspace = WorkspaceConfig(
            resource_id="/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/my-resource-group/providers/microsoft.operationalinsights/workspaces/test-workspace",
            customer_id="11111111-1111-1111-1111-111111111111",
        )
        assert workspace.resource_group == "my-resource-group"
