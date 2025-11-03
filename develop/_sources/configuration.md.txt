---
title: Configuration guide
description: Learn how to configure the Microsoft Sentinel Log Aggregator for your environment and requirements.
author: Microsoft
ms.author: sentinel-team
ms.service: sentinel
ms.topic: how-to
ms.date: 2025-11-01
---

# Configuration guide

This article explains how to configure the Microsoft Sentinel Log Aggregator for your specific environment and requirements.

## Configuration methods

The Sentinel Log Aggregator supports multiple configuration methods:

1. **Environment variables** (highest priority)
2. **YAML configuration files**
3. **Python code configuration**
4. **Default values** (lowest priority)

## Environment variables

Environment variables provide the highest precedence configuration method.

### Required settings

```powershell
# Data Collection Rule endpoint and ID
$env:DCR_LOGS_INGESTION_ENDPOINT = "https://your-dcr-endpoint.monitor.azure.com"
$env:DCR_RULE_ID = "dcr-your-rule-id"
```

### Optional settings

```powershell
# Time range configuration (choose one method)
# Method 1: Lookback period (recommended for scheduled runs)
$env:LOOKBACK_PERIOD = "P30D"         # ISO 8601 duration: P30D (30 days), PT24H (24 hours)

# Method 2: Explicit time range (for historical analysis)
$env:START_TIME = "2025-01-01T00:00:00Z"  # ISO 8601 datetime
$env:END_TIME = "2025-01-31T23:59:59Z"    # ISO 8601 datetime

# Method 3: Continue from last successful run (for incremental processing)
$env:USE_LAST_SUCCESSFUL = "true"     # Boolean: true/false
$env:HEALTH_LOGGING_ENABLED = "true"  # Required when using last successful

# Batch processing configuration
$env:BATCH_TIME_SIZE = "PT24H"        # ISO 8601 duration for batch size

# Performance settings
$env:MAX_CONCURRENT_QUERIES = 5       # Maximum concurrent queries
$env:QUERY_TIMEOUT_SECONDS = 300      # Query timeout in seconds
$env:MAX_RETRIES = 3                  # Maximum retry attempts
$env:RETRY_DELAY_SECONDS = 5          # Initial retry delay

# Logging configuration
$env:LOG_LEVEL = "INFO"               # Logging level (DEBUG, INFO, WARNING, ERROR)
$env:LOG_FORMAT = "json"              # Log format (json, text)

# Authentication settings (choose one method)
# Service Principal
$env:AZURE_CLIENT_ID = "your-client-id"
$env:AZURE_TENANT_ID = "your-tenant-id"
$env:AZURE_CLIENT_SECRET = "your-client-secret"

# Or Certificate-based authentication
$env:AZURE_CLIENT_CERTIFICATE_PATH = "C:/path/to/cert.pem"
```

### Environment file (.env)

Create a `.env` file in your working directory:

```ini
# .env file
DCR_LOGS_INGESTION_ENDPOINT=https://my-dcr.monitor.azure.com
DCR_RULE_ID=dcr-abc123def456

# Time range method 1: Lookback period
LOOKBACK_PERIOD=P7D
BATCH_TIME_SIZE=PT12H

# Alternative: Explicit time range
# START_TIME=2025-01-01T00:00:00Z
# END_TIME=2025-01-31T23:59:59Z

# Alternative: Last successful continuation
# USE_LAST_SUCCESSFUL=true
# HEALTH_LOGGING_ENABLED=true

MAX_CONCURRENT_QUERIES=3
LOG_LEVEL=DEBUG
```

## YAML configuration

### Client configuration

Create a `config.yaml` file for client settings:

```yaml
# config.yaml
dcr_logs_ingestion_endpoint: "https://your-dcr-endpoint.monitor.azure.com"
dcr_rule_id: "dcr-your-rule-id"

# Time range configuration (choose one method)
# Method 1: Lookback period
lookback_period: "P30D"               # ISO 8601 duration

# Method 2: Explicit time range
# start_time: "2025-01-01T00:00:00Z"  # ISO 8601 datetime
# end_time: "2025-01-31T23:59:59Z"    # ISO 8601 datetime

# Method 3: Last successful continuation
# use_last_successful: true           # Boolean
# health_logging_enabled: true        # Required for last successful

# Batch processing
batch_time_size: "PT24H"              # ISO 8601 duration

# Performance settings
max_concurrent_queries: 5
query_timeout_seconds: 300
max_retries: 3
retry_delay_seconds: 5
log_level: "INFO"
```

