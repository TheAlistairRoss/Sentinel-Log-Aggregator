"""
Command-line interface for Microsoft Sentinel Log Aggregator.

Provides Azure SDK-compliant CLI commands for health checks, workspace management,
and query execution following Azure CLI patterns and conventions.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

# Import Azure SDK-compliant components
from .client_options import SentinelAggregatorClientOptions
from .constants import (
    DEFAULT_BATCH_TIME_SIZE,
    DEFAULT_LOOKBACK_PERIOD,
    DEFAULT_QUERY_TIMEOUT_SECONDS,
    HEALTH_TABLE_NAME,
)
from .health_logger import SentinelAggregatorHealthLogger
from .logging_utils import configure_logging
from .models import WorkspaceConfig
from .query_engine import SentinelQueryEngine
from .sentinel_client import SentinelAggregatorClient
from .version import __version__
from .workspace_manager import WorkspaceManager, load_workspace_config  # noqa: F401 - used by tests


def load_environment_variables(env_file_path: Optional[Path] = None) -> None:
    """
    Load environment variables from .env file with priority handling.

    Args:
        env_file_path: Custom path to .env file, defaults to .env in current directory
    """
    if env_file_path:
        if env_file_path.exists():
            load_dotenv(env_file_path)
        else:
            raise FileNotFoundError(f"Specified .env file not found: {env_file_path}")
    else:
        # Try default .env file in current directory
        default_env = Path(".env")
        if default_env.exists():
            load_dotenv(default_env)


def create_client_options_from_args(args) -> SentinelAggregatorClientOptions:
    """
    Create client options from command line arguments with environment variable fallback.

    Args:
        args: Parsed command line arguments

    Returns:
        SentinelAggregatorClientOptions configured from arguments and environment

    Raises:
        ValueError: If required DCR configuration is missing
    """
    # Get DCR configuration (required)
    dcr_endpoint = args.dcr_endpoint or os.getenv("DCR_LOGS_INGESTION_ENDPOINT")
    dcr_immutable_id = args.dcr_immutable_id or os.getenv("DCR_IMMUTABLE_ID")

    # Validate required DCR configuration
    if not dcr_endpoint:
        raise ValueError(
            "DCR logs ingestion endpoint is required. "
            "Provide via --dcr-endpoint argument or DCR_LOGS_INGESTION_ENDPOINT environment variable."
        )

    if not dcr_immutable_id:
        raise ValueError(
            "DCR immutable ID is required. "
            "Provide via --dcr-immutable-id argument or DCR_IMMUTABLE_ID environment variable."
        )

    # Get time configuration (these may not be present for all subcommands)
    start_time = getattr(args, "start_time", None) or os.getenv("START_TIME")
    end_time = getattr(args, "end_time", None) or os.getenv("END_TIME")
    use_last_successful = (
        getattr(args, "use_last_successful", False)
        or os.getenv("USE_LAST_SUCCESSFUL", "false").lower() == "true"
    )

    # Only set lookback_period if no explicit times are provided
    if start_time or end_time or use_last_successful:
        lookback_period = None
    else:
        lookback_period = getattr(args, "lookback_period", None) or os.getenv(
            "LOOKBACK_PERIOD", DEFAULT_LOOKBACK_PERIOD
        )

    batch_time_size = getattr(args, "batch_time_size", None) or os.getenv(
        "BATCH_TIME_SIZE", DEFAULT_BATCH_TIME_SIZE
    )

    # Get health logging configuration
    health_to_sentinel = (
        getattr(args, "health_to_sentinel", False)
        or os.getenv("HEALTH_TO_SENTINEL", "false").lower() == "true"
    )

    # Get execution control configuration
    queries = getattr(args, "queries", None) or os.getenv("QUERIES")
    workspaces = getattr(args, "workspaces", None) or os.getenv("WORKSPACES")
    dry_run = getattr(args, "dry_run", False) or os.getenv("DRY_RUN", "false").lower() == "true"

    # Handle parallel execution - check both CLI args and environment
    parallel_from_args = getattr(args, "parallel", None)
    parallel_from_env = os.getenv("PARALLEL", "true").lower() == "true"
    parallel = parallel_from_args if parallel_from_args is not None else parallel_from_env

    # Get other optional configuration
    max_concurrent = getattr(args, "max_concurrent_queries", None) or int(
        os.getenv("MAX_CONCURRENT_QUERIES", "5")
    )

    # Create client options
    return SentinelAggregatorClientOptions(
        dcr_logs_ingestion_endpoint=dcr_endpoint,
        dcr_immutable_id=dcr_immutable_id,
        lookback_period=lookback_period,
        batch_time_size=batch_time_size,
        start_time=start_time,
        end_time=end_time,
        use_last_successful=use_last_successful,
        health_to_sentinel=health_to_sentinel,
        queries=queries,
        workspaces=workspaces,
        dry_run=dry_run,
        parallel=parallel,
        max_concurrent_queries=max_concurrent,
        query_timeout_seconds=getattr(args, "query_timeout_seconds", None)
        or int(os.getenv("QUERY_TIMEOUT_SECONDS", str(DEFAULT_QUERY_TIMEOUT_SECONDS))),
        max_retries=getattr(args, "max_retries", None) or int(os.getenv("MAX_RETRIES", "3")),
        retry_delay_seconds=getattr(args, "retry_delay_seconds", None)
        or int(os.getenv("RETRY_DELAY_SECONDS", "5")),
    )


def setup_logging(log_level: str = "INFO", log_format: str = None):
    """Setup logging configuration using enhanced logging utilities."""
    configure_logging(
        level=log_level,
        format_string=log_format,
        enable_structured=False,  # Disable structured logging for CLI to avoid correlation_id issues
    )


async def check_service_health(
    client_options: SentinelAggregatorClientOptions, workspaces: List[WorkspaceConfig]
):
    """Check service health using the Azure SDK-compliant client."""
    logger = logging.getLogger(__name__)

    logger.info("Performing service health check using Azure SDK-compliant client...")

    try:
        # Create Azure SDK-compliant client
        credential = DefaultAzureCredential()
        async with SentinelAggregatorClient(
            dcr_logs_ingestion_endpoint=client_options.dcr_logs_ingestion_endpoint,
            credential=credential,
            options=client_options,
        ) as client:

            # Validate credentials
            logger.info("Validating credentials...")
            await client.validate_credentials()
            logger.info("Credential validation successful")

            # Get service properties with query loading
            logger.info("Retrieving service properties...")

            # Load and validate queries for accurate count
            workspace_manager = WorkspaceManager(workspaces)

            try:
                loaded_queries = await _load_and_validate_queries(workspace_manager)
                service_props = await client.get_service_properties()
                service_props.workspace_count = len(workspaces)
                service_props.available_queries = len(loaded_queries)

                logger.info(
                    f"Loaded and validated {len(loaded_queries)} queries from workspace configurations"
                )

            except Exception as e:
                logger.warning(f"Query loading failed: {e}")
                service_props = await client.get_service_properties()
                service_props.workspace_count = len(workspaces)
                # Keep original available_queries count from AVAILABLE_QUERIES

            # Display service health information
            logger.info("Service Health Report:")
            logger.info(f"-Service Version: {service_props.service_version}")
            logger.info(f"-Connectivity Status: {service_props.connectivity_status}")
            logger.info(f"-Authentication Status: {service_props.authentication_status}")
            logger.info(f"-DCR Endpoint: {service_props.dcr_endpoint}")
            logger.info(f"-DCR Immutable ID: {service_props.dcr_immutable_id}")
            logger.info(f"-Configured Workspaces: {service_props.workspace_count}")
            logger.info(f"-Available Queries: {service_props.available_queries}")
            logger.info(f"-Last Check: {service_props.last_check_time}")

            # Add DCR configuration warning
            aggregation_workspace = workspace_manager.get_aggregation_workspace()
            if aggregation_workspace:
                logger.info(f"-Aggregation Workspace: {aggregation_workspace.workspace_name}")
                logger.info(
                    f"  Please verify that your DCR is configured to send data to workspace: {aggregation_workspace.customer_id}"
                )
            else:
                logger.warning(
                    "No aggregation workspace found! Please set 'aggregation_workspace: true' for one workspace."
                )

            # Test a simple query on the aggregation workspace (if available)
            test_workspace = aggregation_workspace or (workspaces[0] if workspaces else None)
            if test_workspace:
                logger.info(
                    f"Testing query connectivity to workspace {test_workspace.workspace_name}..."
                )

                # Simple test query
                test_query = "print 'Health check test query successful'"

                query_result = await client.query_workspace(
                    workspace_id=test_workspace.customer_id, query=test_query
                )

                if query_result.succeeded:
                    logger.info(
                        f"Test query successful: {query_result.record_count} records in {query_result.execution_time:.2f}s"
                    )
                else:
                    logger.warning(f"Test query failed: {query_result.error_message}")

            return (
                service_props.connectivity_status == "connected"
                and service_props.authentication_status == "valid"
            )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False


def create_health_logger_from_args(
    args,
    client_options: SentinelAggregatorClientOptions,
    workspaces: List[WorkspaceConfig],
    force_enable: bool = False,
    force_to_sentinel: bool = False,
) -> Optional[SentinelAggregatorHealthLogger]:
    """
    Create health logger from CLI arguments if health logging is enabled.

    Args:
        args: CLI arguments
        client_options: Main client options
        workspaces: Available workspaces
        force_enable: Force health logging enabled regardless of args.enable_health_logging
                     (used by test-health command where health logging is mandatory)
        force_to_sentinel: Force health_to_sentinel=True regardless of configuration
                          (used by test-health command to ensure events are sent to Sentinel)

    Returns:
        SentinelAggregatorHealthLogger if enabled, None otherwise
    """
    if not force_enable and not getattr(args, "enable_health_logging", False):
        return None

    logger = logging.getLogger(__name__)

    # Determine health DCR configuration
    health_dcr_endpoint = (
        getattr(args, "health_dcr_endpoint", None) or client_options.dcr_logs_ingestion_endpoint
    )
    health_dcr_immutable_id = (
        getattr(args, "health_dcr_immutable_id", None) or client_options.dcr_immutable_id
    )

    # Get health to sentinel flag - force to True if force_to_sentinel is set
    # BUT always disable for dry-run mode (no uploads should occur in dry-run)
    health_to_sentinel = (
        force_to_sentinel
        or getattr(args, "health_to_sentinel", False)
        or client_options.health_to_sentinel
    )

    # Override: disable health uploads in dry-run mode
    if client_options.dry_run:
        health_to_sentinel = False
        logger.info("Dry-run mode: Health logs will be shown in console only (not uploaded)")

    # Create health client options with health-specific DCR settings
    health_client_options = SentinelAggregatorClientOptions(
        dcr_logs_ingestion_endpoint=health_dcr_endpoint,
        dcr_immutable_id=health_dcr_immutable_id,
        # Copy other settings from main options
        lookback_period=client_options.lookback_period,
        batch_time_size=client_options.batch_time_size,
        start_time=client_options.start_time,
        end_time=client_options.end_time,
        use_last_successful=client_options.use_last_successful,
        health_to_sentinel=health_to_sentinel,
        max_concurrent_queries=client_options.max_concurrent_queries,
        query_timeout_seconds=client_options.query_timeout_seconds,
        max_retries=client_options.max_retries,
        retry_delay_seconds=client_options.retry_delay_seconds,
    )

    # Import here to avoid circular import issues
    from azure.identity.aio import DefaultAzureCredential

    from .sentinel_client import SentinelAggregatorClient

    # Create sentinel client for health logging
    credential = DefaultAzureCredential()
    health_client = SentinelAggregatorClient(
        dcr_logs_ingestion_endpoint=health_dcr_endpoint,
        credential=credential,
        options=health_client_options,
    )

    try:
        health_logger = SentinelAggregatorHealthLogger(
            sentinel_client=health_client, enabled=True, health_to_sentinel=health_to_sentinel
        )

        health_mode = "Sentinel table" if health_to_sentinel else "console only"
        logger.info(f"Health logging enabled - mode: {health_mode}")
        return health_logger

    except Exception as e:
        logger.error(f"Failed to create health logger: {e}")
        logger.debug("Health logger creation error details", exc_info=True)
        return None


async def run_aggregation(
    client_options: SentinelAggregatorClientOptions,
    workspaces: List[WorkspaceConfig],
    health_logger: Optional[SentinelAggregatorHealthLogger] = None,
):
    """Run the log aggregation process using Azure SDK-compliant components."""
    logger = logging.getLogger(__name__)

    # Validate configuration
    config_errors = client_options.validate()
    if config_errors:
        logger.error("Configuration validation failed:")
        for error in config_errors:
            logger.error(f"-{error}")
        return False

    # Validate time configuration
    from .time_range_calculator import validate_time_configuration

    time_errors = validate_time_configuration(client_options)
    if time_errors:
        logger.error("Time configuration validation failed:")
        for error in time_errors:
            logger.error(f"-{error}")
        return False

    logger.info("Starting log aggregation process...")
    logger.info(f"-Lookback period: {client_options.lookback_period}")
    logger.info(f"-Batch time size: {client_options.batch_time_size}")
    logger.info(f"-Max concurrent queries: {client_options.max_concurrent_queries}")
    logger.info(f"-Workspaces: {len(workspaces)}")
    if health_logger:
        logger.info("-Health logging: Enabled")
    else:
        logger.info("-Health logging: Disabled")

    # Generate job ID for health logging
    job_id = health_logger.create_job_id() if health_logger else "cli-job"

    # Create Azure SDK-compliant credential (will be closed in finally block)
    credential = DefaultAzureCredential()

    try:
        # Log job start if health logging is enabled
        if health_logger:
            await health_logger.log_job_start(
                job_id=job_id,
                job_type="cli_batch_execution",
                workspace_count=len(workspaces),
                query_count=0,  # Will be updated by query engine
                cli_args={
                    "lookback_period": client_options.lookback_period,
                    "batch_time_size": client_options.batch_time_size,
                    "max_concurrent_queries": client_options.max_concurrent_queries,
                    "start_time": client_options.start_time,
                    "end_time": client_options.end_time,
                    "use_last_successful": client_options.use_last_successful,
                },
            )

        # Create Azure SDK-compliant client with context manager
        async with SentinelAggregatorClient(
            dcr_logs_ingestion_endpoint=client_options.dcr_logs_ingestion_endpoint,
            credential=credential,
            options=client_options,
        ) as client:

            # Use the high-level query engine for batch processing with shared job_id
            query_engine = SentinelQueryEngine(
                client_options, client, job_id=job_id, health_logger=health_logger
            )

            # Execute batch queries with streaming upload
            summary = await query_engine.execute_batch_queries_with_streaming_upload(
                workspaces, job_id=job_id
            )

            # Log job end if health logging is enabled
            if health_logger:
                await health_logger.log_job_end(
                    job_id=job_id,
                    job_type="cli_batch_execution",
                    success=(summary.failed_queries == 0),
                    total_records_processed=summary.total_uploaded_records,
                    total_duration_seconds=summary.total_duration_seconds,
                )

            # Display brief summary - detailed analysis available in logs
            detailed_summary = summary.generate_detailed_summary()

            logger.info("Execution Summary:")
            logger.info("=" * 50)

            # Overview section
            overview = detailed_summary["overview"]
            logger.info("Results:")
            logger.info(f"-Time Range: {overview['total_time_range']}")
            logger.info(f"-Total Duration: {overview['total_duration_seconds']:.2f}s")
            logger.info(f"-Workspaces: {overview['total_workspaces']}")
            logger.info(f"-Unique Queries: {overview['total_unique_queries']}")
            logger.info(f"-Records Downloaded: {overview['total_records_downloaded']:,}")
            logger.info(f"-Records Uploaded: {overview['total_records_uploaded']:,}")
            logger.info("Note: Detailed workspace/query analytics available in logs above")

            return summary.failed_queries == 0

    except Exception as e:
        logger.error(f"Aggregation failed: {e}")

        # Log error to health logger if available
        if health_logger:
            try:
                await health_logger.log_job_end(
                    job_id=job_id,
                    job_type="cli_batch_execution",
                    success=False,
                    error_message=str(e),
                )
            except Exception as health_error:
                logger.debug(f"Failed to log error to health logger: {health_error}")

        return False

    finally:
        # Clean up Azure resources
        try:
            # Close health logger's client session if it exists
            if health_logger and health_logger.sentinel_client:
                await health_logger.sentinel_client.close()
                logger.debug("Health logger client session closed")

            # Close credential
            await credential.close()
            logger.debug("Credential closed")
        except Exception as cleanup_error:
            logger.debug(f"Error during cleanup: {cleanup_error}")


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Microsoft Sentinel Log Aggregator - Azure SDK Compliant CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using command line arguments with time ranges (NOTE: --end-time is INCLUSIVE)
  # Query data from October 1st through October 31st (entire month)
  sentinel-aggregator run --workspace-config workspaces.yaml \\
    --dcr-endpoint "https://myworkspace-abcd.centralus-1.ingest.monitor.azure.com" \\
    --dcr-immutable-id "dcr-12345678901234567890" \\
    --start-time "2025-10-01T00:00:00Z" --end-time "2025-10-31T23:59:59.999999Z"

  # Using lookback period with custom batch size
  sentinel-aggregator run --workspace-config workspaces.yaml \\
    --lookback-period "P7D" --batch-time-size "PT12H"

  # Using last successful timestamps (automatically continues from last run)
  sentinel-aggregator run --workspace-config workspaces.yaml \\
    --use-last-successful --batch-time-size "PT6H"

  # Health logging to Sentinel table
  sentinel-aggregator run --workspace-config workspaces.yaml \\
    --enable-health-logging --health-to-sentinel

  # Query last successful runs
  sentinel-aggregator query-status --workspace-config workspaces.yaml \\
    --lookback-period "P14D" --query-names "incident_summary,alert_summary"

  # Health check with custom DCR configuration
  sentinel-aggregator health --workspace-config workspaces.yaml \\
    --dcr-endpoint "https://myworkspace-abcd.centralus-1.ingest.monitor.azure.com" \\
    --dcr-immutable-id "dcr-12345678901234567890"

  # Validate configuration with debug logging
  sentinel-aggregator --log-level DEBUG validate --workspace-config workspaces.yaml

IMPORTANT: --end-time is INCLUSIVE. To query an entire month, use:
  --start-time "2025-10-01T00:00:00Z" --end-time "2025-10-31T23:59:59.999999Z"
  This includes all data up to and including the last microsecond of October 31st.
        """,
    )

    parser.add_argument(
        "--version", action="version", version=f"Microsoft Sentinel Log Aggregator {__version__}"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level (default: INFO)",
    )

    parser.add_argument(
        "--env-file", type=Path, help="Path to .env file (default: .env in current directory)"
    )

    # Required Azure DCR configuration (global)
    parser.add_argument(
        "--dcr-endpoint", help="Azure Monitor Data Collection Rule logs ingestion endpoint"
    )

    parser.add_argument(
        "--dcr-immutable-id", help="Azure Monitor Data Collection Rule immutable ID"
    )

    parser.add_argument(
        "--config-file",
        type=Path,
        help="Path to YAML configuration file (optional, uses environment variables if not provided)",
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Health check command
    health_parser = subparsers.add_parser(
        "health",
        help="Perform service health check",
        description="Check connectivity, authentication, and service status",
    )
    health_parser.add_argument(
        "--workspace-config",
        type=Path,
        required=True,
        help="Path to workspace configuration file (YAML format)",
    )

    # Run aggregation command
    run_parser = subparsers.add_parser(
        "run",
        help="Run log aggregation process",
        description="Execute batch queries and upload results to Azure Monitor",
    )
    run_parser.add_argument(
        "--workspace-config",
        type=Path,
        required=True,
        help="Path to workspace configuration file (YAML format)",
    )

    # Optional query settings for run command - Time specifications
    time_group = run_parser.add_mutually_exclusive_group()

    time_group.add_argument(
        "--lookback-period",
        help="ISO 8601 duration for how far back to query (e.g., P7D, PT48H) - default: P30D",
    )

    time_group.add_argument(
        "--start-time", help="Explicit start time in ISO 8601 format (e.g., 2025-10-01T17:00:00Z)"
    )

    run_parser.add_argument(
        "--end-time",
        help="Explicit end time in ISO 8601 format (INCLUSIVE - includes data up to this timestamp). "
        "Defaults to now if start-time provided. Use microsecond precision for exact boundaries: "
        "2025-10-31T23:59:59.999999Z includes all of October 31st",
    )

    run_parser.add_argument(
        "--batch-time-size",
        help="ISO 8601 duration for batch size, multiple of 1 hour (e.g., PT24H, PT12H) - default: PT24H",
    )

    run_parser.add_argument(
        "--use-last-successful",
        action="store_true",
        help="Use last successful run timestamps from health table",
    )

    run_parser.add_argument(
        "--max-concurrent-queries", type=int, help="Maximum concurrent queries (default: 5)"
    )

    run_parser.add_argument(
        "--query-timeout-seconds",
        type=int,
        help=f"Query timeout in seconds (default: {DEFAULT_QUERY_TIMEOUT_SECONDS})",
    )

    run_parser.add_argument(
        "--max-retries", type=int, help="Maximum retry attempts for failed operations (default: 3)"
    )

    run_parser.add_argument(
        "--retry-delay-seconds", type=int, help="Delay between retries in seconds (default: 5)"
    )

    # Execution control options for run command
    run_parser.add_argument("--queries", help="Specific queries to run (comma-separated)")

    run_parser.add_argument("--workspaces", help="Specific workspaces to process (comma-separated)")

    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and show what would be executed (default: false)",
    )

    parallel_group = run_parser.add_mutually_exclusive_group()
    parallel_group.add_argument(
        "--parallel",
        action="store_true",
        dest="parallel",
        help="Enable parallel execution (default: true)",
    )
    parallel_group.add_argument(
        "--no-parallel", action="store_false", dest="parallel", help="Disable parallel execution"
    )

    # Health logging options for run command
    run_parser.add_argument(
        "--enable-health-logging", action="store_true", help="Enable health logging"
    )

    run_parser.add_argument(
        "--health-to-sentinel",
        action="store_true",
        help="Send health logs to Sentinel table (otherwise console only)",
    )

    run_parser.add_argument(
        "--health-workspace-id",
        help="Workspace ID for health logging (if different from data workspaces)",
    )

    run_parser.add_argument(
        "--health-dcr-endpoint", help="DCR endpoint for health logging (if different from main DCR)"
    )

    run_parser.add_argument(
        "--health-dcr-immutable-id",
        help="DCR immutable ID for health logging (if different from main DCR)",
    )

    # Validate configuration command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate configuration",
        description="Validate client options and workspace configuration",
    )
    validate_parser.add_argument(
        "--workspace-config",
        type=Path,
        required=True,
        help="Path to workspace configuration file (YAML format)",
    )

    # Verify health logging setup command
    verify_health_parser = subparsers.add_parser(
        "verify-health",
        help="Verify health logging setup",
        description="Check if health logging table and DCR are properly configured",
    )
    verify_health_parser.add_argument(
        "--workspace-config",
        type=Path,
        required=True,
        help="Path to workspace configuration file (YAML format)",
    )
    verify_health_parser.add_argument(
        "--health-workspace-id",
        help="Workspace ID for health logging (if different from first data workspace)",
    )
    verify_health_parser.add_argument(
        "--health-dcr-endpoint", help="DCR endpoint for health logging (if different from main DCR)"
    )
    verify_health_parser.add_argument(
        "--health-dcr-immutable-id",
        help="DCR immutable ID for health logging (if different from main DCR)",
    )

    # Query status command
    query_status_parser = subparsers.add_parser(
        "query-status",
        help="Query last successful run status",
        description="Check the last successful runs for queries from health table",
    )
    query_status_parser.add_argument(
        "--workspace-config",
        type=Path,
        required=True,
        help="Path to workspace configuration file (YAML format)",
    )
    query_status_parser.add_argument(
        "--lookback-period",
        default=DEFAULT_LOOKBACK_PERIOD,
        help=f"ISO 8601 duration for how far back to search (default: {DEFAULT_LOOKBACK_PERIOD})",
    )
    query_status_parser.add_argument(
        "--query-names", help="Comma-separated list of query names to filter (optional)"
    )
    query_status_parser.add_argument(
        "--health-workspace-id",
        help="Workspace ID where health table is located (if different from first data workspace)",
    )
    query_status_parser.add_argument(
        "--health-dcr-endpoint", help="DCR endpoint for health logging (if different from main DCR)"
    )
    query_status_parser.add_argument(
        "--health-dcr-immutable-id",
        help="DCR immutable ID for health logging (if different from main DCR)",
    )

    # Test health command
    test_health_parser = subparsers.add_parser(
        "test-health",
        help="Send test health event and optionally verify ingestion",
        description="Send a test event to health logging table and optionally verify it was ingested",
    )
    test_health_parser.add_argument(
        "--workspace-config",
        type=Path,
        required=True,
        help="Path to workspace configuration file (YAML format)",
    )
    test_health_parser.add_argument(
        "--test-id", help="Custom test identifier (auto-generated if not provided)"
    )
    test_health_parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify that the test event was ingested after sending",
    )
    test_health_parser.add_argument(
        "--max-wait",
        type=int,
        default=300,
        help="Maximum seconds to wait for verification (default: 300)",
    )
    test_health_parser.add_argument(
        "--health-workspace-id",
        help="Workspace ID where health table is located (if different from first data workspace)",
    )
    test_health_parser.add_argument(
        "--health-dcr-endpoint", help="DCR endpoint for health logging (if different from main DCR)"
    )
    test_health_parser.add_argument(
        "--health-dcr-immutable-id",
        help="DCR immutable ID for health logging (if different from main DCR)",
    )

    return parser


