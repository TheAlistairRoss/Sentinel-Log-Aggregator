# SDK Advanced Usage

Advanced patterns and techniques for the Sentinel Log Aggregator Python SDK.

## Table of Contents

- [Custom Query Development](#custom-query-development)
- [Advanced Workspace Filtering](#advanced-workspace-filtering)
- [Performance Optimization](#performance-optimization)
- [Error Handling Patterns](#error-handling-patterns)
- [Integration Patterns](#integration-patterns)
- [Testing and Validation](#testing-and-validation)
- [Production Deployment](#production-deployment)

## Custom Query Development

### Creating Custom Queries

Define custom KQL queries for your specific needs:

```python
from sentinel_log_aggregator.models import KQLQueryDefinition

class CustomThreatQuery(KQLQueryDefinition):
    """Custom query for threat intelligence aggregation"""
    
    def __init__(self):
        super().__init__(
            name="query_threat_intel",
            destination_stream="Custom-Reports_ThreatIntel_CL",
            description="Aggregate threat intelligence indicators",
            report_name="report_threat_intel"
        )
        
        # Define required parameters
        self.add_parameter("row_level_security_tag", "string", required=False, default="")
        self.add_parameter("lookback_days", "int", required=False, default=7)
        self.add_parameter("min_confidence", "int", required=False, default=70)
    
    def get_query(self) -> str:
        return """
        ThreatIntelligenceIndicator
        | where TimeGenerated > ago({lookback_days}d)
        | where ConfidenceScore >= {min_confidence}
        | summarize 
            TotalIndicators=count(),
            UniqueIndicators=dcount(IndicatorId),
            UniqueTypes=dcount(ThreatType),
            HighConfidence=countif(ConfidenceScore >= 90)
            by bin(TimeGenerated, 1h), ThreatType
        | extend 
            row_level_security_tag = "{row_level_security_tag}",
            report_type = "threat_intel",
            processing_time = now()
        """
```

### Registering Custom Queries

```python
from sentinel_log_aggregator.query_registry import QueryRegistry

# Register custom query
registry = QueryRegistry()
registry.register_query(CustomThreatQuery())

# Verify registration
available_queries = registry.list_queries()
print(f"Available queries: {', '.join(available_queries)}")
```

### Using Custom Queries

**In workspace configuration** (`workspaces.yaml`):
```yaml
workspaces:
  - resource_id: /subscriptions/.../workspaces/ws-prod
    customer_id: YOUR-WORKSPACE-ID
    aggregation_workspace: true
    parameters:
      row_level_security_tag: "PROD"
      lookback_days: 7
      min_confidence: 80
    queries_list:
      - query_threat_intel  # Your custom query
      - query_incident_summary
```

**Programmatically**:
```python
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    WorkspaceConfig
)

# Define workspace with custom parameters
workspace = WorkspaceConfig(
    resource_id="/subscriptions/.../workspaces/ws-prod",
    customer_id="YOUR-WORKSPACE-ID",
    aggregation_workspace=True,
    parameters={
        "row_level_security_tag": "PROD",
        "lookback_days": 7,
        "min_confidence": 80
    },
    queries_list=["query_threat_intel"]
)

async with SentinelAggregatorClient(options) as client:
    summary = await client.execute_queries([workspace])
```

### Dynamic Query Parameters

Pass runtime parameters to queries:

```python
import asyncio
from datetime import datetime, timedelta
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    WorkspaceConfig
)

async def run_custom_query_with_params(lookback_days: int, confidence_threshold: int):
    """Run custom query with dynamic parameters"""
    
    options = SentinelAggregatorClientOptions(
        lookback_period=f"P{lookback_days}D",
        dcr_endpoint="https://YOUR-DCE.azure.com",
        dcr_immutable_id="dcr-YOUR-ID"
    )
    
    workspace = WorkspaceConfig(
        resource_id="/subscriptions/.../workspaces/ws-prod",
        customer_id="YOUR-WORKSPACE-ID",
        aggregation_workspace=True,
        parameters={
            "row_level_security_tag": "PROD",
            "lookback_days": lookback_days,
            "min_confidence": confidence_threshold
        },
        queries_list=["query_threat_intel"]
    )
    
    async with SentinelAggregatorClient(options) as client:
        summary = await client.execute_queries([workspace])
        return summary

# Usage
summary = asyncio.run(run_custom_query_with_params(lookback_days=14, confidence_threshold=85))
print(f"Processed {summary.total_records_downloaded} records")
```

## Advanced Workspace Filtering

### Fluent Filtering API

```python
from sentinel_log_aggregator import WorkspaceManager, load_workspace_config

# Load all workspaces
all_workspaces = load_workspace_config("workspaces.yaml")

# Create manager
mgr = WorkspaceManager(all_workspaces)

# Chain filters
filtered_workspaces = (
    mgr
    .for_report("report_incident_summary")
    .for_security_tag("PROD")
    .filter_by_alias("customer-*")
)

print(f"Filtered to {len(filtered_workspaces)} workspaces")
```

### Custom Filter Functions

```python
from sentinel_log_aggregator import WorkspaceManager, WorkspaceConfig

def custom_filter(workspace: WorkspaceConfig) -> bool:
    """Custom filter logic"""
    # Filter by custom parameters
    if "customer_tier" in workspace.parameters:
        return workspace.parameters["customer_tier"] == "premium"
    return False

# Apply custom filter
mgr = WorkspaceManager(all_workspaces)
premium_workspaces = [ws for ws in mgr.workspaces if custom_filter(ws)]

# Execute queries on filtered workspaces
async with SentinelAggregatorClient(options) as client:
    summary = await client.execute_queries(premium_workspaces)
```

### Workspace Grouping

Process workspaces in groups:

```python
from itertools import groupby
from operator import attrgetter

def group_workspaces_by_tag(workspaces: list) -> dict:
    """Group workspaces by security tag"""
    sorted_workspaces = sorted(
        workspaces,
        key=lambda ws: ws.parameters.get("row_level_security_tag", "")
    )
    
    groups = {}
    for tag, group in groupby(sorted_workspaces, key=lambda ws: ws.parameters.get("row_level_security_tag", "")):
        groups[tag] = list(group)
    
    return groups

# Process each group separately
async def process_workspace_groups():
    all_workspaces = load_workspace_config("workspaces.yaml")
    groups = group_workspaces_by_tag(all_workspaces)
    
    async with SentinelAggregatorClient(options) as client:
        for tag, workspaces in groups.items():
            print(f"Processing group: {tag} ({len(workspaces)} workspaces)")
            summary = await client.execute_queries(workspaces)
            print(f"  ✅ {summary.total_records_uploaded} records uploaded")
```

### Dynamic Workspace Discovery

Discover workspaces programmatically:

```python
from azure.mgmt.loganalytics import LogAnalyticsManagementClient
from azure.identity import DefaultAzureCredential
from sentinel_log_aggregator import WorkspaceConfig

async def discover_sentinel_workspaces(subscription_id: str) -> list[WorkspaceConfig]:
    """Discover all Sentinel workspaces in a subscription"""
    
    credential = DefaultAzureCredential()
    la_client = LogAnalyticsManagementClient(credential, subscription_id)
    
    workspaces = []
    for workspace in la_client.workspaces.list():
        # Check if Sentinel is enabled (has SecurityInsights solution)
        workspace_config = WorkspaceConfig(
            resource_id=workspace.id,
            customer_id=workspace.customer_id,
            alias=workspace.name,
            aggregation_workspace=False,
            parameters={"row_level_security_tag": workspace.name.upper()},
            queries_list=["query_incident_summary"]
        )
        workspaces.append(workspace_config)
    
    return workspaces

# Usage
discovered_workspaces = await discover_sentinel_workspaces("YOUR-SUB-ID")
print(f"Discovered {len(discovered_workspaces)} workspaces")
```

## Performance Optimization

### Incremental processing pattern

Implement incremental data aggregation using last successful timestamps:

```python
import asyncio
import logging
from datetime import datetime, timezone
from azure.identity.aio import DefaultAzureCredential
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    load_workspace_config
)

logger = logging.getLogger(__name__)

async def scheduled_incremental_aggregation():
    """
    Production-ready incremental aggregation pattern.
    Designed for scheduled execution (e.g., hourly/daily).
    """
    
    try:
        # Configure for incremental processing
        options = SentinelAggregatorClientOptions.from_environment()
        
        # Override to enable incremental mode
        options.use_last_successful = True
        options.health_to_sentinel = True
        options.batch_time_size = "PT6H"  # Smaller batches for frequent runs
        
        # Validate configuration
        options.validate()
        
        # Load workspaces
        workspaces = load_workspace_config("workspaces.yaml")
        logger.info(f"Loaded {len(workspaces)} workspaces for incremental processing")
        
        # Execute incremental aggregation
        async with SentinelAggregatorClient(
            dcr_logs_ingestion_endpoint=options.dcr_logs_ingestion_endpoint,
            credential=DefaultAzureCredential(),
            options=options
        ) as client:
            
            # Check health logging setup before starting
            health_status = await client.check_health_logging(workspaces)
            if not health_status.all_healthy:
                logger.warning(f"Health logging issues detected in {len(health_status.unhealthy_workspaces)} workspaces")
            
            # Execute queries - will use last successful timestamps
            logger.info("Starting incremental aggregation...")
            start_time = datetime.now(timezone.utc)
            
            summary = await client.execute_queries(workspaces, dry_run=False)
            
            # Log execution summary
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"Incremental aggregation completed in {duration:.1f}s")
            logger.info(f"  Job ID: {summary.job_correlation_id}")
            logger.info(f"  Records processed: {summary.total_records_uploaded:,}")
            logger.info(f"  Successful queries: {summary.total_successful_queries}")
            logger.info(f"  Failed queries: {summary.total_failed_queries}")
            
            # Return status for monitoring systems
            return {
                "status": "success" if summary.total_failed_queries == 0 else "partial_success",
                "job_id": summary.job_correlation_id,
                "records_processed": summary.total_records_uploaded,
                "duration_seconds": duration,
                "failed_queries": summary.total_failed_queries
            }
            
    except Exception as e:
        logger.error(f"Incremental aggregation failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Usage in scheduled task (e.g., Azure Function, cron job)
result = await scheduled_incremental_aggregation()
if result["status"] == "failed":
    # Alert monitoring system
    logger.critical(f"Aggregation job failed: {result['error']}")
```

### Checking last successful timestamps

```python
from sentinel_log_aggregator import SentinelAggregatorClient, load_workspace_config
from azure.identity.aio import DefaultAzureCredential

async def check_last_execution_status():
    """
    Query health logging to see last successful execution times.
    Useful for monitoring and troubleshooting.
    """
    
    options = SentinelAggregatorClientOptions.from_environment()
    workspaces = load_workspace_config("workspaces.yaml")
    credential = DefaultAzureCredential()
    
    async with SentinelAggregatorClient(
        dcr_logs_ingestion_endpoint=options.dcr_logs_ingestion_endpoint,
        credential=credential,
        options=options
    ) as client:
        # Check execution history for each workspace
        for workspace in workspaces:
            # Query health logging table
            query = f"""
            SentinelHealthLog_CL
            | where workspace_id_s == "{workspace.customer_id}"
            | where status_s == "success"
            | summarize 
                LastSuccessful=max(end_time_t),
                TotalRuns=count(),
                AvgDuration=avg(duration_seconds_d)
                by query_name_s
            | project query_name_s, LastSuccessful, TotalRuns, AvgDuration
            """
            
            result = await client.query_workspace(
                workspace_id=workspace.customer_id,
                query=query
            )
            
            if result.succeeded:
                print(f"\nWorkspace: {workspace.alias or workspace.customer_id[:8]}")
                print(f"{'Query':<30} {'Last Success':<25} {'Runs':<8} {'Avg Duration'}")
                print("-" * 80)
                
                for record in result.data:
                    print(
                        f"{record['query_name_s']:<30} "
                        f"{record['LastSuccessful']:<25} "
                        f"{record['TotalRuns']:<8} "
                        f"{record['AvgDuration']:.1f}s"
                    )

# Check status
await check_last_execution_status()
```

### First-run vs incremental behavior

```python
import asyncio
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    load_workspace_config
)
from azure.identity.aio import DefaultAzureCredential

async def smart_aggregation():
    """
    Automatically handle first run (historical) vs incremental runs.
    """
    
    options = SentinelAggregatorClientOptions(
        use_last_successful=True,
        health_to_sentinel=True,
        lookback_period="P30D",          # Used only on first run
        batch_time_size="PT12H",
        dcr_logs_ingestion_endpoint="https://your-dcr.monitor.azure.com",
        dcr_immutable_id="dcr-your-rule-id"
    )
    
    workspaces = load_workspace_config("workspaces.yaml")
    credential = DefaultAzureCredential()
    
    async with SentinelAggregatorClient(
        dcr_logs_ingestion_endpoint=options.dcr_logs_ingestion_endpoint,
        credential=credential,
        options=options
    ) as client:
        # Check if this is first run by querying health logs
        first_run = await is_first_run(client, workspaces)
        
        if first_run:
            print("First run detected - processing historical data (30 days)")
            print("Future runs will be incremental from this point")
        else:
            print("Incremental run - processing data since last successful execution")
        
        # Execute - behavior automatically adjusts
        summary = await client.execute_queries(workspaces)
        
        return summary

async def is_first_run(client, workspaces) -> bool:
    """
    Check if any workspace has successful execution history.
    """
    try:
        # Query health logging for any successful runs
        workspace_ids = [ws.customer_id for ws in workspaces]
        
        # Check aggregation workspace for health logs
        agg_workspace = next((ws for ws in workspaces if ws.aggregation_workspace), None)
        if not agg_workspace:
            return True  # No agg workspace, treat as first run
        
        query = f"""
        SentinelHealthLog_CL
        | where workspace_id_s in ({','.join([f'"{wid}"' for wid in workspace_ids])})
        | where status_s == "success"
        | summarize count()
        """
        
        result = await client.query_workspace(
            workspace_id=agg_workspace.customer_id,
            query=query
        )
        
        if result.succeeded and result.record_count > 0:
            count = result.data[0]['count_'] if result.data else 0
            return count == 0
        
        return True  # Assume first run if health query fails
        
    except Exception:
        return True  # Safe default

# Run smart aggregation
result = await smart_aggregation()
```

### Concurrent Execution Tuning

```python
from sentinel_log_aggregator import SentinelAggregatorClientOptions

# High-throughput configuration
options = SentinelAggregatorClientOptions(
    lookback_period="P1D",
    batch_time_size="PT12H",  # Smaller batches
    max_concurrent_queries=10,  # More parallelism
    dcr_logs_ingestion_endpoint="https://YOUR-DCE.azure.com",
    dcr_immutable_id="dcr-YOUR-ID"
)

# Memory-constrained configuration
options = SentinelAggregatorClientOptions(
    lookback_period="P1D",
    batch_time_size="PT6H",  # Very small batches
    max_concurrent_queries=2,  # Limited parallelism
    dcr_logs_ingestion_endpoint="https://YOUR-DCE.azure.com",
    dcr_immutable_id="dcr-YOUR-ID"
)
```

### Batch Processing Strategies

```python
import asyncio
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    load_workspace_config
)

async def process_in_workspace_batches(batch_size: int = 10):
    """Process workspaces in batches to control resource usage"""
    
    options = SentinelAggregatorClientOptions.from_environment()
    all_workspaces = load_workspace_config("workspaces.yaml")
    
    # Split into batches
    workspace_batches = [
        all_workspaces[i:i + batch_size]
        for i in range(0, len(all_workspaces), batch_size)
    ]
    
    total_records = 0
    
    async with SentinelAggregatorClient(options) as client:
        for i, batch in enumerate(workspace_batches, 1):
            print(f"Processing batch {i}/{len(workspace_batches)}")
            
            summary = await client.execute_queries(batch)
            total_records += summary.total_records_uploaded
            
            print(f"  ✅ Batch {i}: {summary.total_records_uploaded} records")
            
            # Optional: Wait between batches
            if i < len(workspace_batches):
                await asyncio.sleep(5)
    
    print(f"Total records processed: {total_records}")

# Usage
asyncio.run(process_in_workspace_batches(batch_size=5))
```

### Memory Management

```python
import gc
import asyncio
from sentinel_log_aggregator import SentinelAggregatorClient

async def memory_efficient_processing():
    """Process with explicit memory management"""
    
    options = SentinelAggregatorClientOptions.from_environment()
    workspaces = load_workspace_config("workspaces.yaml")
    
    async with SentinelAggregatorClient(options) as client:
        for workspace in workspaces:
            # Process one workspace at a time
            summary = await client.execute_queries([workspace])
            
            print(f"✅ {workspace.alias}: {summary.total_records_uploaded} records")
            
            # Force garbage collection
            gc.collect()
            
            # Brief pause to allow cleanup
            await asyncio.sleep(1)
```

## Error Handling Patterns

### Comprehensive Error Handling

```python
import asyncio
import logging
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    AuthenticationError,
    ConfigurationError,
    QueryExecutionError,
    load_workspace_config
)

logger = logging.getLogger(__name__)

async def robust_execution():
    """Execute with comprehensive error handling"""
    
    try:
        # Configuration loading with validation
        try:
            options = SentinelAggregatorClientOptions.from_environment()
            options.validate()
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            logger.error("Check your .env file and environment variables")
            return 1
        
        # Workspace loading with validation
        try:
            workspaces = load_workspace_config("workspaces.yaml")
            if not workspaces:
                raise ValueError("No workspaces configured")
        except FileNotFoundError:
            logger.error("Workspace configuration file not found")
            return 1
        except Exception as e:
            logger.error(f"Failed to load workspaces: {e}")
            return 1
        
        # Query execution with retry logic
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                async with SentinelAggregatorClient(options) as client:
                    summary = await client.execute_queries(workspaces)
                    
                    # Check for failures
                    if summary.total_failed_queries > 0:
                        logger.warning(
                            f"⚠️  {summary.total_failed_queries} queries failed"
                        )
                    
                    logger.info(f"✅ Success: {summary.total_records_uploaded} records")
                    return 0
                    
            except AuthenticationError as e:
                logger.error(f"Authentication failed: {e}")
                logger.error("Run 'az login' or check Managed Identity")
                return 1
                
            except QueryExecutionError as e:
                logger.error(f"Query execution failed: {e}")
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time}s... (attempt {attempt}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Max retries exceeded")
                    return 1
                    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1

# Usage
exit_code = asyncio.run(robust_execution())
exit(exit_code)
```

### Per-Workspace Error Handling

```python
async def process_workspaces_individually():
    """Process each workspace separately to isolate failures"""
    
    options = SentinelAggregatorClientOptions.from_environment()
    workspaces = load_workspace_config("workspaces.yaml")
    
    results = []
    
    async with SentinelAggregatorClient(options) as client:
        for workspace in workspaces:
            try:
                summary = await client.execute_queries([workspace])
                
                results.append({
                    "workspace": workspace.alias,
                    "status": "success",
                    "records": summary.total_records_uploaded
                })
                
                logger.info(f"✅ {workspace.alias}: {summary.total_records_uploaded} records")
                
            except Exception as e:
                results.append({
                    "workspace": workspace.alias,
                    "status": "failed",
                    "error": str(e)
                })
                
                logger.error(f"❌ {workspace.alias}: {e}")
    
    # Summary
    successful = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - successful
    
    logger.info(f"Summary: {successful} successful, {failed} failed")
    return results
```

## Integration Patterns

### Integration with Azure Functions

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

@app.timer_trigger(schedule="0 0 2 * * *", arg_name="mytimer")
async def sentinel_aggregator_function(mytimer: func.TimerRequest) -> None:
    """Timer-triggered Azure Function"""
    
    if mytimer.past_due:
        logging.warning('Timer is past due!')
    
    try:
        # Load configuration from app settings
        options = SentinelAggregatorClientOptions(
            lookback_period=os.environ.get("LOOKBACK_PERIOD", "P1D"),
            dcr_endpoint=os.environ["DCR_ENDPOINT"],
            dcr_immutable_id=os.environ["DCR_IMMUTABLE_ID"]
        )
        
        # Load workspaces (could be from blob storage)
        workspaces = load_workspace_config("workspaces.yaml")
        
        # Execute
        async with SentinelAggregatorClient(options) as client:
            summary = await client.execute_queries(workspaces)
            
        logging.info(
            f"✅ Job complete: "
            f"{summary.total_records_uploaded} records uploaded, "
            f"Job ID: {summary.job_correlation_id}"
        )
        
    except Exception as e:
        logging.error(f"❌ Job failed: {e}", exc_info=True)
        raise

@app.http_trigger(route="aggregate", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
async def http_trigger_aggregator(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP-triggered aggregation with custom parameters"""
    
    try:
        # Parse request body
        req_body = req.get_json()
        lookback = req_body.get("lookback_period", "P1D")
        dry_run = req_body.get("dry_run", False)
        
        # Configure
        options = SentinelAggregatorClientOptions(
            lookback_period=lookback,
            dcr_endpoint=os.environ["DCR_ENDPOINT"],
            dcr_immutable_id=os.environ["DCR_IMMUTABLE_ID"]
        )
        
        workspaces = load_workspace_config("workspaces.yaml")
        
        # Execute
        async with SentinelAggregatorClient(options) as client:
            summary = await client.execute_queries(workspaces, dry_run=dry_run)
        
        return func.HttpResponse(
            f"Success: {summary.total_records_uploaded} records uploaded",
            status_code=200
        )
        
    except Exception as e:
        logging.error(f"HTTP trigger failed: {e}", exc_info=True)
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
```

### Integration with Azure Logic Apps

Create an Azure Function HTTP trigger as shown above, then call it from Logic Apps:

```json
{
    "definition": {
        "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
        "actions": {
            "Call_Aggregator": {
                "type": "Http",
                "inputs": {
                    "method": "POST",
                    "uri": "https://YOUR-FUNCTION-APP.azurewebsites.net/api/aggregate",
                    "headers": {
                        "x-functions-key": "@parameters('functionKey')"
                    },
                    "body": {
                        "lookback_period": "P1D",
                        "dry_run": false
                    }
                }
            },
            "Send_notification": {
                "type": "Office365",
                "runAfter": {
                    "Call_Aggregator": ["Succeeded"]
                },
                "inputs": {
                    "message": {
                        "subject": "Sentinel Aggregation Complete",
                        "body": "@{body('Call_Aggregator')}"
                    }
                }
            }
        },
        "triggers": {
            "Recurrence": {
                "type": "Recurrence",
                "recurrence": {
                    "frequency": "Day",
                    "interval": 1,
                    "schedule": {
                        "hours": [2]
                    }
                }
            }
        }
    }
}
```

### Integration with Jupyter Notebooks

```python
# Jupyter notebook cell
import asyncio
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    load_workspace_config
)

# Configure (using Azure CLI auth)
options = SentinelAggregatorClientOptions(
    lookback_period="PT1H",  # Last hour for quick testing
    batch_time_size="PT1H"
)

# Load workspaces
workspaces = load_workspace_config("workspaces.yaml")

# Execute (dry-run for testing)
async with SentinelAggregatorClient(options) as client:
    summary = await client.execute_queries(workspaces, dry_run=True)

# Display results
print(f"Downloaded: {summary.total_records_downloaded:,} records")
print(f"Duration: {summary.total_duration:.1f}s")
print(f"Success rate: {summary.total_successful_queries}/{summary.total_successful_queries + summary.total_failed_queries}")
```

## Testing and Validation

### Unit Testing with Mocks

```python
import pytest
from unittest.mock import AsyncMock, patch
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    WorkspaceConfig
)

@pytest.fixture
def mock_options():
    return SentinelAggregatorClientOptions(
        lookback_period="P1D",
        dcr_endpoint="https://test.azure.com",
        dcr_immutable_id="dcr-test"
    )

@pytest.fixture
def mock_workspace():
    return WorkspaceConfig(
        resource_id="/subscriptions/test/workspaces/ws-test",
        customer_id="test-id",
        aggregation_workspace=True,
        parameters={"row_level_security_tag": "TEST"},
        queries_list=["query_incident_summary"]
    )

@pytest.mark.asyncio
async def test_execute_queries_success(mock_options, mock_workspace):
    """Test successful query execution"""
    
    with patch('sentinel_log_aggregator.sentinel_client.LogsQueryClient') as mock_client:
        # Mock the query response
        mock_client.return_value.query_workspace = AsyncMock(
            return_value={"tables": [{"rows": [[1, 2, 3]]}]}
        )
        
        async with SentinelAggregatorClient(mock_options) as client:
            summary = await client.execute_queries([mock_workspace], dry_run=True)
            
            assert summary.total_successful_queries == 1
            assert summary.total_failed_queries == 0
            assert summary.total_records_downloaded > 0

@pytest.mark.asyncio
async def test_authentication_error(mock_options, mock_workspace):
    """Test authentication error handling"""
    
    with patch('sentinel_log_aggregator.sentinel_client.DefaultAzureCredential') as mock_cred:
        mock_cred.side_effect = Exception("Authentication failed")
        
        with pytest.raises(Exception):
            async with SentinelAggregatorClient(mock_options) as client:
                await client.execute_queries([mock_workspace])
```

### Integration Testing

```python
import asyncio
import pytest
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    load_workspace_config
)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_dry_run():
    """Integration test with real Azure (dry-run)"""
    
    # Load real configuration
    options = SentinelAggregatorClientOptions.from_environment()
    workspaces = load_workspace_config("tests/test-workspaces.yaml")
    
    # Execute in dry-run mode
    async with SentinelAggregatorClient(options) as client:
        summary = await client.execute_queries(workspaces, dry_run=True)
    
    # Assertions
    assert summary.total_successful_queries > 0
    assert summary.total_duration > 0
    assert summary.job_correlation_id is not None
```

## Production Deployment

### Docker Deployment

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY workspaces.yaml .
COPY main.py .

# Run as non-root user
RUN useradd -m -u 1000 sentinel && chown -R sentinel:sentinel /app
USER sentinel

CMD ["python", "main.py"]
```

**main.py**:
```python
import asyncio
import logging
import sys
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    load_workspace_config
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

async def main():
    try:
        options = SentinelAggregatorClientOptions.from_environment()
        workspaces = load_workspace_config("workspaces.yaml")
        
        async with SentinelAggregatorClient(options) as client:
            summary = await client.execute_queries(workspaces)
        
        logging.info(f"✅ Complete: {summary.total_records_uploaded} records")
        return 0
        
    except Exception as e:
        logging.error(f"❌ Failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  sentinel-aggregator:
    build: .
    environment:
      - AZURE_CLIENT_ID=${AZURE_CLIENT_ID}
      - AZURE_CLIENT_SECRET=${AZURE_CLIENT_SECRET}
      - AZURE_TENANT_ID=${AZURE_TENANT_ID}
      - DCR_ENDPOINT=${DCR_ENDPOINT}
      - DCR_IMMUTABLE_ID=${DCR_IMMUTABLE_ID}
      - LOOKBACK_PERIOD=P1D
    restart: unless-stopped
```

### Kubernetes Deployment

**deployment.yaml**:
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: sentinel-aggregator
  namespace: sentinel
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        metadata:
          labels:
            app: sentinel-aggregator
        spec:
          containers:
            - name: aggregator
              image: myregistry.azurecr.io/sentinel-aggregator:latest
              env:
                - name: DCR_ENDPOINT
                  valueFrom:
                    secretKeyRef:
                      name: sentinel-config
                      key: dcr-endpoint
                - name: DCR_IMMUTABLE_ID
                  valueFrom:
                    secretKeyRef:
                      name: sentinel-config
                      key: dcr-id
                - name: LOOKBACK_PERIOD
                  value: "P1D"
              resources:
                requests:
                  memory: "256Mi"
                  cpu: "250m"
                limits:
                  memory: "512Mi"
                  cpu: "500m"
          restartPolicy: OnFailure
```

## Next Steps

- 📖 **[SDK Reference](sdk-reference.md)** - Complete API documentation
- 📖 **[CLI Advanced Usage](cli-advanced.md)** - Advanced CLI patterns
- 🔧 **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

---

**Need help?** Check [Troubleshooting](troubleshooting.md) or ask in [GitHub Discussions](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/discussions).