Load YAML configuration in Python:

```python
from sentinel_log_aggregator import SentinelAggregatorClientOptions

# Load from YAML file
options = SentinelAggregatorClientOptions.from_yaml_file("config.yaml")
```

### Workspace configuration

Create a `workspaces.yaml` file for workspace definitions:

```yaml
# workspaces.yaml
workspaces:
  - # Production workspace
    resource_id: "/subscriptions/12345678-1234-1234-1234-123456789012/resourcegroups/rg-prod/providers/microsoft.operationalinsights/workspaces/sentinel-prod"
    customer_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    parameters:
      row_level_security_tag: "production"
      environment: "prod"
      region: "eastus"
    queries_list:
      - "query_incident_summary"
      - "query_user_summary"
      - "query_security_alerts"
  
  - # Development workspace
    resource_id: "/subscriptions/12345678-1234-1234-1234-123456789012/resourcegroups/rg-dev/providers/microsoft.operationalinsights/workspaces/sentinel-dev"
    customer_id: "ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj"
    parameters:
      row_level_security_tag: "development"
      environment: "dev"
      region: "westus"
    queries_list:
      - "query_incident_summary"
      - "query_user_summary"

# Optional metadata
metadata:
  version: "1.2"
  description: "Microsoft Sentinel workspaces for security analytics"
  owner: "security-team@company.com"
  last_updated: "2025-11-01"
  environment: "production"
```

## Configuration in code

### Client options

Configure client options programmatically:

```python
from sentinel_log_aggregator import SentinelAggregatorClientOptions

# Create options with explicit values
options = SentinelAggregatorClientOptions(
    dcr_logs_ingestion_endpoint="https://your-dcr.monitor.azure.com",
    dcr_rule_id="dcr-your-rule-id",
    
    # Time range method 1: Lookback period
    lookback_period="P7D",
    batch_time_size="PT12H",
    
    # Alternative: Explicit time range
    # start_time="2025-01-01T00:00:00Z",
    # end_time="2025-01-31T23:59:59Z",
    
    # Alternative: Last successful continuation
    # use_last_successful=True,
    # health_logging_enabled=True,
    max_concurrent_queries=3,
    query_timeout_seconds=300,
    log_level="DEBUG"
)

# Validate configuration
options.validate()
```

### Workspace configuration

Define workspaces in code:

```python
from sentinel_log_aggregator import WorkspaceConfig, WorkspaceManager

# Create workspace configurations
workspaces = [
    WorkspaceConfig(
        resource_id="/subscriptions/sub-id/resourcegroups/rg/providers/microsoft.operationalinsights/workspaces/ws1",
        customer_id="workspace-customer-id-1",
        parameters={"row_level_security_tag": "prod"},
        queries_list=["query_incident_summary", "query_user_summary"]
    ),
    WorkspaceConfig(
        resource_id="/subscriptions/sub-id/resourcegroups/rg/providers/microsoft.operationalinsights/workspaces/ws2",
        customer_id="workspace-customer-id-2",
        parameters={"row_level_security_tag": "dev"},
        queries_list=["query_incident_summary"]
    )
]

# Create workspace manager
workspace_manager = WorkspaceManager(workspaces)

# Validate configuration
errors = workspace_manager.validate_configuration()
if errors:
    print("Configuration errors:", errors)
```

## Advanced configuration

### Custom retry policies

```python
from azure.core.pipeline.policies import ExponentialRetry

options = SentinelAggregatorClientOptions(
    dcr_logs_ingestion_endpoint="https://your-dcr.monitor.azure.com",
    dcr_rule_id="dcr-your-rule-id",
    max_retries=5,
    retry_delay_seconds=2
)

# The client will automatically use exponential backoff
```