async def test_health_logging(
    args, client_options: SentinelAggregatorClientOptions, workspaces: List[WorkspaceConfig]
) -> bool:
    """
    Send a test health event and optionally verify ingestion.

    Args:
        args: CLI arguments
        client_options: Client configuration options
        workspaces: Available workspace configurations

    Returns:
        bool: True if test succeeded, False otherwise
    """
    logger = logging.getLogger(__name__)

    logger.info("Testing health logging...")

    health_logger = None
    try:
        # Create health logger with force_enable=True and force_to_sentinel=True
        # since test-health command is specifically for testing Sentinel ingestion
        health_logger = create_health_logger_from_args(
            args, client_options, workspaces, force_enable=True, force_to_sentinel=True
        )

        if not health_logger:
            logger.error("Failed to create health logger")
            logger.info("Check DCR configuration (--dcr-endpoint and --dcr-immutable-id)")
            return False

        # Send test event
        logger.info("Sending test health event...")
        send_result = await health_logger.send_test_event(test_id=args.test_id)

        if not send_result["success"]:
            logger.error(f"{send_result['message']}")
            return False

        if send_result.get("warning"):
            logger.warning(f"{send_result['message']}")
            if send_result.get("console_only"):
                logger.info("To send health logs to Sentinel, configure DCR settings:")
                logger.info(
                    " -Set --dcr-endpoint (e.g., https://your-dcr.ingest.monitor.azure.com)"
                )
                logger.info(" -Set --dcr-immutable-id (Data Collection Rule ID)")
                logger.info(
                    " -Or set environment variables: DCR_LOGS_INGESTION_ENDPOINT and DCR_IMMUTABLE_ID"
                )
            return True

        logger.info(f"{send_result['message']}")
        test_id = send_result["test_id"]

        log_output = {
            "Test ID": test_id,
            "Stream Name": send_result.get("stream_name", "N/A"),
            "Data Collection Rule Endpoint": send_result.get("dcr_endpoint", ""),
            "Data Collection Rule Immutable Id": send_result.get("dcr_immutable_id", ""),
            "Log Records": send_result.get("log_record", {}),
        }

        logger.info("Log Record Sent:")
        logger.info(json.dumps(log_output, indent=4))

        # Verify if requested
        if args.verify:
            # Determine workspace ID - use aggregation workspace
            verify_workspace_id = args.health_workspace_id
            if not verify_workspace_id and workspaces:
                from .workspace_manager import WorkspaceManager

                workspace_manager = WorkspaceManager(workspaces)
                aggregation_workspace = workspace_manager.get_aggregation_workspace()
                if aggregation_workspace:
                    verify_workspace_id = aggregation_workspace.customer_id
                    logger.info(
                        f"Using aggregation workspace for verification: {aggregation_workspace.workspace_name}"
                    )
                else:
                    logger.warning(
                        "No aggregation workspace found, health table may not be available"
                    )
                    return False

            if not verify_workspace_id:
                logger.error("No workspace available for verification")
                return False

            logger.info(f"Verifying test event ingestion (max wait: {args.max_wait} seconds)...")
            verify_result = await health_logger.verify_test_event(
                test_id=test_id,
                workspace_id=verify_workspace_id,
                max_wait_seconds=args.max_wait,
            )

            logger.info("Verification Results:")
            logger.info("=" * 50)
            logger.info(f"-Test ID: {verify_result['test_id']}")
            logger.info(f"-Found: {'' if verify_result['found'] else ''}")
            logger.info(f"-Message: {verify_result['message']}")
            if verify_result.get("ingestion_delay_seconds") is not None:
                logger.info(f"-Ingestion Delay: {verify_result['ingestion_delay_seconds']} seconds")
            logger.info("=" * 50)

            return verify_result["found"]
        else:
            logger.info("Manual Verification:")
            logger.info(
                f"Run this query against your aggregation workspace: {HEALTH_TABLE_NAME} | where JobId == '{test_id}' | where OperationName == 'HealthTest'"
            )
            return True

    except Exception as e:
        logger.error(f"Health test failed: {e}", exc_info=True)
        return False
    finally:
        # Clean up health logger resources
        if health_logger and health_logger.sentinel_client:
            try:
                await health_logger.sentinel_client.close()
            except Exception as cleanup_error:
                logger.debug(f"Error closing health logger client: {cleanup_error}")


