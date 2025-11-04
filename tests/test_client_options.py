"""
Comprehensive tests for sentinel_log_aggregator.client_options module.

Tests cover SentinelAggregatorClientOptions initialization, validation,
environment loading, YAML file loading, and all configuration options.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml
from pydantic import ValidationError

from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions


class TestSentinelAggregatorClientOptions:
    """Test SentinelAggregatorClientOptions initialization and basic functionality."""

    def test_initialization_with_defaults(self):
        """Test initialization with default values."""
        options = SentinelAggregatorClientOptions()

        assert options.dcr_logs_ingestion_endpoint is None
        assert options.dcr_immutable_id is None
        assert options.lookback_period == "P30D"
        assert options.batch_time_size == "PT24H"
        assert options.max_concurrent_queries == 5
        assert options.query_timeout_seconds == 300
        assert options.max_retries == 3
        assert options.retry_delay_seconds == 5
        assert options.enable_distributed_tracing is True
        assert options.custom_policies == []

    def test_initialization_with_custom_values(self):
        """Test initialization with custom values."""
        custom_policies = [Mock()]

        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.endpoint.com",
            dcr_immutable_id="dcr-123456",
            lookback_period="P7D",
            batch_time_size="PT12H",
            max_concurrent_queries=10,
            query_timeout_seconds=600,
            max_retries=5,
            retry_delay_seconds=10,
            enable_distributed_tracing=False,
            custom_policies=custom_policies,
        )

        assert options.dcr_logs_ingestion_endpoint == "https://test.endpoint.com"
        assert options.dcr_immutable_id == "dcr-123456"
        assert options.lookback_period == "P7D"
        assert options.batch_time_size == "PT12H"
        assert options.max_concurrent_queries == 10
        assert options.query_timeout_seconds == 600
        assert options.max_retries == 5
        assert options.retry_delay_seconds == 10
        assert options.enable_distributed_tracing is False
        assert options.custom_policies == custom_policies

    def test_initialization_with_kwargs(self):
        """Test initialization passes through kwargs to parent Configuration."""
        with patch("azure.core.configuration.Configuration.__init__") as mock_init:
            mock_init.return_value = None

            SentinelAggregatorClientOptions(custom_arg="test_value", another_arg=123)

            mock_init.assert_called_once_with(custom_arg="test_value", another_arg=123)


class TestValidation:
    """Test client options validation functionality."""

    def test_validate_success_with_new_validation(self):
        """Test successful validation with all required fields."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.endpoint.com", dcr_immutable_id="dcr-123456"
        )

        # Should return empty list for successful validation
        errors = options.validate()
        assert errors == []

    def test_validate_failure_with_missing_endpoint(self):
        """Test validation failure with missing DCR endpoint."""
        options = SentinelAggregatorClientOptions(dcr_immutable_id="dcr-123456")

        errors = options.validate()
        assert len(errors) > 0
        assert any("dcr_logs_ingestion_endpoint is required" in error for error in errors)

    def test_validate_fallback_missing_endpoint(self):
        """Test validation failure with missing endpoint."""
        options = SentinelAggregatorClientOptions(dcr_immutable_id="dcr-123")

        errors = options.validate()
        assert len(errors) > 0
        assert any("dcr_logs_ingestion_endpoint is required" in error for error in errors)

    def test_validate_fallback_missing_rule_id(self):
        """Test validation failure with missing DCR immutable ID."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.endpoint.com"
        )

        errors = options.validate()
        assert len(errors) > 0
        assert any("dcr_immutable_id is required" in error for error in errors)

    def test_validate_fallback_invalid_max_concurrent_queries(self):
        """Test validation failure with invalid max_concurrent_queries."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.endpoint.com",
            dcr_immutable_id="dcr-123",
            max_concurrent_queries=-1,
        )

        errors = options.validate()
        assert len(errors) > 0
        assert any("max_concurrent_queries must be positive" in error for error in errors)

    def test_validate_fallback_invalid_query_timeout(self):
        """Test validation failure with invalid query_timeout_seconds."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.endpoint.com",
            dcr_immutable_id="dcr-123",
            query_timeout_seconds=0,
        )

        errors = options.validate()
        assert len(errors) > 0
        assert any("query_timeout_seconds must be at least 30" in error for error in errors)

    def test_validate_fallback_invalid_max_retries(self):
        """Test validation failure with invalid max_retries."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.endpoint.com",
            dcr_immutable_id="dcr-123",
            max_retries=-1,
        )

        errors = options.validate()
        assert len(errors) > 0
        assert any("max_retries cannot be negative" in error for error in errors)

    def test_validate_fallback_invalid_retry_delay(self):
        """Test validation failure with invalid retry_delay_seconds."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.endpoint.com",
            dcr_immutable_id="dcr-123",
            retry_delay_seconds=0,
        )

        errors = options.validate()
        assert len(errors) > 0
        assert any("retry_delay_seconds must be positive" in error for error in errors)


class TestFromEnvironment:
    """Test creating client options from environment variables."""

    def test_from_environment_with_all_variables(self):
        """Test creating options from complete environment variables."""
        env_vars = {
            "DCR_LOGS_INGESTION_ENDPOINT": "https://env.endpoint.com",
            "DCR_IMMUTABLE_ID": "env-dcr-123",
            "LOOKBACK_PERIOD": "P14D",
            "BATCH_TIME_SIZE": "PT6H",
            "MAX_CONCURRENT_QUERIES": "8",
            "QUERY_TIMEOUT_SECONDS": "600",
            "MAX_RETRIES": "4",
            "RETRY_DELAY_SECONDS": "8",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            options = SentinelAggregatorClientOptions.from_environment()

        assert options.dcr_logs_ingestion_endpoint == "https://env.endpoint.com"
        assert options.dcr_immutable_id == "env-dcr-123"
        assert options.lookback_period == "P14D"
        assert options.batch_time_size == "PT6H"
        assert options.max_concurrent_queries == 8
        assert options.query_timeout_seconds == 600
        assert options.max_retries == 4
        assert options.retry_delay_seconds == 8

    def test_from_environment_with_defaults(self):
        """Test creating options from environment with missing variables (uses defaults)."""
        env_vars = {
            "DCR_LOGS_INGESTION_ENDPOINT": "https://env.endpoint.com",
            "DCR_IMMUTABLE_ID": "env-dcr-123",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            options = SentinelAggregatorClientOptions.from_environment()

        assert options.dcr_logs_ingestion_endpoint == "https://env.endpoint.com"
        assert options.dcr_immutable_id == "env-dcr-123"
        assert options.lookback_period == "P30D"  # default
        assert options.batch_time_size == "PT24H"  # default
        assert options.max_concurrent_queries == 5  # default
        assert options.query_timeout_seconds == 300  # default
        assert options.max_retries == 3  # default
        assert options.retry_delay_seconds == 5  # default

    def test_from_environment_with_kwargs(self):
        """Test from_environment passes through additional kwargs."""
        env_vars = {
            "DCR_LOGS_INGESTION_ENDPOINT": "https://env.endpoint.com",
            "DCR_IMMUTABLE_ID": "env-dcr-123",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            options = SentinelAggregatorClientOptions.from_environment(
                enable_distributed_tracing=False, custom_policies=["policy1"]
            )

        assert options.enable_distributed_tracing is False
        assert options.custom_policies == ["policy1"]

    def test_from_environment_invalid_integer_values(self):
        """Test from_environment with invalid integer values."""
        env_vars = {
            "DCR_LOGS_INGESTION_ENDPOINT": "https://env.endpoint.com",
            "DCR_IMMUTABLE_ID": "env-dcr-123",
            "MAX_CONCURRENT_QUERIES": "invalid_number",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError):
                SentinelAggregatorClientOptions.from_environment()


class TestFromYamlFile:
    """Test creating client options from YAML configuration files."""

    def test_from_yaml_file_complete_config(self):
        """Test creating options from complete YAML configuration."""
        config_data = {
            "dcr_logs_ingestion_endpoint": "https://yaml.endpoint.com",
            "dcr_immutable_id": "yaml-dcr-123",
            "lookback_period": "P21D",
            "batch_time_size": "PT8H",
            "max_concurrent_queries": 12,
            "query_timeout_seconds": 450,
            "max_retries": 6,
            "retry_delay_seconds": 12,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            options = SentinelAggregatorClientOptions.from_yaml_file(temp_path)

            assert options.dcr_logs_ingestion_endpoint == "https://yaml.endpoint.com"
            assert options.dcr_immutable_id == "yaml-dcr-123"
            assert options.lookback_period == "P21D"
            assert options.batch_time_size == "PT8H"
            assert options.max_concurrent_queries == 12
            assert options.query_timeout_seconds == 450
            assert options.max_retries == 6
            assert options.retry_delay_seconds == 12
        finally:
            os.unlink(temp_path)

    def test_from_yaml_file_partial_config_with_defaults(self):
        """Test creating options from partial YAML config (uses defaults for missing)."""
        config_data = {
            "dcr_logs_ingestion_endpoint": "https://yaml.endpoint.com",
            "dcr_immutable_id": "yaml-dcr-123",
            "lookback_period": "P7D",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            options = SentinelAggregatorClientOptions.from_yaml_file(temp_path)

            assert options.dcr_logs_ingestion_endpoint == "https://yaml.endpoint.com"
            assert options.dcr_immutable_id == "yaml-dcr-123"
            assert options.lookback_period == "P7D"
            assert options.batch_time_size == "PT24H"  # default
            assert options.max_concurrent_queries == 5  # default
        finally:
            os.unlink(temp_path)

    def test_from_yaml_file_empty_config(self):
        """Test creating options from empty YAML config (all defaults)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({}, f)
            temp_path = f.name

        try:
            options = SentinelAggregatorClientOptions.from_yaml_file(temp_path)

            assert options.dcr_logs_ingestion_endpoint is None
            assert options.dcr_immutable_id is None
            assert options.lookback_period == "P30D"  # default
            assert options.batch_time_size == "PT24H"  # default
        finally:
            os.unlink(temp_path)

    def test_from_yaml_file_null_config(self):
        """Test creating options from YAML file with null content."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")  # Empty file results in None from yaml.safe_load
            temp_path = f.name

        try:
            options = SentinelAggregatorClientOptions.from_yaml_file(temp_path)

            # Should use all defaults when config is None
            assert options.dcr_logs_ingestion_endpoint is None
            assert options.dcr_immutable_id is None
            assert options.lookback_period == "P30D"
            assert options.batch_time_size == "PT24H"
        finally:
            os.unlink(temp_path)

    def test_from_yaml_file_with_kwargs(self):
        """Test from_yaml_file passes through additional kwargs."""
        config_data = {
            "dcr_logs_ingestion_endpoint": "https://yaml.endpoint.com",
            "dcr_immutable_id": "yaml-dcr-123",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            options = SentinelAggregatorClientOptions.from_yaml_file(
                temp_path, enable_distributed_tracing=False, custom_policies=["yaml_policy"]
            )

            assert options.dcr_logs_ingestion_endpoint == "https://yaml.endpoint.com"
            assert options.enable_distributed_tracing is False
            assert options.custom_policies == ["yaml_policy"]
        finally:
            os.unlink(temp_path)

    def test_from_yaml_file_not_found(self):
        """Test from_yaml_file with non-existent file."""
        non_existent_path = "/path/that/does/not/exist.yaml"

        with pytest.raises(FileNotFoundError) as exc_info:
            SentinelAggregatorClientOptions.from_yaml_file(non_existent_path)

        assert "Configuration file not found" in str(exc_info.value)
        assert non_existent_path in str(exc_info.value)

    def test_from_yaml_file_invalid_yaml(self):
        """Test from_yaml_file with invalid YAML content."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [\n")  # Invalid YAML
            temp_path = f.name

        try:
            with pytest.raises(yaml.YAMLError):
                SentinelAggregatorClientOptions.from_yaml_file(temp_path)
        finally:
            os.unlink(temp_path)


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple features."""

    def test_environment_override_yaml_config(self):
        """Test that environment variables can override YAML config values."""
        # Create YAML config
        config_data = {
            "dcr_logs_ingestion_endpoint": "https://yaml.endpoint.com",
            "dcr_immutable_id": "yaml-dcr-123",
            "lookback_period": "P14D",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            # Load from YAML first
            yaml_options = SentinelAggregatorClientOptions.from_yaml_file(temp_path)
            assert yaml_options.lookback_period == "P14D"

            # Then override with environment
            env_vars = {"LOOKBACK_PERIOD": "P7D"}
            with patch.dict(os.environ, env_vars, clear=False):
                env_options = SentinelAggregatorClientOptions.from_environment()
                assert env_options.lookback_period == "P7D"
        finally:
            os.unlink(temp_path)

    def test_full_configuration_workflow(self):
        """Test complete configuration workflow with validation."""
        config_data = {
            "dcr_logs_ingestion_endpoint": "https://test.endpoint.com",
            "dcr_immutable_id": "test-dcr-123",
            "lookback_period": "P7D",
            "batch_time_size": "PT12H",
            "max_concurrent_queries": 10,
            "query_timeout_seconds": 600,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            # Load configuration
            options = SentinelAggregatorClientOptions.from_yaml_file(temp_path)

            # Mock successful validation
            with patch(
                "sentinel_log_aggregator.client_options.validate_client_options"
            ) as mock_validate:
                mock_validate.return_value = True
                options.validate()  # Should pass

            # Verify all values are set correctly
            assert options.dcr_logs_ingestion_endpoint == "https://test.endpoint.com"
            assert options.dcr_immutable_id == "test-dcr-123"
            assert options.lookback_period == "P7D"
            assert options.batch_time_size == "PT12H"
            assert options.max_concurrent_queries == 10
            assert options.query_timeout_seconds == 600
        finally:
            os.unlink(temp_path)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_from_environment_empty_strings(self):
        """Test from_environment with empty string environment variables."""
        env_vars = {"DCR_LOGS_INGESTION_ENDPOINT": "", "DCR_IMMUTABLE_ID": "", "LOOKBACK_PERIOD": "P30D"}

        with patch.dict(os.environ, env_vars, clear=True):
            options = SentinelAggregatorClientOptions.from_environment()

        assert options.dcr_logs_ingestion_endpoint == ""
        assert options.dcr_immutable_id == ""
        assert options.lookback_period == "P30D"

    def test_initialization_edge_case_values(self):
        """Test initialization with edge case values."""
        options = SentinelAggregatorClientOptions(
            lookback_period="P1D",  # minimum positive value
            batch_time_size="PT1H",  # minimum positive value
            max_concurrent_queries=1,  # minimum positive value
            query_timeout_seconds=1,  # minimum positive value
            max_retries=0,  # minimum non-negative value
            retry_delay_seconds=1,  # minimum positive value
        )

        assert options.lookback_period == "P1D"
        assert options.batch_time_size == "PT1H"
        assert options.max_concurrent_queries == 1
        assert options.query_timeout_seconds == 1
        assert options.max_retries == 0
        assert options.retry_delay_seconds == 1

    def test_validation_with_all_attributes(self):
        """Test that validation works with additional attributes."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.endpoint.com", dcr_immutable_id="test-dcr-123"
        )

        # Set additional attributes (these don't affect validation)
        options.upload_timeout_seconds = 600
        options.max_upload_retries = 5
        options.log_level = "DEBUG"
        options.enable_telemetry = False

        # Should return empty list for successful validation
        errors = options.validate()
        assert errors == []

    def test_yaml_file_with_pathlib_path(self):
        """Test from_yaml_file works with pathlib.Path objects."""
        config_data = {
            "dcr_logs_ingestion_endpoint": "https://pathlib.endpoint.com",
            "dcr_immutable_id": "pathlib-dcr-123",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            options = SentinelAggregatorClientOptions.from_yaml_file(str(temp_path))

            assert options.dcr_logs_ingestion_endpoint == "https://pathlib.endpoint.com"
            assert options.dcr_immutable_id == "pathlib-dcr-123"
        finally:
            temp_path.unlink()
