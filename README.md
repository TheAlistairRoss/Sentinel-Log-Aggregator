# Microsoft Sentinel Log Aggregator

An Azure SDK-compliant Python client library for aggregating and processing logs from multiple Microsoft Sentinel workspaces into centralized reporting tables for security analytics and dashboard creation.

## Features

- **Azure SDK Compliance**: Follows Microsoft Azure SDK design guidelines and patterns
- **Multi-workspace Support**: Query and aggregate data across multiple Sentinel workspaces
- **Batch Processing**: Configurable time-based batching with concurrent execution
- **Centralized Reporting**: Transform and normalize data for centralized analytics
- **Comprehensive Error Handling**: Service-specific exceptions with detailed error information
- **Distributed Tracing**: Built-in Azure Monitor Application Insights integration
- **Long-running Operations**: LRO support for batch operations with progress tracking
- **Health Monitoring**: Built-in health checks and service diagnostics
- **Standard Authentication**: Azure Identity integration with multiple credential types

## Installation

### Requirements
- Python 3.11 or higher (tested on Python 3.11-3.14)
- Azure subscription with Microsoft Sentinel workspaces
- Appropriate Azure permissions (see Configuration section)

### Install from GitHub

#### Install Latest Release (Recommended)
```bash
# Install from latest GitHub release
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git

# Install from specific tag/version
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git@v0.1.0
```

#### Install from Release Package
```bash
# Install wheel package from releases
pip install https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/releases/latest/download/sentinel_log_aggregator-0.1.0-py3-none-any.whl

# Install source distribution from releases
pip install https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/releases/download/v0.1.0/sentinel-log-aggregator-0.1.0.tar.gz
```

#### Install from Development Branches
```bash
# Install from develop branch (latest development features)
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git@develop

# Install from any specific branch
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git@feature/your-branch-name

# Install from specific commit
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git@abc123f
```

> **⚠️ Development Branch Warning**: Development branches may contain unstable features and breaking changes. Always use tagged releases for production environments.

#### Development Installation (Editable)
```bash
# Clone and install in editable mode for development
git clone https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git
cd Sentinel-Log-Aggregator

# Switch to develop branch (optional)
git checkout develop

# Install in editable mode with development dependencies
pip install -e ".[dev,security]"
```

# Microsoft Sentinel Log Aggregator

An Azure SDK-compliant Python client library for aggregating and processing logs from multiple Microsoft Sentinel workspaces into centralized reporting tables for security analytics and dashboard creation.

## Features

- **Azure SDK Compliance**: Follows Microsoft Azure SDK design guidelines and patterns
- **Multi-workspace Support**: Query and aggregate data across multiple Sentinel workspaces
- **Batch Processing**: Configurable time-based batching with concurrent execution
- **Centralized Reporting**: Transform and normalize data for centralized analytics
- **Microsecond Precision**: ISO 8601 datetime formatting with 6-decimal precision prevents data gaps
- **Comprehensive Error Handling**: Service-specific exceptions with detailed error information
- **Distributed Tracing**: Built-in Azure Monitor Application Insights integration
- **Long-running Operations**: LRO support for batch operations with progress tracking
- **Health Monitoring**: Built-in health checks and service diagnostics
- **Standard Authentication**: Azure Identity integration with multiple credential types
- **Flexible Query Organization**: Support for custom query directory structures and relative paths

## Quick Start

### Simple Installation and Basic Usage

This section covers the fastest way to get started with basic functionality.

#### Install the Package

```bash
# Install from GitHub (latest release)
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git
```

#### Basic Configuration

Create a simple environment configuration:

```bash
# Required settings
export DCR_LOGS_INGESTION_ENDPOINT="https://your-dcr-endpoint.monitor.azure.com"
export DCR_RULE_ID="dcr-your-rule-id"

# Time range options (use one of these methods):

# Option 1: Lookback period (ISO 8601 duration)
export LOOKBACK_PERIOD="P7D"              # Look back 7 days
export BATCH_TIME_SIZE="PT12H"            # Process in 12-hour batches

# Option 2: Explicit time range
export START_TIME="2025-01-01T00:00:00Z"  # Explicit start time (ISO 8601)
export END_TIME="2025-01-07T00:00:00Z"    # Explicit end time (ISO 8601)
export BATCH_TIME_SIZE="PT6H"             # Process in 6-hour batches

# Option 3: Use last successful runs (requires health logging)
export USE_LAST_SUCCESSFUL=true           # Start from last successful completion
export HEALTH_LOGGING_ENABLED=true       # Enable health tracking
export BATCH_TIME_SIZE="PT24H"           # Process in 24-hour batches

# Optional settings
export LOG_LEVEL=INFO
```

