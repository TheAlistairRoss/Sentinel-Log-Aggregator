---
title: Basic examples
description: Learn the fundamentals of the Microsoft Sentinel Log Aggregator with practical, step-by-step examples.
author: Microsoft
ms.author: sentinel-team
ms.service: sentinel
ms.topic: tutorial
ms.date: 2025-11-01
---

# Basic examples

This article provides practical, step-by-step examples to help you get started with the Microsoft Sentinel Log Aggregator. These examples cover the most common scenarios and usage patterns.

## Prerequisites

Before running these examples, ensure you have:

- Installed the package: `pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git`
- Configured your environment variables or configuration files
- Set up appropriate Azure permissions
- Access to one or more Microsoft Sentinel workspaces

## Example 1: Basic health check

Verify connectivity and service health before performing operations.

### CLI approach

```powershell
# Create workspace configuration file
@'
workspaces:
  - resource_id: "/subscriptions/your-sub-id/resourcegroups/your-rg/providers/microsoft.operationalinsights/workspaces/your-workspace"
    customer_id: "your-workspace-customer-id"
    parameters:
      row_level_security_tag: "production"
    queries_list:
      - "query_incident_summary"
'@ | Out-File -FilePath workspaces.yaml -Encoding UTF8

# Run health check
sentinel-aggregator health --workspace-config workspaces.yaml
```

### SDK approach

```python
import asyncio
from azure.identity.aio import DefaultAzureCredential
from sentinel_log_aggregator import SentinelAggregatorClient, SentinelAggregatorClientOptions

async def health_check():
    """Perform basic health check."""
    
    # Load configuration from environment
    options = SentinelAggregatorClientOptions.from_environment()
    credential = DefaultAzureCredential()
    
    async with SentinelAggregatorClient(
        dcr_logs_ingestion_endpoint=options.dcr_logs_ingestion_endpoint,
        credential=credential,
        options=options
    ) as client:
        
        # Check service properties
        service_props = await client.get_service_properties()
        print(f"Service version: {service_props.service_version}")
        print(f"Connectivity status: {service_props.connectivity_status}")
        
        # Detailed health check
        health_result = await client.check_health()
        print(f"Overall health: {health_result.status}")
        
        for check in health_result.checks:
            print(f"  ✓ {check.name}: {check.status} ({check.duration_ms}ms)")

# Run the example
asyncio.run(health_check())
```

## Example 2: Simple workspace query

Execute a basic KQL query against a single workspace.

### Environment setup

```powershell
# .env file
@'
DCR_LOGS_INGESTION_ENDPOINT=https://your-dcr-endpoint.monitor.azure.com
DCR_RULE_ID=dcr-your-rule-id
DAYS_AGO=7
LOG_LEVEL=INFO
'@ | Out-File -FilePath .env -Encoding UTF8
```

### SDK implementation

```python
import asyncio
from azure.identity.aio import DefaultAzureCredential
from sentinel_log_aggregator import (
    SentinelAggregatorClient, 
    SentinelAggregatorClientOptions,
    QueryExecutionError
)

async def simple_query():
    """Execute a simple query against a Sentinel workspace."""
    
    options = SentinelAggregatorClientOptions.from_environment()
    credential = DefaultAzureCredential()
    
    async with SentinelAggregatorClient(
        dcr_logs_ingestion_endpoint=options.dcr_logs_ingestion_endpoint,
        credential=credential,
        options=options
    ) as client:
        
        # Define workspace and query
        workspace_id = "your-workspace-customer-id"
        query = """
        SecurityEvent
        | where TimeGenerated > ago(24h)
        | where EventID in (4624, 4625)  // Successful and failed logons
        | summarize 
            SuccessfulLogons = countif(EventID == 4624),
            FailedLogons = countif(EventID == 4625)
            by Computer
        | order by FailedLogons desc
        | take 10
        """
        
        try:
            result = await client.query_workspace(workspace_id, query)
            
            if result.succeeded:
                print(f"Query executed successfully!")
                print(f"Records returned: {result.record_count}")
                print(f"Execution time: {result.execution_time:.2f} seconds")
                
                # Display results
                print("\nLogon Summary by Computer:")
                for record in result.data:
                    computer = record.get('Computer', 'Unknown')
                    successful = record.get('SuccessfulLogons', 0)
                    failed = record.get('FailedLogons', 0)
                    print(f"  {computer}: {successful} successful, {failed} failed")
            
            else:
                print(f"Query failed: {result.error_message}")
        
        except QueryExecutionError as e:
            print(f"Query execution error: {e.message}")
            print(f"Workspace: {e.workspace_id}")

asyncio.run(simple_query())
```

