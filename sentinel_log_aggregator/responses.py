"""
Azure SDK-compliant response models for Sentinel Log Aggregator.

Provides structured response objects following Azure SDK patterns using
azure.core.Model base class for type safety and consistency.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from azure.core import CaseInsensitiveEnumMeta


class QueryStatus(str, Enum, metaclass=CaseInsensitiveEnumMeta):
    """Status of query execution."""

    PENDING = "pending"
    SUCCESS = "success"
    COMPLETED = "success"  # Alias for SUCCESS for test compatibility
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class UploadStatus(str, Enum, metaclass=CaseInsensitiveEnumMeta):
    """Status of data upload to Azure Monitor."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class BatchStatus(str, Enum, metaclass=CaseInsensitiveEnumMeta):
    """Status of batch operation."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL_SUCCESS = "partial_success"


@dataclass
class QueryResult:
    """
    Result of a KQL query execution.

    :param status: Query execution status
    :type status: QueryStatus
    :param data: Query result data as list of dictionaries
    :type data: List[Dict[str, Any]]
    :param record_count: Number of records returned
    :type record_count: int
    :param execution_time: Query execution duration in seconds
    :type execution_time: float
    :param workspace_id: Workspace where query was executed
    :type workspace_id: str
    :param query: KQL query string that was executed
    :type query: str
    :param start_time: Query time range start
    :type start_time: Optional[datetime]
    :param end_time: Query time range end
    :type end_time: Optional[datetime]
    :param correlation_id: Operation correlation ID
    :type correlation_id: Optional[str]
    :param request_id: Azure request ID
    :type request_id: Optional[str]
    :param error_message: Error message if query failed
    :type error_message: Optional[str]
    :param error_code: Error code if query failed
    :type error_code: Optional[str]
    """

    status: QueryStatus
    data: List[Dict[str, Any]] = None
    record_count: int = 0
    execution_time: float = 0.0
    workspace_id: str = ""
    query: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None

    def __init__(
        self,
        status: QueryStatus,
        data: Optional[List[Dict[str, Any]]] = None,
        record_count: int = 0,
        execution_time: Optional[float] = None,
        workspace_id: str = "",
        query: str = "",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        # Backward compatibility aliases
        records: Optional[List[Dict[str, Any]]] = None,
        execution_time_seconds: Optional[float] = None,
    ):
        """Initialize QueryResult with support for legacy parameter names."""
        self.status = status
        # Use 'records' if provided, otherwise 'data'
        self.data = records if records is not None else (data if data is not None else [])
        self.record_count = record_count
        # Use 'execution_time_seconds' if provided, otherwise 'execution_time'
        self.execution_time = (
            execution_time_seconds
            if execution_time_seconds is not None
            else (execution_time if execution_time is not None else 0.0)
        )
        self.workspace_id = workspace_id
        self.query = query
        self.start_time = start_time
        self.end_time = end_time
        self.correlation_id = correlation_id
        self.request_id = request_id
        self.error_message = error_message
        self.error_code = error_code

    @property
    def succeeded(self) -> bool:
        """Whether the query executed successfully."""
        return self.status == QueryStatus.SUCCESS

    @property
    def failed(self) -> bool:
        """Whether the query failed."""
        return self.status == QueryStatus.FAILED

    @property
    def workspace_alias(self) -> str:
        """Workspace ID for logging."""
        return self.workspace_id if self.workspace_id else "unknown"

    @property
    def records(self) -> List[Dict[str, Any]]:
        """Alias for data property for backward compatibility."""
        return self.data

    @property
    def execution_time_seconds(self) -> float:
        """Alias for execution_time for backward compatibility."""
        return self.execution_time


@dataclass
class UploadResult:
    """
    Result of data upload to Azure Monitor.

    :param status: Upload status
    :type status: UploadStatus
    :param record_count: Number of records uploaded
    :type record_count: int
    :param upload_time: Upload duration in seconds
    :type upload_time: float
    :param stream_name: Destination stream name
    :type stream_name: str
    :param dcr_immutable_id: Data Collection Rule immutable ID
    :type dcr_immutable_id: str
    :param correlation_id: Operation correlation ID
    :type correlation_id: Optional[str]
    :param request_id: Azure request ID
    :type request_id: Optional[str]
    :param error_message: Error message if upload failed
    :type error_message: Optional[str]
    :param error_code: Error code if upload failed
    :type error_code: Optional[str]
    :param bytes_uploaded: Number of bytes uploaded
    :type bytes_uploaded: Optional[int]
    """

    status: UploadStatus
    record_count: int
    upload_time: float
    stream_name: str
    dcr_immutable_id: str
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    bytes_uploaded: Optional[int] = None

    @property
    def succeeded(self) -> bool:
        """Whether the upload succeeded."""
        return self.status == UploadStatus.SUCCESS

    @property
    def failed(self) -> bool:
        """Whether the upload failed."""
        return self.status == UploadStatus.FAILED


@dataclass
class WorkspaceQueryExecution:
    """
    Result of query execution for a single workspace.

    :param workspace_id: Workspace ID
    :type workspace_id: str
    :param workspace_alias: Workspace alias for display
    :type workspace_alias: str
    :param query_result: Query execution result
    :type query_result: QueryResult
    :param upload_result: Upload result if data was uploaded
    :type upload_result: Optional[UploadResult]
    :param correlation_id: Operation correlation ID
    :type correlation_id: Optional[str]
    """

    workspace_id: str
    workspace_alias: str
    query_result: QueryResult
    upload_result: Optional[UploadResult] = None
    correlation_id: Optional[str] = None

    @property
    def succeeded(self) -> bool:
        """Whether both query and upload (if attempted) succeeded."""
        query_ok = self.query_result.succeeded
        upload_ok = self.upload_result.succeeded if self.upload_result else True
        return query_ok and upload_ok


@dataclass
class BatchExecutionResult:
    """
    Result of batch query execution across multiple workspaces.

    :param status: Overall batch execution status
    :type status: BatchStatus
    :param workspace_results: Results for each workspace
    :type workspace_results: List[WorkspaceQueryExecution]
    :param total_records: Total records processed across all workspaces
    :type total_records: int
    :param total_execution_time: Total execution time in seconds
    :type total_execution_time: float
    :param job_correlation_id: Job correlation ID
    :type job_correlation_id: str
    :param start_time: Batch execution start time
    :type start_time: datetime
    :param end_time: Batch execution end time
    :type end_time: Optional[datetime]
    :param successful_workspaces: Number of workspaces processed successfully
    :type successful_workspaces: int
    :param failed_workspaces: Number of workspaces that failed
    :type failed_workspaces: int
    :param query_name: Name of the query that was executed
    :type query_name: Optional[str]
    :param report_name: Name of the report being generated
    :type report_name: Optional[str]
    """

    status: BatchStatus
    workspace_results: List[WorkspaceQueryExecution]
    total_records: int
    total_execution_time: float
    job_correlation_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    successful_workspaces: int = 0
    failed_workspaces: int = 0
    query_name: Optional[str] = None
    report_name: Optional[str] = None

    @property
    def succeeded(self) -> bool:
        """Whether the batch execution succeeded."""
        return self.status == BatchStatus.SUCCESS

    @property
    def failed(self) -> bool:
        """Whether the batch execution failed."""
        return self.status == BatchStatus.FAILED

    @property
    def partial_success(self) -> bool:
        """Whether the batch had partial success."""
        return self.status == BatchStatus.PARTIAL_SUCCESS

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        total = self.successful_workspaces + self.failed_workspaces
        return (self.successful_workspaces / total * 100) if total > 0 else 0.0

    @property
    def duration(self) -> Optional[float]:
        """Total duration in seconds if completed."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


@dataclass
class ServiceProperties:
    """
    Service properties for health checks and diagnostics.

    :param service_version: Service version
    :type service_version: str
    :param connectivity_status: Service connectivity status
    :type connectivity_status: str
    :param authentication_status: Authentication status
    :type authentication_status: str
    :param dcr_endpoint: DCR endpoint URL
    :type dcr_endpoint: str
    :param dcr_immutable_id: DCR immutable ID
    :type dcr_immutable_id: str
    :param workspace_count: Number of configured workspaces
    :type workspace_count: int
    :param available_queries: Number of available queries
    :type available_queries: int
    :param last_check_time: Last health check time
    :type last_check_time: datetime
    """

    service_version: str
    connectivity_status: str
    authentication_status: str
    dcr_endpoint: str
    dcr_immutable_id: str
    workspace_count: int
    available_queries: int
    last_check_time: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.last_check_time is None:
            self.last_check_time = datetime.now(timezone.utc)
