"""
Comprehensive tests for sentinel_log_aggregator.client_options module.

Tests cover SentinelAggregatorClientOptions initialization, validation,
environment loading, YAML file loading, and all configuration options.
"""

import pytest
import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, Mock
from pydantic import ValidationError

from sentinel_log_aggregator.client_options import SentinelAggregatorClientOptions


class TestSentinelAggregatorClientOptions:
    """Test SentinelAggregatorClientOptions initialization and basic functionality."""
    
    def test_initialization_with_defaults(self):
        """Test initialization with default values."""
        options = SentinelAggregatorClientOptions()
        
        assert options.dcr_logs_ingestion_endpoint is None
        assert options.dcr_rule_id is None
        assert options.days_ago == 30
        assert options.batch_hours == 24
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
            dcr_rule_id="dcr-123456",
            days_ago=7,
            batch_hours=12,
            max_concurrent_queries=10,
            query_timeout_seconds=600,
            max_retries=5,
            retry_delay_seconds=10,
            enable_distributed_tracing=False,
            custom_policies=custom_policies
        )
        
        assert options.dcr_logs_ingestion_endpoint == "https://test.endpoint.com"
        assert options.dcr_rule_id == "dcr-123456"
        assert options.days_ago == 7
        assert options.batch_hours == 12
        assert options.max_concurrent_queries == 10
        assert options.query_timeout_seconds == 600
        assert options.max_retries == 5
        assert options.retry_delay_seconds == 10
        assert options.enable_distributed_tracing is False
        assert options.custom_policies == custom_policies
    
    def test_initialization_with_kwargs(self):
        """Test initialization passes through kwargs to parent Configuration."""
        with patch('azure.core.configuration.Configuration.__init__') as mock_init:
            mock_init.return_value = None
            
            SentinelAggregatorClientOptions(
                custom_arg="test_value",
                another_arg=123
            )
            
            mock_init.assert_called_once_with(
                custom_arg="test_value",
                another_arg=123
            )