## Example 3: Multi-workspace aggregation

Query multiple workspaces and aggregate the results.

### Workspace configuration

```yaml
# workspaces.yaml
workspaces:
  - resource_id: "/subscriptions/sub-id/resourcegroups/rg/providers/microsoft.operationalinsights/workspaces/prod-east"
    customer_id: "prod-east-workspace-id"
    parameters:
      row_level_security_tag: "prod-east"
      region: "eastus"
    queries_list:
      - "query_incident_summary"
  
  - resource_id: "/subscriptions/sub-id/resourcegroups/rg/providers/microsoft.operationalinsights/workspaces/prod-west"
    customer_id: "prod-west-workspace-id"
    parameters:
      row_level_security_tag: "prod-west"
      region: "westus"
    queries_list:
      - "query_incident_summary"
  
  - resource_id: "/subscriptions/sub-id/resourcegroups/rg/providers/microsoft.operationalinsights/workspaces/dev"
    customer_id: "dev-workspace-id"
    parameters:
      row_level_security_tag: "dev"
      region: "eastus"
    queries_list:
      - "query_incident_summary"

metadata:
  version: "1.0"
  description: "Multi-region Sentinel workspaces"
```

### CLI approach

```powershell
# Run aggregation across all workspaces
sentinel-aggregator run --workspace-config workspaces.yaml --days-back 7

# Run for specific workspaces only
sentinel-aggregator run `
  --workspace-config workspaces.yaml `
  --workspaces "prod-east,prod-west" `
  --days-back 3

# Dry run to validate configuration
sentinel-aggregator run `
  --workspace-config workspaces.yaml `
  --dry-run
```

### SDK implementation

```python
import asyncio
from azure.identity.aio import DefaultAzureCredential
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    WorkspaceManager
)

