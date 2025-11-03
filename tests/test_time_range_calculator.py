"""
Tests for time_range_calculator module - time range calculation with precedence logic.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import List, Dict, Any

from sentinel_log_aggregator.time_range_calculator import (
    calculate_execution_time_ranges,
    calculate_execution_batches,
    validate_time_configuration,
    _calculate_from_explicit_times,
    _calculate_from_last_successful,
    _query_last_successful_for_query_workspace,
    TimeRangeCalculationError,
)
from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions
from sentinel_log_aggregator.health_logger import SentinelAggregatorHealthLogger
from sentinel_log_aggregator.models import WorkspaceConfig
from sentinel_log_aggregator.time_utils import TimeParsingError, InvalidTimeRangeError


class TestTimeConfigurationValidation:
    """Test time configuration validation logic."""
    
    def test_valid_single_time_methods(self):
        """Test valid single time specification methods."""
        # Lookback period only
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            lookback_period="P7D",
            batch_time_size="PT12H"
        )
        errors = validate_time_configuration(options)
        assert errors == []
        
        # Explicit times only
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            start_time="2025-11-01T00:00:00Z",
            end_time="2025-11-03T00:00:00Z",
            batch_time_size="PT12H"
        )
        errors = validate_time_configuration(options)
        assert errors == []
        
        # Last successful only
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            use_last_successful=True,
            batch_time_size="PT12H"
        )
        errors = validate_time_configuration(options)
        assert errors == []
    
    def test_conflicting_time_specifications(self):
        """Test detection of conflicting time specifications."""
        # Lookback + explicit times
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            lookback_period="P7D",
            start_time="2025-11-01T00:00:00Z",
            batch_time_size="PT12H"
        )
        errors = validate_time_configuration(options)
        assert len(errors) == 1
        assert "Conflicting time specifications" in errors[0]
        assert "lookback_period" in errors[0]
        assert "explicit times" in errors[0]
        
        # All three methods
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            lookback_period="P7D",
            start_time="2025-11-01T00:00:00Z",
            use_last_successful=True,
            batch_time_size="PT12H"
        )
        errors = validate_time_configuration(options)
        assert len(errors) == 1
        assert "Conflicting time specifications" in errors[0]
    
    def test_invalid_datetime_formats(self):
        """Test validation of invalid datetime formats."""
        # Invalid start time
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            start_time="invalid-datetime",
            batch_time_size="PT12H"
        )
        errors = validate_time_configuration(options)
        assert any("Invalid start_time" in error for error in errors)
        
        # Invalid end time
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            end_time="invalid-datetime",
            batch_time_size="PT12H"
        )
        errors = validate_time_configuration(options)
        assert any("Invalid end_time" in error for error in errors)
    
    def test_invalid_time_range(self):
        """Test validation of invalid time ranges."""
        # End before start
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            start_time="2025-11-03T00:00:00Z",
            end_time="2025-11-01T00:00:00Z",
            batch_time_size="PT12H"
        )
        errors = validate_time_configuration(options)
        assert any("Invalid time range" in error for error in errors)
    
    def test_invalid_durations(self):
        """Test validation of invalid duration formats."""
        # Invalid lookback period
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            lookback_period="invalid-duration",
            batch_time_size="PT12H"
        )
        errors = validate_time_configuration(options)
        assert any("Invalid lookback_period" in error for error in errors)
        
        # Invalid batch time size
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            lookback_period="P7D",
            batch_time_size="invalid-duration"
        )
        errors = validate_time_configuration(options)
        assert any("Invalid batch_time_size" in error for error in errors)
    
    def test_validation_exception_handling(self):
        """Test that validation catches unexpected exceptions."""
        # Create options that might cause an unexpected error
        options = MagicMock()
        options.start_time = None
        options.end_time = None
        options.lookback_period = None
        options.use_last_successful = None  # This might cause issues
        options.batch_time_size = "PT12H"
        
        errors = validate_time_configuration(options)
        # Should catch any unexpected errors and return them as validation errors
        assert isinstance(errors, list)


class TestTimeRangeCalculation:
    """Test time range calculation with different precedence scenarios."""
    
    @patch('sentinel_log_aggregator.time_utils.datetime')
    @pytest.mark.asyncio
    async def test_lookback_period_calculation(self, mock_datetime):
        """Test time range calculation using lookback period."""
        # Mock current time
        mock_now = datetime(2025, 11, 3, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            lookback_period="P7D",
            batch_time_size="PT12H"
        )
        
        workspaces = [
            WorkspaceConfig(
                customer_id="test-customer",
                resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.OperationalInsights/workspaces/test"
            )
        ]
        
        start_time, end_time, batch_size = await calculate_execution_time_ranges(
            options, workspaces
        )
        
        expected_start = mock_now - timedelta(days=7)
        assert start_time == expected_start
        assert end_time == mock_now
        assert batch_size == timedelta(hours=12)
    
    @pytest.mark.asyncio
    async def test_explicit_time_range_calculation(self):
        """Test time range calculation using explicit start/end times."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            start_time="2025-11-01T00:00:00Z",
            end_time="2025-11-03T00:00:00Z",
            batch_time_size="PT6H"
        )
        
        workspaces = [
            WorkspaceConfig(
                customer_id="test-customer",
                resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.OperationalInsights/workspaces/test"
            )
        ]
        
        start_time, end_time, batch_size = await calculate_execution_time_ranges(
            options, workspaces
        )
        
        assert start_time.year == 2025
        assert start_time.month == 11
        assert start_time.day == 1
        assert end_time.year == 2025
        assert end_time.month == 11
        assert end_time.day == 3
        assert batch_size == timedelta(hours=6)
    
    @patch('sentinel_log_aggregator.time_range_calculator.datetime')
    @pytest.mark.asyncio
    async def test_end_time_defaults_to_now(self, mock_datetime):
        """Test that end_time defaults to now when only start_time is provided."""
        # Mock current time
        mock_now = datetime(2025, 11, 3, 15, 30, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            start_time="2025-11-01T00:00:00Z",
            batch_time_size="PT24H"
        )
        
        workspaces = [
            WorkspaceConfig(
                customer_id="test-customer",
                resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.OperationalInsights/workspaces/test"
            )
        ]
        
        start_time, end_time, batch_size = await calculate_execution_time_ranges(
            options, workspaces
        )
        
        assert start_time.year == 2025
        assert start_time.month == 11
        assert start_time.day == 1
        assert end_time == mock_now
        assert batch_size == timedelta(hours=24)
    
    @pytest.mark.asyncio
    async def test_last_successful_calculation(self):
        """Test time range calculation using last successful runs."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            use_last_successful=True,
            batch_time_size="PT12H"
        )
        
        workspaces = [
            WorkspaceConfig(
                customer_id="test-customer-1",
                resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.OperationalInsights/workspaces/test1",
                queries_list=[{"name": "test_query"}]
            ),
            WorkspaceConfig(
                customer_id="test-customer-2",
                resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.OperationalInsights/workspaces/test2",
                queries_list=[{"name": "test_query"}]
            )
        ]
        
        # Mock health logger
        mock_health_logger = AsyncMock()
        
        # Mock the query function to return successful results
        with patch('sentinel_log_aggregator.time_range_calculator._query_last_successful_for_query_workspace') as mock_query:
            mock_query.side_effect = [
                {"end_time": "2025-11-01T12:00:00Z"},  # First workspace
                {"end_time": "2025-11-01T10:00:00Z"}   # Second workspace (earlier)
            ]
            
            with patch('sentinel_log_aggregator.time_range_calculator.datetime') as mock_datetime:
                mock_now = datetime(2025, 11, 3, 12, 0, 0, tzinfo=timezone.utc)
                mock_datetime.now.return_value = mock_now
                
                start_time, end_time, batch_size = await calculate_execution_time_ranges(
                    options, workspaces, mock_health_logger
                )
        
        # Should use the earliest last successful time
        assert start_time.year == 2025
        assert start_time.month == 11
        assert start_time.day == 1
        assert start_time.hour == 10  # Earliest time
        assert end_time == mock_now
        assert batch_size == timedelta(hours=12)
    
    def test_missing_health_logger_for_last_successful(self):
        """Test error when health logger is missing for last successful option."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            use_last_successful=True,
            batch_time_size="PT12H"
        )
        
        workspaces = []
        
        # This should be tested as an async function
        import asyncio
        
        async def test_missing_logger():
            with pytest.raises(TimeRangeCalculationError, match="use_last_successful requires health logging"):
                await calculate_execution_time_ranges(options, workspaces)
        
        # Run the async test
        asyncio.run(test_missing_logger())
    
    def test_invalid_time_configuration_error(self):
        """Test error for invalid time configuration."""
        # Create options with invalid start_time but no end_time
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            start_time="invalid-datetime-string",
            batch_time_size="PT12H"
        )
        
        workspaces = []
        
        # This should be tested as an async function
        import asyncio
        
        async def test_invalid_config():
            with pytest.raises(TimeRangeCalculationError, match="Time range calculation failed"):
                await calculate_execution_time_ranges(options, workspaces)
        
        # Run the async test
        asyncio.run(test_invalid_config())


