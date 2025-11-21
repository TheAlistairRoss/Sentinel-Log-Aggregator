---
title: Installation and setup
description: Learn how to install and set up the Microsoft Sentinel Log Aggregator in your environment.
author: Alistair Ross
ms.author: community
ms.service: sentinel
ms.topic: how-to
ms.date: 2025-11-21
---

# Installation and setup

> **📝 Documentation Status**: This documentation is being actively developed. Some sections may be incomplete.

This article explains how to install and set up the Microsoft Sentinel Log Aggregator in your environment.

**Note**: This is a community-maintained open-source project provided under the MIT License.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.11 or later**: The library requires Python 3.11+
- **Azure subscription**: With access to Microsoft Sentinel workspaces
- **Required permissions**: See [Azure permissions](#azure-permissions)

## Installation methods

### Install from GitHub (recommended)

Install the latest stable version from GitHub:

```bash
# Install from latest release
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git

# Install from specific version tag
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git@v0.1.0
```

### Install from GitHub Release Packages

Install directly from release artifacts:

```bash
# Install wheel package from releases
pip install https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/releases/latest/download/sentinel_log_aggregator-0.1.0-py3-none-any.whl

# Install source distribution from releases  
pip install https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/releases/download/v0.1.0/sentinel-log-aggregator-0.1.0.tar.gz
```

### Install development version

For the latest development features:

```bash
# Install from develop branch
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git@develop
```

### Install with development dependencies

For development and testing:

```bash
# Clone repository and install in editable mode
git clone https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git
cd Sentinel-Log-Aggregator
pip install -e ".[dev]"
```

## Environment setup

### Virtual environment (recommended)

Create an isolated Python environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install the package from GitHub
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git
```

### Dependencies

The package automatically installs required dependencies:

- `azure-identity`: Azure authentication
- `azure-monitor-query`: Azure Monitor Logs querying
- `azure-monitor-ingestion`: Data ingestion to Azure Monitor
- `azure-core`: Azure SDK core functionality
- `pydantic`: Data validation and settings management
- `pyyaml`: YAML configuration file support
- `python-dotenv`: Environment variable management

## Azure permissions

Your identity (user, service principal, or managed identity) requires the following permissions:

### Microsoft Sentinel Reader

Grant **Microsoft Sentinel Reader** role on all source Sentinel workspaces:

```bash
# Using Azure CLI
az role assignment create \
  --assignee <your-principal-id> \
  --role "Microsoft Sentinel Reader" \
  --scope "/subscriptions/<subscription-id>/resourcegroups/<resource-group>/providers/microsoft.operationalinsights/workspaces/<workspace-name>"
```

### Monitoring Metrics Publisher

Grant **Monitoring Metrics Publisher** role for data ingestion:

```bash
# Using Azure CLI
az role assignment create \
  --assignee <your-principal-id> \
  --role "Monitoring Metrics Publisher" \
  --scope "/subscriptions/<subscription-id>/resourcegroups/<resource-group>/providers/microsoft.insights/datacollectionrules/<dcr-name>"
```

### Data Collection Rule permissions

Ensure your identity has permissions on the Data Collection Rule (DCR):

1. Navigate to your DCR in the Azure portal
2. Select **Access control (IAM)**
3. Add role assignment: **Monitoring Metrics Publisher**

## Configuration

### Environment variables

Create a `.env` file in your project directory:

```bash
# Required settings
DCR_LOGS_INGESTION_ENDPOINT=https://your-dcr-endpoint.monitor.azure.com
DCR_RULE_ID=dcr-your-rule-id

# Optional settings
LOOKBACK_PERIOD=P30D
BATCH_TIME_SIZE=PT24H
MAX_CONCURRENT_QUERIES=5
QUERY_TIMEOUT_SECONDS=300
MAX_RETRIES=3
RETRY_DELAY_SECONDS=5
LOG_LEVEL=INFO

# Authentication (choose one method)
# For service principal:
AZURE_CLIENT_ID=your-client-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_SECRET=your-client-secret
```

### Workspace configuration

Create a `workspaces.yaml` file:

```yaml
# Microsoft Sentinel Workspaces Configuration
workspaces:
  - resource_id: "/subscriptions/your-sub-id/resourcegroups/your-rg/providers/microsoft.operationalinsights/workspaces/prod-sentinel"
    customer_id: "your-workspace-customer-id"
    parameters:
      row_level_security_tag: "prod"
    queries_list:
      - "query_incident_summary"
      - "query_user_summary"
  
  - resource_id: "/subscriptions/your-sub-id/resourcegroups/your-rg/providers/microsoft.operationalinsights/workspaces/dev-sentinel"
    customer_id: "another-workspace-customer-id"
    parameters:
      row_level_security_tag: "dev"
    queries_list:
      - "query_incident_summary"

metadata:
  version: "1.0"
  description: "Microsoft Sentinel workspaces configuration"
  last_updated: "2025-11-01"
```

## Authentication setup

### Managed Identity (recommended for Azure-hosted)

For Azure-hosted applications (Azure Functions, Logic Apps, VMs):

```python
from azure.identity.aio import DefaultAzureCredential

# No configuration needed - automatic in Azure environments
credential = DefaultAzureCredential()
```

### Service Principal (CI/CD and automation)

For automated scenarios:

```python
from azure.identity.aio import ClientSecretCredential

credential = ClientSecretCredential(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret"
)
```

### Azure CLI (development)

For local development:

```bash
# Login first
az login

# Then use in code
from azure.identity.aio import AzureCLICredential
credential = AzureCLICredential()
```

## Verification

### Test installation

Verify the installation works:

```python
from sentinel_log_aggregator import __version__, SentinelAggregatorClient
print(f"Sentinel Log Aggregator version: {__version__}")
```

### Test configuration

Validate your configuration:

```bash
# Using CLI
sentinel-aggregator validate --workspace-config workspaces.yaml

# Or using Python
python -c "
from sentinel_log_aggregator import SentinelAggregatorClientOptions
options = SentinelAggregatorClientOptions.from_environment()
print('Configuration loaded successfully')
"
```

### Test connectivity

Perform a health check:

```bash
sentinel-aggregator health --workspace-config workspaces.yaml
```

## Development setup

### Pre-commit hooks

For contributors, set up pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
```

### Testing

Run tests to verify everything works:

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=sentinel_log_aggregator
```

## Common issues

### Import errors

If you encounter import errors:

```bash
# Ensure you're in the correct virtual environment
pip list | grep sentinel-log-aggregator

# Reinstall if necessary
pip uninstall sentinel-log-aggregator
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git
```

### Permission errors

If you get authentication/permission errors:

1. Verify your Azure permissions
2. Check your credential configuration
3. Test with Azure CLI: `az account show`

### Configuration errors

If configuration validation fails:

1. Check your `.env` file format
2. Verify workspace configuration YAML syntax
3. Ensure all required fields are present

## Next steps

- [Configuration guide](configuration.md)
- [CLI usage](cli-usage.md)
- [SDK usage](sdk-usage.md)
- [Basic examples](examples/basic-examples.md)
