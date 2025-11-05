# Environment Variables Reference

This document describes all available environment variables for the Microsoft Sentinel Log Aggregator CLI, following the priority order you requested:

## Priority Order

1. **Command Line Arguments** - Highest priority
2. **Environment Variables** - Second priority
3. **`.env` File Variables** - Third priority
4. **Default Values** - Lowest priority

## Complete Parameter Reference

| CLI Parameter | Environment Variable | .env File | Default | Description |
|---------------|---------------------|-----------|---------|-------------|
| `--workspace-config` | N/A | N/A | Required | Path to workspace configuration file (file paths not suitable for env vars) |
| **Time Range Options (mutually exclusive)** |
| `--lookback-period` | `LOOKBACK_PERIOD` | ✅ | `P30D` | ISO 8601 duration to look back |
| `--start-time` | `START_TIME` | ✅ | None | ISO 8601 start datetime |
| `--end-time` | `END_TIME` | ✅ | None | ISO 8601 end datetime |
| `--use-last-successful` | `USE_LAST_SUCCESSFUL` | ✅ | `false` | Continue from last successful run |
| **Batch Processing** |
| `--batch-time-size` | `BATCH_TIME_SIZE` | ✅ | `PT24H` | ISO 8601 duration for batch size |
| **Execution Control** |
| `--queries` | `QUERIES` | ✅ | All | Specific queries to run (comma-separated) |
| `--workspaces` | `WORKSPACES` | ✅ | All | Specific workspaces to process (comma-separated) |
| `--dry-run` | `DRY_RUN` | ✅ | `false` | Validate and show what would be executed |
| `--parallel`/`--no-parallel` | `PARALLEL` | ✅ | `true` | Enable parallel execution |
| `--max-concurrent-queries` | `MAX_CONCURRENT_QUERIES` | ✅ | `5` | Maximum parallel workers |
| **Health Logging** |
| `--health-to-sentinel` | `HEALTH_TO_SENTINEL` | ✅ | `false` | Enable health tracking to Sentinel table |
| **Query Configuration** |
| `--query-timeout-seconds` | `QUERY_TIMEOUT_SECONDS` | ✅ | `300` | Query timeout in seconds |
| `--max-retries` | `MAX_RETRIES` | ✅ | `3` | Maximum retry attempts |
| `--retry-delay-seconds` | `RETRY_DELAY_SECONDS` | ✅ | `5` | Delay between retries in seconds |
| **Required Azure Configuration** |
| `--dcr-endpoint` | `DCR_LOGS_INGESTION_ENDPOINT` | ✅ | Required | Azure Monitor DCR logs ingestion endpoint |
| `--dcr-immutable-id` | `DCR_IMMUTABLE_ID` | ✅ | Required | Data Collection Rule immutable ID |
| **Global Options** |
| `--log-level` | `LOG_LEVEL` | ✅ | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Example `.env` File

```bash
# Azure Data Collection Rule Configuration
# Required: Set these to your actual Azure DCR endpoint and rule ID
DCR_LOGS_INGESTION_ENDPOINT=https://your-dcr-endpoint.monitor.azure.com
DCR_IMMUTABLE_ID=dcr-your-rule-id

# Time Range Configuration (mutually exclusive with start/end times)
# Use lookback period OR explicit start/end times, not both
LOOKBACK_PERIOD=P30D
START_TIME=
END_TIME=
USE_LAST_SUCCESSFUL=false

# Batch Processing Configuration
BATCH_TIME_SIZE=PT24H

# Execution Control Configuration
QUERIES=
WORKSPACES=
DRY_RUN=false
PARALLEL=true
MAX_CONCURRENT_QUERIES=5

# Query Execution Configuration
QUERY_TIMEOUT_SECONDS=300
MAX_RETRIES=3
RETRY_DELAY_SECONDS=5

# Health Logging Configuration
HEALTH_TO_SENTINEL=false

# Logging Configuration
LOG_LEVEL=INFO
```

## Usage Examples

