---
title: CLI usage
description: Learn how to use the Microsoft Sentinel Log Aggregator command-line interface for automation and manual operations.
author: Alistair Ross
ms.author: community
ms.service: sentinel
ms.topic: reference
ms.date: 2025-11-01
---

# CLI usage

The Microsoft Sentinel Log Aggregator includes a comprehensive command-line interface (CLI) that follows Azure CLI patterns and conventions. The CLI is ideal for automation, CI/CD pipelines, and manual operations.

## Installation

The CLI is included when you install the package:

```powershell
# Install from GitHub repository
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git

# Or install from GitHub release
pip install https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/releases/latest/download/sentinel_log_aggregator-1.0.0-py3-none-any.whl
```

## Global options

Global options apply to all commands:

```powershell
sentinel-aggregator [global-options] <command> [command-options]
```

### Global options reference

| Option | Description | Default |
|--------|-------------|---------|
| `--version` | Show version information | |
| `--help`, `-h` | Show help information | |
| `--log-level` | Set logging level | `INFO` |
| `--config-file` | Path to configuration file | `.env` |
| `--no-color` | Disable colored output | `false` |
| `--quiet`, `-q` | Suppress non-error output | `false` |
| `--verbose`, `-v` | Enable verbose output | `false` |

### Examples

```bash
# Show version
sentinel-aggregator --version

# Get help
sentinel-aggregator --help

# Enable debug logging
sentinel-aggregator --log-level DEBUG run --workspace-config workspaces.yaml

# Quiet mode (errors only)
sentinel-aggregator --quiet run --workspace-config workspaces.yaml
```

## Commands

### health

Check service health and connectivity.

```bash
sentinel-aggregator health [options]
```

#### Options

| Option | Description | Required |
|--------|-------------|----------|
| `--workspace-config` | Path to workspace configuration file | Yes |
| `--timeout` | Health check timeout in seconds | No (default: 30) |

#### Examples

```bash
# Basic health check
sentinel-aggregator health --workspace-config workspaces.yaml

# Health check with custom timeout
sentinel-aggregator health --workspace-config workspaces.yaml --timeout 60

# Health check with debug logging
sentinel-aggregator --log-level DEBUG health --workspace-config workspaces.yaml
```

#### Output

```json
{
  "status": "healthy",
  "service_version": "1.0.0",
  "connectivity_status": "connected",
  "workspaces_checked": 3,
  "workspaces_healthy": 3,
  "timestamp": "2025-11-01T10:30:00Z",
  "checks": [
    {
      "name": "authentication",
      "status": "pass",
      "duration_ms": 245
    },
    {
      "name": "dcr_connectivity",
      "status": "pass",
      "duration_ms": 156
    },
    {
      "name": "workspace_access",
      "status": "pass",
      "duration_ms": 892
    }
  ]
}
```

### run

Execute log aggregation queries and upload results.

```bash
sentinel-aggregator run [options]
```

#### Options

| Option | Description | Required | Default | Environment Variable |
|--------|-------------|----------|---------|---------------------|
| `--workspace-config` | Path to workspace configuration file | Yes | | N/A |
| **Time Range Options (mutually exclusive)** | | | | |
| `--lookback-period` | ISO 8601 duration to look back | No | P30D | `LOOKBACK_PERIOD` |
| `--start-time` | ISO 8601 start datetime | No | | `START_TIME` |
| `--end-time` | ISO 8601 end datetime | No | | `END_TIME` |
| `--use-last-successful` | Continue from last successful run | No | false | `USE_LAST_SUCCESSFUL` |
| **Batch Processing** | | | | |
| `--batch-time-size` | ISO 8601 duration for batch size | No | PT24H | `BATCH_TIME_SIZE` |
| **Execution Control** | | | | |
| `--queries` | Specific queries to run (comma-separated) | No | All | `QUERIES` |
| `--workspaces` | Specific workspaces to process (comma-separated) | No | All | `WORKSPACES` |
| `--dry-run` | Validate and show what would be executed | No | `false` | `DRY_RUN` |
| `--parallel` / `--no-parallel` | Enable parallel execution | No | `true` | `PARALLEL` |
| `--max-workers` | Maximum parallel workers | No | 5 | `MAX_CONCURRENT_QUERIES` |
| **Health Logging** | | | | |
| `--health-logging-enabled` | Enable health tracking | No | false | `HEALTH_TO_SENTINEL` |

#### Examples

