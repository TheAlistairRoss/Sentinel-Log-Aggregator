"""Time utilities for handling ISO 8601 durations and time range calculations."""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Union

import isodate
from pydantic import ValidationError, validate_call

from .constants import SECONDS_PER_HOUR


class TimeParsingError(Exception):
    """Raised when time parsing fails."""

    pass


class InvalidTimeRangeError(Exception):
    """Raised when time range validation fails."""

    pass


@validate_call
def parse_iso8601_duration(duration_str: str) -> timedelta:
    """
    Parse ISO 8601 duration string to timedelta object.

    Supports formats like:
    - P1D (1 day)
    - PT24H (24 hours)
    - PT1H30M (1 hour 30 minutes)
    - P1DT12H (1 day 12 hours)

    Args:
        duration_str: ISO 8601 duration string

    Returns:
        timedelta object

    Raises:
        TimeParsingError: If duration string is invalid
    """
    try:
        # Use isodate library to parse ISO 8601 duration
        duration = isodate.parse_duration(duration_str)

        # Ensure we get a timedelta object (not relativedelta)
        if not isinstance(duration, timedelta):
            raise TimeParsingError(
                f"Duration '{duration_str}' resulted in unsupported type: {type(duration)}"
            )

        return duration

    except (isodate.ISO8601Error, ValueError) as e:
        raise TimeParsingError(f"Invalid ISO 8601 duration format '{duration_str}': {e}")


@validate_call
def validate_batch_time_size(duration_str: str) -> timedelta:
    """
    Validate batch time size meets constraints.

    Requirements:
    - Must be a multiple of 1 hour
    - Must be between 1 hour and 24 hours (inclusive)

    Args:
        duration_str: ISO 8601 duration string

    Returns:
        timedelta object if valid

    Raises:
        TimeParsingError: If duration doesn't meet constraints
    """
    duration = parse_iso8601_duration(duration_str)

    # Convert to total hours for validation
    total_hours = duration.total_seconds() / SECONDS_PER_HOUR

    # Check minimum (1 hour)
    if total_hours < 1:
        raise TimeParsingError(f"Batch time size must be at least 1 hour, got: {duration_str}")

    # Check maximum (24 hours)
    if total_hours > 24:
        raise TimeParsingError(f"Batch time size must be at most 24 hours, got: {duration_str}")

    # Check that it's a multiple of 1 hour
    if total_hours != int(total_hours):
        raise TimeParsingError(f"Batch time size must be a multiple of 1 hour, got: {duration_str}")

    return duration


@validate_call
def parse_iso8601_datetime(datetime_str: str) -> datetime:
    """
    Parse ISO 8601 datetime string to UTC datetime object.

    Supports various precision levels (seconds, milliseconds, microseconds).
    Examples:
    - "2025-10-01T17:00:00Z"
    - "2025-10-01T17:00:00.123456Z"
    - "2025-10-01T17:00:00.123456+00:00"

    Args:
        datetime_str: ISO 8601 datetime string

    Returns:
        datetime object in UTC timezone

    Raises:
        TimeParsingError: If datetime string is invalid
    """
    try:
        # Parse ISO 8601 datetime
        dt = isodate.parse_datetime(datetime_str)

        # Ensure timezone-aware datetime
        if dt.tzinfo is None:
            # Assume UTC if no timezone specified
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            # Convert to UTC
            dt = dt.astimezone(timezone.utc)

        return dt

    except (isodate.ISO8601Error, ValueError) as e:
        raise TimeParsingError(f"Invalid ISO 8601 datetime format '{datetime_str}': {e}")


@validate_call
def format_datetime_iso8601(dt: datetime) -> str:
    """
    Format datetime to ISO 8601 string with microsecond precision.

    This function ensures consistent datetime formatting across the application
    following KQL/Log Analytics recommendations for ISO 8601 format with microseconds.

    Format: yyyy-MM-ddTHH:mm:ss.ffffffZ
    Example: 2025-10-31T23:59:59.123456Z

    Args:
        dt: Datetime to format (will be converted to UTC if not already)

    Returns:
        ISO 8601 formatted string with microsecond precision and UTC timezone (Z suffix)

    Examples:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2025, 10, 31, 23, 59, 59, 123456, tzinfo=timezone.utc)
        >>> format_datetime_iso8601(dt)
        '2025-10-31T23:59:59.123456Z'
    """
    # Ensure datetime is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC
        dt = dt.astimezone(timezone.utc)

    # Format with microsecond precision
    # isoformat() gives us: 2025-10-31T23:59:59.123456+00:00
    # We need: 2025-10-31T23:59:59.123456Z
    iso_str = dt.isoformat(timespec="microseconds")

    # Replace +00:00 with Z for UTC
    if iso_str.endswith("+00:00"):
        iso_str = iso_str[:-6] + "Z"

    return iso_str


