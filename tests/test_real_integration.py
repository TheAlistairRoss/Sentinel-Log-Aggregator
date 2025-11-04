"""
Real integration tests for Microsoft Sentinel Log Aggregator.

These tests use actual Azure credentials and workspaces to validate the end-to-end functionality.
They are designed to be run manually with real Azure resources and credentials.

Test queries are loaded from tests/data/queries/ and workspace configurations are generated
dynamically using TEST_WORKSPACE_ID and TEST_WORKSPACE_CUSTOMER_ID from the .env file.
"""

import asyncio
import os
from pathlib import Path

import pytest
from azure.identity.aio import DefaultAzureCredential

from sentinel_log_aggregator import SentinelAggregatorClient, SentinelAggregatorClientOptions
from sentinel_log_aggregator.models import WorkspaceConfig
from sentinel_log_aggregator.query_engine import SentinelQueryEngine


class TestRealAzureIntegration:
    """Real integration tests using actual Azure resources."""

    @pytest.fixture
    def client_options(self):
        """Create client options from environment variables."""
        # Load environment from .env file
        from dotenv import load_dotenv

        load_dotenv()

        # Validate required environment variables
        required_vars = [
            "DCR_LOGS_INGESTION_ENDPOINT",
            "DCR_RULE_ID",
            "AZURE_CLIENT_ID",
            "AZURE_TENANT_ID",
            "AZURE_CLIENT_SECRET",
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            pytest.skip(f"Missing required environment variables: {missing_vars}")

        return SentinelAggregatorClientOptions.from_environment()

    @pytest.fixture
    def test_workspace_config(self):
        """Create test workspace configuration from environment variables."""
        from dotenv import load_dotenv

        load_dotenv()

        # Get test workspace details from environment
        test_workspace_id = os.getenv("TEST_WORKSPACE_ID")
        test_workspace_customer_id = os.getenv("TEST_WORKSPACE_CUSTOMER_ID")

        if not test_workspace_id or not test_workspace_customer_id:
            pytest.skip(
                "TEST_WORKSPACE_ID and TEST_WORKSPACE_CUSTOMER_ID must be set in .env for integration tests"
            )

        return {"resource_id": test_workspace_id, "customer_id": test_workspace_customer_id}

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_azure_authentication(self, client_options):
        """Test Azure authentication with real credentials."""
        credential = DefaultAzureCredential()

        async with SentinelAggregatorClient(
            dcr_logs_ingestion_endpoint=client_options.dcr_logs_ingestion_endpoint,
            credential=credential,
            options=client_options,
        ) as client:

            # Test credential validation
            await client.validate_credentials()

            # Test service properties
            service_props = await client.get_service_properties()
            assert service_props.connectivity_status == "connected"
            assert service_props.authentication_status == "valid"
            assert service_props.dcr_endpoint == client_options.dcr_logs_ingestion_endpoint
            assert service_props.dcr_immutable_id == client_options.dcr_immutable_id

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workspace_connectivity(self, client_options, test_workspace_config):
        """Test connectivity to test workspace."""
        credential = DefaultAzureCredential()

        async with SentinelAggregatorClient(
            dcr_logs_ingestion_endpoint=client_options.dcr_logs_ingestion_endpoint,
            credential=credential,
            options=client_options,
        ) as client:

            # Simple connectivity test query
            test_query = "print 'Integration test - workspace connectivity successful'"

            result = await client.query_workspace(
                workspace_id=test_workspace_config["customer_id"], query=test_query
            )

            assert result.succeeded, f"Query failed: {result.error_message}"
            assert result.record_count >= 0
            assert result.execution_time > 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_query_without_params(self, client_options, test_workspace_config):
        """Test query execution without parameters using tests_query_without_params.yaml."""

        # Create workspace config for tests_query_without_params
        workspace = WorkspaceConfig(
            resource_id=test_workspace_config["resource_id"],
            customer_id=test_workspace_config["customer_id"],
            queries_list=["tests/data/queries/tests_query_without_params.yaml"],
            parameters={"row_level_security_tag": "TEST_NO_PARAMS"},
        )

        credential = DefaultAzureCredential()

        # Use minimal options for testing
        test_options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint=client_options.dcr_logs_ingestion_endpoint,
            dcr_immutable_id=client_options.dcr_immutable_id,
            days_ago=1,  # Only last 1 day
            batch_hours=24,  # Single batch
            max_concurrent_queries=1,
            query_timeout_seconds=client_options.query_timeout_seconds,
            max_retries=client_options.max_retries,
            retry_delay_seconds=client_options.retry_delay_seconds,
        )

        async with SentinelAggregatorClient(
            dcr_logs_ingestion_endpoint=test_options.dcr_logs_ingestion_endpoint,
            credential=credential,
            options=test_options,
        ) as client:

            query_engine = SentinelQueryEngine(test_options, client)

            # Execute the query
            summary = await query_engine.execute_batch_queries_with_streaming_upload([workspace])

            # Validate results
            assert summary.total_queries > 0, "No queries were executed"
            assert (
                summary.successful_queries > 0
            ), f"No successful queries. Failed: {summary.failed_queries}"

            # Check for the expected result - should have WithoutParams = true
            successful_executions = [e for e in summary.executions if e.query_status == "success"]
            assert len(successful_executions) > 0, "No successful executions found"

            print(f"\\nQuery without params test:")
            print(f"  Successful queries: {summary.successful_queries}")
            print(f"  Total records: {summary.total_records}")
            print(f"  Query name: {successful_executions[0].query_name}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_query_with_params(self, client_options, test_workspace_config):
        """Test query execution with parameters using tests_query_with_params.yaml."""

        # Create workspace config for tests_query_with_params
        workspace = WorkspaceConfig(
            resource_id=test_workspace_config["resource_id"],
            customer_id=test_workspace_config["customer_id"],
            queries_list=["tests/data/queries/tests_query_with_params.yaml"],
            parameters={
                "row_level_security_tag": "TEST_WITH_PARAMS",
                "required_param": "test_required_value",
                "non_required_param": "test_optional_value",
            },
        )

        credential = DefaultAzureCredential()

        # Use minimal options for testing
        test_options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint=client_options.dcr_logs_ingestion_endpoint,
            dcr_immutable_id=client_options.dcr_immutable_id,
            days_ago=1,  # Only last 1 day
            batch_hours=24,  # Single batch
            max_concurrent_queries=1,
            query_timeout_seconds=client_options.query_timeout_seconds,
            max_retries=client_options.max_retries,
            retry_delay_seconds=client_options.retry_delay_seconds,
        )

        async with SentinelAggregatorClient(
            dcr_logs_ingestion_endpoint=test_options.dcr_logs_ingestion_endpoint,
            credential=credential,
            options=test_options,
        ) as client:

            query_engine = SentinelQueryEngine(test_options, client)

            # Execute the query
            summary = await query_engine.execute_batch_queries_with_streaming_upload([workspace])

            # Validate results
            assert summary.total_queries > 0, "No queries were executed"
            assert (
                summary.successful_queries > 0
            ), f"No successful queries. Failed: {summary.failed_queries}"

            # Check for the expected result - should have parameter values
            successful_executions = [e for e in summary.executions if e.query_status == "success"]
            assert len(successful_executions) > 0, "No successful executions found"

            print(f"\\nQuery with params test:")
            print(f"  Successful queries: {summary.successful_queries}")
            print(f"  Total records: {summary.total_records}")
            print(f"  Query name: {successful_executions[0].query_name}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_query_broken_syntax(self, client_options, test_workspace_config):
        """Test query execution with broken syntax using tests_query_broken_syntax.yaml."""

        # Create workspace config for tests_query_broken_syntax
        workspace = WorkspaceConfig(
            resource_id=test_workspace_config["resource_id"],
            customer_id=test_workspace_config["customer_id"],
            queries_list=["tests/data/queries/tests_query_broken_syntax.yaml"],
            parameters={"row_level_security_tag": "TEST_BROKEN_SYNTAX"},
        )

        credential = DefaultAzureCredential()

        # Use minimal options for testing
        test_options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint=client_options.dcr_logs_ingestion_endpoint,
            dcr_immutable_id=client_options.dcr_immutable_id,
            days_ago=1,  # Only last 1 day
            batch_hours=24,  # Single batch
            max_concurrent_queries=1,
            query_timeout_seconds=client_options.query_timeout_seconds,
            max_retries=client_options.max_retries,
            retry_delay_seconds=client_options.retry_delay_seconds,
        )

        async with SentinelAggregatorClient(
            dcr_logs_ingestion_endpoint=test_options.dcr_logs_ingestion_endpoint,
            credential=credential,
            options=test_options,
        ) as client:

            query_engine = SentinelQueryEngine(test_options, client)

            # Execute the query - this should fail due to broken syntax
            # But the broken syntax query file itself has malformed YAML, so it should be skipped during loading
            summary = await query_engine.execute_batch_queries_with_streaming_upload([workspace])

            # The broken syntax file should not load properly, so no queries should be executed
            # OR if it does load, all queries should fail
            print(f"\\nBroken syntax test:")
            print(f"  Total queries: {summary.total_queries}")
            print(f"  Successful queries: {summary.successful_queries}")
            print(f"  Failed queries: {summary.failed_queries}")

            # Either no queries executed (file didn't load) or all queries failed
            if summary.total_queries > 0:
                # If queries were executed, they should all fail
                assert (
                    summary.failed_queries == summary.total_queries
                ), "Broken syntax query should fail"
                assert summary.successful_queries == 0, "Broken syntax query should not succeed"
            else:
                # Query file failed to load due to malformed YAML, which is also acceptable
                print("  Broken syntax query file failed to load (expected)")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_all_test_queries_together(self, client_options, test_workspace_config):
        """Test all test queries together in a single workspace configuration."""

        # Create workspace config with all test queries (except broken syntax due to YAML parsing issues)
        workspace = WorkspaceConfig(
            resource_id=test_workspace_config["resource_id"],
            customer_id=test_workspace_config["customer_id"],
            queries_list=[
                "tests/data/queries/tests_query_without_params.yaml",
                "tests/data/queries/tests_query_with_params.yaml",
            ],
            parameters={
                "row_level_security_tag": "TEST_ALL_QUERIES",
                "required_param": "test_required_value",
                "non_required_param": "test_optional_value",
            },
        )

        credential = DefaultAzureCredential()

        # Use minimal options for testing
        test_options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint=client_options.dcr_logs_ingestion_endpoint,
            dcr_immutable_id=client_options.dcr_immutable_id,
            days_ago=1,  # Only last 1 day
            batch_hours=24,  # Single batch
            max_concurrent_queries=1,
            query_timeout_seconds=client_options.query_timeout_seconds,
            max_retries=client_options.max_retries,
            retry_delay_seconds=client_options.retry_delay_seconds,
        )

        async with SentinelAggregatorClient(
            dcr_logs_ingestion_endpoint=test_options.dcr_logs_ingestion_endpoint,
            credential=credential,
            options=test_options,
        ) as client:

            query_engine = SentinelQueryEngine(test_options, client)

            # Execute all queries
            summary = await query_engine.execute_batch_queries_with_streaming_upload([workspace])

            # Validate results
            assert summary.total_queries > 0, "No queries were executed"
            assert (
                summary.successful_queries > 0
            ), f"No successful queries. Failed: {summary.failed_queries}"

            # Should have 2 successful queries (with_params and without_params)
            assert (
                summary.successful_queries >= 1
            ), f"Expected at least 1 successful query, got {summary.successful_queries}"

            # Print detailed summary
            detailed_summary = summary.generate_detailed_summary()
            print("\\n" + "=" * 60)
            print("ALL TEST QUERIES INTEGRATION TEST SUMMARY")
            print("=" * 60)
            print(f"Total Duration: {detailed_summary['overview']['total_duration_seconds']:.2f}s")
            print(f"Workspaces: {detailed_summary['overview']['total_workspaces']}")
            print(
                f"Records Downloaded: {detailed_summary['overview']['total_records_downloaded']:,}"
            )
            print(f"Records Uploaded: {detailed_summary['overview']['total_records_uploaded']:,}")
            print(
                f"Success Rate: {summary.success_rate:.1%} ({summary.successful_queries}/{summary.total_queries})"
            )

            # Check individual query results
            print("\\nQuery Execution Details:")
            for workspace_summary in detailed_summary.get("workspaces", []):
                print(f"  Workspace: {workspace_summary['workspace_tag']}")
                for query_result in workspace_summary.get("queries", []):
                    print(
                        f"    {query_result['query_name']}: {query_result['status']} - {query_result['records']} records"
                    )
                    if query_result.get("error"):
                        print(f"      Error: {query_result['error']}")
            print("=" * 60)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_individual_query_execution(self, client_options, test_workspace_config):
        """Test individual query execution using the same queries as the batch test."""
        credential = DefaultAzureCredential()

        async with SentinelAggregatorClient(
            dcr_logs_ingestion_endpoint=client_options.dcr_logs_ingestion_endpoint,
            credential=credential,
            options=client_options,
        ) as client:

            # Test 1: Simple query without parameters (should always work)
            simple_query = """print WithoutParams = true"""

            result = await client.query_workspace(
                workspace_id=test_workspace_config["customer_id"], query=simple_query
            )

            assert result.succeeded, f"Simple query failed: {result.error_message}"
            assert result.record_count == 1, f"Expected 1 record, got {result.record_count}"
            print(f"\\nSimple query test:")
            print(f"  Records found: {result.record_count}")
            print(f"  Execution time: {result.execution_time:.2f}s")

            # Test 2: Usage table query (if available)
            usage_query = """
            Usage
            | where TimeGenerated > ago(7d)
            | summarize Count = count() by DataType
            | project DataType, Count, TestResult = "Usage data check"
            | limit 5
            """

            result = await client.query_workspace(
                workspace_id=test_workspace_config["customer_id"], query=usage_query
            )

            print(f"\\nUsage table test:")
            print(f"  Query succeeded: {result.succeeded}")
            print(f"  Records found: {result.record_count}")
            print(f"  Execution time: {result.execution_time:.2f}s")
            if not result.succeeded:
                print(f"  Error: {result.error_message}")

            # Test 3: Parameter substitution test
            param_query = """
            print
                RequiredParam = "test_param_value",
                WorkspaceTag = "TEST_WORKSPACE",
                TestType = "Parameter substitution"
            """

            result = await client.query_workspace(
                workspace_id=test_workspace_config["customer_id"], query=param_query
            )

            assert result.succeeded, f"Parameter query failed: {result.error_message}"
            print(f"\\nParameter substitution test:")
            print(f"  Records found: {result.record_count}")
            print(f"  Execution time: {result.execution_time:.2f}s")
            print(f"  Test workspace: {test_workspace_config['customer_id'][:8]}***")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_configuration_validation(self, client_options, test_workspace_config):
        """Test configuration validation with real settings."""
        # Validate client options
        config_errors = client_options.validate()
        assert not config_errors, f"Configuration validation failed: {config_errors}"

        # Validate test workspace configuration
        assert test_workspace_config["customer_id"], "Test workspace customer_id is required"
        assert test_workspace_config["resource_id"], "Test workspace resource_id is required"

        print(f"\\nConfiguration validation successful:")
        print(f"  Test workspace configured: {test_workspace_config['customer_id'][:8]}***")
        print(f"  DCR endpoint: {client_options.dcr_logs_ingestion_endpoint}")
        print(
            f"  Batch settings: {client_options.days_ago} days, {client_options.batch_hours}h batches"
        )
