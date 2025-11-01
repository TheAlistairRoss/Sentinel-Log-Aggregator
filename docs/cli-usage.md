---
title: CLI usage
description: Learn how to use the Microsoft Sentinel Log Aggregator command-line interface for automation and manual operations.
author: Microsoft
ms.author: sentinel-team
ms.service: sentinel
ms.topic: reference
ms.date: 2025-11-01
---

# CLI usage

The Microsoft Sentinel Log Aggregator includes a comprehensive command-line interface (CLI) that follows Azure CLI patterns and conventions. The CLI is ideal for automation, CI/CD pipelines, and manual operations.

## Installation

The CLI is included when you install the package:

```bash
pip install sentinel-log-aggregator
```

## Global options

Global options apply to all commands:

```bash
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

| Option | Description | Required | Default |
|--------|-------------|----------|---------|
| `--workspace-config` | Path to workspace configuration file | Yes | |
| `--days-back` | Number of days to look back | No | 30 |
| `--batch-hours` | Hours per batch | No | 24 |
| `--queries` | Specific queries to run (comma-separated) | No | All |
| `--workspaces` | Specific workspaces to process (comma-separated) | No | All |
| `--dry-run` | Validate and show what would be executed | No | `false` |
| `--parallel` | Enable parallel execution | No | `true` |
| `--max-workers` | Maximum parallel workers | No | 5 |

#### Examples

```bash
# Basic run with default settings
sentinel-aggregator run --workspace-config workspaces.yaml

# Run with custom time range
sentinel-aggregator run --workspace-config workspaces.yaml --days-back 7 --batch-hours 12

# Run specific queries only
sentinel-aggregator run --workspace-config workspaces.yaml --queries "query_incident_summary,query_user_summary"

# Run for specific workspaces
sentinel-aggregator run --workspace-config workspaces.yaml --workspaces "prod-workspace,dev-workspace"

# Dry run to validate configuration
sentinel-aggregator run --workspace-config workspaces.yaml --dry-run

# Run with custom parallelism
sentinel-aggregator run --workspace-config workspaces.yaml --max-workers 10

# Sequential execution (no parallelism)
sentinel-aggregator run --workspace-config workspaces.yaml --parallel false
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

```bash
# CLI-specific environment variables
SENTINEL_CLI_CONFIG_FILE=cli-config.yaml
SENTINEL_CLI_OUTPUT_FORMAT=json
SENTINEL_CLI_NO_COLOR=false
SENTINEL_CLI_AUTO_CONFIRM=false
```

## Automation and scripting

### Bash scripting

```bash
#!/bin/bash

# Automated aggregation script
set -e

CONFIG_FILE="workspaces.yaml"
LOG_LEVEL="INFO"

# Function to run aggregation with error handling
run_aggregation() {
    local days_back=${1:-30}
    local batch_hours=${2:-24}
    
    echo "Starting aggregation: days_back=$days_back, batch_hours=$batch_hours"
    
    if sentinel-aggregator validate --workspace-config "$CONFIG_FILE"; then
        echo "Configuration validated successfully"
        
        sentinel-aggregator --log-level "$LOG_LEVEL" run \
            --workspace-config "$CONFIG_FILE" \
            --days-back "$days_back" \
            --batch-hours "$batch_hours"
        
        echo "Aggregation completed successfully"
    else
        echo "Configuration validation failed"
        exit 1
    fi
}

# Health check before running
if sentinel-aggregator health --workspace-config "$CONFIG_FILE"; then
    echo "Health check passed"
    run_aggregation 7 12
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
    param($DaysBack, $BatchHours, $ConfigFile)
    
    Write-Host "Starting aggregation: DaysBack=$DaysBack, BatchHours=$BatchHours"
    
    # Validate configuration
    $validateResult = sentinel-aggregator validate --workspace-config $ConfigFile
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Configuration validation failed"
        exit 1
    }
    
    Write-Host "Configuration validated successfully"
    
    # Run aggregation
    sentinel-aggregator run --workspace-config $ConfigFile --days-back $DaysBack --batch-hours $BatchHours
    
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
    Start-Aggregation -DaysBack $DaysBack -BatchHours $BatchHours -ConfigFile $ConfigFile
} else {
    Write-Error "Health check failed"
    exit 1
}
```

### CI/CD integration

#### Azure DevOps Pipeline

```yaml
# azure-pipelines.yml
trigger:
  - main

variables:
  pythonVersion: '3.11'

stages:
- stage: Validate
  jobs:
  - job: ValidateConfig
    pool:
      vmImage: 'ubuntu-latest'
    steps:
    - task: UsePythonVersion@0
      inputs:
        versionSpec: '$(pythonVersion)'
    
    - script: |
        pip install sentinel-log-aggregator
      displayName: 'Install package'
    
    - script: |
        sentinel-aggregator validate --workspace-config workspaces.yaml
      displayName: 'Validate configuration'

- stage: Deploy
  dependsOn: Validate
  jobs:
  - job: RunAggregation
    pool:
      vmImage: 'ubuntu-latest'
    steps:
    - script: |
        sentinel-aggregator health --workspace-config workspaces.yaml
        sentinel-aggregator run --workspace-config workspaces.yaml --days-back 1
      displayName: 'Run aggregation'
      env:
        DCR_LOGS_INGESTION_ENDPOINT: $(DCR_ENDPOINT)
        DCR_RULE_ID: $(DCR_RULE_ID)
        AZURE_CLIENT_ID: $(AZURE_CLIENT_ID)
        AZURE_CLIENT_SECRET: $(AZURE_CLIENT_SECRET)
        AZURE_TENANT_ID: $(AZURE_TENANT_ID)
```

#### GitHub Actions

```yaml
# .github/workflows/sentinel-aggregation.yml
name: Sentinel Log Aggregation

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  aggregate:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install sentinel-log-aggregator
    
    - name: Validate configuration
      run: |
        sentinel-aggregator validate --workspace-config workspaces.yaml
    
    - name: Run health check
      run: |
        sentinel-aggregator health --workspace-config workspaces.yaml
      env:
        DCR_LOGS_INGESTION_ENDPOINT: ${{ secrets.DCR_ENDPOINT }}
        DCR_RULE_ID: ${{ secrets.DCR_RULE_ID }}
        AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
        AZURE_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
        AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
    
    - name: Run aggregation
      run: |
        sentinel-aggregator run --workspace-config workspaces.yaml --days-back 1
      env:
        DCR_LOGS_INGESTION_ENDPOINT: ${{ secrets.DCR_ENDPOINT }}
        DCR_RULE_ID: ${{ secrets.DCR_RULE_ID }}
        AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
        AZURE_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
        AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
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
