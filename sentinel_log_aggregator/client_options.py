"""
Azure SDK-compliant client options for Sentinel Log Aggregator.

Provides configuration options following Azure SDK patterns using
azure.core.configuration.Configuration as the base class.
"""

from typing import Any, Dict, List, Optional, Union

from azure.core.configuration import Configuration
from azure.core.credentials import TokenCredential
from azure.core.pipeline.policies import HTTPPolicy
from pydantic import ValidationError

from .validation import ClientOptionsModel, validate_client_options


class SentinelAggregatorClientOptions(Configuration):
    """
    Client options for SentinelAggregatorClient.

    :param dcr_logs_ingestion_endpoint: Azure Monitor DCR logs ingestion endpoint
    :type dcr_logs_ingestion_endpoint: str
    :param dcr_rule_id: Data Collection Rule ID for log ingestion
    :type dcr_rule_id: str
    :param days_ago: Number of days ago to query (default: 30)
    :type days_ago: int
    :param batch_hours: Hours per batch for time-based processing (default: 24)
    :type batch_hours: int
    :param max_concurrent_queries: Maximum concurrent queries (default: 5)
    :type max_concurrent_queries: int
    :param query_timeout_seconds: Query timeout in seconds (default: 300)
    :type query_timeout_seconds: int
    :param max_retries: Maximum number of retries (default: 3)
    :type max_retries: int
    :param retry_delay_seconds: Initial retry delay in seconds (default: 5)
    :type retry_delay_seconds: int
    :param enable_distributed_tracing: Enable distributed tracing (default: True)
    :type enable_distributed_tracing: bool
    :param custom_policies: Custom pipeline policies to add
    :type custom_policies: Optional[List[HTTPPolicy]]
    """

    def __init__(
        self,
        *,
        dcr_logs_ingestion_endpoint: Optional[str] = None,
        dcr_rule_id: Optional[str] = None,
        days_ago: int = 30,
        batch_hours: int = 24,
        max_concurrent_queries: int = 5,
        query_timeout_seconds: int = 300,
        max_retries: int = 3,
        retry_delay_seconds: int = 5,
        enable_distributed_tracing: bool = True,
        custom_policies: Optional[List[HTTPPolicy]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        # Core configuration
        self.dcr_logs_ingestion_endpoint = dcr_logs_ingestion_endpoint
        self.dcr_rule_id = dcr_rule_id

        # Query configuration
        self.days_ago = days_ago
        self.batch_hours = batch_hours
        self.max_concurrent_queries = max_concurrent_queries
        self.query_timeout_seconds = query_timeout_seconds

        # Retry configuration
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

        # Observability configuration
        self.enable_distributed_tracing = enable_distributed_tracing

        # Pipeline configuration
        self.custom_policies = custom_policies or []

    def validate(self) -> None:
        """
        Validate the client options using Pydantic models.

        :raises ValueError: If required options are missing or invalid
        """
        try:
            # Convert to dict for validation
            options_dict = {
                "dcr_logs_ingestion_endpoint": self.dcr_logs_ingestion_endpoint,
                "dcr_rule_id": self.dcr_rule_id,
                "max_concurrent_queries": self.max_concurrent_queries,
                "query_timeout_seconds": self.query_timeout_seconds,
                "batch_hours": self.batch_hours,
                "upload_timeout_seconds": getattr(self, "upload_timeout_seconds", 300),
                "max_upload_retries": getattr(self, "max_upload_retries", 3),
                "log_level": getattr(self, "log_level", "INFO"),
                "enable_telemetry": getattr(self, "enable_telemetry", True),
            }

            # Validate using Pydantic
            validate_client_options(options_dict)

        except ValidationError as e:
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            raise ValueError(f"Client options validation failed: {'; '.join(error_messages)}")
        except Exception as e:
            # Fallback to basic validation
            if not self.dcr_logs_ingestion_endpoint:
                raise ValueError("dcr_logs_ingestion_endpoint is required")

            if not self.dcr_rule_id:
                raise ValueError("dcr_rule_id is required")

            if self.days_ago <= 0:
                raise ValueError("days_ago must be positive")

            if self.batch_hours <= 0:
                raise ValueError("batch_hours must be positive")

            if self.max_concurrent_queries <= 0:
                raise ValueError("max_concurrent_queries must be positive")

            if self.query_timeout_seconds <= 0:
                raise ValueError("query_timeout_seconds must be positive")

            if self.max_retries < 0:
                raise ValueError("max_retries cannot be negative")

            if self.retry_delay_seconds <= 0:
                raise ValueError("retry_delay_seconds must be positive")

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
            dcr_rule_id=os.getenv("DCR_RULE_ID"),
            days_ago=int(os.getenv("DAYS_AGO", "30")),
            batch_hours=int(os.getenv("BATCH_HOURS", "24")),
            max_concurrent_queries=int(os.getenv("MAX_CONCURRENT_QUERIES", "5")),
            query_timeout_seconds=int(os.getenv("QUERY_TIMEOUT_SECONDS", "300")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_delay_seconds=int(os.getenv("RETRY_DELAY_SECONDS", "5")),
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
            dcr_rule_id=config_data.get("dcr_rule_id"),
            days_ago=config_data.get("days_ago", 30),
            batch_hours=config_data.get("batch_hours", 24),
            max_concurrent_queries=config_data.get("max_concurrent_queries", 5),
            query_timeout_seconds=config_data.get("query_timeout_seconds", 300),
            max_retries=config_data.get("max_retries", 3),
            retry_delay_seconds=config_data.get("retry_delay_seconds", 5),
            **kwargs,
        )
