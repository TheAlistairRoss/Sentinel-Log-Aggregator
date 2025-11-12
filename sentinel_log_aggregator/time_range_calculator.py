"""
Time range calculation logic for Sentinel Log Aggregator.

Handles the precedence of different time specification methods:
1. use_last_successful (highest priority)
2. start_time/end_time (explicit time range)
3. lookback_period (relative time range)

Also handles batch calculation from last successful runs with proper constraints.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sentinel_log_aggregator.constants import HEALTH_TABLE_NAME

from .health_logger import SentinelAggregatorHealthLogger
from .models import WorkspaceConfig
from .query_registry import query_registry
from .time_utils import (
    InvalidTimeRangeError,
    TimeParsingError,
    calculate_batches,
    calculate_time_range_from_lookback,
    parse_iso8601_datetime,
    parse_iso8601_duration,
    validate_batch_time_size,
    validate_time_range,
)

logger = logging.getLogger(__name__)


class TimeRangeCalculationError(Exception):
    """Raised when time range calculation fails."""

    pass


async def calculate_execution_time_ranges(
    client_options,
    workspaces: List[WorkspaceConfig],
    health_logger: Optional[SentinelAggregatorHealthLogger] = None,
    job_id: Optional[str] = None,
) -> Tuple[datetime, datetime, timedelta]:
    """
    Calculate execution time ranges based on client options and precedence rules.

    Precedence order:
    1. use_last_successful -> Query health table for last successful runs
    2. start_time/end_time -> Use explicit time range
    3. lookback_period -> Use relative time range from now

    Args:
        client_options: Client configuration options
        workspaces: List of workspace configurations
        health_logger: Optional health logger for querying last successful runs
        job_id: Optional job correlation ID for health logging

    Returns:
        Tuple of (start_time, end_time, batch_size) in UTC

    Raises:
        TimeRangeCalculationError: If time range calculation fails
    """
    try:
        # Get batch size
        batch_size = validate_batch_time_size(client_options.batch_time_size)

        # Precedence 1: Use last successful timestamps
        if client_options.use_last_successful:
            logger.info("Using last successful run timestamps")

            if not health_logger:
                raise TimeRangeCalculationError(
                    "use_last_successful requires health logging to be enabled"
                )

            start_time, end_time = await _calculate_from_last_successful(
                client_options, workspaces, health_logger, batch_size, job_id
            )

        # Precedence 2: Explicit start/end times
        elif client_options.start_time or client_options.end_time:
            logger.info("🕐 Using explicit time range")

            start_time, end_time = _calculate_from_explicit_times(client_options)

        # Precedence 3: Lookback period
        else:
            logger.info(f"🕐 Using lookback period: {client_options.lookback_period}")

            start_time, end_time = calculate_time_range_from_lookback(
                client_options.lookback_period
            )

        # Validate the final time range
        validate_time_range(start_time, end_time, allow_future_end=False)

        logger.info(f"Execution time range: {start_time.isoformat()} to {end_time.isoformat()}")
        logger.info(f"Batch size: {batch_size}")

        return start_time, end_time, batch_size

    except (TimeParsingError, InvalidTimeRangeError) as e:
        raise TimeRangeCalculationError(f"Time range calculation failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in time range calculation: {e}")
        raise TimeRangeCalculationError(f"Time range calculation failed: {e}")


def _calculate_from_explicit_times(client_options) -> Tuple[datetime, datetime]:
    """
    Calculate time range from explicit start/end times.

    Args:
        client_options: Client configuration options

    Returns:
        Tuple of (start_time, end_time) in UTC

    Raises:
        TimeRangeCalculationError: If explicit times are invalid
    """
    start_time = None
    end_time = None

    # Parse start time
    if client_options.start_time:
        start_time = parse_iso8601_datetime(client_options.start_time)

    # Parse end time or default to now
    if client_options.end_time:
        end_time = parse_iso8601_datetime(client_options.end_time)
    else:
        end_time = datetime.now(timezone.utc)
        logger.info("End time not specified, using current time")

    # If start time not specified but end time is, we need a start time
    if not start_time:
        raise TimeRangeCalculationError("start_time is required when using explicit time range")

    return start_time, end_time


async def _calculate_from_last_successful(
    client_options,
    workspaces: List[WorkspaceConfig],
    health_logger: SentinelAggregatorHealthLogger,
    batch_size: timedelta,
    job_id: Optional[str] = None,
) -> Tuple[datetime, datetime]:
    """
    Calculate time range from last successful run timestamps.

    Args:
        client_options: Client configuration options
        workspaces: List of workspace configurations
        health_logger: Health logger for querying last successful runs
        batch_size: Batch size for calculations
        job_id: Optional job correlation ID for health logging

    Returns:
        Tuple of (start_time, end_time) in UTC

    Raises:
        TimeRangeCalculationError: If last successful calculation fails
    """
    logger.info("Querying health table for last successful runs...")

    # Get all unique query names from workspaces
    all_query_names = set()
    for workspace in workspaces:
        for query_item in workspace.queries_list:
            # Handle both dict format (tests) and string format (production YAML file paths)
            if isinstance(query_item, dict):
                # Test format: {"name": "test_query"}
                query_name = query_item.get("name", query_item.get("query_name", "unknown"))
                all_query_names.add(query_name)
            elif isinstance(query_item, str):
                # Production format: "Queries\incident_summary.yaml"
                query_file_name = query_item.replace("\\", "/").split("/")[-1].replace(".yaml", "")

                # Try to find matching query in registry
                for reg_query_name in query_registry.list_queries():
                    if query_file_name in reg_query_name or reg_query_name in query_file_name:
                        all_query_names.add(reg_query_name)
                        break
                else:
                    # Fallback: use the filename as query name
                    all_query_names.add(query_file_name)

    if not all_query_names:
        raise TimeRangeCalculationError("No queries found in workspace configurations")

    logger.debug(f"Checking last successful runs for queries: {sorted(all_query_names)}")

    # Get all last successful runs in a single query
    last_successful_results = await _query_all_last_successful_runs(
        health_logger, list(workspaces), lookback_days=30
    )

    # Check last successful runs for each workspace + query combination
    missing_combinations = []
    earliest_last_end_time = None

    for workspace in workspaces:
        workspace_id = workspace.customer_id

        for query_item in workspace.queries_list:
            # Handle both dict format (tests) and string format (production YAML file paths)
            if isinstance(query_item, dict):
                # Test format: {"name": "test_query"}
                query_name = query_item.get("name", query_item.get("query_name", "unknown"))
            elif isinstance(query_item, str):
                # Production format: "Queries\incident_summary.yaml"
                query_file_name = query_item.replace("\\", "/").split("/")[-1].replace(".yaml", "")

                # Try to find matching query in registry
                query_name = None
                for reg_query_name in query_registry.list_queries():
                    if query_file_name in reg_query_name or reg_query_name in query_file_name:
                        query_name = reg_query_name
                        break

                if not query_name:
                    # Fallback: use the filename as query name
                    query_name = query_file_name
            else:
                # Unknown format, skip
                logger.warning(f"Unknown query item format: {type(query_item)}")
                continue

            # Look up the result from our batched query
            key = (query_name, workspace_id)
            last_successful = last_successful_results.get(key)

            if not last_successful:
                missing_combinations.append(f"{query_name} (workspace: {workspace_id})")
                continue

            # Track the earliest end time across all queries
            last_end_time = last_successful.get("end_time")
            if isinstance(last_end_time, str):
                last_end_time = parse_iso8601_datetime(last_end_time)

            if earliest_last_end_time is None or last_end_time < earliest_last_end_time:
                earliest_last_end_time = last_end_time

    # Check if any combinations are missing
    if missing_combinations:
        logger.error("Missing successful runs for the following query+workspace combinations:")

        # Log health error event for each missing combination
        from .models import AVAILABLE_QUERIES, QueryExecution, QueryStatus, UploadStatus

        for combination in missing_combinations:
            logger.error(f"  ⚠️  {combination}")

            # Parse combination string: "query_name (workspace: workspace_id)"
            try:
                parts = combination.split(" (workspace: ")
                query_name = parts[0]
                workspace_id = parts[1].rstrip(")") if len(parts) > 1 else "unknown"

                # Find the workspace config for this workspace_id
                workspace_config = next(
                    (w for w in workspaces if w.customer_id == workspace_id), None
                )

                if workspace_config:
                    # Get destination stream from query definition if available
                    destination_stream = "unknown"
                    if query_name in AVAILABLE_QUERIES:
                        query_def = AVAILABLE_QUERIES[query_name]
                        destination_stream = getattr(query_def, "destination_stream", "unknown")

                    # Create QueryExecution with error details
                    error_msg = (
                        "No last successful run found. "
                        "Run without --use-last-successful and specify explicit time range: "
                        "--start-time YYYY-MM-DDTHH:MM:SS --end-time YYYY-MM-DDTHH:MM:SS"
                    )

                    timestamp = datetime.now(timezone.utc)
                    query_execution = QueryExecution(
                        job_correlation_id=job_id or "unknown",
                        execution_id=f"missing_baseline_{workspace_id[:8]}_{query_name}",
                        workspace_id=workspace_config.resource_id,
                        query_name=query_name,
                        destination_stream=destination_stream,
                        start_time=timestamp,
                        end_time=timestamp,
                        execution_timestamp=timestamp,
                        query_status=QueryStatus.FAILED.value,
                        query_duration_seconds=0.0,
                        record_count=0,
                        query_error_message=error_msg,
                        upload_status=UploadStatus.SKIPPED.value,
                    )

                    # Log to health table (or console in dry-run mode)
                    await health_logger.log_query_execution(
                        job_id=job_id or "unknown",
                        query_execution=query_execution,
                        workspace_config=workspace_config,
                        batch_id=None,
                    )
            except Exception as log_error:
                logger.debug(f"Failed to log health error for {combination}: {log_error}")

        # Raise error with helpful remediation message
        raise TimeRangeCalculationError(
            f"Cannot use --use-last-successful: Missing last successful run data for "
            f"{len(missing_combinations)} query+workspace combination(s). "
            f"To resolve: Run the aggregator WITHOUT --use-last-successful flag and specify "
            f"explicit time range using --start-time and --end-time to populate initial baseline data. "
            f"Example: --start-time 2025-10-01T00:00:00 --end-time 2025-11-01T00:00:00"
        )

    # Use the earliest last successful end time + 1 microsecond as our start time
    # This ensures continuous data coverage with no gaps or overlaps
    if earliest_last_end_time is None:
        raise TimeRangeCalculationError(
            "No successful runs found for any query+workspace combinations"
        )

    # Add 1 microsecond to the last end time to start from the next moment
    start_time = earliest_last_end_time + timedelta(microseconds=1)
    end_time = datetime.now(timezone.utc)

    logger.info(f"Using last successful end time + 1µs as start: {start_time.isoformat()}")

    return start_time, end_time


async def _query_all_last_successful_runs(
    health_logger: SentinelAggregatorHealthLogger,
    workspaces: List[WorkspaceConfig],
    lookback_days: int = 30,
) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    Query last successful runs for all workspace+query combinations in one optimized query.

    Args:
        health_logger: Health logger with sentinel client
        workspaces: List of workspace configurations
        lookback_days: How many days back to search

    Returns:
        Dict mapping (query_name, workspace_id) tuples to last successful run data
    """
    from datetime import timedelta

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=lookback_days)

    # Get the aggregation workspace for querying
    aggregation_workspace = None
    for workspace in workspaces:
        if workspace.aggregation_workspace:
            aggregation_workspace = workspace
            break

    if not aggregation_workspace:
        logger.warning("No aggregation workspace found, using first workspace for health queries")
        aggregation_workspace = workspaces[0]

    # Build optimized KQL query for all successful runs
    kql_query = f"""
{HEALTH_TABLE_NAME}
| where OperationName == 'QueryExecution'
| where OperationStatus == 'Completed'
| extend EndTime = todatetime(ExtendedProperties.end_time)
| extend QueryName = tostring(ExtendedProperties.query_name)
| extend WorkspaceId = tostring(ExtendedProperties.workspace_id)
| where isnotnull(EndTime) and isnotnull(QueryName)and isnotnull(WorkspaceId) 
| summarize arg_max(EndTime, *) by QueryName, WorkspaceId
| project 
    LastRunTime=TimeGenerated,
    QueryName,
    WorkspaceId,
    EndTime, 
    JobId    
"""

    try:
        from azure.identity.aio import DefaultAzureCredential
        from azure.monitor.query.aio import LogsQueryClient

        credential = DefaultAzureCredential()
        query_client = LogsQueryClient(credential=credential, logging_enable=True)

        try:
            # Execute the query against the aggregation workspace
            response = await query_client.query_workspace(
                workspace_id=aggregation_workspace.customer_id,
                query=kql_query,
                timespan=(start_time, end_time),
            )

            # Process all results and map to (query_name, workspace_id) -> latest result
            results_map = {}

            if response.tables and response.tables[0].rows:
                table = response.tables[0]
                column_names = [col.name for col in table.columns]

                # Process each row and keep the latest result per query+workspace combination
                for row in table.rows:
                    row_dict = dict(zip(column_names, row))

                    query_name = row_dict.get("QueryName")
                    workspace_id = row_dict.get("WorkspaceId")
                    last_run_time = row_dict.get("LastRunTime")

                    if not query_name or not workspace_id:
                        continue

                    # Convert timestamp for comparison
                    if isinstance(last_run_time, str):
                        last_run_time = parse_iso8601_datetime(last_run_time)

                    key = (query_name, workspace_id)

                    # Keep the record with the latest timestamp for each key
                    if key not in results_map:
                        results_map[key] = row_dict.copy()
                    else:
                        existing_time = results_map[key].get("LastRunTime")
                        if isinstance(existing_time, str):
                            existing_time = parse_iso8601_datetime(existing_time)

                        if last_run_time and (not existing_time or last_run_time > existing_time):
                            results_map[key] = row_dict.copy()

                # Convert datetime fields for all results
                for result in results_map.values():
                    for field in ["StartTime", "EndTime", "LastRunTime"]:
                        if field in result and result[field]:
                            if isinstance(result[field], str):
                                result[f"{field.lower()}"] = parse_iso8601_datetime(result[field])
                            else:
                                result[f"{field.lower()}"] = result[field]

            logger.debug(
                f"Found {len(results_map)} unique query+workspace combinations in health logs"
            )
            return results_map

        finally:
            # Always close resources, even if query fails
            await credential.close()
            await query_client.close()

    except Exception as e:
        logger.error(f"Failed to query all last successful runs: {e}")
        return {}