async def verify_health_logging_setup(
    args, client_options: SentinelAggregatorClientOptions, workspaces: List[WorkspaceConfig]
) -> bool:
    """
    Verify that health logging infrastructure is properly set up.

    Args:
        args: CLI arguments
        client_options: Client configuration options
        workspaces: Available workspace configurations

    Returns:
        bool: True if health logging is properly configured, False otherwise
    """
    logger = logging.getLogger(__name__)

    logger.info("Verifying health logging setup...")

    health_logger = None
    try:
        # Create health logger with force_enable=True since verification requires health logging
        health_logger = create_health_logger_from_args(
            args, client_options, workspaces, force_enable=True
        )

        if not health_logger:
            logger.error("Failed to create health logger")
            logger.info("Check DCR configuration (--dcr-endpoint and --dcr-immutable-id)")
            return False

        # Determine which workspace to test against - use aggregation workspace
        test_workspace_id = args.health_workspace_id
        if not test_workspace_id and workspaces:
            from .workspace_manager import WorkspaceManager

            workspace_manager = WorkspaceManager(workspaces)
            aggregation_workspace = workspace_manager.get_aggregation_workspace()
            if aggregation_workspace:
                test_workspace_id = aggregation_workspace.customer_id
                logger.info(
                    f"Using aggregation workspace for testing: {aggregation_workspace.workspace_name}"
                )
            else:
                logger.warning("No aggregation workspace found, health table may not be available")
                return False

        if not test_workspace_id:
            logger.error("No workspace available for health logging verification")
            return False

        # Verify health logging setup
        verification_result = await health_logger.verify_health_table_setup(test_workspace_id)

        logger.info("Health Logging Verification Results:")
        logger.info("=" * 50)
        logger.info(f"-Enabled: {'' if verification_result['enabled'] else ''}")
        logger.info(f"-Table Exists: {'' if verification_result['table_exists'] else ''}")
        logger.info(f"-DCR Accessible: {'' if verification_result['dcr_accessible'] else ''}")
        logger.info(f"-Status: {verification_result['message']}")

        if (
            verification_result["enabled"]
            and verification_result["table_exists"]
            and verification_result["dcr_accessible"]
        ):
            logger.info("Health logging is fully operational!")
            return True
        elif verification_result["enabled"] and verification_result["table_exists"]:
            logger.warning("Health table exists but DCR access failed")
            logger.info("Check DCR configuration and permissions")
            return False
        elif verification_result["enabled"]:
            logger.error("Health logging enabled but table not found")
            logger.info("Deploy the health logging infrastructure using:")
            logger.info("   az deployment group create \\")
            logger.info("     --resource-group <your-rg> \\")
            logger.info("     --template-file Templates/main.bicep \\")
            logger.info("     --parameters workspaceName=<your-workspace>")
            return False
        else:
            logger.info("Health logging is disabled")
            return True

    except Exception as e:
        logger.error(f"Health logging verification failed: {e}")
        logger.debug("Verification error details", exc_info=True)
        return False
    finally:
        # Clean up health logger resources
        if health_logger and health_logger.sentinel_client:
            try:
                await health_logger.sentinel_client.close()
            except Exception as cleanup_error:
                logger.debug(f"Error closing health logger client: {cleanup_error}")


