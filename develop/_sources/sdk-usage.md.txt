---
title: SDK usage
description: Learn how to use the Microsoft Sentinel Log Aggregator SDK for programmatic access and integration.
author: Microsoft
ms.author: sentinel-team
ms.service: sentinel
ms.topic: how-to
ms.date: 2025-11-01
---

# SDK usage

The Microsoft Sentinel Log Aggregator SDK provides a comprehensive, Azure SDK-compliant Python library for programmatic access to log aggregation functionality. This article covers the key components and usage patterns.

## Overview

The SDK follows Azure SDK design patterns and provides:

- **Azure SDK compliance**: Consistent patterns with other Azure SDKs
- **Async/await support**: Full asynchronous operation support
- **Structured responses**: Rich response objects with detailed information
- **Comprehensive error handling**: Service-specific exceptions
- **Long-running operations (LRO)**: Support for batch operations with progress tracking
- **Health monitoring**: Built-in health checks and diagnostics

## Core components

### SentinelAggregatorClient

The main client class providing Azure SDK-compliant operations:

```python
from azure.identity.aio import DefaultAzureCredential
from sentinel_log_aggregator import SentinelAggregatorClient, SentinelAggregatorClientOptions

async def main():
    # Create client options
    options = SentinelAggregatorClientOptions.from_environment()
    
    # Create credential
    credential = DefaultAzureCredential()
    
    # Create client
    async with SentinelAggregatorClient(
        dcr_logs_ingestion_endpoint=options.dcr_logs_ingestion_endpoint,
        credential=credential,
        options=options
    ) as client:
        
        # Use client operations
        service_props = await client.get_service_properties()
        print(f"Service version: {service_props.service_version}")
```

### SentinelAggregatorClientOptions

Configuration management with multiple source support:

```python
from sentinel_log_aggregator import SentinelAggregatorClientOptions

# From environment variables
options = SentinelAggregatorClientOptions.from_environment()

# From YAML file
options = SentinelAggregatorClientOptions.from_yaml_file("config.yaml")

# Programmatic configuration
options = SentinelAggregatorClientOptions(
    dcr_logs_ingestion_endpoint="https://your-dcr.monitor.azure.com",
    dcr_rule_id="dcr-your-rule-id",
    days_ago=30,
    batch_hours=24,
    max_concurrent_queries=5
)

# Validate configuration
options.validate()
```

## Authentication

### Managed Identity (recommended)

```python
from azure.identity.aio import DefaultAzureCredential

# Automatic in Azure environments
credential = DefaultAzureCredential()

async with SentinelAggregatorClient(endpoint, credential, options=options) as client:
    # Operations automatically use managed identity
    pass
```

### Service Principal

```python
from azure.identity.aio import ClientSecretCredential

credential = ClientSecretCredential(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret"
)

async with SentinelAggregatorClient(endpoint, credential, options=options) as client:
    # Operations use service principal
    pass
```

### Azure CLI

```python
from azure.identity.aio import AzureCLICredential

# Requires 'az login' first
credential = AzureCLICredential()

async with SentinelAggregatorClient(endpoint, credential, options=options) as client:
    # Operations use Azure CLI credentials
    pass
```

### Connection string

```python
from sentinel_log_aggregator import SentinelAggregatorClient

# Create client from connection string
client = SentinelAggregatorClient.from_connection_string(
    "endpoint=https://your-dcr.monitor.azure.com;dcr_rule_id=dcr-your-rule-id;timeout=300"
)

async with client:
    # Use client
    pass
```

## Basic operations

### Health checks

```python
async with SentinelAggregatorClient(endpoint, credential, options=options) as client:
    # Get service properties and health status
    service_props = await client.get_service_properties()
    
    print(f"Service version: {service_props.service_version}")
    print(f"Connectivity status: {service_props.connectivity_status}")
    print(f"Endpoint health: {service_props.endpoint_health}")
    
    # Detailed health check
    health_result = await client.check_health()
    print(f"Overall health: {health_result.status}")
    
    for check in health_result.checks:
        print(f"  {check.name}: {check.status} ({check.duration_ms}ms)")
```