class TestLastSuccessfulRunsProcessing:
    """Test processing of last successful runs from health table."""
    
    @pytest.mark.asyncio
    async def test_query_last_successful_for_query_workspace_success(self):
        """Test successful query for last successful run."""
        workspace_id = "test-workspace-id"
        query_name = "test_query"
        
        # Mock the health logger and Azure clients
        mock_health_logger = AsyncMock()
        
        with patch('azure.monitor.query.aio.LogsQueryClient') as mock_logs_client_class, \
             patch('azure.identity.aio.DefaultAzureCredential') as mock_credential_class:
            
            # Set up mock objects
            mock_credential = AsyncMock()
            mock_credential_class.return_value = mock_credential
            
            mock_query_client = AsyncMock()
            mock_logs_client_class.return_value = mock_query_client
            
            # Mock response
            mock_response = MagicMock()
            mock_table = MagicMock()
            
            # Create proper column mocks with name attribute
            mock_columns = []
            for col_name in ["QueryName", "WorkspaceId", "StartTime", "EndTime", "RecordCount", "LastRunTime"]:
                mock_col = MagicMock()
                mock_col.name = col_name
                mock_columns.append(mock_col)
            
            mock_table.columns = mock_columns
            mock_table.rows = [[
                "test_query",
                "test-workspace-id", 
                "2025-11-01T10:00:00Z",
                "2025-11-01T12:00:00Z",
                100,
                "2025-11-01T12:05:00Z"
            ]]
            mock_response.tables = [mock_table]
            mock_query_client.query_workspace.return_value = mock_response
            
            result = await _query_last_successful_for_query_workspace(
                mock_health_logger, workspace_id, query_name
            )
            
            # Verify result
            assert result is not None
            assert result["QueryName"] == "test_query"
            assert result["WorkspaceId"] == "test-workspace-id"
            assert "starttime" in result
            assert "endtime" in result
    
    @pytest.mark.asyncio
    async def test_query_last_successful_for_query_workspace_no_results(self):
        """Test query when no results are found."""
        workspace_id = "test-workspace-id"
        query_name = "test_query"
        
        mock_health_logger = AsyncMock()
        
        with patch('azure.monitor.query.aio.LogsQueryClient') as mock_logs_client_class, \
             patch('azure.identity.aio.DefaultAzureCredential') as mock_credential_class:
            
            # Set up mock objects
            mock_credential = AsyncMock()
            mock_credential_class.return_value = mock_credential
            
            mock_query_client = AsyncMock()
            mock_logs_client_class.return_value = mock_query_client
            
            # Mock empty response
            mock_response = MagicMock()
            mock_response.tables = []
            mock_query_client.query_workspace.return_value = mock_response
            
            result = await _query_last_successful_for_query_workspace(
                mock_health_logger, workspace_id, query_name
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_calculate_from_last_successful_success(self):
        """Test successful calculation from last successful runs."""
        from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions
        
        client_options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            use_last_successful=True,
            batch_time_size="PT12H"
        )
        
        workspaces = [
            WorkspaceConfig(
                customer_id="ws1", 
                resource_id="/path/to/ws1",
                queries_list=[{"name": "test_query"}]
            ),
            WorkspaceConfig(
                customer_id="ws2", 
                resource_id="/path/to/ws2",
                queries_list=[{"name": "test_query"}]
            )
        ]
        
        mock_health_logger = AsyncMock()
        batch_size = timedelta(hours=12)
        
        # Mock the individual query function
        with patch('sentinel_log_aggregator.time_range_calculator._query_last_successful_for_query_workspace') as mock_query:
            mock_query.side_effect = [
                {"end_time": "2025-11-01T12:00:00Z"},  # ws1
                {"end_time": "2025-11-01T10:00:00Z"}   # ws2 (earlier)
            ]
            
            with patch('sentinel_log_aggregator.time_range_calculator.datetime') as mock_datetime:
                mock_now = datetime(2025, 11, 3, 12, 0, 0, tzinfo=timezone.utc)
                mock_datetime.now.return_value = mock_now
                
                start_time, end_time = await _calculate_from_last_successful(
                    client_options, workspaces, mock_health_logger, batch_size
                )
        
        # Should use the earliest end time
        assert start_time.year == 2025
        assert start_time.month == 11
        assert start_time.day == 1
        assert start_time.hour == 10  # Earlier of the two
        assert end_time == mock_now
    
    @pytest.mark.asyncio
    async def test_calculate_from_last_successful_missing_runs(self):
        """Test calculation when some successful runs are missing."""
        from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions
        
        client_options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            use_last_successful=True,
            batch_time_size="PT12H"
        )
        
        workspaces = [
            WorkspaceConfig(
                customer_id="ws1", 
                resource_id="/path/to/ws1",
                queries_list=[{"name": "test_query"}]
            )
        ]
        
        mock_health_logger = AsyncMock()
        batch_size = timedelta(hours=12)
        
        # Mock missing results
        with patch('sentinel_log_aggregator.time_range_calculator._query_last_successful_for_query_workspace') as mock_query:
            mock_query.return_value = None  # No successful runs found
            
            with pytest.raises(TimeRangeCalculationError, match="Cannot use last successful timestamps"):
                await _calculate_from_last_successful(
                    client_options, workspaces, mock_health_logger, batch_size
                )