async def query_last_successful_runs(
    args, client_options: SentinelAggregatorClientOptions, workspaces: List[WorkspaceConfig]
) -> bool:
    """
    Query last successful runs from health table and display results.

    Args:
        args: CLI arguments
        client_options: Client configuration options
        workspaces: Available workspace configurations

    Returns:
        bool: True if query was successful, False otherwise
    """
    logger = logging.getLogger(__name__)

    logger.info("Querying last successful runs...")

    health_logger = None
    try:
        # Create health logger with force_enable=True since querying requires health logging
        health_logger = create_health_logger_from_args(
            args, client_options, workspaces, force_enable=True
        )

        if not health_logger:
            logger.error("Failed to create health logger")
            logger.info("Check DCR configuration (--dcr-endpoint and --dcr-immutable-id)")
            return False

        # Determine workspace to query against - use aggregation workspace
        health_workspace_id = getattr(args, "health_workspace_id", None)
        if not health_workspace_id and workspaces:
            from .workspace_manager import WorkspaceManager

            workspace_manager = WorkspaceManager(workspaces)
            aggregation_workspace = workspace_manager.get_aggregation_workspace()
            if aggregation_workspace:
                health_workspace_id = aggregation_workspace.customer_id
                logger.debug(
                    f"Using aggregation workspace for health queries: {aggregation_workspace.workspace_name}"
                )
            else:
                logger.warning("No aggregation workspace found, health table may not be available")
                return False

        if not health_workspace_id:
            logger.error("No workspace available for health table queries")
            return False

        # Parse query filter if provided
        query_names_filter = None
        if hasattr(args, "query_names") and args.query_names:
            query_names_filter = [name.strip() for name in args.query_names.split(",")]
            logger.debug(f"Filtering by query names: {query_names_filter}")

        # Get lookback period
        lookback_period = getattr(args, "lookback_period", "P30D")

        # Import time utilities
        from .time_utils import calculate_time_range_from_lookback, format_datetime_for_display

        # Calculate time range
        start_time, end_time = calculate_time_range_from_lookback(lookback_period)

        logger.info(
            f"Searching for successful runs from {format_datetime_for_display(start_time)} to {format_datetime_for_display(end_time)}"
        )

        # Import time range calculator to use common health query function
        from .time_range_calculator import _query_all_last_successful_runs
        from .workspace_manager import WorkspaceManager

        # Get workspaces for the common query function
        workspace_manager = WorkspaceManager.from_file(args.workspace_config)
        workspaces_list = list(workspace_manager.workspaces)

        # Query health table using common function
        results_map = await _query_all_last_successful_runs(
            health_logger, workspaces_list, lookback_days=30
        )

        # Convert results_map to list format for display
        # Filter by query names if specified
        successful_runs = []
        for (query_name, workspace_id), result in results_map.items():
            # Apply query name filter if provided
            if query_names_filter and query_name not in query_names_filter:
                continue

            # Convert result dict to expected format for display
            successful_runs.append(
                {
                    "QueryName": query_name,
                    "WorkspaceId": workspace_id,
                    "StartTime": result.get("StartTime", result.get("start_time")),
                    "EndTime": result.get("EndTime", result.get("end_time")),
                    "RecordCount": result.get("RecordCount", result.get("record_count")),
                    "LastRunTime": result.get("LastRunTime", result.get("last_run_time")),
                }
            )

        # Sort by QueryName and WorkspaceId
        successful_runs.sort(key=lambda x: (x["QueryName"], x["WorkspaceId"]))

        if not successful_runs:
            logger.warning("No successful runs found in the specified time period")
            return True

        # Display results in table format
        _display_successful_runs_table(successful_runs)

        logger.info(f"Found {len(successful_runs)} successful run(s)")
        return True

    except Exception as e:
        logger.error(f"Failed to query last successful runs: {e}")
        logger.debug("Query error details", exc_info=True)
        return False
    finally:
        # Clean up health logger resources
        if health_logger and health_logger.sentinel_client:
            try:
                await health_logger.sentinel_client.close()
            except Exception as cleanup_error:
                logger.debug(f"Error closing health logger client: {cleanup_error}")