### Single workspace queries

```python
async with SentinelAggregatorClient(endpoint, credential, options=options) as client:
    # Execute KQL query against specific workspace
    result = await client.query_workspace(
        workspace_id="workspace-customer-id",
        query="SecurityEvent | where TimeGenerated > ago(1h) | take 100"
    )
    
    if result.succeeded:
        print(f"Query succeeded: {result.record_count} records")
        print(f"Execution time: {result.execution_time} seconds")
        
        # Access data
        for record in result.data:
            print(f"Event: {record}")
    else:
        print(f"Query failed: {result.error_message}")
```

### Data upload

```python
async with SentinelAggregatorClient(endpoint, credential, options=options) as client:
    # Prepare data for upload
    data = [
        {
            "timestamp": "2025-11-01T10:30:00Z",
            "event_type": "security_alert",
            "severity": "high",
            "workspace_id": "prod-east"
        }
    ]
    
    # Upload to custom log table
    upload_result = await client.upload_logs(
        data=data,
        stream_name="Custom-SecurityEvents_CL"
    )
    
    if upload_result.succeeded:
        print(f"Upload succeeded: {upload_result.record_count} records")
        print(f"Upload duration: {upload_result.upload_duration} seconds")
    else:
        print(f"Upload failed: {upload_result.error_message}")
```

### Incremental processing with last successful timestamps

```python
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    load_workspace_config
)

async def incremental_aggregation():
    """
    Run incremental aggregation starting from last successful execution.
    Requires health logging to be enabled to track execution history.
    """
    
    # Configure for incremental processing
    options = SentinelAggregatorClientOptions(
        use_last_successful=True,        # Start from last successful run
        health_to_sentinel=True,         # Required: enables execution tracking
        batch_time_size="PT12H",         # Process in 12-hour batches
        max_concurrent_queries=5,
        dcr_logs_ingestion_endpoint="https://your-dcr.monitor.azure.com",
        dcr_immutable_id="dcr-your-rule-id"
    )
    
    # Load workspaces
    workspaces = load_workspace_config("workspaces.yaml")
    
    async with SentinelAggregatorClient(endpoint, credential, options=options) as client:
        # This will automatically query from the last successful timestamp
        # for each workspace/query combination
        summary = await client.execute_queries(workspaces)
        
        print(f"Incremental aggregation complete:")
        print(f"  Records processed: {summary.total_records_uploaded}")
        print(f"  Duration: {summary.total_duration:.1f}s")
        print(f"  Job ID: {summary.job_correlation_id}")

# Run incremental aggregation
await incremental_aggregation()
```

**How it works:**

1. **First run**: Queries use the configured lookback period (or start_time/end_time)
2. **Subsequent runs**: Queries start from the last successful completion timestamp
3. **Per workspace/query**: Each workspace and query combination tracks its own last successful time
4. **Health logging**: Execution metadata is stored in the health logging table for tracking

**Use cases:**
- **Scheduled aggregation**: Run every hour/day and automatically process only new data
- **Resume after failure**: If a job fails, the next run continues from the last success
- **Efficient processing**: Avoid re-processing historical data on every execution

## Advanced operations

### Batch operations with LRO

