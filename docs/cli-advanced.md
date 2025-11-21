# CLI Advanced Usage

Advanced patterns and techniques for the Sentinel Log Aggregator CLI.

## Table of Contents

- [Multi-Workspace Management](#multi-workspace-management)
- [Time Range Strategies](#time-range-strategies)
- [Health Logging](#health-logging)
- [Automation Patterns](#automation-patterns)
- [Performance Optimization](#performance-optimization)
- [Error Handling](#error-handling)
- [Monitoring and Observability](#monitoring-and-observability)

## Multi-Workspace Management

### Basic Multi-Workspace Configuration

**workspaces.yaml**:
```yaml
workspaces:
  # Production SOC workspace
  - resource_id: /subscriptions/abc-123/resourcegroups/rg-prod-soc/providers/microsoft.operationalinsights/workspaces/ws-prod-soc
    customer_id: aaaaaaaa-1111-2222-3333-444444444444
    alias: prod-soc
    aggregation_workspace: true
    parameters:
      row_level_security_tag: "PROD_SOC"
    queries_list:
      - query_incident_summary
      - query_workspace_usage
      - query_alert_summary
  
  # Customer A workspace
  - resource_id: /subscriptions/abc-123/resourcegroups/rg-customer-a/providers/microsoft.operationalinsights/workspaces/ws-customer-a
    customer_id: bbbbbbbb-1111-2222-3333-444444444444
    alias: customer-a
    aggregation_workspace: false
    parameters:
      row_level_security_tag: "CUSTOMER_A"
      customer_name: "Acme Corporation"
    queries_list:
      - query_incident_summary
      - query_alert_summary
  
  # Customer B workspace
  - resource_id: /subscriptions/abc-123/resourcegroups/rg-customer-b/providers/microsoft.operationalinsights/workspaces/ws-customer-b
    customer_id: cccccccc-1111-2222-3333-444444444444
    alias: customer-b
    aggregation_workspace: false
    parameters:
      row_level_security_tag: "CUSTOMER_B"
      customer_name: "Beta Industries"
    queries_list:
      - query_incident_summary
```

### Running Against Specific Workspaces

The CLI processes all workspaces defined in the configuration file. To process specific workspaces, create separate configuration files:

**Production only**:
```bash
sentinel-aggregator run --workspace-config workspaces-prod.yaml
```

**Customers only**:
```bash
sentinel-aggregator run --workspace-config workspaces-customers.yaml
```

**Single customer** (create `workspace-customer-a.yaml`):
```bash
sentinel-aggregator run --workspace-config workspace-customer-a.yaml
```

### Organizing Multiple Configuration Files

```
config/
├── workspaces-all.yaml          # All workspaces
├── workspaces-prod.yaml         # Production workspaces only
├── workspaces-customers.yaml    # All customer workspaces
├── workspaces-customer-a.yaml   # Single customer
└── workspaces-test.yaml         # Test/dev workspaces
```

## Time Range Strategies

### ISO 8601 Duration Patterns

```bash
# Last 1 day
sentinel-aggregator run --workspace-config workspaces.yaml --lookback-period P1D

# Last 7 days
sentinel-aggregator run --workspace-config workspaces.yaml --lookback-period P7D

# Last 30 days
sentinel-aggregator run --workspace-config workspaces.yaml --lookback-period P30D

# Last 3 months (90 days)
sentinel-aggregator run --workspace-config workspaces.yaml --lookback-period P90D

# Last 12 hours
sentinel-aggregator run --workspace-config workspaces.yaml --lookback-period PT12H
```

### Specific Date Ranges

```bash
# Specific date range
sentinel-aggregator run \
    --workspace-config workspaces.yaml \
    --start-time 2025-11-01T00:00:00Z \
    --end-time 2025-11-07T23:59:59Z

# Month-end reporting (October 2025)
sentinel-aggregator run \
    --workspace-config workspaces.yaml \
    --start-time 2025-10-01T00:00:00Z \
    --end-time 2025-10-31T23:59:59Z
```

### Batch Processing Configuration

Control how large time ranges are split into batches:

**.env**:
```bash
# Default: 24-hour batches
BATCH_TIME_SIZE=PT24H

# Smaller batches (12 hours) for large datasets
BATCH_TIME_SIZE=PT12H

# Larger batches (7 days) for smaller datasets
BATCH_TIME_SIZE=P7D
```

**Command line**:
```bash
sentinel-aggregator run \
    --workspace-config workspaces.yaml \
    --lookback-period P30D \
    --batch-time-size PT12H  # Split 30 days into 12-hour batches
```

### Historical Data Backfill

Process historical data in manageable chunks:

```bash
#!/bin/bash
# Backfill script: Process 6 months in 1-week chunks

for i in {0..25}; do
    START_DAYS=$((i * 7))
    END_DAYS=$((START_DAYS + 7))
    
    START_DATE=$(date -u -d "-$START_DAYS days" +%Y-%m-%dT00:00:00Z)
    END_DATE=$(date -u -d "-$END_DAYS days" +%Y-%m-%dT23:59:59Z)
    
    echo "Processing: $START_DATE to $END_DATE"
    
    sentinel-aggregator run \
        --workspace-config workspaces.yaml \
        --start-time $START_DATE \
        --end-time $END_DATE \
        --batch-time-size P1D
    
    # Wait between batches to avoid throttling
    sleep 60
done
```

## Health Logging

### Check Health Logging Setup

```bash
sentinel-aggregator health --workspace-config workspaces.yaml
```

**Expected output**:
```
✅ All workspaces have health logging configured correctly
   • ws-prod-soc: Custom-Reports_Health_CL table exists
   • ws-customer-a: Custom-Reports_Health_CL table exists
   • ws-customer-b: Custom-Reports_Health_CL table exists
```

### Health Logging Queries

After running health checks, query the logs:

```kql
// Check recent health logs
Custom-Reports_Health_CL
| where TimeGenerated > ago(7d)
| project TimeGenerated, JobCorrelationId=job_correlation_id_s, 
          Status=execution_status_s, Query=query_name_s,
          RecordsDownloaded=records_downloaded_d
| order by TimeGenerated desc

// Identify failing queries
Custom-Reports_Health_CL
| where TimeGenerated > ago(7d)
| where execution_status_s == "Failed"
| summarize FailureCount=count() by query_name_s, error_message_s
| order by FailureCount desc

// Performance monitoring
Custom-Reports_Health_CL
| where TimeGenerated > ago(7d)
| where execution_status_s == "Completed"
| summarize 
    AvgDuration=avg(duration_seconds_d),
    MaxDuration=max(duration_seconds_d),
    TotalRecords=sum(records_downloaded_d)
    by query_name_s
| order by AvgDuration desc
```

### Enable Health Logging in Production

Ensure health logging is enabled for all aggregation workspaces:

**workspaces.yaml**:
```yaml
workspaces:
  - resource_id: /subscriptions/.../workspaces/ws-aggregation
    customer_id: YOUR-WORKSPACE-ID
    aggregation_workspace: true  # Must be true for health logging
    parameters:
      row_level_security_tag: "AGGREGATION"
    queries_list:
      - query_health_log  # Health logging query
      - query_incident_summary
```

## Automation Patterns

### Cron Job (Linux/macOS)

```bash
# Edit crontab
crontab -e

# Daily at 2 AM
0 2 * * * cd /opt/sentinel-aggregator && /usr/local/bin/sentinel-aggregator --env-file .env run --workspace-config workspaces.yaml >> /var/log/sentinel-aggregator.log 2>&1

# Every 6 hours
0 */6 * * * cd /opt/sentinel-aggregator && /usr/local/bin/sentinel-aggregator --env-file .env run --workspace-config workspaces.yaml --lookback-period PT6H >> /var/log/sentinel-aggregator.log 2>&1

# Weekly full backfill (Sundays at 3 AM)
0 3 * * 0 cd /opt/sentinel-aggregator && /usr/local/bin/sentinel-aggregator --env-file .env run --workspace-config workspaces.yaml --lookback-period P7D >> /var/log/sentinel-aggregator-weekly.log 2>&1
```

### Windows Task Scheduler

**PowerShell script** (`run-sentinel-aggregator.ps1`):
```powershell
# Set error action preference
$ErrorActionPreference = "Stop"

# Set working directory
Set-Location "C:\sentinel-aggregator"

# Load environment variables
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}

# Run aggregator
& sentinel-aggregator run --workspace-config workspaces.yaml

# Check exit code
if ($LASTEXITCODE -ne 0) {
    Write-Error "Sentinel aggregator failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
```

**Create scheduled task**:
```powershell
# Create scheduled task
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\sentinel-aggregator\run-sentinel-aggregator.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest

Register-ScheduledTask -TaskName "Sentinel Log Aggregator" -Action $action -Trigger $trigger -Principal $principal
```

### Azure Function (Timer Trigger)

**function_app.py**:
```python
import azure.functions as func
import asyncio
import logging
import os
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    load_workspace_config
)

app = func.FunctionApp()

@app.timer_trigger(schedule="0 0 2 * * *", arg_name="mytimer", run_on_startup=False)
async def sentinel_aggregator_timer(mytimer: func.TimerRequest) -> None:
    """Run daily at 2 AM UTC"""
    
    if mytimer.past_due:
        logging.warning('Timer trigger is past due!')
    
    try:
        # Load configuration
        options = SentinelAggregatorClientOptions(
            lookback_period="P1D",
            batch_time_size="PT24H",
            dcr_endpoint=os.environ["DCR_ENDPOINT"],
            dcr_immutable_id=os.environ["DCR_IMMUTABLE_ID"]
        )
        
        # Load workspaces from blob storage or local file
        workspaces = load_workspace_config("workspaces.yaml")
        
        # Execute
        async with SentinelAggregatorClient(options) as client:
            summary = await client.execute_queries(workspaces)
            
        logging.info(f"✅ Job complete: {summary.total_records_uploaded} records uploaded")
        
    except Exception as e:
        logging.error(f"❌ Job failed: {e}", exc_info=True)
        raise
```

**host.json**:
```json
{
  "version": "2.0",
  "logging": {
    "logLevel": {
      "default": "Information",
      "sentinel_log_aggregator": "Information"
    }
  },
  "functionTimeout": "00:30:00"
}
```

### GitHub Actions

**.github/workflows/sentinel-aggregator.yml**:
```yaml
name: Sentinel Log Aggregator

on:
  schedule:
    # Daily at 2 AM UTC
    - cron: '0 2 * * *'
  
  # Allow manual trigger
  workflow_dispatch:
    inputs:
      lookback_period:
        description: 'Lookback period (e.g., P1D, P7D)'
        required: false
        default: 'P1D'
      dry_run:
        description: 'Dry run mode'
        type: boolean
        required: false
        default: false

jobs:
  aggregate:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install sentinel-log-aggregator
      
      - name: Run aggregation
        env:
          AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
          AZURE_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
          AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
          DCR_ENDPOINT: ${{ secrets.DCR_ENDPOINT }}
          DCR_IMMUTABLE_ID: ${{ secrets.DCR_IMMUTABLE_ID }}
        run: |
          DRY_RUN_FLAG=""
          if [ "${{ github.event.inputs.dry_run }}" == "true" ]; then
            DRY_RUN_FLAG="--dry-run"
          fi
          
          sentinel-aggregator run \
            --workspace-config workspaces.yaml \
            --lookback-period ${{ github.event.inputs.lookback_period || 'P1D' }} \
            $DRY_RUN_FLAG
      
      - name: Upload logs
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: aggregation-logs
          path: |
            *.log
```

## Performance Optimization

### Concurrent Query Execution

Control parallelism:

**.env**:
```bash
# Default: 5 concurrent queries
MAX_CONCURRENT_QUERIES=5

# High-performance setup (more memory required)
MAX_CONCURRENT_QUERIES=10

# Conservative setup (limited resources)
MAX_CONCURRENT_QUERIES=2
```

### Batch Size Tuning

Balance between API calls and memory usage:

```bash
# Large datasets: smaller batches to avoid memory issues
sentinel-aggregator run \
    --workspace-config workspaces.yaml \
    --lookback-period P30D \
    --batch-time-size PT6H \
    --max-concurrent-queries 3

# Small datasets: larger batches for faster processing
sentinel-aggregator run \
    --workspace-config workspaces.yaml \
    --lookback-period P7D \
    --batch-time-size P7D \
    --max-concurrent-queries 10
```

### Memory Management

Monitor and optimize memory usage:

**Linux**:
```bash
# Monitor memory during execution
watch -n 1 'ps aux | grep sentinel-aggregator | grep -v grep'

# Limit memory (cgroups)
systemd-run --scope -p MemoryMax=2G sentinel-aggregator run --workspace-config workspaces.yaml
```

**PowerShell**:
```powershell
# Monitor memory
while ($true) {
    Get-Process sentinel-aggregator -ErrorAction SilentlyContinue | 
        Select-Object Name, @{Name="Memory(MB)";Expression={$_.WorkingSet64/1MB}}
    Start-Sleep -Seconds 1
}
```

## Error Handling

### Retry Failed Queries

```bash
#!/bin/bash
# Retry script with exponential backoff

MAX_RETRIES=3
RETRY_DELAY=60

for i in $(seq 1 $MAX_RETRIES); do
    echo "Attempt $i of $MAX_RETRIES"
    
    if sentinel-aggregator run --workspace-config workspaces.yaml; then
        echo "✅ Success"
        exit 0
    else
        echo "❌ Failed, waiting ${RETRY_DELAY}s before retry..."
        sleep $RETRY_DELAY
        RETRY_DELAY=$((RETRY_DELAY * 2))  # Exponential backoff
    fi
done

echo "❌ All retries exhausted"
exit 1
```

### Graceful Failure Handling

```bash
#!/bin/bash
# Production script with error handling and notifications

LOG_FILE="/var/log/sentinel-aggregator.log"

# Run aggregation
if sentinel-aggregator run --workspace-config workspaces.yaml >> "$LOG_FILE" 2>&1; then
    echo "$(date): ✅ Aggregation successful" >> "$LOG_FILE"
else
    EXIT_CODE=$?
    echo "$(date): ❌ Aggregation failed with exit code $EXIT_CODE" >> "$LOG_FILE"
    
    # Send alert (example: email)
    mail -s "Sentinel Aggregator Failed" admin@example.com < "$LOG_FILE"
    
    # Or: Post to Teams webhook
    curl -H "Content-Type: application/json" -d "{\"text\":\"Sentinel Aggregator failed\"}" "$TEAMS_WEBHOOK_URL"
    
    exit $EXIT_CODE
fi
```

## Monitoring and Observability

### Structured Logging

Enable detailed logging for troubleshooting:

```bash
# Debug level logging
sentinel-aggregator --log-level DEBUG run --workspace-config workspaces.yaml

# JSON-formatted logs for parsing
sentinel-aggregator --log-format json run --workspace-config workspaces.yaml > logs.json
```

### Correlation IDs

Every execution has a unique correlation ID for tracking:

```bash
# Run and capture correlation ID
OUTPUT=$(sentinel-aggregator run --workspace-config workspaces.yaml 2>&1)
CORRELATION_ID=$(echo "$OUTPUT" | grep "job_correlation_id" | awk '{print $NF}')

echo "Job ID: $CORRELATION_ID"

# Query health logs by correlation ID
az monitor log-analytics query \
    --workspace YOUR-WORKSPACE-ID \
    --analytics-query "Custom-Reports_Health_CL | where job_correlation_id_s == '$CORRELATION_ID'"
```

### Performance Metrics

Track execution metrics over time:

```kql
// Average execution time per query
Custom-Reports_Health_CL
| where TimeGenerated > ago(30d)
| where execution_status_s == "Completed"
| summarize 
    AvgDuration=avg(duration_seconds_d),
    P50=percentile(duration_seconds_d, 50),
    P95=percentile(duration_seconds_d, 95),
    P99=percentile(duration_seconds_d, 99)
    by query_name_s
| order by AvgDuration desc

// Daily record processing volume
Custom-Reports_Health_CL
| where TimeGenerated > ago(30d)
| summarize TotalRecords=sum(records_downloaded_d) by bin(TimeGenerated, 1d)
| render timechart

// Query success rate
Custom-Reports_Health_CL
| where TimeGenerated > ago(7d)
| summarize 
    Total=count(),
    Successful=countif(execution_status_s == "Completed"),
    Failed=countif(execution_status_s == "Failed")
    by query_name_s
| extend SuccessRate=round(100.0 * Successful / Total, 2)
| order by SuccessRate asc
```

## Advanced Configuration Patterns

### Environment-Specific Configurations

**Production** (`.env.production`):
```bash
LOOKBACK_PERIOD=P1D
BATCH_TIME_SIZE=PT24H
MAX_CONCURRENT_QUERIES=5
DCR_ENDPOINT=https://prod-dce.azure.com
DCR_IMMUTABLE_ID=dcr-prod-123
LOG_LEVEL=INFO
```

**Development** (`.env.development`):
```bash
LOOKBACK_PERIOD=PT1H
BATCH_TIME_SIZE=PT1H
MAX_CONCURRENT_QUERIES=2
DCR_ENDPOINT=https://dev-dce.azure.com
DCR_IMMUTABLE_ID=dcr-dev-456
LOG_LEVEL=DEBUG
```

**Usage**:
```bash
# Production
sentinel-aggregator --env-file .env.production run --workspace-config workspaces.yaml

# Development
sentinel-aggregator --env-file .env.development run --workspace-config workspaces-dev.yaml --dry-run
```

### Parameterized Executions

Pass parameters dynamically:

```bash
#!/bin/bash
# Dynamic parameter script

ENVIRONMENT=${1:-production}
LOOKBACK=${2:-P1D}

echo "Running in $ENVIRONMENT with lookback $LOOKBACK"

sentinel-aggregator \
    --env-file ".env.$ENVIRONMENT" \
    run \
    --workspace-config "workspaces-$ENVIRONMENT.yaml" \
    --lookback-period "$LOOKBACK"
```

**Usage**:
```bash
# Production, last 1 day
./run.sh production P1D

# Development, last 1 hour
./run.sh development PT1H

# Test, last 7 days
./run.sh test P7D
```

## Next Steps

- 📖 **[CLI Reference](cli-reference.md)** - Complete CLI command documentation
- 📖 **[SDK Advanced Usage](sdk-advanced.md)** - Advanced SDK patterns
- 🔧 **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

---

**Need help?** Check [Troubleshooting](troubleshooting.md) or ask in [GitHub Discussions](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/discussions).