#### Create Your First Query

Create a simple query file `my_query.yaml`:

```yaml
name: "security_events_summary"
destination_stream: "Custom-SecuritySummary_CL"
description: "Basic security events summary"

parameters:
  row_level_security_tag:
    type: "string"
    required: false
    default: ""

query: |
  SecurityEvent
  | where TimeGenerated > ago(7d)
  | summarize EventCount = count() by Computer
  | extend WorkspaceTag = "{row_level_security_tag}"
```

#### Create Workspace Configuration

Create a simple `workspaces.yaml`:

```yaml
workspaces:
  - resource_id: "/subscriptions/YOUR-SUB-ID/resourcegroups/YOUR-RG/providers/microsoft.operationalinsights/workspaces/YOUR-WORKSPACE"
    customer_id: "YOUR-WORKSPACE-CUSTOMER-ID"
    queries_list:
      - "my_query.yaml"
    parameters:
      row_level_security_tag: "main"
```

#### Run the Aggregator

```bash
# Run with your configuration
sentinel-aggregator run --workspace-config workspaces.yaml
```

### Simple Programmatic Usage

For basic programmatic usage without complex configuration:

```python
import asyncio
from azure.identity.aio import DefaultAzureCredential
from sentinel_log_aggregator import SentinelAggregatorClient

async def simple_example():
    # Auto-configure from environment variables
    credential = DefaultAzureCredential()
    
    # Connection string approach (simplest)
    client = SentinelAggregatorClient.from_connection_string(
        "endpoint=https://your-dcr.monitor.azure.com;dcr_rule_id=dcr-your-rule-id"
    )
    
    async with client:
        # Quick health check
        health = await client.get_service_properties()
        print(f"Service status: {health.connectivity_status}")
        
        # Simple query
        result = await client.query_workspace(
            workspace_id="your-workspace-id",
            query="SecurityEvent | take 5"
        )
        
        if result.succeeded:
            print(f"Got {result.record_count} records")

# Run it
asyncio.run(simple_example())
```

---

## Advanced Setup and Configuration

This section covers complex scenarios, enterprise deployments, and advanced configuration options.

### Installation Options

#### Production Installation

```bash
# Install from specific release tag
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git@v0.1.0

# Install from release package (exact version control)
pip install https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/releases/download/v0.1.0/sentinel-log-aggregator-0.1.0.tar.gz
```

#### Development Installation

```bash
# Clone and install in editable mode
git clone https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git
cd Sentinel-Log-Aggregator
git checkout develop  # Latest development features
pip install -e ".[dev,security]"
```

#### Branch-Specific Installation

```bash
# Install from development branch (latest features)
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git@develop

# Install from specific feature branch
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git@feature/your-branch-name

# Install from specific commit
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git@abc123f
```

> **⚠️ Development Branch Warning**: Development branches may contain unstable features and breaking changes. Always use tagged releases for production environments.

### Advanced Environment Configuration

#### Complete Environment Variables

```bash
# Required settings
DCR_LOGS_INGESTION_ENDPOINT=https://your-dcr-endpoint.monitor.azure.com
DCR_RULE_ID=dcr-your-rule-id

# Time range configuration (choose one method)
# Method 1: Lookback period (recommended for scheduled runs)
LOOKBACK_PERIOD=P30D                    # ISO 8601 duration: P30D (30 days), PT24H (24 hours), P1DT12H (1.5 days)

# Method 2: Explicit time range (for historical analysis)
START_TIME=2025-01-01T00:00:00Z         # ISO 8601 datetime
END_TIME=2025-01-31T23:59:59Z           # ISO 8601 datetime

# Method 3: Continue from last successful run (for incremental processing)
USE_LAST_SUCCESSFUL=true               # Boolean: true/false
HEALTH_LOGGING_ENABLED=true            # Required when using last successful

# Batch processing configuration
BATCH_TIME_SIZE=PT24H                  # ISO 8601 duration: batch size for time-based processing

# Performance tuning
MAX_CONCURRENT_QUERIES=5               # Number of concurrent queries
QUERY_TIMEOUT_SECONDS=300              # Query timeout in seconds

# Logging and monitoring
LOG_LEVEL=INFO
CORRELATION_ID_PREFIX=sentinel-agg

# Authentication - choose one method:

# Option 1: Managed Identity (recommended for Azure-hosted environments)
# No additional configuration needed

# Option 2: Service Principal (CI/CD and automation)
AZURE_CLIENT_ID=your-client-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_SECRET=your-client-secret

# Option 3: Azure CLI (development)
# Run 'az login' first, then no additional config needed
```

