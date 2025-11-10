"""
Azure SDK-compliant client options for Sentinel Log Aggregator.

Provides configuration options following Azure SDK patterns using
azure.core.configuration.Configuration as the base class.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from azure.core.configuration import Configuration
from azure.core.credentials import TokenCredential
from azure.core.pipeline.policies import HTTPPolicy
from pydantic import ValidationError

from .constants import (
    DEFAULT_BATCH_TIME_SIZE,
    DEFAULT_LOOKBACK_PERIOD,
    DEFAULT_MAX_CONCURRENT_QUERIES,
    DEFAULT_MAX_RETRIES,
    DEFAULT_QUERY_TIMEOUT_SECONDS,
    DEFAULT_RETRY_DELAY_SECONDS,
    MIN_QUERY_TIMEOUT,
)
from .time_utils import TimeParsingError, parse_iso8601_duration, validate_batch_time_size
from .validation import ClientOptionsModel, validate_client_options


class SentinelAggregatorClientOptions(Configuration):
    """
    Client options for SentinelAggregatorClient.

    :param dcr_logs_ingestion_endpoint: Azure Monitor DCR logs ingestion endpoint
    :type dcr_logs_ingestion_endpoint: str
    :param dcr_immutable_id: Data Collection Rule immutable ID for log ingestion
    :type dcr_immutable_id: str
    :param lookback_period: ISO 8601 duration for how far back to query (default: "P30D")
    :type lookback_period: str
    :param batch_time_size: ISO 8601 duration for batch size (default: "PT24H")
    :type batch_time_size: str
    :param start_time: Explicit start time (ISO 8601 datetime)
    :type start_time: Optional[str]
    :param end_time: Explicit end time (ISO 8601 datetime)
    :type end_time: Optional[str]
    :param use_last_successful: Whether to use last successful run timestamps
    :type use_last_successful: bool
    :param health_to_sentinel: Whether to send health logs to Sentinel table
    :type health_to_sentinel: bool
    :param max_concurrent_queries: Maximum concurrent queries (default: 5)
    :type max_concurrent_queries: int
    :param query_timeout_seconds: Query timeout in seconds (default: from constants.py)
    :type query_timeout_seconds: int
    :param max_retries: Maximum number of retries (default: from constants.py)
    :type max_retries: int
    :param retry_delay_seconds: Initial retry delay in seconds (default: from constants.py)
    :type retry_delay_seconds: int
    :param queries: Specific queries to run (comma-separated string)
    :type queries: Optional[str]
    :param workspaces: Specific workspaces to process (comma-separated string)
    :type workspaces: Optional[str]
    :param dry_run: Validate and show what would be executed (default: False)
    :type dry_run: bool
    :param parallel: Enable parallel execution (default: True)
    :type parallel: bool
    :param enable_distributed_tracing: Enable distributed tracing (default: True)
    :type enable_distributed_tracing: bool
    :param custom_policies: Custom pipeline policies to add
    :type custom_policies: Optional[List[HTTPPolicy]]
    """

    def __init__(
        self,
        *,
        dcr_logs_ingestion_endpoint: Optional[str] = None,
        dcr_immutable_id: Optional[str] = None,
        lookback_period: Optional[str] = None,
        batch_time_size: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        use_last_successful: bool = False,
        health_to_sentinel: bool = False,
        max_concurrent_queries: int = DEFAULT_MAX_CONCURRENT_QUERIES,
        query_timeout_seconds: int = DEFAULT_QUERY_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay_seconds: int = DEFAULT_RETRY_DELAY_SECONDS,
        queries: Optional[str] = None,
        workspaces: Optional[str] = None,
        dry_run: bool = False,
        parallel: bool = True,
        enable_distributed_tracing: bool = True,
        custom_policies: Optional[List[HTTPPolicy]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        # Core configuration
        self.dcr_logs_ingestion_endpoint = dcr_logs_ingestion_endpoint
        self.dcr_immutable_id = dcr_immutable_id

        # Time configuration
        self.lookback_period = lookback_period or DEFAULT_LOOKBACK_PERIOD
        self.batch_time_size = batch_time_size or DEFAULT_BATCH_TIME_SIZE
        self.start_time = start_time
        self.end_time = end_time
        self.use_last_successful = use_last_successful

        # Health logging configuration
        self.health_to_sentinel = health_to_sentinel

        # Query configuration
        self.max_concurrent_queries = max_concurrent_queries
        self.query_timeout_seconds = query_timeout_seconds

        # Execution control configuration
        self.queries = queries
        self.workspaces = workspaces
        self.dry_run = dry_run
        self.parallel = parallel

        # Retry configuration
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

        # Observability configuration
        self.enable_distributed_tracing = enable_distributed_tracing

        # Pipeline configuration
        self.custom_policies = custom_policies or []

    def validate(self) -> List[str]:
        """
        Validate the client options.

        :return: List of validation error messages (empty if valid)
        :rtype: List[str]
        """
        errors = []

        try:
            # Core configuration validation
            if not self.dcr_logs_ingestion_endpoint:
                errors.append("dcr_logs_ingestion_endpoint is required")

            if not self.dcr_immutable_id:
                errors.append("dcr_immutable_id is required")

            # Time configuration validation
            try:
                parse_iso8601_duration(self.lookback_period)
            except TimeParsingError as e:
                errors.append(f"Invalid lookback_period: {e}")

            try:
                validate_batch_time_size(self.batch_time_size)
            except TimeParsingError as e:
                errors.append(f"Invalid batch_time_size: {e}")

            # Start/end time validation
            if self.start_time:
                try:
                    from .time_utils import parse_iso8601_datetime

                    parse_iso8601_datetime(self.start_time)
                except TimeParsingError as e:
                    errors.append(f"Invalid start_time: {e}")

            if self.end_time:
                try:
                    from .time_utils import parse_iso8601_datetime

                    parse_iso8601_datetime(self.end_time)
                except TimeParsingError as e:
                    errors.append(f"Invalid end_time: {e}")

            # Query configuration validation
            if self.max_concurrent_queries <= 0:
                errors.append("max_concurrent_queries must be positive")

            if self.query_timeout_seconds < MIN_QUERY_TIMEOUT:
                errors.append(f"query_timeout_seconds must be at least {MIN_QUERY_TIMEOUT}")

            # Retry configuration validation
            if self.max_retries < 0:
                errors.append("max_retries cannot be negative")

            if self.retry_delay_seconds <= 0:
                errors.append("retry_delay_seconds must be positive")

        except Exception as e:
            errors.append(f"Validation error: {e}")

        return errors

    @classmethod
    def from_environment(cls, **kwargs: Any) -> "SentinelAggregatorClientOptions":
        """
        Create client options from environment variables.

        :return: Configured client options
        :rtype: SentinelAggregatorClientOptions
        """
        import os

        return cls(
            dcr_logs_ingestion_endpoint=os.getenv("DCR_LOGS_INGESTION_ENDPOINT"),
            dcr_immutable_id=os.getenv("DCR_IMMUTABLE_ID"),
            lookback_period=os.getenv("LOOKBACK_PERIOD"),
            batch_time_size=os.getenv("BATCH_TIME_SIZE"),
            start_time=os.getenv("START_TIME"),
            end_time=os.getenv("END_TIME"),
            use_last_successful=os.getenv("USE_LAST_SUCCESSFUL", "false").lower() == "true",
            health_to_sentinel=os.getenv("HEALTH_TO_SENTINEL", "false").lower() == "true",
            max_concurrent_queries=int(
                os.getenv("MAX_CONCURRENT_QUERIES", str(DEFAULT_MAX_CONCURRENT_QUERIES))
            ),
            query_timeout_seconds=int(
                os.getenv("QUERY_TIMEOUT_SECONDS", str(DEFAULT_QUERY_TIMEOUT_SECONDS))
            ),
            max_retries=int(os.getenv("MAX_RETRIES", str(DEFAULT_MAX_RETRIES))),
            retry_delay_seconds=int(
                os.getenv("RETRY_DELAY_SECONDS", str(DEFAULT_RETRY_DELAY_SECONDS))
            ),
            queries=os.getenv("QUERIES"),
            workspaces=os.getenv("WORKSPACES"),
            dry_run=os.getenv("DRY_RUN", "false").lower() == "true",
            parallel=os.getenv("PARALLEL", "true").lower() == "true",
            **kwargs,
        )

    @classmethod
    def from_yaml_file(cls, file_path: str, **kwargs: Any) -> "SentinelAggregatorClientOptions":
        """
        Create client options from YAML configuration file.

        :param file_path: Path to YAML configuration file
        :type file_path: str
        :return: Configured client options
        :rtype: SentinelAggregatorClientOptions
        """
        from pathlib import Path

        import yaml

        config_path = Path(file_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

        return cls(
            dcr_logs_ingestion_endpoint=config_data.get("dcr_logs_ingestion_endpoint"),
            dcr_immutable_id=config_data.get("dcr_immutable_id"),
            lookback_period=config_data.get("lookback_period"),
            batch_time_size=config_data.get("batch_time_size"),
            start_time=config_data.get("start_time"),
            end_time=config_data.get("end_time"),
            use_last_successful=config_data.get("use_last_successful", False),
            health_to_sentinel=config_data.get("health_to_sentinel", False),
            max_concurrent_queries=config_data.get(
                "max_concurrent_queries", DEFAULT_MAX_CONCURRENT_QUERIES
            ),
            query_timeout_seconds=config_data.get(
                "query_timeout_seconds", DEFAULT_QUERY_TIMEOUT_SECONDS
            ),
            max_retries=config_data.get("max_retries", DEFAULT_MAX_RETRIES),
            retry_delay_seconds=config_data.get("retry_delay_seconds", DEFAULT_RETRY_DELAY_SECONDS),
            queries=config_data.get("queries"),
            workspaces=config_data.get("workspaces"),
            dry_run=config_data.get("dry_run", False),
            parallel=config_data.get("parallel", True),
            **kwargs,
        )
