# Health Test Command Usage Guide

## Overview

The `test-health` command provides a way to manually test your health logging pipeline end-to-end. It can send a test event to the health table and optionally verify that it was successfully ingested.

## Prerequisites

- Health logging must be enabled (`--enable-health-logging`)
- Health logging must be configured to send to Sentinel (`--health-to-sentinel`)
- Valid DCR endpoint and immutable ID for health logging
- Workspace configuration file with at least one workspace

## Basic Usage

### Send a Test Event

Send a test health event with an auto-generated test ID:

```bash
sentinel-aggregator test-health \
  --workspace-config workspaces.yaml \
  --enable-health-logging \
  --health-to-sentinel \
  --dcr-endpoint "https://your-dcr-endpoint.ingest.monitor.azure.com" \
  --dcr-immutable-id "dcr-your-immutable-id"
```

### Send and Verify

Send a test event and wait up to 5 minutes to verify it was ingested:

```bash
sentinel-aggregator test-health \
  --workspace-config workspaces.yaml \
  --enable-health-logging \
  --health-to-sentinel \
  --dcr-endpoint "https://your-dcr-endpoint.ingest.monitor.azure.com" \
  --dcr-immutable-id "dcr-your-immutable-id" \
  --verify \
  --max-wait 300
```

### Custom Test ID

Use a custom test identifier for tracking:

```bash
sentinel-aggregator test-health \
  --workspace-config workspaces.yaml \
  --enable-health-logging \
  --health-to-sentinel \
  --dcr-endpoint "https://your-dcr-endpoint.ingest.monitor.azure.com" \
  --dcr-immutable-id "dcr-your-immutable-id" \
  --test-id "my-custom-test-2025-01-20" \
  --verify
```

## Command-Line Arguments

### Required Arguments

- `--workspace-config PATH`: Path to workspace configuration YAML file

### Health Logging Configuration (Required)

These must be provided either via command line or environment variables:

- `--dcr-endpoint URL`: Azure Monitor DCR logs ingestion endpoint
- `--dcr-immutable-id ID`: Azure Monitor DCR immutable ID
- `--enable-health-logging`: Enable health logging
- `--health-to-sentinel`: Send health logs to Sentinel table

### Optional Arguments

- `--test-id ID`: Custom test identifier (auto-generated if not provided)
- `--verify`: Verify that the test event was ingested after sending
- `--max-wait SECONDS`: Maximum seconds to wait for verification (default: 300)
- `--health-workspace-id ID`: Workspace ID where health table is located (uses first workspace if not specified)
- `--health-dcr-endpoint URL`: Separate DCR endpoint for health logging (if different from main DCR)
- `--health-dcr-immutable-id ID`: Separate DCR immutable ID for health logging (if different from main DCR)

## Output Examples

### Successful Test Event Send

```
🧪 Testing health logging...
📤 Sending test health event...
✅ Test event sent successfully (Test ID: health-test-a1b2c3d4e5f6)
💡 Use --verify flag to check if the test event was ingested successfully
```

### Successful Verification

```
🧪 Testing health logging...
📤 Sending test health event...
✅ Test event sent successfully (Test ID: health-test-a1b2c3d4e5f6)
🔍 Using first workspace for verification: Production-Workspace
🔍 Verifying test event ingestion (max wait: 300 seconds)...
🔍 Searching for test event: health-test-a1b2c3d4e5f6
⏳ Waiting 5 seconds before retry...
⏳ Waiting 10 seconds before retry...
✅ Test event verified: health-test-a1b2c3d4e5f6 (ingestion delay: 15s)
📊 Verification Results:
==================================================
  • Test ID: health-test-a1b2c3d4e5f6
  • Found: ✅
  • Message: Test event found after 15 seconds (Test ID: health-test-a1b2c3d4e5f6)
  • Ingestion Delay: 15 seconds
==================================================
```

### Test Event Not Found (Expected for Immediate Checks)

```
🧪 Testing health logging...
📤 Sending test health event...
✅ Test event sent successfully (Test ID: health-test-a1b2c3d4e5f6)
🔍 Verifying test event ingestion (max wait: 60 seconds)...
⚠️ Test event not found yet: health-test-a1b2c3d4e5f6
📊 Verification Results:
==================================================
  • Test ID: health-test-a1b2c3d4e5f6
  • Found: ❌
  • Message: Test event not found after 60 seconds. It may take up to 10-15 minutes for data to appear in Log Analytics. Test ID: health-test-a1b2c3d4e5f6
==================================================
```

## Verification Retry Logic

The verification process uses an exponential backoff strategy with the following intervals:
- First attempt: Immediate
- 2nd attempt: After 5 seconds
- 3rd attempt: After 10 more seconds (15s total)
- 4th attempt: After 15 more seconds (30s total)
- 5th attempt: After 30 more seconds (60s total)
- 6th attempt: After 60 more seconds (120s total)

The verification stops when:
1. The test event is found in the health table
2. The maximum wait time (`--max-wait`) is exceeded
3. All retry intervals have been exhausted

## Use Cases

### 1. Manual Pipeline Testing

Verify your health logging pipeline is working correctly:

```bash
sentinel-aggregator test-health \
  --workspace-config workspaces.yaml \
  --enable-health-logging \
  --health-to-sentinel \
  --dcr-endpoint "$DCR_ENDPOINT" \
  --dcr-immutable-id "$DCR_IMMUTABLE_ID" \
  --verify
```

### 2. Automated Health Checks

Include in CI/CD pipelines or scheduled health checks:

```bash
# Send test event and exit immediately
sentinel-aggregator test-health \
  --workspace-config workspaces.yaml \
  --enable-health-logging \
  --health-to-sentinel \
  --dcr-endpoint "$DCR_ENDPOINT" \
  --dcr-immutable-id "$DCR_IMMUTABLE_ID" \
  --test-id "ci-health-check-$(date +%s)"

# Later, verify the event was ingested
sentinel-aggregator test-health \
  --workspace-config workspaces.yaml \
  --enable-health-logging \
  --health-to-sentinel \
  --dcr-endpoint "$DCR_ENDPOINT" \
  --dcr-immutable-id "$DCR_IMMUTABLE_ID" \
  --test-id "ci-health-check-1705774800" \
  --verify \
  --max-wait 600
```

### 3. Debugging Ingestion Issues

When troubleshooting health logging issues, send a test event and check the health table:

```bash
# Send test event
sentinel-aggregator test-health \
  --workspace-config workspaces.yaml \
  --enable-health-logging \
  --health-to-sentinel \
  --dcr-endpoint "$DCR_ENDPOINT" \
  --dcr-immutable-id "$DCR_IMMUTABLE_ID" \
  --test-id "debug-test-$(date +%s)"

# Query the health table directly using Azure portal or Log Analytics
# Look for records where:
# - OperationName == "HealthTest"
# - JobId == "debug-test-<timestamp>"
```

## Programmatic Usage

You can also use the health test functionality programmatically:

```python
from sentinel_log_aggregator.health_logger import SentinelAggregatorHealthLogger
from sentinel_log_aggregator.sentinel_client import SentinelAggregatorClient
from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions
from azure.identity.aio import DefaultAzureCredential

# Create client
credential = DefaultAzureCredential()
config = SentinelAggregatorClientOptions(
    dcr_logs_ingestion_endpoint="https://your-dcr-endpoint.ingest.monitor.azure.com",
    dcr_immutable_id="dcr-your-immutable-id"
)
client = SentinelAggregatorClient(
    dcr_logs_ingestion_endpoint=config.dcr_logs_ingestion_endpoint,
    credential=credential,
    options=config
)

# Create health logger
health_logger = SentinelAggregatorHealthLogger(
    sentinel_client=client,
    enabled=True,
    health_to_sentinel=True
)

# Send test event
send_result = await health_logger.send_test_event(test_id="my-test")
print(f"Test ID: {send_result['test_id']}")
print(f"Success: {send_result['success']}")
print(f"Message: {send_result['message']}")

# Verify test event (optional)
verify_result = await health_logger.verify_test_event(
    test_id=send_result['test_id'],
    workspace_id="your-workspace-id",
    max_wait_seconds=300
)
print(f"Found: {verify_result['found']}")
print(f"Message: {verify_result['message']}")
if verify_result.get('ingestion_delay_seconds'):
    print(f"Ingestion delay: {verify_result['ingestion_delay_seconds']} seconds")
```

## Troubleshooting

### Health Logging Not Enabled Error

```
❌ Health logging is not enabled or configured
💡 Enable health logging with --enable-health-logging
```

**Solution**: Add `--enable-health-logging --health-to-sentinel` flags.

### Health Logging in Console-Only Mode

```
⚠️ Health logging is in console-only mode (not sent to Sentinel). Ensure you check the workspace logs.
```

**Solution**: Add the `--health-to-sentinel` flag to send health logs to Sentinel table.

### Test Event Not Found After Max Wait

```
❌ Test event not found after 300 seconds. It may take up to 10-15 minutes for data to appear in Log Analytics.
```

**Possible causes**:
1. **Normal ingestion delay**: Log Analytics can take 10-15 minutes to ingest data
2. **DCR misconfiguration**: Check DCR endpoint and immutable ID
3. **Table not created**: Ensure health table exists in workspace
4. **Permission issues**: Verify managed identity has proper permissions

**Solution**: Wait longer (use `--max-wait 900` for 15 minutes) or verify DCR configuration.

### Upload Failed Error

```
❌ Failed to send test event: <error message>
```

**Possible causes**:
1. Invalid DCR endpoint or immutable ID
2. Network connectivity issues
3. Authentication/permission issues
4. DCR not properly configured

**Solution**: 
- Verify DCR configuration with `verify-health` command
- Check Azure managed identity permissions
- Review DCR transformation rules

## Related Commands

- `verify-health`: Verify health logging infrastructure setup
- `health`: Perform general service health check
- `query-status`: Query last successful run timestamps from health table

## Notes

- **Ingestion Delay**: Azure Log Analytics typically has a 5-15 minute ingestion delay
- **Test Event Format**: Test events use `OperationName="HealthTest"` and `OperationStatus="TestEvent"`
- **Unique Test IDs**: Auto-generated test IDs use format `health-test-<12-char-hex>`
- **Verification Timeout**: Default max wait is 300 seconds (5 minutes), adjustable via `--max-wait`