```python
from sentinel_log_aggregator import WorkspaceManager

async with SentinelAggregatorClient(endpoint, credential, options=options) as client:
    # Load workspace configuration
    workspace_manager = WorkspaceManager.from_file("workspaces.yaml")
    
    # Start long-running batch operation
    poller = await client.begin_batch_operation(
        workspaces=workspace_manager.workspaces,
        queries=["query_incident_summary", "query_user_summary"],
        time_range_days=7
    )
    
    print(f"Batch operation started: {poller.get_status()}")
    
    # Monitor progress
    while not poller.done():
        try:
            # Wait with timeout
            result = await poller.result(timeout=30)
            print(f"Progress: {result.completed_operations}/{result.total_operations}")
            
            # Optional: process partial results
            if result.partial_results:
                for partial in result.partial_results:
                    print(f"Completed: {partial.workspace_id} - {partial.query}")
                    
        except asyncio.TimeoutError:
            print("Still running...")
    
    # Get final result
    final_result = await poller.result()
    print(f"Batch completed: {final_result.success_count} successful, {final_result.error_count} failed")
    
    # Process results
    for execution in final_result.executions:
        if execution.succeeded:
            print(f"Success: {execution.workspace_id} - {execution.query} ({execution.record_count} records)")
        else:
            print(f"Failed: {execution.workspace_id} - {execution.query}: {execution.error_message}")
```

### Workspace management

```python
from sentinel_log_aggregator import WorkspaceManager, WorkspaceConfig

# Create workspace configurations
workspaces = [
    WorkspaceConfig(
        resource_id="/subscriptions/sub-id/resourcegroups/rg/providers/microsoft.operationalinsights/workspaces/ws1",
        customer_id="workspace-id-1",
        parameters={"row_level_security_tag": "prod"},
        queries_list=["query_incident_summary", "query_user_summary"]
    ),
    WorkspaceConfig(
        resource_id="/subscriptions/sub-id/resourcegroups/rg/providers/microsoft.operationalinsights/workspaces/ws2",
        customer_id="workspace-id-2",
        parameters={"row_level_security_tag": "dev"},
        queries_list=["query_incident_summary"]
    )
]

# Create workspace manager
workspace_manager = WorkspaceManager(workspaces)

# Filtering operations
prod_workspaces = workspace_manager.for_parameter("row_level_security_tag", "prod")
incident_workspaces = workspace_manager.for_query("query_incident_summary")

print(f"Production workspaces: {prod_workspaces.count()}")
print(f"Workspaces with incident queries: {incident_workspaces.count()}")

# Validation
errors = workspace_manager.validate_configuration()
if errors:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")

# Display summary
workspace_manager.display_summary()
```

### High-level query engine

```python
from sentinel_log_aggregator import SentinelQueryEngine

async with SentinelAggregatorClient(endpoint, credential, options=options) as client:
    # Create query engine
    engine = SentinelQueryEngine(options, client)
    
    # Execute batch queries with streaming upload
    summary = await engine.execute_batch_queries_with_streaming_upload(
        workspaces=workspace_manager.workspaces,
        query_names=["query_incident_summary", "query_user_summary"],
        days_back=7,
        batch_hours=12
    )
    
    print(f"Batch execution summary:")
    print(f"  Total queries: {summary.total_queries}")
    print(f"  Successful: {summary.successful_queries}")
    print(f"  Failed: {summary.failed_queries}")
    print(f"  Total records: {summary.total_records_processed}")
    print(f"  Duration: {summary.total_duration} seconds")
    
    # Detailed results
    for execution in summary.query_executions:
        status = "✓" if execution.succeeded else "✗"
        print(f"  {status} {execution.workspace_alias} - {execution.query_name}: {execution.record_count} records")
```

## Response models

### QueryResult

```python
result = await client.query_workspace(workspace_id, query)

# Access response properties
print(f"Succeeded: {result.succeeded}")
print(f"Status: {result.status}")  # QueryStatus enum
print(f"Record count: {result.record_count}")
print(f"Execution time: {result.execution_time}")
print(f"Workspace ID: {result.workspace_id}")
print(f"Query: {result.query}")

# Access data
if result.succeeded:
    for record in result.data:
        # Process record dictionary
        pass

# Error handling
if not result.succeeded:
    print(f"Error: {result.error_message}")
    print(f"Error code: {result.error_code}")
```

### UploadResult

