# Example Workspace Configuration with Relative Query Paths

This example demonstrates the new flexible query organization using relative file paths.

## Directory Structure

```
examples/
├── workspaces-example.yaml          # This configuration file
├── queries/
│   ├── security/
│   │   └── incident_trends.yaml     # Security incident analysis
│   └── compliance/
│       └── audit_report.yaml        # Compliance audit reporting
```

## Configuration File: workspaces-example.yaml

```yaml
# Microsoft Sentinel Workspaces Configuration
# Demonstrates flexible query organization with relative paths

metadata:
  version: "2.0"
  description: "Example workspace configuration with organized query structure"
  last_updated: "2025-11-03"
  environment: "example"

workspaces:
  # Production Security Operations Center
  - resource_id: "/subscriptions/12345678-1234-1234-1234-123456789012/resourcegroups/security-rg/providers/microsoft.operationalinsights/workspaces/prod-soc-sentinel"
    customer_id: "87654321-4321-4321-4321-210987654321"
    queries_list:
      # Security team queries - organized in security/ directory
      - "queries/security/incident_trends.yaml"
      
      # Compliance queries - organized in compliance/ directory  
      - "queries/compliance/audit_report.yaml"
    parameters:
      row_level_security_tag: "prod-soc"
      environment: "production"
      region: "east-us"
      compliance_framework: "SOX"
  
  # Development Environment
  - resource_id: "/subscriptions/12345678-1234-1234-1234-123456789012/resourcegroups/dev-rg/providers/microsoft.operationalinsights/workspaces/dev-sentinel"
    customer_id: "11111111-2222-3333-4444-555555555555"
    queries_list:
      # Use same queries but with different parameters
      - "queries/security/incident_trends.yaml"
    parameters:
      row_level_security_tag: "dev"
      environment: "development"
      region: "west-us"
      # Different time window for development
      time_window_days: 7
  
  # European Operations (GDPR Compliance)
  - resource_id: "/subscriptions/12345678-1234-1234-1234-123456789012/resourcegroups/eu-rg/providers/microsoft.operationalinsights/workspaces/eu-sentinel"
    customer_id: "22222222-3333-4444-5555-666666666666"
    queries_list:
      - "queries/security/incident_trends.yaml"
      - "queries/compliance/audit_report.yaml"
    parameters:
      row_level_security_tag: "eu-ops"
      environment: "production"
      region: "north-europe"
      compliance_framework: "GDPR"
      data_residency: "eu"
```

## Key Benefits of This Organization

### 1. **Clear Structure**
- Queries are organized by functional area (security, compliance)
- Easy to locate and maintain specific query types
- Supports team-based development workflows

### 2. **Flexible Configuration**
- Same queries can be used across multiple workspaces
- Different parameters per workspace (time windows, compliance frameworks)
- Environment-specific customization

### 3. **Scalable Organization**
- Add new query categories by creating new directories
- Organize by team, function, compliance requirement, or any other criteria
- No hardcoded assumptions about query locations

### 4. **Backward Compatibility**
- Mix relative paths with legacy query names if needed
- Gradual migration from old to new format
- No breaking changes for existing configurations

## Usage Examples

### CLI Usage
```bash
# Run with this example configuration
sentinel-aggregator run --workspace-config examples/workspaces-example.yaml

# Validate the configuration
sentinel-aggregator validate --workspace-config examples/workspaces-example.yaml

# Run with debug logging to see query loading
sentinel-aggregator --log-level DEBUG run --workspace-config examples/workspaces-example.yaml
```

### Programmatic Usage
```python
from sentinel_log_aggregator import WorkspaceManager
from pathlib import Path

# Load the example configuration
manager = WorkspaceManager.from_file("examples/workspaces-example.yaml")

# Filter workspaces by environment
prod_workspaces = manager.filter_by_parameter("environment", "production")
print(f"Production workspaces: {len(prod_workspaces.workspaces)}")

# Get all unique queries across workspaces
unique_queries = manager.unique_reports()
print(f"Unique queries: {unique_queries}")
```

## Migration from Legacy Format

If you have existing configurations using query names, you can migrate gradually:

```yaml
workspaces:
  - resource_id: "/subscriptions/.../workspaces/hybrid"
    customer_id: "your-workspace-id"
    queries_list:
      # Legacy format (still supported)
      - "query_legacy_report"
      
      # New format with relative paths
      - "queries/security/incident_trends.yaml"
      - "queries/compliance/audit_report.yaml"
    parameters:
      row_level_security_tag: "hybrid"
```

This mixed approach allows you to:
1. Keep existing queries working while migrating
2. Organize new queries using the flexible structure
3. Gradually move legacy queries to the new format
4. Test the new organization before full migration