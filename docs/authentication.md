# Authentication Guide

Complete guide to authenticating Sentinel Log Aggregator with Azure.

## Overview

Sentinel Log Aggregator uses **Azure Identity** for authentication, supporting multiple credential types through `DefaultAzureCredential`. This provides a seamless authentication experience across development, testing, and production environments.

## Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│ DefaultAzureCredential (tries in order)                     │
├─────────────────────────────────────────────────────────────┤
│ 1. Environment Variables (Service Principal)                │
│ 2. Managed Identity (Azure-hosted)                          │
│ 3. Azure CLI (Development)                                  │
│ 4. Azure PowerShell (Alternative development)               │
│ 5. Interactive Browser (Last resort)                        │
└─────────────────────────────────────────────────────────────┘
```

The tool automatically tries each method until one succeeds.

## Development Authentication

### Option 1: Azure CLI (Recommended for Development)

**Best for**: Local development, testing, Jupyter notebooks

```bash
# Login interactively
az login

# Verify authentication
az account show

# Set specific subscription
az account set --subscription "Your-Subscription-Name"
```

**Python example**:
```python
from sentinel_log_aggregator import SentinelAggregatorClient

# No additional configuration needed
async with SentinelAggregatorClient(options) as client:
    summary = await client.execute_queries(workspaces)
```

**CLI example**:
```bash
sentinel-aggregator run --workspace-config workspaces.yaml
```

✅ **Automatic**: Uses your Azure CLI session credentials

### Option 2: Azure PowerShell

**Best for**: PowerShell users

```powershell
# Connect to Azure
Connect-AzAccount

# Verify authentication
Get-AzContext

# Set specific subscription
Set-AzContext -Subscription "Your-Subscription-Name"
```

Works the same way as Azure CLI - no additional configuration needed.

### Option 3: Visual Studio Code

**Best for**: VS Code development

1. Install Azure Account extension
2. Sign in through VS Code (Ctrl+Shift+P → "Azure: Sign In")
3. Authentication is automatic

## Production Authentication

### Option 1: Managed Identity (Recommended for Production)

**Best for**: Azure Functions, Azure Container Instances, Azure VMs, Azure App Service

#### System-Assigned Managed Identity

**Setup**:
```bash
# Enable on Azure Function
az functionapp identity assign \
    --name YOUR-FUNCTION-APP \
    --resource-group YOUR-RG

# Enable on VM
az vm identity assign \
    --name YOUR-VM \
    --resource-group YOUR-RG

# Enable on Container Instance
az container create \
    --name YOUR-CONTAINER \
    --resource-group YOUR-RG \
    --assign-identity
```

**Grant Permissions**:
```bash
# Get the principal ID
PRINCIPAL_ID=$(az functionapp identity show \
    --name YOUR-FUNCTION-APP \
    --resource-group YOUR-RG \
    --query principalId -o tsv)

# Grant Log Analytics Reader on workspace
az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Log Analytics Reader" \
    --scope /subscriptions/YOUR-SUB/resourceGroups/YOUR-RG/providers/Microsoft.OperationalInsights/workspaces/YOUR-WS

# Grant Monitoring Metrics Publisher for DCR
az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Monitoring Metrics Publisher" \
    --scope /subscriptions/YOUR-SUB/resourceGroups/YOUR-RG/providers/Microsoft.Insights/dataCollectionRules/YOUR-DCR
```

**Python code** (no changes needed):
```python
# Works automatically in Azure-hosted environment
async with SentinelAggregatorClient(options) as client:
    summary = await client.execute_queries(workspaces)
```

**CLI** (no changes needed):
```bash
sentinel-aggregator run --workspace-config workspaces.yaml
```

✅ **Automatic**: Detects Managed Identity in Azure environment

#### User-Assigned Managed Identity

**Setup**:
```bash
# Create managed identity
az identity create \
    --name sentinel-aggregator-identity \
    --resource-group YOUR-RG

# Get client ID
CLIENT_ID=$(az identity show \
    --name sentinel-aggregator-identity \
    --resource-group YOUR-RG \
    --query clientId -o tsv)

