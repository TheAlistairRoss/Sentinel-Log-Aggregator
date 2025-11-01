"""
Tests for command-line interface (CLI) module.

Provides comprehensive testing for CLI argument parsing, environment variable loading,
client options creation, error handling, and command execution.
"""

import argparse
import asyncio
import os
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from azure.core.exceptions import AzureError

from sentinel_log_aggregator.cli import (
    cli_main,
    create_client_options_from_args,
    create_parser,
    load_environment_variables,
    main,
    setup_logging,
)
from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions
from sentinel_log_aggregator.models import WorkspaceConfig


class TestEnvironmentVariableLoading:
    """Test environment variable loading functionality."""

    def test_load_environment_variables_default_file_exists(self):
        """Test loading from default .env file when it exists."""
        with (
            patch("sentinel_log_aggregator.cli.Path.exists", return_value=True),
            patch("sentinel_log_aggregator.cli.load_dotenv") as mock_load_dotenv,
        ):

            load_environment_variables()
            mock_load_dotenv.assert_called_once()

    def test_load_environment_variables_default_file_not_exists(self):
        """Test behavior when default .env file doesn't exist."""
        with (
            patch("sentinel_log_aggregator.cli.Path.exists", return_value=False),
            patch("sentinel_log_aggregator.cli.load_dotenv") as mock_load_dotenv,
        ):

            load_environment_variables()
            mock_load_dotenv.assert_not_called()

    def test_load_environment_variables_custom_file_exists(self):
        """Test loading from custom .env file when it exists."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("sentinel_log_aggregator.cli.load_dotenv") as mock_load_dotenv,
        ):

            custom_path = Path("/custom/.env")
            load_environment_variables(custom_path)
            mock_load_dotenv.assert_called_once_with(custom_path)

    def test_load_environment_variables_custom_file_not_exists(self):
        """Test error handling when custom .env file doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            custom_path = Path("/nonexistent/.env")
            with pytest.raises(FileNotFoundError, match="Specified .env file not found"):
                load_environment_variables(custom_path)