```bash
# Basic run with default settings (30 days lookback)
sentinel-aggregator run --workspace-config workspaces.yaml

# Run with custom lookback period
sentinel-aggregator run --workspace-config workspaces.yaml --lookback-period "P7D" --batch-time-size "PT12H"

# Run with explicit time range (historical analysis)
sentinel-aggregator run --workspace-config workspaces.yaml \
  --start-time "2025-01-01T00:00:00Z" \
  --end-time "2025-01-31T23:59:59Z" \
  --batch-time-size "PT6H"

# Continue from last successful run (incremental processing)
sentinel-aggregator run --workspace-config workspaces.yaml \
  --use-last-successful \
  --health-logging-enabled

# Run specific queries only
sentinel-aggregator run --workspace-config workspaces.yaml --queries "query_incident_summary,query_user_summary"

# Run for specific workspaces
sentinel-aggregator run --workspace-config workspaces.yaml --workspaces "prod-workspace,dev-workspace"

# Dry run to validate configuration
sentinel-aggregator run --workspace-config workspaces.yaml --dry-run

# Run with custom parallelism
sentinel-aggregator run --workspace-config workspaces.yaml --max-workers 10

# Sequential execution (no parallelism)
sentinel-aggregator run --workspace-config workspaces.yaml --no-parallel

# Using environment variables with CLI overrides
export LOOKBACK_PERIOD="P30D"
export QUERIES="incident_summary,alert_summary"
sentinel-aggregator run --workspace-config workspaces.yaml --lookback-period "P7D"
# Result: Uses P7D (CLI override) and incident_summary,alert_summary (from env var)

# Using .env file with minimal CLI
echo "LOOKBACK_PERIOD=P7D" > .env
echo "BATCH_TIME_SIZE=PT12H" >> .env
sentinel-aggregator run --workspace-config workspaces.yaml
```

#### Output

```json
{
  "status": "completed",
  "execution_id": "exec-2025-11-01-103000",
  "start_time": "2025-11-01T10:30:00Z",
  "end_time": "2025-11-01T10:35:42Z",
  "duration_seconds": 342,
  "summary": {
    "total_queries": 12,
    "successful_queries": 11,
    "failed_queries": 1,
    "total_records_processed": 15847,
    "total_records_uploaded": 15847,
    "workspaces_processed": 3
  },
  "details": [
    {
      "workspace_id": "prod-east-workspace",
      "query": "query_incident_summary",
      "status": "completed",
      "records_processed": 1245,
      "duration_seconds": 23.4
    }
  ]
}
```

### validate

Validate configuration files and settings.

```bash
sentinel-aggregator validate [options]
```

#### Options

| Option | Description | Required |
|--------|-------------|----------|
| `--workspace-config` | Path to workspace configuration file | Yes |
| `--config-file` | Path to client configuration file | No |
| `--strict` | Enable strict validation mode | No |

#### Examples

```bash
# Validate workspace configuration
sentinel-aggregator validate --workspace-config workspaces.yaml

# Validate all configuration files
sentinel-aggregator validate --workspace-config workspaces.yaml --config-file config.yaml

# Strict validation (all warnings become errors)
sentinel-aggregator validate --workspace-config workspaces.yaml --strict
```

#### Output

```json
{
  "status": "valid",
  "validation_time": "2025-11-01T10:30:00Z",
  "client_config": {
    "status": "valid",
    "source": "environment"
  },
  "workspace_config": {
    "status": "valid",
    "workspaces_count": 3,
    "queries_count": 4,
    "warnings": [],
    "errors": []
  },
  "connectivity": {
    "dcr_endpoint": "reachable",
    "authentication": "valid"
  }
}
```

### query

Execute a single query for testing and development.

```bash
sentinel-aggregator query [options]
```

#### Options

| Option | Description | Required |
|--------|-------------|----------|
| `--workspace-id` | Workspace customer ID | Yes |
| `--query` | KQL query to execute | Yes |
| `--output` | Output format (json, table, csv) | No (default: json) |
| `--limit` | Maximum records to return | No (default: 1000) |
| `--timeout` | Query timeout in seconds | No (default: 300) |

#### Examples

```bash
# Execute simple query
sentinel-aggregator query \
  --workspace-id "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" \
  --query "SecurityEvent | take 10"

# Query with table output
sentinel-aggregator query \
  --workspace-id "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" \
  --query "SecurityEvent | summarize count() by Computer" \
  --output table

# Query with limits and timeout
sentinel-aggregator query \
  --workspace-id "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" \
  --query "SecurityEvent | where TimeGenerated > ago(1h)" \
  --limit 5000 \
  --timeout 600
```

### list

List available resources and configurations.

```bash
sentinel-aggregator list <resource-type> [options]
```

#### Subcommands

##### workspaces

```bash
sentinel-aggregator list workspaces --workspace-config workspaces.yaml
```

##### queries

```bash
sentinel-aggregator list queries [--workspace-config workspaces.yaml]
```

#### Examples

```bash
# List configured workspaces
sentinel-aggregator list workspaces --workspace-config workspaces.yaml

# List available queries
sentinel-aggregator list queries

# List queries for specific workspace configuration
sentinel-aggregator list queries --workspace-config workspaces.yaml
```

