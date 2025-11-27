"""
Sentinel Log Aggregator Health Logger

Provides comprehensive health and operational logging to Log Analytics tables
for monitoring job execution, query performance, and workspace processing.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .constants import HEALTH_STREAM_NAME
from .models import QueryExecution, WorkspaceConfig
from .sentinel_client import SentinelAggregatorClient
from .time_utils import format_datetime_iso8601

logger = logging.getLogger(__name__)


class SentinelAggregatorHealthLogger:
    """
    Health logger for comprehensive operational monitoring.

    Logs job execution, query performance, workspace processing, and errors
    to the SentinelAggregatorHealth_CL Log Analytics table.
    """

    def __init__(
        self,
        sentinel_client: SentinelAggregatorClient,
        enabled: bool = True,
        health_to_sentinel: bool = False,
    ):
        """
        Initialize the health logger.

        Args:
            sentinel_client: Configured Sentinel client for Log Analytics ingestion
            enabled: Whether health logging is enabled
            health_to_sentinel: Whether to send health logs to Sentinel table (vs console only)
        """
        self.sentinel_client = sentinel_client
        self.enabled = enabled
        self.health_to_sentinel = health_to_sentinel
        self.health_stream_name = HEALTH_STREAM_NAME

        if self.enabled and not self.health_to_sentinel:
            logger.info("Health logging enabled - console only (not sent to Sentinel)")
        elif self.enabled and self.health_to_sentinel:
            logger.info("Health logging enabled - sending to Sentinel table")
        else:
            logger.debug("Health logging disabled")

        logger.debug(
            f"Health logger initialized - enabled: {enabled}, to_sentinel: {health_to_sentinel}"
        )

    async def log_job_start(
        self, job_id: str, job_type: str, workspace_count: int, query_count: int, **kwargs
    ) -> None:
        """
        Log job start event.

        Args:
            job_id: Unique job identifier
            job_type: Type of job (e.g., 'batch_execution', 'single_query')
            workspace_count: Number of workspaces to process
            query_count: Number of queries to execute
            **kwargs: Additional properties to include in ExtendedProperties
        """
        if not self.enabled:
            return

        extended_properties = {
            "workspace_count": workspace_count,
            "query_count": query_count,
            **kwargs,
        }

        await self._log_health_event(
            operation_name="JobStart",
            operation_status="Started",
            job_id=job_id,
            extended_properties=extended_properties,
        )

    async def log_job_end(
        self,
        job_id: str,
        job_type: str,
        success: bool,
        total_records_processed: int = 0,
        total_duration_seconds: float = 0.0,
        error_message: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Log job completion event.

        Args:
            job_id: Unique job identifier
            job_type: Type of job
            success: Whether job completed successfully
            total_records_processed: Total records processed across all queries
            total_duration_seconds: Total job execution time
            error_message: Error message if job failed
            **kwargs: Additional properties to include in ExtendedProperties
        """
        if not self.enabled:
            return

        extended_properties = {
            "total_records_processed": total_records_processed,
            "total_duration_seconds": total_duration_seconds,
            **kwargs,
        }

        await self._log_health_event(
            operation_name="JobEnd",
            operation_status="Completed" if success else "Failed",
            job_id=job_id,
            operation_status_reason=error_message,
            extended_properties=extended_properties,
        )

    async def log_query_execution(
        self,
        job_id: str,
        query_execution: QueryExecution,
        workspace_config: WorkspaceConfig,
        batch_id: Optional[str] = None,
    ) -> None:
        """
        Log individual query execution details.

        Args:
            job_id: Job identifier this query belongs to
            query_execution: Query execution details
            workspace_config: Workspace where query was executed
            batch_id: Optional batch identifier
        """
        if not self.enabled:
            return

        # Determine operation status based on query execution
        if query_execution.query_error_message:
            status = "Failed"
        elif query_execution.record_count is not None:
            status = "Completed"
        else:
            status = "InProgress"

        extended_properties = {
            "workspace_id": workspace_config.customer_id,
            "query_name": query_execution.query_name,
            "start_time": format_datetime_iso8601(query_execution.start_time),
            "end_time": format_datetime_iso8601(query_execution.end_time),
            "duration_seconds": query_execution.query_duration_seconds or 0.0,
            "record_count": query_execution.record_count or 0,
            "workspace_resource_id": query_execution.workspace_id,
        }

        await self._log_health_event(
            operation_name="QueryExecution",
            operation_status=status,
            job_id=job_id,
            operation_status_reason=query_execution.query_error_message,
            batch_id=batch_id,
            extended_properties=extended_properties,
        )

    async def log_workspace_processing_start(
        self, job_id: str, workspace_config: WorkspaceConfig, query_names: List[str]
    ) -> None:
        """
        Log start of workspace processing.

        Args:
            job_id: Job identifier
            workspace_config: Workspace being processed
            query_names: List of queries to execute on this workspace
        """
        if not self.enabled:
            return

        extended_properties = {
            "workspace_id": workspace_config.customer_id,
            "workspace_name": workspace_config.workspace_name,
            "query_names": query_names,
            "query_count": len(query_names),
        }

        await self._log_health_event(
            operation_name="WorkspaceProcessingStart",
            operation_status="Started",
            job_id=job_id,
            extended_properties=extended_properties,
        )

    async def log_workspace_processing_end(
        self,
        job_id: str,
        workspace_config: WorkspaceConfig,
        success: bool,
        records_processed: int = 0,
        duration_seconds: float = 0.0,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log end of workspace processing.

        Args:
            job_id: Job identifier
            workspace_config: Workspace that was processed
            success: Whether processing completed successfully
            records_processed: Number of records processed from this workspace
            duration_seconds: Processing duration
            error_message: Error message if processing failed
        """
        if not self.enabled:
            return

        operation_status = "Completed" if success else "Failed"

        # Calculate successful and failed queries
        successful_queries = 0
        failed_queries = 0
        if success:
            successful_queries = 1  # At least one query succeeded
        else:
            failed_queries = 1  # Processing failed

        extended_properties = {
            "workspace_id": workspace_config.customer_id,
            "workspace_name": workspace_config.workspace_name,
            "duration_seconds": duration_seconds,
            "total_records": records_processed,
            "successful_queries": successful_queries,
            "failed_queries": failed_queries,
        }

        await self._log_health_event(
            operation_name="WorkspaceProcessingEnd",
            operation_status=operation_status,
            job_id=job_id,
            extended_properties=extended_properties,
            operation_status_reason=error_message,
        )

    async def log_error(
        self,
        job_id: str,
        error_type: str,
        error_message: str,
        workspace_id: Optional[str] = None,
        query_name: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Log error event.

        Args:
            job_id: Job identifier where error occurred
            error_type: Type/category of error
            error_message: Detailed error message
            workspace_id: Workspace ID if error is workspace-specific
            query_name: Query name if error is query-specific
            **kwargs: Additional error context
        """
        if not self.enabled:
            return

        extended_properties = {"error_type": error_type, **kwargs}

        # Add workspace_id and query_name to extended properties if provided
        if workspace_id:
            extended_properties["workspace_id"] = workspace_id
        if query_name:
            extended_properties["query_name"] = query_name

        await self._log_health_event(
            operation_name="Error",
            operation_status="Failed",
            job_id=job_id,
            extended_properties=extended_properties,
            operation_status_reason=error_message,
        )

    async def log_watermark_update(
        self,
        job_id: str,
        workspace_id: str,
        query_name: str,
        watermark_timestamp: datetime,
        previous_watermark: Optional[datetime] = None,
    ) -> None:
        """
        Log watermark update event.

        Args:
            job_id: Job identifier
            workspace_id: Workspace ID
            query_name: Query name
            watermark_timestamp: New watermark timestamp
            previous_watermark: Previous watermark timestamp if available
        """
        if not self.enabled:
            return

        extended_properties = {
            "workspace_id": workspace_id,
            "query_name": query_name,
            "watermark_timestamp": format_datetime_iso8601(watermark_timestamp),
        }

        if previous_watermark:
            extended_properties["previous_watermark"] = format_datetime_iso8601(previous_watermark)
            extended_properties["watermark_advance_seconds"] = (
                watermark_timestamp - previous_watermark
            ).total_seconds()

        await self._log_health_event(
            operation_name="WatermarkUpdate",
            operation_status="Completed",
            job_id=job_id,
            extended_properties=extended_properties,
        )

    async def _log_health_event(
        self,
        operation_name: str,
        operation_status: str,
        job_id: str,
        operation_status_reason: Optional[str] = None,
        batch_id: Optional[str] = None,
        extended_properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Internal method to log health event.

        Args:
            operation_name: Name of the operation
            operation_status: Status of the operation
            job_id: Job identifier
            operation_status_reason: Optional reason/error message for the status
            batch_id: Optional batch identifier
            extended_properties: Optional additional properties (should include workspace_id, query_name if relevant)
        """
        if not self.enabled:
            return

        try:
            # Create health log record
            health_record = {
                "TimeGenerated": format_datetime_iso8601(datetime.now(timezone.utc)),
                "OperationName": operation_name,
                "OperationStatus": operation_status,
                "JobId": job_id,
            }

            # Add operation status reason if provided (for errors/warnings)
            if operation_status_reason:
                health_record["OperationStatusReason"] = operation_status_reason

            # Add batch ID to extended properties if provided
            if batch_id:
                if extended_properties is None:
                    extended_properties = {}
                extended_properties["batch_id"] = batch_id

            # Add extended properties as JSON string
            if extended_properties:
                health_record["ExtendedProperties"] = json.dumps(extended_properties, default=str)

            # Upload to Log Analytics if health_to_sentinel is enabled
            if self.health_to_sentinel:
                await self.sentinel_client.upload_logs(
                    data=[health_record], stream_name=self.health_stream_name
                )

            # Log single consolidated JSON output
            self._log_health_to_console(health_record, extended_properties)

        except Exception as e:
            # Log health logging errors but don't fail the main operation
            logger.error(f"Failed to log health event: {e}")
            logger.debug("Health logging error details", exc_info=True)

    def _log_health_to_console(
        self, health_record: Dict[str, Any], extended_properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log health event to console with both human-readable INFO and structured JSON DEBUG.

        Args:
            health_record: Health record data
            extended_properties: Extended properties for additional context
        """
        operation_name = health_record.get("OperationName", "Unknown")
        operation_status = health_record.get("OperationStatus", "Unknown")
        job_id = health_record.get("JobId", "")  # Full job ID

        # Build context information for INFO message
        context_parts = []

        if workspace_id := health_record.get("WorkspaceId"):
            context_parts.append(f"Workspace: {workspace_id}")

        if query_name := health_record.get("QueryName"):
            context_parts.append(f"Query: {query_name}")

        # Add key extended properties
        if extended_properties:
            if record_count := extended_properties.get("record_count"):
                context_parts.append(f"Records: {record_count:,}")
            if duration_seconds := extended_properties.get("duration_seconds"):
                context_parts.append(f"Duration: {duration_seconds:.1f}s")
            if error_message := extended_properties.get("error_message"):
                context_parts.append(f"Error: {error_message}")

        context_str = f" ({', '.join(context_parts)})" if context_parts else ""

        # Log human-readable INFO message
        health_message = f"{operation_name}: {operation_status} [Job: {job_id}]{context_str}"

        # Use appropriate log level based on status
        if operation_status.lower() in ["failed", "error"]:
            logger.error(health_message)
        elif operation_status.lower() in ["warning", "partial"]:
            logger.warning(health_message)
        else:
            logger.info(health_message)

        # Log structured JSON at DEBUG level for detailed analysis
        # Create a clean record for logging (remove Time as it's handled by log formatter)
        debug_record = {k: v for k, v in health_record.items() if k != "Time"}
        debug_record["to_sentinel"] = self.health_to_sentinel
        logger.debug(json.dumps(debug_record, default=str, indent=2))

    async def verify_health_table_setup(self, workspace_id: str) -> dict:
        """
        Verify that the health logging table and DCR are properly configured.

        Args:
            workspace_id: Log Analytics workspace customer ID to test against

        Returns:
            dict: Status information about health logging setup
        """
        if not self.enabled:
            return {
                "enabled": False,
                "table_exists": None,
                "dcr_accessible": None,
                "message": "Health logging is disabled",
            }

        if not self.health_to_sentinel:
            return {
                "enabled": True,
                "table_exists": None,
                "dcr_accessible": None,
                "message": "Health logging enabled (console only, not sent to Sentinel)",
            }

        result = {"enabled": True, "table_exists": False, "dcr_accessible": False, "message": ""}

        try:
            # Test table existence by attempting to query it
            from datetime import datetime, timedelta, timezone

            table_name = self.health_stream_name.replace("Custom-", "")
            test_query = f"{table_name} | getschema | limit 1"

            # Try to query the workspace using the sentinel client
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(minutes=1)

            query_result = await self.sentinel_client.query_workspace(
                workspace_id=workspace_id,
                query=test_query,
                start_time=start_time,
                end_time=end_time,
            )

            if query_result.succeeded:
                result["table_exists"] = True
                result["message"] = "Health table exists and is accessible"

                # Test DCR accessibility by attempting a small upload
                try:
                    test_record = {
                        "TimeGenerated": format_datetime_iso8601(datetime.now(timezone.utc)),
                        "OperationName": "HealthCheck",
                        "OperationStatus": "Testing",
                        "JobId": "health-check-test",
                        "ExtendedProperties": json.dumps({"test": True}),
                    }

                    upload_result = await self.sentinel_client.upload_logs(
                        data=[test_record], stream_name=self.health_stream_name
                    )

                    if upload_result.succeeded:
                        result["dcr_accessible"] = True
                        result["message"] = "Health logging is fully configured and operational"
                    else:
                        result["message"] = (
                            f"Health table exists but DCR upload failed: {upload_result.error_message}"
                        )

                except Exception as upload_error:
                    result["message"] = f"Health table exists but DCR test failed: {upload_error}"

            else:
                result["message"] = f"Health table query failed: {query_result.error_message}"

        except Exception as e:
            result["message"] = f"Health setup verification failed: {e}"
            logger.debug(f"Health setup verification error: {e}", exc_info=True)

        return result

    async def send_test_event(self, test_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Send a test health event to verify health logging functionality.

        Args:
            test_id: Optional test identifier (generates one if not provided)
            **kwargs: Additional properties to include in the test event

        Returns:
            Dictionary with test results:
            - test_id: The test event identifier
            - success: Whether the test event was sent successfully
            - message: Description of the result
            - timestamp: When the test was performed
            - error: Error message if failed
        """
        if not self.enabled:
            return {
                "test_id": None,
                "success": False,
                "message": "Health logging is disabled",
                "timestamp": format_datetime_iso8601(datetime.now(timezone.utc)),
            }

        if not self.health_to_sentinel:
            return {
                "test_id": None,
                "success": True,
                "message": "Health logging is in console-only mode (not sent to Sentinel)",
                "timestamp": format_datetime_iso8601(datetime.now(timezone.utc)),
                "warning": True,
                "console_only": True,
            }

        # Generate test ID if not provided
        if test_id is None:
            test_id = f"health-test-{uuid4().hex[:12]}"

        timestamp = datetime.now(timezone.utc)
        result = {
            "test_id": test_id,
            "success": False,
            "message": "",
            "timestamp": format_datetime_iso8601(timestamp),
        }

        try:
            # Create test health event
            extended_properties = {
                "test_event": True,
                "test_id": test_id,
                "test_timestamp": format_datetime_iso8601(timestamp),
                **kwargs,
            }

            test_record = {
                "TimeGenerated": format_datetime_iso8601(timestamp),
                "OperationName": "HealthTest",
                "OperationStatus": "TestEvent",
                "JobId": test_id,
                "ExtendedProperties": json.dumps(extended_properties),
            }

            # Attempt to upload the test event
            upload_result = await self.sentinel_client.upload_logs(
                data=[test_record], stream_name=self.health_stream_name
            )

            if upload_result.succeeded:
                result["success"] = True
                result["message"] = f"Test event sent successfully (Test ID: {test_id})"
                result["log_record"] = test_record
                result["stream_name"] = self.health_stream_name
                result["dcr_endpoint"] = (
                    self.sentinel_client._dcr_endpoint
                    if hasattr(self.sentinel_client, "_dcr_endpoint")
                    else None
                )
                result["dcr_immutable_id"] = (
                    self.sentinel_client._options.dcr_immutable_id
                    if hasattr(self.sentinel_client, "_options")
                    and hasattr(self.sentinel_client._options, "dcr_immutable_id")
                    else None
                )
                logger.info(f"Health test event sent: {test_id}")
            else:
                result["message"] = f"Failed to send test event: {upload_result.error_message}"
                result["error"] = upload_result.error_message
                logger.error(f"Health test event failed: {upload_result.error_message}")

        except Exception as e:
            result["message"] = f"Error sending test event: {str(e)}"
            result["error"] = str(e)
            logger.error(f"Health test event error: {e}", exc_info=True)

        return result

    async def verify_test_event(
        self, test_id: str, workspace_id: str, max_wait_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        Verify that a test health event was ingested successfully.

        Args:
            test_id: The test event identifier to look for
            workspace_id: Workspace ID where health table is located
            max_wait_seconds: Maximum time to wait for ingestion (default: 300 seconds / 5 minutes)

        Returns:
            Dictionary with verification results:
            - test_id: The test event identifier
            - found: Whether the test event was found
            - message: Description of the result
            - ingestion_delay_seconds: Time between send and ingestion (if found)
            - record: The actual record found (if found)
        """
        if not self.enabled or not self.health_to_sentinel:
            return {
                "test_id": test_id,
                "found": False,
                "message": "Health logging is not configured to send to Sentinel",
            }

        result = {
            "test_id": test_id,
            "found": False,
            "message": "",
            "ingestion_delay_seconds": None,
            "record": None,
        }

        try:
            table_name = self.health_stream_name.replace("Custom-", "").replace("-", "_")

            # Query for the test event
            # Use a lookback of max_wait_seconds + 60 seconds buffer
            lookback_minutes = (max_wait_seconds + 60) // 60

            query = f"""
{table_name}
| where TimeGenerated > ago({lookback_minutes}m)
| where JobId == "{test_id}"
| where OperationName == "HealthTest"
| extend IngestionTime = ingestion_time()
| extend TimeTakenSeconds = datetime_diff('second', IngestionTime, TimeGenerated)
| project TimeGenerated, OperationName, OperationStatus, JobId, ExtendedProperties, IngestionTime, TimeTakenSeconds
| take 1
"""

            logger.info(f"Searching for test event: {test_id}")

            # Try multiple times with increasing delays
            import asyncio

            wait_intervals = [5, 10, 15, 30, 60]  # seconds
            total_waited = 0

            for i, wait_seconds in enumerate(wait_intervals):
                if total_waited >= max_wait_seconds:
                    break

                if i > 0:  # Don't wait on first attempt
                    logger.info(f"⏳ Waiting {wait_seconds} seconds before retry...")
                    await asyncio.sleep(wait_seconds)
                    total_waited += wait_seconds

                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(minutes=lookback_minutes)

                query_result = await self.sentinel_client.query_workspace(
                    workspace_id=workspace_id,
                    query=query,
                    start_time=start_time,
                    end_time=end_time,
                )

                if query_result.succeeded and query_result.record_count > 0:
                    result["found"] = True
                    record = query_result.data[0] if query_result.data else None
                    result["record"] = record

                    # Extract TimeTakenSeconds from query result if available
                    if record and isinstance(record, dict):
                        time_taken = record.get("TimeTakenSeconds")
                        if time_taken is not None:
                            result["ingestion_delay_seconds"] = float(time_taken)
                        else:
                            result["ingestion_delay_seconds"] = total_waited
                    else:
                        result["ingestion_delay_seconds"] = total_waited

                    result["message"] = (
                        f"Test event found after {total_waited} seconds "
                        f"(Ingestion delay: {result['ingestion_delay_seconds']:.1f}s, Test ID: {test_id})"
                    )
                    logger.info(
                        f"Test event verified: {test_id} "
                        f"(query wait: {total_waited}s, ingestion delay: {result['ingestion_delay_seconds']:.1f}s)"
                    )
                    return result

            # Not found after all retries
            result["message"] = (
                f"Test event not found after {total_waited} seconds. "
                f"It may take up to 10-15 minutes for data to appear in Log Analytics. "
                f"Test ID: {test_id}"
            )
            logger.warning(f"Test event not found yet: {test_id}")

        except Exception as e:
            result["message"] = f"Error verifying test event: {str(e)}"
            result["error"] = str(e)
            logger.error(f"Error verifying test event: {e}", exc_info=True)

        return result

    def create_job_id(self) -> str:
        """Create a new unique job ID."""
        return str(uuid4())

    @classmethod
    def create_disabled(cls) -> "SentinelAggregatorHealthLogger":
        """Create a disabled health logger for testing or when health logging is not needed."""
        from azure.identity.aio import DefaultAzureCredential

        from .client_options import SentinelAggregatorClientOptions
        from .sentinel_client import SentinelAggregatorClient

        # Create minimal configuration for disabled logger
        config = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://disabled.ingest.monitor.azure.com",
            dcr_immutable_id="dcr-00000000000000000000000000000000",  # Valid format: dcr-[32 hex chars]
        )
        credential = DefaultAzureCredential()
        client = SentinelAggregatorClient(
            dcr_logs_ingestion_endpoint="https://disabled.ingest.monitor.azure.com",
            credential=credential,
            options=config,
        )

        return cls(sentinel_client=client, enabled=False)