class TestClientOptionsCreation:
    """Test client options creation from CLI arguments."""

    @pytest.fixture
    def mock_args(self):
        """Create mock arguments for testing."""
        args = MagicMock()
        args.dcr_endpoint = "https://test.ingest.monitor.azure.com"
        args.dcr_rule_id = "dcr-test-rule-id"
        args.days_back = 7
        args.batch_hours = 12
        args.max_concurrent_queries = 3
        return args

    def test_create_client_options_from_args_success(self, mock_args):
        """Test successful client options creation from arguments."""
        with patch.dict(os.environ, {}, clear=True):
            options = create_client_options_from_args(mock_args)

            assert options.dcr_logs_ingestion_endpoint == "https://test.ingest.monitor.azure.com"
            assert options.dcr_rule_id == "dcr-test-rule-id"
            assert options.days_ago == 7
            assert options.batch_hours == 12
            assert options.max_concurrent_queries == 3

    def test_create_client_options_missing_dcr_endpoint(self, mock_args):
        """Test error when DCR endpoint is missing."""
        mock_args.dcr_endpoint = None

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="DCR logs ingestion endpoint is required"):
                create_client_options_from_args(mock_args)

    def test_create_client_options_missing_dcr_rule_id(self, mock_args):
        """Test error when DCR rule ID is missing."""
        mock_args.dcr_rule_id = None

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="DCR rule ID is required"):
                create_client_options_from_args(mock_args)

    def test_create_client_options_env_fallback(self, mock_args):
        """Test fallback to environment variables when args are None."""
        mock_args.dcr_endpoint = None
        mock_args.dcr_rule_id = None
        mock_args.days_back = None
        mock_args.batch_hours = None
        mock_args.max_concurrent_queries = None

        env_vars = {
            "DCR_LOGS_INGESTION_ENDPOINT": "https://env.ingest.monitor.azure.com",
            "DCR_RULE_ID": "dcr-env-rule-id",
            "DAYS_AGO": "14",
            "BATCH_HOURS": "6",
            "MAX_CONCURRENT_QUERIES": "8",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            options = create_client_options_from_args(mock_args)

            assert options.dcr_logs_ingestion_endpoint == "https://env.ingest.monitor.azure.com"
            assert options.dcr_rule_id == "dcr-env-rule-id"
            assert options.days_ago == 14
            assert options.batch_hours == 6
            assert options.max_concurrent_queries == 8


class TestLoggingSetup:
    """Test logging configuration setup."""

    @patch("sentinel_log_aggregator.cli.configure_logging")
    def test_setup_logging_default(self, mock_configure_logging):
        """Test logging setup with default parameters."""
        setup_logging()

        mock_configure_logging.assert_called_once_with(
            level="INFO", format_string=None, enable_structured=False
        )

    @patch("sentinel_log_aggregator.cli.configure_logging")
    def test_setup_logging_custom(self, mock_configure_logging):
        """Test logging setup with custom parameters."""
        setup_logging(log_level="DEBUG", log_format="custom_format")

        mock_configure_logging.assert_called_once_with(
            level="DEBUG", format_string="custom_format", enable_structured=False
        )


class TestArgumentParser:
    """Test command-line argument parsing."""

    def test_create_parser_basic(self):
        """Test basic parser creation."""
        parser = create_parser()
        assert isinstance(parser, argparse.ArgumentParser)
        assert "Microsoft Sentinel Log Aggregator" in parser.description

    def test_parser_version_argument(self):
        """Test version argument parsing."""
        parser = create_parser()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                parser.parse_args(["--version"])

            assert exc_info.value.code == 0
            assert "Microsoft Sentinel Log Aggregator" in mock_stdout.getvalue()

    def test_parser_help_argument(self):
        """Test help argument parsing."""
        parser = create_parser()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                parser.parse_args(["--help"])

            assert exc_info.value.code == 0
            help_text = mock_stdout.getvalue()
            assert "Microsoft Sentinel Log Aggregator" in help_text
            assert "health" in help_text
            assert "run" in help_text
            assert "validate" in help_text

    def test_parser_global_arguments(self):
        """Test parsing of global arguments."""
        parser = create_parser()
        args = parser.parse_args(
            [
                "--log-level",
                "DEBUG",
                "--dcr-endpoint",
                "https://test.ingest.monitor.azure.com",
                "--dcr-rule-id",
                "dcr-test",
                "health",
                "--workspace-config",
                "test.yaml",
            ]
        )

        assert args.log_level == "DEBUG"
        assert args.dcr_endpoint == "https://test.ingest.monitor.azure.com"
        assert args.dcr_rule_id == "dcr-test"
        assert args.command == "health"

    def test_parser_health_command(self):
        """Test parsing health command arguments."""
        parser = create_parser()
        args = parser.parse_args(["health", "--workspace-config", "workspaces.yaml"])

        assert args.command == "health"
        assert args.workspace_config == Path("workspaces.yaml")

    def test_parser_run_command(self):
        """Test parsing run command arguments."""
        parser = create_parser()
        args = parser.parse_args(
            [
                "run",
                "--workspace-config",
                "workspaces.yaml",
                "--days-back",
                "14",
                "--batch-hours",
                "6",
                "--max-concurrent-queries",
                "10",
            ]
        )

        assert args.command == "run"
        assert args.workspace_config == Path("workspaces.yaml")
        assert args.days_back == 14
        assert args.batch_hours == 6
        assert args.max_concurrent_queries == 10

    def test_parser_validate_command(self):
        """Test parsing validate command arguments."""
        parser = create_parser()
        args = parser.parse_args(["validate", "--workspace-config", "workspaces.yaml"])

        assert args.command == "validate"
        assert args.workspace_config == Path("workspaces.yaml")

    def test_parser_invalid_log_level(self):
        """Test error handling for invalid log level."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(
                ["--log-level", "INVALID", "health", "--workspace-config", "test.yaml"]
            )


class TestMainFunction:
    """Test main CLI function execution."""

    @pytest.fixture
    def mock_client_options(self):
        """Create mock client options."""
        return SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.ingest.monitor.azure.com",
            dcr_rule_id="dcr-test-rule",
        )

    @pytest.fixture
    def mock_workspaces(self):
        """Create mock workspaces."""
        return [
            WorkspaceConfig(
                resource_id="/subscriptions/test/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace",
                customer_id="test-customer-id",
                parameters={"row_level_security_tag": "test"},
            )
        ]

    @patch("sentinel_log_aggregator.cli.load_environment_variables")
    @patch("sentinel_log_aggregator.cli.setup_logging")
    @patch("sentinel_log_aggregator.cli.create_client_options_from_args")
    @patch("sentinel_log_aggregator.cli.load_workspace_config")
    @patch("sentinel_log_aggregator.cli.check_service_health")
    @patch("sys.argv", ["sentinel-aggregator", "health", "--workspace-config", "test.yaml"])
    @pytest.mark.asyncio
    async def test_main_health_command_success(
        self,
        mock_health,
        mock_load_ws,
        mock_create_options,
        mock_setup_logging,
        mock_load_env,
        mock_workspaces,
        mock_client_options,
    ):
        """Test successful health command execution."""
        mock_load_ws.return_value = mock_workspaces
        mock_create_options.return_value = mock_client_options
        mock_health.return_value = True

        result = await main()

        assert result == 0
        mock_load_env.assert_called_once()
        mock_setup_logging.assert_called_once()
        mock_health.assert_called_once_with(mock_client_options, mock_workspaces)

    @patch("sentinel_log_aggregator.cli.load_environment_variables")
    @patch("sentinel_log_aggregator.cli.setup_logging")
    @patch("sentinel_log_aggregator.cli.create_client_options_from_args")
    @patch("sentinel_log_aggregator.cli.load_workspace_config")
    @patch("sentinel_log_aggregator.cli.run_aggregation")
    @patch(
        "sys.argv",
        ["sentinel-aggregator", "run", "--workspace-config", "test.yaml", "--days-back", "7"],
    )
    @pytest.mark.asyncio
    async def test_main_run_command_success(
        self,
        mock_run,
        mock_load_ws,
        mock_create_options,
        mock_setup_logging,
        mock_load_env,
        mock_workspaces,
        mock_client_options,
    ):
        """Test successful run command execution."""
        mock_load_ws.return_value = mock_workspaces
        mock_create_options.return_value = mock_client_options
        mock_run.return_value = True

        result = await main()

        assert result == 0
        mock_run.assert_called_once_with(
            mock_client_options, mock_workspaces, 7, mock_client_options.batch_hours
        )

    @patch("sentinel_log_aggregator.cli.load_environment_variables")
    @patch("sentinel_log_aggregator.cli.setup_logging")
    @patch("sentinel_log_aggregator.cli.create_client_options_from_args")
    @patch("sentinel_log_aggregator.cli.load_workspace_config")
    @patch("sys.argv", ["sentinel-aggregator", "validate", "--workspace-config", "test.yaml"])
    @pytest.mark.asyncio
    async def test_main_validate_command_success(
        self,
        mock_load_ws,
        mock_create_options,
        mock_setup_logging,
        mock_load_env,
        mock_workspaces,
        mock_client_options,
    ):
        """Test successful validate command execution."""
        mock_load_ws.return_value = mock_workspaces
        mock_client_options_instance = MagicMock()
        mock_client_options_instance.validate.return_value = []  # No validation errors
        mock_create_options.return_value = mock_client_options_instance

        result = await main()

        assert result == 0
        mock_client_options_instance.validate.assert_called_once()

    @patch("sentinel_log_aggregator.cli.load_environment_variables")
    @patch("sentinel_log_aggregator.cli.setup_logging")
    @patch("sys.argv", ["sentinel-aggregator"])
    @pytest.mark.asyncio
    async def test_main_no_command_shows_help(self, mock_setup_logging, mock_load_env):
        """Test that no command shows help and returns error code."""
        with patch("sentinel_log_aggregator.cli.create_parser") as mock_create_parser:
            mock_parser = MagicMock()
            mock_parser.parse_args.return_value.command = None
            mock_create_parser.return_value = mock_parser

            result = await main()

            assert result == 1
            mock_parser.print_help.assert_called_once()

    @patch("sentinel_log_aggregator.cli.load_environment_variables")
    @patch("sys.argv", ["sentinel-aggregator", "health", "--workspace-config", "test.yaml"])
    @pytest.mark.asyncio
    async def test_main_env_file_not_found_error(self, mock_load_env):
        """Test error handling when .env file is not found."""
        mock_load_env.side_effect = FileNotFoundError("Test .env file not found")

        with patch("builtins.print") as mock_print:
            result = await main()

            assert result == 1
            mock_print.assert_called_with("Error: Test .env file not found")

    @patch("sentinel_log_aggregator.cli.load_environment_variables")
    @patch("sentinel_log_aggregator.cli.setup_logging")
    @patch("sentinel_log_aggregator.cli.create_client_options_from_args")
    @patch("sys.argv", ["sentinel-aggregator", "health", "--workspace-config", "test.yaml"])
    @pytest.mark.asyncio
    async def test_main_unexpected_error(
        self, mock_create_options, mock_setup_logging, mock_load_env
    ):
        """Test error handling for unexpected exceptions."""
        mock_create_options.side_effect = Exception("Unexpected error")

        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            result = await main()

            assert result == 1
            mock_logger.error.assert_called()


class TestCLIMainWrapper:
    """Test the synchronous CLI entry point."""

    @patch("sentinel_log_aggregator.cli.asyncio.run")
    def test_cli_main_success(self, mock_asyncio_run):
        """Test successful CLI execution."""

        # Create a side effect that properly consumes the coroutine before returning
        def success_side_effect(coro):
            coro.close()  # Close the coroutine to avoid unawaited warning
            return 0

        mock_asyncio_run.side_effect = success_side_effect

        result = cli_main()

        assert result == 0
        mock_asyncio_run.assert_called_once()

    @patch("sentinel_log_aggregator.cli.asyncio.run")
    def test_cli_main_keyboard_interrupt(self, mock_asyncio_run):
        """Test handling of keyboard interrupt."""

        # Create a side effect that properly consumes the coroutine before raising
        def keyboard_interrupt_side_effect(coro):
            coro.close()  # Close the coroutine to avoid unawaited warning
            raise KeyboardInterrupt()

        mock_asyncio_run.side_effect = keyboard_interrupt_side_effect

        with patch("builtins.print") as mock_print:
            result = cli_main()

            assert result == 130
            mock_print.assert_called_with("\n❌ Operation cancelled by user")

    @patch("sentinel_log_aggregator.cli.asyncio.run")
    def test_cli_main_error(self, mock_asyncio_run):
        """Test CLI execution with error return code."""

        # Create a side effect that properly consumes the coroutine before returning
        def error_side_effect(coro):
            coro.close()  # Close the coroutine to avoid unawaited warning
            return 1

        mock_asyncio_run.side_effect = error_side_effect

        result = cli_main()

        assert result == 1


class TestArgumentValidation:
    """Test advanced argument validation scenarios."""

    def test_parser_missing_required_workspace_config(self):
        """Test error when required workspace-config is missing."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["health"])  # Missing --workspace-config

    def test_parser_env_file_path_handling(self):
        """Test env file path argument handling."""
        parser = create_parser()
        args = parser.parse_args(
            ["--env-file", "/custom/path/.env", "health", "--workspace-config", "test.yaml"]
        )

        assert args.env_file == Path("/custom/path/.env")

    def test_parser_config_file_path_handling(self):
        """Test config file path argument handling."""
        parser = create_parser()
        args = parser.parse_args(
            ["--config-file", "/path/to/config.yaml", "health", "--workspace-config", "test.yaml"]
        )

        assert args.config_file == Path("/path/to/config.yaml")


class TestEnvironmentVariableDefaults:
    """Test environment variable default handling."""

    def test_create_client_options_with_env_defaults(self):
        """Test client options creation with environment variable defaults."""
        args = MagicMock()
        args.dcr_endpoint = "https://test.ingest.monitor.azure.com"
        args.dcr_rule_id = "dcr-test"
        args.days_back = None
        args.batch_hours = None
        args.max_concurrent_queries = None

        env_vars = {"QUERY_TIMEOUT_SECONDS": "600", "MAX_RETRIES": "5", "RETRY_DELAY_SECONDS": "10"}

        with patch.dict(os.environ, env_vars, clear=True):
            options = create_client_options_from_args(args)

            assert options.query_timeout_seconds == 600
            assert options.max_retries == 5
            assert options.retry_delay_seconds == 10
            # Defaults for unset values
            assert options.days_ago == 30
            assert options.batch_hours == 24
            assert options.max_concurrent_queries == 5


class TestConfigFileLoading:
    """Test configuration file loading scenarios."""

    @pytest.fixture
    def mock_client_options(self):
        """Create mock client options for config file tests."""
        options = MagicMock()
        options.validate.return_value = []
        return options

    @patch("sentinel_log_aggregator.cli.load_environment_variables")
    @patch("sentinel_log_aggregator.cli.setup_logging")
    @patch("sentinel_log_aggregator.cli.SentinelAggregatorClientOptions.from_yaml_file")
    @patch("sentinel_log_aggregator.cli.load_workspace_config")
    @patch(
        "sys.argv",
        [
            "sentinel-aggregator",
            "--config-file",
            "config.yaml",
            "validate",
            "--workspace-config",
            "test.yaml",
        ],
    )
    @pytest.mark.asyncio
    async def test_main_with_config_file(
        self, mock_load_ws, mock_from_yaml, mock_setup_logging, mock_load_env, mock_client_options
    ):
        """Test main function with config file loading."""
        mock_from_yaml.return_value = mock_client_options
        mock_load_ws.return_value = []

        result = await main()

        assert result == 0
        mock_from_yaml.assert_called_once_with(Path("config.yaml"))


class TestCheckServiceHealth:
    """Test check_service_health function."""

    @pytest.mark.asyncio
    async def test_check_service_health_success(self):
        """Test successful service health check."""
        from sentinel_log_aggregator.cli import check_service_health
        from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions
        from sentinel_log_aggregator.models import WorkspaceConfig

        # Create test client options
        client_options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.ingest.monitor.azure.com",
            dcr_rule_id="dcr-12345678901234567890123456789012",  # Valid 32-char hex
            days_ago=7,
            batch_hours=24,
        )

        # Create test workspaces
        workspaces = [
            WorkspaceConfig(
                customer_id="11111111-1111-1111-1111-111111111111",
                resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.OperationalInsights/workspaces/test",
            )
        ]

        # Mock the SentinelAggregatorClient
        with patch("sentinel_log_aggregator.cli.SentinelAggregatorClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock the service properties with proper string values
            mock_service_props = MagicMock()
            mock_service_props.service_version = "1.0.0"
            mock_service_props.connectivity_status = "connected"  # lowercase to match check
            mock_service_props.authentication_status = "valid"  # lowercase to match check
            mock_service_props.dcr_endpoint = "https://test.ingest.monitor.azure.com"
            mock_service_props.workspace_count = 1
            mock_client.get_service_properties.return_value = mock_service_props

            # Mock the correct query method: query_workspace
            mock_query_result = MagicMock()
            mock_query_result.succeeded = True
            mock_query_result.record_count = 100
            mock_query_result.execution_time = 1.5
            mock_query_result.error_message = None
            mock_client.query_workspace.return_value = mock_query_result

            # Mock DefaultAzureCredential
            with patch("sentinel_log_aggregator.cli.DefaultAzureCredential") as mock_cred:
                mock_cred.return_value = MagicMock()

                result = await check_service_health(client_options, workspaces)

                assert result is True
                mock_client.validate_credentials.assert_called_once()
                mock_client.get_service_properties.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_service_health_query_failure(self):
        """Test service health check with failed test query."""
        from sentinel_log_aggregator.cli import check_service_health
        from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions
        from sentinel_log_aggregator.models import WorkspaceConfig

        # Create test client options
        client_options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.ingest.monitor.azure.com",
            dcr_rule_id="dcr-12345678901234567890123456789012",
            days_ago=7,
            batch_hours=24,
        )

        # Create test workspaces
        workspaces = [
            WorkspaceConfig(
                customer_id="11111111-1111-1111-1111-111111111111",
                resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.OperationalInsights/workspaces/test",
            )
        ]

        # Mock the SentinelAggregatorClient
        with patch("sentinel_log_aggregator.cli.SentinelAggregatorClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock successful credentials and service properties
            mock_client.validate_credentials.return_value = True

            mock_service_props = MagicMock()
            mock_service_props.service_version = "1.0.0"
            mock_service_props.connectivity_status = "connected"
            mock_service_props.authentication_status = "valid"
            mock_service_props.dcr_endpoint = "https://test.ingest.monitor.azure.com"
            mock_service_props.workspace_count = 1
            mock_client.get_service_properties.return_value = mock_service_props

            # Mock FAILED query result - this will hit line 163
            mock_query_result = MagicMock()
            mock_query_result.succeeded = False  # This makes the query fail
            mock_query_result.error_message = "Query syntax error"
            mock_client.query_workspace.return_value = mock_query_result

            # Mock DefaultAzureCredential
            with patch("sentinel_log_aggregator.cli.DefaultAzureCredential") as mock_cred:
                mock_cred.return_value = MagicMock()

                result = await check_service_health(client_options, workspaces)

                # Should still return True because connectivity and auth are valid,
                # even though the test query failed
                assert result is True

    @pytest.mark.asyncio
    async def test_check_service_health_credential_failure(self):
        """Test service health check with credential validation failure."""
        from sentinel_log_aggregator.cli import check_service_health
        from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions

        client_options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.ingest.monitor.azure.com",
            dcr_rule_id="dcr-12345678901234567890123456789012",
        )

        with patch("sentinel_log_aggregator.cli.SentinelAggregatorClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.validate_credentials.side_effect = AzureError("Authentication failed")

            with patch("sentinel_log_aggregator.cli.DefaultAzureCredential") as mock_cred:
                mock_cred.return_value = MagicMock()

                result = await check_service_health(client_options, [])

                assert result is False

    @pytest.mark.asyncio
    async def test_check_service_health_general_exception(self):
        """Test service health check with general exception."""
        from sentinel_log_aggregator.cli import check_service_health
        from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions

        client_options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.ingest.monitor.azure.com",
            dcr_rule_id="dcr-12345678901234567890123456789012",
        )

        with patch("sentinel_log_aggregator.cli.DefaultAzureCredential") as mock_cred:
            mock_cred.side_effect = Exception("Unexpected error")

            result = await check_service_health(client_options, [])

            assert result is False


