# Health Logging Infrastructure Deployment Guide

This guide explains how to deploy the health logging infrastructure for the Sentinel Log Aggregator using the provided Bicep template.

## Overview

The health logging system captures operational metrics and execution status for the Sentinel Log Aggregator service. It creates:

- Custom Log Analytics table (`SentinelAggregator-Health_CL`) for health data
- Data Collection Rule (DCR) for secure log ingestion
- Stream definition for structured health data

## Prerequisites

Before deploying the health logging infrastructure, ensure you have:

1. **Azure CLI installed and authenticated**
   ```bash
   az login
   az account set --subscription <your-subscription-id>
   ```

2. **Required permissions in your Azure subscription:**
   - `Contributor` or `Owner` role on the resource group
   - `Log Analytics Contributor` role on the Log Analytics workspace

3. **Existing Log Analytics workspace** where Sentinel data is stored

## Deployment Steps

### 1. Navigate to Template Directory

```bash
cd c:\Repos\Sentinel-Log-Aggregator
```

### 2. Deploy Using Azure CLI

Replace the parameter values with your specific environment details:

```bash
az deployment group create \
  --resource-group <your-resource-group> \
  --template-file Templates/main.bicep \
  --parameters workspaceName=<your-log-analytics-workspace-name>
```

**Example:**
```bash
az deployment group create \
  --resource-group rg-sentinel-prod \
  --template-file Templates/main.bicep \
  --parameters workspaceName=law-sentinel-prod
```

### 3. Verify Deployment

The deployment will output important configuration values:

```json
{
  "dcrEndpoint": {
    "type": "String",
    "value": "https://dcr-sentinel-health-xyz.eastus-1.ingest.monitor.azure.com"
  },
  "dcrRuleId": {
    "type": "String",
    "value": "dcr-abcd1234-5678-90ef-ghij-klmnopqrstuv"
  },
  "healthTableName": {
    "type": "String",
    "value": "SentinelAggregator-Health_CL"
  }
}
```

**Save these output values** - you'll need them for configuring the health logging client.

## Configuration

### 1. Update Environment Variables

Add the deployment outputs to your environment configuration:

```bash
# Environment variables (.env file or system environment)
HEALTH_DCR_ENDPOINT=https://dcr-sentinel-health-xyz.eastus-1.ingest.monitor.azure.com
HEALTH_DCR_RULE_ID=dcr-abcd1234-5678-90ef-ghij-klmnopqrstuv
HEALTH_WORKSPACE_ID=<your-workspace-customer-id>
```

### 2. Update YAML Configuration (Alternative)

Or add to your configuration YAML file:

```yaml
# config.yaml
health_logging:
  enabled: true
  dcr_endpoint: "https://dcr-sentinel-health-xyz.eastus-1.ingest.monitor.azure.com"
  dcr_rule_id: "dcr-abcd1234-5678-90ef-ghij-klmnopqrstuv"
  workspace_id: "<your-workspace-customer-id>"
```

## Verification

### 1. Test Health Logging Setup

Use the CLI verification command to test your setup:

```bash
sentinel-aggregator verify-health --workspace-config workspaces.yaml --enable-health-logging
```

This command will:
- ✅ Verify the health table exists
- ✅ Test DCR accessibility 
- ✅ Validate permissions
- ✅ Confirm end-to-end connectivity

### 2. Expected Output

```
🏥 Verifying health logging setup...
🔍 Using first workspace for testing: MyWorkspace
📊 Health Logging Verification Results:
==================================================
  • Enabled: ✅
  • Table Exists: ✅  
  • DCR Accessible: ✅
  • Status: Health logging is fully operational

🎉 Health logging is fully operational!
```

## Usage

### 1. Enable Health Logging in Production

```bash
# Run aggregation with health logging enabled
sentinel-aggregator run \
  --workspace-config workspaces.yaml \
  --enable-health-logging \
  --days-back 7
```

### 2. Monitor Health Data

Query the health table in your Log Analytics workspace:

```kql
SentinelAggregator-Health_CL
| where TimeGenerated > ago(1h)
| order by TimeGenerated desc
```

## Troubleshooting

### Common Issues

1. **"Health table not found"**
   - Verify deployment completed successfully
   - Check Log Analytics workspace name in deployment
   - Ensure sufficient time has passed for table creation (up to 15 minutes)

2. **"DCR access failed"** 
   - Verify DCR endpoint and rule ID from deployment outputs
   - Check managed identity or service principal permissions
   - Ensure DCR is in the same region as your Log Analytics workspace

3. **"Health logging verification failed"**
   - Check Azure authentication (`az login`)
   - Verify workspace configuration file path
   - Enable debug logging: `--log-level DEBUG`

### Debug Mode

Run verification with detailed logging:

```bash
sentinel-aggregator --log-level DEBUG verify-health \
  --workspace-config workspaces.yaml \
  --enable-health-logging
```

## Advanced Configuration

### Custom DCR Parameters

If you need custom DCR settings, you can provide additional parameters during deployment:

```bash
az deployment group create \
  --resource-group <your-resource-group> \
  --template-file Templates/main.bicep \
  --parameters workspaceName=<workspace-name> \
               dcrName=<custom-dcr-name> \
               location=<specific-region>
```

### Multiple Environments

For multiple environments (dev/staging/prod), deploy separate DCRs:

```bash
# Development environment
az deployment group create \
  --resource-group rg-sentinel-dev \
  --template-file Templates/main.bicep \
  --parameters workspaceName=law-sentinel-dev

# Production environment  
az deployment group create \
  --resource-group rg-sentinel-prod \
  --template-file Templates/main.bicep \
  --parameters workspaceName=law-sentinel-prod
```

## Security Considerations

- **Managed Identity**: The health logging system uses Azure Managed Identity for authentication when deployed to Azure
- **Least Privilege**: The DCR only grants write access to the specific health table
- **Data Isolation**: Health data is tagged with `row_level_security_tag` for workspace identification
- **Encryption**: All data is encrypted in transit and at rest using Azure standards

## Next Steps

After successful deployment:

1. **Enable health logging** in your scheduled aggregation jobs
2. **Set up monitoring alerts** on health data for operational issues
3. **Create dashboards** in Azure Monitor or Sentinel for health visualization
4. **Configure retention policies** for health data based on your requirements

For more information, see:
- [CLI Usage Guide](cli-usage.md)
- [Configuration Guide](configuration.md)
- [Security Implementation](security-implementation.md)