@validate_call
def validate_time_range(
    start_time: datetime, end_time: datetime, allow_future_end: bool = False
) -> None:
    """
    Validate time range constraints.

    Args:
        start_time: Start datetime (must be UTC)
        end_time: End datetime (must be UTC)
        allow_future_end: Whether to allow end_time in the future

    Raises:
        InvalidTimeRangeError: If time range is invalid
    """
    # Ensure both times are timezone-aware
    if start_time.tzinfo is None or end_time.tzinfo is None:
        raise InvalidTimeRangeError("Both start_time and end_time must be timezone-aware")

    # Convert to UTC for comparison
    start_utc = start_time.astimezone(timezone.utc)
    end_utc = end_time.astimezone(timezone.utc)
    now_utc = datetime.now(timezone.utc)

    # Check that start_time is before end_time
    if start_utc >= end_utc:
        raise InvalidTimeRangeError(f"Start time ({start_utc}) must be before end time ({end_utc})")

    # Check that end_time is not in the future (unless allowed)
    if not allow_future_end and end_utc > now_utc:
        raise InvalidTimeRangeError(
            f"End time ({end_utc}) cannot be in the future (current: {now_utc})"
        )


@validate_call
def calculate_time_range_from_lookback(
    lookback_period: str, reference_time: Optional[datetime] = None
) -> Tuple[datetime, datetime]:
    """
    Calculate start and end times from lookback period.

    Args:
        lookback_period: ISO 8601 duration string (e.g., "P7D", "PT24H")
        reference_time: Reference time (defaults to now in UTC)

    Returns:
        Tuple of (start_time, end_time) in UTC

    Raises:
        TimeParsingError: If lookback period is invalid
    """
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)

    # Ensure reference time is UTC
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)
    else:
        reference_time = reference_time.astimezone(timezone.utc)

    # Parse lookback duration
    lookback_duration = parse_iso8601_duration(lookback_period)

    # Calculate start time
    start_time = reference_time - lookback_duration
    end_time = reference_time

    return start_time, end_time


@validate_call
def calculate_batches(
    start_time: datetime,
    end_time: datetime,
    batch_size: timedelta,
    min_batch_size: Optional[timedelta] = None,
) -> list[Tuple[datetime, datetime]]:
    """
    Calculate time-based batches from start to end time.

    Args:
        start_time: Batch start time (UTC)
        end_time: Batch end time (UTC)
        batch_size: Size of each batch
        min_batch_size: Minimum batch size (defaults to 1 hour)

    Returns:
        List of (batch_start, batch_end) tuples

    Raises:
        InvalidTimeRangeError: If time range is invalid
    """
    if min_batch_size is None:
        min_batch_size = timedelta(hours=1)

    # Validate time range
    validate_time_range(start_time, end_time, allow_future_end=False)

    batches = []
    current_time = start_time

    while current_time < end_time:
        batch_end = min(current_time + batch_size, end_time)
        batch_duration = batch_end - current_time

        # Only include batch if it meets minimum size requirement
        if batch_duration >= min_batch_size:
            # Subtract 1 microsecond from batch_end to prevent overlapping boundaries
            # Azure Monitor queries are inclusive on both start and end times
            # This ensures records at exact boundary timestamps don't appear in multiple batches
            # Exception: Don't subtract from the final end_time as it's already the desired boundary
            if batch_end < end_time:
                adjusted_batch_end = batch_end - timedelta(microseconds=1)
            else:
                adjusted_batch_end = batch_end
            batches.append((current_time, adjusted_batch_end))

        current_time = batch_end

    return batches


@validate_call
def format_datetime_for_display(dt: datetime, local_timezone: bool = True) -> str:
    """
    Format datetime for user display.

    Args:
        dt: Datetime to format
        local_timezone: Whether to convert to local timezone for display

    Returns:
        Formatted datetime string
    """
    if local_timezone:
        # Convert to local timezone for display
        local_dt = dt.astimezone()
        return local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    else:
        # Display in UTC
        utc_dt = dt.astimezone(timezone.utc)
        return utc_dt.strftime("%Y-%m-%d %H:%M:%S UTC")


@validate_call
def format_timedelta_for_display(td: timedelta) -> str:
    """
    Format timedelta for user display.

    Args:
        td: Timedelta to format

    Returns:
        Human-readable string (e.g., "2 days, 3 hours")
    """
    total_seconds = int(td.total_seconds())

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, SECONDS_PER_HOUR)
    minutes, seconds = divmod(remainder, 60)

    parts = []

    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds and not (days or hours):  # Only show seconds if no larger units
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

    return ", ".join(parts) if parts else "0 seconds"