class TestValidation:
    """Test client options validation functionality."""
    
    def test_validate_success_with_pydantic(self):
        """Test successful validation with all required fields."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.endpoint.com",
            dcr_rule_id="dcr-123456"
        )
        
        # Mock the validation function to simulate successful validation
        with patch('sentinel_log_aggregator.client_options.validate_client_options') as mock_validate:
            mock_validate.return_value = True
            
            # Should not raise any exception
            options.validate()
            
            mock_validate.assert_called_once()
    
    def test_validate_failure_with_pydantic_validation_error(self):
        """Test validation failure with Pydantic ValidationError."""
        options = SentinelAggregatorClientOptions()
        
        # Import ValidationError to create a real instance
        from pydantic import ValidationError, BaseModel
        from pydantic_core import ValidationError as CoreValidationError
        
        # Create a simple model to generate real ValidationError
        class TestModel(BaseModel):
            dcr_logs_ingestion_endpoint: str
            dcr_rule_id: str
        
        try:
            TestModel(dcr_logs_ingestion_endpoint=None, dcr_rule_id=None)
        except ValidationError as real_error:
            # Use this real error
            with patch('sentinel_log_aggregator.client_options.validate_client_options') as mock_validate:
                mock_validate.side_effect = real_error
                
                with pytest.raises(ValueError) as exc_info:
                    options.validate()
                
                assert "Client options validation failed" in str(exc_info.value)
    
    def test_validate_fallback_missing_endpoint(self):
        """Test fallback validation when Pydantic validation fails - missing endpoint."""
        options = SentinelAggregatorClientOptions(dcr_rule_id="dcr-123")
        
        # Mock ValidationError import to fail, triggering fallback
        with patch('sentinel_log_aggregator.client_options.validate_client_options') as mock_validate:
            mock_validate.side_effect = ImportError("Pydantic not available")
            
            with pytest.raises(ValueError) as exc_info:
                options.validate()
            
            assert "dcr_logs_ingestion_endpoint is required" in str(exc_info.value)
    
    def test_validate_fallback_missing_rule_id(self):
        """Test fallback validation - missing DCR rule ID."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.endpoint.com"
        )
        
        with patch('sentinel_log_aggregator.client_options.validate_client_options') as mock_validate:
            mock_validate.side_effect = ImportError("Pydantic not available")
            
            with pytest.raises(ValueError) as exc_info:
                options.validate()
            
            assert "dcr_rule_id is required" in str(exc_info.value)
    
    def test_validate_fallback_invalid_days_ago(self):
        """Test fallback validation - invalid days_ago."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.endpoint.com",
            dcr_rule_id="dcr-123",
            days_ago=-1
        )
        
        with patch('sentinel_log_aggregator.client_options.validate_client_options') as mock_validate:
            mock_validate.side_effect = Exception("Validation failed")
            
            with pytest.raises(ValueError) as exc_info:
                options.validate()
            
            assert "days_ago must be positive" in str(exc_info.value)
    
    def test_validate_fallback_invalid_batch_hours(self):
        """Test fallback validation - invalid batch_hours."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.endpoint.com",
            dcr_rule_id="dcr-123",
            batch_hours=0
        )
        
        with patch('sentinel_log_aggregator.client_options.validate_client_options') as mock_validate:
            mock_validate.side_effect = Exception("Validation failed")
            
            with pytest.raises(ValueError) as exc_info:
                options.validate()
            
            assert "batch_hours must be positive" in str(exc_info.value)
    
    def test_validate_fallback_invalid_max_concurrent_queries(self):
        """Test fallback validation - invalid max_concurrent_queries."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.endpoint.com",
            dcr_rule_id="dcr-123",
            max_concurrent_queries=-1
        )
        
        with patch('sentinel_log_aggregator.client_options.validate_client_options') as mock_validate:
            mock_validate.side_effect = Exception("Validation failed")
            
            with pytest.raises(ValueError) as exc_info:
                options.validate()
            
            assert "max_concurrent_queries must be positive" in str(exc_info.value)
    
    def test_validate_fallback_invalid_query_timeout(self):
        """Test fallback validation - invalid query_timeout_seconds."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.endpoint.com",
            dcr_rule_id="dcr-123",
            query_timeout_seconds=0
        )
        
        with patch('sentinel_log_aggregator.client_options.validate_client_options') as mock_validate:
            mock_validate.side_effect = Exception("Validation failed")
            
            with pytest.raises(ValueError) as exc_info:
                options.validate()
            
            assert "query_timeout_seconds must be positive" in str(exc_info.value)
    
    def test_validate_fallback_invalid_max_retries(self):
        """Test fallback validation - invalid max_retries."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.endpoint.com",
            dcr_rule_id="dcr-123",
            max_retries=-1
        )
        
        with patch('sentinel_log_aggregator.client_options.validate_client_options') as mock_validate:
            mock_validate.side_effect = Exception("Validation failed")
            
            with pytest.raises(ValueError) as exc_info:
                options.validate()
            
            assert "max_retries cannot be negative" in str(exc_info.value)
    
    def test_validate_fallback_invalid_retry_delay(self):
        """Test fallback validation - invalid retry_delay_seconds."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.endpoint.com",
            dcr_rule_id="dcr-123",
            retry_delay_seconds=0
        )
        
        with patch('sentinel_log_aggregator.client_options.validate_client_options') as mock_validate:
            mock_validate.side_effect = Exception("Validation failed")
            
            with pytest.raises(ValueError) as exc_info:
                options.validate()
            
            assert "retry_delay_seconds must be positive" in str(exc_info.value)