### Using Command Line Arguments Only
```bash
sentinel-aggregator run --workspace-config workspaces.yaml \
  --dcr-endpoint "https://myworkspace-abcd.centralus-1.ingest.monitor.azure.com" \
  --dcr-immutable-id "dcr-12345678901234567890" \
  --lookback-period "P7D" \
  --batch-time-size "PT12H" \
  --queries "incident_summary,alert_summary" \
  --parallel \
  --max-concurrent-queries 10
```

### Using Environment Variables
```bash
# Set environment variables
export DCR_LOGS_INGESTION_ENDPOINT="https://myworkspace-abcd.centralus-1.ingest.monitor.azure.com"
export DCR_IMMUTABLE_ID="dcr-12345678901234567890"
export LOOKBACK_PERIOD="P7D"
export BATCH_TIME_SIZE="PT12H"
export QUERIES="incident_summary,alert_summary"
export PARALLEL="true"
export MAX_CONCURRENT_QUERIES="10"

# Run with minimal command line
sentinel-aggregator run --workspace-config workspaces.yaml
```

### Using .env File
```bash
# Create .env file with your configuration
cat > .env << EOF
DCR_LOGS_INGESTION_ENDPOINT=https://myworkspace-abcd.centralus-1.ingest.monitor.azure.com
DCR_IMMUTABLE_ID=dcr-12345678901234567890
LOOKBACK_PERIOD=P7D
BATCH_TIME_SIZE=PT12H
QUERIES=incident_summary,alert_summary
PARALLEL=true
MAX_CONCURRENT_QUERIES=10
EOF

# Run with minimal command line
sentinel-aggregator run --workspace-config workspaces.yaml
```

### Mixed Priority Example
```bash
# .env file has:
# LOOKBACK_PERIOD=P30D
# MAX_CONCURRENT_QUERIES=5

# Environment variable overrides .env:
export LOOKBACK_PERIOD="P7D"

# Command line overrides both:
sentinel-aggregator run --workspace-config workspaces.yaml --max-concurrent-queries 10

# Result: LOOKBACK_PERIOD=P7D (from env var), MAX_CONCURRENT_QUERIES=10 (from CLI)
```

## Boolean Values

For boolean environment variables, the following values are supported:

- **True**: `true`, `True`, `TRUE`, `1`, `yes`, `Yes`, `YES`
- **False**: `false`, `False`, `FALSE`, `0`, `no`, `No`, `NO`

## Special Cases

### Time Range Mutual Exclusivity
- `LOOKBACK_PERIOD` and `START_TIME`/`END_TIME` are mutually exclusive
- If both are provided, command line arguments take precedence
- If `USE_LAST_SUCCESSFUL=true`, it overrides other time configurations

### Parallel Execution
- Use `--parallel` to enable (default)
- Use `--no-parallel` to disable
- Environment variable: `PARALLEL=true` or `PARALLEL=false`

### Query and Workspace Filtering
- Leave `QUERIES` empty to run all available queries
- Leave `WORKSPACES` empty to process all configured workspaces
- Use comma-separated values for multiple items: `query1,query2,query3`

## Validation

All parameters are validated according to their types and constraints:

- **ISO 8601 durations**: Must be valid durations (e.g., `P30D`, `PT24H`)
- **ISO 8601 datetimes**: Must be valid timestamps (e.g., `2025-01-01T00:00:00Z`)
- **URLs**: Must be valid HTTPS URLs for DCR endpoints
- **DCR IDs**: Must match pattern `dcr-[a-f0-9]{32}` or test patterns
- **Integers**: Must be positive integers within specified ranges

## Legacy Compatibility

The following legacy environment variables are still supported but deprecated:

- `DCR_RULE_ID` → use `DCR_IMMUTABLE_ID`
- `DAYS_BACK` → use `LOOKBACK_PERIOD`
- `BATCH_HOURS` → use `BATCH_TIME_SIZE`

## Azure Authentication

Azure authentication is handled automatically by `DefaultAzureCredential` and does not require environment variables. However, you can provide these if needed:

- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_TENANT_ID`

## Next Steps

- [CLI Usage Documentation](cli-usage.md)
- [Configuration Guide](configuration.md)
- [Troubleshooting](troubleshooting.md)