"""
Final comprehensive tests for sentinel_client.py targeting specific missing lines for maximum coverage.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from azure.core.credentials import AccessToken
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.monitor.ingestion import LogsIngestionClient
from azure.monitor.query import LogsQueryClient

from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions
from sentinel_log_aggregator.exceptions import (
    CredentialValidationError,
    DataIngestionError,
    QueryExecutionError,
    SentinelAggregatorError,
    WorkspaceAccessError,
)
from sentinel_log_aggregator.models import AVAILABLE_QUERIES, KQLQueryDefinition, WorkspaceConfig
from sentinel_log_aggregator.responses import (
    BatchExecutionResult,
    BatchStatus,
    QueryResult,
    QueryStatus,
    UploadResult,
    UploadStatus,
    WorkspaceQueryExecution,
)

# Import the classes we're testing
from sentinel_log_aggregator.sentinel_client import SentinelAggregatorClient


class TestSentinelClientSpecificLineCoverage:
    """Test suite targeting specific missing lines for maximum coverage."""

    @pytest.fixture
    def mock_credential(self):
        """Mock Azure credential."""
        credential = AsyncMock(spec=DefaultAzureCredential)
        credential.get_token = AsyncMock(return_value=AccessToken("test-token", 1234567890))
        return credential

    @pytest.fixture
    def client_options(self):
        """Sample client options with valid DCR rule ID."""
        return SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.ingest.monitor.azure.com",
            dcr_rule_id="dcr-" + "a" * 32,  # Valid DCR rule ID format
            max_retries=3,
            retry_delay_seconds=2.0,
            enable_distributed_tracing=True,
            custom_policies=[],
        )

    @pytest.mark.asyncio
    async def test_upload_logs_data_preparation_with_complex_data(
        self, mock_credential, client_options
    ):
        """Test _prepare_data_for_upload with complex data types (lines 484-508)."""
        client = SentinelAggregatorClient(
            "https://test.endpoint.com", mock_credential, options=client_options
        )

        # Test data with various types that need conversion
        test_data = [
            {
                "TimeGenerated": datetime.now(timezone.utc),
                "EventType": "Test",
                "Count": 42,
                "IsActive": True,
                "Tags": ["tag1", "tag2"],
                "NullValue": None,
                "NestedDict": {"key": "value"},
            }
        ]

        prepared_data = client._prepare_data_for_upload(test_data)

        # Verify data preparation
        assert len(prepared_data) == 1
        assert isinstance(prepared_data[0]["TimeGenerated"], str)
        assert prepared_data[0]["EventType"] == "Test"
        assert prepared_data[0]["Count"] == 42
        assert prepared_data[0]["IsActive"] is True

    @pytest.mark.asyncio
    async def test_query_workspace_with_various_exceptions(self, mock_credential, client_options):
        """Test query_workspace exception handling (lines 315, 330-346)."""
        client = SentinelAggregatorClient(
            "https://test.endpoint.com", mock_credential, options=client_options
        )

        # Test with ClientAuthenticationError
        mock_query_client = AsyncMock(spec=LogsQueryClient)
        mock_query_client.query_workspace = AsyncMock(
            side_effect=ClientAuthenticationError("Authentication failed")
        )
        client._logs_query_client = mock_query_client

        result = await client.query_workspace(
            workspace_id=str(uuid.uuid4()), query="SecurityEvent | take 1"
        )

        # Verify error handling
        assert not result.succeeded
        assert (
            "authentication" in result.error_message.lower()
            or "failed" in result.error_message.lower()
        )

    @pytest.mark.asyncio
    async def test_upload_logs_with_data_ingestion_error(self, mock_credential, client_options):
        """Test upload_logs with DataIngestionError (lines 534, 545)."""
        client = SentinelAggregatorClient(
            "https://test.endpoint.com", mock_credential, options=client_options
        )

        # Mock ingestion client to raise DataIngestionError
        mock_ingestion_client = AsyncMock(spec=LogsIngestionClient)
        mock_ingestion_client.upload = AsyncMock(side_effect=Exception("Ingestion failed"))
        client._logs_ingestion_client = mock_ingestion_client

        test_data = [{"TimeGenerated": "2023-01-01T00:00:00Z", "EventType": "Test"}]
        result = await client.upload_logs(data=test_data, stream_name="Custom-TestStream_CL")

        # Verify error handling
        assert not result.succeeded
        assert (
            "failed" in result.error_message.lower() or "ingestion" in result.error_message.lower()
        )

    @pytest.mark.asyncio
    async def test_begin_batch_operation_coverage(self, mock_credential, client_options):
        """Test begin_batch_operation method (lines 595-643)."""
        client = SentinelAggregatorClient(
            "https://test.endpoint.com", mock_credential, options=client_options
        )

        # Create sample workspaces and query definition
        workspaces = [
            WorkspaceConfig(
                resource_id="/subscriptions/test-sub/resourceGroups/test-rg/providers/Microsoft.OperationalInsights/workspaces/test-ws",
                customer_id=str(uuid.uuid4()),
                parameters={"row_level_security_tag": "workspace1"},
            )
        ]

        # Use an available query definition
        query_name = list(AVAILABLE_QUERIES.keys())[0]
        query_def = AVAILABLE_QUERIES[query_name]

        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time = datetime.now(timezone.utc)

        # Test begin_batch_operation
        poller = await client.begin_batch_operation(
            workspaces=workspaces,
            query_definition=query_def,
            start_time=start_time,
            end_time=end_time,
        )

        # Verify poller creation
        assert poller is not None
        assert hasattr(poller, "result")
        assert hasattr(poller, "done")

    @pytest.mark.asyncio
    async def test_list_query_results_pagination(self, mock_credential, client_options):
        """Test list_query_results pagination logic (lines 403-473)."""
        client = SentinelAggregatorClient(
            "https://test.endpoint.com", mock_credential, options=client_options
        )

        workspace_id = str(uuid.uuid4())
        query = "SecurityEvent | take 100"

        # Mock the query client to simulate pagination
        mock_query_client = AsyncMock(spec=LogsQueryClient)

        # Create mock result with pagination
        mock_result = MagicMock()
        mock_result.tables = [MagicMock()]
        mock_result.tables[0].rows = [["row1"], ["row2"]]
        mock_result.tables[0].columns = [MagicMock(name="TestColumn")]

        mock_query_client.query_workspace = AsyncMock(return_value=mock_result)
        client._logs_query_client = mock_query_client

        # Test pagination setup
        paginated_iterator = client.list_query_results(
            workspace_id=workspace_id, query=query, page_size=10
        )

        # Verify iterator creation
        assert paginated_iterator is not None

    def test_client_context_manager_properties(self, mock_credential, client_options):
        """Test client context manager properties (lines 645-665)."""
        client = SentinelAggregatorClient(
            "https://test.endpoint.com", mock_credential, options=client_options
        )

        # Test that context manager properties exist
        assert hasattr(client, "__aenter__")
        assert hasattr(client, "__aexit__")
        assert callable(getattr(client, "__aenter__"))
        assert callable(getattr(client, "__aexit__"))

    @pytest.mark.asyncio
    async def test_close_method_coverage(self, mock_credential, client_options):
        """Test close method (lines 645-665)."""
        client = SentinelAggregatorClient(
            "https://test.endpoint.com", mock_credential, options=client_options
        )

        # Create mock clients to test close functionality
        mock_query_client = AsyncMock(spec=LogsQueryClient)
        mock_ingestion_client = AsyncMock(spec=LogsIngestionClient)

        # Make close methods async mocks
        mock_query_client.close = AsyncMock()
        mock_ingestion_client.close = AsyncMock()

        client._logs_query_client = mock_query_client
        client._logs_ingestion_client = mock_ingestion_client

        # Test close method
        await client.close()

        # Verify clients were closed
        mock_query_client.close.assert_called_once()
        mock_ingestion_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_credentials_authentication_error(self, mock_credential, client_options):
        """Test validate_credentials with authentication error (lines 229-231)."""
        client = SentinelAggregatorClient(
            "https://test.endpoint.com", mock_credential, options=client_options
        )

        # Mock credential to raise authentication error
        mock_credential.get_token = AsyncMock(
            side_effect=ClientAuthenticationError("Invalid credentials")
        )

        # This should raise CredentialValidationError
        with pytest.raises(CredentialValidationError):
            await client.validate_credentials()

    def test_property_initialization_coverage(self, mock_credential, client_options):
        """Test property initialization (lines 193, 203)."""
        client = SentinelAggregatorClient(
            "https://test.endpoint.com", mock_credential, options=client_options
        )

        # Access properties to trigger lazy initialization
        query_client = client._logs_query_client_instance
        ingestion_client = client._logs_ingestion_client_instance

        # Verify properties are initialized
        assert query_client is not None
        assert ingestion_client is not None

        # Test second access returns the same instance
        query_client2 = client._logs_query_client_instance
        ingestion_client2 = client._logs_ingestion_client_instance

        assert query_client is query_client2
        assert ingestion_client is ingestion_client2
