# Example Queries

This directory contains sample KQL queries for the Sentinel Log Aggregator. These queries demonstrate how to structure your own query files and can be used as starting points for your custom queries.

## Included Examples

### Security Queries (`security/`)

- **`incident_trends.yaml`**: Analyzes incident patterns and trends over time
  - Provides insights into incident volume, severity distribution, and resolution times
  - Useful for security operations teams to identify patterns

### Compliance Queries (`compliance/`)

- **`audit_report.yaml`**: Generates compliance audit reports
  - Tracks audit events and compliance-related activities
  - Suitable for regulatory reporting and compliance monitoring

## Using These Examples

### Option 1: Copy to Your Project

1. Copy the query files to your project directory:
   ```
   cp -r examples/queries/* your-project/queries/
   ```

2. Update your workspace configuration to reference the queries:
   ```yaml
   workspaces:
     - resource_id: "your-workspace-id"
       customer_id: "your-customer-id"
       queries_list:
         - "queries/security/incident_trends.yaml"
         - "queries/compliance/audit_report.yaml"
   ```

### Option 2: Reference Directly

You can reference these example queries directly in your workspace configuration:

```yaml
workspaces:
  - resource_id: "your-workspace-id" 
    customer_id: "your-customer-id"
    queries_list:
      - "examples/queries/security/incident_trends.yaml"
      - "examples/queries/compliance/audit_report.yaml"
```

## Customizing Queries

Each query file includes:

- **Parameters**: Configurable values that can be set per workspace
- **KQL Query**: The actual Kusto query with parameter placeholders
- **Metadata**: Description, destination stream, and report categorization

To customize:

1. Copy the query file to your project
2. Modify the KQL query logic as needed
3. Adjust parameters to match your requirements
4. Update the description and metadata

## Next Steps

- Review the [Query Setup Guide](../docs/query-setup.md) for detailed query configuration
- See [YAML Queries Documentation](../docs/YAML_QUERIES.md) for query file structure
- Check [Workspace Configuration Examples](workspaces-example.yaml) for more configuration patterns

## Support

For questions about query development:
- Review the [Troubleshooting Guide](../docs/troubleshooting.md)
- See [Best Practices](../docs/best-practices.md)
- Check the [Installation Guide](../docs/installation.md)