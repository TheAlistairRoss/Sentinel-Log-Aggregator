"""
Sentinel Log Aggregator Constants

Centralized configuration values and constants used throughout the application.
"""

# ============================================================================
# Health Logging Configuration
# ============================================================================

# Custom Log Analytics table name for health/operational logging
HEALTH_TABLE_NAME = "SentinelAggregator_Health_CL"

# DCR stream name for health log ingestion (must match DCR configuration)
HEALTH_STREAM_NAME = "Custom-SentinelAggregator_Health_CL"


# ============================================================================
# Default Time Configuration
# ============================================================================

# Default lookback period in ISO 8601 duration format (30 days)
DEFAULT_LOOKBACK_PERIOD = "P30D"

# Default batch time size in ISO 8601 duration format (24 hours)
DEFAULT_BATCH_TIME_SIZE = "PT24H"


# ============================================================================
# Default Query Execution Configuration
# ============================================================================

# Default number of queries that can execute concurrently
DEFAULT_MAX_CONCURRENT_QUERIES = 5

# Default query timeout in seconds (5 minutes)
DEFAULT_QUERY_TIMEOUT_SECONDS = 300

# Default maximum number of retry attempts for failed operations
DEFAULT_MAX_RETRIES = 3

# Default delay between retry attempts in seconds
DEFAULT_RETRY_DELAY_SECONDS = 5


# ============================================================================
# Azure Monitor / Log Analytics Limits
# ============================================================================

# Maximum records allowed per batch upload to Azure Monitor DCR
MAX_RECORDS_PER_BATCH = 500000

# Maximum upload payload size in MB for Azure Monitor DCR
MAX_UPLOAD_SIZE_MB = 200

# Maximum KQL query size in characters (100KB)
MAX_QUERY_SIZE = 100000

# Default page size for paginated queries
DEFAULT_PAGE_SIZE = 1000


# ============================================================================
# Validation Limits
# ============================================================================

# Maximum length for user input strings
MAX_USER_INPUT_LENGTH = 10000

# Maximum length for query parameter values
MAX_PARAMETER_VALUE_LENGTH = 1000

# Minimum query timeout in seconds
MIN_QUERY_TIMEOUT = 30

# Maximum query timeout in seconds (1 hour)
MAX_QUERY_TIMEOUT = 3600

# Maximum upload timeout in seconds (30 minutes)
MAX_UPLOAD_TIMEOUT = 1800


# ============================================================================
# Time Calculation Constants
# ============================================================================

# Seconds per hour (for time conversions)
SECONDS_PER_HOUR = 3600