### monitor

Monitor ongoing operations and view logs.

```bash
sentinel-aggregator monitor [options]
```

#### Options

| Option | Description | Required |
|--------|-------------|----------|
| `--execution-id` | Monitor specific execution | No |
| `--follow`, `-f` | Follow log output | No |
| `--tail` | Number of recent log entries | No (default: 100) |

#### Examples

```bash
# Monitor recent activity
sentinel-aggregator monitor

# Follow live logs
sentinel-aggregator monitor --follow

# Monitor specific execution
sentinel-aggregator monitor --execution-id exec-2025-11-01-103000

# Show last 50 log entries
sentinel-aggregator monitor --tail 50
```

### query-status

Check the status of last successful query runs across workspaces. This command helps track execution history and determine starting points for incremental processing.

```bash
sentinel-aggregator query-status [options]
```

#### Options

| Option | Description | Required | Default |
|--------|-------------|----------|---------|
| `--workspace-config` | Path to workspace configuration file | Yes | |
| `--query-filter` | Specific queries to check (comma-separated) | No | All |
| `--workspace-filter` | Specific workspaces to check (comma-separated) | No | All |
| `--lookback-days` | Days to look back for execution history | No | 30 |
| `--show-details` | Show detailed execution information | No | false |
| `--show-execution-history` | Show execution history and timing | No | false |
| `--format` | Output format (table, json, csv) | No | table |

#### Examples

```bash
# Check status for all queries and workspaces
sentinel-aggregator query-status --workspace-config workspaces.yaml

# Check specific queries with details
sentinel-aggregator query-status --workspace-config workspaces.yaml \
  --query-filter "incident_summary,threat_hunting" \
  --show-details

# Show execution history for last 7 days
sentinel-aggregator query-status --workspace-config workspaces.yaml \
  --lookback-days 7 \
  --show-execution-history

# Get status in JSON format for automation
sentinel-aggregator query-status --workspace-config workspaces.yaml \
  --format json

# Check specific workspace status
sentinel-aggregator query-status --workspace-config workspaces.yaml \
  --workspace-filter "prod-workspace-1,prod-workspace-2" \
  --show-details
```

#### Output Examples

**Table format (default):**
```
┌─────────────────┬────────────────────┬─────────────────────┬─────────────────┬────────────┐
│ Workspace       │ Query Name         │ Last Successful     │ Records         │ Status     │
├─────────────────┼────────────────────┼─────────────────────┼─────────────────┼────────────┤
│ prod-ws-1       │ incident_summary   │ 2025-11-03 08:00Z  │ 1,234           │ Success    │
│ prod-ws-1       │ threat_hunting     │ 2025-11-03 08:00Z  │ 567             │ Success    │
│ prod-ws-2       │ incident_summary   │ 2025-11-03 07:45Z  │ 890             │ Success    │
│ prod-ws-2       │ threat_hunting     │ 2025-11-02 20:15Z  │ 123             │ Warning    │
└─────────────────┴────────────────────┴─────────────────────┴─────────────────┴────────────┘
```

**JSON format:**
```json
{
  "query_status": [
    {
      "workspace_id": "prod-ws-1",
      "workspace_alias": "Production Workspace 1",
      "query_name": "incident_summary",
      "last_successful_time": "2025-11-03T08:00:00Z",
      "record_count": 1234,
      "status": "success",
      "execution_duration": "PT5M30S"
    }
  ],
  "summary": {
    "total_combinations": 4,
    "successful": 3,
    "warnings": 1,
    "errors": 0
  }
}
```

## Configuration files

### CLI configuration

Create a CLI-specific configuration file:

```yaml
# cli-config.yaml
default_workspace_config: "workspaces.yaml"
default_log_level: "INFO"
output_format: "json"
enable_color: true
auto_confirm: false
max_retries: 3
```

Use with:

```bash
sentinel-aggregator --config-file cli-config.yaml run --workspace-config workspaces.yaml
```

### Environment variables for CLI

All CLI parameters can be configured using environment variables following this priority order:

1. **Command line arguments** (highest priority)
2. **Environment variables** 
3. **`.env` file variables**
4. **Default values** (lowest priority)

```bash
# Environment variables for common parameters
DCR_LOGS_INGESTION_ENDPOINT=https://your-dcr-endpoint.monitor.azure.com
DCR_IMMUTABLE_ID=dcr-your-rule-id
LOOKBACK_PERIOD=P7D
BATCH_TIME_SIZE=PT12H
QUERIES=incident_summary,alert_summary
WORKSPACES=prod-workspace-1,prod-workspace-2
DRY_RUN=false
PARALLEL=true
MAX_CONCURRENT_QUERIES=5
HEALTH_TO_SENTINEL=false
LOG_LEVEL=INFO

# Query execution settings
QUERY_TIMEOUT_SECONDS=300
MAX_RETRIES=3
RETRY_DELAY_SECONDS=5

# Time range alternatives (mutually exclusive)
START_TIME=2025-01-01T00:00:00Z
END_TIME=2025-01-31T23:59:59Z
USE_LAST_SUCCESSFUL=false
```