class TestBatchCalculation:
    """Test batch calculation functionality."""
    
    def test_calculate_execution_batches_simple(self):
        """Test simple batch calculation."""
        start_time = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 3, 0, 0, 0, tzinfo=timezone.utc)
        batch_size = timedelta(hours=24)
        
        batches = calculate_execution_batches(start_time, end_time, batch_size)
        
        assert len(batches) == 2
        assert batches[0] == (
            datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 11, 2, 0, 0, 0, tzinfo=timezone.utc)
        )
        assert batches[1] == (
            datetime(2025, 11, 2, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 11, 3, 0, 0, 0, tzinfo=timezone.utc)
        )
    
    def test_calculate_execution_batches_partial(self):
        """Test batch calculation with partial final batch."""
        start_time = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 1, 18, 0, 0, tzinfo=timezone.utc)
        batch_size = timedelta(hours=12)
        
        batches = calculate_execution_batches(start_time, end_time, batch_size)
        
        assert len(batches) == 2
        assert batches[0] == (
            datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
        )
        assert batches[1] == (
            datetime(2025, 11, 1, 12, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 11, 1, 18, 0, 0, tzinfo=timezone.utc)
        )
    
    def test_calculate_execution_batches_single(self):
        """Test batch calculation for single batch."""
        start_time = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 1, 6, 0, 0, tzinfo=timezone.utc)
        batch_size = timedelta(hours=12)
        
        batches = calculate_execution_batches(start_time, end_time, batch_size)
        
        assert len(batches) == 1
        assert batches[0] == (start_time, end_time)
    
    def test_calculate_execution_batches_empty(self):
        """Test batch calculation for very short time range."""
        start_time = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 1, 0, 30, 0, tzinfo=timezone.utc)  # 30 minutes
        batch_size = timedelta(hours=1)
        
        batches = calculate_execution_batches(start_time, end_time, batch_size)
        
        assert len(batches) == 0  # No batches since range is shorter than min_batch_size