#### YAML Configuration File

Create a comprehensive `config.yaml`:

```yaml
# Core configuration
dcr_logs_ingestion_endpoint: "https://your-endpoint.monitor.azure.com"
dcr_rule_id: "dcr-your-rule-id"

# Time range configuration (choose one method)
# Method 1: Lookback period
lookback_period: "P30D"              # ISO 8601 duration

# Method 2: Explicit time range
start_time: "2025-01-01T00:00:00Z"   # ISO 8601 datetime
end_time: "2025-01-31T23:59:59Z"     # ISO 8601 datetime

# Method 3: Last successful continuation
use_last_successful: true           # Boolean
health_logging_enabled: true        # Required for last successful

# Batch processing
batch_time_size: "PT24H"            # ISO 8601 duration

# Performance settings
max_concurrent_queries: 10
query_timeout_seconds: 600

# Monitoring settings
log_level: "INFO"
enable_distributed_tracing: true
correlation_id_prefix: "sentinel-prod"

# Retry configuration
max_retries: 3
retry_delay_seconds: 5
exponential_backoff: true

# Security settings
validate_queries: true
sanitize_parameters: true
```

### Complex Workspace Configuration

Create an enterprise-grade `workspaces.yaml`:

```yaml
# Enterprise Microsoft Sentinel Workspaces Configuration
metadata:
  version: "2.0"
  description: "Production workspace configuration for security analytics"
  last_updated: "2025-11-03"
  environment: "production"

workspaces:
  # Production Security Operations Center
  - resource_id: "/subscriptions/prod-sub-id/resourcegroups/security-rg/providers/microsoft.operationalinsights/workspaces/prod-soc-sentinel"
    customer_id: "12345678-1234-1234-1234-123456789012"
    queries_list:
      - "queries/security/incident_analysis.yaml"
      - "queries/security/threat_intelligence.yaml"
      - "queries/compliance/regulatory_audit.yaml"
      - "queries/reports/executive_summary.yaml"
    parameters:
      row_level_security_tag: "prod-soc"
      environment: "production"
      region: "east-us"
      cost_center: "security-ops"
  
  # Development Environment
  - resource_id: "/subscriptions/dev-sub-id/resourcegroups/dev-rg/providers/microsoft.operationalinsights/workspaces/dev-sentinel"
    customer_id: "87654321-4321-4321-4321-210987654321"
    queries_list:
      - "queries/development/test_scenarios.yaml"
      - "queries/shared/baseline_metrics.yaml"
    parameters:
      row_level_security_tag: "dev"
      environment: "development"
      region: "west-us"
  
  # Regional SOC - Europe
  - resource_id: "/subscriptions/eu-sub-id/resourcegroups/eu-security-rg/providers/microsoft.operationalinsights/workspaces/eu-soc-sentinel"
    customer_id: "11111111-2222-3333-4444-555555555555"
    queries_list:
      - "queries/security/incident_analysis.yaml"
      - "queries/compliance/gdpr_compliance.yaml"
      - "queries/regional/eu_specific_threats.yaml"
    parameters:
      row_level_security_tag: "eu-soc"
      environment: "production"
      region: "north-europe"
      gdpr_compliant: true
      data_residency: "eu"

# Environment-specific settings
environments:
  production:
    max_concurrent_queries: 3
    batch_hours: 12
    enable_monitoring: true
  
  development:
    max_concurrent_queries: 2
    batch_hours: 6
    enable_monitoring: false
```

### Query Organization and Setup

For complex query organization, see the dedicated [Query Setup Guide](docs/query-setup.md) which covers:

