# Quick Start - CLI

Get started with Sentinel Log Aggregator CLI in 5 minutes.

## Prerequisites

- Python 3.8 or later installed
- Azure CLI installed and authenticated (`az login`)
- Access to at least one Microsoft Sentinel workspace

## Step 1: Install the Package

```bash
pip install sentinel-log-aggregator
```

Verify installation:
```bash
sentinel-aggregator --version
```

## Step 2: Set Up Authentication

The easiest way to start is using Azure CLI authentication:

```bash
# Login to Azure
az login

# Set your subscription
az account set --subscription "Your-Subscription-Name"
```

✅ **That's it!** The tool will use your Azure CLI credentials automatically.

## Step 3: Create Workspace Configuration

Create a file named `workspaces.yaml`:

```yaml
workspaces:
  - resource_id: /subscriptions/YOUR-SUB-ID/resourcegroups/YOUR-RG/providers/microsoft.operationalinsights/workspaces/YOUR-WORKSPACE
    customer_id: YOUR-WORKSPACE-CUSTOMER-ID
    aggregation_workspace: true
    parameters:
      row_level_security_tag: "PROD"
    queries_list:
      - query_incident_summary
```

**How to find these values:**

```bash
# List your workspaces
az monitor log-analytics workspace list --output table

# Get workspace details
az monitor log-analytics workspace show \
    --resource-group YOUR-RG \
    --workspace-name YOUR-WORKSPACE
```

## Step 4: Run Your First Query (Dry-Run)

Test without uploading data:

```bash
sentinel-aggregator run \
    --workspace-config workspaces.yaml \
    --lookback-period P1D \
    --dry-run
```

**Expected Output:**
```
2025-11-07 10:00:00 | INFO | 🚀 Starting log aggregation process...
2025-11-07 10:00:00 | INFO |   • Lookback period: P1D
2025-11-07 10:00:00 | INFO |   • Workspaces: 1
2025-11-07 10:00:05 | INFO | ✅ Batch execution complete
2025-11-07 10:00:05 | INFO |   • Records Downloaded: 45
2025-11-07 10:00:05 | INFO |   • Duration: 5.2s
```

✅ **Success!** You've executed your first query.

## Step 5: Validate Configuration

Before running in production, validate your setup:

```bash
sentinel-aggregator validate --workspace-config workspaces.yaml
```

**Expected Output:**
```
✅ Client options validation successful
✅ Workspace configuration validation successful
```

## Common Commands

### Check Health Logging Setup
```bash
sentinel-aggregator health --workspace-config workspaces.yaml
```

### Run with Different Time Range
```bash
# Last 7 days
sentinel-aggregator run --workspace-config workspaces.yaml --lookback-period P7D --dry-run

# Specific date range
sentinel-aggregator run \
    --workspace-config workspaces.yaml \
    --start-time 2025-11-01T00:00:00Z \
    --end-time 2025-11-07T00:00:00Z \
    --dry-run
```

### Enable Debug Logging
```bash
sentinel-aggregator --log-level DEBUG run \
    --workspace-config workspaces.yaml \
    --lookback-period P1D \
    --dry-run
```

## Step 6: Production Run (Upload Data)

Once you're confident, remove `--dry-run` and configure DCR:

### Option A: Use Environment Variables

Create `.env` file:
```bash
DCR_ENDPOINT=https://YOUR-DCR-ENDPOINT.azure.com
DCR_IMMUTABLE_ID=dcr-YOUR-DCR-ID
```

Run with environment file:
```bash
sentinel-aggregator --env-file .env run --workspace-config workspaces.yaml
```

### Option B: Use Command-Line Arguments

```bash
sentinel-aggregator run \
    --workspace-config workspaces.yaml \
    --dcr-endpoint https://YOUR-DCR-ENDPOINT.azure.com \
    --dcr-immutable-id dcr-YOUR-DCR-ID \
    --lookback-period P1D
```