# Assign to Function App
az functionapp identity assign \
    --name YOUR-FUNCTION-APP \
    --resource-group YOUR-RG \
    --identities /subscriptions/YOUR-SUB/resourceGroups/YOUR-RG/providers/Microsoft.ManagedIdentity/userAssignedIdentities/sentinel-aggregator-identity
```

**Specify in environment**:
```bash
AZURE_CLIENT_ID=YOUR-USER-ASSIGNED-MANAGED-IDENTITY-CLIENT-ID
```

### Option 2: Service Principal (CI/CD)

**Best for**: GitHub Actions, Azure DevOps, automation scripts

#### Create Service Principal

```bash
# Create service principal
az ad sp create-for-rbac \
    --name sentinel-aggregator-sp \
    --role "Log Analytics Reader" \
    --scopes /subscriptions/YOUR-SUB/resourceGroups/YOUR-RG

# Output (save these securely):
# {
#   "appId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
#   "displayName": "sentinel-aggregator-sp",
#   "password": "your-secret-password",
#   "tenant": "ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj"
# }
```

#### Configure Environment Variables

**Linux/macOS**:
```bash
export AZURE_CLIENT_ID="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
export AZURE_CLIENT_SECRET="your-secret-password"
export AZURE_TENANT_ID="ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj"
```

**Windows (PowerShell)**:
```powershell
$env:AZURE_CLIENT_ID="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
$env:AZURE_CLIENT_SECRET="your-secret-password"
$env:AZURE_TENANT_ID="ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj"
```

**Windows (Command Prompt)**:
```cmd
set AZURE_CLIENT_ID=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
set AZURE_CLIENT_SECRET=your-secret-password
set AZURE_TENANT_ID=ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj
```

**.env file**:
```bash
AZURE_CLIENT_ID=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
AZURE_CLIENT_SECRET=your-secret-password
AZURE_TENANT_ID=ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj
```

**Python usage**:
```python
from sentinel_log_aggregator import SentinelAggregatorClient

# Automatically uses environment variables
async with SentinelAggregatorClient(options) as client:
    summary = await client.execute_queries(workspaces)
```

**CLI usage**:
```bash
sentinel-aggregator --env-file .env run --workspace-config workspaces.yaml
```

#### GitHub Actions Example

```yaml
name: Run Sentinel Aggregator

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC

jobs:
  aggregate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install package
        run: pip install sentinel-log-aggregator
      
      - name: Run aggregation
        env:
          AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
          AZURE_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
          AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
          DCR_ENDPOINT: ${{ secrets.DCR_ENDPOINT }}
          DCR_IMMUTABLE_ID: ${{ secrets.DCR_IMMUTABLE_ID }}
        run: |
          sentinel-aggregator run \
            --workspace-config workspaces.yaml \
            --lookback-period P1D
```

#### Azure DevOps Pipeline Example

```yaml
trigger:
  - main

schedules:
  - cron: "0 2 * * *"
    displayName: Daily 2 AM run
    branches:
      include:
        - main

pool:
  vmImage: 'ubuntu-latest'

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.11'
  
  - script: |
      pip install sentinel-log-aggregator
    displayName: 'Install package'
  
  - task: AzureCLI@2
    inputs:
      azureSubscription: 'YOUR-SERVICE-CONNECTION'
      scriptType: 'bash'
      scriptLocation: 'inlineScript'
      inlineScript: |
        sentinel-aggregator run \
          --workspace-config workspaces.yaml \
          --lookback-period P1D
    displayName: 'Run aggregation'
    env:
      DCR_ENDPOINT: $(DCR_ENDPOINT)
      DCR_IMMUTABLE_ID: $(DCR_IMMUTABLE_ID)
```

## Required Azure Permissions

### Minimum Permissions

| Resource | Role | Purpose |
|----------|------|---------|
| **Source Workspaces** | Log Analytics Reader | Query logs from Sentinel workspaces |
| **Data Collection Rule** | Monitoring Metrics Publisher | Upload aggregated data |
| **DCR Association** | (Configured in DCR) | Link DCR to destination workspace |

### Grant Permissions Script

```bash
#!/bin/bash
# Grant all required permissions

