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

```bash
pip install sentinel-log-aggregator
```

## Quick Start

### Basic Usage

```python
import asyncio
from azure.identity.aio import DefaultAzureCredential
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    WorkspaceConfig
)

async def main():
    # Create client options from environment
    options = SentinelAggregatorClientOptions.from_environment()
    
    # Create credential and client
    credential = DefaultAzureCredential()
    
    async with SentinelAggregatorClient(
        dcr_logs_ingestion_endpoint=options.dcr_logs_ingestion_endpoint,
        credential=credential,
        options=options
    ) as client:
        
        # Health check
        service_props = await client.get_service_properties()
        print(f"Service status: {service_props.connectivity_status}")
        
        # Query workspace
        result = await client.query_workspace(
            workspace_id="your-workspace-customer-id",
            query="SecurityEvent | take 10"
        )
        
        if result.succeeded:
            print(f"Retrieved {result.record_count} records")
            
            # Upload results
            upload_result = await client.upload_logs(
                data=result.data,
                stream_name="Custom-SecurityEvents_CL"
            )
            
            if upload_result.succeeded:
                print(f"Uploaded {upload_result.record_count} records")

# Run it
asyncio.run(main())
```

### Connection String Usage

```python
from sentinel_log_aggregator import SentinelAggregatorClient

# Create client from connection string
client = SentinelAggregatorClient.from_connection_string(
    "endpoint=https://your-dcr.monitor.azure.com;dcr_rule_id=dcr-your-rule-id"
)
```

### Batch Operations with LRO

```python
async with SentinelAggregatorClient(endpoint, credential, options=options) as client:
    # Start long-running batch operation
    poller = await client.begin_batch_operation(
        workspaces=workspace_configs,
        queries=["query_incident_summary", "query_user_summary"]
    )
    
    # Monitor progress
    while not poller.done():
        result = poller.result(timeout=30)
        print(f"Progress: {result.completed_operations}/{result.total_operations}")
    
    # Get final result
    final_result = await poller.result()
    print(f"Batch completed: {final_result.success_count} successful")
```

## Configuration

### Environment Variables

```bash
# Required settings
DCR_LOGS_INGESTION_ENDPOINT=https://your-dcr-endpoint.monitor.azure.com
DCR_RULE_ID=dcr-your-rule-id

# Optional settings
DAYS_AGO=30
BATCH_HOURS=24
MAX_CONCURRENT_QUERIES=5
QUERY_TIMEOUT_SECONDS=300
LOG_LEVEL=INFO

# Authentication (use one method)
# Managed Identity (recommended for Azure-hosted)
# - No configuration needed

# Service Principal
AZURE_CLIENT_ID=your-client-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_SECRET=your-client-secret

# Azure CLI (for development)
# - Run 'az login' first
```

### YAML Configuration

```yaml
dcr_logs_ingestion_endpoint: "https://your-endpoint.monitor.azure.com"
dcr_rule_id: "dcr-your-rule-id"
days_ago: 30
batch_hours: 24
max_concurrent_queries: 5
log_level: "INFO"
```

### Workspace Configuration

Create a `workspaces.yaml` file (YAML format recommended):

```yaml
# Microsoft Sentinel Workspaces Configuration
workspaces:
  - # Production Sentinel Workspace
    resource_id: "/subscriptions/your-sub-id/resourcegroups/your-rg/providers/microsoft.operationalinsights/workspaces/prod-sentinel"
    customer_id: "your-workspace-customer-id"
    row_level_security_tag: "prod"
    reports_list:
      - "report_incident_summary"
      - "report_user_summary"
    
  - # Development Sentinel Workspace
    resource_id: "/subscriptions/your-sub-id/resourcegroups/your-rg/providers/microsoft.operationalinsights/workspaces/dev-sentinel"
    customer_id: "another-workspace-customer-id"
    row_level_security_tag: "dev"
    reports_list:
      - "report_incident_summary"

# Configuration metadata (optional)
metadata:
  version: "1.0"
  description: "Microsoft Sentinel workspaces configuration for log aggregation"
  last_updated: "2025-10-31"
```

## CLI Usage

The package includes a command-line interface for automation and manual execution:

### Health Check

```bash
# Check service health and connectivity
sentinel-aggregator health --workspace-config workspaces.yaml
```

### Run Aggregation

```bash
# Run with default settings
sentinel-aggregator run --workspace-config workspaces.yaml

# Run with custom time range
sentinel-aggregator run --workspace-config workspaces.yaml --days-back 7 --batch-hours 12

# Run with debug logging
sentinel-aggregator --log-level DEBUG run --workspace-config workspaces.yaml
```

### Validate Configuration

```bash
# Validate configuration files
sentinel-aggregator validate --workspace-config workspaces.yaml
```

## Error Handling

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

## Response Models

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

## Authentication

The package supports multiple Azure authentication methods:

### Managed Identity (Recommended for Azure-hosted)

```python
from azure.identity.aio import DefaultAzureCredential

# Automatic in Azure-hosted environments
credential = DefaultAzureCredential()
```

### Service Principal (CI/CD scenarios)

```python
from azure.identity.aio import ClientSecretCredential

credential = ClientSecretCredential(
    tenant_id="your-tenant-id",
    client_id="your-client-id", 
    client_secret="your-client-secret"
)
```

### Azure CLI (Development)

```bash
# Login first
az login

# Then use in code
from azure.identity.aio import AzureCLICredential
credential = AzureCLICredential()
```

## Required Azure Permissions

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

- **[Installation Guide](docs/installation.md)**: Complete installation instructions and setup
- **[Packaging Guide](docs/packaging.md)**: Guide for package distribution and development
- **[GitHub Actions Workflows](docs/workflows.md)**: Comprehensive documentation of CI/CD and security workflows
- **API Documentation**: Generated from code docstrings (see built documentation)
- **CLI Reference**: `sentinel-aggregator --help` for command-line usage

### Workflow Documentation

The project includes comprehensive GitHub Actions workflows for:

- **CI/CD Pipeline**: Automated testing, building, and deployment across multiple Python versions
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