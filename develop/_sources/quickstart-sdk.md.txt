# Quick Start - Python SDK

Get started with Sentinel Log Aggregator Python SDK in 5 minutes.

## Prerequisites

- Python 3.8 or later
- Azure CLI authenticated (`az login`) or Managed Identity configured
- Access to at least one Microsoft Sentinel workspace

## Step 1: Install the Package

```bash
pip install sentinel-log-aggregator
```

## Step 2: Basic Usage

### Minimal Example (Dry-Run)

```python
import asyncio
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    WorkspaceConfig
)

async def main():
    # Configure client
    options = SentinelAggregatorClientOptions(
        lookback_period="P1D",
        batch_time_size="PT24H"
    )
    
    # Define workspace
    workspace = WorkspaceConfig(
        resource_id="/subscriptions/YOUR-SUB/resourcegroups/YOUR-RG/providers/microsoft.operationalinsights/workspaces/YOUR-WS",
        customer_id="YOUR-WORKSPACE-CUSTOMER-ID",
        aggregation_workspace=True,
        parameters={"row_level_security_tag": "PROD"},
        queries_list=["query_incident_summary"]
    )
    
    # Create client and run (dry-run mode)
    async with SentinelAggregatorClient(options) as client:
        summary = await client.execute_queries(
            workspaces=[workspace],
            dry_run=True
        )
        
        print(f"✅ Downloaded {summary.total_records_downloaded} records")
        print(f"⏱️  Duration: {summary.total_duration:.1f}s")

if __name__ == "__main__":
    asyncio.run(main())
```

**Run it:**
```bash
python my_script.py
```

**Expected Output:**
```
✅ Downloaded 45 records
⏱️  Duration: 5.2s
```

## Step 3: Load Configuration from Files

### Using YAML Configuration

**workspaces.yaml**:
```yaml
workspaces:
  - resource_id: /subscriptions/abc-123/resourcegroups/rg-sentinel/providers/microsoft.operationalinsights/workspaces/ws-prod
    customer_id: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
    aggregation_workspace: true
    parameters:
      row_level_security_tag: "PROD"
    queries_list:
      - query_incident_summary
      - query_workspace_usage
```

**.env**:
```bash
LOOKBACK_PERIOD=P1D
BATCH_TIME_SIZE=PT24H
MAX_CONCURRENT_QUERIES=5
```

**Python Script**:
```python
import asyncio
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    load_workspace_config
)

async def main():
    # Load configuration from environment
    options = SentinelAggregatorClientOptions.from_environment()
    
    # Load workspaces from YAML
    workspaces = load_workspace_config("workspaces.yaml")
    
    # Execute queries (dry-run)
    async with SentinelAggregatorClient(options) as client:
        summary = await client.execute_queries(workspaces, dry_run=True)
        
        print(f"✅ Execution Summary:")
        print(f"   • Workspaces processed: {len(workspaces)}")
        print(f"   • Records downloaded: {summary.total_records_downloaded}")
        print(f"   • Successful queries: {summary.total_successful_queries}")
        print(f"   • Failed queries: {summary.total_failed_queries}")
        print(f"   • Duration: {summary.total_duration:.1f}s")

if __name__ == "__main__":
    asyncio.run(main())
```

## Step 4: Production Run with Data Upload

```python
import asyncio
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    load_workspace_config
)

async def main():
    # Configure with DCR endpoints
    options = SentinelAggregatorClientOptions(
        lookback_period="P1D",
        batch_time_size="PT24H",
        dcr_endpoint="https://YOUR-DCR-ENDPOINT.azure.com",
        dcr_immutable_id="dcr-YOUR-DCR-ID"
    )
    
    # Load workspaces
    workspaces = load_workspace_config("workspaces.yaml")
    
    # Execute and upload
    async with SentinelAggregatorClient(options) as client:
        summary = await client.execute_queries(workspaces, dry_run=False)
        
        print(f"✅ Batch Complete:")
        print(f"   • Records uploaded: {summary.total_records_uploaded}")
        print(f"   • Successful uploads: {summary.total_successful_uploads}")
        print(f"   • Duration: {summary.total_duration:.1f}s")

if __name__ == "__main__":
    asyncio.run(main())
```

## Common Patterns

### Pattern 1: Filter Workspaces by Report

```python
from sentinel_log_aggregator import WorkspaceManager, load_workspace_config

# Load all workspaces
all_workspaces = load_workspace_config("workspaces.yaml")

# Filter for specific report
workspace_mgr = WorkspaceManager(all_workspaces)
incident_workspaces = workspace_mgr.for_report("report_incident_summary")

# Execute only relevant queries
async with SentinelAggregatorClient(options) as client:
    summary = await client.execute_queries(incident_workspaces)
```

