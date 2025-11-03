"""
Command-line interface for Microsoft Sentinel Log Aggregator.

Provides Azure SDK-compliant CLI commands for health checks, workspace management,
and query execution following Azure CLI patterns and conventions.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

from azure.core.exceptions import AzureError
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

# Import Azure SDK-compliant components
from .client_options import SentinelAggregatorClientOptions
from .logging_utils import configure_logging
from .models import WorkspaceConfig
from .query_engine import SentinelQueryEngine
from .sentinel_client import SentinelAggregatorClient
from .version import __version__
from .workspace_manager import WorkspaceManager, load_workspace_config


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
    dcr_rule_id = args.dcr_rule_id or os.getenv("DCR_RULE_ID")

    # Validate required DCR configuration
    if not dcr_endpoint:
        raise ValueError(
            "DCR logs ingestion endpoint is required. "
            "Provide via --dcr-endpoint argument or DCR_LOGS_INGESTION_ENDPOINT environment variable."
        )

    if not dcr_rule_id:
        raise ValueError(
            "DCR rule ID is required. "
            "Provide via --dcr-rule-id argument or DCR_RULE_ID environment variable."
        )

    # Get optional configuration with defaults (these may not be present for all subcommands)
    days_back = getattr(args, 'days_back', None) or int(os.getenv("DAYS_AGO", "30"))
    batch_hours = getattr(args, 'batch_hours', None) or int(os.getenv("BATCH_HOURS", "24"))
    max_concurrent = getattr(args, 'max_concurrent_queries', None) or int(os.getenv("MAX_CONCURRENT_QUERIES", "5"))

    # Create client options
    return SentinelAggregatorClientOptions(
        dcr_logs_ingestion_endpoint=dcr_endpoint,
        dcr_rule_id=dcr_rule_id,
        days_ago=days_back,
        batch_hours=batch_hours,
        max_concurrent_queries=max_concurrent,
        query_timeout_seconds=int(os.getenv("QUERY_TIMEOUT_SECONDS", "300")),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        retry_delay_seconds=int(os.getenv("RETRY_DELAY_SECONDS", "5")),
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

    logger.info("🔍 Performing service health check using Azure SDK-compliant client...")

    try:
        # Create Azure SDK-compliant client
        credential = DefaultAzureCredential()
        async with SentinelAggregatorClient(
            dcr_logs_ingestion_endpoint=client_options.dcr_logs_ingestion_endpoint,
            credential=credential,
            options=client_options,
        ) as client:

            # Validate credentials
            logger.info("🔐 Validating credentials...")
            await client.validate_credentials()
            logger.info("✅ Credential validation successful")

            # Get service properties
            logger.info("📊 Retrieving service properties...")
            service_props = await client.get_service_properties()
            service_props.workspace_count = len(workspaces)

            # Display service health information
            logger.info("🏥 Service Health Report:")
            logger.info(f"  • Service Version: {service_props.service_version}")
            logger.info(f"  • Connectivity Status: {service_props.connectivity_status}")
            logger.info(f"  • Authentication Status: {service_props.authentication_status}")
            logger.info(f"  • DCR Endpoint: {service_props.dcr_endpoint}")
            logger.info(f"  • DCR Rule ID: {service_props.dcr_rule_id}")
            logger.info(f"  • Configured Workspaces: {service_props.workspace_count}")
            logger.info(f"  • Available Queries: {service_props.available_queries}")
            logger.info(f"  • Available Reports: {service_props.available_reports}")
            logger.info(f"  • Last Check: {service_props.last_check_time}")

            # Test a simple query on the first workspace (if any)
            if workspaces:
                test_workspace = workspaces[0]
                logger.info(
                    f"🧪 Testing query connectivity to workspace {test_workspace.workspace_name}..."
                )

                # Simple test query
                test_query = "print 'Health check test query successful'"

                query_result = await client.query_workspace(
                    workspace_id=test_workspace.customer_id, query=test_query
                )

                if query_result.succeeded:
                    logger.info(
                        f"✅ Test query successful: {query_result.record_count} records in {query_result.execution_time:.2f}s"
                    )
                else:
                    logger.warning(f"⚠️ Test query failed: {query_result.error_message}")

            return (
                service_props.connectivity_status == "connected"
                and service_props.authentication_status == "valid"
            )

    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return False


async def run_aggregation(
    client_options: SentinelAggregatorClientOptions,
    workspaces: List[WorkspaceConfig],
    days_back: int = None,
    batch_hours: int = None,
):
    """Run the log aggregation process using Azure SDK-compliant components."""
    logger = logging.getLogger(__name__)

    # Validate configuration
    config_errors = client_options.validate()
    if config_errors:
        logger.error("❌ Configuration validation failed:")
        for error in config_errors:
            logger.error(f"  • {error}")
        return False

    # Override configuration values if provided
    if days_back is not None:
        client_options.days_ago = days_back
    if batch_hours is not None:
        client_options.batch_hours = batch_hours

    logger.info(f"🚀 Starting log aggregation process...")
    logger.info(f"  • Days back: {client_options.days_ago}")
    logger.info(f"  • Batch hours: {client_options.batch_hours}")
    logger.info(f"  • Max concurrent queries: {client_options.max_concurrent_queries}")
    logger.info(f"  • Workspaces: {len(workspaces)}")

    try:
        # Create Azure SDK-compliant client
        credential = DefaultAzureCredential()
        async with SentinelAggregatorClient(
            dcr_logs_ingestion_endpoint=client_options.dcr_logs_ingestion_endpoint,
            credential=credential,
            options=client_options,
        ) as client:

            # Use the high-level query engine for batch processing
            query_engine = SentinelQueryEngine(client_options, client)

            # Execute batch queries with streaming upload
            summary = await query_engine.execute_batch_queries_with_streaming_upload(workspaces)

            # Display brief summary - detailed analysis available in logs
            detailed_summary = summary.generate_detailed_summary()

            logger.info("📊 Execution Summary:")
            logger.info("=" * 50)

            # Overview section
            overview = detailed_summary["overview"]
            logger.info(f"📋 Results:")
            logger.info(f"  • Time Range: {overview['total_time_range']}")
            logger.info(f"  • Total Duration: {overview['total_duration_seconds']:.2f}s")
            logger.info(f"  • Workspaces: {overview['total_workspaces']}")
            logger.info(f"  • Unique Queries: {overview['total_unique_queries']}")
            logger.info(f"  • Records Downloaded: {overview['total_records_downloaded']:,}")
            logger.info(f"  • Records Uploaded: {overview['total_records_uploaded']:,}")
            logger.info("")
            logger.info("💡 Note: Detailed workspace/query analytics available in logs above")
            logger.info("")

            return summary.failed_queries == 0

    except Exception as e:
        logger.error(f"❌ Aggregation failed: {e}")
        return False


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Microsoft Sentinel Log Aggregator - Azure SDK Compliant CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using command line arguments (no .env file needed)
  sentinel-aggregator run --workspace-config workspaces.yaml \\
    --dcr-endpoint "https://myworkspace-abcd.centralus-1.ingest.monitor.azure.com" \\
    --dcr-rule-id "dcr-12345678901234567890" \\
    --days-back 7
  
  # Using custom .env file
  sentinel-aggregator run --workspace-config workspaces.yaml --env-file custom.env
  
  # Using default .env file (if exists)
  sentinel-aggregator run --workspace-config workspaces.yaml
  
  # Health check with custom DCR configuration
  sentinel-aggregator health --workspace-config workspaces.yaml \\
    --dcr-endpoint "https://myworkspace-abcd.centralus-1.ingest.monitor.azure.com" \\
    --dcr-rule-id "dcr-12345678901234567890"
  
  # Validate configuration with debug logging
  sentinel-aggregator --log-level DEBUG validate --workspace-config workspaces.yaml
  
  # Run with custom batch settings
  sentinel-aggregator run --workspace-config workspaces.yaml \\
    --days-back 14 --batch-hours 12 --max-concurrent-queries 3
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

    parser.add_argument("--dcr-rule-id", help="Azure Monitor Data Collection Rule ID")

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

    # Optional query settings for run command
    run_parser.add_argument(
        "--days-back", type=int, help="Number of days to look back for data (default: 30)"
    )

    run_parser.add_argument(
        "--batch-hours", type=int, help="Number of hours per batch (default: 24)"
    )

    run_parser.add_argument(
        "--max-concurrent-queries", type=int, help="Maximum concurrent queries (default: 5)"
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

    return parser


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
        if args.config_file:
            logger.debug(f"📋 Loading configuration from file: {args.config_file}")
            client_options = SentinelAggregatorClientOptions.from_yaml_file(args.config_file)
        else:
            logger.debug("📋 Creating configuration from arguments and environment variables")
            client_options = create_client_options_from_args(args)

        # Load workspace configuration if required
        workspaces = []
        if hasattr(args, "workspace_config") and args.workspace_config:
            workspaces = load_workspace_config(args.workspace_config)

        # Execute the appropriate command
        success = True

        if args.command == "health":
            success = await check_service_health(client_options, workspaces)

        elif args.command == "run":
            # Use CLI arguments or fall back to client options
            days_back = args.days_back if args.days_back is not None else client_options.days_ago
            batch_hours = (
                args.batch_hours if args.batch_hours is not None else client_options.batch_hours
            )

            success = await run_aggregation(client_options, workspaces, days_back, batch_hours)

        elif args.command == "validate":
            logger.info("🔍 Validating configuration...")

            # Validate client options
            config_errors = client_options.validate()
            if config_errors:
                logger.error("❌ Client options validation failed:")
                for error in config_errors:
                    logger.error(f"  • {error}")
                success = False
            else:
                logger.info("✅ Client options validation successful")

            # Validate workspace configuration
            if workspaces:
                logger.info(f"✅ Workspace configuration loaded: {len(workspaces)} workspaces")
                for i, workspace in enumerate(workspaces, 1):
                    masked_id = (
                        workspace.customer_id[:8] + "***"
                        if len(workspace.customer_id) > 8
                        else "***"
                    )
                    logger.info(f"  • Workspace {i}: {workspace.workspace_name} (ID: {masked_id})")
            else:
                logger.warning("⚠️ No workspaces configured")

        return 0 if success else 1

    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        logger.debug("Full traceback:", exc_info=True)
        return 1


def cli_main():
    """Synchronous entry point for the CLI."""
    try:
        return asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        return 130  # Standard exit code for SIGINT


if __name__ == "__main__":
    sys.exit(cli_main())