**Expected Output:**
```
2025-11-07 10:00:00 | INFO | 🚀 Starting log aggregation process...
2025-11-07 10:00:05 | INFO | [BATCH_END] Queries: 4/4 | Uploads: 4/4 | Records: 45 uploaded
2025-11-07 10:00:05 | INFO | ✅ Batch execution complete
```

## Troubleshooting Quick Start

### Error: "No such command 'sentinel-aggregator'"
**Solution**: Ensure package is installed:
```bash
pip install --upgrade sentinel-log-aggregator
```

### Error: "Authentication failed"
**Solution**: Login to Azure:
```bash
az login
az account show  # Verify correct subscription
```

### Error: "Workspace not found"
**Solution**: Verify workspace IDs:
```bash
az monitor log-analytics workspace list --output table
```

### Error: "Permission denied"
**Solution**: Ensure you have "Log Analytics Reader" role:
```bash
az role assignment list --scope /subscriptions/YOUR-SUB-ID/resourceGroups/YOUR-RG/providers/Microsoft.OperationalInsights/workspaces/YOUR-WORKSPACE
```

### Queries Return No Data
**Causes**:
- Workspace has no data in the lookback period
- Query is filtering too strictly
- Time zone differences

**Debug**:
```bash
# Check if workspace has data
az monitor log-analytics query \
    --workspace YOUR-WORKSPACE-ID \
    --analytics-query "SecurityIncident | take 10"
```

## Next Steps

Now that you have the basics working:

1. **[Authentication Guide](authentication.md)** - Set up Managed Identity for production
2. **[Workspace Configuration](workspace-configuration.md)** - Configure multiple workspaces
3. **[CLI Reference](cli-reference.md)** - Explore all CLI options
4. **[CLI Advanced Usage](cli-advanced.md)** - Learn advanced patterns

### Production Checklist

Before going to production:

- ✅ Set up Managed Identity authentication
- ✅ Configure Data Collection Rule (DCR)
- ✅ Test with `--dry-run` first
- ✅ Enable health logging
- ✅ Schedule with Azure Functions or GitHub Actions
- ✅ Set up monitoring and alerts
- ✅ Document workspace-to-customer mappings

## Example: Complete Workflow

Here's a complete example from setup to production:

### 1. Install and Authenticate
```bash
pip install sentinel-log-aggregator
az login
```

### 2. Create Configuration Files

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
DCR_ENDPOINT=https://my-dce-abc123.azure.com
DCR_IMMUTABLE_ID=dcr-abcdef1234567890
LOOKBACK_PERIOD=P1D
BATCH_TIME_SIZE=PT24H
MAX_CONCURRENT_QUERIES=5
```

### 3. Test Configuration
```bash
sentinel-aggregator validate --workspace-config workspaces.yaml
sentinel-aggregator health --workspace-config workspaces.yaml
```

### 4. Dry Run
```bash
sentinel-aggregator --env-file .env run \
    --workspace-config workspaces.yaml \
    --dry-run
```

### 5. Production Run
```bash
sentinel-aggregator --env-file .env run \
    --workspace-config workspaces.yaml
```

### 6. Schedule (Cron Example)
```bash
# Run daily at 2 AM
0 2 * * * cd /opt/sentinel && /usr/local/bin/sentinel-aggregator --env-file .env run --workspace-config workspaces.yaml >> /var/log/sentinel-aggregator.log 2>&1
```

## Getting Help

- 📖 **[CLI Reference](cli-reference.md)** - Complete command documentation
- 🔧 **[Troubleshooting](troubleshooting.md)** - Common issues and solutions
- 💬 **[GitHub Discussions](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/discussions)** - Ask questions
- 🐛 **[GitHub Issues](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/issues)** - Report bugs

---

**Ready for more?** Continue to [CLI Advanced Usage](cli-advanced.md) to learn about:
- Multiple workspace management
- Custom query development
- Health logging and monitoring
- Automation patterns
