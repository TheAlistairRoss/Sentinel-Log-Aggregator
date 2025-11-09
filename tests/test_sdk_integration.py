"""
Integration tests for Sentinel Log Aggregator Python SDK.

Tests the main SDK classes as they would be used programmatically,
not through the CLI interface. Validates the public API and common usage patterns.
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest
from azure.core.credentials import AccessToken
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryResult

from sentinel_log_aggregator import (
    BatchExecutionResult,
    QueryResult,
    QueryStatus,
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    SentinelQueryEngine,
    UploadResult,
    WorkspaceConfig,
    WorkspaceManager,
    WorkspaceQueryExecution,
    load_workspace_config,
)
from sentinel_log_aggregator.exceptions import (
    ConfigurationError,
    QueryExecutionError,
)
from sentinel_log_aggregator.models import QueryExecution
from sentinel_log_aggregator.query_registry import QueryRegistry

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "data"


class TestSentinelAggregatorClientOptions:
    """Test the SentinelAggregatorClientOptions configuration class."""

    def test_from_environment_variables(self, monkeypatch):
        """Test creating configuration from environment variables."""
        # Set environment variables
        monkeypatch.setenv("DCR_ENDPOINT", "https://test-dcr.azure.com")
        monkeypatch.setenv("DCR_IMMUTABLE_ID", "dcr-test123")
        monkeypatch.setenv("LOOKBACK_PERIOD", "P7D")
        monkeypatch.setenv("BATCH_TIME_SIZE", "PT12H")
        monkeypatch.setenv("MAX_CONCURRENT_QUERIES", "10")
        monkeypatch.setenv("QUERY_TIMEOUT_SECONDS", "300")
        monkeypatch.setenv("MAX_RETRIES", "5")
        monkeypatch.setenv("RETRY_DELAY_SECONDS", "10")

        # Create config from environment
        config = SentinelAggregatorClientOptions.from_environment()

        # Validate
        assert config.dcr_endpoint == "https://test-dcr.azure.com"
        assert config.dcr_immutable_id == "dcr-test123"
        assert config.lookback_period == "P7D"
        assert config.batch_time_size == "PT12H"
        assert config.max_concurrent_queries == 10
        assert config.query_timeout_seconds == 300
        assert config.max_retries == 5
        assert config.retry_delay_seconds == 10

    def test_validation_success(self):
        """Test configuration validation with valid values."""
        config = SentinelAggregatorClientOptions(
            dcr_endpoint="https://test-dcr.azure.com",
            dcr_immutable_id="dcr-test123",
            lookback_period="P1D",
            batch_time_size="PT24H",
        )

        # Should not raise
        config.validate()

    def test_validation_invalid_lookback_period(self):
        """Test validation fails with invalid lookback period."""
        config = SentinelAggregatorClientOptions(
            dcr_endpoint="https://test-dcr.azure.com",
            dcr_immutable_id="dcr-test123",
            lookback_period="invalid",
        )

        with pytest.raises(ConfigurationError, match="Invalid lookback_period"):
            config.validate()

    def test_validation_conflicting_time_specs(self):
        """Test validation fails with conflicting time specifications."""
        config = SentinelAggregatorClientOptions(
            dcr_endpoint="https://test-dcr.azure.com",
            dcr_immutable_id="dcr-test123",
            lookback_period="P1D",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(days=1),
        )

        with pytest.raises(ConfigurationError, match="Conflicting time specifications"):
            config.validate()


class TestWorkspaceConfig:
    """Test the WorkspaceConfig data class."""

    def test_workspace_config_creation(self):
        """Test creating a workspace configuration."""
        config = WorkspaceConfig(
            resource_id="/subscriptions/sub123/resourcegroups/rg/providers/microsoft.operationalinsights/workspaces/ws1",
            customer_id="workspace-id-123",
            aggregation_workspace=True,
            parameters={"row_level_security_tag": "TAG1"},
            queries_list=["query_incident_summary", "query_workspace_usage"],
        )

        assert config.resource_id.endswith("ws1")
        assert config.customer_id == "workspace-id-123"
        assert config.aggregation_workspace is True
        assert config.parameters["row_level_security_tag"] == "TAG1"
        assert len(config.queries_list) == 2

    def test_workspace_alias_extraction(self):
        """Test extracting workspace alias from resource ID."""
        config = WorkspaceConfig(
            resource_id="/subscriptions/sub123/resourcegroups/rg/providers/microsoft.operationalinsights/workspaces/my-workspace",
            customer_id="workspace-id-123",
        )

        # The alias should be the workspace name from the resource ID
        assert "my-workspace" in config.resource_id


class TestWorkspaceManager:
    """Test the WorkspaceManager class for filtering and managing workspaces."""

    @pytest.fixture
    def sample_workspaces(self) -> List[WorkspaceConfig]:
        """Create sample workspace configurations."""
        return [
            WorkspaceConfig(
                resource_id="/subscriptions/sub1/resourcegroups/rg1/providers/microsoft.operationalinsights/workspaces/ws1",
                customer_id="ws1-customer-id",
                aggregation_workspace=True,
                queries_list=["query_incident_summary", "query_workspace_usage"],
                parameters={"row_level_security_tag": "WS1"},
            ),
            WorkspaceConfig(
                resource_id="/subscriptions/sub1/resourcegroups/rg1/providers/microsoft.operationalinsights/workspaces/ws2",
                customer_id="ws2-customer-id",
                aggregation_workspace=False,
                queries_list=["query_incident_summary"],
                parameters={"row_level_security_tag": "WS2"},
            ),
            WorkspaceConfig(
                resource_id="/subscriptions/sub1/resourcegroups/rg1/providers/microsoft.operationalinsights/workspaces/ws3",
                customer_id="ws3-customer-id",
                aggregation_workspace=True,
                queries_list=["query_workspace_usage"],
                parameters={"row_level_security_tag": "WS3"},
            ),
        ]

    def test_workspace_manager_creation(self, sample_workspaces):
        """Test creating a workspace manager."""
        manager = WorkspaceManager(sample_workspaces)
        assert len(manager.workspaces) == 3

    def test_filter_by_workspace_ids(self, sample_workspaces):
        """Test filtering workspaces by customer IDs."""
        manager = WorkspaceManager(sample_workspaces)
        filtered = manager.with_workspace_ids(["ws1-customer-id", "ws2-customer-id"])

        assert len(filtered.workspaces) == 2
        assert filtered.workspaces[0].customer_id == "ws1-customer-id"
        assert filtered.workspaces[1].customer_id == "ws2-customer-id"

    def test_filter_aggregation_workspaces_only(self, sample_workspaces):
        """Test filtering for aggregation workspaces only."""
        manager = WorkspaceManager(sample_workspaces)
        filtered = manager.aggregation_only()

        assert len(filtered.workspaces) == 2
        assert all(ws.aggregation_workspace for ws in filtered.workspaces)

    def test_filter_by_query(self, sample_workspaces):
        """Test filtering workspaces that have a specific query."""
        manager = WorkspaceManager(sample_workspaces)
        filtered = manager.with_query("query_incident_summary")

        assert len(filtered.workspaces) == 2
        assert all("query_incident_summary" in ws.queries_list for ws in filtered.workspaces)

    def test_chaining_filters(self, sample_workspaces):
        """Test chaining multiple filters together."""
        manager = WorkspaceManager(sample_workspaces)
        filtered = manager.aggregation_only().with_query("query_workspace_usage")

        assert len(filtered.workspaces) == 1
        assert filtered.workspaces[0].customer_id == "ws3-customer-id"


class TestQueryRegistry:
    """Test the QueryRegistry for managing available queries."""

    def test_list_all_queries(self):
        """Test listing all registered queries."""
        registry = QueryRegistry()
        queries = registry.list_queries()

        # Should have standard queries
        assert len(queries) > 0
        query_names = [q["name"] for q in queries]
        assert "query_incident_summary" in query_names

    def test_get_query_by_name(self):
        """Test retrieving a specific query by name."""
        registry = QueryRegistry()
        query_def = registry.get_query("query_incident_summary")

        assert query_def is not None
        assert query_def.name == "query_incident_summary"
        assert query_def.destination_stream is not None
        assert len(query_def.get_query()) > 0

    def test_get_nonexistent_query(self):
        """Test that getting a non-existent query raises appropriate error."""
        registry = QueryRegistry()

        with pytest.raises(ValueError, match="not found"):
            registry.get_query("nonexistent_query")

    def test_query_has_parameters(self):
        """Test that queries have expected parameters."""
        registry = QueryRegistry()
        query_def = registry.get_query("query_incident_summary")

        # Should have row_level_security_tag parameter
        assert "row_level_security_tag" in [p.name for p in query_def.parameters]


class TestSentinelAggregatorClient:
    """Test the SentinelAggregatorClient class for Azure integration."""

    @pytest.fixture
    def mock_config(self) -> SentinelAggregatorClientOptions:
        """Create a mock configuration."""
        return SentinelAggregatorClientOptions(
            dcr_endpoint="https://test-dcr.azure.com",
            dcr_immutable_id="dcr-test123",
            lookback_period="P1D",
            max_retries=2,
            retry_delay_seconds=1,
        )

    @pytest.fixture
    def mock_credential(self):
        """Create a mock Azure credential."""
        mock_cred = Mock(spec=DefaultAzureCredential)
        mock_cred.get_token = Mock(return_value=AccessToken("fake_token", 9999999999))
        return mock_cred

    @pytest.mark.asyncio
    async def test_client_initialization(self, mock_config, mock_credential):
        """Test initializing the Sentinel client."""
        async with SentinelAggregatorClient(mock_config, mock_credential) as client:
            assert client is not None
            assert client.config == mock_config

    @pytest.mark.asyncio
    async def test_query_workspace_success(self, mock_config, mock_credential):
        """Test querying a workspace successfully."""
        # Mock the Azure query response
        mock_response = Mock(spec=LogsQueryResult)
        mock_response.status = "Success"
        mock_response.tables = [
            Mock(
                rows=[
                    ["value1", "value2"],
                    ["value3", "value4"],
                ],
                columns=[
                    Mock(name="column1", type="string"),
                    Mock(name="column2", type="string"),
                ],
            )
        ]

        with patch("sentinel_log_aggregator.sentinel_client.LogsQueryClient") as mock_logs_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.query_workspace.return_value = mock_response
            mock_logs_client.return_value.__aenter__.return_value = mock_client_instance

            async with SentinelAggregatorClient(mock_config, mock_credential) as client:
                result = await client.query_workspace(
                    workspace_id="test-workspace-id",
                    query="TestQuery | take 10",
                    timespan=timedelta(days=1),
                )

                assert result is not None
                assert result.status == QueryStatus.SUCCESS
                assert len(result.records) == 2

    @pytest.mark.asyncio
    async def test_query_workspace_with_retry(self, mock_config, mock_credential):
        """Test query retry logic on transient failures."""
        mock_response = Mock(spec=LogsQueryResult)
        mock_response.status = "Success"
        mock_response.tables = [Mock(rows=[], columns=[])]

        with patch("sentinel_log_aggregator.sentinel_client.LogsQueryClient") as mock_logs_client:
            mock_client_instance = AsyncMock()
            # Fail once, then succeed
            mock_client_instance.query_workspace.side_effect = [
                Exception("Transient error"),
                mock_response,
            ]
            mock_logs_client.return_value.__aenter__.return_value = mock_client_instance

            async with SentinelAggregatorClient(mock_config, mock_credential) as client:
                result = await client.query_workspace(
                    workspace_id="test-workspace-id",
                    query="TestQuery",
                    timespan=timedelta(days=1),
                )

                assert result is not None
                assert mock_client_instance.query_workspace.call_count == 2


class TestQueryResult:
    """Test the QueryResult data class."""

    def test_query_result_creation(self):
        """Test creating a query result."""
        result = QueryResult(
            status=QueryStatus.SUCCESS,
            records=[
                {"column1": "value1", "column2": "value2"},
                {"column1": "value3", "column2": "value4"},
            ],
            record_count=2,
            execution_time_seconds=1.5,
        )

        assert result.status == QueryStatus.SUCCESS
        assert result.record_count == 2
        assert len(result.records) == 2
        assert result.execution_time_seconds == 1.5

    def test_query_result_empty(self):
        """Test creating an empty query result."""
        result = QueryResult(
            status=QueryStatus.SUCCESS,
            records=[],
            record_count=0,
            execution_time_seconds=0.5,
        )

        assert result.record_count == 0
        assert len(result.records) == 0


class TestQueryExecution:
    """Test the QueryExecution tracking class."""

    def test_query_execution_creation(self):
        """Test creating a query execution record."""
        execution = QueryExecution(
            workspace_id="ws-123",
            workspace_alias="test-workspace",
            query_name="query_incident_summary",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            status="success",
            records_downloaded=100,
            records_uploaded=100,
            execution_time=2.5,
            upload_time=0.5,
            job_correlation_id="job-123",
        )

        assert execution.workspace_id == "ws-123"
        assert execution.query_name == "query_incident_summary"
        assert execution.records_downloaded == 100
        assert execution.records_uploaded == 100
        assert execution.execution_time == 2.5

    def test_query_execution_failed(self):
        """Test creating a failed query execution record."""
        execution = QueryExecution(
            workspace_id="ws-123",
            workspace_alias="test-workspace",
            query_name="query_incident_summary",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            status="failed",
            error_message="Query timeout",
            records_downloaded=0,
            records_uploaded=0,
            execution_time=30.0,
            job_correlation_id="job-123",
        )

        assert execution.status == "failed"
        assert execution.error_message == "Query timeout"
        assert execution.records_downloaded == 0


class TestBatchExecutionResult:
    """Test the BatchExecutionResult results class."""

    def test_batch_execution_result_creation(self):
        """Test creating a batch execution result."""
        executions = [
            WorkspaceQueryExecution(
                workspace_id="ws-1",
                workspace_alias="workspace1",
                query_name="query1",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc) + timedelta(seconds=1),
                query_status=QueryStatus.SUCCESS,
                records_downloaded=50,
                records_uploaded=50,
                execution_time_seconds=1.0,
            ),
            WorkspaceQueryExecution(
                workspace_id="ws-2",
                workspace_alias="workspace2",
                query_name="query2",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc) + timedelta(seconds=2),
                query_status=QueryStatus.SUCCESS,
                records_downloaded=75,
                records_uploaded=75,
                execution_time_seconds=2.0,
            ),
        ]

        result = BatchExecutionResult(
            batch_id="batch-1",
            status=QueryStatus.SUCCESS,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(seconds=5),
            total_execution_time_seconds=5.0,
            workspace_executions=executions,
            total_records_downloaded=125,
            total_records_uploaded=125,
            successful_operations=2,
            failed_operations=0,
        )

        assert result.total_records_downloaded == 125
        assert result.total_records_uploaded == 125
        assert result.successful_operations == 2
        assert result.failed_operations == 0
        assert len(result.workspace_executions) == 2

    def test_batch_execution_with_failures(self):
        """Test batch execution result with some failures."""
        executions = [
            WorkspaceQueryExecution(
                workspace_id="ws-1",
                workspace_alias="workspace1",
                query_name="query1",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc) + timedelta(seconds=1),
                query_status=QueryStatus.SUCCESS,
                records_downloaded=50,
                records_uploaded=50,
                execution_time_seconds=1.0,
            ),
            WorkspaceQueryExecution(
                workspace_id="ws-2",
                workspace_alias="workspace2",
                query_name="query2",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc) + timedelta(seconds=2),
                query_status=QueryStatus.FAILED,
                error_message="Query failed",
                records_downloaded=0,
                records_uploaded=0,
                execution_time_seconds=2.0,
            ),
        ]

        result = BatchExecutionResult(
            batch_id="batch-1",
            status=QueryStatus.FAILED,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(seconds=5),
            total_execution_time_seconds=5.0,
            workspace_executions=executions,
            total_records_downloaded=50,
            total_records_uploaded=50,
            successful_operations=1,
            failed_operations=1,
        )

        assert result.successful_operations == 1
        assert result.failed_operations == 1
        assert result.total_records_downloaded == 50
        assert result.total_records_uploaded == 50


class TestSentinelQueryEngineConfiguration:
    """Test SentinelQueryEngine configuration and setup."""

    @pytest.fixture
    def mock_config(self) -> SentinelAggregatorClientOptions:
        """Create a mock configuration."""
        return SentinelAggregatorClientOptions(
            dcr_endpoint="https://test-dcr.azure.com",
            dcr_immutable_id="dcr-test123",
            lookback_period="P1D",
            batch_time_size="PT24H",
            max_concurrent_queries=5,
        )

    @pytest.fixture
    def mock_client(self):
        """Create a mock Sentinel client."""
        return AsyncMock(spec=SentinelAggregatorClient)

    def test_query_engine_initialization(self, mock_config, mock_client):
        """Test initializing the query engine."""
        engine = SentinelQueryEngine(mock_config, mock_client)

        assert engine.config == mock_config
        assert engine.client == mock_client

    def test_query_engine_with_dry_run(self, mock_client):
        """Test query engine in dry-run mode."""
        config = SentinelAggregatorClientOptions(
            dcr_endpoint="https://test-dcr.azure.com",
            dcr_immutable_id="dcr-test123",
            lookback_period="P1D",
            dry_run=True,
        )

        engine = SentinelQueryEngine(config, mock_client)

        assert engine.config.dry_run is True


class TestEndToEndSDKUsage:
    """Test end-to-end SDK usage patterns."""

    @pytest.mark.asyncio
    async def test_complete_workflow_dry_run(self, tmp_path):
        """Test a complete workflow in dry-run mode."""
        # Create test workspace config
        workspace_config_content = """
