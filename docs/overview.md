# Overview

## What is Sentinel Log Aggregator?

The **Sentinel Log Aggregator** is a production-ready Python package designed to aggregate and process logs from multiple Microsoft Sentinel workspaces into centralized reporting tables. It follows Azure SDK design patterns and provides both CLI and SDK interfaces for maximum flexibility.

### Problem Statement

Organizations with multiple Microsoft Sentinel workspaces face challenges:
- Data is siloed across different tenants/workspaces
- Cross-workspace reporting requires manual data collection
- Building unified dashboards is complex and time-consuming
- Scheduled aggregation jobs need custom development

### Solution

Sentinel Log Aggregator provides:
- **Automated data collection** from multiple workspaces
- **Parallel query execution** for performance
- **Centralized data storage** in Azure Monitor custom logs
- **Flexible configuration** via YAML, environment variables, or code
- **Production-ready** error handling and health monitoring

## Key Features

### Multi-Workspace Support
Query and aggregate data from dozens of Sentinel workspaces simultaneously with parallel execution and automatic retry logic.

### Flexible Configuration
- **YAML Files**: Define workspaces and queries in structured configuration
- **Environment Variables**: Override settings without code changes
- **Programmatic**: Full SDK control for custom integrations

### Azure SDK Compliant
- Follows Microsoft Azure SDK design patterns
- Uses `DefaultAzureCredential` for authentication
- Implements proper retry logic and error handling
- Supports Azure Monitor ingestion via Data Collection Rules (DCR)

### Production Features
- ✅ **Comprehensive Error Handling**: Detailed error messages with correlation IDs
- ✅ **Retry Logic**: Exponential backoff for transient failures
- ✅ **Health Logging**: Track execution metrics and success rates
- ✅ **Dry-Run Mode**: Test queries without uploading data
- ✅ **Debug Logging**: Detailed logging for troubleshooting
- ✅ **Concurrent Execution**: Configurable parallel query limits
- ✅ **Batch Processing**: Process large time ranges in manageable chunks

### CLI & SDK
Use as a standalone command-line tool for operations teams or integrate the SDK into your Python applications for custom workflows.

## Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    User / Automation                             │
│                           │                                       │
│          ┌───────────────┴───────────────┐                       │
│          ▼                               ▼                       │
│    ┌──────────┐                   ┌────────────┐                │
│    │   CLI    │                   │ Python SDK │                │
│    └──────────┘                   └────────────┘                │
└──────────┬──────────────────────────────┬────────────────────────┘
           │                              │
           └──────────────┬───────────────┘
                          ▼
        ┌─────────────────────────────────────────┐
        │   Sentinel Log Aggregator Package       │
        ├─────────────────────────────────────────┤
        │                                          │
        │  ┌────────────────────────────────────┐ │
        │  │  Configuration Management          │ │
        │  │  • YAML Parsing                    │ │
        │  │  • Environment Variables           │ │
        │  │  • Validation                      │ │
        │  └────────────────────────────────────┘ │
        │                │                         │
        │                ▼                         │
        │  ┌────────────────────────────────────┐ │
        │  │  Query Engine                      │ │
        │  │  • Batch Processing                │ │
        │  │  • Concurrent Execution            │ │
        │  │  • Time Range Calculation          │ │
        │  └────────────────────────────────────┘ │
        │                │                         │
        │                ▼                         │
        │  ┌────────────────────────────────────┐ │
        │  │  Azure Sentinel Client             │ │
        │  │  • Authentication                  │ │
        │  │  • Query Execution                 │ │
        │  │  • Retry Logic                     │ │
        │  └────────────────────────────────────┘ │
        │                │                         │
        └────────────────┼─────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
  ┌──────────┐   ┌──────────┐   ┌──────────┐
  │Workspace1│   │Workspace2│   │WorkspaceN│
  │  (KQL)   │   │  (KQL)   │   │  (KQL)   │
  └──────────┘   └──────────┘   └──────────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │  Data Transformation   │
            │  • Schema Mapping      │
            │  • Field Enrichment    │
            │  • Metadata Addition   │
            └────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │   Azure Monitor DCR    │
            │   • Custom Log Upload  │
            │   • Schema Validation  │
            │   • Ingestion Pipeline │
            └────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │  Centralized Tables    │
            │  • Reports             │
            │  • Dashboards          │
            │  • Analytics           │
            └────────────────────────┘