```python
upload_result = await client.upload_logs(data, stream_name)

# Access response properties
print(f"Succeeded: {upload_result.succeeded}")
print(f"Status: {upload_result.status}")  # UploadStatus enum
print(f"Record count: {upload_result.record_count}")
print(f"Upload duration: {upload_result.upload_duration}")
print(f"Stream name: {upload_result.stream_name}")

# Error handling
if not upload_result.succeeded:
    print(f"Error: {upload_result.error_message}")
    print(f"Error code: {upload_result.error_code}")
```

### BatchExecutionResult

```python
batch_result = await poller.result()

# Access summary
print(f"Status: {batch_result.status}")  # BatchStatus enum
print(f"Total operations: {batch_result.total_operations}")
print(f"Completed: {batch_result.completed_operations}")
print(f"Successful: {batch_result.success_count}")
print(f"Failed: {batch_result.error_count}")

# Access individual executions
for execution in batch_result.executions:
    print(f"Workspace: {execution.workspace_id}")
    print(f"Query: {execution.query}")
    print(f"Status: {execution.status}")
    print(f"Records: {execution.record_count}")
    print(f"Duration: {execution.execution_time}")
```

### ServiceProperties

```python
service_props = await client.get_service_properties()

# Access properties
print(f"Service version: {service_props.service_version}")
print(f"Connectivity status: {service_props.connectivity_status}")
print(f"Endpoint health: {service_props.endpoint_health}")
print(f"Authentication status: {service_props.authentication_status}")
print(f"Last health check: {service_props.last_health_check}")

# Feature capabilities
print(f"Supports batch operations: {service_props.supports_batch_operations}")
print(f"Supports streaming: {service_props.supports_streaming}")
print(f"Max concurrent queries: {service_props.max_concurrent_queries}")
```

## Error handling

### Exception hierarchy

```python
from sentinel_log_aggregator import (
    SentinelAggregatorError,
    QueryExecutionError,
    WorkspaceAccessError,
    DataIngestionError,
    ConfigurationError,
    BatchOperationError
)

try:
    result = await client.query_workspace(workspace_id, query)
    
except QueryExecutionError as e:
    print(f"Query execution failed: {e.message}")
    print(f"Workspace: {e.workspace_id}")
    print(f"Query: {e.query_name}")
    print(f"Error code: {e.error_code}")
    
except WorkspaceAccessError as e:
    print(f"Access denied to workspace: {e.workspace_id}")
    print(f"Required permissions: {e.required_permissions}")
    
except DataIngestionError as e:
    print(f"Data ingestion failed: {e.message}")
    print(f"Stream name: {e.stream_name}")
    print(f"Record count: {e.record_count}")
    
except ConfigurationError as e:
    print(f"Configuration error: {e.message}")
    print(f"Configuration source: {e.source}")
    
except SentinelAggregatorError as e:
    # Base exception for all service errors
    print(f"Service error: {e.message}")
    print(f"Correlation ID: {e.correlation_id}")
    print(f"Timestamp: {e.timestamp}")
    
except Exception as e:
    # Handle other exceptions
    print(f"Unexpected error: {e}")
```

### Error context information

```python
try:
    result = await client.query_workspace(workspace_id, query)
except QueryExecutionError as e:
    # Rich error context
    print(f"Error details:")
    print(f"  Message: {e.message}")
    print(f"  Error code: {e.error_code}")
    print(f"  Workspace ID: {e.workspace_id}")
    print(f"  Query name: {e.query_name}")
    print(f"  Correlation ID: {e.correlation_id}")
    print(f"  Timestamp: {e.timestamp}")
    print(f"  Inner error: {e.inner_error}")
    
    # Additional context if available
    if hasattr(e, 'query_text'):
        print(f"  Query text: {e.query_text}")
    if hasattr(e, 'execution_time'):
        print(f"  Execution time: {e.execution_time}")
```

