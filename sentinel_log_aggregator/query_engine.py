"""
Query execution engine for Microsoft Sentinel Log Aggregator.

This module provides the core query execution functionality using Azure SDK-compliant
patterns, including batch processing, time range management, and data transformation
for centralized reporting.
"""

import asyncio
import gc
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from .health_logger import SentinelAggregatorHealthLogger

from .client_options import SentinelAggregatorClientOptions
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
        health_logger: Optional["SentinelAggregatorHealthLogger"] = None,
    ):
        """
        Initialize query engine.

        Args:
            client_options: Azure SDK-compliant client options
            azure_client: Azure SDK-compliant Sentinel client for queries and ingestion
            health_logger: Optional health logger for operational monitoring
        """
        self.client_options = client_options
        self.azure_client = azure_client
        self.health_logger = health_logger

        # Generate unique job correlation ID
        self.job_correlation_id = f"{uuid.uuid4()}"

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
            batches.append((current_time, batch_end))
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

        time_range_str = (
            f"{end_time.strftime('%Y-%m-%d %H:%M')} to {start_time.strftime('%Y-%m-%d %H:%M')}"
        )

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
                        resource_id=f"/subscriptions/unknown/resourceGroups/unknown/providers/Microsoft.OperationalInsights/workspaces/{workspace_alias}",
                        customer_id=workspace_id,
                        queries_list=[],
                        parameters={},
                    ),
                )

            # Execute query using Azure SDK-compliant method
            query_result = await self.azure_client.query_workspace(
                workspace_id=workspace_id, query=query, start_time=start_time, end_time=end_time
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

                # Upload data if results exist
                if query_result.data:
                    upload_start_time = time.time()

                    # Transform data for upload (add metadata fields)
                    transformed_data = self._transform_data_for_upload(
                        query_result.data, workspace_id
                    )

                    # Upload using Azure SDK-compliant method
                    upload_result = await self.azure_client.upload_logs(
                        data=transformed_data, stream_name=destination_stream
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
            else:
                # Query failed
                execution.query_status = QueryStatus.FAILED.value
                execution.query_error_message = query_result.error_message
                execution.query_duration_seconds = query_result.execution_time
                execution.upload_status = UploadStatus.SKIPPED.value
                self.logger.query_end(
                    query_name, workspace_alias, 0, query_result.execution_time, success=False
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
                transformed_record["TimeGenerated"] = datetime.now(timezone.utc).isoformat()

            if "WorkspaceId" not in transformed_record:
                transformed_record["WorkspaceId"] = workspace_id

            # Add processing metadata
            transformed_record["ProcessedBy"] = "SentinelLogAggregator"
            transformed_record["ProcessingTimestamp"] = datetime.now(timezone.utc).isoformat()
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

        self.logger.info(f"🚀 Starting batch execution with job ID: {job_id}")

        # Calculate execution time ranges using new time range calculator
        from .time_range_calculator import (
            calculate_execution_time_ranges,
            calculate_execution_batches,
        )

        try:
            start_time, end_time, batch_size = await calculate_execution_time_ranges(
                client_options=self.client_options,
                workspaces=workspace_configs,
                health_logger=self.health_logger,
            )

            # Calculate time batches
            time_batches = calculate_execution_batches(start_time, end_time, batch_size)

        except Exception as e:
            self.logger.error(f"❌ Failed to calculate execution time ranges: {e}")
            return BatchExecutionSummary(
                job_id=job_id,
                batch_id=batch_id,
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                total_duration=0.0,
                total_workspaces=len(workspace_configs),
                total_queries=0,
                successful_executions=0,
                failed_executions=0,
                total_records_processed=0,
                success_rate=0.0,
                executions=[],
            )

        self.logger.batch_start(
            total_days=(end_time - start_time).days,
            batch_hours=int(batch_size.total_seconds() / 3600),
            workspace_count=len(workspace_configs),
        )

        # Collect all query tasks
        all_tasks = []

        for workspace in workspace_configs:
            workspace_id = workspace.customer_id
            queries_list = workspace.queries_list
            workspace_alias = workspace.parameters.get("row_level_security_tag", workspace_id)

            # Log workspace processing start
            if self.health_logger:
                await self.health_logger.log_workspace_processing_start(
                    job_id=job_id,
                    workspace_config=workspace,
                    query_names=[
                        q.get("name", q.get("query_name", "unknown")) for q in queries_list
                    ],
                )

            for query_config in queries_list:
                # Handle both dict and string query configurations
                if isinstance(query_config, dict):
                    query_name = query_config.get("name", query_config.get("query_name", "unknown"))
                else:
                    query_name = str(query_config)

                # Check if this is a file path or a query name
                query_instance = None
                actual_query_name = query_name

                if query_name in AVAILABLE_QUERIES:
                    # Query already loaded by name
                    query_instance = AVAILABLE_QUERIES[query_name]
                elif query_name.endswith(".yaml") or query_name.endswith(".yml"):
                    # This looks like a file path, try to load it
                    from pathlib import Path

                    from .query_registry import QueryRegistry

                    query_file = Path(query_name)
                    if query_file.exists():
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
                                    f"Loaded query '{loaded_query_name}' from file '{query_file}'"
                                )
                            else:
                                self.logger.error(
                                    "QUERY_LOAD_EMPTY", f"No queries found in file '{query_file}'"
                                )
                                continue
                        except Exception as e:
                            self.logger.error(
                                "QUERY_LOAD_FILE",
                                f"Failed to load query from file '{query_file}': {e}",
                            )
                            continue
                    else:
                        self.logger.error(
                            "QUERY_FILE_NOT_FOUND", f"Query file not found: '{query_file}'"
                        )
                        continue
                else:
                    # Not a file path and not in AVAILABLE_QUERIES
                    self.logger.warning(
                        f"Query '{query_name}' not found in AVAILABLE_QUERIES and not a file path"
                    )
                    continue

                if query_instance:
                    try:
                        # Build query with workspace-specific parameters
                        query_parameters = workspace.parameters.copy()

                        parameterized_query = self.build_query_with_parameters(
                            actual_query_name, query_parameters
                        )

                        # Get destination stream from the query instance
                        destination_stream = query_instance.destination_stream

                        self.logger.debug(
                            f"Built query '{actual_query_name}' for workspace {workspace_alias}"
                        )

                        # Create tasks for each time batch
                        for batch_start, batch_end in time_batches:
                            execution_id = f"{batch_id}_{workspace_id[:8]}_{actual_query_name}_{batch_start.strftime('%Y%m%d_%H')}"

                            task = self.execute_single_query_with_upload(
                                workspace_id=workspace_id,
                                query=parameterized_query,
                                query_name=actual_query_name,
                                destination_stream=destination_stream,
                                start_time=batch_start,
                                end_time=batch_end,
                                execution_id=execution_id,
                                workspace_alias=workspace_alias,
                            )
                            all_tasks.append(task)

                    except Exception as e:
                        self.logger.error("QUERY_BUILD", str(e), query_name=actual_query_name)

                        # Create failed execution record
                        failed_execution = QueryExecution(
                            job_correlation_id=self.job_correlation_id,
                            execution_id=f"{batch_id}_{workspace_id[:8]}_{actual_query_name}_failed",
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

        # Execute in batches with concurrent limit
        batch_size = self.client_options.max_concurrent_queries
        critical_error_detected = False
        completed_tasks = 0

        for i in range(0, len(all_tasks), batch_size):
            if critical_error_detected:
                self.logger.error("CRITICAL", "Critical errors detected - stopping execution")
                break

            batch_tasks = all_tasks[i : i + batch_size]

            try:
                results = await asyncio.gather(*batch_tasks, return_exceptions=True)

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
                    critical_error_detected = True
                    break

                completed_tasks += len(batch_tasks)
                self.logger.progress(completed_tasks, len(all_tasks))

                # Small delay between batches and force garbage collection
                await asyncio.sleep(1)
                gc.collect()

            except Exception as e:
                self.logger.error("BATCH_EXECUTION", str(e))
                break

        # Calculate final summary
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

                await self.health_logger.log_workspace_processing_end(
                    job_id=job_id,
                    workspace_config=workspace,
                    success=workspace_success,
                    records_processed=workspace_records,
                    duration_seconds=total_duration,  # Approximation since we don't track individual workspace duration
                )

        # Log detailed summary programmatically
        detailed_summary = summary.generate_detailed_summary()
        self.logger.batch_summary(detailed_summary)
        self.logger.workspace_query_details(detailed_summary["workspace_query_details"])

        if critical_error_detected:
            self.logger.error("CRITICAL_STOP", "EXECUTION STOPPED DUE TO CRITICAL ERRORS")
            self.logger.error("ACTION_REQUIRED", "Fix syntax errors in KQL queries before retrying")

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