### Pattern 2: Custom Time Range

```python
from datetime import datetime, timedelta, timezone

# Last 7 days
options = SentinelAggregatorClientOptions(
    start_time=datetime.now(timezone.utc) - timedelta(days=7),
    end_time=datetime.now(timezone.utc)
)

async with SentinelAggregatorClient(options) as client:
    summary = await client.execute_queries(workspaces)
```

### Pattern 3: Workspace Filtering and Selection

```python
from sentinel_log_aggregator import WorkspaceManager

workspaces = load_workspace_config("workspaces.yaml")
mgr = WorkspaceManager(workspaces)

# Get aggregation workspaces only
agg_workspaces = mgr.get_aggregation_workspaces()

# Get by security tag
prod_workspaces = mgr.for_security_tag("PROD")

# Filter by alias pattern
customer_workspaces = mgr.filter_by_alias("customer-*")

# Combine filters
filtered = mgr.for_report("report_incidents").for_security_tag("PROD")
```

### Pattern 4: Error Handling

```python
import asyncio
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    AuthenticationError,
    ConfigurationError
)

async def main():
    try:
        options = SentinelAggregatorClientOptions.from_environment()
        workspaces = load_workspace_config("workspaces.yaml")
        
        async with SentinelAggregatorClient(options) as client:
            summary = await client.execute_queries(workspaces)
            
    except ConfigurationError as e:
        print(f"❌ Configuration error: {e}")
        print("Check your .env file and workspaces.yaml")
        
    except AuthenticationError as e:
        print(f"❌ Authentication error: {e}")
        print("Run 'az login' or check Managed Identity")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
```

### Pattern 5: Health Monitoring

```python
async def main():
    options = SentinelAggregatorClientOptions.from_environment()
    workspaces = load_workspace_config("workspaces.yaml")
    
    async with SentinelAggregatorClient(options) as client:
        # Check health logging setup
        health_status = await client.check_health_logging(workspaces)
        
        if health_status.all_healthy:
            print("✅ All workspaces healthy")
        else:
            print(f"⚠️  Issues found in {len(health_status.unhealthy_workspaces)} workspaces")
            for ws_alias, issues in health_status.issues.items():
                print(f"   • {ws_alias}: {', '.join(issues)}")
```

## API Reference Quick Guide

### `SentinelAggregatorClientOptions`

Configuration object for the client:

```python
options = SentinelAggregatorClientOptions(
    # Time range (use one of these patterns)
    lookback_period="P7D",              # ISO 8601 duration
    # OR
    start_time=datetime(...),           # Specific start
    end_time=datetime(...),             # Specific end
    
    # Batch processing
    batch_time_size="PT24H",            # Split into 24-hour batches
    
    # DCR configuration (required for upload)
    dcr_endpoint="https://...",         # Data Collection Endpoint
    dcr_immutable_id="dcr-...",         # DCR ID
    
    # Performance tuning
    max_concurrent_queries=5,           # Parallel query limit
    
    # Logging
    log_level="INFO"                    # DEBUG, INFO, WARNING, ERROR
)
```

**Load from environment**:
```python
options = SentinelAggregatorClientOptions.from_environment()
```

**Load from YAML**:
```python
options = SentinelAggregatorClientOptions.from_yaml_file("config.yaml")
```

### `SentinelAggregatorClient`

Main client class:

```python
async with SentinelAggregatorClient(options) as client:
    # Execute queries
    summary = await client.execute_queries(
        workspaces=[...],
        dry_run=True  # Set False to upload data
    )
    
    # Check health
    health = await client.check_health_logging(workspaces)
    
    # Validate configuration
    client.validate()
```

### `WorkspaceConfig`

Workspace configuration:

```python
workspace = WorkspaceConfig(
    resource_id="/subscriptions/.../workspaces/ws-name",
    customer_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    aggregation_workspace=True,
    alias="my-workspace",  # Optional friendly name
    parameters={"row_level_security_tag": "PROD"},
    queries_list=["query_incident_summary"]
)
```

### `ExecutionSummary`

Result object from `execute_queries()`:

```python
summary = await client.execute_queries(workspaces)

# Access results
print(summary.total_records_downloaded)    # int
print(summary.total_records_uploaded)      # int
print(summary.total_successful_queries)    # int
print(summary.total_failed_queries)        # int
print(summary.total_successful_uploads)    # int
print(summary.total_duration)              # float (seconds)
print(summary.job_correlation_id)          # str (UUID)
```