- **Flexible Directory Structures**: Organize queries by type, environment, or team
- **Query File Format**: Complete YAML specification with parameters and metadata
- **Relative Path Configuration**: Use file paths instead of hardcoded query names
- **Parameter Substitution**: Advanced parameter handling and type validation
- **Best Practices**: Query development, testing, and deployment guidelines

Quick example of advanced query organization:

```yaml
# Advanced workspace configuration with organized queries
workspaces:
  - resource_id: "/subscriptions/.../workspaces/enterprise-sentinel"
    customer_id: "your-workspace-id"
    queries_list:
      # Security team queries
      - "queries/security-team/incident_response.yaml"
      - "queries/security-team/threat_hunting.yaml"
      
      # Compliance queries
      - "queries/compliance/sox_audit.yaml"
      - "queries/compliance/pci_monitoring.yaml"
      
      # Custom analytics
      - "custom/executive_dashboard.yaml"
      - "custom/regional_analysis.yaml"
    parameters:
      row_level_security_tag: "enterprise"
      compliance_level: "high"
```

---

## Programmatic Usage (Advanced)

Advanced programmatic usage for enterprise applications and custom integrations.

### Azure SDK-Compliant Client

```python
import asyncio
from azure.identity.aio import DefaultAzureCredential, ClientSecretCredential
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    WorkspaceConfig
)

async def enterprise_example():
    # Advanced client configuration with new time parameters
    options = SentinelAggregatorClientOptions(
        # Time range method 1: Lookback period
        lookback_period="P30D",              # 30 days back (ISO 8601)
        batch_time_size="PT12H",             # 12-hour batches (ISO 8601)
        
        # Alternative: Explicit time range
        # start_time="2025-01-01T00:00:00Z",
        # end_time="2025-01-31T23:59:59Z",
        
        # Alternative: Continue from last successful
        # use_last_successful=True,
        # health_logging_enabled=True,
        
        # Performance settings
        max_concurrent_queries=10,
        query_timeout_seconds=600,
        log_level="DEBUG",
        enable_distributed_tracing=True,
        correlation_id_prefix="enterprise-analytics"
    )
    
    # Choose authentication method
    credential = DefaultAzureCredential()
    # Or for service principal:
    # credential = ClientSecretCredential(tenant_id, client_id, client_secret)
    
    # Create client with full configuration
    async with SentinelAggregatorClient(
        dcr_logs_ingestion_endpoint="https://your-dcr.monitor.azure.com",
        credential=credential,
        options=options
    ) as client:
        
        # Health check with detailed diagnostics
        service_props = await client.get_service_properties()
        print(f"Service version: {service_props.service_version}")
        print(f"Connectivity: {service_props.connectivity_status}")
        print(f"Features: {service_props.supported_features}")
        
        # Complex workspace configurations
        workspaces = [
            WorkspaceConfig(
                resource_id="/subscriptions/.../workspaces/prod-soc",
                customer_id="prod-workspace-id",
                queries_list=["queries/security/advanced_analytics.yaml"],
                parameters={
                    "row_level_security_tag": "prod-soc",
                    "environment": "production",
                    "compliance_level": "high"
                }
            ),
            WorkspaceConfig(
                resource_id="/subscriptions/.../workspaces/dev-soc",
                customer_id="dev-workspace-id", 
                queries_list=["queries/development/test_analytics.yaml"],
                parameters={
                    "row_level_security_tag": "dev-soc",
                    "environment": "development"
                }
            )
        ]
        
        # Execute with advanced error handling
        try:
            for workspace in workspaces:
                for query_path in workspace.queries_list:
                    result = await client.query_workspace_with_path(
                        workspace_id=workspace.customer_id,
                        query_path=query_path,
                        parameters=workspace.parameters
                    )
                    
                    if result.succeeded:
                        # Process and upload results
                        upload_result = await client.upload_logs(
                            data=result.data,
                            stream_name=result.stream_name
                        )
                        
                        print(f"✅ {query_path}: {upload_result.record_count} records uploaded")
                    else:
                        print(f"❌ {query_path}: {result.error_message}")
                        
        except Exception as e:
            print(f"Critical error: {e}")

asyncio.run(enterprise_example())
```

### Long-Running Operations (LRO)

