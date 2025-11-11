"""
Core data models for Sentinel Log Aggregator.

This module contains dataclasses and models extracted from the original notebook
for workspace configurations, KQL query definitions, and execution tracking.
Includes both legacy models and new Azure SDK-compliant response models.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import yaml

# Import new Azure SDK-compliant models
from .responses import QueryStatus, UploadStatus

# Export the imported enums so they can be imported from models module
__all__ = [
    "QueryParameter",
    "WorkspaceConfig",
    "KQLQueryDefinition",
    "QueryExecution",
    "BatchExecutionSummary",
    "QueryStatus",
    "UploadStatus",
    "AVAILABLE_QUERIES",
]


@dataclass
class QueryParameter:
    """Define a query parameter with validation."""

    param_type: str
    required: bool = False
    default: Optional[Any] = None
    description: str = ""


@dataclass
class WorkspaceConfig:
    """
    Configuration for a Microsoft Sentinel workspace.

    This class represents a workspace configuration with flexible parameter support.
    Parameters are stored in a dictionary allowing workspace-specific customization
    including row-level security tags, environment settings, and custom values.

    Attributes:
        resource_id: Full Azure resource ID for the Log Analytics workspace
        customer_id: Log Analytics workspace customer ID (GUID)
        queries_list: List of query names or relative paths to query files this workspace should execute.
                     Supports both query names (for backward compatibility) and relative file paths
                     (e.g., "queries/incident_summary.yaml", "custom/my_query.yaml")
        parameters: Dictionary of workspace-specific parameters including:
            - row_level_security_tag: Security tag for data isolation
            - environment: Environment designation (dev, test, prod)
            - custom parameters: Any additional workspace-specific values
        aggregation_workspace: Boolean flag indicating if this workspace is used for health data and
                              aggregated logs. Exactly one workspace must have this set to True.
                              This workspace should match the DCR configuration target.
    """

    resource_id: str
    customer_id: str
    queries_list: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    aggregation_workspace: bool = False

    @property
    def workspace_name(self) -> str:
        """Extract workspace name from resource ID."""
        return self.resource_id.split("/")[-1] if self.resource_id else ""

    @property
    def subscription_id(self) -> str:
        """Extract subscription ID from resource ID."""
        parts = self.resource_id.split("/")
        try:
            sub_index = parts.index("subscriptions")
            return parts[sub_index + 1] if sub_index + 1 < len(parts) else ""
        except ValueError:
            return ""

    @property
    def resource_group(self) -> str:
        """Extract resource group name from resource ID."""
        parts = self.resource_id.split("/")
        try:
            rg_index = parts.index("resourcegroups")
            return parts[rg_index + 1] if rg_index + 1 < len(parts) else ""
        except ValueError:
            return ""


class KQLQueryDefinition:
    """Base class for KQL query definitions."""

    def __init__(
        self,
        name: str,
        destination_stream: str,
        description: str,
        stream_name: str,
        query: str = "",
    ):
        self.name = name
        self.destination_stream = destination_stream
        self.description = description
        self.stream_name = stream_name
        self._query = query
        self.parameters: Dict[str, QueryParameter] = {}

    def add_parameter(
        self,
        name: str,
        param_type: str,
        required: bool = False,
        default: Any = None,
        description: str = "",
    ) -> "KQLQueryDefinition":
        """Add a parameter to the query."""
        self.parameters[name] = QueryParameter(
            param_type=param_type, required=required, default=default, description=description
        )
        return self

    def set_stream(self, stream_name: str) -> "KQLQueryDefinition":
        """Set the stream association for this query."""
        self.stream_name = stream_name
        return self

    def get_query(self) -> str:
        """Return the KQL query string."""
        return self._query

    @classmethod
    def from_yaml(cls, yaml_file_path: str) -> "KQLQueryDefinition":
        """Create a KQLQueryDefinition from a YAML file."""
        with open(yaml_file_path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        # Extract required fields with defaults for optional ones
        name = data["name"]
        destination_stream = data["destination_stream"]
        description = data["description"]
        stream_name = data.get("stream_name", destination_stream)  # Default to destination_stream
        query = data["query"]

        # Create the query definition
        query_def = cls(
            name=name,
            destination_stream=destination_stream,
            description=description,
            stream_name=stream_name,
            query=query,
        )

        # Add parameters if they exist
        if "parameters" in data and data["parameters"] is not None:
            for param_name, param_config in data["parameters"].items():
                if param_config is not None:  # Handle empty parameter blocks
                    query_def.add_parameter(
                        name=param_name,
                        param_type=param_config.get("type", "string"),
                        required=param_config.get("required", False),
                        default=param_config.get("default"),
                        description=param_config.get("description", ""),
                    )

        return query_def

    def build_query(self, parameters: Optional[Dict[str, Any]] = None) -> str:
        """Build query with parameter substitution."""
        if parameters is None:
            parameters = {}

        query = self.get_query()

        # Apply parameter substitution
        for param_name, param_config in self.parameters.items():
            placeholder = f"{{{param_name}}}"

            if param_name in parameters:
                value = parameters[param_name]
            elif param_config.default is not None:
                value = param_config.default
            elif param_config.required:
                raise ValueError(f"Required parameter '{param_name}' not provided")
            else:
                value = ""

            query = query.replace(placeholder, str(value))

        return query

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for compatibility."""
        params_dict = {}
        for name, param in self.parameters.items():
            params_dict[name] = {
                "type": param.param_type,
                "required": param.required,
                "description": param.description,
            }
            if param.default is not None:
                params_dict[name]["default"] = param.default

        return {
            "destination_stream": self.destination_stream,
            "description": self.description,
            "parameters": params_dict,
            "query": self.get_query(),
            "stream_name": self.stream_name,
        }


