"""
Azure SDK-compliant Sentinel Log Aggregator client.

Provides a service client following Azure SDK design patterns for querying
Microsoft Sentinel workspaces and aggregating data with proper authentication,
retry logic, error handling, and observability.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from azure.core.credentials_async import AsyncTokenCredential
from azure.core.exceptions import (
    AzureError,
    ClientAuthenticationError,
    HttpResponseError,
)
from azure.core.paging import ItemPaged
from azure.core.pipeline.policies import (
    BearerTokenCredentialPolicy,
    HeadersPolicy,
    NetworkTraceLoggingPolicy,
    RequestIdPolicy,
    RetryPolicy,
    UserAgentPolicy,
)
from azure.core.tracing.decorator_async import distributed_trace_async
from azure.identity.aio import DefaultAzureCredential
from azure.monitor.ingestion.aio import LogsIngestionClient
from azure.monitor.query.aio import LogsQueryClient

from .client_options import SentinelAggregatorClientOptions
from .constants import DEFAULT_PAGE_SIZE
from .exceptions import (
    CredentialValidationError,
    DataIngestionError,
    QueryExecutionError,
)
from .models import KQLQueryDefinition, WorkspaceConfig
from .responses import (
    BatchExecutionResult,
    BatchStatus,
    QueryResult,
    QueryStatus,
    ServiceProperties,
    UploadResult,
    UploadStatus,
    WorkspaceQueryExecution,
)
from .security_utils import (
    SecureLogger,
    generate_correlation_id,
    validate_kql_query,
    validate_workspace_id,
)
from .time_utils import format_datetime_iso8601


class SentinelAggregatorClient:
    """
    Azure SDK-compliant client for Microsoft Sentinel log aggregation.

    This client provides methods for querying multiple Sentinel workspaces,
    processing query results, and ingesting aggregated data following
    Azure SDK design patterns and best practices.

    :param dcr_logs_ingestion_endpoint: Azure Monitor DCR logs ingestion endpoint
    :type dcr_logs_ingestion_endpoint: str
    :param credential: Azure credential for authentication
    :type credential: AsyncTokenCredential
    :param options: Client configuration options
    :type options: Optional[SentinelAggregatorClientOptions]
    """

    def __init__(
        self,
        dcr_logs_ingestion_endpoint: str,
        credential: AsyncTokenCredential,
        *,
        options: Optional[SentinelAggregatorClientOptions] = None,
        **kwargs,
    ):
        """
        Initialize the Sentinel Aggregator client.

        :param dcr_logs_ingestion_endpoint: Azure Monitor DCR logs ingestion endpoint
        :type dcr_logs_ingestion_endpoint: str
        :param credential: Azure credential for authentication
        :type credential: AsyncTokenCredential
        :param options: Client configuration options
        :type options: Optional[SentinelAggregatorClientOptions]
        """
        # Validate required parameters
        if not dcr_logs_ingestion_endpoint:
            raise ValueError("dcr_logs_ingestion_endpoint is required")
        if not credential:
            raise ValueError("credential is required")

        # Store configuration
        self._dcr_endpoint = dcr_logs_ingestion_endpoint
        self._credential = credential
        self._options = options or SentinelAggregatorClientOptions()

        # Validate options
        self._options.dcr_logs_ingestion_endpoint = dcr_logs_ingestion_endpoint
        self._options.validate()

        # Initialize logging
        self._logger = SecureLogger(logging.getLogger(__name__))

        # Initialize Azure SDK clients (lazy loaded)
        self._logs_query_client: Optional[LogsQueryClient] = None
        self._logs_ingestion_client: Optional[LogsIngestionClient] = None

        # Generate session correlation ID
        self._session_id = f"session_{generate_correlation_id()[:8]}"

    @classmethod
    def from_connection_string(
        cls,
        connection_string: str,
        *,
        credential: Optional[AsyncTokenCredential] = None,
        options: Optional[SentinelAggregatorClientOptions] = None,
        **kwargs,
    ) -> "SentinelAggregatorClient":
        """
        Create client from connection string.

        :param connection_string: Connection string containing endpoint and rule ID
        :type connection_string: str
        :param credential: Azure credential (uses DefaultAzureCredential if None)
        :type credential: Optional[AsyncTokenCredential]
        :param options: Client configuration options
        :type options: Optional[SentinelAggregatorClientOptions]
        :return: Configured client instance
        :rtype: SentinelAggregatorClient
        """
        # Parse connection string (format: "endpoint=https://...;dcr_immutable_id=dcr-...")
        conn_parts = {}
        for part in connection_string.split(";"):
            if "=" in part:
                key, value = part.split("=", 1)
                conn_parts[key.strip().lower()] = value.strip()

        endpoint = conn_parts.get("endpoint")
        if not endpoint:
            raise ValueError("Connection string must contain 'endpoint' parameter")

        # Update options with connection string values
        if options is None:
            options = SentinelAggregatorClientOptions()

        if "dcr_immutable_id" in conn_parts:
            options.dcr_immutable_id = conn_parts["dcr_immutable_id"]

        cred = credential or DefaultAzureCredential()
        return cls(endpoint, cred, options=options, **kwargs)

    def _get_user_agent(self) -> str:
        """Get user agent string for requests."""
        from .version import __version__

        return f"sentinel-aggregator/{__version__} (Azure SDK for Python)"

    def _create_pipeline_policies(self) -> List:
        """Create pipeline policies with proper configuration."""
        policies = [
            RequestIdPolicy(),
            UserAgentPolicy(user_agent=self._get_user_agent()),
            HeadersPolicy(),
            BearerTokenCredentialPolicy(self._credential, "https://api.loganalytics.io/.default"),
            RetryPolicy(
                retry_total=self._options.max_retries,
                retry_backoff_factor=self._options.retry_delay_seconds,
            ),
        ]

        # Add network tracing if enabled
        if self._options.enable_distributed_tracing:
            policies.append(NetworkTraceLoggingPolicy())

        # Add custom policies
        policies.extend(self._options.custom_policies)

        return policies

    @property
    def _logs_query_client_instance(self) -> LogsQueryClient:
        """Get or create logs query client."""
        if self._logs_query_client is None:
            self._logs_query_client = LogsQueryClient(
                credential=self._credential,
                timeout=self._options.query_timeout_seconds,
                logging_enable=True,
            )
        return self._logs_query_client

    @property
    def _logs_ingestion_client_instance(self) -> LogsIngestionClient:
        """Get or create logs ingestion client."""
        if self._logs_ingestion_client is None:
            self._logs_ingestion_client = LogsIngestionClient(
                endpoint=self._dcr_endpoint, credential=self._credential, logging_enable=True
            )
        return self._logs_ingestion_client

    @distributed_trace_async
    async def validate_credentials(self) -> None:
        """
        Validate credentials and connectivity.

        :raises CredentialValidationError: If credential validation fails
        """
        try:
            # Attempt to get a token to validate credentials
            token = await self._credential.get_token("https://api.loganalytics.io/.default")
            if not token or not token.token:
                raise CredentialValidationError(
                    "Failed to obtain access token",
                    credential_type=type(self._credential).__name__,
                    scope="https://api.loganalytics.io/.default",
                )

            self._logger.info("Credential validation successful")

        except Exception as e:
            self._logger.error(f"Credential validation failed: {e}")
            raise CredentialValidationError(
                f"Credential validation failed: {e}",
                credential_type=type(self._credential).__name__,
                scope="https://api.loganalytics.io/.default",
            ) from e

    @distributed_trace_async
    async def get_service_properties(self) -> ServiceProperties:
        """
        Get service properties for health checks and diagnostics.

        :return: Service properties
        :rtype: ServiceProperties
        """
        from .models import AVAILABLE_QUERIES
        from .version import __version__

        # Validate connectivity
        connectivity_status = "unknown"
        auth_status = "unknown"

        try:
            await self.validate_credentials()
            auth_status = "valid"
            connectivity_status = "connected"
        except Exception as e:
            auth_status = "failed"
            connectivity_status = "disconnected"
            self._logger.warning(f"Service health check failed: {e}")

        return ServiceProperties(
            service_version=__version__,
            connectivity_status=connectivity_status,
            authentication_status=auth_status,
            dcr_endpoint=self._dcr_endpoint,
            dcr_immutable_id=self._options.dcr_immutable_id or "not_configured",
            workspace_count=0,  # Updated by caller based on workspace config
            available_queries=len(AVAILABLE_QUERIES),
            last_check_time=datetime.now(timezone.utc),
        )

    @distributed_trace_async
    async def query_workspace(
        self,
        workspace_id: str,
        query: str,
        *,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        timeout_seconds: Optional[int] = None,
        correlation_id: Optional[str] = None,
    ) -> QueryResult:
        """
        Execute KQL query against a specific workspace.

        :param workspace_id: Workspace customer ID
        :type workspace_id: str
        :param query: KQL query string
        :type query: str
        :param start_time: Query time range start
        :type start_time: Optional[datetime]
        :param end_time: Query time range end
        :type end_time: Optional[datetime]
        :param timeout_seconds: Query timeout override
        :type timeout_seconds: Optional[int]
        :param correlation_id: Operation correlation ID
        :type correlation_id: Optional[str]
        :return: Query execution result
        :rtype: QueryResult
        :raises QueryExecutionError: If query execution fails
        """
        correlation_id = correlation_id or generate_correlation_id()

        # Validate inputs for security
        validate_workspace_id(workspace_id)
        validate_kql_query(query)

        start_exec = datetime.now(timezone.utc)

        try:
            # Configure timespan if provided
            timespan = None
            if start_time and end_time:
                timespan = (start_time, end_time)
                self._logger.debug(
                    f"Query timespan configured: {format_datetime_iso8601(start_time)} to {format_datetime_iso8601(end_time)} "
                    f"[workspace={workspace_id}] [correlation_id={correlation_id}]"
                )
            else:
                self._logger.warning(
                    f"Query executed WITHOUT timespan filter - this may scan entire table! "
                    f"[workspace={workspace_id}] [correlation_id={correlation_id}]"
                )

            # Execute query with timeout
            timeout = timeout_seconds or self._options.query_timeout_seconds

            self._logger.debug(
                f"Executing query with timeout={timeout}s, timespan={timespan is not None} "
                f"[workspace={workspace_id}] [correlation_id={correlation_id}]"
            )

            # Log full KQL query for debugging
            self._logger.debug(
                f"KQL Query:\n{query}\n"
                f"[workspace={workspace_id}] [correlation_id={correlation_id}]"
            )

            response = await asyncio.wait_for(
                self._logs_query_client_instance.query_workspace(
                    workspace_id, query, timespan=timespan
                ),
                timeout=timeout,
            )

            # Process results
            results = []
            if response.tables:
                for table in response.tables:
                    if (
                        hasattr(table, "columns")
                        and hasattr(table, "rows")
                        and table.columns
                        and table.rows
                    ):
                        # Get column names - handle different possible structures
                        if hasattr(table.columns[0], "name"):
                            columns = [col.name for col in table.columns]
                        else:
                            # Fallback for string columns
                            columns = table.columns

                        for row in table.rows:
                            results.append(dict(zip(columns, row)))

            execution_time = (datetime.now(timezone.utc) - start_exec).total_seconds()

            # Log query execution details
            self._logger.info(
                f"Query completed: {len(results)} records in {execution_time:.2f}s "
                f"[workspace={workspace_id}] "
                f"[timespan={'YES' if timespan else 'NO'}] "
                f"[correlation_id={correlation_id}]"
            )

            # Log statistics if available
            if hasattr(response, "statistics"):
                stats = response.statistics
                if stats:
                    self._logger.debug(
                        f"Query statistics: {stats} "
                        f"[workspace={workspace_id}] [correlation_id={correlation_id}]"
                    )

            # Log first 5 rows of results for debugging
            if results:
                sample_results = results[:5]
                self._logger.debug(
                    f"Query results (first {len(sample_results)} of {len(results)} rows):\n"
                    f"{json.dumps(sample_results, default=str, indent=2)}\n"
                    f"[workspace={workspace_id}] [correlation_id={correlation_id}]"
                )

            return QueryResult(
                status=QueryStatus.SUCCESS,
                data=results,
                record_count=len(results),
                execution_time=execution_time,
                workspace_id=workspace_id,
                query=query,
                start_time=start_time,
                end_time=end_time,
                correlation_id=correlation_id,
                request_id=getattr(response, "request_id", None),
            )

        except asyncio.TimeoutError:
            execution_time = (datetime.now(timezone.utc) - start_exec).total_seconds()
            self._logger.error(
                f"Query timeout after {execution_time:.2f}s for workspace {workspace_id} "
                f"[correlation_id={correlation_id}]"
            )

            return QueryResult(
                status=QueryStatus.TIMEOUT,
                data=[],
                record_count=0,
                execution_time=execution_time,
                workspace_id=workspace_id,
                query=query,
                start_time=start_time,
                end_time=end_time,
                correlation_id=correlation_id,
                error_message=f"Query timeout after {timeout}s",
                error_code="TIMEOUT",
            )

        except (ClientAuthenticationError, HttpResponseError, AzureError) as e:
            execution_time = (datetime.now(timezone.utc) - start_exec).total_seconds()
            error_msg = str(e)

            self._logger.error(
                f"Query failed for workspace {workspace_id}: {error_msg} "
                f"[correlation_id={correlation_id}]"
            )

            return QueryResult(
                status=QueryStatus.FAILED,
                data=[],
                record_count=0,
                execution_time=execution_time,
                workspace_id=workspace_id,
                query=query,
                start_time=start_time,
                end_time=end_time,
                correlation_id=correlation_id,
                error_message=error_msg,
                error_code=getattr(e, "error_code", type(e).__name__),
            )

    def list_query_results(
        self,
        workspace_id: str,
        query: str,
        *,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        timeout_seconds: Optional[int] = None,
    ) -> ItemPaged[Dict[str, Any]]:
        """
        List query results using Azure SDK paging pattern.

        This method returns an ItemPaged object that can be used to iterate
        through large result sets efficiently without loading all results
        into memory at once.

        :param workspace_id: Workspace customer ID
        :type workspace_id: str
        :param query: KQL query string
        :type query: str
        :param start_time: Query time range start
        :type start_time: Optional[datetime]
        :param end_time: Query time range end
        :type end_time: Optional[datetime]
        :param page_size: Number of records per page
        :type page_size: int
        :param timeout_seconds: Query timeout override
        :type timeout_seconds: Optional[int]
        :return: Paginated query results
        :rtype: ItemPaged[Dict[str, Any]]
        """

        async def get_page(continuation_token=None):
            """Get a page of results."""
            page_query = query

            # Add pagination to the query if not already present
            if "take" not in query.lower() and "limit" not in query.lower():
                if continuation_token:
                    # Calculate skip based on continuation token
                    skip_count = int(continuation_token) * page_size
                    page_query = f"{query} | skip {skip_count} | take {page_size}"
                else:
                    page_query = f"{query} | take {page_size}"

            result = await self.query_workspace(
                workspace_id=workspace_id,
                query=page_query,
                start_time=start_time,
                end_time=end_time,
                timeout_seconds=timeout_seconds,
            )

            if not result.succeeded:
                raise QueryExecutionError(
                    f"Query failed: {result.error_message}",
                    workspace_id=workspace_id,
                    query=page_query,
                    error_code=result.error_code,
                )

            # Return data and next continuation token
            next_token = None
            if len(result.data) == page_size:
                # If we got a full page, there might be more
                current_page = int(continuation_token) if continuation_token else 0
                next_token = str(current_page + 1)

            return result.data, next_token

        return ItemPaged(get_page)

    def _prepare_data_for_upload(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare data for upload by converting non-JSON serializable types.

        :param data: Raw data from query results
        :type data: List[Dict[str, Any]]
        :return: JSON-serializable data
        :rtype: List[Dict[str, Any]]
        """
        from decimal import Decimal

        def convert_value(value):
            """Convert a single value to JSON-serializable format."""
            if isinstance(value, datetime):
                # Convert datetime to ISO format string with microsecond precision
                return format_datetime_iso8601(value)
            elif isinstance(value, Decimal):
                # Convert Decimal to float
                return float(value)
            elif hasattr(value, "__dict__"):
                # Convert objects with __dict__ to dict representation
                return str(value)
            else:
                return value

        serializable_data = []
        for record in data:
            converted_record = {}
            for key, value in record.items():
                converted_record[key] = convert_value(value)
            serializable_data.append(converted_record)

        return serializable_data

    @distributed_trace_async
    async def upload_logs(
        self, data: List[Dict[str, Any]], stream_name: str, *, correlation_id: Optional[str] = None
    ) -> UploadResult:
        """
        Upload data to Azure Monitor via Data Collection Rule.

        :param data: List of log records to upload
        :type data: List[Dict[str, Any]]
        :param stream_name: DCR stream name
        :type stream_name: str
        :param correlation_id: Operation correlation ID
        :type correlation_id: Optional[str]
        :return: Upload result
        :rtype: UploadResult
        :raises DataIngestionError: If upload fails
        """
        correlation_id = correlation_id or generate_correlation_id()

        if not data:
            return UploadResult(
                status=UploadStatus.SKIPPED,
                record_count=0,
                upload_time=0.0,
                stream_name=stream_name,
                dcr_immutable_id=self._options.dcr_immutable_id,
                correlation_id=correlation_id,
            )

        # In dry-run mode, simulate successful upload without actually sending data
        if self._options.dry_run:
            self._logger.info(
                f"DRY-RUN: Would upload {len(data)} records to stream {stream_name} "
                f"[correlation_id={correlation_id}]"
            )
            return UploadResult(
                status=UploadStatus.SUCCESS,
                record_count=len(data),
                upload_time=0.0,  # No actual upload time in dry-run
                stream_name=stream_name,
                dcr_immutable_id=self._options.dcr_immutable_id,
                correlation_id=correlation_id,
            )

        # Validate stream name for security
        if not stream_name or not re.match(r"^[A-Za-z0-9_-]+$", stream_name):
            raise DataIngestionError("Invalid stream name format", stream_name=stream_name)

        start_upload = datetime.now(timezone.utc)

        try:
            # Transform data to ensure JSON serialization compatibility
            serializable_data = self._prepare_data_for_upload(data)

            response = await self._logs_ingestion_client_instance.upload(
                rule_id=self._options.dcr_immutable_id,
                stream_name=stream_name,
                logs=serializable_data,
            )

            upload_time = (datetime.now(timezone.utc) - start_upload).total_seconds()

            return UploadResult(
                status=UploadStatus.SUCCESS,
                record_count=len(data),
                upload_time=upload_time,
                stream_name=stream_name,
                dcr_immutable_id=self._options.dcr_immutable_id,
                correlation_id=correlation_id,
                request_id=getattr(response, "request_id", None),
            )

        except Exception as e:
            upload_time = (datetime.now(timezone.utc) - start_upload).total_seconds()
            error_msg = str(e)

            self._logger.error(
                f"Upload failed for stream {stream_name}: {error_msg} "
                f"[correlation_id={correlation_id}]"
            )

            return UploadResult(
                status=UploadStatus.FAILED,
                record_count=len(data),
                upload_time=upload_time,
                stream_name=stream_name,
                dcr_immutable_id=self._options.dcr_immutable_id,
                correlation_id=correlation_id,
                error_message=error_msg,
                error_code=getattr(e, "error_code", type(e).__name__),
            )

    @distributed_trace_async
    async def begin_batch_operation(
        self,
        workspaces: List[WorkspaceConfig],
        query_definition: KQLQueryDefinition,
        *,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> "BatchOperationPoller":
        """
        Begin a long-running batch operation across multiple workspaces.

        This method returns a poller that can be used to monitor the progress
        of the batch operation and retrieve results when complete.

        :param workspaces: List of workspace configurations
        :type workspaces: List[WorkspaceConfig]
        :param query_definition: KQL query definition to execute
        :type query_definition: KQLQueryDefinition
        :param start_time: Query time range start
        :type start_time: Optional[datetime]
        :param end_time: Query time range end
        :type end_time: Optional[datetime]
        :return: Batch operation poller
        :rtype: BatchOperationPoller
        """
        # Generate job correlation ID
        job_id = f"batch_{generate_correlation_id()[:8]}"

        # Create initial batch result
        batch_result = BatchExecutionResult(
            status=BatchStatus.PENDING,
            workspace_results=[],
            total_records=0,
            total_execution_time=0.0,
            job_correlation_id=job_id,
            start_time=datetime.now(timezone.utc),
            query_name=query_definition.name,
            report_name=getattr(query_definition, "report_name", None),
        )

        # Return a custom poller that manages the batch operation
        return BatchOperationPoller(
            client=self,
            workspaces=workspaces,
            query_definition=query_definition,
            start_time=start_time,
            end_time=end_time,
            initial_result=batch_result,
        )

    async def close(self) -> None:
        """Close client connections."""
        if self._logs_query_client:
            await self._logs_query_client.close()
        if self._logs_ingestion_client:
            await self._logs_ingestion_client.close()
        if self._credential and hasattr(self._credential, "close"):
            # Check if close method is async or sync
            close_method = getattr(self._credential, "close")
            if asyncio.iscoroutinefunction(close_method):
                await self._credential.close()
            else:
                # DefaultAzureCredential.close() is sync, not async
                self._credential.close()

    async def __aenter__(self) -> "SentinelAggregatorClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


class BatchOperationPoller:
    """
    Poller for long-running batch operations.

    Provides progress monitoring and result retrieval for batch operations
    that execute queries across multiple workspaces.
    """

    def __init__(
        self,
        client: SentinelAggregatorClient,
        workspaces: List[WorkspaceConfig],
        query_definition: KQLQueryDefinition,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        initial_result: BatchExecutionResult,
    ):
        self._client = client
        self._workspaces = workspaces
        self._query_definition = query_definition
        self._start_time = start_time
        self._end_time = end_time
        self._result = initial_result
        self._task: Optional[asyncio.Task] = None
        self._completed = False

    async def result(self, timeout: Optional[float] = None) -> BatchExecutionResult:
        """
        Get the final result of the batch operation.

        :param timeout: Maximum time to wait for completion
        :type timeout: Optional[float]
        :return: Batch execution result
        :rtype: BatchExecutionResult
        """
        if not self._task:
            self._task = asyncio.create_task(self._execute_batch())

        if timeout:
            await asyncio.wait_for(self._task, timeout=timeout)
        else:
            await self._task

        return self._result

    def done(self) -> bool:
        """Check if the operation is complete."""
        return self._completed

    def status(self) -> str:
        """Get current operation status."""
        return self._result.status.value

    async def _execute_batch(self) -> None:
        """Execute the batch operation."""
        self._result.status = BatchStatus.RUNNING

        try:
            workspace_results = []
            total_records = 0
            successful_workspaces = 0
            failed_workspaces = 0

            for workspace in self._workspaces:
                try:
                    # Execute query for this workspace
                    query_result = await self._client.query_workspace(
                        workspace_id=workspace.customer_id,
                        query=self._query_definition.get_query(),
                        start_time=self._start_time,
                        end_time=self._end_time,
                    )

                    # Upload results if query succeeded
                    upload_result = None
                    if query_result.succeeded and query_result.data:
                        upload_result = await self._client.upload_logs(
                            data=query_result.data,
                            stream_name=self._query_definition.destination_stream,
                        )

                    # Create workspace execution result
                    workspace_exec = WorkspaceQueryExecution(
                        workspace_id=workspace.customer_id,
                        workspace_alias=workspace.parameters.get(
                            "row_level_security_tag", workspace.customer_id
                        ),
                        query_result=query_result,
                        upload_result=upload_result,
                        correlation_id=self._result.job_correlation_id,
                    )

                    workspace_results.append(workspace_exec)
                    total_records += query_result.record_count

                    if workspace_exec.succeeded:
                        successful_workspaces += 1
                    else:
                        failed_workspaces += 1

                except Exception:
                    # Handle workspace-level errors
                    failed_workspaces += 1
                    # Add error handling as needed

            # Update final result
            self._result.workspace_results = workspace_results
            self._result.total_records = total_records
            self._result.successful_workspaces = successful_workspaces
            self._result.failed_workspaces = failed_workspaces
            self._result.end_time = datetime.now(timezone.utc)
            self._result.total_execution_time = (
                self._result.end_time - self._result.start_time
            ).total_seconds()

            # Set final status
            if failed_workspaces == 0:
                self._result.status = BatchStatus.SUCCESS
            elif successful_workspaces == 0:
                self._result.status = BatchStatus.FAILED
            else:
                self._result.status = BatchStatus.PARTIAL_SUCCESS

        except Exception:
            self._result.status = BatchStatus.FAILED
            # Add error details to result

        finally:
            self._completed = True
