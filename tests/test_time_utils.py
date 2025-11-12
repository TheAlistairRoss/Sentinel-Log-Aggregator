"""
Tests for time_utils module - ISO 8601 duration and datetime parsing utilities.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from sentinel_log_aggregator.time_utils import (
    InvalidTimeRangeError,
    TimeParsingError,
    calculate_batches,
    format_datetime_for_display,
    parse_iso8601_datetime,
    parse_iso8601_duration,
    validate_batch_time_size,
    validate_time_range,
)


class TestISO8601DurationParsing:
    """Test ISO 8601 duration parsing functionality."""

    def test_parse_basic_durations(self):
        """Test parsing basic ISO 8601 durations."""
        # Days
        assert parse_iso8601_duration("P1D") == timedelta(days=1)
        assert parse_iso8601_duration("P7D") == timedelta(days=7)
        assert parse_iso8601_duration("P30D") == timedelta(days=30)

        # Hours
        assert parse_iso8601_duration("PT1H") == timedelta(hours=1)
        assert parse_iso8601_duration("PT12H") == timedelta(hours=12)
        assert parse_iso8601_duration("PT24H") == timedelta(hours=24)

        # Minutes
        assert parse_iso8601_duration("PT30M") == timedelta(minutes=30)
        assert parse_iso8601_duration("PT90M") == timedelta(minutes=90)

        # Seconds
        assert parse_iso8601_duration("PT30S") == timedelta(seconds=30)
        assert parse_iso8601_duration("PT3600S") == timedelta(seconds=3600)

    def test_parse_combined_durations(self):
        """Test parsing combined ISO 8601 durations."""
        # Days and hours
        assert parse_iso8601_duration("P1DT12H") == timedelta(days=1, hours=12)
        assert parse_iso8601_duration("P7DT6H") == timedelta(days=7, hours=6)

        # Hours and minutes
        assert parse_iso8601_duration("PT2H30M") == timedelta(hours=2, minutes=30)
        assert parse_iso8601_duration("PT1H45M") == timedelta(hours=1, minutes=45)

        # Complex combinations
        assert parse_iso8601_duration("P1DT2H30M15S") == timedelta(
            days=1, hours=2, minutes=30, seconds=15
        )

    def test_parse_invalid_durations(self):
        """Test parsing invalid ISO 8601 durations raises errors."""
        invalid_durations = [
            "",  # Empty string
            "1D",  # Missing P
            "P",  # Empty duration
            "P1Y",  # Years not supported by timedelta
            "P1M",  # Months not supported by timedelta
            "PXD",  # Invalid number
            "PT1X",  # Invalid time unit
            "P-1D",  # Negative values
            "1PT1H",  # Invalid format
        ]

        for invalid_duration in invalid_durations:
            with pytest.raises(TimeParsingError):
                parse_iso8601_duration(invalid_duration)

    def test_parse_edge_cases(self):
        """Test edge cases for ISO 8601 duration parsing."""
        # Zero duration
        assert parse_iso8601_duration("P0D") == timedelta(0)
        assert parse_iso8601_duration("PT0H") == timedelta(0)

        # Large values
        assert parse_iso8601_duration("P365D") == timedelta(days=365)
        assert parse_iso8601_duration("PT8760H") == timedelta(hours=8760)


class TestBatchTimeSizeValidation:
    """Test batch time size validation."""

    def test_valid_batch_sizes(self):
        """Test valid batch time sizes."""
        valid_sizes = [
            ("PT1H", timedelta(hours=1)),
            ("PT2H", timedelta(hours=2)),
            ("PT6H", timedelta(hours=6)),
            ("PT12H", timedelta(hours=12)),
            ("PT24H", timedelta(hours=24)),
            ("P1D", timedelta(days=1)),  # Same as PT24H
        ]

        for size_str, expected in valid_sizes:
            result = validate_batch_time_size(size_str)
            assert result == expected

    def test_invalid_batch_sizes(self):
        """Test invalid batch time sizes raise errors."""
        invalid_sizes = [
            "PT30M",  # Not a multiple of 1 hour
            "PT90M",  # 1.5 hours, not whole hours
            "PT25H",  # Greater than 24 hours
            "P2D",  # Greater than 24 hours
            "PT0H",  # Zero duration
            "P0D",  # Zero duration
            "PT-1H",  # Negative duration
        ]

        for invalid_size in invalid_sizes:
            with pytest.raises(TimeParsingError):
                validate_batch_time_size(invalid_size)

    def test_batch_size_constraints_message(self):
        """Test batch size constraint error messages."""
        with pytest.raises(TimeParsingError, match="must be at least 1 hour"):
            validate_batch_time_size("PT30M")

        with pytest.raises(TimeParsingError, match="must be at most 24 hours"):
            validate_batch_time_size("PT25H")

        with pytest.raises(TimeParsingError, match="must be a multiple of 1 hour"):
            validate_batch_time_size("PT90M")
            validate_batch_time_size("PT0H")


class TestISO8601DateTimeParsing:
    """Test ISO 8601 datetime parsing functionality."""

    def test_parse_basic_datetimes(self):
        """Test parsing basic ISO 8601 datetime strings."""
        # UTC timezone
        dt = parse_iso8601_datetime("2025-11-03T10:30:00Z")
        assert dt.year == 2025
        assert dt.month == 11
        assert dt.day == 3
        assert dt.hour == 10  # Should remain 10 since it's already UTC
        assert dt.minute == 30
        assert dt.second == 0
        assert dt.tzinfo == timezone.utc

        # With timezone offset - should be converted to UTC
        dt = parse_iso8601_datetime("2025-11-03T10:30:00+05:00")
        assert dt.year == 2025
        assert dt.month == 11
        assert dt.day == 3
        assert dt.hour == 5  # 10:30+05:00 becomes 05:30 UTC
        assert dt.minute == 30
        assert dt.second == 0
        assert dt.tzinfo == timezone.utc

    def test_parse_datetime_with_microseconds(self):
        """Test parsing datetime with microseconds."""
        dt = parse_iso8601_datetime("2025-11-03T10:30:00.123456Z")
        assert dt.microsecond == 123456

        dt = parse_iso8601_datetime("2025-11-03T10:30:00.123Z")
        assert dt.microsecond == 123000

    def test_parse_invalid_datetimes(self):
        """Test parsing invalid datetime strings raises errors."""
        invalid_datetimes = [
            "",
            "2025-11-03",  # Date only
            "10:30:00",  # Time only
            "2025-13-03T10:30:00Z",  # Invalid month
            "2025-11-32T10:30:00Z",  # Invalid day
            "2025-11-03T25:30:00Z",  # Invalid hour
            "2025-11-03T10:60:00Z",  # Invalid minute
            "2025-11-03T10:30:60Z",  # Invalid second
            "2025/11/03T10:30:00Z",  # Wrong date separator
            "2025-11-03 10:30:00Z",  # Wrong datetime separator
        ]

        for invalid_datetime in invalid_datetimes:
            with pytest.raises(TimeParsingError):
                parse_iso8601_datetime(invalid_datetime)


class TestTimeRangeValidation:
    """Test time range validation functionality."""

    def test_valid_time_ranges(self):
        """Test valid time ranges pass validation."""
        start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 3, 0, 0, 0, tzinfo=timezone.utc)

        # Normal case
        validate_time_range(start, end)

        # Allow future end time
        future_end = datetime(2025, 12, 1, 0, 0, 0, tzinfo=timezone.utc)
        validate_time_range(start, future_end, allow_future_end=True)

    def test_invalid_time_ranges(self):
        """Test invalid time ranges raise errors."""
        start = datetime(2025, 11, 3, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)  # End before start

        with pytest.raises(InvalidTimeRangeError, match="Start time .* must be before end time"):
            validate_time_range(start, end)

    @patch("sentinel_log_aggregator.time_utils.datetime")
    def test_future_end_time_validation(self, mock_datetime):
        """Test future end time validation."""
        # Mock current time
        mock_now = datetime(2025, 11, 3, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        future_end = datetime(2025, 11, 4, 0, 0, 0, tzinfo=timezone.utc)  # Future

        # Should raise error when future not allowed
        with pytest.raises(InvalidTimeRangeError, match="End time .* cannot be in the future"):
            validate_time_range(start, future_end, allow_future_end=False)

        # Should pass when future allowed
        validate_time_range(start, future_end, allow_future_end=True)


class TestBatchCalculation:
    """Test batch calculation functionality."""

    def test_calculate_simple_batches(self):
        """Test calculating simple batch ranges."""
        start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 3, 0, 0, 0, tzinfo=timezone.utc)
        batch_size = timedelta(hours=24)

        batches = calculate_batches(start, end, batch_size)

        assert len(batches) == 2
        # First batch (intermediate): adjusted by -1µs
        assert batches[0] == (
            datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 11, 1, 23, 59, 59, 999999, tzinfo=timezone.utc),
        )
        # Last batch: ends at end_time (not adjusted)
        assert batches[1] == (
            datetime(2025, 11, 2, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 11, 3, 0, 0, 0, tzinfo=timezone.utc),
        )

    def test_calculate_partial_batches(self):
        """Test calculating batches with partial final batch."""
        start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 1, 18, 0, 0, tzinfo=timezone.utc)  # 18 hours
        batch_size = timedelta(hours=12)

        batches = calculate_batches(start, end, batch_size)

        assert len(batches) == 2
        # First batch (intermediate): adjusted by -1µs
        assert batches[0] == (
            datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 11, 1, 11, 59, 59, 999999, tzinfo=timezone.utc),
        )
        # Last batch: ends at end_time (not adjusted)
        assert batches[1] == (
            datetime(2025, 11, 1, 12, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 11, 1, 18, 0, 0, tzinfo=timezone.utc),
        )

    def test_calculate_single_batch(self):
        """Test calculating when time range fits in single batch."""
        start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 1, 6, 0, 0, tzinfo=timezone.utc)  # 6 hours
        batch_size = timedelta(hours=12)

        batches = calculate_batches(start, end, batch_size)

        assert len(batches) == 1
        # Single batch is also the last batch: ends at end_time (not adjusted)
        assert batches[0] == (start, end)

    def test_calculate_empty_range(self):
        """Test calculating batches for very short time range."""
        start = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 1, 0, 30, 0, tzinfo=timezone.utc)  # 30 minutes
        batch_size = timedelta(hours=1)

        # This should create no batches because the range is shorter than min_batch_size (1 hour)
        batches = calculate_batches(start, end, batch_size)

        assert len(batches) == 0


class TestDateTimeFormatting:
    """Test datetime formatting functionality."""

    def test_format_datetime_display(self):
        """Test formatting datetime for display."""
        dt = datetime(2025, 11, 3, 14, 30, 45, tzinfo=timezone.utc)

        # Test with UTC display (no local conversion)
        formatted = format_datetime_for_display(dt, local_timezone=False)
        assert formatted == "2025-11-03 14:30:45 UTC"

        # Test with local timezone (will include timezone name)
        formatted_local = format_datetime_for_display(dt, local_timezone=True)
        assert "2025-11-03" in formatted_local  # Date should be consistent
        assert (
            "14:30:45" in formatted_local
            or "09:30:45" in formatted_local
            or "05:30:45" in formatted_local
        )  # Time may vary by local TZ

    def test_format_datetime_with_timezone(self):
        """Test formatting datetime with timezone info."""
        from datetime import timezone

        dt = datetime(2025, 11, 3, 14, 30, 45, tzinfo=timezone.utc)

        formatted = format_datetime_for_display(dt)
        # Should handle timezone appropriately
        assert "2025-11-03" in formatted
        assert "14:30:45" in formatted


class TestErrorHandling:
    """Test error handling in time utilities."""

    def test_time_parsing_error_attributes(self):
        """Test TimeParsingError has proper attributes."""
        error = TimeParsingError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_invalid_time_range_error_attributes(self):
        """Test InvalidTimeRangeError has proper attributes."""
        error = InvalidTimeRangeError("Test range error")
        assert str(error) == "Test range error"
        assert isinstance(error, Exception)

    def test_error_propagation(self):
        """Test that errors propagate properly from underlying functions."""
        # Test that invalid ISO format raises TimeParsingError
        with pytest.raises(TimeParsingError):
            parse_iso8601_duration("invalid")

        with pytest.raises(TimeParsingError):
            parse_iso8601_datetime("invalid")

        with pytest.raises(TimeParsingError):
            validate_batch_time_size("invalid")


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_typical_batch_processing_scenario(self):
        """Test a typical batch processing scenario."""
        # Parse lookback period
        lookback = parse_iso8601_duration("P7D")
        assert lookback == timedelta(days=7)

        # Parse batch size
        batch_size = validate_batch_time_size("PT12H")
        assert batch_size == timedelta(hours=12)

        # Calculate time range
        end_time = datetime(2025, 11, 3, 0, 0, 0, tzinfo=timezone.utc)
        start_time = end_time - lookback

        # Validate range
        validate_time_range(start_time, end_time)

        # Calculate batches
        batches = calculate_batches(start_time, end_time, batch_size)

        # Should have 14 batches (7 days * 2 batches per day)
        assert len(batches) == 14

        # First batch should start at calculated start time
        assert batches[0][0] == start_time

        # Last batch should end at end_time (not adjusted)
        assert batches[-1][1] == end_time

    def test_explicit_time_range_scenario(self):
        """Test explicit time range scenario."""
        # Parse explicit times
        start_time = parse_iso8601_datetime("2025-10-01T00:00:00Z")
        end_time = parse_iso8601_datetime("2025-10-02T00:00:00Z")

        # Validate range
        validate_time_range(start_time, end_time, allow_future_end=True)

        # Parse batch size
        batch_size = validate_batch_time_size("PT6H")

        # Calculate batches
        batches = calculate_batches(start_time, end_time, batch_size)

        # Should have 4 batches (24 hours / 6 hours)
        assert len(batches) == 4

        # Verify batch continuity (batches have 1µs gap to prevent overlapping boundaries)
        for i in range(len(batches) - 1):
            assert batches[i][1] + timedelta(microseconds=1) == batches[i + 1][0]

    def test_format_for_logging_scenario(self):
        """Test formatting datetime for logging scenario."""
        # Parse and format various datetime strings
        test_cases = [
            "2025-11-03T10:30:00Z",
            "2025-11-03T14:45:30.123Z",
            "2025-11-03T08:15:00+02:00",
        ]

        for iso_string in test_cases:
            dt = parse_iso8601_datetime(iso_string)
            formatted = format_datetime_for_display(dt)

            # Should be formatted consistently
            assert len(formatted) >= 19  # At least YYYY-MM-DD HH:MM:SS
            assert formatted[4] == "-"  # Year separator
            assert formatted[7] == "-"  # Month separator
            assert formatted[10] == " "  # Date-time separator
            assert formatted[13] == ":"  # Hour separator
            assert formatted[16] == ":"  # Minute separator