async def multi_workspace_aggregation():
    """Query multiple workspaces and aggregate results."""
    
    options = SentinelAggregatorClientOptions.from_environment()
    credential = DefaultAzureCredential()
    
    async with SentinelAggregatorClient(
        dcr_logs_ingestion_endpoint=options.dcr_logs_ingestion_endpoint,
        credential=credential,
        options=options
    ) as client:
        
        # Load workspace configuration
        workspace_manager = WorkspaceManager.from_file("workspaces.yaml")
        
        # Validate configuration
        errors = workspace_manager.validate_configuration()
        if errors:
            print("Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            return
        
        print(f"Loaded {workspace_manager.count()} workspaces")
        
        # Define query for incident summary
        incident_query = """
        SecurityIncident
        | where TimeGenerated > ago(7d)
        | where Status != "Closed"
        | summarize
            TotalIncidents = count(),
            HighSeverityIncidents = countif(Severity == "High"),
            MediumSeverityIncidents = countif(Severity == "Medium"),
            LowSeverityIncidents = countif(Severity == "Low")
        | extend WorkspaceRegion = "{region}"
        """
        
        # Execute queries across all workspaces
        all_results = []
        
        for workspace in workspace_manager.workspaces:
            try:
                # Customize query with workspace-specific parameters
                workspace_query = incident_query.format(
                    region=workspace.parameters.get('region', 'unknown')
                )
                
                result = await client.query_workspace(workspace.customer_id, workspace_query)
                
                if result.succeeded:
                    # Add workspace metadata to results
                    for record in result.data:
                        record['workspace_id'] = workspace.customer_id
                        record['workspace_alias'] = workspace.parameters.get('row_level_security_tag')
                        record['source_region'] = workspace.parameters.get('region')
                    
                    all_results.extend(result.data)
                    print(f"✓ {workspace.parameters.get('row_level_security_tag')}: {result.record_count} records")
                
                else:
                    print(f"✗ {workspace.parameters.get('row_level_security_tag')}: {result.error_message}")
            
            except Exception as e:
                print(f"✗ {workspace.parameters.get('row_level_security_tag')}: {str(e)}")
        
        # Aggregate results
        if all_results:
            total_incidents = sum(record.get('TotalIncidents', 0) for record in all_results)
            total_high = sum(record.get('HighSeverityIncidents', 0) for record in all_results)
            total_medium = sum(record.get('MediumSeverityIncidents', 0) for record in all_results)
            total_low = sum(record.get('LowSeverityIncidents', 0) for record in all_results)
            
            print(f"\nAggregated Incident Summary (Last 7 days):")
            print(f"  Total Incidents: {total_incidents}")
            print(f"  High Severity: {total_high}")
            print(f"  Medium Severity: {total_medium}")
            print(f"  Low Severity: {total_low}")
            
            # Upload aggregated results
            aggregated_data = [{
                'timestamp': '2025-11-01T10:30:00Z',
                'total_incidents': total_incidents,
                'high_severity_incidents': total_high,
                'medium_severity_incidents': total_medium,
                'low_severity_incidents': total_low,
                'workspaces_count': len(all_results),
                'report_type': 'incident_summary_aggregated'
            }]
            
            upload_result = await client.upload_logs(
                data=aggregated_data,
                stream_name="Custom-IncidentSummary_CL"
            )
            
            if upload_result.succeeded:
                print(f"✓ Uploaded aggregated data: {upload_result.record_count} records")
            else:
                print(f"✗ Upload failed: {upload_result.error_message}")

asyncio.run(multi_workspace_aggregation())
```

## Example 4: Configuration management

Manage and validate workspace configurations programmatically.

```python
import asyncio
from pathlib import Path
from sentinel_log_aggregator import (
    WorkspaceManager,
    WorkspaceConfig,
    SentinelAggregatorClientOptions
)

async def configuration_management():
    """Demonstrate configuration management capabilities."""
    
    # Create workspace configurations programmatically
    workspaces = [
        WorkspaceConfig(
            resource_id="/subscriptions/sub1/resourcegroups/rg1/providers/microsoft.operationalinsights/workspaces/prod-east",
            customer_id="prod-east-customer-id",
            parameters={
                "row_level_security_tag": "prod-east",
                "environment": "production",
                "region": "eastus",
                "compliance_zone": "regulated"
            },
            queries_list=["query_incident_summary", "query_user_summary", "query_security_alerts"]
        ),
        WorkspaceConfig(
            resource_id="/subscriptions/sub1/resourcegroups/rg1/providers/microsoft.operationalinsights/workspaces/prod-west",
            customer_id="prod-west-customer-id",
            parameters={
                "row_level_security_tag": "prod-west",
                "environment": "production",
                "region": "westus",
                "compliance_zone": "standard"
            },
            queries_list=["query_incident_summary", "query_user_summary"]
        ),
        WorkspaceConfig(
            resource_id="/subscriptions/sub2/resourcegroups/rg2/providers/microsoft.operationalinsights/workspaces/dev",
            customer_id="dev-customer-id",
            parameters={
                "row_level_security_tag": "dev",
                "environment": "development",
                "region": "eastus"
            },
            queries_list=["query_incident_summary"]
        )
    ]
    
    # Create workspace manager
    workspace_manager = WorkspaceManager(workspaces)
    
    # Validate configuration
    print("Validating workspace configuration...")
    errors = workspace_manager.validate_configuration()
    
    if errors:
        print("Configuration errors found:")
        for error in errors:
            print(f"  - {error}")
        return
    else:
        print("✓ Configuration is valid")
    
    # Display configuration summary
    print(f"\nWorkspace Configuration Summary:")
    print(f"  Total workspaces: {workspace_manager.count()}")
    
    # Filter by environment
    prod_workspaces = workspace_manager.for_parameter("environment", "production")
    dev_workspaces = workspace_manager.for_parameter("environment", "development")
    
    print(f"  Production workspaces: {prod_workspaces.count()}")
    print(f"  Development workspaces: {dev_workspaces.count()}")
    
    # Filter by region
    east_workspaces = workspace_manager.for_parameter("region", "eastus")
    west_workspaces = workspace_manager.for_parameter("region", "westus")
    
    print(f"  East US workspaces: {east_workspaces.count()}")
    print(f"  West US workspaces: {west_workspaces.count()}")
    
    # Filter by query support
    incident_workspaces = workspace_manager.for_query("query_incident_summary")
    user_workspaces = workspace_manager.for_query("query_user_summary")
    
    print(f"  Workspaces with incident queries: {incident_workspaces.count()}")
    print(f"  Workspaces with user queries: {user_workspaces.count()}")
    
    # Get reports summary
    reports = workspace_manager.reports_summary()
    print(f"\nReports Summary:")
    for report, count in reports.items():
        print(f"  {report}: {count} workspace(s)")
    
    # Get subscription summary
    subscriptions = workspace_manager.get_subscription_summary()
    print(f"\nSubscription Summary:")
    for sub_id, sub_data in subscriptions.items():
        print(f"  {sub_id}: {sub_data['workspace_count']} workspace(s)")
    
    # Save configuration to file
    config_path = Path("generated-workspaces.yaml")
    workspace_manager.save_to_file(config_path)
    print(f"✓ Configuration saved to {config_path}")
    
    # Load configuration from file
    loaded_manager = WorkspaceManager.from_file(config_path)
    print(f"✓ Configuration loaded from file: {loaded_manager.count()} workspaces")
    
    # Validate client configuration
    print("\nValidating client configuration...")
    try:
        options = SentinelAggregatorClientOptions.from_environment()
        options.validate()
        print("✓ Client configuration is valid")
        print(f"  DCR endpoint: {options.dcr_logs_ingestion_endpoint}")
        print(f"  DCR rule ID: {options.dcr_rule_id}")
        print(f"  Days ago: {options.days_ago}")
        print(f"  Batch hours: {options.batch_hours}")
        print(f"  Max concurrent queries: {options.max_concurrent_queries}")
    
    except Exception as e:
        print(f"✗ Client configuration error: {e}")

asyncio.run(configuration_management())
```

## Example 5: Data upload and ingestion

Upload processed data to Azure Monitor for analytics and dashboards.

```python
import asyncio
from datetime import datetime, timezone
from azure.identity.aio import DefaultAzureCredential
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    DataIngestionError
)