workspaces:
  - resource_id: /subscriptions/test/resourcegroups/rg/providers/microsoft.operationalinsights/workspaces/testws
    customer_id: test-workspace-id
    aggregation_workspace: true
    parameters:
      row_level_security_tag: TEST
    queries_list:
      - query_incident_summary
"""
        workspace_file = tmp_path / "workspaces.yaml"
        workspace_file.write_text(workspace_config_content)

        # Create client options
        config = SentinelAggregatorClientOptions(
            dcr_endpoint="https://test-dcr.azure.com",
            dcr_immutable_id="dcr-test123",
            lookback_period="P1D",
            dry_run=True,
        )

        # Validate configuration
        config.validate()

        # Load workspace config
        workspaces = load_workspace_config(workspace_file)
        assert len(workspaces) == 1

        # Create workspace manager
        manager = WorkspaceManager(workspaces)
        assert len(manager.workspaces) == 1

        # Filter for aggregation workspaces
        agg_workspaces = manager.aggregation_only()
        assert len(agg_workspaces.workspaces) == 1

    def test_query_registry_usage(self):
        """Test using the query registry."""
        # Get registry
        registry = QueryRegistry()

        # List all queries
        all_queries = registry.list_queries()
        assert len(all_queries) > 0

        # Get specific query
        query_def = registry.get_query("query_incident_summary")
        assert query_def is not None

        # Build query with parameters
        kql = query_def.build_query(
            start_time=datetime.now(timezone.utc) - timedelta(days=1),
            end_time=datetime.now(timezone.utc),
            row_level_security_tag="TEST",
        )
        assert len(kql) > 0
        assert "TEST" in kql

    def test_workspace_filtering_patterns(self):
        """Test common workspace filtering patterns."""
        workspaces = [
            WorkspaceConfig(
                resource_id=f"/subscriptions/sub/resourcegroups/rg/providers/microsoft.operationalinsights/workspaces/ws{i}",
                customer_id=f"ws{i}-id",
                aggregation_workspace=(i % 2 == 0),
                queries_list=["query_incident_summary"] if i < 3 else ["query_workspace_usage"],
            )
            for i in range(5)
        ]

        manager = WorkspaceManager(workspaces)

        # Filter by aggregation
        agg = manager.aggregation_only()
        assert len(agg.workspaces) == 3

        # Filter by query
        incident = manager.with_query("query_incident_summary")
        assert len(incident.workspaces) == 3

        # Chain filters
        filtered = manager.aggregation_only().with_query("query_incident_summary")
        assert len(filtered.workspaces) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