```python
async def batch_operations_example():
    async with SentinelAggregatorClient(endpoint, credential, options=options) as client:
        # Start long-running batch operation
        poller = await client.begin_batch_operation(
            workspaces=workspace_configs,
            queries=["query_incident_summary", "query_user_analytics"],
            correlation_id="batch-2025-11-03"
        )
        
        print("🚀 Batch operation started...")
        
        # Monitor progress with detailed feedback
        while not poller.done():
            try:
                # Get intermediate results (non-blocking)
                result = poller.result(timeout=30)
                
                print(f"📊 Progress: {result.completed_operations}/{result.total_operations}")
                print(f"✅ Successful: {result.success_count}")
                print(f"❌ Failed: {result.error_count}")
                print(f"⏱️ Elapsed: {result.elapsed_time}s")
                
                # Optional: pause between checks
                await asyncio.sleep(10)
                
            except TimeoutError:
                print("⏳ Operation still in progress...")
        
        # Get final comprehensive results
        final_result = await poller.result()
        
        print(f"🎯 Batch completed:")
        print(f"  Total operations: {final_result.total_operations}")
        print(f"  Successful: {final_result.success_count}")
        print(f"  Failed: {final_result.error_count}")
        print(f"  Total records: {final_result.total_records}")
        print(f"  Execution time: {final_result.total_execution_time}s")
        
        # Process any failures
        for failure in final_result.failures:
            print(f"❌ Failed: {failure.workspace_id} - {failure.error_message}")
```

### Custom Query Loading and Execution

```python
from sentinel_log_aggregator.query_registry import QueryRegistry
from pathlib import Path

async def custom_query_management():
    # Advanced query registry usage
    registry = QueryRegistry()
    
    # Load queries from multiple sources
    registry.load_queries_from_directory(Path("queries/production"), recursive=True)
    registry.load_queries_from_directory(Path("queries/shared"))
    
    # Load specific queries dynamically
    custom_query = registry.load_query_from_path(
        "custom/special_analysis.yaml",
        base_directory=Path(".")
    )
    
    # Validate all queries before execution
    validation_results = registry.validate_all_queries()
    for query_name, issues in validation_results.items():
        if issues:
            print(f"⚠️ Query {query_name} has validation issues:")
            for issue in issues:
                print(f"  - {issue}")
    
    # Get query metadata
    for query_name in registry.list_queries():
        metadata = registry.get_metadata(query_name)
        print(f"📋 {query_name}: {metadata.description}")
        print(f"   Tags: {metadata.tags}")
        print(f"   Version: {metadata.version}")
    
    # Execute with custom parameters
    async with SentinelAggregatorClient(endpoint, credential) as client:
        query = registry.get_query("advanced_threat_detection")
        
        custom_params = {
            "row_level_security_tag": "enterprise",
            "time_window_hours": 72,
            "severity_threshold": "High",
            "threat_types": "Malware,Phishing,C2"
        }
        
        result = await client.execute_query(
            workspace_id="workspace-id",
            query=query,
            parameters=custom_params
        )
```

---

## CLI Usage (Advanced)

Enterprise-grade command-line usage for automation, monitoring, and operations.

### Health Monitoring and Diagnostics

```bash
# Comprehensive health check with detailed output
sentinel-aggregator health \
  --workspace-config workspaces.yaml \
  --verbose \
  --output-format json

# Health check with specific workspace validation
sentinel-aggregator health \
  --workspace-config workspaces.yaml \
  --workspace-filter "environment=production" \
  --test-queries

# Export health metrics for monitoring systems
sentinel-aggregator health \
  --workspace-config workspaces.yaml \
  --export-metrics \
  --metrics-format prometheus
```

### Production Execution

```bash
# Production run with lookback period (recommended)
sentinel-aggregator run \
  --workspace-config workspaces.yaml \
  --config config.yaml \
  --lookback-period "P30D" \
  --batch-time-size "PT12H" \
  --max-concurrent 5 \
  --correlation-id "prod-run-$(date +%Y%m%d-%H%M%S)"

# Run with explicit time range (historical analysis)
sentinel-aggregator run \
  --workspace-config workspaces.yaml \
  --start-time "2025-01-01T00:00:00Z" \
  --end-time "2025-01-31T23:59:59Z" \
  --batch-time-size "PT6H"

# Continue from last successful run (incremental processing)
sentinel-aggregator run \
  --workspace-config workspaces.yaml \
  --use-last-successful \
  --health-logging-enabled

# Run with workspace filtering (enterprise scenarios)
sentinel-aggregator run \
  --workspace-config workspaces.yaml \
  --workspace-filter "environment=production,region=us-east" \
  --query-filter "tags=compliance,security"

# Dry run for validation (staging/testing)
sentinel-aggregator run \
  --workspace-config workspaces.yaml \
  --dry-run \
  --validate-only \
  --verbose
```