@dataclass
class QueryExecution:
    """Track execution of a single query."""

    job_correlation_id: str
    execution_id: str
    workspace_id: str
    query_name: str
    destination_stream: str
    start_time: datetime
    end_time: datetime
    execution_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Query execution details
    query_status: str = QueryStatus.PENDING.value
    query_duration_seconds: float = 0.0
    query_error_message: str = ""
    record_count: int = 0

    # Upload details
    upload_status: str = UploadStatus.PENDING.value
    upload_duration_seconds: float = 0.0
    upload_error_message: str = ""
    uploaded_count: int = 0

    @property
    def time_range_str(self) -> str:
        """Get formatted time range string (oldest to newest)."""
        return f"{self.start_time.strftime('%Y-%m-%d %H:%M')} to {self.end_time.strftime('%Y-%m-%d %H:%M')}"

    @property
    def workspace_alias(self) -> str:
        """Get workspace identifier."""
        return self.workspace_id

    @property
    def status(self) -> str:
        """Get the primary status - returns query_status."""
        return self.query_status

    @property
    def error_message(self) -> str:
        """Get the most relevant error message."""
        if self.query_error_message:
            return self.query_error_message
        elif self.upload_error_message:
            return self.upload_error_message
        else:
            return ""


@dataclass
class BatchExecutionSummary:
    """Summary of batch query execution."""

    job_correlation_id: str
    batch_id: str
    notebook_run_timestamp: datetime
    total_queries: int
    successful_queries: int
    failed_queries: int
    successful_uploads: int
    failed_uploads: int
    total_records: int
    total_uploaded_records: int
    total_duration_seconds: float
    time_range_start: datetime
    time_range_end: datetime
    executions: List["QueryExecution"] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate query success rate."""
        if self.total_queries == 0:
            return 0.0
        return (self.successful_queries / self.total_queries) * 100

    @property
    def upload_success_rate(self) -> float:
        """Calculate upload success rate."""
        total_uploads = self.successful_uploads + self.failed_uploads
        if total_uploads == 0:
            return 0.0
        return (self.successful_uploads / total_uploads) * 100

    def generate_detailed_summary(self) -> Dict[str, Any]:
        """
        Generate detailed summary grouped by workspace and query.

        Returns:
            Dictionary with detailed workspace/query statistics
        """
        from collections import defaultdict

        # Group executions by workspace and query
        workspace_query_stats: Dict[str, Dict[str, List[Any]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for execution in self.executions:
            # Use full workspace ID as key, store execution for later access
            workspace_key = execution.workspace_id
            workspace_query_stats[workspace_key][execution.query_name].append(execution)

        detailed_summary: Dict[str, Any] = {
            "overview": {
                "total_workspaces": len(workspace_query_stats),
                "total_unique_queries": len(set(e.query_name for e in self.executions)),
                "total_time_range": f"{self.time_range_start.strftime('%Y-%m-%d %H:%M')} to {self.time_range_end.strftime('%Y-%m-%d %H:%M')}",
                "total_duration_seconds": self.total_duration_seconds,
                "total_records_downloaded": self.total_records,
                "total_records_uploaded": self.total_uploaded_records,
            },
            "workspace_query_details": [],
        }

        # Generate statistics for each workspace/query combination
        for workspace, queries in workspace_query_stats.items():
            for query_name, query_executions in queries.items():
                successful_executions = [
                    e for e in query_executions if e.query_status == QueryStatus.SUCCESS.value
                ]
                failed_executions = [
                    e for e in query_executions if e.query_status == QueryStatus.FAILED.value
                ]
                successful_uploads = [
                    e for e in query_executions if e.upload_status == UploadStatus.SUCCESS.value
                ]

                # Calculate execution time statistics
                exec_times = [
                    e.query_duration_seconds
                    for e in successful_executions
                    if e.query_duration_seconds > 0
                ]
                avg_exec_time = sum(exec_times) / len(exec_times) if exec_times else 0.0
                total_exec_time = sum(exec_times)

                # Calculate upload time statistics
                upload_times = [
                    e.upload_duration_seconds
                    for e in successful_uploads
                    if e.upload_duration_seconds > 0
                ]
                avg_upload_time = sum(upload_times) / len(upload_times) if upload_times else 0.0
                total_upload_time = sum(upload_times)

                # Calculate record statistics
                records_downloaded = sum(e.record_count for e in successful_executions)
                records_uploaded = sum(e.uploaded_count for e in successful_uploads)
                upload_failed_count = (
                    records_downloaded - records_uploaded
                    if records_downloaded > records_uploaded
                    else 0
                )

                query_detail = {
                    "workspaceId": workspace,  # Full workspace GUID
                    "query": query_name,
                    "logsDownloaded": records_downloaded,
                    "uploadSuccess": records_uploaded,
                    "uploadFailure": upload_failed_count,
                    "avgQueryTime": round(avg_exec_time, 2),
                    "totalQueryTime": round(total_exec_time, 2),
                    "queryExecutions": len(query_executions),
                    "startTimeRange": min(e.start_time for e in query_executions).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "endTimeRange": max(e.end_time for e in query_executions).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    # Keep legacy fields for backward compatibility
                    "workspace": (
                        query_executions[0].workspace_alias or workspace[:8] + "..."
                        if len(workspace) > 8
                        else workspace
                    ),
                    "total_executions": len(query_executions),
                    "successful_executions": len(successful_executions),
                    "failed_executions": len(failed_executions),
                    "execution_times": {
                        "average_seconds": round(avg_exec_time, 2),
                        "total_seconds": round(total_exec_time, 2),
                    },
                    "upload_times": {
                        "average_seconds": round(avg_upload_time, 2),
                        "total_seconds": round(total_upload_time, 2),
                    },
                    "records": {
                        "downloaded": records_downloaded,
                        "uploaded_success": records_uploaded,
                        "uploaded_failed": (
                            records_downloaded - records_uploaded
                            if records_downloaded > records_uploaded
                            else 0
                        ),
                    },
                    "time_range": {
                        "start": min(e.start_time for e in query_executions).strftime(
                            "%Y-%m-%d %H:%M"
                        ),
                        "end": max(e.end_time for e in query_executions).strftime("%Y-%m-%d %H:%M"),
                    },
                }

                detailed_summary["workspace_query_details"].append(query_detail)

        # Sort by workspace then query for consistent output
        detailed_summary["workspace_query_details"].sort(key=lambda x: (x["workspace"], x["query"]))

        return detailed_summary


# Initialize an empty AVAILABLE_QUERIES dict - queries are loaded on-demand from workspace configs
AVAILABLE_QUERIES: Dict[str, KQLQueryDefinition] = {}


# Initialize query registry - queries will be loaded on-demand from workspace configurations
def _initialize_query_registry() -> None:
    """Initialize the global query registry. Queries are loaded on-demand from workspace configs."""
    from .query_registry import query_registry

    # Registry starts empty - queries are loaded when workspace configurations are processed
    query_registry._queries = {}


# Initialize the empty registry
_initialize_query_registry()
