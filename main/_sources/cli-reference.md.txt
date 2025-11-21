# CLI Reference

Complete command-line interface reference for Sentinel Log Aggregator.

## Table of Contents

- [Command Structure](#command-structure)
- [Global Options](#global-options)
- [Commands](#commands)
  - [run](#run-command)
  - [validate](#validate-command)
  - [health](#health-command)
  - [test-health](#test-health-command)
  - [verify-health](#verify-health-command)
  - [query-status](#query-status-command)
- [Environment Variables](#environment-variables)
- [Exit Codes](#exit-codes)
- [Examples](#examples)

## Command Structure

```
sentinel-aggregator [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]
```

## Global Options

These options apply to all commands and must be specified before the command name.

### `--version`

Display the installed version and exit.

```bash
sentinel-aggregator --version
```

**Output**:
```
sentinel-log-aggregator 1.0.0
```

### `--log-level LEVEL`

Set the logging verbosity level.

**Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

**Default**: `INFO`

**Example**:
```bash
sentinel-aggregator --log-level DEBUG run --workspace-config workspaces.yaml
```

**Use cases**:
- `DEBUG`: Troubleshooting, development
- `INFO`: Normal operations (default)
- `WARNING`: Production with minimal logging
- `ERROR`: Only log errors
- `CRITICAL`: Only log critical failures

### `--log-format FORMAT`

Set the log output format.

**Options**: `text`, `json`

**Default**: `text`

**Example**:
```bash
# JSON format for log aggregation systems
sentinel-aggregator --log-format json run --workspace-config workspaces.yaml

# Human-readable text format
sentinel-aggregator --log-format text run --workspace-config workspaces.yaml
```

**JSON output example**:
```json
{"timestamp":"2025-11-07T10:00:00Z","level":"INFO","message":"Starting aggregation","job_id":"abc-123"}
```

### `--env-file PATH`

Load environment variables from a file.

**Default**: None (uses system environment variables)

**Example**:
```bash
sentinel-aggregator --env-file .env run --workspace-config workspaces.yaml
sentinel-aggregator --env-file .env.production run --workspace-config workspaces.yaml
```

**.env file format**:
```bash
DCR_ENDPOINT=https://YOUR-DCE.azure.com
DCR_IMMUTABLE_ID=dcr-YOUR-ID
LOOKBACK_PERIOD=P1D
BATCH_TIME_SIZE=PT24H
MAX_CONCURRENT_QUERIES=5
LOG_LEVEL=INFO
```

---

## Commands

### `run` Command

Execute log aggregation queries.

#### Syntax

```bash
sentinel-aggregator run --workspace-config PATH [OPTIONS]
```

#### Required Arguments

##### `--workspace-config PATH` / `-w PATH`

Path to the workspace configuration YAML file.

**Required**: Yes

**Example**:
```bash
sentinel-aggregator run --workspace-config workspaces.yaml
sentinel-aggregator run -w config/prod-workspaces.yaml
```

#### Time Range Options

Specify the time range for queries. Use **either** `--lookback-period` **or** `--start-time` + `--end-time`.

##### `--lookback-period DURATION` / `-l DURATION`

ISO 8601 duration string relative to current time.

**Format**: `PnDTnHnMnS` where:
- `P` = Period indicator
- `nD` = Number of days
- `T` = Time indicator (required for hours/minutes/seconds)
- `nH` = Number of hours
- `nM` = Number of minutes
- `nS` = Number of seconds

**Examples**:
```bash
# Last 1 day
sentinel-aggregator run -w workspaces.yaml --lookback-period P1D

# Last 7 days
sentinel-aggregator run -w workspaces.yaml --lookback-period P7D

# Last 12 hours
sentinel-aggregator run -w workspaces.yaml --lookback-period PT12H

# Last 30 minutes
sentinel-aggregator run -w workspaces.yaml --lookback-period PT30M
```

##### `--start-time DATETIME`

Specific start time in ISO 8601 format.

**Format**: `YYYY-MM-DDTHH:MM:SSZ`

**Must be used with**: `--end-time`

**Example**:
```bash
sentinel-aggregator run \
    -w workspaces.yaml \
    --start-time 2025-11-01T00:00:00Z \
    --end-time 2025-11-07T23:59:59Z
```

##### `--end-time DATETIME`

Specific end time in ISO 8601 format.

**Format**: `YYYY-MM-DDTHH:MM:SSZ`

**Must be used with**: `--start-time`

**Example**:
```bash
# Process October 2025 data
sentinel-aggregator run \
    -w workspaces.yaml \
    --start-time 2025-10-01T00:00:00Z \
    --end-time 2025-10-31T23:59:59Z
```

#### Batch Processing Options

##### `--batch-time-size DURATION`

Split large time ranges into batches of this size.

**Format**: ISO 8601 duration string

**Default**: `PT24H` (24 hours)

**Environment variable**: `BATCH_TIME_SIZE`

**Examples**:
```bash
# 12-hour batches (for large datasets)
sentinel-aggregator run -w workspaces.yaml --lookback-period P30D --batch-time-size PT12H

# 7-day batches (for smaller datasets)
sentinel-aggregator run -w workspaces.yaml --lookback-period P90D --batch-time-size P7D

# 6-hour batches (very large datasets)
sentinel-aggregator run -w workspaces.yaml --lookback-period P7D --batch-time-size PT6H
```

**Use cases**:
- Large datasets: Smaller batches (PT6H, PT12H)
- Small datasets: Larger batches (P7D)
- Memory constraints: Smaller batches
- Performance: Balance batch size with API overhead

##### `--max-concurrent-queries N`

Maximum number of concurrent query executions.

**Type**: Integer

**Default**: `5`

**Range**: 1-20 (recommended)

**Environment variable**: `MAX_CONCURRENT_QUERIES`

**Examples**:
```bash
# High-performance setup
sentinel-aggregator run -w workspaces.yaml --max-concurrent-queries 10

# Conservative setup (limited resources)
sentinel-aggregator run -w workspaces.yaml --max-concurrent-queries 2

# Default
sentinel-aggregator run -w workspaces.yaml --max-concurrent-queries 5
```

**Considerations**:
- Higher values: Faster processing, more memory, more API calls
- Lower values: Slower processing, less memory, fewer API calls
- Azure throttling: Monitor for 429 errors
- Memory: Each concurrent query consumes memory

#### Data Collection Rule Options

Required for uploading data to Azure Monitor.

##### `--dcr-endpoint URL`

Data Collection Endpoint URL.

**Required for upload**: Yes (unless `--dry-run`)

**Environment variable**: `DCR_ENDPOINT`

**Format**: `https://YOUR-DCE-NAME.REGION.ingest.monitor.azure.com`

**Example**:
```bash
sentinel-aggregator run \
    -w workspaces.yaml \
    --dcr-endpoint https://my-dce-abc123.eastus2.ingest.monitor.azure.com
```

**How to find**:
```bash
az monitor data-collection endpoint show \
    --name YOUR-DCE-NAME \
    --resource-group YOUR-RG \
    --query logsIngestion.endpoint
```

##### `--dcr-immutable-id ID`

Data Collection Rule immutable ID.

**Required for upload**: Yes (unless `--dry-run`)

**Environment variable**: `DCR_IMMUTABLE_ID`

**Format**: `dcr-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`

**Example**:
```bash
sentinel-aggregator run \
    -w workspaces.yaml \
    --dcr-immutable-id dcr-abcdef1234567890abcdef1234567890
```

**How to find**:
```bash
az monitor data-collection rule show \
    --name YOUR-DCR-NAME \
    --resource-group YOUR-RG \
    --query immutableId
```

#### Execution Options

##### `--dry-run`

Execute queries but do not upload data to Azure.

**Default**: `False` (upload enabled)

**Example**:
```bash
# Test queries without uploading
sentinel-aggregator run -w workspaces.yaml --lookback-period P1D --dry-run

# Production run (upload data)
sentinel-aggregator run -w workspaces.yaml --lookback-period P1D
```

**Use cases**:
- Testing configuration
- Validating queries
- Checking data volumes
- Development and debugging
- Dry-run before production

**Output differences**:
```
# Dry-run output
✅ Records Downloaded: 45 (not uploaded)

# Production output
✅ Records Uploaded: 45
```

#### Complete Example

```bash
sentinel-aggregator \
    --log-level INFO \
    --env-file .env.production \
    run \
    --workspace-config config/prod-workspaces.yaml \
    --lookback-period P7D \
    --batch-time-size PT12H \
    --max-concurrent-queries 5 \
    --dcr-endpoint https://my-dce.eastus2.ingest.monitor.azure.com \
    --dcr-immutable-id dcr-abc123
```

---

### `validate` Command

Validate configuration files without executing queries.

#### Syntax

```bash
sentinel-aggregator validate --workspace-config PATH [OPTIONS]
```

#### Required Arguments

##### `--workspace-config PATH` / `-w PATH`

Path to the workspace configuration YAML file to validate.

**Required**: Yes

**Example**:
```bash
sentinel-aggregator validate --workspace-config workspaces.yaml
sentinel-aggregator validate -w config/test-workspaces.yaml
```

#### Optional Arguments

All global options (`--log-level`, `--log-format`, `--env-file`) are supported.

#### Exit Codes

- `0`: Configuration is valid
- `1`: Configuration has errors

#### Output

**Valid configuration**:
```bash
$ sentinel-aggregator validate -w workspaces.yaml
✅ Client options validation successful
✅ Workspace configuration validation successful
```

**Invalid configuration**:
```bash
$ sentinel-aggregator validate -w workspaces.yaml
❌ Configuration validation failed:
   • Missing required field: customer_id in workspace 'prod-workspace'
   • Invalid resource_id format in workspace 'test-workspace'
   • Query 'invalid_query' not found in registry
```

#### Examples

```bash
# Validate production configuration
sentinel-aggregator validate --workspace-config workspaces-prod.yaml

# Validate with environment variables
sentinel-aggregator --env-file .env.production validate -w workspaces.yaml

# Validate with debug output
sentinel-aggregator --log-level DEBUG validate -w workspaces.yaml
```

#### Validation Checks

The validate command checks:

1. **Client Options**:
   - Time range configuration (lookback_period or start_time/end_time)
   - DCR configuration (if not dry-run)
   - Batch configuration
   - Concurrency limits

2. **Workspace Configuration**:
   - Required fields (resource_id, customer_id)
   - Resource ID format
   - Customer ID format (valid GUID)
   - Query references (queries exist in registry)
   - Parameter definitions

3. **File Accessibility**:
   - YAML file exists and is readable
   - YAML syntax is valid
   - Environment variables are accessible

---

### `health` Command

Check health logging configuration and table accessibility for workspaces.

#### Syntax

```bash
sentinel-aggregator health --workspace-config PATH [OPTIONS]
```

#### Required Arguments

##### `--workspace-config PATH` / `-w PATH`

Path to the workspace configuration YAML file.

**Required**: Yes

**Example**:
```bash
sentinel-aggregator health --workspace-config workspaces.yaml
sentinel-aggregator health -w config/prod-workspaces.yaml
```

#### Optional Arguments

All global options (`--log-level`, `--log-format`, `--env-file`) are supported.

#### Exit Codes

- `0`: All workspaces healthy
- `1`: One or more workspaces have health logging issues

#### Output

**All healthy**:
```bash
$ sentinel-aggregator health -w workspaces.yaml
✅ All workspaces have health logging configured correctly
   • ws-prod-soc: Custom-Reports_Health_CL table exists
   • ws-customer-a: Custom-Reports_Health_CL table exists
   • ws-customer-b: Custom-Reports_Health_CL table exists
```

**Issues found**:
```bash
$ sentinel-aggregator health -w workspaces.yaml
⚠️  Health logging issues detected:

❌ ws-prod-soc:
   • Custom-Reports_Health_CL table not found
   • Ensure health logging query has run at least once

✅ ws-customer-a: Healthy

❌ ws-customer-b:
   • Workspace not accessible
   • Check permissions (Log Analytics Reader required)
```

#### What It Checks

1. **Workspace Accessibility**: Verify authentication and permissions
2. **Health Log Table**: Check if `Custom-Reports_Health_CL` table exists
3. **Recent Data**: Verify recent health log entries (optional)

#### Examples

```bash
# Check health of all workspaces
sentinel-aggregator health -w workspaces.yaml

# Check health with detailed logging
sentinel-aggregator --log-level DEBUG health -w workspaces.yaml

# Check health using specific environment
sentinel-aggregator --env-file .env.production health -w workspaces-prod.yaml
```

#### Troubleshooting Health Issues

If health check fails:

1. **Table not found**: Run aggregation once to create the table
   ```bash
   sentinel-aggregator run -w workspaces.yaml --lookback-period PT1H
   ```

2. **Workspace not accessible**: Check authentication
   ```bash
   az login
   az account show
   ```

3. **Permission denied**: Grant Log Analytics Reader role
   ```bash
   az role assignment create \
       --assignee YOUR-PRINCIPAL-ID \
       --role "Log Analytics Reader" \
       --scope /subscriptions/.../workspaces/YOUR-WORKSPACE
   ```

---

### `test-health` Command

Send a test event to health logging table and optionally verify ingestion.

#### Syntax

```bash
sentinel-aggregator test-health --workspace-config PATH [OPTIONS]
```

#### Required Arguments

##### `--workspace-config PATH` / `-w PATH`

Path to the workspace configuration YAML file.

**Required**: Yes

**Example**:
```bash
sentinel-aggregator test-health --workspace-config workspaces.yaml
sentinel-aggregator test-health -w config/prod-workspaces.yaml
```

#### Optional Arguments

##### `--test-id ID`

Custom test identifier for tracking the test event.

**Default**: Auto-generated UUID

**Example**:
```bash
sentinel-aggregator test-health -w workspaces.yaml --test-id "manual-test-001"
```

##### `--verify`

Verify that the test event was successfully ingested after sending.

**Default**: `False` (send only, no verification)

**Example**:
```bash
# Send and verify
sentinel-aggregator test-health -w workspaces.yaml --verify

# Send only (no verification)
sentinel-aggregator test-health -w workspaces.yaml
```

##### `--max-wait SECONDS`

Maximum seconds to wait for verification when `--verify` is used.

**Type**: Integer

**Default**: `300` (5 minutes)

**Range**: 30-600 recommended

**Example**:
```bash
# Wait up to 2 minutes for verification
sentinel-aggregator test-health -w workspaces.yaml --verify --max-wait 120

# Wait up to 10 minutes for verification
sentinel-aggregator test-health -w workspaces.yaml --verify --max-wait 600
```

##### `--health-workspace-id ID`

Workspace ID where health table is located (if different from first data workspace).

**Format**: GUID

**Example**:
```bash
sentinel-aggregator test-health -w workspaces.yaml \
    --health-workspace-id aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
```

##### `--health-dcr-endpoint URL`

DCR endpoint for health logging (if different from main DCR).

**Format**: HTTPS URL

**Example**:
```bash
sentinel-aggregator test-health -w workspaces.yaml \
    --health-dcr-endpoint https://health-dce.eastus2.ingest.monitor.azure.com
```

##### `--health-dcr-immutable-id ID`

DCR immutable ID for health logging (if different from main DCR).

**Format**: dcr-* string

**Example**:
```bash
sentinel-aggregator test-health -w workspaces.yaml \
    --health-dcr-immutable-id dcr-health123
```

#### Exit Codes

- `0`: Test event sent successfully (and verified if `--verify` used)
- `1`: Test failed (send failed or verification failed)

#### Output

**Send only (no verification)**:
```bash
$ sentinel-aggregator test-health -w workspaces.yaml --test-id test-001
🧪 Testing health logging...
📤 Sending test health event...
✅ Test event sent successfully
   Test ID: test-001
   Correlation ID: 12345678-1234-1234-1234-123456789012
```

**Send and verify (success)**:
```bash
$ sentinel-aggregator test-health -w workspaces.yaml --verify
🧪 Testing health logging...
📤 Sending test health event...
✅ Test event sent successfully
   Test ID: a1b2c3d4-5678-90ab-cdef-123456789abc
🔍 Verifying test event ingestion...
⏳ Waiting for event to appear in health table (max 300 seconds)...
✅ Test event verified in health table
   Found after: 45 seconds
   Event timestamp: 2025-11-10T14:30:00Z
```

**Verification failure**:
```bash
$ sentinel-aggregator test-health -w workspaces.yaml --verify --max-wait 60
🧪 Testing health logging...
📤 Sending test health event...
✅ Test event sent successfully
   Test ID: test-002
🔍 Verifying test event ingestion...
⏳ Waiting for event to appear in health table (max 60 seconds)...
❌ Test event NOT found in health table after 60 seconds
💡 This may be due to:
   • Ingestion delay (can take 5-10 minutes)
   • DCR configuration issues
   • Workspace query permissions
Try running verification separately: sentinel-aggregator verify-health --test-id test-002
```

#### Examples

```bash
# Simple test (send only)
sentinel-aggregator test-health -w workspaces.yaml

# Test with custom ID
sentinel-aggregator test-health -w workspaces.yaml --test-id "prod-health-check-001"

# Send and verify (recommended)
sentinel-aggregator test-health -w workspaces.yaml --verify

# Send and verify with extended wait time
sentinel-aggregator test-health -w workspaces.yaml --verify --max-wait 600

# Test with separate health DCR
sentinel-aggregator test-health -w workspaces.yaml \
    --health-dcr-endpoint https://health-dce.eastus2.ingest.monitor.azure.com \
    --health-dcr-immutable-id dcr-health123 \
    --verify
```

#### Use Cases

1. **Manual Health Check**: Verify health logging is working correctly
2. **Post-Deployment Validation**: Confirm health logging after infrastructure changes
3. **Troubleshooting**: Test health logging when aggregation issues occur
4. **Monitoring Setup**: Validate health monitoring configuration
5. **Automated Tests**: Include in CI/CD pipelines for infrastructure validation

---

### `verify-health` Command

Verify that a previously sent test event has been ingested into the health table.

#### Syntax

```bash
sentinel-aggregator verify-health --workspace-config PATH --test-id ID [OPTIONS]
```

#### Required Arguments

##### `--workspace-config PATH` / `-w PATH`

Path to the workspace configuration YAML file.

**Required**: Yes

##### `--test-id ID`

Test identifier to search for in the health table.

**Required**: Yes

**Example**:
```bash
sentinel-aggregator verify-health -w workspaces.yaml --test-id "test-001"
```

#### Optional Arguments

##### `--max-wait SECONDS`

Maximum seconds to wait for the event to appear.

**Type**: Integer

**Default**: `300` (5 minutes)

**Example**:
```bash
sentinel-aggregator verify-health -w workspaces.yaml \
    --test-id test-001 \
    --max-wait 600
```

##### `--health-workspace-id ID`

Workspace ID where health table is located.

**Format**: GUID

##### `--health-dcr-endpoint URL`

DCR endpoint for health logging (if different from main DCR).

##### `--health-dcr-immutable-id ID`

DCR immutable ID for health logging (if different from main DCR).

#### Exit Codes

- `0`: Test event found in health table
- `1`: Test event not found or verification failed

#### Output

**Success**:
```bash
$ sentinel-aggregator verify-health -w workspaces.yaml --test-id test-001
🔍 Verifying test event ingestion...
⏳ Waiting for event to appear in health table (max 300 seconds)...
✅ Test event found in health table
   Event timestamp: 2025-11-10T14:35:00Z
   Time since send: 67 seconds
```

**Not found**:
```bash
$ sentinel-aggregator verify-health -w workspaces.yaml --test-id test-001 --max-wait 60
🔍 Verifying test event ingestion...
⏳ Waiting for event to appear in health table (max 60 seconds)...
❌ Test event NOT found after 60 seconds
```

#### Examples

```bash
# Verify specific test event
sentinel-aggregator verify-health -w workspaces.yaml --test-id "test-001"

# Verify with extended wait
sentinel-aggregator verify-health -w workspaces.yaml \
    --test-id "test-001" \
    --max-wait 600

# Verify in specific workspace
sentinel-aggregator verify-health -w workspaces.yaml \
    --test-id "test-001" \
    --health-workspace-id aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
```

#### Use Cases

1. **Delayed Verification**: Check test event after waiting for ingestion delay
2. **Separate Verification**: Verify test sent in different session
3. **Troubleshooting**: Confirm event ingestion as part of debugging
4. **Automated Monitoring**: Schedule verification checks for health events

---

### `query-status` Command

Check the execution status of queries based on health logging data.

#### Syntax

```bash
sentinel-aggregator query-status --workspace-config PATH [OPTIONS]
```

#### Required Arguments

##### `--workspace-config PATH` / `-w PATH`

Path to the workspace configuration YAML file.

**Required**: Yes

**Example**:
```bash
sentinel-aggregator query-status --workspace-config workspaces.yaml
```

#### Optional Arguments

##### `--query-name NAME`

Filter status to specific query name.

**Example**:
```bash
sentinel-aggregator query-status -w workspaces.yaml \
    --query-name query_incident_summary
```

##### `--days-back N`

Number of days of history to check.

**Type**: Integer

**Default**: `7`

**Example**:
```bash
# Last 30 days
sentinel-aggregator query-status -w workspaces.yaml --days-back 30

# Last 24 hours
sentinel-aggregator query-status -w workspaces.yaml --days-back 1
```

##### `--health-workspace-id ID`

Workspace ID where health table is located.

**Format**: GUID

##### `--health-dcr-endpoint URL`

DCR endpoint for health logging (if different from main DCR).

##### `--health-dcr-immutable-id ID`

DCR immutable ID for health logging (if different from main DCR).

#### Exit Codes

- `0`: Query status retrieved successfully
- `1`: Failed to retrieve status

#### Output

```bash
$ sentinel-aggregator query-status -w workspaces.yaml --days-back 7
📊 Query Execution Status (Last 7 days)

Query: query_incident_summary
  Total Executions: 168
  ✅ Successful: 165 (98.2%)
  ❌ Failed: 3 (1.8%)
  ⏱️  Avg Duration: 12.3s
  📊 Avg Records: 450

Query: query_alert_triage
  Total Executions: 168
  ✅ Successful: 168 (100.0%)
  ❌ Failed: 0 (0.0%)
  ⏱️  Avg Duration: 8.7s
  📊 Avg Records: 120

Recent Failures:
  • query_incident_summary @ 2025-11-09T14:23:00Z
    Error: Timeout after 300 seconds
  • query_incident_summary @ 2025-11-08T02:15:00Z
    Error: Workspace throttled (429)
```

#### Examples

```bash
# Check all query status (last 7 days)
sentinel-aggregator query-status -w workspaces.yaml

# Check specific query
sentinel-aggregator query-status -w workspaces.yaml \
    --query-name query_incident_summary

# Check last 30 days
sentinel-aggregator query-status -w workspaces.yaml --days-back 30

# Check with detailed logging
sentinel-aggregator --log-level DEBUG query-status -w workspaces.yaml
```

#### Use Cases

1. **Monitoring**: Track query execution success rates
2. **Performance Analysis**: Identify slow queries
3. **Troubleshooting**: Find recent query failures
4. **Capacity Planning**: Analyze query load and duration
5. **SLA Tracking**: Monitor query reliability metrics

---

## Environment Variables

Environment variables provide defaults for command-line arguments. Command-line arguments override environment variables.

### Time Range

| Variable | Description | Format | Default |
|----------|-------------|--------|---------|
| `LOOKBACK_PERIOD` | Lookback period | ISO 8601 duration | None (required) |

### Batch Processing

| Variable | Description | Format | Default |
|----------|-------------|--------|---------|
| `BATCH_TIME_SIZE` | Batch size | ISO 8601 duration | `PT24H` |
| `MAX_CONCURRENT_QUERIES` | Max concurrent queries | Integer (1-20) | `5` |

### Data Collection Rule

| Variable | Description | Format | Example |
|----------|-------------|--------|---------|
| `DCR_ENDPOINT` | DCR endpoint URL | HTTPS URL | `https://my-dce.azure.com` |
| `DCR_IMMUTABLE_ID` | DCR immutable ID | dcr-* string | `dcr-abc123...` |

### Authentication

| Variable | Description | Format | Default |
|----------|-------------|--------|---------|
| `AZURE_CLIENT_ID` | Service Principal ID | GUID | None |
| `AZURE_CLIENT_SECRET` | Service Principal secret | String | None |
| `AZURE_TENANT_ID` | Azure Tenant ID | GUID | None |

### Logging

| Variable | Description | Options | Default |
|----------|-------------|---------|---------|
| `LOG_LEVEL` | Logging level | DEBUG, INFO, WARNING, ERROR, CRITICAL | `INFO` |

### Complete .env Example

```bash
# Time range
LOOKBACK_PERIOD=P1D

# Batch processing
BATCH_TIME_SIZE=PT24H
MAX_CONCURRENT_QUERIES=5

# Data Collection Rule
DCR_ENDPOINT=https://my-dce-abc123.eastus2.ingest.monitor.azure.com
DCR_IMMUTABLE_ID=dcr-abcdef1234567890abcdef1234567890

# Authentication (Service Principal)
AZURE_CLIENT_ID=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
AZURE_CLIENT_SECRET=your-secret-here
AZURE_TENANT_ID=ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj

# Logging
LOG_LEVEL=INFO
```

---

## Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `0` | Success | Command completed successfully |
| `1` | General error | Configuration error, authentication error, or execution failure |
| `2` | Invalid arguments | Missing required arguments or invalid argument values |

### Checking Exit Codes

**Linux/macOS**:
```bash
sentinel-aggregator run -w workspaces.yaml
echo $?  # Print exit code
```

**PowerShell**:
```powershell
sentinel-aggregator run -w workspaces.yaml
echo $LASTEXITCODE  # Print exit code
```

**Windows CMD**:
```cmd
sentinel-aggregator run -w workspaces.yaml
echo %ERRORLEVEL%
```

---

## Examples

### Basic Usage

```bash
# Simplest command (using environment variables)
sentinel-aggregator run --workspace-config workspaces.yaml

# With explicit time range
sentinel-aggregator run -w workspaces.yaml --lookback-period P1D

# Dry-run to test
sentinel-aggregator run -w workspaces.yaml --lookback-period P1D --dry-run
```

### Using Environment Files

```bash
# Load from .env file
sentinel-aggregator --env-file .env run -w workspaces.yaml

# Production environment
sentinel-aggregator --env-file .env.production run -w workspaces-prod.yaml

# Development environment
sentinel-aggregator --env-file .env.dev run -w workspaces-dev.yaml --dry-run
```

### Time Range Examples

```bash
# Last 24 hours
sentinel-aggregator run -w workspaces.yaml --lookback-period P1D

# Last 7 days
sentinel-aggregator run -w workspaces.yaml --lookback-period P7D

# Last 12 hours
sentinel-aggregator run -w workspaces.yaml --lookback-period PT12H

# Specific date range
sentinel-aggregator run -w workspaces.yaml \
    --start-time 2025-11-01T00:00:00Z \
    --end-time 2025-11-07T23:59:59Z

# Last month (using date command on Linux/macOS)
START=$(date -u -d "1 month ago" +%Y-%m-%dT00:00:00Z)
END=$(date -u +%Y-%m-%dT00:00:00Z)
sentinel-aggregator run -w workspaces.yaml --start-time $START --end-time $END
```

### Performance Tuning

```bash
# High-throughput configuration
sentinel-aggregator run -w workspaces.yaml \
    --lookback-period P30D \
    --batch-time-size PT12H \
    --max-concurrent-queries 10

# Memory-constrained configuration
sentinel-aggregator run -w workspaces.yaml \
    --lookback-period P7D \
    --batch-time-size PT6H \
    --max-concurrent-queries 2

# Balanced configuration
sentinel-aggregator run -w workspaces.yaml \
    --lookback-period P7D \
    --batch-time-size PT24H \
    --max-concurrent-queries 5
```

### Debug and Troubleshooting

```bash
# Enable debug logging
sentinel-aggregator --log-level DEBUG run -w workspaces.yaml --dry-run

# JSON logging for parsing
sentinel-aggregator --log-format json run -w workspaces.yaml > logs.json

# Validate configuration before running
sentinel-aggregator validate -w workspaces.yaml && \
    sentinel-aggregator run -w workspaces.yaml

# Check health logging
sentinel-aggregator health -w workspaces.yaml
```

### Production Patterns

```bash
# Full production command
sentinel-aggregator \
    --env-file .env.production \
    --log-level INFO \
    run \
    --workspace-config workspaces-prod.yaml \
    --lookback-period P1D

# With error handling (bash)
if sentinel-aggregator run -w workspaces.yaml; then
    echo "✅ Success"
else
    echo "❌ Failed with exit code $?"
    exit 1
fi

# Retry on failure (bash)
MAX_RETRIES=3
for i in $(seq 1 $MAX_RETRIES); do
    if sentinel-aggregator run -w workspaces.yaml; then
        exit 0
    fi
    sleep 60
done
exit 1
```

### Automation Examples

```bash
# Cron job (daily at 2 AM)
0 2 * * * cd /opt/sentinel && sentinel-aggregator --env-file .env run -w workspaces.yaml >> /var/log/sentinel.log 2>&1

# Systemd timer service
[Unit]
Description=Sentinel Log Aggregator

[Service]
Type=oneshot
WorkingDirectory=/opt/sentinel
EnvironmentFile=/opt/sentinel/.env
ExecStart=/usr/local/bin/sentinel-aggregator run -w workspaces.yaml

[Install]
WantedBy=multi-user.target
```

---

## See Also

- **[Quick Start - CLI](quickstart-cli.md)** - Get started in 5 minutes
- **[CLI Advanced Usage](cli-advanced.md)** - Advanced CLI patterns
- **[Health Test Usage](health-test-usage.md)** - Detailed health testing guide
- **[Workspace Configuration](workspace-configuration.md)** - Configure workspaces
- **[Authentication Guide](authentication.md)** - Set up authentication
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

---

**Need help?** Check [Troubleshooting](troubleshooting.md) or ask in [GitHub Discussions](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/discussions).