class TestRunAggregation:
    """Test run_aggregation function."""

    @pytest.mark.asyncio
    async def test_run_aggregation_success(self):
        """Test successful run aggregation."""
        from sentinel_log_aggregator.cli import run_aggregation
        from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions
        from sentinel_log_aggregator.models import WorkspaceConfig

        client_options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.ingest.monitor.azure.com",
            dcr_rule_id="dcr-12345678901234567890123456789012",
            days_ago=7,
            batch_hours=24,
        )

        workspaces = [
            WorkspaceConfig(
                customer_id="11111111-1111-1111-1111-111111111111",
                resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.OperationalInsights/workspaces/test",
            )
        ]

        # Mock client_options.validate to return no errors
        with patch(
            "sentinel_log_aggregator.client_options.SentinelAggregatorClientOptions.validate",
            return_value=[],
        ):
            with patch("sentinel_log_aggregator.cli.SentinelAggregatorClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                # Mock the query engine
                with patch("sentinel_log_aggregator.cli.SentinelQueryEngine") as mock_engine_class:
                    mock_engine = AsyncMock()
                    mock_engine_class.return_value = mock_engine

                    # Mock successful batch execution
                    mock_summary = MagicMock()
                    mock_summary.failed_queries = 0
                    mock_summary.generate_detailed_summary.return_value = {
                        "overview": {
                            "total_time_range": "2024-01-01 to 2024-01-02",
                            "total_duration_seconds": 120.5,
                            "total_workspaces": 1,
                            "total_unique_queries": 3,
                            "total_records_downloaded": 1000,
                            "total_records_uploaded": 1000,
                        }
                    }
                    mock_engine.execute_batch_queries_with_streaming_upload.return_value = (
                        mock_summary
                    )

                    with patch("sentinel_log_aggregator.cli.DefaultAzureCredential") as mock_cred:
                        mock_cred.return_value = MagicMock()

                        result = await run_aggregation(client_options, workspaces, 7, 24)

                        assert result is True
                        mock_engine.execute_batch_queries_with_streaming_upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_aggregation_config_validation_failure(self):
        """Test run aggregation with configuration validation failure."""
        from sentinel_log_aggregator.cli import run_aggregation
        from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions

        # Create client options
        client_options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.ingest.monitor.azure.com",
            dcr_rule_id="dcr-12345678901234567890123456789012",
        )

        # Mock client_options.validate to return validation errors
        with patch(
            "sentinel_log_aggregator.client_options.SentinelAggregatorClientOptions.validate",
            return_value=["Missing required field"],
        ):
            result = await run_aggregation(client_options, [], 7, 24)

            assert result is False

    @pytest.mark.asyncio
    async def test_run_aggregation_with_overrides(self):
        """Test run aggregation with parameter overrides."""
        from sentinel_log_aggregator.cli import run_aggregation
        from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions

        client_options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.ingest.monitor.azure.com",
            dcr_rule_id="dcr-12345678901234567890123456789012",
            days_ago=30,  # Original value
            batch_hours=12,  # Original value
        )

        with patch("sentinel_log_aggregator.cli.SentinelAggregatorClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_summary = MagicMock()
            mock_client.execute_batch_queries_with_streaming_upload.return_value = mock_summary

            with patch("sentinel_log_aggregator.cli.DefaultAzureCredential") as mock_cred:
                mock_cred.return_value = MagicMock()

                # Override values should be used
                result = await run_aggregation(client_options, [], 7, 24)

                assert result is True
                # Verify overrides were applied
                assert client_options.days_ago == 7
                assert client_options.batch_hours == 24

    @pytest.mark.asyncio
    async def test_run_aggregation_execution_failure(self):
        """Test run aggregation with execution failure."""
        from sentinel_log_aggregator.cli import run_aggregation
        from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions

        client_options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.ingest.monitor.azure.com",
            dcr_rule_id="dcr-12345678901234567890123456789012",
        )

        # Mock client_options.validate to return no errors
        with patch(
            "sentinel_log_aggregator.client_options.SentinelAggregatorClientOptions.validate",
            return_value=[],
        ):
            with patch("sentinel_log_aggregator.cli.SentinelAggregatorClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                # Mock the query engine to raise an exception
                with patch("sentinel_log_aggregator.cli.SentinelQueryEngine") as mock_engine_class:
                    mock_engine = AsyncMock()
                    mock_engine_class.return_value = mock_engine
                    mock_engine.execute_batch_queries_with_streaming_upload.side_effect = Exception(
                        "Execution failed"
                    )

                    with patch("sentinel_log_aggregator.cli.DefaultAzureCredential") as mock_cred:
                        mock_cred.return_value = MagicMock()

                        result = await run_aggregation(client_options, [], 7, 24)

                        assert result is False


class TestMainCommandHandling:
    """Test main function command handling."""

    @pytest.mark.asyncio
    async def test_main_health_command(self):
        """Test main function with health command."""
        from sentinel_log_aggregator.cli import main

        with patch("sentinel_log_aggregator.cli.create_parser") as mock_create_parser:
            # Mock the parser and args
            mock_parser = MagicMock()
            mock_create_parser.return_value = mock_parser

            mock_args = MagicMock()
            mock_args.command = "health"
            mock_args.env_file = None
            mock_args.log_level = "INFO"
            mock_args.config_file = None
            mock_args.workspace_config = None
            mock_parser.parse_args.return_value = mock_args

            with patch(
                "sentinel_log_aggregator.cli.check_service_health", new_callable=AsyncMock
            ) as mock_health:
                with patch(
                    "sentinel_log_aggregator.cli.create_client_options_from_args"
                ) as mock_create_opts:
                    mock_opts = MagicMock()
                    mock_create_opts.return_value = mock_opts
                    mock_health.return_value = True

                    result = await main()

                    assert result == 0
                    mock_health.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_run_command(self):
        """Test main function with run command."""
        from sentinel_log_aggregator.cli import main

        with patch("sentinel_log_aggregator.cli.create_parser") as mock_create_parser:
            mock_parser = MagicMock()
            mock_create_parser.return_value = mock_parser

            mock_args = MagicMock()
            mock_args.command = "run"
            mock_args.env_file = None
            mock_args.log_level = "INFO"
            mock_args.config_file = None
            mock_args.workspace_config = "workspaces.yaml"
            mock_args.days_back = 14
            mock_args.batch_hours = 12
            mock_parser.parse_args.return_value = mock_args

            with patch(
                "sentinel_log_aggregator.cli.run_aggregation", new_callable=AsyncMock
            ) as mock_run:
                with patch(
                    "sentinel_log_aggregator.cli.create_client_options_from_args"
                ) as mock_create_opts:
                    with patch(
                        "sentinel_log_aggregator.cli.load_workspace_config", return_value=[]
                    ):
                        mock_opts = MagicMock()
                        mock_opts.days_ago = 7
                        mock_opts.batch_hours = 24
                        mock_create_opts.return_value = mock_opts
                        mock_run.return_value = True

                        result = await main()

                        assert result == 0
                        mock_run.assert_called_once()
                        # Verify that CLI arguments were passed
                        call_args = mock_run.call_args[0]
                        assert call_args[2] == 14  # days_back
                        assert call_args[3] == 12  # batch_hours

    @pytest.mark.asyncio
    async def test_main_validate_command_success(self):
        """Test main function with validate command - success case."""
        from sentinel_log_aggregator.cli import main

        with patch("sentinel_log_aggregator.cli.create_parser") as mock_create_parser:
            mock_parser = MagicMock()
            mock_create_parser.return_value = mock_parser

            mock_args = MagicMock()
            mock_args.command = "validate"
            mock_args.env_file = None
            mock_args.log_level = "INFO"
            mock_args.config_file = None
            mock_args.workspace_config = "workspaces.yaml"
            mock_parser.parse_args.return_value = mock_args

            with patch(
                "sentinel_log_aggregator.cli.create_client_options_from_args"
            ) as mock_create_opts:
                with patch("sentinel_log_aggregator.cli.load_workspace_config") as mock_load_ws:
                    # Mock valid client options
                    mock_opts = MagicMock()
                    mock_opts.validate.return_value = []  # No validation errors
                    mock_create_opts.return_value = mock_opts

                    mock_workspaces = [
                        MagicMock(
                            customer_id="11111111-1111-1111-1111-111111111111",
                            workspace_name="test-ws",
                        )
                    ]
                    mock_load_ws.return_value = mock_workspaces

                    result = await main()

                    assert result == 0  # Success

    @pytest.mark.asyncio
    async def test_main_validate_command_failure(self):
        """Test main function with validate command - validation failure."""
        from sentinel_log_aggregator.cli import main

        with patch("sentinel_log_aggregator.cli.create_parser") as mock_create_parser:
            mock_parser = MagicMock()
            mock_create_parser.return_value = mock_parser

            mock_args = MagicMock()
            mock_args.command = "validate"
            mock_args.env_file = None
            mock_args.log_level = "INFO"
            mock_args.config_file = None
            mock_args.workspace_config = "workspaces.yaml"
            mock_parser.parse_args.return_value = mock_args

            with patch(
                "sentinel_log_aggregator.cli.create_client_options_from_args"
            ) as mock_create_opts:
                with patch("sentinel_log_aggregator.cli.load_workspace_config", return_value=[]):
                    # Mock invalid client options with validation errors
                    mock_opts = MagicMock()
                    mock_opts.validate.return_value = [
                        "Missing required field"
                    ]  # Validation errors
                    mock_create_opts.return_value = mock_opts

                    result = await main()

                    assert result == 1  # Failure due to validation errors

    @pytest.mark.asyncio
    async def test_main_no_command(self):
        """Test main function with no command specified."""
        from sentinel_log_aggregator.cli import main

        with patch("sentinel_log_aggregator.cli.create_parser") as mock_create_parser:
            mock_parser = MagicMock()
            mock_create_parser.return_value = mock_parser

            mock_args = MagicMock()
            mock_args.command = None
            mock_args.env_file = None
            mock_args.log_level = "INFO"
            mock_parser.parse_args.return_value = mock_args

            result = await main()

            assert result == 1
            mock_parser.print_help.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_file_not_found_error(self):
        """Test main function with file not found error during env loading."""
        from sentinel_log_aggregator.cli import main

        with patch("sentinel_log_aggregator.cli.create_parser") as mock_create_parser:
            mock_parser = MagicMock()
            mock_create_parser.return_value = mock_parser

            mock_args = MagicMock()
            mock_args.command = "health"
            mock_args.env_file = "nonexistent.env"
            mock_args.log_level = "INFO"
            mock_parser.parse_args.return_value = mock_args

            with patch("sentinel_log_aggregator.cli.load_environment_variables") as mock_load_env:
                mock_load_env.side_effect = FileNotFoundError("File not found")

                with patch("builtins.print") as mock_print:
                    result = await main()

                    assert result == 1
                    mock_print.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_workspace_config_file_not_found(self):
        """Test main function when workspace config file is not found."""
        from sentinel_log_aggregator.cli import main

        with patch("sentinel_log_aggregator.cli.create_parser") as mock_create_parser:
            mock_parser = MagicMock()
            mock_create_parser.return_value = mock_parser

            mock_args = MagicMock()
            mock_args.command = "run"
            mock_args.env_file = None
            mock_args.log_level = "INFO"
            mock_args.config_file = None
            mock_args.workspace_config = "nonexistent.yaml"
            mock_parser.parse_args.return_value = mock_args

            with patch(
                "sentinel_log_aggregator.cli.create_client_options_from_args"
            ) as mock_create_opts:
                with patch("sentinel_log_aggregator.cli.load_workspace_config") as mock_load_ws:
                    mock_opts = MagicMock()
                    mock_create_opts.return_value = mock_opts
                    mock_load_ws.side_effect = FileNotFoundError("Workspace config not found")

                    result = await main()

                    assert result == 1

    @pytest.mark.asyncio
    async def test_main_unexpected_exception(self):
        """Test main function with unexpected exception."""
        from sentinel_log_aggregator.cli import main

        with patch("sentinel_log_aggregator.cli.create_parser") as mock_create_parser:
            mock_parser = MagicMock()
            mock_create_parser.return_value = mock_parser

            mock_args = MagicMock()
            mock_args.command = "health"
            mock_args.env_file = None
            mock_args.log_level = "INFO"
            mock_args.config_file = None
            mock_parser.parse_args.return_value = mock_args

            with patch(
                "sentinel_log_aggregator.cli.create_client_options_from_args"
            ) as mock_create:
                mock_create.side_effect = Exception("Unexpected error")

                result = await main()

                assert result == 1