## Troubleshooting SDK Usage

### Import Error
```python
# Error: ModuleNotFoundError: No module named 'sentinel_log_aggregator'
```
**Solution**:
```bash
pip install --upgrade sentinel-log-aggregator
```

### Authentication Error
```python
# Error: AuthenticationError: No credentials available
```
**Solution**:
```bash
az login
az account show  # Verify subscription
```

### Configuration Error
```python
# Error: ConfigurationError: lookback_period or start_time/end_time must be specified
```
**Solution**:
```python
options = SentinelAggregatorClientOptions(
    lookback_period="P1D"  # Add time range
)
```

### Async Runtime Error
```python
# Error: RuntimeError: asyncio.run() cannot be called from a running event loop
```
**Solution**: Use `await` if already in async context:
```python
# In Jupyter notebook or async function
summary = await client.execute_queries(workspaces)
```

## Complete Working Example

Here's a complete script you can copy and run:

```python
"""
Sentinel Log Aggregator - Complete Example
Demonstrates: configuration loading, workspace filtering, dry-run, error handling
"""
import asyncio
import logging
from pathlib import Path
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    load_workspace_config,
    WorkspaceManager,
    ConfigurationError,
    AuthenticationError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Run Sentinel log aggregation with full error handling"""
    try:
        # Step 1: Load configuration
        logger.info("Loading configuration...")
        options = SentinelAggregatorClientOptions.from_environment()
        
        # Step 2: Load and filter workspaces
        logger.info("Loading workspaces...")
        workspace_file = Path("workspaces.yaml")
        if not workspace_file.exists():
            raise FileNotFoundError(f"Workspace config not found: {workspace_file}")
        
        all_workspaces = load_workspace_config(str(workspace_file))
        logger.info(f"Loaded {len(all_workspaces)} workspaces")
        
        # Step 3: Filter workspaces (optional)
        workspace_mgr = WorkspaceManager(all_workspaces)
        incident_workspaces = workspace_mgr.for_report("report_incident_summary")
        logger.info(f"Filtered to {len(incident_workspaces)} workspaces for incident report")
        
        # Step 4: Execute queries
        logger.info("Starting query execution (dry-run)...")
        async with SentinelAggregatorClient(options) as client:
            # Validate first
            client.validate()
            logger.info("✅ Configuration validated")
            
            # Execute (dry-run)
            summary = await client.execute_queries(
                workspaces=incident_workspaces,
                dry_run=True
            )
            
            # Step 5: Display results
            logger.info("=" * 60)
            logger.info("EXECUTION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Job ID: {summary.job_correlation_id}")
            logger.info(f"Workspaces: {len(incident_workspaces)}")
            logger.info(f"Records Downloaded: {summary.total_records_downloaded:,}")
            logger.info(f"Successful Queries: {summary.total_successful_queries}")
            logger.info(f"Failed Queries: {summary.total_failed_queries}")
            logger.info(f"Duration: {summary.total_duration:.1f}s")
            logger.info("=" * 60)
            
            if summary.total_failed_queries > 0:
                logger.warning(f"⚠️  {summary.total_failed_queries} queries failed")
                return 1
            
            logger.info("✅ All queries completed successfully")
            return 0
            
    except ConfigurationError as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.error("Check your .env file and workspaces.yaml")
        return 1
        
    except AuthenticationError as e:
        logger.error(f"❌ Authentication error: {e}")
        logger.error("Run 'az login' or configure Managed Identity")
        return 1
        
    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
        return 1
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
```

## Next Steps

Now that you have the SDK basics:

1. **[Authentication Guide](authentication.md)** - Set up production authentication
2. **[SDK Reference](sdk-reference.md)** - Complete API documentation
3. **[SDK Advanced Usage](sdk-advanced.md)** - Advanced patterns and techniques
4. **[Workspace Configuration](workspace-configuration.md)** - Multi-workspace management

## Getting Help

- 📖 **[SDK Reference](sdk-reference.md)** - Complete API documentation
- 🔧 **[Troubleshooting](troubleshooting.md)** - Common issues and solutions
- 💬 **[GitHub Discussions](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/discussions)** - Ask questions
- 🐛 **[GitHub Issues](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/issues)** - Report bugs

---

**Ready for more?** Continue to [SDK Advanced Usage](sdk-advanced.md) to learn about:
- Custom query development
- Advanced workspace filtering
- Performance optimization
- Integration patterns