PRINCIPAL_ID="YOUR-MANAGED-IDENTITY-OR-SP-OBJECT-ID"
SUBSCRIPTION="YOUR-SUBSCRIPTION-ID"

# Grant Log Analytics Reader on all source workspaces
for WORKSPACE in workspace1 workspace2 workspace3; do
    az role assignment create \
        --assignee $PRINCIPAL_ID \
        --role "Log Analytics Reader" \
        --scope "/subscriptions/$SUBSCRIPTION/resourceGroups/rg-sentinel/providers/Microsoft.OperationalInsights/workspaces/$WORKSPACE"
done

# Grant Monitoring Metrics Publisher for DCR
az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Monitoring Metrics Publisher" \
    --scope "/subscriptions/$SUBSCRIPTION/resourceGroups/rg-dcr/providers/Microsoft.Insights/dataCollectionRules/dcr-sentinel-aggregator"

echo "✅ Permissions granted"
```

### Verify Permissions

```bash
# Check role assignments for a principal
az role assignment list \
    --assignee YOUR-PRINCIPAL-ID \
    --output table

# Check if specific permission exists
az role assignment list \
    --assignee YOUR-PRINCIPAL-ID \
    --scope /subscriptions/YOUR-SUB/resourceGroups/YOUR-RG/providers/Microsoft.OperationalInsights/workspaces/YOUR-WS \
    --query "[?roleDefinitionName=='Log Analytics Reader']" \
    --output table
```

## Authentication Patterns by Environment

### Local Development

```python
# Uses Azure CLI credentials automatically
import asyncio
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    load_workspace_config
)

async def main():
    options = SentinelAggregatorClientOptions.from_environment()
    workspaces = load_workspace_config("workspaces.yaml")
    
    async with SentinelAggregatorClient(options) as client:
        summary = await client.execute_queries(workspaces, dry_run=True)

if __name__ == "__main__":
    asyncio.run(main())
```

**Prerequisites**:
- Run `az login` first
- No environment variables needed

### Azure Function

```python
import azure.functions as func
import asyncio
from sentinel_log_aggregator import (
    SentinelAggregatorClient,
    SentinelAggregatorClientOptions,
    load_workspace_config
)

async def main(mytimer: func.TimerRequest) -> None:
    # Uses Managed Identity automatically
    options = SentinelAggregatorClientOptions(
        lookback_period="P1D",
        dcr_endpoint=os.environ["DCR_ENDPOINT"],
        dcr_immutable_id=os.environ["DCR_IMMUTABLE_ID"]
    )
    
    workspaces = load_workspace_config("workspaces.yaml")
    
    async with SentinelAggregatorClient(options) as client:
        summary = await client.execute_queries(workspaces)
        
    logging.info(f"✅ Uploaded {summary.total_records_uploaded} records")
```

**Prerequisites**:
- System-Assigned Managed Identity enabled
- Permissions granted to Managed Identity
- DCR endpoint configured in app settings

### Docker Container

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY workspaces.yaml .
COPY main.py .

CMD ["python", "main.py"]
```

**Run with Service Principal**:
```bash
docker run \
    -e AZURE_CLIENT_ID=$AZURE_CLIENT_ID \
    -e AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
    -e AZURE_TENANT_ID=$AZURE_TENANT_ID \
    -e DCR_ENDPOINT=$DCR_ENDPOINT \
    -e DCR_IMMUTABLE_ID=$DCR_IMMUTABLE_ID \
    sentinel-aggregator:latest
```

**Run with Managed Identity** (Azure Container Instances):
```bash
az container create \
    --name sentinel-aggregator \
    --resource-group YOUR-RG \
    --image YOUR-REGISTRY/sentinel-aggregator:latest \
    --assign-identity \
    --environment-variables \
        DCR_ENDPOINT=$DCR_ENDPOINT \
        DCR_IMMUTABLE_ID=$DCR_IMMUTABLE_ID
```