### New CLI Commands

```bash
# Check last successful runs across workspaces
sentinel-aggregator query-status \
  --workspace-config workspaces.yaml \
  --show-details

# Query status for specific queries
sentinel-aggregator query-status \
  --workspace-config workspaces.yaml \
  --query-filter "incident_summary,threat_hunting" \
  --lookback-days 7

# Show execution history and timing
sentinel-aggregator query-status \
  --workspace-config workspaces.yaml \
  --show-execution-history \
  --format table
```

### Advanced Validation and Testing

```bash
# Comprehensive configuration validation
sentinel-aggregator validate \
  --workspace-config workspaces.yaml \
  --config config.yaml \
  --validate-queries \
  --validate-permissions \
  --validate-connectivity

# Query-specific validation
sentinel-aggregator validate \
  --workspace-config workspaces.yaml \
  --query-path "queries/security/advanced_analytics.yaml" \
  --test-parameters \
  --check-syntax

# Environment validation for deployment
sentinel-aggregator validate \
  --workspace-config workspaces.yaml \
  --environment production \
  --check-quotas \
  --verify-dcr-access
```

### Monitoring and Logging

```bash
# Debug mode with comprehensive logging
sentinel-aggregator \
  --log-level DEBUG \
  --log-format json \
  --correlation-id "debug-session-123" \
  run --workspace-config workspaces.yaml

# Export execution metrics
sentinel-aggregator run \
  --workspace-config workspaces.yaml \
  --export-metrics \
  --metrics-file execution-metrics.json \
  --enable-performance-tracking

# Run with custom log destination
sentinel-aggregator \
  --log-file /var/log/sentinel-aggregator.log \
  --log-level INFO \
  run --workspace-config workspaces.yaml
```

---

## Configuration Reference

### Client Options

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `dcr_logs_ingestion_endpoint` | `DCR_LOGS_INGESTION_ENDPOINT` | Required | Azure Monitor ingestion endpoint |
| `dcr_rule_id` | `DCR_RULE_ID` | Required | Data Collection Rule ID |
| **Time Range Options (choose one method)** | | | |
| `lookback_period` | `LOOKBACK_PERIOD` | "P30D" | ISO 8601 duration for relative time range |
| `start_time` | `START_TIME` | None | ISO 8601 datetime for explicit start time |
| `end_time` | `END_TIME` | None | ISO 8601 datetime for explicit end time |
| `use_last_successful` | `USE_LAST_SUCCESSFUL` | false | Continue from last successful completion |
| **Batch Processing** | | | |
| `batch_time_size` | `BATCH_TIME_SIZE` | "PT24H" | ISO 8601 duration for batch size |
| **Performance** | | | |
| `max_concurrent_queries` | `MAX_CONCURRENT_QUERIES` | 5 | Maximum concurrent query execution |
| `query_timeout_seconds` | `QUERY_TIMEOUT_SECONDS` | 300 | Query timeout in seconds |
| **Monitoring** | | | |
| `health_logging_enabled` | `HEALTH_LOGGING_ENABLED` | false | Enable health tracking and logging |
| `log_level` | `LOG_LEVEL` | INFO | Logging level |

### ISO 8601 Time Format Reference

The new time parameters use ISO 8601 standardized formats for maximum precision and clarity.

#### Duration Examples (`lookback_period`, `batch_time_size`)

| Duration | ISO 8601 Format | Description |
|----------|----------------|-------------|
| 1 hour | `PT1H` | 1 hour |
| 6 hours | `PT6H` | 6 hours |
| 12 hours | `PT12H` | 12 hours |
| 1 day | `P1D` or `PT24H` | 24 hours |
| 3 days | `P3D` | 3 days |
| 1 week | `P7D` | 7 days |
| 1 month | `P30D` | 30 days |
| 1.5 days | `P1DT12H` | 1 day + 12 hours |
| 2 hours 30 minutes | `PT2H30M` | 2.5 hours |

