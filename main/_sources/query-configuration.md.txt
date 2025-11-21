# Query Configuration Guide

Complete guide to configuring and customizing KQL queries for Sentinel Log Aggregator.

## Overview

Sentinel Log Aggregator uses YAML files to define KQL queries, making it easy to add, modify, and version control queries without changing Python code. This approach provides:

- **Easy customization** - Edit queries without rebuilding the package
- **Version control** - Track query changes independently
- **Validation** - Use KQL editors for syntax checking
- **Collaboration** - Share queries with non-Python developers
- **Flexibility** - Organize queries by security domain, compliance requirement, or operational need

## Quick Start

### 1. Create a Query YAML File

**examples/queries/my_custom_query.yaml**:
```yaml
name: "query_failed_logins"
destination_stream: "Custom-Reports_FailedLogins_CL"
description: "Track failed login attempts across all workspaces"
report_name: "report_security"

parameters:
  row_level_security_tag:
    type: "string"
    required: false
    default: ""
    description: "Workspace identifier for row-level security"
  
  threshold:
    type: "int"
    required: false
    default: 5
    description: "Minimum failed login attempts to report"

query: |
  SigninLogs
  | where TimeGenerated >= startofday(ago(1d))
  | where ResultType != "0"  // Failed logins only
  | summarize 
      FailedAttempts = count(),
      FirstAttempt = min(TimeGenerated),
      LastAttempt = max(TimeGenerated)
      by UserPrincipalName, IPAddress, AppDisplayName
  | where FailedAttempts >= {threshold}
  | extend 
      row_level_security_tag = "{row_level_security_tag}",
      report_type = "security_failed_logins"
  | order by FailedAttempts desc
```

### 2. Configure Workspace to Use Query

**workspaces.yaml**:
```yaml
workspaces:
  - resource_id: /subscriptions/abc/resourcegroups/rg/providers/microsoft.operationalinsights/workspaces/ws-prod
    customer_id: YOUR-WORKSPACE-ID
    aggregation_workspace: true
    parameters:
      row_level_security_tag: "PROD"
      threshold: 10  # Custom threshold for this workspace
    queries_list:
      - query_failed_logins  # References the query name
```

### 3. Run the Query

```bash
# CLI
sentinel-aggregator run --workspace-config workspaces.yaml

# Python SDK
from sentinel_log_aggregator import SentinelAggregatorClient, load_workspace_config

workspaces = load_workspace_config("workspaces.yaml")
async with SentinelAggregatorClient(options) as client:
    summary = await client.execute_queries(workspaces)
```

## Query YAML Structure

### Required Fields

```yaml
name: "query_unique_identifier"
  # Unique identifier for the query
  # Must start with "query_" by convention
  # Used in workspace configuration to reference this query

destination_stream: "Custom-Reports_TableName_CL"
  # Azure Monitor custom log table name
  # Must end with "_CL" for custom logs
  # Format: Custom-Reports_<YourTable>_CL

description: "Human-readable description"
  # Clear description of what the query does
  # Used in documentation and logs

report_name: "report_category"
  # Report category for grouping related queries
  # Used for filtering workspaces by report type
  # Format: report_<category>

query: |
  # Your KQL query here
  # Use {parameter_name} for substitution
```

### Optional Fields

```yaml
parameters:
  parameter_name:
    type: "string"  # string, int, float, bool
    required: false
    default: "default_value"
    description: "Parameter description"

enabled: true  # Enable/disable query without deleting it

tags:  # Optional metadata for organization
  - security
  - compliance
  
version: "1.0.0"  # Semantic versioning for the query
```

## Parameter System

### Parameter Types

| Type | Description | Example |
|------|-------------|---------|
| `string` | Text values, inserted as-is | `"PROD"`, `"customer-name"` |
| `int` | Integer numbers | `5`, `100` |
| `float` | Decimal numbers | `0.5`, `99.9` |
| `bool` | Boolean values | `true`, `false` |

### Parameter Substitution

Parameters are substituted using `{parameter_name}` syntax in the KQL query:

```yaml
parameters:
  severity_threshold:
    type: "string"
    required: true
    description: "Minimum severity level"

query: |
  SecurityIncident
  | where Severity == "{severity_threshold}"
  | summarize count() by Title
```

### Required vs Optional Parameters

**Required parameters** must be provided in workspace configuration:
```yaml
parameters:
  customer_id:
    type: "string"
    required: true  # Must be in workspace config
```

**Optional parameters** have defaults:
```yaml
parameters:
  lookback_days:
    type: "int"
    required: false
    default: 7  # Used if not specified in workspace config
```

### Standard Parameters

All queries should include these standard parameters:

```yaml
parameters:
  row_level_security_tag:
    type: "string"
    required: false
    default: ""
    description: "Workspace identifier for data isolation"
  
  customer_name:
    type: "string"
    required: false
    default: ""
    description: "Customer name for reporting"
```

## Query Organization Patterns

### By Security Domain

```
queries/
├── authentication/
│   ├── failed_logins.yaml
│   ├── mfa_failures.yaml
│   └── suspicious_logins.yaml
├── threats/
│   ├── malware_detections.yaml
│   ├── threat_intel.yaml
│   └── suspicious_processes.yaml
└── compliance/
    ├── privileged_access.yaml
    ├── data_access.yaml
    └── configuration_changes.yaml
```

### By Report Type

```
queries/
├── daily_reports/
│   ├── incident_summary.yaml
│   ├── alert_summary.yaml
│   └── workspace_usage.yaml
├── weekly_reports/
│   ├── trend_analysis.yaml
│   └── compliance_summary.yaml
└── adhoc/
    └── investigation_queries.yaml
```

### By Customer

```
queries/
├── common/
│   └── base_queries.yaml
├── customer_a/
│   └── custom_alerts.yaml
└── customer_b/
    └── custom_compliance.yaml
```

## Built-in Queries

The package includes several built-in queries:

### Incident Summary Query
```yaml
name: "query_incident_summary"
destination_stream: "Custom-Reports_IncidentSummary_CL"
description: "Aggregate incident data across workspaces"
report_name: "report_incident_summary"
```

**Use case**: Daily SOC dashboard showing incident metrics

### Alert Summary Query
```yaml
name: "query_alert_summary"
destination_stream: "Custom-Reports_AlertSummary_CL"
description: "Aggregate alert data across workspaces"
report_name: "report_alert_summary"
```

**Use case**: Alert volume trending and analysis

### Workspace Usage Query
```yaml
name: "query_workspace_usage"
destination_stream: "Custom-Reports_WorkspaceUsage_CL"
description: "Track data ingestion and workspace health"
report_name: "report_workspace_usage"
```

**Use case**: Capacity planning and cost monitoring

### Health Logging Query
```yaml
name: "query_health_log"
destination_stream: "Custom-Reports_Health_CL"
description: "Track aggregator execution health"
report_name: "report_health"
```

**Use case**: Monitor aggregator execution success/failure

## Advanced Query Patterns

### Multi-Table Joins

```yaml
name: "query_incident_with_alerts"
destination_stream: "Custom-Reports_IncidentAlerts_CL"
description: "Join incidents with related alerts"
report_name: "report_security"

query: |
  SecurityIncident
  | where TimeGenerated >= ago(1d)
  | join kind=inner (
      SecurityAlert
      | where TimeGenerated >= ago(1d)
  ) on SystemAlertId
  | project 
      TimeGenerated,
      IncidentNumber,
      Title,
      Severity,
      AlertCount = AlertIds
  | extend row_level_security_tag = "{row_level_security_tag}"
```

### Dynamic Thresholds

```yaml
name: "query_anomalous_activity"
destination_stream: "Custom-Reports_Anomalies_CL"
description: "Detect activity above baseline"
report_name: "report_security"

parameters:
  std_dev_threshold:
    type: "float"
    required: false
    default: 3.0
    description: "Standard deviations above mean"

query: |
  SecurityEvent
  | where TimeGenerated >= ago(30d)
  | summarize 
      EventCount = count(),
      AvgCount = avg(count()),
      StdDev = stdev(count())
      by bin(TimeGenerated, 1h), Account
  | where EventCount > (AvgCount + ({std_dev_threshold} * StdDev))
  | extend row_level_security_tag = "{row_level_security_tag}"
```