### Kubernetes

**Deployment with Azure AD Workload Identity**:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: sentinel-aggregator
  annotations:
    azure.workload.identity/client-id: YOUR-USER-ASSIGNED-IDENTITY-CLIENT-ID
---
apiVersion: apps/v1
kind: CronJob
metadata:
  name: sentinel-aggregator
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        metadata:
          labels:
            azure.workload.identity/use: "true"
        spec:
          serviceAccountName: sentinel-aggregator
          containers:
            - name: aggregator
              image: YOUR-REGISTRY/sentinel-aggregator:latest
              env:
                - name: DCR_ENDPOINT
                  valueFrom:
                    secretKeyRef:
                      name: sentinel-config
                      key: dcr-endpoint
                - name: DCR_IMMUTABLE_ID
                  valueFrom:
                    secretKeyRef:
                      name: sentinel-config
                      key: dcr-id
```

## Troubleshooting Authentication

### Error: "No credentials available"

**Cause**: No authentication method found

**Solutions**:
```bash
# For local development
az login

# For production (check environment variables)
echo $AZURE_CLIENT_ID
echo $AZURE_TENANT_ID
# (Don't echo AZURE_CLIENT_SECRET in production!)

# For Azure-hosted (verify Managed Identity)
az functionapp identity show --name YOUR-FUNCTION --resource-group YOUR-RG
```

### Error: "Insufficient permissions"

**Cause**: Missing required role assignments

**Solution**:
```bash
# Check current permissions
az role assignment list --assignee YOUR-PRINCIPAL-ID --output table

# Grant Log Analytics Reader
az role assignment create \
    --assignee YOUR-PRINCIPAL-ID \
    --role "Log Analytics Reader" \
    --scope /subscriptions/YOUR-SUB/resourceGroups/YOUR-RG/providers/Microsoft.OperationalInsights/workspaces/YOUR-WS

# Grant Monitoring Metrics Publisher
az role assignment create \
    --assignee YOUR-PRINCIPAL-ID \
    --role "Monitoring Metrics Publisher" \
    --scope /subscriptions/YOUR-SUB/resourceGroups/YOUR-RG/providers/Microsoft.Insights/dataCollectionRules/YOUR-DCR
```

### Error: "Invalid tenant"

**Cause**: Wrong tenant ID specified

**Solution**:
```bash
# Get correct tenant ID
az account show --query tenantId -o tsv

# Set correct tenant
export AZURE_TENANT_ID="YOUR-CORRECT-TENANT-ID"
```

### Error: "Client secret expired"

**Cause**: Service Principal secret has expired

**Solution**:
```bash
# Create new secret
az ad sp credential reset \
    --id YOUR-APP-ID \
    --append  # Keeps existing credentials valid

# Update environment variable with new secret
export AZURE_CLIENT_SECRET="new-secret-value"
```

## Security Best Practices

### ✅ DO

- **Use Managed Identity** for Azure-hosted applications
- **Rotate Service Principal secrets** regularly (90 days recommended)
- **Use Azure Key Vault** to store secrets
- **Grant least-privilege access** (only required roles)
- **Use separate identities** per environment (dev/test/prod)
- **Enable audit logging** on role assignments
- **Use User-Assigned Managed Identity** for shared scenarios

### ❌ DON'T

- **Don't commit credentials** to version control
- **Don't share Service Principals** across teams
- **Don't use long-lived secrets** (prefer Managed Identity)
- **Don't grant broad permissions** (avoid Contributor role)
- **Don't log credentials** in application logs
- **Don't use production credentials** in development

## Next Steps

- 📖 **[CLI Reference](cli-reference.md)** - Complete CLI command documentation
- 📖 **[SDK Reference](sdk-reference.md)** - Complete API documentation
- 🔧 **[Troubleshooting](troubleshooting.md)** - Authentication troubleshooting
- 🏗️ **[Workspace Configuration](workspace-configuration.md)** - Configure workspaces

---

**Need help?** Check [Troubleshooting](troubleshooting.md) or ask in [GitHub Discussions](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/discussions).
