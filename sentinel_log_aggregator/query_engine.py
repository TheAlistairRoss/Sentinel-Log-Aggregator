"""
Query execution engine for Microsoft Sentinel Log Aggregator.

This module provides the core query execution functionality using Azure SDK-compliant
patterns, including batch processing, time range management, and data transformation
for centralized reporting.
"""

import asyncio
import gc
import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from .health_logger import SentinelAggregatorHealthLogger

from .client_options import SentinelAggregatorClientOptions
from .constants import SECONDS_PER_HOUR
from .logging_formatter import ContextualLogger
from .logging_utils import get_logger
from .models import (
    AVAILABLE_QUERIES,
    BatchExecutionSummary,
    KQLQueryDefinition,
    QueryExecution,
    QueryStatus,
    UploadStatus,
    WorkspaceConfig,
)
from .sentinel_client import SentinelAggregatorClient
from .time_utils import format_datetime_iso8601


class SentinelQueryEngine:
    """
    Core query execution engine for Sentinel log aggregation.

    Handles batch query execution across multiple workspaces with concurrent processing,
    automatic retry logic, and comprehensive error tracking using Azure SDK-compliant patterns.
    """

    def __init__(
        self,
        client_options: SentinelAggregatorClientOptions,
        azure_client: SentinelAggregatorClient,
        job_id: str,
        health_logger: Optional["SentinelAggregatorHealthLogger"] = None,
    ):
        """
        Initialize query engine.

        Args:
            client_options: Azure SDK-compliant client options
            azure_client: Azure SDK-compliant Sentinel client for queries and ingestion
            job_id: Job ID for correlation with health logs and tracking execution
            health_logger: Optional health logger for operational monitoring
        """
        self.client_options = client_options
        self.azure_client = azure_client
        self.health_logger = health_logger

        # Use provided job_id for correlation across all operations
        self.job_correlation_id = job_id

        # Set up logging with contextual formatter
        base_logger = get_logger(__name__)
        self.logger = ContextualLogger(base_logger, self.job_correlation_id)

        # Execution tracking
        self.execution_log: List[QueryExecution] = []

    def calculate_time_batches(
        self, days_back: int, batch_hours: int
    ) -> List[Tuple[datetime, datetime]]:
        """
        Calculate time range batches for query execution.

        Args:
            days_back: Number of days to go back from now
            batch_hours: Hours per batch (e.g., 24 for daily batches)

        Returns:
            List of (start_time, end_time) tuples, ordered newest first
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days_back)

        batches = []
        current_time = start_time

        while current_time < end_time:
            batch_end = min(current_time + timedelta(hours=batch_hours), end_time)
            # Subtract 1 microsecond from batch_end to prevent overlapping boundaries
            # Azure Monitor queries are inclusive on both start and end times
            # This ensures records at exact boundary timestamps don't appear in multiple batches
            # Exception: Don't subtract from the final end_time as it's already the desired boundary
            if batch_end < end_time:
                adjusted_batch_end = batch_end - timedelta(microseconds=1)
            else:
                adjusted_batch_end = batch_end
            batches.append((current_time, adjusted_batch_end))
            current_time = batch_end

        # Return batches in reverse order (newest first)
        batches.reverse()

        self.logger.info(f"Generated {len(batches)} time batches of {batch_hours}h each")
        return batches

    def build_query_with_parameters(
        self, query_name: str, parameters: Dict[str, Any] = None
    ) -> str:
        """
        Build KQL query with parameter substitution.

        Args:
            query_name: Name of the query to build
            parameters: Query parameters

        Returns:
            Built KQL query string

        Raises:
            ValueError: If query not found or required parameters missing
        """
        if query_name not in AVAILABLE_QUERIES:
            raise ValueError(f"Query '{query_name}' not found in available queries")

        query_instance = AVAILABLE_QUERIES[query_name]

        return query_instance.build_query(parameters or {})

    def build_query_from_name(self, query_name: str) -> str:
        """
        Build KQL query from query name (legacy method).

        Args:
            query_name: Name of the query to build

        Returns:
            Built KQL query string

        Raises:
            KeyError: If query not found
        """
        if query_name not in AVAILABLE_QUERIES:
            raise KeyError(f"Query '{query_name}' not found in available queries")

        query_instance = AVAILABLE_QUERIES[query_name]
        return query_instance.build_query({})

    async def execute_single_query_with_upload(
        self,
        workspace_id: str,
        query: str,
        query_name: str,
        destination_stream: str,
        start_time: datetime,
        end_time: datetime,
        execution_id: str,
        workspace_alias: str = "",
        workspace_resource_id: str = "",
        batch_id: Optional[str] = None,
    ) -> QueryExecution:
        """
        Execute a single query and upload results immediately.

        Args:
            workspace_id: Log Analytics workspace customer ID
            query: KQL query string
            query_name: Name of the query for tracking
            destination_stream: Target stream for data upload
            start_time: Query time range start
            end_time: Query time range end
            execution_id: Unique execution identifier
            workspace_alias: Short workspace identifier for logging
            workspace_resource_id: Full Azure resource ID for the workspace
            batch_id: Optional batch identifier for this query execution

        Returns:
            QueryExecution tracking object
        """
        # Initialize execution tracking
        execution = QueryExecution(
            job_correlation_id=self.job_correlation_id,
            execution_id=execution_id,
            workspace_id=workspace_id,
            query_name=query_name,
            destination_stream=destination_stream,
            start_time=start_time,
            end_time=end_time,
        )

        if not workspace_alias:
            workspace_alias = workspace_id

        try:
            time_range_str = (
                f"{start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}"
            )
        except (AttributeError, TypeError):
            # Handle cases where start_time/end_time might be mocks or invalid
            time_range_str = f"{str(start_time)} to {str(end_time)}"

        self.logger.debug(
            f"Executing query '{query_name}' for workspace {workspace_alias} ({workspace_id})"
        )
        self.logger.debug(f"Time range: {time_range_str}")
        self.logger.debug(f"Destination stream: {destination_stream}")

        # Log comprehensive query execution details as formatted JSON
        query_execution_details = {
            "operation": "query_execution",
            "workspace_resource_id": workspace_resource_id,
            "workspace_id": workspace_id,
            "workspace_alias": workspace_alias,
            "query_name": query_name,
            "start_time": (
                format_datetime_iso8601(start_time)
                if hasattr(start_time, "isoformat")
                else str(start_time)
            ),
            "end_time": (
                format_datetime_iso8601(end_time)
                if hasattr(end_time, "isoformat")
                else str(end_time)
            ),
            "destination_stream": destination_stream,
            "execution_id": execution_id,
        }
        self.logger.debug(
            f"Query execution metadata:\n{json.dumps(query_execution_details, indent=2)}"
        )

        # Log the KQL query separately with proper formatting
        self.logger.debug(f"KQL Query:\n{query}")

        query_response = None
        transformed_data = None

        try:
            # Execute query
            query_start_time = time.time()

            self.logger.query_start(query_name, workspace_alias, time_range_str)

            # Log query execution start to health logger
            if self.health_logger:
                await self.health_logger.log_query_execution(
                    job_id=self.job_correlation_id,
                    query_execution=execution,
                    workspace_config=WorkspaceConfig(
                        resource_id=workspace_resource_id
                        or f"/subscriptions/unknown/resourceGroups/unknown/providers/Microsoft.OperationalInsights/workspaces/{workspace_alias}",
                        customer_id=workspace_id,
                        queries_list=[],
                        parameters={},
                    ),
                    batch_id=batch_id,
                )

            # Execute query using Azure SDK-compliant method
            query_result = await self.azure_client.query_workspace(
                workspace_id=workspace_id, query=query, start_time=start_time, end_time=end_time
            )

            # Safely extract attributes for logging (handle potential mocks in tests)
            try:
                exec_time_str = f"{query_result.execution_time:.2f}s"
                exec_time_val = query_result.execution_time
            except (TypeError, ValueError, AttributeError):
                exec_time_str = str(getattr(query_result, "execution_time", "N/A"))
                exec_time_val = None

            query_completion = {
                "success": query_result.succeeded,
                "records": query_result.record_count,
                "duration_seconds": exec_time_val,
                "duration": exec_time_str,
            }
            self.logger.debug(
                f"Query execution completed:\n{json.dumps(query_completion, indent=2)}"
            )

            if query_result.succeeded:
                execution.query_status = QueryStatus.SUCCESS.value
                execution.query_duration_seconds = query_result.execution_time
                execution.record_count = query_result.record_count

                self.logger.query_end(
                    query_name,
                    workspace_alias,
                    execution.record_count,
                    query_result.execution_time,
                    success=True,
                )

                # Log first 5 rows of query results for debugging
                if query_result.data:
                    sample_data = query_result.data[:5]
                    self.logger.debug(
                        f"Query results (first {len(sample_data)} of {len(query_result.data)} rows):\n"
                        f"{json.dumps(sample_data, default=str, indent=2)}"
                    )

                # Upload data if results exist
                if query_result.data:
                    upload_start_time = time.time()

                    self.logger.debug(
                        f"🔄 Transforming {len(query_result.data)} records for upload..."
                    )

                    # Transform data for upload (add metadata fields)
                    transformed_data = self._transform_data_for_upload(
                        query_result.data, workspace_id
                    )

                    self.logger.debug(
                        f"Data transformed: {len(transformed_data)} records ready for upload"
                    )
                    self.logger.debug(f"Uploading to stream: {destination_stream}")

                    # Upload using Azure SDK-compliant method
                    upload_result = await self.azure_client.upload_logs(
                        data=transformed_data, stream_name=destination_stream
                    )

                    # Safely extract attributes for logging (handle potential mocks in tests)
                    try:
                        upload_time_str = f"{upload_result.upload_time:.2f}s"
                    except (TypeError, ValueError, AttributeError):
                        upload_time_str = str(getattr(upload_result, "upload_time", "N/A"))

                    self.logger.debug(
                        f"Upload completed: success={upload_result.succeeded}, "
                        f"records={upload_result.record_count}, duration={upload_time_str}"
                    )

                    if upload_result.succeeded:
                        execution.upload_status = UploadStatus.SUCCESS.value
                        execution.upload_duration_seconds = upload_result.upload_time
                        execution.uploaded_count = upload_result.record_count

                        self.logger.upload_end(
                            query_name,
                            workspace_alias,
                            upload_result.record_count,
                            upload_result.upload_time,
                            success=True,
                        )
                    else:
                        execution.upload_status = UploadStatus.FAILED.value
                        execution.upload_error_message = upload_result.error_message
                        self.logger.error(
                            "UPLOAD",
                            upload_result.error_message,
                            query_name=query_name,
                            workspace_alias=workspace_alias,
                        )

                else:
                    execution.upload_status = UploadStatus.SKIPPED.value
                    execution.uploaded_count = 0
                    self.logger.info(
                        f"No data to upload - Job: {self.job_correlation_id} | Query: {query_name} | Workspace: {workspace_alias}"
                    )
                    self.logger.debug(
                        f"Skipping upload for query '{query_name}' - no data returned"
                    )
            else:
                # Query failed
                execution.query_status = QueryStatus.FAILED.value
                execution.query_error_message = query_result.error_message
                execution.query_duration_seconds = query_result.execution_time
                execution.upload_status = UploadStatus.SKIPPED.value
                self.logger.query_end(
                    query_name, workspace_alias, 0, query_result.execution_time, success=False
                )
                self.logger.debug(
                    f"Query '{query_name}' failed: {query_result.error_message[:100]}..."
                )

        except Exception as e:
            execution.query_status = QueryStatus.FAILED.value
            execution.query_error_message = f"Error: {str(e)}"
            execution.query_duration_seconds = time.time() - query_start_time
            execution.upload_status = UploadStatus.SKIPPED.value

            # Enhanced error logging with classification
            error_type = type(e).__name__
            self.logger.error(
                "QUERY_ENGINE",
                str(e),
                query_name=query_name,
                workspace_alias=workspace_alias,
                error_type=error_type,
            )
            # Log exception traceback at debug level
            import traceback

            self.logger.debug(
                f"💥 Exception details for query '{query_name}': {traceback.format_exc()}"
            )

        finally:
            # Cleanup memory
            if query_response is not None:
                del query_response
            if transformed_data is not None:
                del transformed_data
            gc.collect()

            # Log final query execution status to health logger
            if self.health_logger:
                await self.health_logger.log_query_execution(
                    job_id=self.job_correlation_id,
                    query_execution=execution,
                    workspace_config=WorkspaceConfig(
                        resource_id=f"/subscriptions/unknown/resourceGroups/unknown/providers/Microsoft.OperationalInsights/workspaces/{workspace_alias}",
                        customer_id=workspace_id,
                        queries_list=[],
                        parameters={},
                    ),
                    batch_id=batch_id,
                )

        self.execution_log.append(execution)
        return execution

    def _transform_data_for_upload(
        self, data: List[Dict[str, Any]], workspace_id: str
    ) -> List[Dict[str, Any]]:
        """
        Transform query results for upload to Azure Monitor.

        Args:
            data: Raw query results
            workspace_id: Source workspace ID

        Returns:
            Transformed data ready for upload
        """
        transformed = []

        for record in data:
            # Create a copy to avoid modifying original
            transformed_record = record.copy()

            # Ensure required metadata fields
            if "TimeGenerated" not in transformed_record:
                transformed_record["TimeGenerated"] = format_datetime_iso8601(
                    datetime.now(timezone.utc)
                )

            if "WorkspaceId" not in transformed_record:
                transformed_record["WorkspaceId"] = workspace_id

            # Add processing metadata
            transformed_record["ProcessedBy"] = "SentinelLogAggregator"
            transformed_record["ProcessingTimestamp"] = format_datetime_iso8601(
                datetime.now(timezone.utc)
            )
            transformed_record["JobCorrelationId"] = self.job_correlation_id

            transformed.append(transformed_record)

        return transformed

    async def execute_batch_queries_with_streaming_upload(
        self,
        workspace_configs: List[WorkspaceConfig],
        job_id: str = None,
    ) -> BatchExecutionSummary:
        """
        Execute all queries for all workspaces with immediate streaming upload.

        Args:
            workspace_configs: List of workspace configurations
            job_id: Optional job ID for health logging correlation

        Returns:
            BatchExecutionSummary with execution results
        """
        batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        batch_start_time = time.time()
        job_id = job_id or self.job_correlation_id

        self.logger.info(f"Starting batch execution with job ID: {job_id}")
        self.logger.debug(f"Batch ID: {batch_id}")
        self.logger.debug(
            f"Client options: dry_run={getattr(self.client_options, 'dry_run', False)}"
        )

        # Early validation of workspace configurations
        self.logger.debug(f"Validating {len(workspace_configs)} workspace configurations...")
        for idx, workspace in enumerate(workspace_configs):
            self.logger.debug(
                f"  Workspace {idx + 1}: {workspace.customer_id} with {len(workspace.queries_list)} queries"
            )
            if not workspace.queries_list:
                self.logger.warning(f"Workspace {workspace.customer_id} has no queries configured!")

        # Calculate execution time ranges using new time range calculator
        from .time_range_calculator import (
            calculate_execution_batches,
            calculate_execution_time_ranges,
        )

        try:
            self.logger.debug("Calculating execution time ranges...")
            start_time, end_time, batch_size = await calculate_execution_time_ranges(
                client_options=self.client_options,
                workspaces=workspace_configs,
                health_logger=self.health_logger,
                job_id=self.job_correlation_id,
            )

            self.logger.debug(f"Time range calculated: {start_time} to {end_time}")
            self.logger.debug(f"📏 Batch size: {batch_size}")

            # Calculate time batches
            time_batches = calculate_execution_batches(start_time, end_time, batch_size)
            self.logger.debug(f"Generated {len(time_batches)} time batches")

        except Exception as e:
            self.logger.error("TIME_RANGE_CALC", f"Failed to calculate execution time ranges: {e}")
            # Log exception traceback at debug level
            import traceback

            self.logger.debug(f"Time range calculation exception: {traceback.format_exc()}")
            return BatchExecutionSummary(
                job_correlation_id=self.job_correlation_id,
                batch_id=batch_id,
                notebook_run_timestamp=datetime.now(timezone.utc),
                total_queries=0,
                successful_queries=0,
                failed_queries=0,
                successful_uploads=0,
                failed_uploads=0,
                total_records=0,
                total_uploaded_records=0,
                total_duration_seconds=0.0,
                time_range_start=datetime.now(timezone.utc),
                time_range_end=datetime.now(timezone.utc),
                executions=[],
            )

        self.logger.batch_start(
            total_days=(end_time - start_time).days,
            batch_hours=int(batch_size.total_seconds() / SECONDS_PER_HOUR),
            workspace_count=len(workspace_configs),
        )

        # Collect all query tasks
        all_tasks = []

        for workspace in workspace_configs:
            workspace_id = workspace.customer_id
            queries_list = workspace.queries_list

            # Extract workspace name from resource ID with validation
            try:
                resource_parts = workspace.resource_id.split("/")
                if len(resource_parts) >= 9 and resource_parts[8]:
                    workspace_alias = resource_parts[8]
                    self.logger.debug(
                        f"Extracted workspace alias: {workspace_alias} from resource ID"
                    )
                else:
                    self.logger.warning(
                        f"Malformed resource ID: {workspace.resource_id}, using workspace ID as alias"
                    )
                    workspace_alias = workspace_id
            except (IndexError, AttributeError):
                self.logger.warning(
                    f"Failed to extract workspace name from resource ID: {workspace.resource_id}, using workspace ID as alias"
                )
                workspace_alias = workspace_id

            self.logger.debug(
                f"Processing workspace: {workspace_alias} with {len(queries_list)} queries"
            )
            self.logger.debug(
                f"Query configuration types: {[type(q).__name__ for q in queries_list]}"
            )

            # Extract query names for health logging - handle both string and dict formats
            query_names_for_logging = []
            for q in queries_list:
                if isinstance(q, dict):
                    query_names_for_logging.append(q.get("name", q.get("query_name", "unknown")))
                elif isinstance(q, str):
                    # If it's a file path, extract just the filename without extension
                    if q.endswith((".yaml", ".yml")):
                        from pathlib import Path

                        query_names_for_logging.append(Path(q).stem)
                    else:
                        query_names_for_logging.append(q)
                else:
                    query_names_for_logging.append(str(q))

            self.logger.debug(
                f"Query names for workspace {workspace_alias}: {query_names_for_logging}"
            )

            # Log workspace processing start
            if self.health_logger:
                await self.health_logger.log_workspace_processing_start(
                    job_id=job_id,
                    workspace_config=workspace,
                    query_names=query_names_for_logging,
                )

            for query_config in queries_list:
                # Handle both dict and string query configurations
                if isinstance(query_config, dict):
                    query_name = query_config.get("name", query_config.get("query_name", "unknown"))
                    self.logger.debug(
                        f"📘 Query config is dictionary - extracted name: {query_name}"
                    )
                else:
                    query_name = str(query_config)
                    self.logger.debug(f"Query config is string/path: {query_name}")

                # Early validation
                if not query_name or query_name == "unknown":
                    self.logger.error(
                        "QUERY_CONFIG",
                        f"Invalid query configuration: {query_config}. Query name could not be determined.",
                    )
                    continue

                # Check if this is a file path or a query name
                query_instance = None
                actual_query_name = query_name

                if query_name in AVAILABLE_QUERIES:
                    # Query already loaded by name
                    query_instance = AVAILABLE_QUERIES[query_name]
                    self.logger.debug(f"Found query '{query_name}' in AVAILABLE_QUERIES registry")
                elif query_name.endswith(".yaml") or query_name.endswith(".yml"):
                    # This looks like a file path, try to load it
                    from pathlib import Path

                    from .query_registry import QueryRegistry

                    query_file = Path(query_name)
                    self.logger.debug(f"📂 Attempting to load query from file: {query_file}")

                    if query_file.exists():
                        self.logger.debug(f"Query file exists: {query_file}")
                        try:
                            # Create a temporary registry to load this query
                            temp_registry = QueryRegistry()
                            temp_registry.load_from_yaml(query_file)

                            # Get the loaded query - it should be the only one
                            loaded_queries = temp_registry.list_queries()
                            if loaded_queries:
                                loaded_query_name = loaded_queries[0]
                                query_instance = temp_registry.get_query(loaded_query_name)
                                actual_query_name = loaded_query_name

                                # Register it in AVAILABLE_QUERIES for future use
                                AVAILABLE_QUERIES[loaded_query_name] = query_instance

                                self.logger.debug(
                                    f"Successfully loaded query '{loaded_query_name}' from file '{query_file}'"
                                )
                                query_details = {
                                    "query_name": loaded_query_name,
                                    "destination_stream": query_instance.destination_stream,
                                    "parameters": list(query_instance.parameters.keys()),
                                }
                                self.logger.debug(
                                    f"Query details:\n{json.dumps(query_details, indent=2)}"
                                )
                            else:
                                self.logger.error(
                                    "QUERY_LOAD_EMPTY",
                                    f"No queries found in file '{query_file}'. File may be empty or improperly formatted.",
                                )
                                continue
                        except Exception as e:
                            self.logger.error(
                                "QUERY_LOAD_FILE",
                                f"Failed to load query from file '{query_file}': {e}",
                            )
                            # Log exception traceback at debug level
                            import traceback

                            self.logger.debug(f"Query load exception: {traceback.format_exc()}")
                            continue
                    else:
                        self.logger.error(
                            "QUERY_FILE_NOT_FOUND",
                            f"Query file not found: '{query_file}'. Ensure the path is correct and relative to the current working directory.",
                        )
                        self.logger.debug(f"Current working directory: {Path.cwd()}")
                        self.logger.debug(f"Absolute path attempted: {query_file.absolute()}")
                        continue
                else:
                    # Not a file path and not in AVAILABLE_QUERIES
                    self.logger.error(
                        "QUERY_NOT_FOUND",
                        f"Query '{query_name}' not found in AVAILABLE_QUERIES registry and is not a valid file path. Available queries: {list(AVAILABLE_QUERIES.keys())}",
                    )
                    continue

                if not query_instance:
                    self.logger.error(
                        "QUERY_INSTANCE",
                        f"Failed to load query instance for '{query_name}'. Skipping this query.",
                    )
                    continue

                if query_instance:
                    try:
                        # Build query with workspace-specific parameters
                        query_parameters = workspace.parameters.copy()
                        self.logger.debug(
                            f"Building query '{actual_query_name}' with parameters: {list(query_parameters.keys())}"
                        )

                        parameterized_query = self.build_query_with_parameters(
                            actual_query_name, query_parameters
                        )

                        # Get destination stream from the query instance
                        destination_stream = query_instance.destination_stream

                        self.logger.debug(
                            f"Built query '{actual_query_name}' for workspace {workspace_alias}"
                        )
                        self.logger.debug(f"Target stream: {destination_stream}")

                        # Create tasks for each time batch
                        batch_list = []
                        for batch_idx, (batch_start, batch_end) in enumerate(time_batches):
                            try:
                                execution_id = f"{batch_id}_{workspace_id}_{actual_query_name}_{batch_start.strftime('%Y%m%d_%H')}"
                            except (AttributeError, TypeError):
                                # Handle mock objects or invalid datetime
                                execution_id = f"{batch_id}_{workspace_id}_{actual_query_name}_batch{batch_idx}"

                            if batch_idx < 3 or batch_idx >= len(time_batches) - 3:
                                # Log first 3 and last 3 batches in debug mode
                                try:
                                    from datetime import timedelta

                                    time_period = batch_end - batch_start
                                    batch_info = {
                                        "Index": batch_idx + 1,
                                        "StartTime": batch_start.isoformat(),
                                        "EndTime": batch_end.isoformat(),
                                        "TimePeriod": str(time_period),
                                    }
                                except (AttributeError, TypeError):
                                    batch_info = {
                                        "Index": batch_idx + 1,
                                        "StartTime": str(batch_start),
                                        "EndTime": str(batch_end),
                                        "TimePeriod": "unknown",
                                    }
                                batch_list.append(batch_info)

                            task = self.execute_single_query_with_upload(
                                workspace_id=workspace_id,
                                query=parameterized_query,
                                query_name=actual_query_name,
                                destination_stream=destination_stream,
                                start_time=batch_start,
                                end_time=batch_end,
                                execution_id=execution_id,
                                workspace_alias=workspace_alias,
                                workspace_resource_id=workspace.resource_id,
                                batch_id=batch_id,
                            )
                            all_tasks.append(task)

                        # Log batch information as JSON array
                        if batch_list:
                            self.logger.debug(
                                f"Created {len(time_batches)} batch tasks for query '{actual_query_name}':\n{json.dumps(batch_list, indent=2)}"
                            )

                    except Exception as e:
                        self.logger.error(
                            "QUERY_BUILD",
                            f"Failed to build query '{actual_query_name}': {e}",
                        )
                        # Log exception traceback at debug level
                        import traceback

                        self.logger.debug(f"Query build exception: {traceback.format_exc()}")

                        # Create failed execution record
                        failed_execution = QueryExecution(
                            job_correlation_id=self.job_correlation_id,
                            execution_id=f"{batch_id}_{workspace_id}_{actual_query_name}_failed",
                            workspace_id=workspace_id,
                            query_name=actual_query_name,
                            destination_stream=query_instance.destination_stream,
                            start_time=datetime.now(timezone.utc),
                            end_time=datetime.now(timezone.utc),
                            execution_timestamp=datetime.now(timezone.utc),
                            query_status=QueryStatus.FAILED.value,
                            upload_status=UploadStatus.SKIPPED.value,
                            query_error_message=f"Query build error: {str(e)}",
                        )
                        self.execution_log.append(failed_execution)

        self.logger.info(f"Total operations scheduled: {len(all_tasks)}")
        self.logger.debug(
            f"Execution configuration: max_concurrent={self.client_options.max_concurrent_queries}"
        )

        # Execute in batches with concurrent limit
        batch_size = self.client_options.max_concurrent_queries
        critical_error_detected = False
        completed_tasks = 0

        for i in range(0, len(all_tasks), batch_size):
            if critical_error_detected:
                self.logger.error("CRITICAL_STOP", "Critical errors detected - stopping execution")
                break

            batch_tasks = all_tasks[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(all_tasks) // batch_size) + 1

            self.logger.info(
                f"Executing batch {batch_num}/{total_batches} ({len(batch_tasks)} tasks)"
            )
            self.logger.debug(
                f"Batch details: tasks {i + 1}-{min(i + batch_size, len(all_tasks))} of {len(all_tasks)}"
            )

            try:
                self.logger.debug(
                    f"🔄 Starting concurrent execution of {len(batch_tasks)} tasks..."
                )
                results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                # Log any exceptions from the batch
                exception_count = 0
                for idx, result in enumerate(results):
                    if isinstance(result, Exception):
                        exception_count += 1
                        self.logger.error(
                            "TASK_EXCEPTION",
                            f"Task {i + idx + 1} failed with exception: {result}",
                        )
                        self.logger.debug(f"Exception details:", exc_info=result)

                if exception_count > 0:
                    self.logger.warning(
                        f"{exception_count}/{len(results)} tasks in batch failed with exceptions"
                    )

                self.logger.debug(f"Batch {batch_num} completed: {len(results)} results processed")

                # Check for critical syntax errors
                recent_executions = self.execution_log[-len(batch_tasks) :]
                syntax_errors = [
                    e
                    for e in recent_executions
                    if e.query_status == QueryStatus.FAILED.value
                    and any(
                        error_type in e.query_error_message
                        for error_type in [
                            "BadArgumentError",
                            "QueryCompilationError",
                            "SyntaxError",
                            "SemanticError",
                        ]
                    )
                ]

                if syntax_errors:
                    self.logger.error(
                        "SYNTAX",
                        f"{len(syntax_errors)} syntax error(s) detected - stopping execution",
                    )
                    for error_exec in syntax_errors:
                        self.logger.error(
                            "SYNTAX_DETAIL",
                            error_exec.query_error_message,
                            query_name=error_exec.query_name,
                        )
                        self.logger.debug(
                            f"Syntax error query: {error_exec.query_name} on workspace {error_exec.workspace_id}"
                        )
                    critical_error_detected = True
                    break

                completed_tasks += len(batch_tasks)
                self.logger.progress(completed_tasks, len(all_tasks))
                self.logger.debug(
                    f"📈 Progress: {completed_tasks}/{len(all_tasks)} tasks completed ({completed_tasks * 100 // len(all_tasks)}%)"
                )

                # Small delay between batches and force garbage collection
                await asyncio.sleep(1)
                gc.collect()
                self.logger.debug("🧹 Performed garbage collection between batches")

            except Exception as e:
                self.logger.error("BATCH_EXECUTION", str(e))
                # Log exception traceback at debug level
                import traceback

                self.logger.debug(f"Batch execution exception: {traceback.format_exc()}")
                break

        # Calculate final summary
        self.logger.debug("Calculating execution summary...")
        all_executions = self.execution_log
        successful_queries = len(
            [e for e in all_executions if e.query_status == QueryStatus.SUCCESS.value]
        )
        failed_queries = len(
            [e for e in all_executions if e.query_status == QueryStatus.FAILED.value]
        )
        successful_uploads = len(
            [e for e in all_executions if e.upload_status == UploadStatus.SUCCESS.value]
        )
        failed_uploads = len(
            [e for e in all_executions if e.upload_status == UploadStatus.FAILED.value]
        )
        total_records = sum(e.record_count for e in all_executions)
        total_uploaded_records = sum(e.uploaded_count for e in all_executions)
        total_duration = time.time() - batch_start_time

        self.logger.debug(
            f"📈 Summary stats: {successful_queries} successful, {failed_queries} failed queries"
        )
        self.logger.debug(
            f"Upload stats: {successful_uploads} successful, {failed_uploads} failed uploads"
        )
        self.logger.debug(
            f"Record stats: {total_records} total records, {total_uploaded_records} uploaded"
        )
        self.logger.debug(f"Total duration: {total_duration:.2f}s")

        summary = BatchExecutionSummary(
            job_correlation_id=self.job_correlation_id,
            batch_id=batch_id,
            notebook_run_timestamp=datetime.now(timezone.utc),
            total_queries=len(all_tasks),
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            successful_uploads=successful_uploads,
            failed_uploads=failed_uploads,
            total_records=total_records,
            total_uploaded_records=total_uploaded_records,
            total_duration_seconds=total_duration,
            time_range_start=time_batches[0][0] if time_batches else datetime.now(timezone.utc),
            time_range_end=time_batches[-1][1] if time_batches else datetime.now(timezone.utc),
            executions=all_executions,
        )

        self.logger.debug("Batch execution summary created")

        # Log execution summary using standardized formatter
        summary_data = {
            "successful_queries": successful_queries,
            "total_queries": len(all_tasks),
            "successful_uploads": successful_uploads,
            "total_uploads": successful_uploads + failed_uploads,
            "total_records": total_records,
            "total_uploaded": total_uploaded_records,
            "total_duration": total_duration,
        }
        self.logger.batch_end(summary_data)

        self.logger.debug("Logging workspace processing completion to health logger...")
        # Log workspace processing completion to health logger
        if self.health_logger:
            for workspace in workspace_configs:
                # Calculate workspace-specific metrics
                workspace_executions = [
                    e for e in all_executions if e.workspace_id == workspace.customer_id
                ]
                workspace_records = sum(e.record_count or 0 for e in workspace_executions)
                workspace_success = all(
                    e.query_status == QueryStatus.SUCCESS.value for e in workspace_executions
                )

                self.logger.debug(
                    f"Workspace {workspace.customer_id}: {len(workspace_executions)} executions, "
                    f"{workspace_records} records, success={workspace_success}"
                )

                await self.health_logger.log_workspace_processing_end(
                    job_id=job_id,
                    workspace_config=workspace,
                    success=workspace_success,
                    records_processed=workspace_records,
                    duration_seconds=total_duration,  # Approximation since we don't track individual workspace duration
                )
                self.logger.debug(f"Health log completed for workspace {workspace.customer_id}")

        # Log detailed summary programmatically
        self.logger.debug("Generating and logging detailed summary...")
        detailed_summary = summary.generate_detailed_summary()
        self.logger.batch_summary(detailed_summary)
        self.logger.workspace_query_details(detailed_summary["workspace_query_details"])

        if critical_error_detected:
            self.logger.error("CRITICAL_STOP", "EXECUTION STOPPED DUE TO CRITICAL ERRORS")
            self.logger.error("ACTION_REQUIRED", "Fix syntax errors in KQL queries before retrying")
            self.logger.debug("⛔ Critical error flag was set during execution")

        self.logger.info(f"Batch execution complete: {batch_id}")
        self.logger.debug(
            f"Final summary: {successful_queries}/{len(all_tasks)} queries successful"
        )
        return summary

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of current execution session."""
        if not self.execution_log:
            return {"message": "No executions recorded"}

        successful_queries = len(
            [e for e in self.execution_log if e.query_status == QueryStatus.SUCCESS.value]
        )
        failed_queries = len(
            [e for e in self.execution_log if e.query_status == QueryStatus.FAILED.value]
        )
        total_records = sum(e.record_count for e in self.execution_log)
        total_uploaded = sum(e.uploaded_count for e in self.execution_log)

        return {
            "job_correlation_id": self.job_correlation_id,
            "total_executions": len(self.execution_log),
            "successful_queries": successful_queries,
            "failed_queries": failed_queries,
            "success_rate": (
                (successful_queries / len(self.execution_log)) * 100 if self.execution_log else 0
            ),
            "total_records_retrieved": total_records,
            "total_records_uploaded": total_uploaded,
        }
