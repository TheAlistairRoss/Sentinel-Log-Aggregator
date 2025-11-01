# Copilot Instructions for Sentinel Log Aggregator

## Project Overview
This is a comprehensive Microsoft Sentinel log aggregation service designed to collect, process, and aggregate logs from multiple Microsoft Sentinel workspaces into centralized reporting tables. The project has been extracted from a Jupyter notebook and refactored into a production-ready Python package.

Before you make any changes, ensure to ask clarifying questions before executing.

## Architecture Overview
The package is organized into distinct modules with clear separation of concerns:

```
sentinel_log_aggregator/
├── __init__.py           # Package exports and public API
├── config.py            # Configuration management (env vars, YAML)
├── models.py            # Data models, query definitions, execution tracking
├── azure_client.py      # Azure Monitor client with auth and retry logic
├── query_engine.py      # Core batch query execution engine
├── workspace_manager.py # Multi-workspace configuration management
├── cli.py              # Command-line interface
└── version.py          # Version information
```

## Core Architecture Patterns

### Query Execution Flow
1. **Configuration Loading**: `SentinelAggregatorConfig` from environment/YAML
2. **Workspace Management**: `WorkspaceManager` handles multi-workspace configs
3. **Azure Authentication**: `DefaultAzureCredential` with managed identity
4. **Batch Processing**: Time-based batching with configurable intervals
5. **Concurrent Execution**: Async query execution with concurrency limits
6. **Streaming Upload**: Immediate data upload to avoid memory issues
7. **Error Tracking**: Comprehensive execution logging with `QueryExecution` models

### Key Classes and Their Responsibilities
- **`SentinelQueryEngine`**: Core orchestration and batch processing
- **`AzureMonitorClient`**: Azure SDK wrapper with retry logic and authentication
- **`WorkspaceManager`/`WorkspaceSet`**: Fluent interface for workspace filtering
- **`KQLQueryDefinition`**: Base class for parameterized KQL queries
- **`WorkspaceConfig`**: Dataclass for workspace metadata and configuration

## Development Guidelines

### Coding Standards for Python
- Follow PEP 8 style guide - the codebase uses `black` and `isort` for formatting
- Use type hints extensively - all public APIs have type annotations
- Async/await patterns for I/O operations - all Azure calls are async
- Dataclasses for structured data (`@dataclass` decorator used throughout)
- Comprehensive docstrings following Google/Sphinx style
- Use `logging.getLogger(__name__)` pattern, never print statements
- Ensure that the design is aligned to Microsoft best practices found here. https://azure.github.io/azure-sdk/python_design.html

### Azure Integration Patterns (CRITICAL)
- **Authentication**: Always use `DefaultAzureCredential`, never hardcode secrets
- **Retry Logic**: Implement exponential backoff for transient failures
- **Concurrent Operations**: Respect `max_concurrent_queries` configuration
- **Resource Cleanup**: Use async context managers (`async with`) for clients
- **Error Classification**: Distinguish between retryable and non-retryable errors
- **Managed Identity**: Preferred authentication method for Azure-hosted scenarios

### Query and Data Processing Patterns
- **Parameterized Queries**: Use `{parameter_name}` placeholders in KQL strings
- **Row-Level Security**: Always include `row_level_security_tag` for data isolation
- **Batch Time Ranges**: Split large time ranges into configurable batches
- **Memory Management**: Use `gc.collect()` after processing large datasets
- **Stream Processing**: Upload data immediately after query completion
- **Metadata Enrichment**: Add processing timestamps and correlation IDs

### Error Handling and Monitoring
- **Correlation IDs**: Every job has unique `job_correlation_id` for traceability
- **Execution Tracking**: Use `QueryExecution` dataclass for detailed logging
- **Critical Error Detection**: Stop batch processing on syntax errors
- **Comprehensive Logging**: Include workspace aliases, record counts, and durations
- **Graceful Degradation**: Continue processing other queries if one fails

## File Organization Patterns

### Adding New Queries
1. Create query class inheriting from `KQLQueryDefinition` in `models.py`
2. Add to `AVAILABLE_QUERIES` registry
3. Update `REPORT_QUERIES` mapping
4. Example pattern:
```python
class NewReportQuery(KQLQueryDefinition):
    def __init__(self):
        super().__init__(
            name="query_new_report",
            destination_stream="Custom-Reports_NewReport_CL",
            description="Description of the query",
            report_name="report_new_report"
        )
        self.add_parameter("row_level_security_tag", "string", required=False, default="")
    
    def get_query(self) -> str:
        return "YOUR KQL QUERY HERE"
```

### Configuration Management
- Environment variables take precedence over file-based config
- Use `SentinelAggregatorClientOptions.from_environment()` for env-based config
- Use `SentinelAggregatorClientOptions.from_yaml_file()` for file-based config
- All configuration has validation via `validate()` method
- Workspace configs stored as YAML files, loaded via `load_workspace_config()`

### Testing Patterns
- Tests are in `tests/` directory using pytest
- Mock Azure services using `pytest-mock` for unit tests
- Use `conftest.py` for shared test fixtures
- Integration tests should use real Azure resources in test environment
- Follow naming: `test_*.py` for test files, `test_*()` for test methods

## CLI and Automation Patterns

### Command Line Interface
```bash
# Production usage
sentinel-aggregator run --workspace-config workspaces.yaml

# Development/debugging
sentinel-aggregator --log-level DEBUG run --workspace-config workspaces.yaml --days-back 1

# Configuration validation
sentinel-aggregator validate --workspace-config workspaces.yaml
```

### Programmatic Usage
```python
# Async pattern (preferred)
async with AzureMonitorClient(config) as azure_client:
    engine = SentinelQueryEngine(config, azure_client)
    summary = await engine.execute_batch_queries_with_streaming_upload(workspaces)

# Workspace filtering
workspace_mgr = WorkspaceManager(workspaces)
incident_workspaces = workspace_mgr.for_report("report_incident_summary")
```

## Security and Authentication Patterns (CRITICAL)

### Authentication Methods (in order of preference)
1. **Managed Identity** (Azure-hosted): Automatic, no configuration needed
2. **Azure CLI** (Development): `az login` for interactive development
3. **Service Principal** (CI/CD): Environment variables for automation
4. **Interactive Browser** (Jupyter): Fallback for notebook scenarios

### Required Azure Permissions
- **Log Analytics Reader** on all source workspaces
- **Monitoring Metrics Publisher** for DCR ingestion endpoint
- **DCR permissions** configured properly for your identity

### Data Security Patterns
- Use `row_level_security_tag` for workspace identification and data isolation
- Never log sensitive data (workspace IDs truncated to 8 chars in logs)
- All Azure communications use TLS 1.2+
- Implement job correlation IDs for audit trails

## Performance and Scalability Patterns

### Batch Processing
- Default 24-hour batches, configurable via `batch_hours`
- Concurrent execution limited by `max_concurrent_queries`
- Memory management with explicit garbage collection
- Early termination on critical errors (syntax errors in KQL)

### Monitoring and Observability
- Structured logging with correlation IDs
- Execution summaries with success rates and record counts
- Performance metrics (query duration, upload duration)
- Progress tracking for long-running batch operations

---

**When working on this codebase**: Always follow the async patterns, use the established error handling, and maintain the modular architecture. The code is production-ready and follows Azure best practices throughout.