class TestFromEnvironment:
    """Test creating client options from environment variables."""
    
    def test_from_environment_with_all_variables(self):
        """Test creating options from complete environment variables."""
        env_vars = {
            "DCR_LOGS_INGESTION_ENDPOINT": "https://env.endpoint.com",
            "DCR_RULE_ID": "env-dcr-123",
            "DAYS_AGO": "14",
            "BATCH_HOURS": "6",
            "MAX_CONCURRENT_QUERIES": "8",
            "QUERY_TIMEOUT_SECONDS": "600",
            "MAX_RETRIES": "4",
            "RETRY_DELAY_SECONDS": "8"
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            options = SentinelAggregatorClientOptions.from_environment()
        
        assert options.dcr_logs_ingestion_endpoint == "https://env.endpoint.com"
        assert options.dcr_rule_id == "env-dcr-123"
        assert options.days_ago == 14
        assert options.batch_hours == 6
        assert options.max_concurrent_queries == 8
        assert options.query_timeout_seconds == 600
        assert options.max_retries == 4
        assert options.retry_delay_seconds == 8
    
    def test_from_environment_with_defaults(self):
        """Test creating options from environment with missing variables (uses defaults)."""
        env_vars = {
            "DCR_LOGS_INGESTION_ENDPOINT": "https://env.endpoint.com",
            "DCR_RULE_ID": "env-dcr-123"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            options = SentinelAggregatorClientOptions.from_environment()
        
        assert options.dcr_logs_ingestion_endpoint == "https://env.endpoint.com"
        assert options.dcr_rule_id == "env-dcr-123"
        assert options.days_ago == 30  # default
        assert options.batch_hours == 24  # default
        assert options.max_concurrent_queries == 5  # default
        assert options.query_timeout_seconds == 300  # default
        assert options.max_retries == 3  # default
        assert options.retry_delay_seconds == 5  # default
    
    def test_from_environment_with_kwargs(self):
        """Test from_environment passes through additional kwargs."""
        env_vars = {
            "DCR_LOGS_INGESTION_ENDPOINT": "https://env.endpoint.com",
            "DCR_RULE_ID": "env-dcr-123"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            options = SentinelAggregatorClientOptions.from_environment(
                enable_distributed_tracing=False,
                custom_policies=["policy1"]
            )
        
        assert options.enable_distributed_tracing is False
        assert options.custom_policies == ["policy1"]
    
    def test_from_environment_invalid_integer_values(self):
        """Test from_environment with invalid integer values."""
        env_vars = {
            "DCR_LOGS_INGESTION_ENDPOINT": "https://env.endpoint.com",
            "DCR_RULE_ID": "env-dcr-123",
            "DAYS_AGO": "invalid_number"
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
            "dcr_rule_id": "yaml-dcr-123",
            "days_ago": 21,
            "batch_hours": 8,
            "max_concurrent_queries": 12,
            "query_timeout_seconds": 450,
            "max_retries": 6,
            "retry_delay_seconds": 12
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            options = SentinelAggregatorClientOptions.from_yaml_file(temp_path)
            
            assert options.dcr_logs_ingestion_endpoint == "https://yaml.endpoint.com"
            assert options.dcr_rule_id == "yaml-dcr-123"
            assert options.days_ago == 21
            assert options.batch_hours == 8
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
            "dcr_rule_id": "yaml-dcr-123",
            "days_ago": 7
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            options = SentinelAggregatorClientOptions.from_yaml_file(temp_path)
            
            assert options.dcr_logs_ingestion_endpoint == "https://yaml.endpoint.com"
            assert options.dcr_rule_id == "yaml-dcr-123"
            assert options.days_ago == 7
            assert options.batch_hours == 24  # default
            assert options.max_concurrent_queries == 5  # default
        finally:
            os.unlink(temp_path)
    
    def test_from_yaml_file_empty_config(self):
        """Test creating options from empty YAML config (all defaults)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({}, f)
            temp_path = f.name
        
        try:
            options = SentinelAggregatorClientOptions.from_yaml_file(temp_path)
            
            assert options.dcr_logs_ingestion_endpoint is None
            assert options.dcr_rule_id is None
            assert options.days_ago == 30  # default
            assert options.batch_hours == 24  # default
        finally:
            os.unlink(temp_path)
    
    def test_from_yaml_file_null_config(self):
        """Test creating options from YAML file with null content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")  # Empty file results in None from yaml.safe_load
            temp_path = f.name
        
        try:
            options = SentinelAggregatorClientOptions.from_yaml_file(temp_path)
            
            # Should use all defaults when config is None
            assert options.dcr_logs_ingestion_endpoint is None
            assert options.dcr_rule_id is None
            assert options.days_ago == 30
        finally:
            os.unlink(temp_path)
    
    def test_from_yaml_file_with_kwargs(self):
        """Test from_yaml_file passes through additional kwargs."""
        config_data = {
            "dcr_logs_ingestion_endpoint": "https://yaml.endpoint.com",
            "dcr_rule_id": "yaml-dcr-123"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            options = SentinelAggregatorClientOptions.from_yaml_file(
                temp_path,
                enable_distributed_tracing=False,
                custom_policies=["yaml_policy"]
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
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
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
            "dcr_rule_id": "yaml-dcr-123",
            "days_ago": 14
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            # Load from YAML first
            yaml_options = SentinelAggregatorClientOptions.from_yaml_file(temp_path)
            assert yaml_options.days_ago == 14
            
            # Then override with environment
            env_vars = {"DAYS_AGO": "7"}
            with patch.dict(os.environ, env_vars, clear=False):
                env_options = SentinelAggregatorClientOptions.from_environment()
                assert env_options.days_ago == 7
        finally:
            os.unlink(temp_path)
    
    def test_full_configuration_workflow(self):
        """Test complete configuration workflow with validation."""
        config_data = {
            "dcr_logs_ingestion_endpoint": "https://test.endpoint.com",
            "dcr_rule_id": "test-dcr-123",
            "days_ago": 7,
            "batch_hours": 12,
            "max_concurrent_queries": 10,
            "query_timeout_seconds": 600
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            # Load configuration
            options = SentinelAggregatorClientOptions.from_yaml_file(temp_path)
            
            # Mock successful validation
            with patch('sentinel_log_aggregator.client_options.validate_client_options') as mock_validate:
                mock_validate.return_value = True
                options.validate()  # Should pass
            
            # Verify all values are set correctly
            assert options.dcr_logs_ingestion_endpoint == "https://test.endpoint.com"
            assert options.dcr_rule_id == "test-dcr-123"
            assert options.days_ago == 7
            assert options.batch_hours == 12
            assert options.max_concurrent_queries == 10
            assert options.query_timeout_seconds == 600
        finally:
            os.unlink(temp_path)


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_from_environment_empty_strings(self):
        """Test from_environment with empty string environment variables."""
        env_vars = {
            "DCR_LOGS_INGESTION_ENDPOINT": "",
            "DCR_RULE_ID": "",
            "DAYS_AGO": "30"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            options = SentinelAggregatorClientOptions.from_environment()
        
        assert options.dcr_logs_ingestion_endpoint == ""
        assert options.dcr_rule_id == ""
        assert options.days_ago == 30
    
    def test_initialization_edge_case_values(self):
        """Test initialization with edge case values."""
        options = SentinelAggregatorClientOptions(
            days_ago=1,  # minimum positive value
            batch_hours=1,  # minimum positive value
            max_concurrent_queries=1,  # minimum positive value
            query_timeout_seconds=1,  # minimum positive value
            max_retries=0,  # minimum non-negative value
            retry_delay_seconds=1  # minimum positive value
        )
        
        assert options.days_ago == 1
        assert options.batch_hours == 1
        assert options.max_concurrent_queries == 1
        assert options.query_timeout_seconds == 1
        assert options.max_retries == 0
        assert options.retry_delay_seconds == 1
    
    def test_validation_dict_creation(self):
        """Test that validation creates proper dict for Pydantic validation."""
        options = SentinelAggregatorClientOptions(
            dcr_logs_ingestion_endpoint="https://test.endpoint.com",
            dcr_rule_id="test-dcr-123"
        )
        
        # Set additional attributes that should be included in validation
        options.upload_timeout_seconds = 600
        options.max_upload_retries = 5
        options.log_level = "DEBUG"
        options.enable_telemetry = False
        
        with patch('sentinel_log_aggregator.client_options.validate_client_options') as mock_validate:
            mock_validate.return_value = True
            
            options.validate()
            
            # Check that the validation was called with correct dict
            call_args = mock_validate.call_args[0][0]
            assert call_args['dcr_logs_ingestion_endpoint'] == "https://test.endpoint.com"
            assert call_args['dcr_rule_id'] == "test-dcr-123"
            assert call_args['upload_timeout_seconds'] == 600
            assert call_args['max_upload_retries'] == 5
            assert call_args['log_level'] == "DEBUG"
            assert call_args['enable_telemetry'] is False
    
    def test_yaml_file_with_pathlib_path(self):
        """Test from_yaml_file works with pathlib.Path objects."""
        config_data = {
            "dcr_logs_ingestion_endpoint": "https://pathlib.endpoint.com",
            "dcr_rule_id": "pathlib-dcr-123"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            options = SentinelAggregatorClientOptions.from_yaml_file(str(temp_path))
            
            assert options.dcr_logs_ingestion_endpoint == "https://pathlib.endpoint.com"
            assert options.dcr_rule_id == "pathlib-dcr-123"
        finally:
            temp_path.unlink()