def _display_successful_runs_table(runs: List[Dict[str, Any]]) -> None:
    """
    Display successful runs in table format.

    Args:
        runs: List of successful run records
    """
    if not runs:
        return

    from .time_utils import format_datetime_for_display

    logger = logging.getLogger(__name__)

    # Calculate column widths
    max_query_name = max(len(run.get("QueryName", "")) for run in runs)
    max_workspace_id = min(max(len(str(run.get("WorkspaceId", ""))[:12]) for run in runs), 12)

    # Table headers
    headers = [
        "Query Name".ljust(max_query_name),
        "Workspace ID".ljust(max_workspace_id),
        "Start Time".ljust(20),
        "End Time".ljust(20),
        "Records".rjust(10),
    ]

    # Print table header
    header_line = " | ".join(headers)
    separator_line = "-" * len(header_line)

    logger.info("Last Successful Runs:")
    logger.info(separator_line)
    logger.info(header_line)
    logger.info(separator_line)

    # Print table rows
    for run in runs:
        query_name = str(run.get("QueryName", "")).ljust(max_query_name)
        workspace_id = str(run.get("WorkspaceId", ""))[:12].ljust(max_workspace_id)

        # Format times for display
        start_time = run.get("StartTime")
        end_time = run.get("EndTime")

        if isinstance(start_time, str):
            start_str = start_time[:19] if len(start_time) >= 19 else start_time
        else:
            start_str = format_datetime_for_display(start_time, local_timezone=True)[:19]

        if isinstance(end_time, str):
            end_str = end_time[:19] if len(end_time) >= 19 else end_time
        else:
            end_str = format_datetime_for_display(end_time, local_timezone=True)[:19]

        start_str = start_str.ljust(20)
        end_str = end_str.ljust(20)

        record_count = str(run.get("RecordCount", 0)).rjust(10)

        row = " | ".join([query_name, workspace_id, start_str, end_str, record_count])
        logger.info(row)

    logger.info(separator_line)


