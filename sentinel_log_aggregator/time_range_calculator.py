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

from .health_logger import SentinelAggregatorHealthLogger
from .models import WorkspaceConfig
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
            logger.info("🕐 Using last successful run timestamps")

            if not health_logger:
                raise TimeRangeCalculationError(
                    "use_last_successful requires health logging to be enabled"
                )

            start_time, end_time = await _calculate_from_last_successful(
                client_options, workspaces, health_logger, batch_size
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

        logger.info(f"📅 Execution time range: {start_time.isoformat()} to {end_time.isoformat()}")
        logger.info(f"⏱️  Batch size: {batch_size}")

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
        logger.info("📅 End time not specified, using current time")

    # If start time not specified but end time is, we need a start time
    if not start_time:
        raise TimeRangeCalculationError("start_time is required when using explicit time range")

    return start_time, end_time


async def _calculate_from_last_successful(
    client_options,
    workspaces: List[WorkspaceConfig],
    health_logger: SentinelAggregatorHealthLogger,
    batch_size: timedelta,
) -> Tuple[datetime, datetime]:
    """
    Calculate time range from last successful run timestamps.

    Args:
        client_options: Client configuration options
        workspaces: List of workspace configurations
        health_logger: Health logger for querying last successful runs
        batch_size: Batch size for calculations

    Returns:
        Tuple of (start_time, end_time) in UTC

    Raises:
        TimeRangeCalculationError: If last successful calculation fails
    """
    logger.info("🔍 Querying health table for last successful runs...")

    # Get all unique query names from workspaces
    all_query_names = set()
    for workspace in workspaces:
        for query_config in workspace.queries_list:
            all_query_names.add(query_config.get("name", query_config.get("query_name", "unknown")))

    if not all_query_names:
        raise TimeRangeCalculationError("No queries found in workspace configurations")

    logger.debug(f"Checking last successful runs for queries: {sorted(all_query_names)}")

    # Check last successful runs for each workspace + query combination
    missing_combinations = []
    earliest_last_end_time = None

    for workspace in workspaces:
        workspace_id = workspace.customer_id

        for query_config in workspace.queries_list:
            query_name = query_config.get("name", query_config.get("query_name", "unknown"))

            try:
                # Query for last successful run of this query+workspace combination
                last_successful = await _query_last_successful_for_query_workspace(
                    health_logger, workspace_id, query_name
                )

                if not last_successful:
                    missing_combinations.append(f"{query_name} (workspace: {workspace_id[:8]})")
                    continue

                # Track the earliest end time across all queries
                last_end_time = last_successful.get("end_time")
                if isinstance(last_end_time, str):
                    last_end_time = parse_iso8601_datetime(last_end_time)

                if earliest_last_end_time is None or last_end_time < earliest_last_end_time:
                    earliest_last_end_time = last_end_time

            except Exception as e:
                logger.error(
                    f"Failed to query last successful run for {query_name} in workspace {workspace_id[:8]}: {e}"
                )
                missing_combinations.append(
                    f"{query_name} (workspace: {workspace_id[:8]}) - error: {e}"
                )

    # Check if any combinations are missing
    if missing_combinations:
        logger.error("❌ Missing successful runs for the following query+workspace combinations:")
        for combination in missing_combinations:
            logger.error(f"  • {combination}")
        raise TimeRangeCalculationError(
            f"Cannot use last successful timestamps - missing {len(missing_combinations)} query+workspace combinations"
        )

    # Use the earliest last successful end time as our start time
    if earliest_last_end_time is None:
        raise TimeRangeCalculationError(
            "No successful runs found for any query+workspace combinations"
        )

    start_time = earliest_last_end_time
    end_time = datetime.now(timezone.utc)

    logger.info(f"✅ Using last successful end time as start: {start_time.isoformat()}")

    return start_time, end_time


async def _query_last_successful_for_query_workspace(
    health_logger: SentinelAggregatorHealthLogger,
    workspace_id: str,
    query_name: str,
    lookback_days: int = 30,
) -> Optional[Dict[str, Any]]:
    """
    Query last successful run for a specific query+workspace combination.

    Args:
        health_logger: Health logger with sentinel client
        workspace_id: Workspace ID to query
        query_name: Query name to search for
        lookback_days: How many days back to search

    Returns:
        Dict with last successful run data or None if not found
    """
    from datetime import timedelta

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=lookback_days)

    # Build KQL query for specific query+workspace combination
    kql_query = f"""
    SentinelAggregator-Health_CL
    | where TimeGenerated between (datetime({start_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}) .. datetime({end_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}))
    | where OperationName == "QueryExecution"
    | where OperationStatus == "Completed"
    | where QueryName == "{query_name}"
    | where WorkspaceId == "{workspace_id}"
    | extend ExtendedProps = parse_json(ExtendedProperties)
    | extend StartTime = todatetime(ExtendedProps.start_time)
    | extend EndTime = todatetime(ExtendedProps.end_time)
    | extend RecordCount = toint(ExtendedProps.record_count)
    | where isnotnull(StartTime) and isnotnull(EndTime) and isnotnull(RecordCount)
    | top 1 by TimeGenerated desc
    | project QueryName, WorkspaceId, StartTime, EndTime, RecordCount, LastRunTime=TimeGenerated
    """

    try:
        from azure.identity.aio import DefaultAzureCredential
        from azure.monitor.query.aio import LogsQueryClient

        credential = DefaultAzureCredential()
        query_client = LogsQueryClient(credential=credential)

        # Execute the query
        response = await query_client.query_workspace(
            workspace_id=workspace_id, query=kql_query, timespan=(start_time, end_time)
        )

        # Convert results
        result = None
        if response.tables and response.tables[0].rows:
            table = response.tables[0]
            column_names = [col.name for col in table.columns]
            row = table.rows[0]
            result = dict(zip(column_names, row))

            # Convert datetime fields
            for field in ["StartTime", "EndTime", "LastRunTime"]:
                if field in result and result[field]:
                    if isinstance(result[field], str):
                        result[f"{field.lower()}"] = parse_iso8601_datetime(result[field])
                    else:
                        result[f"{field.lower()}"] = result[field]

        await credential.close()
        await query_client.close()

        return result

    except Exception as e:
        logger.debug(
            f"Failed to query last successful run for {query_name}/{workspace_id[:8]}: {e}"
        )
        return None


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

        logger.info(f"📊 Calculated {len(batches)} execution batches")

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