```

### Component Breakdown

#### 1. Configuration Layer
- **Workspace Manager**: Filters and manages workspace configurations
- **Query Registry**: Manages available queries and parameters
- **Client Options**: Validates and manages runtime configuration

#### 2. Execution Layer
- **Query Engine**: Orchestrates batch query execution across workspaces
- **Sentinel Client**: Wraps Azure Monitor Query SDK with retry logic
- **Health Logger**: Tracks execution metrics and success rates

#### 3. Data Layer
- **Data Transformation**: Enriches records with metadata
- **DCR Uploader**: Streams data to Azure Monitor custom logs
- **Schema Validation**: Ensures data matches target schema

## Use Cases

### 1. Centralized Security Dashboards
**Scenario**: Security Operations Center (SOC) managing 50+ customer workspaces

**Solution**: Aggregate incident data nightly into centralized tables
- Query: `incident_summary` across all workspaces
- Result: Single table with all incidents for dashboard consumption
- Benefit: Unified view of security posture across all customers

### 2. Multi-Tenant Reporting
**Scenario**: Managed Service Provider (MSP) tracking workspace usage

**Solution**: Collect usage metrics for billing and capacity planning
- Query: `workspace_usage` for resource consumption
- Result: Daily usage reports per customer
- Benefit: Accurate billing and trend analysis

### 3. Cross-Workspace Threat Intelligence
**Scenario**: Enterprise with regional Sentinel instances

**Solution**: Correlate threat indicators across all regions
- Query: Custom threat intelligence aggregation
- Result: Global view of threat landscape
- Benefit: Faster threat detection and response

### 4. Compliance Reporting
**Scenario**: Financial institution with regulatory requirements

**Solution**: Automated daily security metrics collection
- Query: Multiple queries for different compliance metrics
- Result: Timestamped compliance evidence
- Benefit: Audit-ready documentation

## Data Flow

### Query Execution Flow

```
1. Load Configuration
   ├─ Read workspaces.yaml
   ├─ Load environment variables
   └─ Validate configuration

2. Calculate Time Ranges
   ├─ Parse lookback period (e.g., P7D)
   ├─ Split into batches (e.g., PT24H)
   └─ Generate execution schedule

3. Execute Queries
   ├─ For each workspace
   │  ├─ For each query
   │  │  ├─ Build KQL with parameters
   │  │  ├─ Execute query (with retry)
   │  │  ├─ Process results
   │  │  └─ Transform data
   │  └─ Continue to next query
   └─ Continue to next workspace

4. Upload Results
   ├─ Batch records by stream
   ├─ Add metadata (timestamps, tags)
   ├─ Upload to DCR
   └─ Log success/failure

5. Generate Summary
   ├─ Count successful/failed queries
   ├─ Sum records processed
   ├─ Calculate duration
   └─ Log to health table (optional)
```

### Authentication Flow

```
1. Initialize Credential
   ├─ DefaultAzureCredential()
   │  ├─ Try Managed Identity
   │  ├─ Try Service Principal (env vars)
   │  ├─ Try Azure CLI
   │  └─ Try Interactive Browser

2. Authenticate to Services
   ├─ Azure Monitor (query workspaces)
   └─ DCR Endpoint (upload results)

3. Token Management
   ├─ Azure SDK handles renewal
   └─ Retry on auth failures
```

## System Requirements

### Platform Requirements
- **Python**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Operating System**: Windows, Linux, macOS
- **Azure SDK**: Auto-installed with package

### Azure Requirements
- **Azure Subscription**: Active subscription
- **Microsoft Sentinel**: One or more workspaces
- **Log Analytics**: Workspaces must be Log Analytics-based
- **Data Collection Rule**: For data ingestion
- **Azure Monitor**: For custom log ingestion

### Permission Requirements

#### Source Workspaces
- **Role**: Log Analytics Reader
- **Scope**: Each source workspace
- **Purpose**: Execute KQL queries

#### Target DCR/DCE
- **Role**: Monitoring Metrics Publisher
- **Scope**: Data Collection Rule
- **Purpose**: Upload aggregated data

#### (Optional) Health Logging
- **Role**: Monitoring Metrics Publisher
- **Scope**: Health logging DCR
- **Purpose**: Track execution metrics

### Network Requirements
- **Outbound HTTPS**: To Azure Monitor endpoints
- **Proxy Support**: Via Azure SDK environment variables
- **Private Endpoints**: Supported via DCR configuration

## Performance Characteristics

### Scalability
- **Workspaces**: Tested with 50+ workspaces
- **Queries per Workspace**: Up to 20 queries
- **Concurrent Execution**: Configurable (default: 5)
- **Records per Query**: Handles millions of records via streaming

### Execution Time
- **Per Query**: 1-30 seconds (depends on data volume)
- **Per Workspace**: 5-60 seconds (depends on query count)
- **Full Batch**: Minutes to hours (depends on total workspaces)

### Resource Usage
- **Memory**: ~100-500MB (streaming upload prevents memory issues)
- **CPU**: Moderate (async I/O-bound workload)
- **Network**: Proportional to data volume

## Security & Compliance

### Authentication
- Uses Azure Identity SDK (`DefaultAzureCredential`)
- Supports Managed Identity (recommended)
- No hardcoded credentials in code or configuration

### Data Protection
- TLS 1.2+ for all Azure communications
- Row-level security tags for data isolation
- Sensitive data redaction in logs

### Audit Trail
- Job correlation IDs for tracking
- Execution timestamps and duration
- Success/failure status per query
- Optional health logging to Sentinel

### Compliance Features
- Supports Azure compliance frameworks
- Audit-ready logging
- Data residency via workspace selection
- Configurable data retention

## Next Steps

Ready to get started? Continue to:

1. **[Quick Start - CLI](quickstart-cli.md)** - Run your first aggregation in 5 minutes
2. **[Quick Start - SDK](quickstart-sdk.md)** - Integrate into Python application
3. **[Authentication](authentication.md)** - Set up Azure credentials
4. **[Workspace Configuration](workspace-configuration.md)** - Configure your workspaces

For questions or support:
- 📖 [Troubleshooting Guide](troubleshooting.md)
- 💬 [GitHub Discussions](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/discussions)
- 🐛 [Report Issues](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/issues)