async def _load_and_validate_queries(workspace_manager) -> Dict[str, Any]:
    """
    Load and validate all queries from workspace configurations without executing them.

    Args:
        workspace_manager: WorkspaceManager instance with configured workspaces

    Returns:
        Dictionary of successfully loaded queries keyed by query name or file path

    Raises:
        Exception: If critical query loading errors occur
    """
    from pathlib import Path

    from .models import KQLQueryDefinition

    loaded_queries = {}
    logger = logging.getLogger(__name__)

    # Get all unique query references from all workspaces
    all_query_refs = set()
    for workspace in workspace_manager.workspaces:
        all_query_refs.update(workspace.queries_list)

    logger.debug(f"Found {len(all_query_refs)} unique query references across all workspaces")

    for query_ref in all_query_refs:
        try:
            # Check if it's a file path (contains / or .yaml/.yml extension)
            if "/" in query_ref or query_ref.endswith((".yaml", ".yml")):
                # It's a file path - try to load from file
                query_file_path = Path(query_ref)

                # If it's relative, assume it's relative to current working directory
                if not query_file_path.is_absolute():
                    query_file_path = Path.cwd() / query_file_path

                if query_file_path.exists():
                    # Load the query definition from YAML file
                    query_def = KQLQueryDefinition.from_yaml(str(query_file_path))
                    loaded_queries[query_ref] = {
                        "type": "file",
                        "path": str(query_file_path),
                        "name": query_def.name,
                        "destination_stream": query_def.destination_stream,
                        "description": query_def.description,
                        "parameters": list(query_def.parameters.keys()),
                    }
                    logger.debug(f"Loaded query from file: {query_ref}")
                else:
                    logger.warning(f"Query file not found: {query_file_path}")
                    loaded_queries[query_ref] = {
                        "type": "file",
                        "path": str(query_file_path),
                        "error": "File not found",
                    }
            else:
                # It's a query name - check if it exists in AVAILABLE_QUERIES
                from .models import AVAILABLE_QUERIES

                if query_ref in AVAILABLE_QUERIES:
                    query_def = AVAILABLE_QUERIES[query_ref]
                    loaded_queries[query_ref] = {
                        "type": "builtin",
                        "name": query_def.name,
                        "destination_stream": query_def.destination_stream,
                        "description": query_def.description,
                        "parameters": list(query_def.parameters.keys()),
                    }
                    logger.debug(f"Found built-in query: {query_ref}")
                else:
                    logger.warning(f"Built-in query not found: {query_ref}")
                    loaded_queries[query_ref] = {
                        "type": "builtin",
                        "name": query_ref,
                        "error": "Query not found in AVAILABLE_QUERIES",
                    }

        except Exception as e:
            logger.warning(f"Failed to load query '{query_ref}': {e}")
            loaded_queries[query_ref] = {"type": "unknown", "error": str(e)}

    # Count successful loads
    successful_loads = sum(1 for q in loaded_queries.values() if "error" not in q)
    total_queries = len(loaded_queries)

    if successful_loads < total_queries:
        logger.warning(f"Loaded {successful_loads}/{total_queries} queries successfully")

    return loaded_queries


