"""
Configuration validation and schema definitions using Pydantic.

Provides robust validation for all configuration inputs with detailed
error messages and type safety.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.networks import AnyUrl


class WorkspaceConfigModel(BaseModel):
    """Pydantic model for workspace configuration validation."""

    resource_id: str = Field(
        ...,
        description="Full Azure resource ID for the Log Analytics workspace",
        pattern=r"^/subscriptions/[0-9a-f-]+/resourcegroups/.+/providers/microsoft\.operationalinsights/workspaces/.+$",
    )
    customer_id: str = Field(
        ...,
        description="Log Analytics workspace customer ID (GUID)",
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Workspace-specific parameters for query execution"
    )
    queries_list: List[str] = Field(
        default_factory=list, description="List of queries this workspace should execute"
    )

    @field_validator("resource_id")
    @classmethod
    def validate_resource_id(cls, v: str) -> str:
        """Validate Azure resource ID format."""
        if not v.lower().startswith("/subscriptions/"):
            raise ValueError("Resource ID must start with /subscriptions/")
        if "microsoft.operationalinsights/workspaces" not in v.lower():
            raise ValueError("Resource ID must be for a Log Analytics workspace")
        return v

    @field_validator("queries_list")
    @classmethod
    def validate_queries_list(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate queries list contains valid query names."""
        if v is None:
            return v

        # With the new on-demand query architecture, we don't validate against 
        # a hardcoded list since queries are loaded from workspace configurations.
        # Basic validation: check that we have strings and they're not empty
        for query in v:
            if not isinstance(query, str) or not query.strip():
                raise ValueError(f"Query names must be non-empty strings, got: {query}")

        return v

    @field_validator("parameters")
    @classmethod
    def validate_parameters(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workspace parameters structure and types."""
        if not isinstance(v, dict):
            raise ValueError("Parameters must be a dictionary")

        # Validate common parameter types
        for param_name, param_value in v.items():
            if not isinstance(param_name, str):
                raise ValueError(f"Parameter name must be a string, got {type(param_name)}")

            # Allow any type for parameter values, but warn about complex types
            if isinstance(param_value, (dict, list)) and len(str(param_value)) > 1000:
                raise ValueError(f"Parameter '{param_name}' value is too complex (>1000 chars)")

        return v

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


class QueryParameterModel(BaseModel):
    """Pydantic model for query parameter validation."""

    type: str = Field(..., pattern=r"^(string|int|float|bool|datetime)$")
    required: bool = Field(default=False)
    default: Optional[Any] = None
    description: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def validate_default_type(self) -> "QueryParameterModel":
        """Validate that default value matches parameter type."""
        param_type = self.type
        default = self.default

        if default is not None and param_type:
            if param_type == "int" and not isinstance(default, int):
                raise ValueError(f"Default value must be an integer for type 'int'")
            elif param_type == "float" and not isinstance(default, (int, float)):
                raise ValueError(f"Default value must be a number for type 'float'")
            elif param_type == "bool" and not isinstance(default, bool):
                raise ValueError(f"Default value must be a boolean for type 'bool'")
            elif param_type == "string" and not isinstance(default, str):
                raise ValueError(f"Default value must be a string for type 'string'")

        return self


class QueryDefinitionModel(BaseModel):
    """Pydantic model for query definition validation."""

    name: str = Field(
        ..., pattern=r"^[a-z][a-z0-9_]*$", description="Query name (lowercase, underscores allowed)"
    )
    destination_stream: str = Field(
        ...,
        pattern=r"^Custom-[A-Za-z0-9_]+-[A-Za-z0-9_]+_CL$|^Custom-[A-Za-z0-9_]+_[A-Za-z0-9_]+_CL$",
        description="Azure Monitor custom log table name",
    )
    description: str = Field(
        default="", max_length=1000, description="Human-readable query description"
    )
    stream_name: str = Field(
        ...,
        pattern=r"^stream_[a-z][a-z0-9_]*$",
        description="Stream name (must start with 'stream_')",
    )
    version: str = Field(
        default="1.0",
        pattern=r"^\d+\.\d+(\.\d+)?$",
        description="Query version (semantic versioning)",
    )
    parameters: Dict[str, QueryParameterModel] = Field(
        default_factory=dict, description="Query parameters definition"
    )
    query: str = Field(..., min_length=10, description="KQL query text")
    tags: List[str] = Field(default_factory=list, description="Query tags for categorization")

    @field_validator("query")
    @classmethod
    def validate_query_syntax(cls, v: str) -> str:
        """Basic KQL query validation."""
        if not v.strip():
            raise ValueError("Query cannot be empty")

        # Check for dangerous operations
        dangerous_operations = [
            ".drop",
            ".delete",
            ".create",
            ".alter",
            ".set",
            "drop table",
            "delete from",
            "truncate",
        ]

        query_lower = v.lower()
        for operation in dangerous_operations:
            if operation in query_lower:
                raise ValueError(f"Query contains potentially dangerous operation: {operation}")

        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate tag format."""
        tag_pattern = re.compile(r"^[a-z][a-z0-9_-]*$")
        for tag in v:
            if not tag_pattern.match(tag):
                raise ValueError(
                    f"Invalid tag format: {tag}. Tags must be lowercase, alphanumeric with underscores/hyphens"
                )
        return v


class ClientOptionsModel(BaseModel):
    """Pydantic model for client configuration validation."""

    # Azure Monitor configuration
    dcr_logs_ingestion_endpoint: AnyUrl = Field(
        ..., description="Azure Monitor Data Collection Rule logs ingestion endpoint"
    )
    dcr_rule_id: str = Field(
        ..., description="Data Collection Rule ID", pattern=r"^dcr-[a-f0-9]{32}$"
    )

    # Query execution settings
    max_concurrent_queries: int = Field(
        default=5, ge=1, le=20, description="Maximum number of concurrent queries"
    )
    query_timeout_seconds: int = Field(
        default=300, ge=30, le=3600, description="Query timeout in seconds"
    )
    batch_hours: int = Field(
        default=24, ge=1, le=168, description="Batch processing time window in hours"
    )

    # Upload settings
    upload_timeout_seconds: int = Field(
        default=300, ge=30, le=1800, description="Upload timeout in seconds"
    )
    max_upload_retries: int = Field(
        default=3, ge=1, le=10, description="Maximum upload retry attempts"
    )

    # Logging and monitoring
    log_level: str = Field(
        default="INFO",
        pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level",
    )
    enable_telemetry: bool = Field(default=True, description="Enable Azure SDK telemetry")

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class WorkspaceCollectionModel(BaseModel):
    """Pydantic model for workspace collection validation."""

    workspaces: List[WorkspaceConfigModel] = Field(
        ..., min_length=1, description="List of workspace configurations"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional metadata for the workspace collection"
    )

    @field_validator("workspaces")
    @classmethod
    def validate_unique_workspaces(
        cls, v: List[WorkspaceConfigModel]
    ) -> List[WorkspaceConfigModel]:
        """Ensure workspace IDs and security tags are unique."""
        customer_ids = [ws.customer_id for ws in v]
        resource_ids = [ws.resource_id for ws in v]
        security_tags = [
            ws.parameters.get("row_level_security_tag", "")
            for ws in v
            if ws.parameters.get("row_level_security_tag")
        ]

        if len(customer_ids) != len(set(customer_ids)):
            raise ValueError("Duplicate customer IDs found in workspace list")

        if len(resource_ids) != len(set(resource_ids)):
            raise ValueError("Duplicate resource IDs found in workspace list")

        if len(security_tags) != len(set(security_tags)):
            raise ValueError("Duplicate row-level security tags found in workspace list")

        return v


def validate_workspace_config(config_data: Dict[str, Any]) -> WorkspaceCollectionModel:
    """
    Validate workspace configuration data.

    Args:
        config_data: Raw configuration data

    Returns:
        Validated workspace collection model

    Raises:
        ValidationError: If validation fails
    """
    return WorkspaceCollectionModel(**config_data)


def validate_query_definition(query_data: Dict[str, Any]) -> QueryDefinitionModel:
    """
    Validate query definition data.

    Args:
        query_data: Raw query definition data

    Returns:
        Validated query definition model

    Raises:
        ValidationError: If validation fails
    """
    return QueryDefinitionModel(**query_data)


def validate_client_options(options_data: Dict[str, Any]) -> ClientOptionsModel:
    """
    Validate client options data.

    Args:
        options_data: Raw client options data

    Returns:
        Validated client options model

    Raises:
        ValidationError: If validation fails
    """
    return ClientOptionsModel(**options_data)
