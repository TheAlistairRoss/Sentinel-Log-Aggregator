"""
Azure SDK-compliant exception hierarchy for Sentinel Log Aggregator.

Provides service-specific exceptions following Azure SDK patterns for better
error handling and debugging capabilities.
"""

from typing import Any, Dict, Optional

from azure.core.exceptions import AzureError, ClientAuthenticationError, HttpResponseError


class SentinelAggregatorError(AzureError):
    """Base exception for all Sentinel Log Aggregator errors."""

    def __init__(
        self,
        message: str,
        *,
        error_code: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.error_code = error_code
        self.error_details = error_details or {}


class QueryExecutionError(SentinelAggregatorError):
    """Exception raised when KQL query execution fails."""

    def __init__(
        self,
        message: str,
        *,
        workspace_id: Optional[str] = None,
        query: Optional[str] = None,
        error_code: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code=error_code, **kwargs)
        self.workspace_id = workspace_id
        self.query = query


class WorkspaceAccessError(SentinelAggregatorError):
    """Exception raised when workspace access is denied or unavailable."""

    def __init__(
        self,
        message: str,
        *,
        workspace_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        error_code: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code=error_code, **kwargs)
        self.workspace_id = workspace_id
        self.resource_id = resource_id


class DataIngestionError(SentinelAggregatorError):
    """Exception raised when data ingestion to Azure Monitor fails."""

    def __init__(
        self,
        message: str,
        *,
        stream_name: Optional[str] = None,
        dcr_immutable_id: Optional[str] = None,
        record_count: Optional[int] = None,
        error_code: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code=error_code, **kwargs)
        self.stream_name = stream_name
        self.dcr_immutable_id = dcr_immutable_id
        self.record_count = record_count


class ConfigurationError(SentinelAggregatorError):
    """Exception raised when configuration is invalid or missing."""

    def __init__(
        self,
        message: str,
        *,
        config_key: Optional[str] = None,
        error_code: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code=error_code, **kwargs)
        self.config_key = config_key


class WorkspaceConfigurationError(SentinelAggregatorError):
    """Exception raised when workspace configuration is invalid."""

    def __init__(
        self,
        message: str,
        *,
        workspace_alias: Optional[str] = None,
        config_file: Optional[str] = None,
        error_code: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code=error_code, **kwargs)
        self.workspace_alias = workspace_alias
        self.config_file = config_file


class BatchOperationError(SentinelAggregatorError):
    """Exception raised when batch operation fails."""

    def __init__(
        self,
        message: str,
        *,
        failed_operations: Optional[int] = None,
        total_operations: Optional[int] = None,
        error_code: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code=error_code, **kwargs)
        self.failed_operations = failed_operations
        self.total_operations = total_operations


class CredentialValidationError(ClientAuthenticationError):
    """Exception raised when credential validation fails."""

    def __init__(
        self,
        message: str,
        *,
        credential_type: Optional[str] = None,
        scope: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.credential_type = credential_type
        self.scope = scope