See the [Environment Variables Reference](environment-variables.md) for complete documentation.

## Configuration files

### Bash scripting

```bash
#!/bin/bash

# Automated aggregation script
set -e

CONFIG_FILE="workspaces.yaml"
LOG_LEVEL="INFO"

# Function to run aggregation with error handling
run_aggregation() {
    local lookback_period=${1:-"P30D"}
    local batch_time_size=${2:-"PT24H"}
    
    echo "Starting aggregation: lookback_period=$lookback_period, batch_time_size=$batch_time_size"
    
    if sentinel-aggregator validate --workspace-config "$CONFIG_FILE"; then
        echo "Configuration validated successfully"
        
        sentinel-aggregator --log-level "$LOG_LEVEL" run \
            --workspace-config "$CONFIG_FILE" \
            --lookback-period "$lookback_period" \
            --batch-time-size "$batch_time_size"
        
        echo "Aggregation completed successfully"
    else
        echo "Configuration validation failed"
        exit 1
    fi
}

# Health check before running
if sentinel-aggregator health --workspace-config "$CONFIG_FILE"; then
    echo "Health check passed"
    run_aggregation "P7D" "PT12H"
else
    echo "Health check failed"
    exit 1
fi
```

### PowerShell scripting

```powershell
# Automated aggregation script
param(
    [int]$DaysBack = 30,
    [int]$BatchHours = 24,
    [string]$ConfigFile = "workspaces.yaml"
)

# Function to run aggregation with error handling
function Start-Aggregation {
    param($LookbackPeriod, $BatchTimeSize, $ConfigFile)
    
    Write-Host "Starting aggregation: LookbackPeriod=$LookbackPeriod, BatchTimeSize=$BatchTimeSize"
    
    # Validate configuration
    $validateResult = sentinel-aggregator validate --workspace-config $ConfigFile
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Configuration validation failed"
        exit 1
    }
    
    Write-Host "Configuration validated successfully"
    
    # Run aggregation
    sentinel-aggregator run --workspace-config $ConfigFile --lookback-period $LookbackPeriod --batch-time-size $BatchTimeSize
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Aggregation completed successfully"
    } else {
        Write-Error "Aggregation failed"
        exit 1
    }
}

# Health check
$healthResult = sentinel-aggregator health --workspace-config $ConfigFile
if ($LASTEXITCODE -eq 0) {
    Write-Host "Health check passed"
    Start-Aggregation -LookbackPeriod "P7D" -BatchTimeSize "PT12H" -ConfigFile $ConfigFile
} else {
    Write-Error "Health check failed"
    exit 1
}
```

## Error handling

The CLI provides comprehensive error codes and messages:

### Exit codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | Authentication error |
| 4 | Network/connectivity error |
| 5 | Permission error |
| 6 | Query execution error |
| 7 | Data ingestion error |

### Error output

```json
{
  "error": {
    "code": "ConfigurationError",
    "message": "Invalid workspace configuration",
    "details": [
      "Workspace 1: customer_id is required",
      "Workspace 2: Invalid resource_id format"
    ],
    "timestamp": "2025-11-01T10:30:00Z",
    "correlation_id": "12345678-1234-1234-1234-123456789012"
  }
}
```

## Best practices

### Performance optimization

```bash
# Optimize for large datasets
sentinel-aggregator run \
  --workspace-config workspaces.yaml \
  --batch-hours 6 \
  --max-workers 15 \
  --days-back 3

# Optimize for resource-constrained environments
sentinel-aggregator run \
  --workspace-config workspaces.yaml \
  --batch-hours 48 \
  --max-workers 2 \
  --parallel false
```

### Monitoring and logging

```bash
# Enable comprehensive logging
sentinel-aggregator --log-level DEBUG --verbose run \
  --workspace-config workspaces.yaml 2>&1 | tee aggregation.log

# JSON output for programmatic processing
sentinel-aggregator run --workspace-config workspaces.yaml \
  --output json > results.json 2>&1
```

### Security considerations

```bash
# Use managed identity (no credentials in command)
sentinel-aggregator run --workspace-config workspaces.yaml

# Validate before running in production
sentinel-aggregator validate --workspace-config workspaces.yaml --strict
sentinel-aggregator health --workspace-config workspaces.yaml
```

## Next steps

- [SDK usage](sdk-usage.md)
- [Basic examples](examples/basic-examples.md)
- [Advanced examples](examples/advanced-examples.md)
- [Troubleshooting](troubleshooting.md)