async def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Load environment variables from .env file
    try:
        load_environment_variables(args.env_file)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # If no command specified, show help
    if not args.command:
        parser.print_help()
        return 1

    try:
        # Create client options from arguments and environment
        client_options = None
        if args.command != "validate":
            # Only require DCR configuration for non-validation commands
            if args.config_file:
                logger.debug(f"Loading configuration from file: {args.config_file}")
                client_options = SentinelAggregatorClientOptions.from_yaml_file(args.config_file)
            else:
                logger.debug("Creating configuration from arguments and environment variables")
                client_options = create_client_options_from_args(args)
        else:
            # For validation, try to create client options but don't fail if DCR config is missing
            try:
                if args.config_file:
                    logger.debug(f"Loading configuration from file: {args.config_file}")
                    client_options = SentinelAggregatorClientOptions.from_yaml_file(
                        args.config_file
                    )
                else:
                    logger.debug("Creating configuration from arguments and environment variables")
                    client_options = create_client_options_from_args(args)
            except ValueError as e:
                if "DCR" in str(e):
                    logger.debug(
                        "DCR configuration not provided for validation - will validate workspace config only"
                    )
                    client_options = None
                else:
                    raise

        # Load workspace configuration if required
        workspaces = []
        workspace_manager = None
        if hasattr(args, "workspace_config") and args.workspace_config:
            workspace_manager = WorkspaceManager.from_file(args.workspace_config)
            # Only try to get workspaces if validation was successful
            if workspace_manager and not workspace_manager.has_validation_errors():
                workspaces = workspace_manager.workspaces

        # Execute the appropriate command
        success = True

        if args.command == "health":
            success = await check_service_health(client_options, workspaces)

        elif args.command == "run":
            # Create health logger if enabled
            health_logger = create_health_logger_from_args(args, client_options, workspaces)

            success = await run_aggregation(client_options, workspaces, health_logger)

        elif args.command == "verify-health":
            success = await verify_health_logging_setup(args, client_options, workspaces)

        elif args.command == "test-health":
            success = await test_health_logging(args, client_options, workspaces)

        elif args.command == "query-status":
            success = await query_last_successful_runs(args, client_options, workspaces)

        elif args.command == "validate":
            logger.info("Validating configuration...")

            # Validate client options if available
            if client_options:
                config_errors = client_options.validate()
                if config_errors:
                    logger.error("Client options validation failed:")
                    for error in config_errors:
                        logger.error(f"-{error}")
                    success = False
                else:
                    logger.info("Client options validation successful")
            else:
                logger.info("Client configuration not provided - skipping client validation")

            # Validate workspace configuration
            if workspace_manager:
                # Check for validation errors first
                if workspace_manager.has_validation_errors():
                    logger.error("Workspace configuration validation failed:")
                    for error in workspace_manager.get_validation_errors():
                        logger.error(f"-{error}")
                    success = False
                else:
                    logger.info("Workspace configuration validation successful")

                # Show workspace summary regardless of validation status
                if workspaces:
                    logger.info(f"Loaded {len(workspaces)} workspaces:")
                    for i, workspace in enumerate(workspaces, 1):
                        logger.info(
                            f"-Workspace {i}: {workspace.workspace_name} (ID: {workspace.customer_id})"
                        )
                else:
                    logger.warning("No workspaces found in configuration")
            else:
                logger.warning("No workspace configuration provided")

        return 0 if success else 1

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug("Full traceback:", exc_info=True)
        return 1


def cli_main():
    """Synchronous entry point for the CLI."""
    try:
        return asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130  # Standard exit code for SIGINT


if __name__ == "__main__":
    sys.exit(cli_main())