### Time-Based Aggregations

```yaml
name: "query_hourly_trends"
destination_stream: "Custom-Reports_Trends_CL"
description: "Hourly trend analysis"
report_name: "report_analytics"

parameters:
  bin_size:
    type: "string"
    required: false
    default: "1h"
    description: "Time bin size (1h, 6h, 1d)"

query: |
  SecurityEvent
  | where TimeGenerated >= ago(7d)
  | summarize 
      EventCount = count(),
      UniqueUsers = dcount(Account),
      UniqueComputers = dcount(Computer)
      by bin(TimeGenerated, {bin_size})
  | extend row_level_security_tag = "{row_level_security_tag}"
```

## Query Development Workflow

### 1. Design Phase

1. **Identify requirements**: What data do you need?
2. **Choose source tables**: Which Sentinel tables contain the data?
3. **Define parameters**: What should be configurable?
4. **Plan aggregations**: How should data be summarized?

### 2. Development Phase

1. **Test in Log Analytics**: Use Azure Portal to develop query
   ```kql
   // Test in Log Analytics workspace
   SecurityIncident
   | where TimeGenerated > ago(1h)
   | summarize count() by Severity
   ```

2. **Parameterize**: Replace hardcoded values with parameters
   ```kql
   // Before
   | where Severity == "High"
   
   // After
   | where Severity == "{severity_level}"
   ```

3. **Add metadata columns**: Include required fields
   ```kql
   | extend 
       row_level_security_tag = "{row_level_security_tag}",
       report_type = "security",
       processing_time = now()
   ```

### 3. Testing Phase

1. **Validate syntax**: Use KQL tools to check syntax
2. **Dry-run test**: Run with `--dry-run` flag
   ```bash
   sentinel-aggregator run --workspace-config workspaces.yaml --dry-run
   ```
3. **Check results**: Verify data structure and values

### 4. Deployment Phase

1. **Document query**: Add clear description and parameter docs
2. **Version control**: Commit query YAML to Git
3. **Configure workspaces**: Add query to workspace configs
4. **Monitor execution**: Check health logs for errors

## Query Validation

### Syntax Validation

Use Azure Portal Log Analytics to validate KQL syntax:

1. Navigate to Log Analytics workspace
2. Open "Logs" blade
3. Paste query (with parameters replaced by test values)
4. Click "Run" to validate

### Parameter Validation

Ensure all parameters are properly defined:

```bash
# Test with debug logging
sentinel-aggregator --log-level DEBUG run \
    --workspace-config workspaces.yaml \
    --dry-run
```

### Output Validation

Check that output matches expected schema:

```kql
// Query the destination table
Custom-Reports_YourTable_CL
| take 10
| getschema
```

## Query Performance Optimization

### 1. Filter Early

```kql
// Good: Filter first
SecurityEvent
| where TimeGenerated >= ago(1h)
| where EventID == 4625
| summarize count()

// Bad: Filter after summarization
SecurityEvent
| summarize count() by EventID, TimeGenerated
| where TimeGenerated >= ago(1h)
| where EventID == 4625
```

### 2. Use Summarize Efficiently

```kql
// Good: Summarize specific columns
| summarize 
    TotalEvents = count(),
    UniqueUsers = dcount(UserPrincipalName)
    by bin(TimeGenerated, 1h)

// Bad: Select all then summarize
| extend Hour = bin(TimeGenerated, 1h)
| summarize TotalEvents = count() by Hour, *
```

### 3. Limit Result Size

```kql
// Always include row limits for large datasets
| summarize count() by Category
| top 100 by count_
```

### 4. Avoid Expensive Operations

```kql
// Expensive: String operations in where clause
| where tolower(UserPrincipalName) contains "admin"

// Better: Use case-insensitive operators
| where UserPrincipalName has "admin"
```

## Troubleshooting Queries

### Query Returns No Data

**Possible causes**:
- Time range doesn't match data availability
- Filters are too restrictive
- Table doesn't exist in workspace

