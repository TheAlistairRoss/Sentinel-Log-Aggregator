# SDK Reference

Complete Python SDK API reference for Sentinel Log Aggregator.

## Table of Contents

- [Client](#client)
  - [SentinelAggregatorClient](#sentinelaggreggatorclient)
  - [SentinelAggregatorClientOptions](#sentinelaggreggatorclientoptions)
- [Data Models](#data-models)
  - [WorkspaceConfig](#workspaceconfig)
  - [KQLQueryDefinition](#kqlquerydefinition)
  - [QueryExecution](#queryexecution)
- [Response Models](#response-models)
  - [BatchExecutionResult](#batchexecutionresult)
  - [QueryResult](#queryresult)
  - [UploadResult](#uploadresult)
  - [WorkspaceQueryExecution](#workspacequeryexecution)
- [Utilities](#utilities)
  - [WorkspaceManager](#workspacemanager)
  - [load_workspace_config](#load_workspace_config)
- [Exceptions](#exceptions)
- [Enums](#enums)

---

## Client

### SentinelAggregatorClient

The main client class for executing log aggregation operations.

#### Constructor

```python
SentinelAggregatorClient(
    options: SentinelAggregatorClientOptions,
    *,
    credential: Optional[TokenCredential] = None
)
```

**Parameters**:
- `options` (`SentinelAggregatorClientOptions`): Client configuration options
- `credential` (`TokenCredential`, optional): Azure credential. If not provided, uses `DefaultAzureCredential`

**Example**:
```python
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions
)

options = SentinelAggregatorClientOptions(
    lookback_period="P1D",
    dcr_endpoint="https://YOUR-DCE.azure.com",
    dcr_immutable_id="dcr-YOUR-ID"
)

# With default credential
async with SentinelAggregatorClient(options) as client:
    ...

# With custom credential
from azure.identity import ManagedIdentityCredential
credential = ManagedIdentityCredential()
async with SentinelAggregatorClient(options, credential=credential) as client:
    ...
```

#### Methods

##### `execute_queries()`

Execute aggregation queries across workspaces.

```python
async def execute_queries(
    workspaces: list[WorkspaceConfig],
    *,
    dry_run: bool = False
) -> BatchExecutionResult
```

**Parameters**:
- `workspaces` (`list[WorkspaceConfig]`): List of workspace configurations
- `dry_run` (`bool`, optional): If True, queries execute but data is not uploaded. Default: `False`

**Returns**: `BatchExecutionResult` - Execution summary with statistics

**Raises**:
- `ConfigurationError`: Invalid configuration
- `AuthenticationError`: Authentication failed
- `QueryExecutionError`: Query execution failed
- `DataIngestionError`: Data upload failed

**Example**:
```python
workspaces = load_workspace_config("workspaces.yaml")

async with SentinelAggregatorClient(options) as client:
    # Production execution
    result = await client.execute_queries(workspaces)
    print(f"Uploaded {result.total_records_uploaded} records")
    
    # Dry-run (no upload)
    result = await client.execute_queries(workspaces, dry_run=True)
    print(f"Downloaded {result.total_records_downloaded} records")
```

##### `check_health_logging()`

Check health logging configuration for workspaces.

```python
async def check_health_logging(
    workspaces: list[WorkspaceConfig]
) -> dict
```

**Parameters**:
- `workspaces` (`list[WorkspaceConfig]`): List of workspace configurations

**Returns**: `dict` - Health status for each workspace

**Example**:
```python
async with SentinelAggregatorClient(options) as client:
    health = await client.check_health_logging(workspaces)
    
    for ws_alias, status in health.items():
        if status["healthy"]:
            print(f"✅ {ws_alias}: Healthy")
        else:
            print(f"❌ {ws_alias}: {status['issues']}")
```

##### `validate()`

Validate client configuration.

```python
def validate() -> None
```

**Raises**: `ConfigurationError` if configuration is invalid

**Example**:
```python
client = SentinelAggregatorClient(options)
try:
    client.validate()
    print("✅ Configuration valid")
except ConfigurationError as e:
    print(f"❌ Configuration error: {e}")
```

##### `close()`

Close the client and release resources.

```python
async def close() -> None
```

**Example**:
```python
client = SentinelAggregatorClient(options)
try:
    result = await client.execute_queries(workspaces)
finally:
    await client.close()

# Preferred: Use async context manager
async with SentinelAggregatorClient(options) as client:
    result = await client.execute_queries(workspaces)
```

---

### SentinelAggregatorClientOptions

Configuration options for the Sentinel Aggregator client.

#### Constructor

```python
SentinelAggregatorClientOptions(
    *,
    lookback_period: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    batch_time_size: str = "PT24H",
    max_concurrent_queries: int = 5,
    dcr_endpoint: Optional[str] = None,
    dcr_immutable_id: Optional[str] = None,
    log_level: str = "INFO"
)
```

**Parameters**:
- `lookback_period` (`str`, optional): ISO 8601 duration (e.g., "P1D", "PT12H")
- `start_time` (`datetime`, optional): Specific start time (UTC timezone required)
- `end_time` (`datetime`, optional): Specific end time (UTC timezone required)
- `batch_time_size` (`str`, optional): Batch size as ISO 8601 duration. Default: "PT24H"
- `max_concurrent_queries` (`int`, optional): Max concurrent queries. Default: 5
- `dcr_endpoint` (`str`, optional): Data Collection Endpoint URL
- `dcr_immutable_id` (`str`, optional): Data Collection Rule ID
- `log_level` (`str`, optional): Logging level. Default: "INFO"

**Time Range Requirements**:
- Must specify **either** `lookback_period` **or** both `start_time` and `end_time`
- `start_time` and `end_time` must have UTC timezone

**Examples**:

```python
from datetime import datetime, timezone
from sentinel_log_aggregator import SentinelAggregatorClientOptions

# Using lookback period
options = SentinelAggregatorClientOptions(
    lookback_period="P7D",
    batch_time_size="PT24H",
    max_concurrent_queries=5,
    dcr_endpoint="https://YOUR-DCE.azure.com",
    dcr_immutable_id="dcr-YOUR-ID"
)

# Using specific time range
options = SentinelAggregatorClientOptions(
    start_time=datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
    end_time=datetime(2025, 11, 7, 23, 59, 59, tzinfo=timezone.utc),
    batch_time_size="PT12H",
    dcr_endpoint="https://YOUR-DCE.azure.com",
    dcr_immutable_id="dcr-YOUR-ID"
)

# Minimal (for dry-run)
options = SentinelAggregatorClientOptions(
    lookback_period="P1D"
)
```

#### Class Methods

##### `from_environment()`

Create options from environment variables.

```python
@classmethod
def from_environment(cls) -> SentinelAggregatorClientOptions
```

**Environment Variables**:
- `LOOKBACK_PERIOD`: ISO 8601 duration
- `BATCH_TIME_SIZE`: ISO 8601 duration (default: "PT24H")
- `MAX_CONCURRENT_QUERIES`: Integer (default: 5)
- `DCR_ENDPOINT`: DCR endpoint URL
- `DCR_IMMUTABLE_ID`: DCR ID
- `LOG_LEVEL`: Logging level (default: "INFO")

**Example**:
```python
# .env file
# LOOKBACK_PERIOD=P1D
# DCR_ENDPOINT=https://my-dce.azure.com
# DCR_IMMUTABLE_ID=dcr-abc123

from sentinel_log_aggregator import SentinelAggregatorClientOptions

options = SentinelAggregatorClientOptions.from_environment()
```

##### `from_yaml_file()`

Create options from YAML configuration file.

```python
@classmethod
def from_yaml_file(cls, file_path: str) -> SentinelAggregatorClientOptions
```

**Parameters**:
- `file_path` (`str`): Path to YAML configuration file

**YAML Format**:
```yaml
lookback_period: P1D
batch_time_size: PT24H
max_concurrent_queries: 5
dcr_endpoint: https://YOUR-DCE.azure.com
dcr_immutable_id: dcr-YOUR-ID
log_level: INFO
```

**Example**:
```python
options = SentinelAggregatorClientOptions.from_yaml_file("config.yaml")
```

#### Methods

##### `validate()`

Validate configuration options.

```python
def validate() -> None
```

**Raises**: `ConfigurationError` if configuration is invalid

**Validation Checks**:
- Time range specified (lookback_period or start_time/end_time)
- If using start_time/end_time, both must be specified
- Batch size is valid ISO 8601 duration
- Max concurrent queries is positive integer
- DCR configuration present (if not dry-run)

**Example**:
```python
options = SentinelAggregatorClientOptions(lookback_period="P1D")
try:
    options.validate()
    print("✅ Valid")
except ConfigurationError as e:
    print(f"❌ Invalid: {e}")
```

---

## Data Models

### WorkspaceConfig

Configuration for a Sentinel workspace.

#### Constructor

```python
@dataclass
class WorkspaceConfig:
    resource_id: str
    customer_id: str
    aggregation_workspace: bool = False
    alias: Optional[str] = None
    parameters: dict = field(default_factory=dict)
    queries_list: list[str] = field(default_factory=list)
```

**Attributes**:
- `resource_id` (`str`): Azure resource ID of the workspace
  - Format: `/subscriptions/{sub}/resourcegroups/{rg}/providers/microsoft.operationalinsights/workspaces/{name}`
- `customer_id` (`str`): Workspace customer ID (GUID)
- `aggregation_workspace` (`bool`): If True, workspace receives aggregated data. Default: `False`
- `alias` (`str`, optional): Friendly name for the workspace
- `parameters` (`dict`): Query parameters (e.g., `{"row_level_security_tag": "PROD"}`)
- `queries_list` (`list[str]`): List of query names to execute

**Example**:
```python
from sentinel_log_aggregator import WorkspaceConfig

workspace = WorkspaceConfig(
    resource_id="/subscriptions/abc-123/resourcegroups/rg-sentinel/providers/microsoft.operationalinsights/workspaces/ws-prod",
    customer_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    aggregation_workspace=True,
    alias="prod-soc",
    parameters={
        "row_level_security_tag": "PROD_SOC",
        "customer_name": "Production SOC"
    },
    queries_list=[
        "query_incident_summary",
        "query_alert_summary",
        "query_workspace_usage"
    ]
)
```

**YAML Representation**:
```yaml
resource_id: /subscriptions/abc-123/resourcegroups/rg-sentinel/providers/microsoft.operationalinsights/workspaces/ws-prod
customer_id: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
aggregation_workspace: true
alias: prod-soc
parameters:
  row_level_security_tag: PROD_SOC
  customer_name: Production SOC
queries_list:
  - query_incident_summary
  - query_alert_summary
  - query_workspace_usage
```

---

### KQLQueryDefinition

Base class for KQL query definitions.

#### Constructor

```python
class KQLQueryDefinition:
    def __init__(
        self,
        name: str,
        destination_stream: str,
        description: str,
        report_name: str
    ):
        self.name = name
        self.destination_stream = destination_stream
        self.description = description
        self.report_name = report_name
        self._parameters: dict = {}
```

**Attributes**:
- `name` (`str`): Unique query identifier
- `destination_stream` (`str`): Azure Monitor stream name (e.g., "Custom-Reports_Incidents_CL")
- `description` (`str`): Human-readable description
- `report_name` (`str`): Report category identifier

#### Methods

##### `add_parameter()`

Add a query parameter definition.

```python
def add_parameter(
    self,
    name: str,
    param_type: str,
    *,
    required: bool = False,
    default: Any = None
) -> None
```

**Parameters**:
- `name` (`str`): Parameter name
- `param_type` (`str`): Parameter type ("string", "int", "bool", "datetime")
- `required` (`bool`): If True, parameter must be provided
- `default` (`Any`): Default value if not provided

##### `get_query()`

Get the KQL query string. Must be implemented by subclasses.

```python
def get_query(self) -> str
```

**Returns**: KQL query string with parameter placeholders

**Example - Custom Query**:
```python
from sentinel_log_aggregator.models import KQLQueryDefinition

class CustomThreatQuery(KQLQueryDefinition):
    def __init__(self):
        super().__init__(
            name="query_threat_intel",
            destination_stream="Custom-Reports_ThreatIntel_CL",
            description="Aggregate threat intelligence indicators",
            report_name="report_threat_intel"
        )
        
        self.add_parameter("row_level_security_tag", "string", required=False, default="")
        self.add_parameter("min_confidence", "int", required=False, default=70)
    
    def get_query(self) -> str:
        return """
        ThreatIntelligenceIndicator
        | where TimeGenerated > ago(7d)
        | where ConfidenceScore >= {min_confidence}
        | summarize 
            TotalIndicators=count(),
            UniqueTypes=dcount(ThreatType)
            by bin(TimeGenerated, 1h), ThreatType
        | extend 
            row_level_security_tag = "{row_level_security_tag}",
            processing_time = now()
        """
```

---

### QueryExecution

Execution metadata for a query.

```python
@dataclass
class QueryExecution:
    workspace_alias: str
    query_name: str
    execution_status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    records_downloaded: int = 0
    records_uploaded: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    job_correlation_id: Optional[str] = None
```

**Attributes**:
- `workspace_alias` (`str`): Workspace identifier
- `query_name` (`str`): Query name
- `execution_status` (`str`): "Completed", "Failed", "Skipped"
- `start_time` (`datetime`): Query start time
- `end_time` (`datetime`, optional): Query end time
- `records_downloaded` (`int`): Number of records retrieved
- `records_uploaded` (`int`): Number of records uploaded
- `duration_seconds` (`float`): Execution duration
- `error_message` (`str`, optional): Error message if failed
- `job_correlation_id` (`str`, optional): Correlation ID for tracking

---

## Response Models

### BatchExecutionResult

Result of a batch query execution.

```python
@dataclass
class BatchExecutionResult:
    job_correlation_id: str
    total_workspaces: int
    total_queries_executed: int
    total_successful_queries: int
    total_failed_queries: int
    total_records_downloaded: int
    total_records_uploaded: int
    total_successful_uploads: int
    total_failed_uploads: int
    total_duration: float
    batch_status: BatchStatus
    query_results: list[QueryResult]
    upload_results: list[UploadResult]
    start_time: datetime
    end_time: datetime
```

**Key Attributes**:
- `job_correlation_id` (`str`): Unique job identifier
- `total_records_uploaded` (`int`): Total records uploaded
- `total_successful_queries` (`int`): Number of successful queries
- `total_failed_queries` (`int`): Number of failed queries
- `total_duration` (`float`): Total execution time in seconds
- `batch_status` (`BatchStatus`): Overall batch status enum

**Example**:
```python
result = await client.execute_queries(workspaces)

print(f"Job ID: {result.job_correlation_id}")
print(f"Uploaded: {result.total_records_uploaded:,} records")
print(f"Success rate: {result.total_successful_queries}/{result.total_queries_executed}")
print(f"Duration: {result.total_duration:.1f}s")
print(f"Status: {result.batch_status.value}")
```

---

### QueryResult

Result of a single query execution.

```python
@dataclass
class QueryResult:
    workspace_alias: str
    query_name: str
    status: QueryStatus
    records_downloaded: int
    duration_seconds: float
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
```

**Attributes**:
- `workspace_alias` (`str`): Workspace identifier
- `query_name` (`str`): Query name
- `status` (`QueryStatus`): Query status enum
- `records_downloaded` (`int`): Records retrieved
- `duration_seconds` (`float`): Execution time
- `error_message` (`str`, optional): Error if failed

---

### UploadResult

Result of a data upload operation.

```python
@dataclass
class UploadResult:
    workspace_alias: str
    query_name: str
    status: UploadStatus
    records_uploaded: int
    duration_seconds: float
    error_message: Optional[str] = None
```

**Attributes**:
- `workspace_alias` (`str`): Workspace identifier
- `query_name` (`str`): Query name
- `status` (`UploadStatus`): Upload status enum
- `records_uploaded` (`int`): Records uploaded
- `duration_seconds` (`float`): Upload time
- `error_message` (`str`, optional): Error if failed

---

### WorkspaceQueryExecution

Execution details for a workspace query.

```python
@dataclass
class WorkspaceQueryExecution:
    workspace_alias: str
    query_name: str
    query_result: Optional[QueryResult]
    upload_result: Optional[UploadResult]
```

---

## Utilities

### WorkspaceManager

Utility class for filtering and managing workspace collections.

#### Constructor

```python
class WorkspaceManager:
    def __init__(self, workspaces: list[WorkspaceConfig]):
        self.workspaces = workspaces
```

#### Methods

##### `for_report()`

Filter workspaces by report name.

```python
def for_report(self, report_name: str) -> list[WorkspaceConfig]
```

**Example**:
```python
from sentinel_log_aggregator import WorkspaceManager

mgr = WorkspaceManager(all_workspaces)
incident_workspaces = mgr.for_report("report_incident_summary")
```

##### `for_security_tag()`

Filter workspaces by security tag.

```python
def for_security_tag(self, tag: str) -> list[WorkspaceConfig]
```

**Example**:
```python
prod_workspaces = mgr.for_security_tag("PROD")
```

##### `filter_by_alias()`

Filter workspaces by alias pattern.

```python
def filter_by_alias(self, pattern: str) -> list[WorkspaceConfig]
```

**Example**:
```python
customer_workspaces = mgr.filter_by_alias("customer-*")
```

##### `get_aggregation_workspaces()`

Get workspaces marked as aggregation targets.

```python
def get_aggregation_workspaces(self) -> list[WorkspaceConfig]
```

**Example**:
```python
agg_workspaces = mgr.get_aggregation_workspaces()
```

##### Chaining Filters

```python
filtered = (
    WorkspaceManager(all_workspaces)
    .for_report("report_incidents")
    .for_security_tag("PROD")
)
```

---

### load_workspace_config()

Load workspace configuration from YAML file.

```python
def load_workspace_config(file_path: str) -> list[WorkspaceConfig]
```

**Parameters**:
- `file_path` (`str`): Path to YAML configuration file

**Returns**: `list[WorkspaceConfig]` - List of workspace configurations

**Raises**:
- `FileNotFoundError`: Configuration file not found
- `ValueError`: Invalid YAML format or structure

**Example**:
```python
from sentinel_log_aggregator import load_workspace_config

workspaces = load_workspace_config("workspaces.yaml")
print(f"Loaded {len(workspaces)} workspaces")
```

---

## Exceptions

All exceptions inherit from `SentinelAggregatorError`.

### Exception Hierarchy

```
SentinelAggregatorError (base)
├── ConfigurationError
│   └── WorkspaceConfigurationError
├── QueryExecutionError
├── WorkspaceAccessError
├── DataIngestionError
├── BatchOperationError
└── CredentialValidationError
```

### Exception Classes

#### `SentinelAggregatorError`

Base exception for all package errors.

```python
class SentinelAggregatorError(Exception):
    """Base exception for Sentinel Aggregator"""
```

#### `ConfigurationError`

Configuration validation error.

```python
class ConfigurationError(SentinelAggregatorError):
    """Configuration is invalid"""
```

**Example**:
```python
from sentinel_log_aggregator import ConfigurationError

try:
    options = SentinelAggregatorClientOptions()
    options.validate()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

#### `QueryExecutionError`

Query execution failed.

```python
class QueryExecutionError(SentinelAggregatorError):
    """Query execution failed"""
```

#### `DataIngestionError`

Data upload to Azure Monitor failed.

```python
class DataIngestionError(SentinelAggregatorError):
    """Data ingestion failed"""
```

#### `WorkspaceAccessError`

Workspace authentication or permission error.

```python
class WorkspaceAccessError(SentinelAggregatorError):
    """Workspace access denied"""
```

---

## Enums

### QueryStatus

```python
class QueryStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
```

### UploadStatus

```python
class UploadStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
```

### BatchStatus

```python
class BatchStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
```

---

## Complete Example

```python
import asyncio
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    WorkspaceConfig,
    WorkspaceManager,
    load_workspace_config,
    ConfigurationError,
    QueryExecutionError
)

async def main():
    try:
        # Configure client
        options = SentinelAggregatorClientOptions(
            lookback_period="P1D",
            batch_time_size="PT24H",
            max_concurrent_queries=5,
            dcr_endpoint="https://YOUR-DCE.azure.com",
            dcr_immutable_id="dcr-YOUR-ID"
        )
        
        # Validate configuration
        options.validate()
        
        # Load and filter workspaces
        all_workspaces = load_workspace_config("workspaces.yaml")
        mgr = WorkspaceManager(all_workspaces)
        prod_workspaces = mgr.for_security_tag("PROD")
        
        # Execute queries
        async with SentinelAggregatorClient(options) as client:
            result = await client.execute_queries(prod_workspaces)
            
            # Display results
            print(f"Job ID: {result.job_correlation_id}")
            print(f"Uploaded: {result.total_records_uploaded:,} records")
            print(f"Success: {result.total_successful_queries}/{result.total_queries_executed}")
            print(f"Duration: {result.total_duration:.1f}s")
            
            return 0 if result.batch_status == BatchStatus.COMPLETED else 1
            
    except ConfigurationError as e:
        print(f"Configuration error: {e}")
        return 1
    except QueryExecutionError as e:
        print(f"Query execution error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
```

---

## See Also

- **[Quick Start - SDK](quickstart-sdk.md)** - Get started in 5 minutes
- **[SDK Advanced Usage](sdk-advanced.md)** - Advanced SDK patterns
- **[Authentication Guide](authentication.md)** - Set up authentication
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

---

**Need help?** Check [Troubleshooting](troubleshooting.md) or ask in [GitHub Discussions](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/discussions).