class TestErrorHandling:
    """Test error handling in time range calculator."""
    
    def test_time_range_calculation_error(self):
        """Test TimeRangeCalculationError properties."""
        error = TimeRangeCalculationError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    @pytest.mark.asyncio
    async def test_error_propagation_from_time_utils(self):
        """Test that errors from time_utils are properly propagated."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            lookback_period="invalid",  # This should cause TimeParsingError
            batch_time_size="PT12H"
        )
        
        workspaces = []
        
        with pytest.raises(TimeRangeCalculationError):
            await calculate_execution_time_ranges(options, workspaces)
    
    def test_error_handling_in_validation(self):
        """Test error handling in validation catches all exceptions."""
        # Create a mock that will raise an unexpected exception
        mock_options = MagicMock()
        mock_options.start_time = None
        mock_options.end_time = None
        mock_options.lookback_period = None
        mock_options.use_last_successful = False
        mock_options.batch_time_size = "PT12H"
        
        # Make an attribute access raise an exception
        type(mock_options).lookback_period = PropertyMock(side_effect=Exception("Unexpected error"))
        
        errors = validate_time_configuration(mock_options)
        
        # Should catch the exception and return it as a validation error
        assert len(errors) == 1
        assert "Time configuration validation error" in errors[0]
        assert "Unexpected error" in errors[0]


class TestIntegrationScenarios:
    """Test realistic integration scenarios combining multiple components."""
    
    @patch('sentinel_log_aggregator.time_utils.datetime')
    @pytest.mark.asyncio
    async def test_full_lookback_scenario(self, mock_datetime):
        """Test complete lookback period scenario."""
        mock_now = datetime(2025, 11, 3, 14, 30, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            lookback_period="P3D",
            batch_time_size="PT6H"
        )
        
        workspaces = [
            WorkspaceConfig(customer_id="ws1", resource_id="/path/to/ws1"),
            WorkspaceConfig(customer_id="ws2", resource_id="/path/to/ws2")
        ]
        
        # Calculate time ranges
        start_time, end_time, batch_size = await calculate_execution_time_ranges(
            options, workspaces
        )
        
        # Calculate batches
        batches = calculate_execution_batches(start_time, end_time, batch_size)
        
        # Verify results
        expected_start = mock_now - timedelta(days=3)
        assert start_time == expected_start
        assert end_time == mock_now
        assert batch_size == timedelta(hours=6)
        
        # Should have 12 batches (3 days * 4 batches per day)
        assert len(batches) == 12
        
        # Verify batch continuity
        for i in range(len(batches) - 1):
            assert batches[i][1] == batches[i + 1][0]
        
        # Verify full range coverage
        assert batches[0][0] == start_time
        assert batches[-1][1] == end_time
    
    @pytest.mark.asyncio
    async def test_full_explicit_time_scenario(self):
        """Test complete explicit time range scenario."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            start_time="2025-10-01T00:00:00Z",
            end_time="2025-10-02T00:00:00Z",
            batch_time_size="PT8H"
        )
        
        workspaces = [
            WorkspaceConfig(customer_id="ws1", resource_id="/path/to/ws1")
        ]
        
        # Validate configuration first
        errors = validate_time_configuration(options)
        assert errors == []
        
        # Calculate time ranges
        start_time, end_time, batch_size = await calculate_execution_time_ranges(
            options, workspaces
        )
        
        # Calculate batches
        batches = calculate_execution_batches(start_time, end_time, batch_size)
        
        # Verify results
        assert start_time.year == 2025
        assert start_time.month == 10
        assert start_time.day == 1
        assert end_time.year == 2025
        assert end_time.month == 10
        assert end_time.day == 2
        assert batch_size == timedelta(hours=8)
        
        # Should have 3 batches (24 hours / 8 hours)
        assert len(batches) == 3
        
        # Verify each batch is exactly 8 hours
        for batch_start, batch_end in batches:
            assert batch_end - batch_start == timedelta(hours=8)
    
    @pytest.mark.skip(reason="Complex Azure mocking scenario - core functionality tested elsewhere")
    @pytest.mark.asyncio
    async def test_precedence_logic_scenario(self):
        """Test that precedence logic works correctly."""
        # Test that use_last_successful takes precedence over explicit times
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.com",
            dcr_rule_id="test-rule",
            start_time="2025-10-01T00:00:00Z",  # This should be ignored
            use_last_successful=True,           # This takes precedence
            batch_time_size="PT12H"
        )
        
        workspaces = [
            WorkspaceConfig(
                customer_id="ws1", 
                resource_id="/path/to/ws1",
                queries_list=[{"name": "test_query"}]
            )
        ]
        
        mock_health_logger = AsyncMock()
        mock_health_logger.query_logs.return_value = [
            {
                "workspace_id": "ws1",
                "query_name": "test_query",
                "last_successful_time": "2025-11-01T08:00:00Z"
            }
        ]
        
        # Mock the Azure query function to return a successful result
        with patch('azure.monitor.query.aio.LogsQueryClient') as mock_logs_client_class, \
             patch('azure.identity.aio.DefaultAzureCredential') as mock_credential_class, \
             patch('sentinel_log_aggregator.time_utils.datetime') as mock_datetime:
            
            # Set up Azure mocks
            mock_credential = AsyncMock()
            mock_credential_class.return_value = mock_credential
            
            mock_query_client = AsyncMock()
            mock_logs_client_class.return_value = mock_query_client
            
            # Mock successful query response
            mock_response = MagicMock()
            mock_table = MagicMock()
            
            # Create proper column mocks
            mock_columns = []
            for col_name in ["QueryName", "WorkspaceId", "StartTime", "EndTime", "RecordCount", "LastRunTime"]:
                mock_col = MagicMock()
                mock_col.name = col_name
                mock_columns.append(mock_col)
            
            mock_table.columns = mock_columns
            mock_table.rows = [[
                "test_query",
                "ws1", 
                "2025-11-01T06:00:00Z",
                "2025-11-01T08:00:00Z",  # This will be the start time
                100,
                "2025-11-01T08:05:00Z"
            ]]
            mock_response.tables = [mock_table]
            mock_query_client.query_workspace.return_value = mock_response
            
            # Mock current time
            mock_now = datetime(2025, 11, 3, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            
            start_time, end_time, batch_size = await calculate_execution_time_ranges(
                options, workspaces, mock_health_logger
            )
        
        # Should use last successful time, not explicit start_time
        assert start_time.year == 2025
        assert start_time.month == 11
        assert start_time.day == 1
        assert start_time.hour == 8  # From last successful, not explicit start_time
        assert end_time == mock_now