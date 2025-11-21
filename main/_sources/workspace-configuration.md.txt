# Workspace Configuration Guide

Complete guide to configuring workspaces in YAML format.

## Table of Contents

- [Overview](#overview)
- [File Structure](#file-structure)
- [Workspace Properties](#workspace-properties)
- [Required Fields](#required-fields)
- [Optional Fields](#optional-fields)
- [Parameters](#parameters)
- [Multiple Workspaces](#multiple-workspaces)
- [Best Practices](#best-practices)
- [Examples](#examples)
- [Validation](#validation)

---

## Overview

The workspace configuration file defines which Microsoft Sentinel workspaces to aggregate data from, what queries to execute, and how to parameterize those queries.

**File Format**: YAML
**Default Name**: `workspaces.yaml`
**Location**: Specified via `--workspace-config` argument

---

## File Structure

### Basic Structure

```yaml
workspaces:
  - resource_id: WORKSPACE_RESOURCE_ID
    customer_id: WORKSPACE_CUSTOMER_ID
    aggregation_workspace: true|false
    alias: FRIENDLY_NAME
    parameters:
      key: value
    queries_list:
      - query_name
```

### Complete Example

```yaml
workspaces:
  - resource_id: /subscriptions/abc-123/resourcegroups/rg-prod/providers/microsoft.operationalinsights/workspaces/ws-prod-soc
    customer_id: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
    aggregation_workspace: true
    alias: prod-soc
    parameters:
      row_level_security_tag: "PROD_SOC"
      customer_name: "Production SOC"
      tier: "premium"
    queries_list:
      - query_incident_summary
      - query_alert_summary
      - query_workspace_usage
```

---

## Workspace Properties

### `resource_id` (Required)

The Azure resource ID of the Log Analytics workspace.

**Type**: String

**Format**: `/subscriptions/{subscription-id}/resourcegroups/{resource-group}/providers/microsoft.operationalinsights/workspaces/{workspace-name}`

**How to find**:
```bash
# List all workspaces
az monitor log-analytics workspace list --output table

# Get specific workspace resource ID
az monitor log-analytics workspace show \
    --resource-group YOUR-RG \
    --workspace-name YOUR-WORKSPACE \
    --query id -o tsv
```

**Example**:
```yaml
resource_id: /subscriptions/12345678-1234-1234-1234-123456789012/resourcegroups/security-prod/providers/microsoft.operationalinsights/workspaces/sentinel-prod
```

**Common Errors**:
- ❌ Missing `/subscriptions/` prefix
- ❌ Incorrect provider namespace (must be `microsoft.operationalinsights`)
- ❌ Using workspace ID instead of resource ID

---

### `customer_id` (Required)

The workspace customer ID (also called workspace ID).

**Type**: String (GUID)

**Format**: `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee`

**How to find**:
```bash
# Get workspace customer ID
az monitor log-analytics workspace show \
    --resource-group YOUR-RG \
    --workspace-name YOUR-WORKSPACE \
    --query customerId -o tsv
```

**Example**:
```yaml
customer_id: 87654321-4321-4321-4321-210987654321
```

**Common Errors**:
- ❌ Using workspace resource ID instead of customer ID
- ❌ Invalid GUID format
- ❌ Missing dashes in GUID

---

### `aggregation_workspace` (Optional)

Indicates if this workspace receives aggregated data.

**Type**: Boolean

**Default**: `false`

**Purpose**:
- If `true`: Workspace receives uploaded aggregated data AND health logs
- If `false`: Workspace is queried but does not receive uploads

**Example**:
```yaml
# Central aggregation workspace
- resource_id: /subscriptions/.../workspaces/central-reports
  customer_id: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
  aggregation_workspace: true
  queries_list:
    - query_health_log  # Health logging enabled
    - query_incident_summary

# Source workspace (no uploads)
- resource_id: /subscriptions/.../workspaces/customer-a
  customer_id: bbbbbbbb-bbbb-cccc-dddd-eeeeeeeeeeee
  aggregation_workspace: false
  queries_list:
    - query_incident_summary
```

**Use Cases**:
- **True**: Central reporting workspace, SOC dashboard workspace
- **False**: Customer workspaces, source workspaces

---

### `alias` (Optional)

Friendly name for the workspace.

**Type**: String

**Purpose**: Used in logs, reports, and error messages instead of workspace ID

**Example**:
```yaml
alias: prod-soc
```

**Best Practices**:
- Use lowercase with hyphens
- Keep it short and descriptive
- Make it unique across all workspaces
- Use consistent naming patterns

**Naming Patterns**:
```yaml
# Environment-based
alias: prod-soc
alias: dev-soc
alias: test-soc

# Customer-based
alias: customer-acme
alias: customer-beta

# Region-based
alias: us-east-soc
alias: eu-west-soc
```

---

### `parameters` (Optional)

Key-value pairs passed to queries.

**Type**: Dictionary

**Purpose**: Customize query behavior per workspace

**Common Parameters**:
- `row_level_security_tag`: Workspace identifier in aggregated data
- `customer_name`: Customer display name
- `environment`: Environment type (prod, dev, test)
- `region`: Geographic region
- `tier`: Service tier (premium, standard, basic)

**Example**:
```yaml
parameters:
  row_level_security_tag: "PROD_SOC"
  customer_name: "Acme Corporation"
  environment: "production"
  region: "us-east"
  tier: "premium"
  compliance_framework: "SOX"
```

**Parameter Types**:
```yaml
parameters:
  # Strings
  row_level_security_tag: "PROD"
  customer_name: "Acme Corp"
  
  # Numbers
  min_severity: 3
  max_results: 1000
  
  # Booleans
  include_false_positives: false
  enable_enrichment: true
  
  # Lists (as comma-separated strings in queries)
  alert_types: "Malware,Phishing,Ransomware"
```

---

### `queries_list` (Required)

List of queries to execute for this workspace.

**Type**: List of strings

**Format**: Query names from the registry

**Available Queries**:
- `query_incident_summary`
- `query_alert_summary`
- `query_workspace_usage`
- `query_health_log`
- Custom queries (see Query YAML Configuration)

**Example**:
```yaml
queries_list:
  - query_incident_summary
  - query_alert_summary
  - query_workspace_usage
```

**Query Selection Strategies**:

**1. All Workspaces Get Same Queries**:
```yaml
workspaces:
  - resource_id: /subscriptions/.../ws-1
    customer_id: id-1
    queries_list:
      - query_incident_summary
      - query_alert_summary
  
  - resource_id: /subscriptions/.../ws-2
    customer_id: id-2
    queries_list:
      - query_incident_summary
      - query_alert_summary
```

**2. Different Queries Per Workspace Type**:
```yaml
workspaces:
  # SOC workspace - all queries
  - resource_id: /subscriptions/.../ws-soc
    customer_id: id-soc
    aggregation_workspace: true
    queries_list:
      - query_incident_summary
      - query_alert_summary
      - query_workspace_usage
      - query_health_log
  
  # Customer workspace - limited queries
  - resource_id: /subscriptions/.../ws-customer
    customer_id: id-customer
    queries_list:
      - query_incident_summary
```

**3. Tier-Based Query Selection**:
```yaml
workspaces:
  # Premium tier - all reports
  - resource_id: /subscriptions/.../ws-premium
    customer_id: id-premium
    parameters:
      tier: "premium"
    queries_list:
      - query_incident_summary
      - query_alert_summary
      - query_threat_intelligence
      - query_compliance_report
  
  # Standard tier - basic reports
  - resource_id: /subscriptions/.../ws-standard
    customer_id: id-standard
    parameters:
      tier: "standard"
    queries_list:
      - query_incident_summary
      - query_alert_summary
```

---

## Parameters

### Standard Parameters

#### `row_level_security_tag`

**Purpose**: Identify data source in aggregated tables

**Type**: String

**Required**: Recommended for all workspaces

**Usage in Queries**:
```kql
SecurityIncident
| where TimeGenerated > ago(7d)
| summarize IncidentCount=count()
| extend row_level_security_tag = "{row_level_security_tag}"
```

**Example Values**:
```yaml
# Environment-based
row_level_security_tag: "PROD"
row_level_security_tag: "DEV"

# Customer-based
row_level_security_tag: "CUSTOMER_ACME"
row_level_security_tag: "CUSTOMER_BETA"

# Combined
row_level_security_tag: "PROD_CUSTOMER_ACME"
```

#### Custom Parameters

Define your own parameters for query customization:

```yaml
workspaces:
  - resource_id: /subscriptions/.../ws-1
    customer_id: id-1
    parameters:
      # Custom threshold
      high_severity_threshold: 7
      
      # Custom time window
      lookback_days: 30
      
      # Custom filtering
      include_test_data: false
      
      # Custom enrichment
      enrich_with_threat_intel: true
    queries_list:
      - query_custom_report
```

**Use in Custom Queries**:
```kql
SecurityIncident
| where TimeGenerated > ago({lookback_days}d)
| where Severity >= {high_severity_threshold}
| extend include_test = tobool("{include_test_data}")
| where not(include_test) or IncidentName !contains "TEST"
```

---

## Multiple Workspaces

### Pattern 1: Multiple Customers

```yaml
workspaces:
  # Central aggregation workspace
  - resource_id: /subscriptions/.../ws-central-reports
    customer_id: central-id
    aggregation_workspace: true
    alias: central-reports
    parameters:
      row_level_security_tag: "CENTRAL"
    queries_list:
      - query_health_log
  
  # Customer A
  - resource_id: /subscriptions/.../ws-customer-a
    customer_id: customer-a-id
    alias: customer-a
    parameters:
      row_level_security_tag: "CUSTOMER_A"
      customer_name: "Acme Corporation"
      tier: "premium"
    queries_list:
      - query_incident_summary
      - query_alert_summary
  
  # Customer B
  - resource_id: /subscriptions/.../ws-customer-b
    customer_id: customer-b-id
    alias: customer-b
    parameters:
      row_level_security_tag: "CUSTOMER_B"
      customer_name: "Beta Industries"
      tier: "standard"
    queries_list:
      - query_incident_summary
```

### Pattern 2: Multi-Region

```yaml
workspaces:
  # US East Region
  - resource_id: /subscriptions/.../ws-us-east
    customer_id: us-east-id
    alias: us-east-soc
    parameters:
      row_level_security_tag: "US_EAST"
      region: "us-east"
      timezone: "America/New_York"
    queries_list:
      - query_incident_summary
      - query_alert_summary
  
  # EU West Region
  - resource_id: /subscriptions/.../ws-eu-west
    customer_id: eu-west-id
    alias: eu-west-soc
    parameters:
      row_level_security_tag: "EU_WEST"
      region: "eu-west"
      timezone: "Europe/London"
      compliance_framework: "GDPR"
    queries_list:
      - query_incident_summary
      - query_alert_summary
      - query_compliance_report
```

### Pattern 3: Environment Separation

```yaml
workspaces:
  # Production
  - resource_id: /subscriptions/.../ws-prod
    customer_id: prod-id
    alias: prod-soc
    aggregation_workspace: true
    parameters:
      row_level_security_tag: "PROD"
      environment: "production"
    queries_list:
      - query_incident_summary
      - query_alert_summary
      - query_workspace_usage
      - query_health_log
  
  # Development
  - resource_id: /subscriptions/.../ws-dev
    customer_id: dev-id
    alias: dev-soc
    parameters:
      row_level_security_tag: "DEV"
      environment: "development"
    queries_list:
      - query_incident_summary
```

---

## Best Practices

### 1. Use Meaningful Aliases

```yaml
# ✅ Good
alias: prod-customer-acme
alias: dev-soc-us-east

# ❌ Bad
alias: ws1
alias: workspace
```

### 2. Always Set `row_level_security_tag`

```yaml
# ✅ Good - every workspace has unique tag
parameters:
  row_level_security_tag: "PROD_CUSTOMER_A"

# ❌ Bad - missing or duplicate tags
parameters: {}
```

### 3. Separate Configuration Files by Environment

```
workspaces-production.yaml
workspaces-development.yaml
workspaces-test.yaml
```

### 4. Document Custom Parameters

```yaml
parameters:
  # Security tag for row-level filtering
  row_level_security_tag: "PROD"
  
  # Customer display name for reports
  customer_name: "Acme Corporation"
  
  # Minimum severity level (1-10)
  min_severity: 5
```

### 5. Use Consistent Naming Conventions

```yaml
# Environment prefix pattern
alias: prod-customer-acme
alias: prod-customer-beta
alias: dev-customer-acme

# Region prefix pattern
alias: us-east-acme
alias: eu-west-acme
```

### 6. Group Related Workspaces

```yaml
workspaces:
  # ===== PRODUCTION ENVIRONMENTS =====
  - resource_id: /subscriptions/.../ws-prod-soc
    ...
  
  - resource_id: /subscriptions/.../ws-prod-customer-a
    ...
  
  # ===== DEVELOPMENT ENVIRONMENTS =====
  - resource_id: /subscriptions/.../ws-dev-soc
    ...
```

---

## Examples

### Example 1: Simple Single Workspace

```yaml
workspaces:
  - resource_id: /subscriptions/abc-123/resourcegroups/rg-sentinel/providers/microsoft.operationalinsights/workspaces/ws-prod
    customer_id: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
    aggregation_workspace: true
    parameters:
      row_level_security_tag: "PROD"
    queries_list:
      - query_incident_summary
```

### Example 2: MSP with Multiple Customers

```yaml
workspaces:
  # MSP Central Reporting
  - resource_id: /subscriptions/sub-msp/resourcegroups/rg-reports/providers/microsoft.operationalinsights/workspaces/ws-msp-reports
    customer_id: msp-reports-id
    aggregation_workspace: true
    alias: msp-reports
    parameters:
      row_level_security_tag: "MSP_REPORTS"
    queries_list:
      - query_health_log
  
  # Customer A - Premium Tier
  - resource_id: /subscriptions/sub-a/resourcegroups/rg-security/providers/microsoft.operationalinsights/workspaces/ws-acme
    customer_id: acme-id
    alias: customer-acme
    parameters:
      row_level_security_tag: "CUSTOMER_ACME"
      customer_name: "Acme Corporation"
      tier: "premium"
      contact_email: "security@acme.com"
    queries_list:
      - query_incident_summary
      - query_alert_summary
      - query_workspace_usage
  
  # Customer B - Standard Tier
  - resource_id: /subscriptions/sub-b/resourcegroups/rg-security/providers/microsoft.operationalinsights/workspaces/ws-beta
    customer_id: beta-id
    alias: customer-beta
    parameters:
      row_level_security_tag: "CUSTOMER_BETA"
      customer_name: "Beta Industries"
      tier: "standard"
      contact_email: "it@beta.com"
    queries_list:
      - query_incident_summary
```

### Example 3: Multi-Region Global SOC

```yaml
workspaces:
  # Global Aggregation
  - resource_id: /subscriptions/sub-global/resourcegroups/rg-global/providers/microsoft.operationalinsights/workspaces/ws-global-soc
    customer_id: global-soc-id
    aggregation_workspace: true
    alias: global-soc
    parameters:
      row_level_security_tag: "GLOBAL_SOC"
    queries_list:
      - query_health_log
  
  # Americas Region
  - resource_id: /subscriptions/sub-amer/resourcegroups/rg-amer/providers/microsoft.operationalinsights/workspaces/ws-americas
    customer_id: americas-id
    alias: soc-americas
    parameters:
      row_level_security_tag: "AMERICAS"
      region: "americas"
      timezone: "America/New_York"
    queries_list:
      - query_incident_summary
      - query_alert_summary
  
  # EMEA Region
  - resource_id: /subscriptions/sub-emea/resourcegroups/rg-emea/providers/microsoft.operationalinsights/workspaces/ws-emea
    customer_id: emea-id
    alias: soc-emea
    parameters:
      row_level_security_tag: "EMEA"
      region: "emea"
      timezone: "Europe/London"
      compliance_framework: "GDPR"
    queries_list:
      - query_incident_summary
      - query_alert_summary
      - query_compliance_report
  
  # APAC Region
  - resource_id: /subscriptions/sub-apac/resourcegroups/rg-apac/providers/microsoft.operationalinsights/workspaces/ws-apac
    customer_id: apac-id
    alias: soc-apac
    parameters:
      row_level_security_tag: "APAC"
      region: "apac"
      timezone: "Asia/Tokyo"
    queries_list:
      - query_incident_summary
      - query_alert_summary
```

---

## Validation

### Using CLI

```bash
# Validate configuration file
sentinel-aggregator validate --workspace-config workspaces.yaml
```

**Valid Output**:
```
✅ Client options validation successful
✅ Workspace configuration validation successful
```

**Invalid Output**:
```
❌ Configuration validation failed:
   • Missing required field: customer_id in workspace 'prod-soc'
   • Invalid resource_id format in workspace 'test-workspace'
```

### Validation Checklist

- ✅ All required fields present (`resource_id`, `customer_id`, `queries_list`)
- ✅ Resource ID has correct format
- ✅ Customer ID is valid GUID
- ✅ Query names exist in registry
- ✅ Aliases are unique
- ✅ YAML syntax is valid
- ✅ Parameters are properly formatted

---

## See Also

- **[Query Configuration](query-configuration.md)** - Configure custom queries
- **[CLI Reference](cli-reference.md)** - Command-line usage
- **[SDK Reference](sdk-reference.md)** - Programmatic usage
- **[Environment Variables](environment-variables.md)** - Environment configuration

---

**Need help?** Check [Troubleshooting](troubleshooting.md) or ask in [GitHub Discussions](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/discussions).