#### DateTime Examples (`start_time`, `end_time`)

| Description | ISO 8601 Format |
|-------------|----------------|
| UTC midnight | `2025-01-01T00:00:00Z` |
| UTC with time | `2025-01-15T14:30:00Z` |
| With microseconds | `2025-01-15T14:30:00.123456Z` |
| Timezone offset | `2025-01-15T14:30:00+05:00` |

#### Time Range Configuration Examples

```yaml
# Example 1: Lookback processing (scheduled runs)
lookback_period: "P7D"        # Look back 7 days
batch_time_size: "PT12H"      # Process in 12-hour chunks

# Example 2: Historical analysis (specific period)
start_time: "2025-01-01T00:00:00Z"
end_time: "2025-01-31T23:59:59Z"
batch_time_size: "PT6H"       # Process in 6-hour chunks

# Example 3: Incremental processing (continue from last run)
use_last_successful: true     # Start from last completion
batch_time_size: "PT24H"      # Process in daily chunks
health_logging_enabled: true  # Required for tracking
```

### Workspace Parameters

Workspace-specific parameters that can be used in query substitution:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `row_level_security_tag` | string | Data isolation identifier | `"production"`, `"dev"` |
| `environment` | string | Environment designation | `"prod"`, `"staging"`, `"dev"` |
| `region` | string | Geographic region | `"us-east"`, `"eu-west"` |
| `compliance_level` | string | Compliance requirements | `"high"`, `"medium"`, `"basic"` |
| `cost_center` | string | Billing/cost allocation | `"security-ops"`, `"it-dept"` |
| `data_residency` | string | Data location requirements | `"us"`, `"eu"`, `"global"` |

### Query File Schema

Complete schema for query YAML files:

```yaml
# Required fields
name: string                    # Unique query identifier
destination_stream: string      # Target data stream
description: string            # Human-readable description
query: string                  # KQL query with parameter placeholders

# Optional fields
stream_name: string            # Custom stream name (defaults to destination_stream)
version: string               # Query version for tracking
tags: [string]                # Categorization tags

# Parameters schema
parameters:
  parameter_name:
    type: string               # "string", "int", "double", "bool", "datetime"
    required: boolean          # Whether parameter is required
    default: any              # Default value if not provided
    description: string       # Parameter description
```

### Error Handling

The package provides comprehensive error handling with service-specific exceptions:

```python
from sentinel_log_aggregator import (
    SentinelAggregatorError,
    QueryExecutionError, 
    WorkspaceAccessError,
    DataIngestionError,
    ConfigurationError
)

try:
    result = await client.query_workspace(workspace_id, query)
except QueryExecutionError as e:
    print(f"Query failed: {e.message}")
    print(f"Workspace: {e.workspace_id}")
    print(f"Query: {e.query_name}")
except WorkspaceAccessError as e:
    print(f"Access denied to workspace: {e.workspace_id}")
except ConfigurationError as e:
    print(f"Configuration error: {e.message}")
except SentinelAggregatorError as e:
    print(f"General service error: {e.message}")
```

### Response Models

All operations return structured response objects:

```python
# Query result
result = await client.query_workspace(workspace_id, query)
print(f"Success: {result.succeeded}")
print(f"Records: {result.record_count}")
print(f"Duration: {result.execution_time}s")
print(f"Status: {result.status}")

# Upload result  
upload_result = await client.upload_logs(data, stream_name)
print(f"Success: {upload_result.succeeded}")
print(f"Uploaded: {upload_result.record_count}")
print(f"Status: {upload_result.status}")

# Service properties
service_props = await client.get_service_properties()
print(f"Version: {service_props.service_version}")
print(f"Status: {service_props.connectivity_status}")
```

### Authentication

The package supports multiple Azure authentication methods:

#### Managed Identity (Recommended for Azure-hosted)

```python
from azure.identity.aio import DefaultAzureCredential

# Automatic in Azure-hosted environments
credential = DefaultAzureCredential()
```

#### Service Principal (CI/CD scenarios)

