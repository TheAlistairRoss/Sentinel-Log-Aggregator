"""
Time range calculation logic for Sentinel Log Aggregator.

Handles the precedence of different time specification methods:
1. use_last_successful (highest priority)
2. start_time/end_time (explicit time range)
3. lookback_period (relative time range)

Also handles batch calculation from last successful runs with proper constraints.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sentinel_log_aggregator.constants import HEALTH_TABLE_NAME

from .health_logger import SentinelAggregatorHealthLogger
from .models import AVAILABLE_QUERIES, WorkspaceConfig
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


def _resolve_query_name(query_item: Any) -> Optional[str]:
    """
    Resolve query name from workspace query item.

    This function handles different query formats:
    - If query_item is already in AVAILABLE_QUERIES registry, use it directly
    - If query_item is a file path, load the YAML and extract the 'name' field

    Args:
        query_item: Query name (string) or dict (for tests)

    Returns:
        The query name as defined in the 'name' field, or None if cannot be resolved

    Raises:
        TimeRangeCalculationError: If query file exists but doesn't have a 'name' field
    """
    import yaml

    # Handle test format: dict with 'name' key
    if isinstance(query_item, dict):
        query_name = query_item.get("name")
        if not query_name:
            raise TimeRangeCalculationError(
                f"Query dictionary must have a 'name' field: {query_item}"
            )
        return query_name

    # Handle string format
    if isinstance(query_item, str):
        # Check if it's already registered
        if query_item in AVAILABLE_QUERIES:
            return query_item

        # Check if it's registered in the query registry
        if query_item in query_registry.list_queries():
            return query_item

        # Try to load as a file path
        query_file = Path(query_item)
        if query_file.exists() and query_file.suffix in [".yaml", ".yml"]:
            try:
                with open(query_file, "r") as f:
                    query_data = yaml.safe_load(f)

                if not isinstance(query_data, dict):
                    raise TimeRangeCalculationError(
                        f"Invalid query file format in {query_file}: Expected dict, got {type(query_data)}"
                    )

                query_name = query_data.get("name")
                if not query_name:
                    raise TimeRangeCalculationError(
                        f"Query file {query_file} must have a 'name' field defined. "
                        f"The 'name' field is mandatory and must match the name used in health logging."
                    )

                logger.debug(f"Resolved query name '{query_name}' from file {query_file}")
                return query_name

            except Exception as e:
                if isinstance(e, TimeRangeCalculationError):
                    raise
                raise TimeRangeCalculationError(f"Failed to load query name from {query_file}: {e}")
        else:
            raise TimeRangeCalculationError(
                f"Query '{query_item}' not found in registry and not a valid YAML file. "
                f"Available queries: {sorted(AVAILABLE_QUERIES.keys())}. "
                f"If this is a query file path, ensure it exists and has .yaml or .yml extension."
            )

    raise TimeRangeCalculationError(
        f"Invalid query item type: {type(query_item)}. Expected string or dict."
    )


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
                client_options,
                workspaces,
                health_logger,
                batch_size,
                job_id,
                client_options.lookback_period,
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
    lookback_period: Optional[str] = None,
) -> Tuple[datetime, datetime]:
    """
    Calculate time range from last successful run timestamps.

    NOTE: This function modifies the input workspaces list in-place to filter out
    query+workspace combinations that don't have baseline data. Only combinations
    with successful last runs will remain in the queries_list for each workspace.

    If no successful runs are found, falls back to using the lookback_period.

    Args:
        client_options: Client configuration options
        workspaces: List of workspace configurations (MODIFIED IN-PLACE)
        health_logger: Health logger for querying last successful runs
        batch_size: Batch size for calculations
        job_id: Optional job correlation ID for health logging
        lookback_period: ISO 8601 duration string for fallback lookback (e.g., 'P90D')

    Returns:
        Tuple of (start_time, end_time) in UTC

    Raises:
        TimeRangeCalculationError: If last successful calculation fails or no combinations have baseline data
    """
    logger.info("Querying health table for last successful runs...")

    # Get all unique query names from workspaces
    all_query_names = set()
    for workspace in workspaces:
        for query_item in workspace.queries_list:
            query_name = _resolve_query_name(query_item)
            if query_name:
                all_query_names.add(query_name)

    if not all_query_names:
        raise TimeRangeCalculationError("No queries found in workspace configurations")

    logger.debug(f"Checking last successful runs for queries: {sorted(all_query_names)}")

    # Convert lookback_period to days for health query
    # Default to 30 days if not specified
    if lookback_period:
        from .time_utils import parse_iso8601_duration

        lookback_timedelta = parse_iso8601_duration(lookback_period)
        lookback_days = int(lookback_timedelta.total_seconds() / 86400)  # Convert to days
    else:
        lookback_days = 30

    logger.debug(f"Health query will search back {lookback_days} days for successful runs")

    # Get all last successful runs in a single query
    last_successful_results = await _query_all_last_successful_runs(
        health_logger, list(workspaces), lookback_days=lookback_days
    )

    # Check last successful runs for each workspace + query combination
    # Build a map of successful combinations and track which need baseline establishment
    successful_last_end_times = {}
    queries_needing_baseline = []

    for workspace in workspaces:
        workspace_id = workspace.customer_id

        for query_item in workspace.queries_list:
            query_name = _resolve_query_name(query_item)
            if not query_name:
                logger.warning(f"Could not resolve query name for item: {query_item}")
                continue

            # Look up the result from our batched query
            key = (query_name, workspace_id)
            last_successful = last_successful_results.get(key)

            if not last_successful:
                # Track queries that need baseline establishment
                queries_needing_baseline.append(f"{query_name} (workspace: {workspace_id})")
                logger.info(
                    f"📋 No baseline found for {query_name} in workspace {workspace_id}. "
                    f"Will execute this query to establish baseline."
                )
                continue  # Don't add to successful_last_end_times, but don't skip either

            # Track the end time for this successful combination
            last_end_time = last_successful.get("end_time")
            if isinstance(last_end_time, str):
                last_end_time = parse_iso8601_datetime(last_end_time)

            # Only store if we have a valid end time
            if last_end_time is not None:
                successful_last_end_times[key] = last_end_time
            else:
                logger.warning(
                    f"⚠️  Query {query_name} in workspace {workspace_id} has null end_time in health data. "
                    f"Will treat as needing baseline establishment."
                )
                queries_needing_baseline.append(
                    f"{query_name} (workspace: {workspace_id}) - null end_time"
                )

    # Report summary of queries needing baseline establishment
    if queries_needing_baseline:
        logger.info(
            f"📋 Found {len(queries_needing_baseline)} query+workspace combination(s) that need baseline establishment. "
            f"These WILL be executed in this run to create initial baseline."
        )

    if successful_last_end_times:
        logger.info(
            f"✅ Found {len(successful_last_end_times)} query+workspace combination(s) with existing baseline data."
        )

    # Calculate time range based on whether we have existing baseline data
    end_time = datetime.now(timezone.utc)

    if not successful_last_end_times:
        # No successful runs found - this is expected on first run
        # Use lookback_period to establish baseline for all queries
        logger.warning(
            "⚠️  No successful runs found in health table. "
            "This is expected on first run. "
            f"Using lookback_period ({lookback_period or 'P30D'}) to establish baseline for all queries."
        )

        # Calculate time range using lookback period
        if lookback_period:
            from .time_utils import parse_iso8601_duration

            lookback_timedelta = parse_iso8601_duration(lookback_period)
        else:
            lookback_timedelta = timedelta(days=30)

        start_time = end_time - lookback_timedelta

        logger.info(
            f"First run baseline: Will query {lookback_days} days of data "
            f"from {start_time.isoformat()} to {end_time.isoformat()}"
        )

        return start_time, end_time

    # Some queries have baseline data - calculate appropriate time range
    latest_last_end_time = max(successful_last_end_times.values())

    # Determine the appropriate start time based on whether queries need baseline
    incremental_start_time = latest_last_end_time + timedelta(microseconds=1)

    if queries_needing_baseline:
        # Some queries need baseline establishment
        # Calculate lookback start time for those queries
        if lookback_period:
            from .time_utils import parse_iso8601_duration

            lookback_timedelta = parse_iso8601_duration(lookback_period)
        else:
            lookback_timedelta = timedelta(days=30)

        lookback_start_time = end_time - lookback_timedelta

        # Use the EARLIER of: (latest_last_end_time + 1µs) or (lookback_start_time)
        # This ensures queries needing baseline get full lookback period
        # while incremental queries still get new data since last run
        start_time = min(incremental_start_time, lookback_start_time)
    else:
        # All queries have baseline - pure incremental mode
        start_time = incremental_start_time

    # Debug logging: Show which query+workspace has the most recent successful run
    latest_combination = None
    for key, last_end in successful_last_end_times.items():
        if last_end == latest_last_end_time:
            latest_combination = key
            break

    if latest_combination:
        query_name, workspace_id = latest_combination
        logger.info(
            f"🔍 Latest successful run found: query='{query_name}', workspace={workspace_id}, "
            f"end_time={latest_last_end_time.isoformat()}"
        )

        # Show all other combinations' end times for comparison
        logger.debug("All successful end times by query+workspace:")
        for (q_name, ws_id), last_end in sorted(
            successful_last_end_times.items(), key=lambda x: x[1], reverse=True
        ):
            logger.debug(f"  - {q_name} / {ws_id[:8]}... : {last_end.isoformat()}")

    # Log the calculated time range strategy
    if queries_needing_baseline:
        if start_time == lookback_start_time:
            logger.info(
                f"📅 Time range strategy: Using lookback period ({lookback_period or 'P30D'}) "
                f"to cover both incremental queries AND baseline establishment."
            )
        else:
            logger.info(
                f"📅 Time range strategy: Using incremental start ({incremental_start_time.isoformat()}) "
                f"which also covers lookback period for baseline establishment."
            )
    else:
        logger.info(
            f"📅 Time range strategy: Pure incremental mode - all queries have baseline data."
        )

    logger.info(f"⏰ Execution time range: {start_time.isoformat()} to {end_time.isoformat()}")
    logger.info(
        f"📊 Total queries to execute: {sum(len(w.queries_list) for w in workspaces)} "
        f"across {len(workspaces)} workspace(s)"
    )

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
    # Note: ExtendedProperties is a dynamic (JSON) column that needs proper parsing
    kql_query = f"""
{HEALTH_TABLE_NAME}
| where OperationName == 'QueryExecution'
| where OperationStatus == 'Completed'
| extend ExtendedPropertiesParsed = parse_json(ExtendedProperties)
| extend EndTime = todatetime(ExtendedPropertiesParsed.end_time)
| extend QueryName = tostring(ExtendedPropertiesParsed.query_name)
| extend WorkspaceId = tostring(ExtendedPropertiesParsed.workspace_id)
| where isnotnull(EndTime) and isnotnull(QueryName) and isnotnull(WorkspaceId) 
| summarize arg_max(EndTime, *) by QueryName, WorkspaceId
| project 
    LastRunTime=TimeGenerated,
    QueryName,
    WorkspaceId,
    EndTime, 
    JobId    