## Advanced patterns

### Retry and resilience

```python
import asyncio
from azure.core.exceptions import ClientResponseError

async def resilient_query(client, workspace_id, query, max_retries=3):
    """Execute query with custom retry logic."""
    
    for attempt in range(max_retries):
        try:
            result = await client.query_workspace(workspace_id, query)
            return result
            
        except ClientResponseError as e:
            if e.status_code == 429:  # Rate limited
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                await asyncio.sleep(wait_time)
                continue
            else:
                raise  # Re-raise non-retryable errors
                
        except QueryExecutionError as e:
            if "timeout" in e.message.lower():
                print(f"Query timeout on attempt {attempt + 1}, retrying...")
                continue
            else:
                raise  # Re-raise non-retryable query errors
    
    raise Exception(f"Failed after {max_retries} attempts")

# Usage
result = await resilient_query(client, workspace_id, complex_query)
```

### Parallel processing

```python
import asyncio
from typing import List

async def parallel_workspace_queries(client, workspaces: List[WorkspaceConfig], query: str):
    """Execute query across multiple workspaces in parallel."""
    
    async def query_workspace(workspace):
        try:
            result = await client.query_workspace(workspace.customer_id, query)
            return {
                'workspace': workspace,
                'result': result,
                'error': None
            }
        except Exception as e:
            return {
                'workspace': workspace,
                'result': None,
                'error': str(e)
            }
    
    # Execute queries in parallel with semaphore for concurrency control
    semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent queries
    
    async def limited_query(workspace):
        async with semaphore:
            return await query_workspace(workspace)
    
    # Execute all queries
    tasks = [limited_query(workspace) for workspace in workspaces]
    results = await asyncio.gather(*tasks)
    
    # Process results
    successful = [r for r in results if r['error'] is None]
    failed = [r for r in results if r['error'] is not None]
    
    print(f"Parallel query completed: {len(successful)} successful, {len(failed)} failed")
    return results

# Usage
workspaces = workspace_manager.workspaces
results = await parallel_workspace_queries(client, workspaces, "SecurityEvent | take 10")
```

### Custom data transformations

```python
from typing import Dict, List, Any
import pandas as pd

async def query_and_transform(client, workspace_id: str, query: str, transform_func=None):
    """Execute query and apply custom transformations."""
    
    result = await client.query_workspace(workspace_id, query)
    
    if not result.succeeded:
        raise QueryExecutionError(f"Query failed: {result.error_message}")
    
    # Apply transformation if provided
    if transform_func:
        transformed_data = transform_func(result.data)
        return {
            'original_count': result.record_count,
            'transformed_count': len(transformed_data),
            'data': transformed_data,
            'metadata': {
                'workspace_id': workspace_id,
                'execution_time': result.execution_time,
                'query': query
            }
        }
    
    return result.data

# Example transformation functions
def normalize_security_events(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize security event data."""
    normalized = []
    
    for record in data:
        normalized_record = {
            'timestamp': record.get('TimeGenerated'),
            'event_id': record.get('EventID'),
            'computer': record.get('Computer'),
            'account': record.get('Account'),
            'severity': determine_severity(record),
            'source_workspace': record.get('workspace_id', 'unknown')
        }
        normalized.append(normalized_record)
    
    return normalized

def determine_severity(record: Dict[str, Any]) -> str:
    """Determine event severity based on event ID and other factors."""
    event_id = record.get('EventID', 0)
    
    if event_id in [4625, 4648]:  # Failed logons
        return 'medium'
    elif event_id in [4720, 4726]:  # Account management
        return 'high'
    else:
        return 'low'

# Usage
transformed_data = await query_and_transform(
    client, 
    workspace_id, 
    "SecurityEvent | where TimeGenerated > ago(1h)",
    transform_func=normalize_security_events
)

print(f"Transformed {transformed_data['original_count']} records to {transformed_data['transformed_count']}")
```