async def data_upload_example():
    """Demonstrate data upload to Azure Monitor."""
    
    options = SentinelAggregatorClientOptions.from_environment()
    credential = DefaultAzureCredential()
    
    async with SentinelAggregatorClient(
        dcr_logs_ingestion_endpoint=options.dcr_logs_ingestion_endpoint,
        credential=credential,
        options=options
    ) as client:
        
        # Prepare sample security summary data
        current_time = datetime.now(timezone.utc).isoformat()
        
        security_summary_data = [
            {
                "TimeGenerated": current_time,
                "WorkspaceId": "prod-east-workspace",
                "WorkspaceAlias": "prod-east",
                "Region": "eastus",
                "TotalIncidents": 15,
                "HighSeverityIncidents": 3,
                "MediumSeverityIncidents": 7,
                "LowSeverityIncidents": 5,
                "NewIncidentsLast24h": 4,
                "ResolvedIncidentsLast24h": 2,
                "AverageResolutionTimeHours": 12.5,
                "TopThreatCategory": "Malware",
                "ComplianceStatus": "Compliant",
                "ReportType": "incident_summary"
            },
            {
                "TimeGenerated": current_time,
                "WorkspaceId": "prod-west-workspace",
                "WorkspaceAlias": "prod-west",
                "Region": "westus",
                "TotalIncidents": 8,
                "HighSeverityIncidents": 1,
                "MediumSeverityIncidents": 4,
                "LowSeverityIncidents": 3,
                "NewIncidentsLast24h": 2,
                "ResolvedIncidentsLast24h": 3,
                "AverageResolutionTimeHours": 8.2,
                "TopThreatCategory": "Phishing",
                "ComplianceStatus": "Compliant",
                "ReportType": "incident_summary"
            }
        ]
        
        try:
            # Upload to custom log table
            upload_result = await client.upload_logs(
                data=security_summary_data,
                stream_name="Custom-SecuritySummary_CL"
            )
            
            if upload_result.succeeded:
                print(f"✓ Successfully uploaded {upload_result.record_count} records")
                print(f"  Upload duration: {upload_result.upload_duration:.2f} seconds")
                print(f"  Stream name: {upload_result.stream_name}")
                
                # The data will be available in Log Analytics as:
                # SecuritySummary_CL table
                print(f"\nData will be available in Log Analytics table: SecuritySummary_CL")
                print(f"Sample query to view uploaded data:")
                print(f"SecuritySummary_CL | where TimeGenerated > ago(1h) | order by TimeGenerated desc")
            
            else:
                print(f"✗ Upload failed: {upload_result.error_message}")
        
        except DataIngestionError as e:
            print(f"✗ Data ingestion error: {e.message}")
            print(f"  Stream name: {e.stream_name}")
            print(f"  Record count: {e.record_count}")
        
        # Prepare user activity summary data
        user_activity_data = [
            {
                "TimeGenerated": current_time,
                "WorkspaceId": "prod-east-workspace",
                "WorkspaceAlias": "prod-east",
                "UniqueUsersLast24h": 1250,
                "FailedLogonsLast24h": 45,
                "SuccessfulLogonsLast24h": 3200,
                "SuspiciousActivitiesLast24h": 12,
                "PrivilegedAccountsActive": 35,
                "NewUserAccountsCreated": 3,
                "DisabledUserAccounts": 1,
                "TopSourceCountry": "United States",
                "ReportType": "user_activity_summary"
            }
        ]
        
        try:
            # Upload user activity data
            user_upload_result = await client.upload_logs(
                data=user_activity_data,
                stream_name="Custom-UserActivitySummary_CL"
            )
            
            if user_upload_result.succeeded:
                print(f"✓ Successfully uploaded user activity data: {user_upload_result.record_count} records")
        
        except Exception as e:
            print(f"✗ User activity upload failed: {e}")

