# Query Setup and Configuration

This guide covers how to set up, organize, and configure queries for the Microsoft Sentinel Log Aggregator.

## Query Organization

The Sentinel Log Aggregator supports flexible query organization. You can structure your queries in any directory layout that suits your needs.

### Recommended Directory Structures

#### Option 1: By Query Type
```
project-root/
├── queries/
│   ├── incidents/
│   │   ├── incident_summary.yaml
│   │   └── incident_trends.yaml
│   ├── users/
│   │   ├── user_activity.yaml
│   │   └── user_summary.yaml
│   └── security/
│       ├── security_alerts.yaml
│       └── threat_detection.yaml
```

#### Option 2: By Environment
```
project-root/
├── queries/
│   ├── production/
│   │   ├── critical_alerts.yaml
│   │   └── compliance_reports.yaml
│   ├── development/
│   │   ├── test_queries.yaml
│   │   └── debug_queries.yaml
│   └── shared/
│       ├── common_metrics.yaml
│       └── baseline_reports.yaml
```

#### Option 3: By Team/Department
```
project-root/
├── queries/
│   ├── security-team/
│   │   ├── threat_hunting.yaml
│   │   └── incident_response.yaml
│   ├── compliance/
│   │   ├── audit_reports.yaml
│   │   └── regulatory_checks.yaml
│   └── operations/
│       ├── system_health.yaml
│       └── performance_metrics.yaml
```

## Query File Format

Query files are written in YAML format and contain the KQL query along with metadata and parameters.

### Basic Query Structure

```yaml
name: "query_incident_summary"
destination_stream: "Custom-Reports_IncidentDetails_CL"
stream_name: "stream_incident_summary"
description: "Query to extract incident summary data from Sentinel workspaces"
version: "1.0"
tags: ["incidents", "summary", "security"]

parameters:
  row_level_security_tag:
    type: "string"
    required: false
    default: ""
    description: "Workspace identifier for data isolation"
  
  days_back:
    type: "int"
    required: false
    default: 30
    description: "Number of days to look back for data"

query: |
  SecurityIncident
  | where TimeGenerated > ago({days_back}d)
  | join kind=inner SecurityAlert on $left.AlertIds == $right.SystemAlertId
  | summarize 
      IncidentCount = count(),
      OpenIncidents = countif(Status == "New" or Status == "Active"),
      ClosedIncidents = countif(Status == "Closed"),
      HighSeverityIncidents = countif(Severity == "High")
      by bin(TimeGenerated, 1d)
  | extend WorkspaceTag = "{row_level_security_tag}"
  | order by TimeGenerated desc
```

### Query File Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | Unique identifier for the query |
| `destination_stream` | ✅ | Target stream for data ingestion |
| `description` | ✅ | Human-readable description of the query |
| `query` | ✅ | The KQL query string |
| `stream_name` | ❌ | Custom stream name (defaults to destination_stream) |
| `version` | ❌ | Query version for tracking changes |
| `tags` | ❌ | List of tags for categorization |
| `parameters` | ❌ | Query parameters with types and defaults |

### Parameter Types

Parameters support the following types:
- `string`: Text values
- `int`: Integer numbers
- `double`: Decimal numbers
- `bool`: Boolean values (true/false)
- `datetime`: Date and time values

### Parameter Substitution

Parameters are substituted in the query using `{parameter_name}` syntax:

```yaml
parameters:
  workspace_tag:
    type: "string"
    required: true
    description: "Environment tag for this workspace"
  
  time_range:
    type: "int"
    default: 24
    description: "Time range in hours"

query: |
  SecurityEvent
  | where TimeGenerated > ago({time_range}h)
  | extend Environment = "{workspace_tag}"
  | summarize count() by Computer, Environment
```

## Workspace Configuration

Configure which queries each workspace should execute using the `queries_list` field.

### Using Query Names (Legacy)

```yaml
workspaces:
  - resource_id: "/subscriptions/.../workspaces/prod-sentinel"
    customer_id: "12345678-1234-1234-1234-123456789012"
    queries_list:
      - "query_incident_summary"
      - "query_user_activity"
    parameters:
      row_level_security_tag: "production"
```

### Using Relative File Paths (Recommended)

```yaml
workspaces:
  - resource_id: "/subscriptions/.../workspaces/prod-sentinel"
    customer_id: "12345678-1234-1234-1234-123456789012"
    queries_list:
      - "queries/incidents/incident_summary.yaml"
      - "queries/users/user_activity.yaml"
      - "queries/security/threat_detection.yaml"
    parameters:
      row_level_security_tag: "production"
  
  - resource_id: "/subscriptions/.../workspaces/dev-sentinel"
    customer_id: "87654321-4321-4321-4321-210987654321"
    queries_list:
      - "queries/development/test_queries.yaml"
      - "queries/shared/baseline_reports.yaml"
    parameters:
      row_level_security_tag: "development"
```

### Mixed Configuration (Backward Compatibility)

You can mix query names and file paths in the same configuration:

```yaml
workspaces:
  - resource_id: "/subscriptions/.../workspaces/hybrid-sentinel"
    customer_id: "11111111-1111-1111-1111-111111111111"
    queries_list:
      - "query_legacy_report"  # Query name (legacy)
      - "queries/new/advanced_analytics.yaml"  # File path (new)
      - "custom_reports/executive_summary.yaml"  # Custom organization
    parameters:
      row_level_security_tag: "hybrid"
```

## Loading Queries

### Programmatic Loading

```python
from sentinel_log_aggregator.query_registry import QueryRegistry
from pathlib import Path

# Create registry
registry = QueryRegistry()

# Load from directory (recursive)
registry.load_queries_from_directory(Path("queries"), recursive=True)

# Load specific query file
query = registry.load_query_from_path(
    "queries/incidents/incident_summary.yaml",
    base_directory=Path(".")
)

# Get loaded query
incident_query = registry.get_query("query_incident_summary")
```