**Debug**:
```bash
# Enable debug logging
sentinel-aggregator --log-level DEBUG run \
    --workspace-config workspaces.yaml \
    --queries query_your_query \
    --dry-run
```

### Parameter Substitution Errors

**Error**: `Syntax error: Expected token 'EOF'`

**Cause**: Parameter not properly substituted

**Fix**: Check parameter is defined in both query YAML and workspace config

### Query Timeout

**Error**: `Query execution timeout after 300 seconds`

**Solutions**:
1. Reduce time range
2. Add more specific filters
3. Increase timeout:
   ```yaml
   # In .env
   QUERY_TIMEOUT_SECONDS=600
   ```

### Memory Issues

**Error**: `Memory limit exceeded`

**Solutions**:
1. Use smaller batch sizes:
   ```bash
   sentinel-aggregator run \
       --workspace-config workspaces.yaml \
       --batch-time-size PT6H
   ```
2. Limit result size in query:
   ```kql
   | top 10000 by TimeGenerated desc
   ```

## Example: Complete Custom Query

Here's a complete example of a production-ready custom query:

**queries/security/suspicious_signins.yaml**:
```yaml
name: "query_suspicious_signins"
destination_stream: "Custom-Reports_SuspiciousSignins_CL"
description: "Detect suspicious sign-in patterns including impossible travel, unusual locations, and multiple failures"
report_name: "report_security"
version: "1.0.0"
enabled: true

tags:
  - security
  - authentication
  - threat-detection

parameters:
  row_level_security_tag:
    type: "string"
    required: false
    default: ""
    description: "Workspace identifier for row-level security"
  
  customer_name:
    type: "string"
    required: false
    default: ""
    description: "Customer name for reporting"
  
  risk_threshold:
    type: "string"
    required: false
    default: "medium"
    description: "Minimum risk level to report (low, medium, high)"
  
  failed_login_threshold:
    type: "int"
    required: false
    default: 5
    description: "Minimum failed login attempts to flag"

query: |
  // Suspicious sign-in detection query
  let risk_level = "{risk_threshold}";
  let failed_threshold = {failed_login_threshold};
  
  // Failed login attempts
  let failed_logins = SigninLogs
  | where TimeGenerated >= ago(1d)
  | where ResultType != "0"
  | summarize 
      FailedCount = count(),
      UniqueIPs = dcount(IPAddress),
      Locations = make_set(Location)
      by UserPrincipalName
  | where FailedCount >= failed_threshold;
  
  // Risk events
  let risk_events = SigninLogs
  | where TimeGenerated >= ago(1d)
  | where RiskLevelDuringSignIn >= risk_level
  | summarize 
      RiskySignins = count(),
      RiskReasons = make_set(RiskDetail)
      by UserPrincipalName;
  
  // Combine and report
  failed_logins
  | join kind=leftouter (risk_events) on UserPrincipalName
  | extend 
      TotalRiskScore = FailedCount + (RiskySignins * 2),
      row_level_security_tag = "{row_level_security_tag}",
      customer_name = "{customer_name}",
      report_type = "security_suspicious_signins",
      processing_time = now()
  | project 
      TimeGenerated = now(),
      UserPrincipalName,
      FailedCount,
      UniqueIPs,
      Locations,
      RiskySignins,
      RiskReasons,
      TotalRiskScore,
      row_level_security_tag,
      customer_name,
      report_type,
      processing_time
  | order by TotalRiskScore desc
```

## Next Steps

- **[Workspace Configuration](workspace-configuration.md)** - Configure workspaces to use your queries
- **[CLI Reference](cli-reference.md)** - Run queries from command line
- **[SDK Reference](sdk-reference.md)** - Execute queries programmatically
- **[Troubleshooting](troubleshooting.md)** - Debug query issues

## Additional Resources

- **[KQL Reference](https://docs.microsoft.com/azure/data-explorer/kusto/query/)** - Complete KQL documentation
- **[Example Queries](../examples/queries/)** - Sample query library
- **[Query Best Practices](best-practices.md#query-optimization)** - Performance optimization tips

---

**Need help?** Check [Troubleshooting](troubleshooting.md) or ask in [GitHub Discussions](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/discussions).
