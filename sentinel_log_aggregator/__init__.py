"""
Microsoft Sentinel Log Aggregator

An Azure SDK-compliant Python client library for aggregating and processing logs from multiple 
Microsoft Sentinel workspaces into centralized reporting tables for security analytics and 
dashboard creation.

This package provides:
- Azure SDK-compliant client following Microsoft design patterns
- KQL query execution across multiple Sentinel workspaces
- Data transformation and normalization for centralized reporting  
- Batch processing with configurable time ranges and LRO support
- Azure Monitor ingestion for report tables
- Comprehensive error handling with service-specific exceptions
- Distributed tracing and observability
- Standard authentication patterns with Azure Identity
"""

from .version import __version__

# Azure SDK-compliant client and components
from .sentinel_client import SentinelAggregatorClient
from .client_options import SentinelAggregatorClientOptions

# Response models
from .responses import (
    QueryResult, UploadResult, BatchExecutionResult, ServiceProperties,
    WorkspaceQueryExecution, QueryStatus, UploadStatus, BatchStatus
)

# Service-specific exceptions
from .exceptions import (
    SentinelAggregatorError, QueryExecutionError, WorkspaceAccessError,
    DataIngestionError, ConfigurationError, WorkspaceConfigurationError,
    BatchOperationError, CredentialValidationError
)

# Core data models
from .models import WorkspaceConfig, KQLQueryDefinition, QueryExecution

# Workspace management utilities
from .workspace_manager import WorkspaceManager, load_workspace_config

# High-level query execution engine
from .query_engine import SentinelQueryEngine

__all__ = [
    "__version__",
    
    # Primary Azure SDK-compliant client
    "SentinelAggregatorClient",
    "SentinelAggregatorClientOptions",
    
    # Response models
    "QueryResult",
    "UploadResult", 
    "BatchExecutionResult",
    "ServiceProperties",
    "WorkspaceQueryExecution",
    
    # Status enums
    "QueryStatus",
    "UploadStatus", 
    "BatchStatus",
    
    # Service-specific exceptions
    "SentinelAggregatorError",
    "QueryExecutionError",
    "WorkspaceAccessError", 
    "DataIngestionError",
    "ConfigurationError",
    "WorkspaceConfigurationError",
    "BatchOperationError",
    "CredentialValidationError",
    
    # Core data models
    "WorkspaceConfig",
    "KQLQueryDefinition", 
    "QueryExecution",
    
    # Utilities
    "WorkspaceManager",
    "SentinelQueryEngine",
    "load_workspace_config"
]