### CLI Loading

The CLI automatically loads queries based on workspace configuration:

```bash
# Queries are loaded automatically when running
sentinel-aggregator run --workspace-config workspaces.yaml

# Validate queries and workspace configuration
sentinel-aggregator validate --workspace-config workspaces.yaml
```

## Query Development Best Practices

### 1. Use Descriptive Names

```yaml
# Good
name: "query_failed_login_attempts_by_user"

# Avoid
name: "query1"
```

### 2. Include Comprehensive Parameters

```yaml
parameters:
  # Always include row-level security for multi-workspace environments
  row_level_security_tag:
    type: "string"
    required: false
    default: ""
    description: "Workspace identifier for data isolation"
  
  # Make time ranges configurable
  time_window_hours:
    type: "int"
    required: false
    default: 24
    description: "Time window in hours for the analysis"
  
  # Include relevant filters
  severity_filter:
    type: "string"
    required: false
    default: "High,Critical"
    description: "Comma-separated list of severity levels to include"
```

### 3. Add Meaningful Metadata

```yaml
name: "query_insider_threat_detection"
description: "Detects potential insider threat activities based on user behavior patterns"
version: "2.1"
tags: ["security", "insider-threat", "user-behavior", "anomaly-detection"]
```

### 4. Use Efficient KQL

```yaml
query: |
  // Use efficient time filtering first
  SecurityEvent
  | where TimeGenerated > ago({time_window_hours}h)
  | where EventID in (4624, 4625)  // Specific event filtering
  
  // Join efficiently
  | join kind=inner (
      IdentityInfo
      | where TimeGenerated > ago({time_window_hours}h)
  ) on $left.Account == $right.AccountName
  
  // Aggregate and summarize
  | summarize 
      LoginAttempts = count(),
      FailedLogins = countif(EventID == 4625),
      UniqueComputers = dcount(Computer)
      by Account, bin(TimeGenerated, 1h)
  
  // Add workspace tagging
  | extend WorkspaceTag = "{row_level_security_tag}"
```

### 5. Test Queries Thoroughly

```bash
# Test query syntax and execution
sentinel-aggregator validate --workspace-config workspaces.yaml

# Run with limited time range for testing
sentinel-aggregator run --workspace-config workspaces.yaml --days-back 1
```

## Advanced Configuration

### Custom Query Loaders

```python
from sentinel_log_aggregator import SentinelAggregatorClient, QueryRegistry
from pathlib import Path

# Custom query loading logic
def load_custom_queries(registry: QueryRegistry, config: dict):
    """Custom query loading with environment-specific logic."""
    
    environment = config.get('environment', 'production')
    
    if environment == 'production':
        # Load production queries
        registry.load_queries_from_directory(Path("queries/production"))
    else:
        # Load development queries
        registry.load_queries_from_directory(Path("queries/development"))
        registry.load_queries_from_directory(Path("queries/shared"))

# Use with client
async with SentinelAggregatorClient(endpoint, credential) as client:
    registry = QueryRegistry()
    load_custom_queries(registry, {'environment': 'production'})
    
    # Execute queries
    for query_name in registry.list_queries():
        query = registry.get_query(query_name)
        # ... execute query
```

### Query Validation

```python
from sentinel_log_aggregator.query_registry import QueryRegistry

registry = QueryRegistry()
registry.load_queries_from_directory(Path("queries"))

# Validate all queries
validation_results = registry.validate_all_queries()

for query_name, issues in validation_results.items():
    if issues:
        print(f"Query {query_name} has issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print(f"Query {query_name} is valid")
```

## Migration from Legacy Format

If you're migrating from the legacy query name format to file paths:

### Step 1: Organize Query Files

Move your queries into a logical directory structure:

```bash
mkdir -p queries/reports queries/security queries/compliance
mv query_incident_summary.yaml queries/reports/
mv query_security_alerts.yaml queries/security/
mv query_compliance_check.yaml queries/compliance/
```

### Step 2: Update Workspace Configuration

Change from query names to file paths:

```yaml
# Before (legacy)
queries_list:
  - "query_incident_summary"
  - "query_security_alerts"

# After (recommended)
queries_list:
  - "queries/reports/incident_summary.yaml"
  - "queries/security/security_alerts.yaml"
```

### Step 3: Test Configuration

```bash
# Validate the updated configuration
sentinel-aggregator validate --workspace-config workspaces.yaml

# Test with limited scope
sentinel-aggregator run --workspace-config workspaces.yaml --days-back 1
```

## Troubleshooting

### Common Issues

1. **Query Not Found**
   ```
   Error: Query 'my_query' not found
   ```
   - Check the file path in your workspace configuration
   - Ensure the query file exists and is readable
   - Verify the query name matches the `name` field in the YAML file

2. **Parameter Substitution Fails**
   ```
   Error: Parameter 'workspace_tag' not found
   ```
   - Check parameter spelling in the query
   - Ensure parameters are defined in the workspace configuration
   - Verify parameter types match expected values

3. **KQL Syntax Errors**
   ```
   Error: Invalid KQL syntax
   ```
   - Test your KQL in Azure Data Explorer or Sentinel
   - Check for unescaped special characters
   - Ensure proper parameter substitution syntax

### Debug Mode

Enable debug logging for detailed query loading information:

```bash
sentinel-aggregator --log-level DEBUG run --workspace-config workspaces.yaml
```

This will show:
- Which queries are being loaded
- Parameter substitution details
- Query execution information
- Error details with full stack traces