def calculate_execution_batches(
    start_time: datetime,
    end_time: datetime,
    batch_size: timedelta,
    min_batch_size: Optional[timedelta] = None,
) -> List[Tuple[datetime, datetime]]:
    """
    Calculate execution batches with minimum batch size constraint.

    Args:
        start_time: Batch start time (UTC)
        end_time: Batch end time (UTC)
        batch_size: Size of each batch
        min_batch_size: Minimum batch size (defaults to 1 hour)

    Returns:
        List of (batch_start, batch_end) tuples

    Raises:
        TimeRangeCalculationError: If batch calculation fails
    """
    if min_batch_size is None:
        min_batch_size = timedelta(hours=1)

    try:
        batches = calculate_batches(
            start_time=start_time,
            end_time=end_time,
            batch_size=batch_size,
            min_batch_size=min_batch_size,
        )

        logger.info(f"Calculated {len(batches)} execution batches")

        # Log batch details in debug mode
        if logger.isEnabledFor(logging.DEBUG):
            for i, (batch_start, batch_end) in enumerate(batches, 1):
                duration = batch_end - batch_start
                logger.debug(
                    f"  Batch {i}: {batch_start.isoformat()} to {batch_end.isoformat()} ({duration})"
                )

        return batches

    except Exception as e:
        raise TimeRangeCalculationError(f"Batch calculation failed: {e}")