"""

    logger.debug(
        f"Querying aggregation workspace: {aggregation_workspace.workspace_name} ({aggregation_workspace.customer_id})"
    )
    logger.debug(
        f"Health query lookback: {lookback_days} days (from {start_time.isoformat()} to {end_time.isoformat()})"
    )
    logger.debug(f"Health table: {HEALTH_TABLE_NAME}")

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

            logger.debug(
                f"Health query returned {len(response.tables) if response.tables else 0} table(s)"
            )

            if response.tables and response.tables[0].rows:
                logger.debug(f"Health table has {len(response.tables[0].rows)} row(s)")
                table = response.tables[0]
                # Handle both object-style columns (with .name attribute) and dict/string columns
                column_names = []
                for col in table.columns:
                    if hasattr(col, "name"):
                        column_names.append(col.name)
                    elif isinstance(col, dict):
                        column_names.append(col.get("name", str(col)))
                    else:
                        column_names.append(str(col))

                # Process each row and keep the latest result per query+workspace combination
                for idx, row in enumerate(table.rows, 1):
                    row_dict = dict(zip(column_names, row))

                    # Map EndTime directly to end_time for downstream code
                    if "EndTime" in row_dict:
                        row_dict["end_time"] = row_dict["EndTime"]

                    query_name = row_dict.get("QueryName")
                    workspace_id = row_dict.get("WorkspaceId")
                    last_run_time = row_dict.get("LastRunTime")
                    end_time_value = row_dict.get("EndTime")

                    logger.debug(
                        f"  Row {idx}: query='{query_name}', workspace={workspace_id if workspace_id else 'N/A'}, "
                        f"end_time={end_time_value}, last_run={last_run_time}"
                    )

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

            logger.info(
                f"Found {len(results_map)} unique query+workspace combination(s) with successful runs in last {lookback_days} days"
            )

            # Log full health query details for debugging
            logger.debug(f"Health query KQL:\n{kql_query}")

            # Log first 5 health records for debugging
            if results_map:
                sample_items = list(results_map.items())[:5]
                logger.debug(
                    f"Health query results (first {len(sample_items)} of {len(results_map)} combinations):"
                )
                for (q_name, ws_id), data in sample_items:
                    logger.debug(
                        f"  {json.dumps({'query': q_name, 'workspace': ws_id, 'data': data}, default=str)}"
                    )

            # Log summary of all combinations found
            if results_map:
                logger.debug("All successful runs found:")
                for (q_name, ws_id), data in sorted(results_map.items()):
                    end_time_val = data.get("end_time") or data.get("EndTime")
                    logger.debug(f"  - {q_name} / {ws_id[:8]}... : end_time={end_time_val}")

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

        # Log batch details
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