asyncio.run(data_upload_example())
```

## Example 6: Error handling and resilience

Implement robust error handling and retry logic.

```python
import asyncio
import logging
from typing import List, Dict, Any
from azure.identity.aio import DefaultAzureCredential
from azure.core.exceptions import ClientResponseError
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    QueryExecutionError,
    WorkspaceAccessError,
    DataIngestionError,
    WorkspaceManager
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def resilient_operations():
    """Demonstrate error handling and resilience patterns."""
    
    options = SentinelAggregatorClientOptions.from_environment()
    credential = DefaultAzureCredential()
    
    async with SentinelAggregatorClient(
        dcr_logs_ingestion_endpoint=options.dcr_logs_ingestion_endpoint,
        credential=credential,
        options=options
    ) as client:
        
        # Load workspace configuration
        workspace_manager = WorkspaceManager.from_file("workspaces.yaml")
        
        # Execute queries with comprehensive error handling
        successful_results = []
        failed_results = []
        
        query = """
        SecurityEvent
        | where TimeGenerated > ago(1h)
        | summarize count() by EventID
        | order by count_ desc
        | take 5
        """
        
        for workspace in workspace_manager.workspaces:
            workspace_alias = workspace.parameters.get('row_level_security_tag', 'unknown')
            
            try:
                # Attempt query with retry logic
                result = await resilient_query(
                    client, 
                    workspace.customer_id, 
                    query,
                    workspace_alias=workspace_alias,
                    max_retries=3
                )
                
                if result:
                    successful_results.append({
                        'workspace': workspace_alias,
                        'result': result
                    })
                    logger.info(f"✓ Query succeeded for {workspace_alias}: {result.record_count} records")
            
            except WorkspaceAccessError as e:
                error_info = {
                    'workspace': workspace_alias,
                    'error_type': 'access_denied',
                    'error': str(e)
                }
                failed_results.append(error_info)
                logger.error(f"✗ Access denied to workspace {workspace_alias}: {e.message}")
            
            except QueryExecutionError as e:
                error_info = {
                    'workspace': workspace_alias,
                    'error_type': 'query_execution',
                    'error': str(e)
                }
                failed_results.append(error_info)
                logger.error(f"✗ Query execution failed for {workspace_alias}: {e.message}")
            
            except Exception as e:
                error_info = {
                    'workspace': workspace_alias,
                    'error_type': 'unexpected',
                    'error': str(e)
                }
                failed_results.append(error_info)
                logger.error(f"✗ Unexpected error for {workspace_alias}: {e}")
        
        # Summary
        print(f"\nExecution Summary:")
        print(f"  Successful: {len(successful_results)}")
        print(f"  Failed: {len(failed_results)}")
        
        # Upload results if any successful
        if successful_results:
            try:
                await upload_with_retry(client, successful_results)
            except Exception as e:
                logger.error(f"Failed to upload results: {e}")
        
        # Report failed operations
        if failed_results:
            print(f"\nFailed Operations:")
            for failure in failed_results:
                print(f"  {failure['workspace']}: {failure['error_type']} - {failure['error']}")