### Logging configuration

```python
import logging
from sentinel_log_aggregator.logging_utils import configure_logging

# Configure structured logging
configure_logging(
    level=logging.DEBUG,
    format_type="json",
    enable_correlation_ids=True
)
```

### Connection string configuration

```python
from sentinel_log_aggregator import SentinelAggregatorClient

# Create client from connection string
client = SentinelAggregatorClient.from_connection_string(
    "endpoint=https://your-dcr.monitor.azure.com;dcr_rule_id=dcr-your-rule-id;timeout=300"
)
```

## Configuration validation

### Validate client configuration

```python
from sentinel_log_aggregator import SentinelAggregatorClientOptions

try:
    options = SentinelAggregatorClientOptions.from_environment()
    options.validate()
    print("Configuration is valid")
except Exception as e:
    print(f"Configuration error: {e}")
```

### Validate workspace configuration

```python
from sentinel_log_aggregator import WorkspaceManager

# Load and validate workspace configuration
workspace_manager = WorkspaceManager.from_file("workspaces.yaml")
errors = workspace_manager.validate_configuration()

if errors:
    print("Workspace configuration errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Workspace configuration is valid")
```

### CLI validation

```powershell
# Validate all configuration
sentinel-aggregator validate --workspace-config workspaces.yaml

# Validate specific configuration file
sentinel-aggregator validate --config-file config.yaml --workspace-config workspaces.yaml
```

## Configuration best practices

### Security

1. **Use managed identity** when possible for Azure-hosted applications
2. **Store secrets securely** using Azure Key Vault or environment variables
3. **Avoid hardcoding credentials** in configuration files
4. **Use least privilege permissions** for service principals

### Performance

1. **Tune concurrent queries** based on workspace limits and performance requirements
2. **Adjust batch sizes** based on data volume and processing capacity
3. **Set appropriate timeouts** for your query complexity and data volume
4. **Use correlation IDs** for tracking and debugging

### Monitoring

1. **Enable structured logging** for better observability
2. **Configure appropriate log levels** for your environment
3. **Use correlation IDs** for distributed tracing
4. **Monitor query performance** and adjust configurations accordingly

### Example production configuration

```yaml
# Production configuration example
dcr_logs_ingestion_endpoint: "https://prod-dcr.monitor.azure.com"
dcr_rule_id: "dcr-prod-sentinel-analytics"

# Production time configuration - 30 day lookback with daily batches
lookback_period: "P30D"
batch_time_size: "PT24H"

max_concurrent_queries: 10
query_timeout_seconds: 600
max_retries: 5
retry_delay_seconds: 10
log_level: "INFO"
```

```yaml
# Production workspaces example
workspaces:
  - resource_id: "/subscriptions/prod-sub/resourcegroups/security-rg/providers/microsoft.operationalinsights/workspaces/sentinel-prod-east"
    customer_id: "prod-east-workspace-id"
    parameters:
      row_level_security_tag: "prod-east"
      environment: "production"
      region: "eastus"
      compliance_zone: "regulated"
    queries_list:
      - "query_incident_summary"
      - "query_user_summary"
      - "query_security_alerts"
      - "query_compliance_events"
  
  - resource_id: "/subscriptions/prod-sub/resourcegroups/security-rg/providers/microsoft.operationalinsights/workspaces/sentinel-prod-west"
    customer_id: "prod-west-workspace-id"
    parameters:
      row_level_security_tag: "prod-west"
      environment: "production"
      region: "westus"
      compliance_zone: "standard"
    queries_list:
      - "query_incident_summary"
      - "query_user_summary"
      - "query_security_alerts"

metadata:
  version: "2.1"
  description: "Production Microsoft Sentinel workspaces"
  owner: "security-operations@company.com"
  last_updated: "2025-11-01"
  environment: "production"
  compliance_level: "enterprise"
```

## Next steps

- [CLI usage](cli-usage.md)
- [SDK usage](sdk-usage.md)
- [Basic examples](examples/basic-examples.md)
- [Troubleshooting](troubleshooting.md)