def validate_time_configuration(client_options) -> List[str]:
    """
    Validate time configuration for conflicts and constraints.

    Args:
        client_options: Client configuration options

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    try:
        # Check for conflicting time specifications
        has_explicit_times = bool(client_options.start_time or client_options.end_time)
        has_lookback = bool(
            client_options.lookback_period and client_options.lookback_period != "P30D"
        )  # Default value
        has_last_successful = bool(client_options.use_last_successful)

        time_methods = sum([has_explicit_times, has_lookback, has_last_successful])

        if time_methods > 1:
            active_methods = []
            if has_explicit_times:
                active_methods.append("explicit times (start_time/end_time)")
            if has_lookback:
                active_methods.append("lookback_period")
            if has_last_successful:
                active_methods.append("use_last_successful")

            errors.append(
                f"Conflicting time specifications: {', '.join(active_methods)}. Use only one method."
            )

        # Validate explicit times if provided
        if client_options.start_time:
            try:
                start_time = parse_iso8601_datetime(client_options.start_time)
            except TimeParsingError as e:
                errors.append(f"Invalid start_time: {e}")

        if client_options.end_time:
            try:
                end_time = parse_iso8601_datetime(client_options.end_time)
            except TimeParsingError as e:
                errors.append(f"Invalid end_time: {e}")

        # Validate time range if both are provided
        if client_options.start_time and client_options.end_time:
            try:
                start_time = parse_iso8601_datetime(client_options.start_time)
                end_time = parse_iso8601_datetime(client_options.end_time)
                validate_time_range(start_time, end_time, allow_future_end=False)
            except (TimeParsingError, InvalidTimeRangeError) as e:
                errors.append(f"Invalid time range: {e}")

        # Validate lookback period
        if client_options.lookback_period:
            try:
                parse_iso8601_duration(client_options.lookback_period)
            except TimeParsingError as e:
                errors.append(f"Invalid lookback_period: {e}")

        # Validate batch time size
        if client_options.batch_time_size:
            try:
                validate_batch_time_size(client_options.batch_time_size)
            except TimeParsingError as e:
                errors.append(f"Invalid batch_time_size: {e}")

    except Exception as e:
        errors.append(f"Time configuration validation error: {e}")

    return errors