async def resilient_query(client, workspace_id: str, query: str, workspace_alias: str = None, max_retries: int = 3):
    """Execute query with retry logic and exponential backoff."""
    
    for attempt in range(max_retries):
        try:
            result = await client.query_workspace(workspace_id, query)
            return result
        
        except ClientResponseError as e:
            if e.status_code == 429:  # Rate limited
                wait_time = (2 ** attempt) + 1  # Exponential backoff
                logger.warning(f"Rate limited for {workspace_alias}, waiting {wait_time}s (attempt {attempt + 1})")
                await asyncio.sleep(wait_time)
                continue
            elif e.status_code >= 500:  # Server errors
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + 1
                    logger.warning(f"Server error for {workspace_alias}, retrying in {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise QueryExecutionError(f"Server error after {max_retries} attempts: {e}")
            else:
                # Client errors (4xx) - don't retry
                raise QueryExecutionError(f"Client error: {e}")
        
        except QueryExecutionError as e:
            if "timeout" in str(e).lower() and attempt < max_retries - 1:
                wait_time = (2 ** attempt) + 1
                logger.warning(f"Query timeout for {workspace_alias}, retrying in {wait_time}s (attempt {attempt + 1})")
                await asyncio.sleep(wait_time)
                continue
            else:
                raise
    
    raise QueryExecutionError(f"Failed after {max_retries} attempts")

async def upload_with_retry(client, results: List[Dict[str, Any]], max_retries: int = 3):
    """Upload data with retry logic."""
    
    # Prepare data for upload
    upload_data = []
    current_time = datetime.now(timezone.utc).isoformat()
    
    for result_info in results:
        workspace_alias = result_info['workspace']
        result = result_info['result']
        
        # Create summary record
        summary_record = {
            "TimeGenerated": current_time,
            "WorkspaceAlias": workspace_alias,
            "QueryType": "security_events_summary",
            "RecordCount": result.record_count,
            "ExecutionTimeSeconds": result.execution_time,
            "Status": "success"
        }
        upload_data.append(summary_record)
    
    # Upload with retry
    for attempt in range(max_retries):
        try:
            upload_result = await client.upload_logs(
                data=upload_data,
                stream_name="Custom-QueryExecutionSummary_CL"
            )
            
            if upload_result.succeeded:
                logger.info(f"✓ Upload succeeded: {upload_result.record_count} records")
                return upload_result
            else:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + 1
                    logger.warning(f"Upload failed, retrying in {wait_time}s (attempt {attempt + 1}): {upload_result.error_message}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise DataIngestionError(f"Upload failed after {max_retries} attempts: {upload_result.error_message}")
        
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + 1
                logger.warning(f"Upload error, retrying in {wait_time}s (attempt {attempt + 1}): {e}")
                await asyncio.sleep(wait_time)
                continue
            else:
                raise

# Import required modules at the top
from datetime import datetime, timezone

asyncio.run(resilient_operations())
```

## Running the examples

### Prerequisites setup

1. **Install the package:**
   ```powershell
   pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git
   ```

2. **Set up environment variables:**
   ```powershell
   # Create .env file
   @'
   DCR_LOGS_INGESTION_ENDPOINT=https://your-dcr-endpoint.monitor.azure.com
   DCR_RULE_ID=dcr-your-rule-id
   DAYS_AGO=7
   BATCH_HOURS=24
   MAX_CONCURRENT_QUERIES=5
   LOG_LEVEL=INFO
   '@ | Out-File -FilePath .env -Encoding UTF8
   ```

3. **Configure authentication:**
   ```powershell
   # For Azure CLI (development)
   az login
   
   # For service principal (production)
   $env:AZURE_CLIENT_ID = "your-client-id"
   $env:AZURE_TENANT_ID = "your-tenant-id"
   $env:AZURE_CLIENT_SECRET = "your-client-secret"
   ```

4. **Create workspace configuration:**
   ```powershell
   # Create workspaces.yaml with your actual workspace details
   Copy-Item workspaces.yaml.example workspaces.yaml
   # Edit workspaces.yaml with your workspace information using your preferred editor
   code workspaces.yaml  # Opens in VS Code
   ```

### Running individual examples

```powershell
# Save examples to files and run
python health_check_example.py
python simple_query_example.py
python multi_workspace_example.py
python configuration_example.py
python data_upload_example.py
python resilient_operations_example.py
```

## Next steps

- [Advanced examples](advanced-examples.md) - More complex scenarios and integration patterns
- [CLI usage](../cli-usage.md) - Command-line interface documentation
- [SDK usage](../sdk-usage.md) - Comprehensive SDK reference
- [Best practices](../best-practices.md) - Production deployment guidance
