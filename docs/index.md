---
title: Microsoft Sentinel Log Aggregator
description: Learn how to use the Microsoft Sentinel Log Aggregator to collect, process, and aggregate logs from multiple Sentinel workspaces.
author: Microsoft
ms.author: sentinel-team
ms.service: sentinel
ms.topic: overview
ms.date: 2025-11-03
---

# Microsoft Sentinel Log Aggregator

The Microsoft Sentinel Log Aggregator is an Azure SDK-compliant Python client library designed to collect, process, and aggregate logs from multiple Microsoft Sentinel workspaces into centralized reporting tables for security analytics and dashboard creation.

## Overview

The Sentinel Log Aggregator provides a comprehensive solution for:

- **Multi-workspace aggregation**: Query and aggregate data across multiple Sentinel workspaces
- **Centralized reporting**: Transform and normalize data for unified analytics
- **Scalable processing**: Batch processing with configurable concurrency and time-based batching
- **Azure integration**: Native Azure authentication and monitoring integration
- **Production-ready**: Comprehensive error handling, logging, and health monitoring
- **Flexible query organization**: Support for custom query directory structures and relative paths

## Key features

- **Azure SDK compliance**: Follows Microsoft Azure SDK design guidelines and patterns
- **Flexible authentication**: Supports managed identity, service principal, and Azure CLI authentication
- **Batch processing**: Configurable time-based batching with concurrent execution
- **Error handling**: Service-specific exceptions with detailed error information
- **Health monitoring**: Built-in health checks and service diagnostics
- **Long-running operations**: LRO support for batch operations with progress tracking
- **Custom query organization**: Organize queries in any directory structure using relative paths

## Quick Navigation

### 🚀 Getting Started
- **[Installation Guide](installation.md)**: Get up and running quickly
- **[Quick Start Examples](examples/basic-examples.md)**: Simple examples to get you started
- **[Configuration Guide](configuration.md)**: Basic to advanced configuration options

### 📋 Query Management ⭐ NEW!
- **[Query Setup and Configuration](query-setup.md)**: Comprehensive guide for organizing and configuring queries
  - Flexible directory structures
  - Relative path configuration  
  - Parameter substitution
  - Advanced query organization

### 💻 Usage Guides
- **[CLI Usage](cli-usage.md)**: Command-line interface documentation
- **[SDK Usage](sdk-usage.md)**: Programmatic usage and API reference
- **[Examples](examples/)**: Practical implementation examples

### 🔧 Advanced Topics
- **[Security Implementation](security-implementation.md)**: Security features and compliance
- **[Development Guide](development.md)**: Development setup and contributing
- **[GitHub Actions Workflows](workflows.md)**: CI/CD and automation
- **[Packaging Guide](packaging.md)**: Package distribution and releases
- **[Troubleshooting](troubleshooting.md)**: Common issues and solutions

### 📚 Reference
- **[API Reference](../README.md#configuration-reference)**: Complete configuration options
- **[Best Practices](best-practices.md)**: Development and deployment guidelines
- **[Changelog](changelog.md)**: Version history and changes
- **[Security Policy](security.md)**: Security reporting and policies

## Architecture

The solution is built on a modular architecture with clear separation of concerns:

```mermaid
graph TB
    A[CLI/SDK Client] --> B[SentinelAggregatorClient]
    B --> C[Authentication Layer]
    B --> D[Query Engine]
    B --> E[Workspace Manager]
    D --> F[Azure Monitor Logs]
    D --> G[Data Processing]
    G --> H[Azure Monitor Ingestion]
    E --> I[Workspace Configuration]
    
    C --> J[Managed Identity]
    C --> K[Service Principal]
    C --> L[Azure CLI]
```

## Getting started

### Prerequisites

- Python 3.11 or later
- Azure subscription with Microsoft Sentinel workspaces
- Appropriate Azure permissions (Microsoft Sentinel Reader, Monitoring Metrics Publisher)

### Installation

Install the package from GitHub:

```bash
# Install from GitHub repository
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git

# Or install from GitHub release
pip install https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/releases/latest/download/sentinel_log_aggregator-0.1.0-py3-none-any.whl
```

### Quick start

```python
import asyncio
from azure.identity.aio import DefaultAzureCredential
from sentinel_log_aggregator import SentinelAggregatorClient, SentinelAggregatorClientOptions

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

asyncio.run(main())
```

## Next steps

- [Installation and setup](installation.md)
- [Configuration guide](configuration.md)
- [CLI usage](cli-usage.md)
- [SDK usage](sdk-usage.md)
- [Examples](examples/basic-examples.md)

## Additional resources

- [Advanced examples](examples/advanced-examples.md)
- [Best practices](best-practices.md)
- [Troubleshooting](troubleshooting.md)
- [API reference](api-reference.md)

```{toctree}
:maxdepth: 2
:caption: Contents:
:hidden:

installation
configuration
query-setup
cli-usage
sdk-usage
security-implementation
development
workflows
packaging
troubleshooting
best-practices
changelog
security
examples/index
api-reference
```