### Integration with pandas

```python
import pandas as pd

async def query_to_dataframe(client, workspace_id: str, query: str) -> pd.DataFrame:
    """Execute query and return results as pandas DataFrame."""
    
    result = await client.query_workspace(workspace_id, query)
    
    if not result.succeeded:
        raise QueryExecutionError(f"Query failed: {result.error_message}")
    
    # Convert to DataFrame
    df = pd.DataFrame(result.data)
    
    # Add metadata columns
    df['source_workspace'] = workspace_id
    df['query_execution_time'] = result.execution_time
    df['query_timestamp'] = pd.Timestamp.now()
    
    return df

async def aggregate_across_workspaces(client, workspaces: List[WorkspaceConfig], query: str) -> pd.DataFrame:
    """Execute query across multiple workspaces and combine results."""
    
    dataframes = []
    
    for workspace in workspaces:
        try:
            df = await query_to_dataframe(client, workspace.customer_id, query)
            # Add workspace metadata
            df['workspace_alias'] = workspace.parameters.get('row_level_security_tag', 'unknown')
            df['workspace_resource_id'] = workspace.resource_id
            dataframes.append(df)
            
        except Exception as e:
            print(f"Failed to query workspace {workspace.customer_id}: {e}")
    
    # Combine all dataframes
    if dataframes:
        combined_df = pd.concat(dataframes, ignore_index=True)
        return combined_df
    else:
        return pd.DataFrame()

# Usage
combined_data = await aggregate_across_workspaces(
    client, 
    workspace_manager.workspaces,
    "SecurityEvent | where TimeGenerated > ago(1h) | summarize count() by Computer, EventID"
)

print(f"Combined data shape: {combined_data.shape}")
print(combined_data.groupby('workspace_alias')['Computer'].count())
```

## Best practices

### Resource management

```python
# Always use async context manager
async with SentinelAggregatorClient(endpoint, credential, options=options) as client:
    # Client is automatically closed on exit
    pass

# For long-running applications, consider connection pooling
class ConnectionManager:
    def __init__(self, endpoint, credential, options):
        self.endpoint = endpoint
        self.credential = credential
        self.options = options
        self._client = None
    
    async def get_client(self):
        if self._client is None:
            self._client = SentinelAggregatorClient(
                self.endpoint, self.credential, options=self.options
            )
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.close()
```

### Configuration validation

```python
# Always validate configuration before use
def validate_environment():
    try:
        options = SentinelAggregatorClientOptions.from_environment()
        options.validate()
        print("Configuration is valid")
        return options
    except ConfigurationError as e:
        print(f"Configuration error: {e.message}")
        raise

# Use configuration validation in initialization
options = validate_environment()
```

### Monitoring and observability

```python
import logging
from sentinel_log_aggregator.logging_utils import configure_logging

# Configure structured logging
configure_logging(
    level=logging.INFO,
    format_type="json",
    enable_correlation_ids=True
)

# Use correlation IDs for tracking
import uuid

correlation_id = str(uuid.uuid4())
logger = logging.getLogger(__name__)

async def tracked_operation(client, workspace_id, query):
    logger.info(
        "Starting query execution",
        extra={
            "correlation_id": correlation_id,
            "workspace_id": workspace_id,
            "query": query
        }
    )
    
    try:
        result = await client.query_workspace(workspace_id, query)
        
        logger.info(
            "Query execution completed",
            extra={
                "correlation_id": correlation_id,
                "success": result.succeeded,
                "record_count": result.record_count,
                "execution_time": result.execution_time
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Query execution failed",
            extra={
                "correlation_id": correlation_id,
                "error": str(e),
                "error_type": type(e).__name__
            }
        )
        raise
```

## Next steps

- [Basic examples](examples/basic-examples.md)
- [Advanced examples](examples/advanced-examples.md)
- [Best practices](best-practices.md)
- [API reference](api-reference.md)