```python
from azure.identity.aio import ClientSecretCredential

credential = ClientSecretCredential(
    tenant_id="your-tenant-id",
    client_id="your-client-id", 
    client_secret="your-client-secret"
)
```

#### Azure CLI (Development)

```bash
# Login first
az login

# Then use in code
from azure.identity.aio import AzureCLICredential
credential = AzureCLICredential()
```

### Required Azure Permissions

Your identity needs the following permissions:

- **Log Analytics Reader** on all source Sentinel workspaces
- **Monitoring Metrics Publisher** for the DCR ingestion endpoint
- **Data Collection Rule permissions** configured for your identity

## Development

### Setup Development Environment

```bash
git clone <repository-url>
cd sentinel-log-aggregator
pip install -e ".[dev]"
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sentinel_log_aggregator

# Run specific test file
pytest tests/test_client.py
```

### Code Formatting

```bash
# Format code
black sentinel_log_aggregator tests
isort sentinel_log_aggregator tests

# Lint code
flake8 sentinel_log_aggregator tests
mypy sentinel_log_aggregator
```

## Architecture

### Core Components

- **SentinelAggregatorClient**: Main Azure SDK-compliant client
- **SentinelAggregatorClientOptions**: Configuration management
- **SentinelQueryEngine**: High-level batch processing engine
- **WorkspaceManager**: Multi-workspace configuration and filtering
- **Response Models**: Structured responses for all operations
- **Exception Hierarchy**: Service-specific error handling

### Data Flow

1. **Configuration Loading**: Options loaded from environment/files
2. **Authentication**: Azure Identity credential resolution
3. **Client Creation**: Azure SDK-compliant client initialization
4. **Workspace Discovery**: Load and validate workspace configurations
5. **Batch Processing**: Time-based batching with concurrent execution
6. **Query Execution**: KQL queries across multiple workspaces
7. **Data Transformation**: Normalize and enrich data for reporting
8. **Upload Processing**: Stream data to Azure Monitor ingestion
9. **Progress Tracking**: Comprehensive logging and monitoring

## Documentation

### Available Documentation

- **[Query Setup and Configuration](docs/query-setup.md)**: Comprehensive guide for organizing queries, using relative paths, and advanced query configuration
- **[Installation Guide](docs/installation.md)**: Complete installation instructions and setup
- **[CLI Usage Guide](docs/cli-usage.md)**: Detailed command-line interface documentation
- **[Configuration Guide](docs/configuration.md)**: Advanced configuration options and environment setup
- **[Health Logging Deployment](docs/health-logging-deployment.md)**: Deploy health logging infrastructure using Bicep templates
- **[SDK Usage Guide](docs/sdk-usage.md)**: Programmatic usage examples and API reference
- **[Development Guide](docs/development.md)**: Development setup and contributing guidelines
- **[Security Implementation](docs/security-implementation.md)**: Security features and compliance documentation
- **[GitHub Actions Workflows](docs/workflows.md)**: Comprehensive documentation of CI/CD and security workflows
- **[Troubleshooting Guide](docs/troubleshooting.md)**: Common issues and solutions

### Quick References

- **API Documentation**: Generated from code docstrings (see built documentation)
- **CLI Reference**: `sentinel-aggregator --help` for command-line usage
- **Examples**: See `examples/` for practical implementation examples
- **Changelog**: See `docs/changelog.md` for version history and changes

### Workflow Documentation

The project includes comprehensive GitHub Actions workflows for:

- **CI/CD Pipeline**: Automated testing, building, and deployment (Python 3.11+)
- **Security Scanning**: Microsoft SDL-compliant security analysis with 12+ security tools
- **Documentation Generation**: Automated Sphinx documentation with GitHub Pages deployment
- **Package Distribution**: Automated PyPI publishing and GitHub releases

See [docs/workflows.md](docs/workflows.md) for detailed workflow documentation including job dependencies, troubleshooting, and best practices.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Workflow

Before contributing, please review:
- [GitHub Actions Workflows Documentation](docs/workflows.md) for CI/CD pipeline details
- Pre-commit hooks configuration for local security scanning
- Test coverage requirements (target >95%)
- Security scanning requirements (zero high/critical vulnerabilities)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- Create an issue in the GitHub repository
- Check the documentation and examples
- Review the CLI help: `sentinel-aggregator --help`