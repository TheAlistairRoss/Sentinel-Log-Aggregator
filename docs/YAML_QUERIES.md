# KQL Query Management with YAML

## Overview

The Sentinel Log Aggregator now uses YAML files to define KQL queries instead of hardcoded Python classes. This makes it much easier to:

- Add new queries without touching Python code
- Edit existing queries without rebuilding the package
- Version control queries independently
- Share queries with non-Python developers
- Validate query syntax in editors with KQL support

## Query File Structure

All query YAML files are stored in: `sentinel_log_aggregator/queries/`

### Basic YAML Structure

```yaml
name: "query_unique_name"
destination_stream: "Custom-Reports_TableName_CL"
description: "Human-readable description of what this query does"
report_name: "report_category_name"

parameters:
  parameter_name:
    type: "string|int|float|bool"
    required: true|false
    default: "default_value"  # optional
    description: "Parameter description"

query: |
  // Your KQL query here
  // Use {parameter_name} for parameter substitution
  SecurityEvent
  | where TimeGenerated >= ago(1h)
  | where Account contains "{search_term}"
  | project TimeGenerated, Account, Computer
```

## Parameter Types

- **string**: Text values (will be inserted as-is)
- **int**: Integer numbers
- **float**: Decimal numbers  
- **bool**: true/false values

## Parameter Substitution

Use `{parameter_name}` in your KQL query where you want parameters inserted:

```kql
SecurityEvent
| where TimeGenerated >= ago({hours_back}h)
| where Account == "{account_name}" or "{account_name}" == ""
| project TimeGenerated, Account, Computer
| extend RowLevelSecurityTag = "{row_level_security_tag}"
```

## Adding New Queries

1. Create a new `.yaml` file in `sentinel_log_aggregator/queries/`
2. Follow the structure above
3. The query will be automatically loaded when the package starts
4. No Python code changes needed!

## File Naming Convention

- Use descriptive names: `incident_summary.yaml`, `workspace_usage.yaml`
- Use underscores for spaces: `security_events.yaml`
- Keep names short but clear

## Example: Adding a Security Events Query

File: `sentinel_log_aggregator/queries/security_events.yaml`

```yaml
name: "query_security_events"
destination_stream: "Custom-Reports_SecurityEvents_CL"
description: "Get Windows security events for analysis"
report_name: "report_security_events"

parameters:
  row_level_security_tag:
    type: "string"
    required: false
    default: ""
    description: "Row level security tag"
  
  event_id:
    type: "string"
    required: false
    default: ""
    description: "Specific Event ID to filter (empty = all events)"
  
  hours_back:
    type: "int"
    required: false
    default: 24
    description: "Hours to look back"

query: |
  SecurityEvent
  | where TimeGenerated >= ago({hours_back}h)
  | where EventID == "{event_id}" or "{event_id}" == ""
  | project
      OriginalTimeGenerated = TimeGenerated,
      TimeGenerated = now(),
      WorkspaceId = TenantId,
      EventID,
      Computer,
      Account,
      Activity,
      SubjectUserName,
      TargetUserName,
      LogonType,
      IpAddress,
      RowLevelSecurityTag = "{row_level_security_tag}"
  | take 1000
```

## Migration from Python Classes

The old Python classes (`IncidentSummaryQuery`, `WorkspaceUsageQuery`) have been replaced with:

- `incident_summary.yaml`
- `workspace_usage.yaml`

The functionality is identical, but now much easier to maintain and extend.

## Best Practices

1. **Always include `row_level_security_tag`** parameter for data isolation
2. **Use descriptive parameter names** and descriptions
3. **Set reasonable defaults** for optional parameters
4. **Test your KQL** in Azure Monitor before adding to YAML
5. **Use meaningful destination stream names** following the pattern: `Custom-Reports_TableName_CL`
6. **Document complex queries** with comments in the KQL

## Troubleshooting

- If a query doesn't load, check the YAML syntax
- Parameter names are case-sensitive
- Required parameters must be provided when running queries
- Check the logs for YAML parsing errors on startup