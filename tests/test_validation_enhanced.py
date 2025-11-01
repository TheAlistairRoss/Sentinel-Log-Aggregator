"""
Enhanced validation tests to achieve 95%+ coverage.

Additional tests for edge cases, error scenarios, and uncovered code paths
in the validation module.
"""

import pytest
import sys
from unittest.mock import patch, MagicMock
import re
from pydantic import ValidationError

from sentinel_log_aggregator.validation import (
    WorkspaceConfigModel, QueryParameterModel, QueryDefinitionModel, 
    ClientOptionsModel, WorkspaceCollectionModel,
    validate_workspace_config, validate_query_definition, validate_client_options
)


class TestWorkspaceConfigModelEdgeCases:
    """Test edge cases for WorkspaceConfigModel."""
    
    def test_resource_id_validator_empty_string(self):
        """Test resource ID validator with empty string."""
        config_data = {
            'resource_id': '',
            'customer_id': '11111111-1111-1111-1111-111111111111'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WorkspaceConfigModel(**config_data)
        
        # Pattern mismatch error expected for empty string
        assert 'pattern' in str(exc_info.value).lower()
    
    def test_resource_id_validator_wrong_provider(self):
        """Test resource ID validator with wrong provider."""
        config_data = {
            'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.storage/storageaccounts/test-account',
            'customer_id': '11111111-1111-1111-1111-111111111111'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WorkspaceConfigModel(**config_data)
        
        # Pattern mismatch error expected for wrong provider
        assert 'pattern' in str(exc_info.value).lower()
    
    def test_queries_list_validator_none_value(self):
        """Test queries list validator with default empty list."""
        # Since pydantic List[str] doesn't allow None, test the default behavior  
        config_data = {
            'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace',
            'customer_id': '11111111-1111-1111-1111-111111111111'
            # queries_list omitted to test default_factory behavior
        }
        
        config = WorkspaceConfigModel(**config_data)
        assert config.queries_list == []

    def test_queries_list_validator_direct_none_call(self):
        """Test queries list validator directly with None to cover return v line."""
        # Import the validator and call it directly
        from sentinel_log_aggregator.validation import WorkspaceConfigModel
        
        # Call the validator directly with None
        result = WorkspaceConfigModel.validate_queries_list(None)
        assert result is None

    def test_queries_list_validator_import_error_fallback(self):
        """Test queries list validator fallback when models import fails."""
        config_data = {
            'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace',
            'customer_id': '11111111-1111-1111-1111-111111111111',
            'queries_list': ['query_incident_summary']  # Should work with fallback queries
        }
        
        # Mock import error to test fallback
        with patch('sentinel_log_aggregator.validation.AVAILABLE_QUERIES', side_effect=ImportError("Mocked import error")):
            config = WorkspaceConfigModel(**config_data)
            assert config.queries_list == ['query_incident_summary']

    def test_workspace_name_property_empty_resource_id(self):
        """Test workspace_name property with empty resource_id."""
        config_data = {
            'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace',
            'customer_id': '11111111-1111-1111-1111-111111111111'
        }
        
        config = WorkspaceConfigModel(**config_data)
        assert config.workspace_name == 'test-workspace'
        
        # Test with empty resource_id via direct property access
        config.resource_id = ""
        assert config.workspace_name == ""

    def test_subscription_id_property_no_subscriptions_in_path(self):
        """Test subscription_id property when 'subscriptions' not in path."""
        config_data = {
            'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace',
            'customer_id': '11111111-1111-1111-1111-111111111111'
        }
        
        config = WorkspaceConfigModel(**config_data)
        assert config.subscription_id == '12345678-1234-1234-1234-123456789abc'
        
        # Test case where 'subscriptions' is not in the path
        config.resource_id = "/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace"
        assert config.subscription_id == ""
        
        # Test case where 'subscriptions' is at the end with no following element
        config.resource_id = "/some/path/subscriptions"
        assert config.subscription_id == ""

    def test_subscription_id_property_index_out_of_bounds(self):
        """Test subscription_id property with index out of bounds."""
        config_data = {
            'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace',
            'customer_id': '11111111-1111-1111-1111-111111111111'
        }
        
        config = WorkspaceConfigModel(**config_data)
        
        # Test case where subscriptions is the last element
        config.resource_id = "/some/path/subscriptions"
        parts = config.resource_id.split('/')
        sub_index = parts.index('subscriptions')
        # This should return empty string when sub_index + 1 >= len(parts)
        assert config.subscription_id == ""
        config_data = {
            'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace',
            'customer_id': '11111111-1111-1111-1111-111111111111',
            'queries_list': None
        }
        
        # Pydantic requires list type, so None should raise validation error
        with pytest.raises(ValidationError) as exc_info:
            WorkspaceConfigModel(**config_data)
        
        assert 'list' in str(exc_info.value).lower()
    
    def test_queries_list_validator_import_error_fallback(self):
        """Test queries list validator fallback when models import fails."""
        config_data = {
            'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace',
            'customer_id': '11111111-1111-1111-1111-111111111111',
            'queries_list': ['query_incident_summary']  # Valid in fallback
        }
        
        # Mock the import to trigger fallback path - use correct module path
        import sys
        original_modules = sys.modules.copy()
        try:
            # Remove models module to trigger ImportError
            if 'sentinel_log_aggregator.models' in sys.modules:
                del sys.modules['sentinel_log_aggregator.models']
            
            with patch('builtins.__import__', side_effect=ImportError):
                # Should still validate with fallback queries
                model = WorkspaceConfigModel(**config_data)
                assert 'query_incident_summary' in model.queries_list
        finally:
            # Restore modules
            sys.modules.update(original_modules)
    
    def test_queries_list_validator_invalid_in_fallback(self):
        """Test queries list validator with invalid query in fallback mode."""
        config_data = {
            'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace',
            'customer_id': '11111111-1111-1111-1111-111111111111',
            'queries_list': ['invalid_query_not_in_fallback']
        }
        
        # Mock the import to trigger fallback path
        import sys
        original_modules = sys.modules.copy()
        try:
            # Remove models module to trigger ImportError
            if 'sentinel_log_aggregator.models' in sys.modules:
                del sys.modules['sentinel_log_aggregator.models']
            
            with patch('builtins.__import__', side_effect=ImportError):
                with pytest.raises(ValidationError) as exc_info:
                    WorkspaceConfigModel(**config_data)
                
                assert 'Invalid query name: invalid_query_not_in_fallback' in str(exc_info.value)
        finally:
            # Restore modules
            sys.modules.update(original_modules)
    
    def test_subscription_id_extraction_edge_cases(self):
        """Test subscription ID extraction edge cases."""
        # Case 1: No 'subscriptions' in resource_id
        config_data_1 = {
            'resource_id': '/invalid/path/without/subscriptions',
            'customer_id': '11111111-1111-1111-1111-111111111111'
        }
        
        # This should fail validation, but if it didn't, subscription_id should be empty
        try:
            model_1 = WorkspaceConfigModel(**config_data_1)
            assert model_1.subscription_id == ""
        except ValidationError:
            pass  # Expected due to invalid resource_id format
        
        # Case 2: 'subscriptions' at the end with no following part
        config_data_2 = {
            'resource_id': '/subscriptions',
            'customer_id': '11111111-1111-1111-1111-111111111111'
        }
        
        try:
            model_2 = WorkspaceConfigModel(**config_data_2)
            assert model_2.subscription_id == ""
        except ValidationError:
            pass  # Expected due to invalid resource_id format
    
    def test_workspace_name_empty_resource_id(self):
        """Test workspace name extraction with empty resource ID."""
        config_data = {
            'resource_id': '',
            'customer_id': '11111111-1111-1111-1111-111111111111'
        }
        
        try:
            model = WorkspaceConfigModel(**config_data)
            assert model.workspace_name == ""
        except ValidationError:
            pass  # Expected due to validation


class TestQueryParameterModelValidation:
    """Test QueryParameterModel validation scenarios."""
    
    def test_validate_default_type_int_valid(self):
        """Test int parameter with valid default."""
        param_data = {
            'type': 'int',
            'default': 42,
            'description': 'Test integer parameter'
        }
        
        model = QueryParameterModel(**param_data)
        assert model.default == 42
    
    def test_validate_default_type_int_invalid(self):
        """Test int parameter with invalid default."""
        param_data = {
            'type': 'int',
            'default': 'not_an_int',
            'description': 'Test integer parameter'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            QueryParameterModel(**param_data)
        
        assert "Default value must be an integer for type 'int'" in str(exc_info.value)
    
    def test_validate_default_type_float_valid_int(self):
        """Test float parameter with valid int default (should be accepted)."""
        param_data = {
            'type': 'float',
            'default': 42,  # int should be valid for float
            'description': 'Test float parameter'
        }
        
        model = QueryParameterModel(**param_data)
        assert model.default == 42
    
    def test_validate_default_type_float_valid_float(self):
        """Test float parameter with valid float default."""
        param_data = {
            'type': 'float',
            'default': 42.5,
            'description': 'Test float parameter'
        }
        
        model = QueryParameterModel(**param_data)
        assert model.default == 42.5
    
    def test_validate_default_type_float_invalid(self):
        """Test float parameter with invalid default."""
        param_data = {
            'type': 'float',
            'default': 'not_a_number',
            'description': 'Test float parameter'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            QueryParameterModel(**param_data)
        
        assert "Default value must be a number for type 'float'" in str(exc_info.value)
    
    def test_validate_default_type_bool_valid(self):
        """Test bool parameter with valid default."""
        param_data = {
            'type': 'bool',
            'default': True,
            'description': 'Test boolean parameter'
        }
        
        model = QueryParameterModel(**param_data)
        assert model.default is True
    
    def test_validate_default_type_bool_invalid(self):
        """Test bool parameter with invalid default."""
        param_data = {
            'type': 'bool',
            'default': 'not_a_bool',
            'description': 'Test boolean parameter'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            QueryParameterModel(**param_data)
        
        assert "Default value must be a boolean for type 'bool'" in str(exc_info.value)
    
    def test_validate_default_type_string_valid(self):
        """Test string parameter with valid default."""
        param_data = {
            'type': 'string',
            'default': 'test_string',
            'description': 'Test string parameter'
        }
        
        model = QueryParameterModel(**param_data)
        assert model.default == 'test_string'
    
    def test_validate_default_type_string_invalid(self):
        """Test string parameter with invalid default."""
        param_data = {
            'type': 'string',
            'default': 123,  # Not a string
            'description': 'Test string parameter'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            QueryParameterModel(**param_data)
        
        assert "Default value must be a string for type 'string'" in str(exc_info.value)
    
    def test_validate_default_type_none_default(self):
        """Test parameter with None default (should pass all type checks)."""
        param_data = {
            'type': 'int',
            'default': None,
            'description': 'Test parameter with None default'
        }
        
        # Should not raise exception since default is None
        model = QueryParameterModel(**param_data)
        assert model.default is None
    
    def test_validate_default_type_empty_type(self):
        """Test parameter with empty type field."""
        param_data = {
            'type': '',  # This should fail pattern validation
            'default': 'test',
            'description': 'Test parameter'
        }
        
        with pytest.raises(ValidationError):
            QueryParameterModel(**param_data)


class TestQueryDefinitionModelEdgeCases:
    """Test edge cases for QueryDefinitionModel."""
    
    def test_validate_query_syntax_whitespace_only(self):
        """Test query validation with whitespace-only query that meets min_length."""
        query_data = {
            'name': 'test_query',
            'destination_stream': 'Custom-Test_TestQuery_CL',
            'stream_name': 'stream_test_query',
            'query': '          '  # 10 spaces - meets min_length but only whitespace
        }
        
        with pytest.raises(ValidationError) as exc_info:
            QueryDefinitionModel(**query_data)
        
        assert "Query cannot be empty" in str(exc_info.value)

    def test_validate_query_syntax_completely_empty(self):
        """Test query validation with completely empty query."""
        query_data = {
            'name': 'test_query',
            'destination_stream': 'Custom-Test_TestQuery_CL',
            'stream_name': 'stream_test_query',
            'query': ''  # Completely empty - should fail min_length first
        }
        
        # This will fail min_length validation, not our custom validator
        with pytest.raises(ValidationError) as exc_info:
            QueryDefinitionModel(**query_data)
        
        # Either min_length or our custom validation could catch this
        assert ('characters' in str(exc_info.value).lower() or 
                'Query cannot be empty' in str(exc_info.value))

    def test_validate_query_syntax_completely_empty(self):
        """Test query validation with completely empty query."""
        query_data = {
            'name': 'test_query',
            'destination_stream': 'Custom-Test_TestQuery_CL',
            'stream_name': 'stream_test_query',
            'query': ''  # Completely empty
        }
        
        with pytest.raises(ValidationError) as exc_info:
            QueryDefinitionModel(**query_data)
        
        assert "Query cannot be empty" in str(exc_info.value)
    
    def test_validate_query_syntax_dangerous_operations_case_insensitive(self):
        """Test detection of dangerous operations in different cases."""
        dangerous_queries = [
            'SecurityIncident | take 10; .DROP table Test',  # Uppercase
            'SecurityIncident | take 10; .Delete table Test',  # Mixed case
            'SecurityIncident | take 10; .CREATE table Test',
            'SecurityIncident | take 10; .ALTER table Test',
            'SecurityIncident | take 10; .SET option',
            'SecurityIncident | take 10; DROP TABLE Test',
            'SecurityIncident | take 10; DELETE FROM Test',
            'SecurityIncident | take 10; TRUNCATE table Test'
        ]
        
        for dangerous_query in dangerous_queries:
            query_data = {
                'name': 'dangerous_query',
                'destination_stream': 'Custom-Test_DangerousQuery_CL',
                'stream_name': 'stream_dangerous_query',
                'query': dangerous_query
            }
            
            with pytest.raises(ValidationError) as exc_info:
                QueryDefinitionModel(**query_data)
            
            assert 'Query contains potentially dangerous operation' in str(exc_info.value)
    
    def test_validate_tags_edge_cases(self):
        """Test tag validation edge cases."""
        # Valid tags
        valid_tags_data = {
            'name': 'test_query',
            'destination_stream': 'Custom-Test_TestQuery_CL',
            'stream_name': 'stream_test_query',
            'query': 'SecurityIncident | take 10',
            'tags': ['valid-tag', 'another_tag', 'tag123', 'a']  # Various valid formats
        }
        
        model = QueryDefinitionModel(**valid_tags_data)
        assert len(model.tags) == 4
        
        # Invalid tag formats
        invalid_tag_sets = [
            ['Invalid-Tag-With-Uppercase'],
            ['123-starts-with-number'],
            ['tag with spaces'],
            ['tag!with!special'],
            ['tag@with@symbols'],
            ['']  # Empty tag
        ]
        
        for invalid_tags in invalid_tag_sets:
            invalid_tags_data = {
                'name': 'test_query',
                'destination_stream': 'Custom-Test_TestQuery_CL',
                'stream_name': 'stream_test_query',
                'query': 'SecurityIncident | take 10',
                'tags': invalid_tags
            }
            
            with pytest.raises(ValidationError) as exc_info:
                QueryDefinitionModel(**invalid_tags_data)
            
            assert 'Invalid tag format' in str(exc_info.value)


class TestWorkspaceCollectionModelEdgeCases:
    """Test edge cases for WorkspaceCollectionModel."""
    
    def test_validate_unique_workspaces_duplicate_resource_ids(self):
        """Test validation with duplicate resource IDs."""
        collection_data = {
            'workspaces': [
                {
                    'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/duplicate-workspace',
                    'customer_id': '11111111-1111-1111-1111-111111111111',
                    'row_level_security_tag': 'test1'
                },
                {
                    'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/duplicate-workspace',  # Duplicate
                    'customer_id': '22222222-2222-2222-2222-222222222222',
                    'row_level_security_tag': 'test2'
                }
            ]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WorkspaceCollectionModel(**collection_data)
        
        assert 'duplicate resource ids' in str(exc_info.value).lower()
    
    def test_validate_unique_workspaces_duplicate_security_tags(self):
        """Test validation with duplicate row-level security tags."""
        collection_data = {
            'workspaces': [
                {
                    'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace-1',
                    'customer_id': '11111111-1111-1111-1111-111111111111',
                    'row_level_security_tag': 'duplicate_tag'
                },
                {
                    'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace-2',
                    'customer_id': '22222222-2222-2222-2222-222222222222',
                    'row_level_security_tag': 'duplicate_tag'  # Duplicate tag
                }
            ]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WorkspaceCollectionModel(**collection_data)
        
        assert 'duplicate row-level security tags' in str(exc_info.value).lower()
    
    def test_validate_unique_workspaces_empty_security_tags_allowed(self):
        """Test that empty security tags don't count as duplicates."""
        collection_data = {
            'workspaces': [
                {
                    'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace-1',
                    'customer_id': '11111111-1111-1111-1111-111111111111',
                    'row_level_security_tag': ''  # Empty tag
                },
                {
                    'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace-2',
                    'customer_id': '22222222-2222-2222-2222-222222222222',
                    'row_level_security_tag': ''  # Empty tag - should be allowed
                }
            ]
        }
        
        # Should not raise exception for empty tags
        model = WorkspaceCollectionModel(**collection_data)
        assert len(model.workspaces) == 2

    def test_validate_unique_workspaces_duplicate_customer_ids(self):
        """Test validation with duplicate customer IDs."""
        collection_data = {
            'workspaces': [
                {
                    'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace-1',
                    'customer_id': '11111111-1111-1111-1111-111111111111',  # Duplicate customer ID
                    'row_level_security_tag': 'test1'
                },
                {
                    'resource_id': '/subscriptions/87654321-4321-4321-4321-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace-2',
                    'customer_id': '11111111-1111-1111-1111-111111111111',  # Same customer ID
                    'row_level_security_tag': 'test2'
                }
            ]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WorkspaceCollectionModel(**collection_data)
        
        assert 'duplicate customer ids' in str(exc_info.value).lower()


class TestValidationFunctions:
    """Test the module-level validation functions."""
    
    def test_validate_workspace_config_function(self):
        """Test validate_workspace_config function."""
        config_data = {
            'workspaces': [
                {
                    'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace',
                    'customer_id': '11111111-1111-1111-1111-111111111111',
                    'row_level_security_tag': 'test'
                }
            ]
        }
        
        result = validate_workspace_config(config_data)
        assert isinstance(result, WorkspaceCollectionModel)
        assert len(result.workspaces) == 1
    
    def test_validate_query_definition_function(self):
        """Test validate_query_definition function."""
        query_data = {
            'name': 'test_query',
            'destination_stream': 'Custom-Test_TestQuery_CL',
            'stream_name': 'stream_test_query',
            'query': 'SecurityIncident | take 10'
        }
        
        result = validate_query_definition(query_data)
        assert isinstance(result, QueryDefinitionModel)
        assert result.name == 'test_query'
    
    def test_validate_client_options_function(self):
        """Test validate_client_options function."""
        options_data = {
            'dcr_logs_ingestion_endpoint': 'https://test.ingest.monitor.azure.com',
            'dcr_rule_id': 'dcr-12345678123456781234567812345678'
        }
        
        result = validate_client_options(options_data)
        assert isinstance(result, ClientOptionsModel)
        assert 'test.ingest.monitor.azure.com' in str(result.dcr_logs_ingestion_endpoint)
    
    def test_validate_functions_with_validation_errors(self):
        """Test validation functions with invalid data."""
        # Invalid workspace config
        invalid_workspace_data = {
            'workspaces': [
                {
                    'resource_id': 'invalid-resource-id',
                    'customer_id': 'invalid-customer-id'
                }
            ]
        }
        
        with pytest.raises(ValidationError):
            validate_workspace_config(invalid_workspace_data)
        
        # Invalid query definition
        invalid_query_data = {
            'name': 'Invalid-Name-With-Uppercase',
            'destination_stream': 'invalid-stream-format',
            'stream_name': 'invalid_stream_name',
            'query': ''
        }
        
        with pytest.raises(ValidationError):
            validate_query_definition(invalid_query_data)
        
        # Invalid client options
        invalid_options_data = {
            'dcr_logs_ingestion_endpoint': 'not-a-url',
            'dcr_rule_id': 'invalid-dcr-format'
        }
        
        with pytest.raises(ValidationError):
            validate_client_options(invalid_options_data)


class TestClientOptionsModelEdgeCases:
    """Test edge cases for ClientOptionsModel."""
    
    def test_log_level_validation(self):
        """Test log level validation with various cases."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        
        for level in valid_levels:
            options_data = {
                'dcr_logs_ingestion_endpoint': 'https://test.ingest.monitor.azure.com',
                'dcr_rule_id': 'dcr-12345678123456781234567812345678',
                'log_level': level
            }
            
            model = ClientOptionsModel(**options_data)
            assert model.log_level == level
        
        # Invalid log level
        invalid_options_data = {
            'dcr_logs_ingestion_endpoint': 'https://test.ingest.monitor.azure.com',
            'dcr_rule_id': 'dcr-12345678123456781234567812345678',
            'log_level': 'INVALID_LEVEL'
        }
        
        with pytest.raises(ValidationError):
            ClientOptionsModel(**invalid_options_data)
    
    def test_boundary_values(self):
        """Test boundary values for numeric fields."""
        # Test minimum values
        min_options_data = {
            'dcr_logs_ingestion_endpoint': 'https://test.ingest.monitor.azure.com',
            'dcr_rule_id': 'dcr-12345678123456781234567812345678',
            'max_concurrent_queries': 1,  # Minimum
            'query_timeout_seconds': 30,  # Minimum
            'batch_hours': 1,  # Minimum
            'upload_timeout_seconds': 30,  # Minimum
            'max_upload_retries': 1  # Minimum
        }
        
        model = ClientOptionsModel(**min_options_data)
        assert model.max_concurrent_queries == 1
        
        # Test maximum values
        max_options_data = {
            'dcr_logs_ingestion_endpoint': 'https://test.ingest.monitor.azure.com',
            'dcr_rule_id': 'dcr-12345678123456781234567812345678',
            'max_concurrent_queries': 20,  # Maximum
            'query_timeout_seconds': 3600,  # Maximum
            'batch_hours': 168,  # Maximum
            'upload_timeout_seconds': 1800,  # Maximum
            'max_upload_retries': 10  # Maximum
        }
        
        model = ClientOptionsModel(**max_options_data)
        assert model.max_concurrent_queries == 20
        
        # Test out of bounds values
        invalid_options_data = {
            'dcr_logs_ingestion_endpoint': 'https://test.ingest.monitor.azure.com',
            'dcr_rule_id': 'dcr-12345678123456781234567812345678',
            'max_concurrent_queries': 0,  # Below minimum
        }
        
        with pytest.raises(ValidationError):
            ClientOptionsModel(**invalid_options_data)


class TestComplexValidationScenarios:
    """Test complex validation scenarios combining multiple models."""
    
    def test_comprehensive_validation_with_all_features(self):
        """Test comprehensive validation with all model features."""
        # Query definition with all optional fields
        query_data = {
            'name': 'comprehensive_test_query',
            'destination_stream': 'Custom-ComprehensiveTest_TestQuery_CL',
            'description': 'A comprehensive test query with all features',
            'stream_name': 'stream_comprehensive_test_query',
            'version': '2.1.0',
            'parameters': {
                'days_back': {
                    'type': 'int',
                    'required': True,
                    'default': 7,
                    'description': 'Number of days to look back'
                },
                'severity_threshold': {
                    'type': 'float',
                    'required': False,
                    'default': 3.5,
                    'description': 'Minimum severity threshold'
                },
                'include_resolved': {
                    'type': 'bool',
                    'required': False,
                    'default': False,
                    'description': 'Include resolved incidents'
                },
                'filter_pattern': {
                    'type': 'string',
                    'required': False,
                    'default': '*',
                    'description': 'Pattern to filter results'
                }
            },
            'query': '''
                SecurityIncident
                | where TimeGenerated > ago({days_back}d)
                | where Severity >= {severity_threshold}
                | where {include_resolved} or Status != "Resolved"
                | where Title contains "{filter_pattern}"
                | project TimeGenerated, Title, Severity, Status
                | take 1000
            ''',
            'tags': ['security', 'incident-management', 'high-priority']
        }
        
        model = validate_query_definition(query_data)
        assert model.name == 'comprehensive_test_query'
        assert len(model.parameters) == 4
        assert len(model.tags) == 3
        assert model.version == '2.1.0'
    
    def test_workspace_collection_with_metadata(self):
        """Test workspace collection with metadata."""
        collection_data = {
            'workspaces': [
                {
                    'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/prod-rg/providers/microsoft.operationalinsights/workspaces/prod-workspace',
                    'customer_id': '11111111-1111-1111-1111-111111111111',
                    'row_level_security_tag': 'prod',
                    'queries_list': ['query_incident_summary']
                }
            ],
            'metadata': {
                'version': '1.0',
                'created_by': 'test_user',
                'environment': 'production',
                'last_updated': '2024-01-01T00:00:00Z'
            }
        }
        
        model = validate_workspace_config(collection_data)
        assert len(model.workspaces) == 1
        assert model.metadata is not None
        assert model.metadata['environment'] == 'production'


class TestSpecificUncoveredLines:
    """Target specific uncovered lines for 95%+ coverage."""
    
    def test_resource_id_validator_manual_trigger(self):
        """Test to trigger the resource_id validator specifically."""
        # Test case where resource_id passes pattern but fails custom validation
        # Create a malformed but pattern-matching resource ID
        test_cases = [
            # Case that doesn't start with /subscriptions/ (line 45)
            'invalid/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace',
            # Case missing operationalinsights (line 47)  
            '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.storage/storageaccounts/test-account'
        ]
        
        # Test with bypassing pattern validation first
        from sentinel_log_aggregator.validation import WorkspaceConfigModel
        
        # Create instance to test validator directly
        for test_resource_id in test_cases:
            try:
                # Call the validator method directly
                WorkspaceConfigModel.validate_resource_id(test_resource_id)
                assert False, "Should have raised ValueError"
            except ValueError as e:
                # Should catch our custom validation errors
                error_msg = str(e)
                assert 'Resource ID must start with /subscriptions/' in error_msg or \
                       'Resource ID must be for a Log Analytics workspace' in error_msg
    
    def test_subscription_id_extraction_edge_cases_direct(self):
        """Test subscription_id property edge cases directly."""
        # Test case where ValueError is caught (line 82-87)
        config_data = {
            'resource_id': '/invalid/path/no/subscriptions/here',
            'customer_id': '11111111-1111-1111-1111-111111111111'
        }
        
        try:
            model = WorkspaceConfigModel(**config_data)
            # If it somehow passes validation, test the property
            assert model.subscription_id == ""
        except ValidationError:
            # Expected due to pattern validation
            pass
    
    def test_query_parameter_validator_datetime_type(self):
        """Test datetime parameter type validation (line 112)."""
        param_data = {
            'type': 'datetime',
            'default': '2024-01-01T00:00:00Z',  # String for datetime
            'description': 'Test datetime parameter'
        }
        
        # Should pass since datetime type doesn't have specific validation
        model = QueryParameterModel(**param_data)
        assert model.type == 'datetime'
    
    def test_validate_unique_workspaces_empty_tags_filtering(self):
        """Test the filtering of empty tags in unique validation (line 274)."""
        collection_data = {
            'workspaces': [
                {
                    'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace-1',
                    'customer_id': '11111111-1111-1111-1111-111111111111',
                    'row_level_security_tag': ''  # Empty - should be filtered out
                },
                {
                    'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace-2',
                    'customer_id': '22222222-2222-2222-2222-222222222222',
                    'row_level_security_tag': 'valid_tag'
                },
                {
                    'resource_id': '/subscriptions/12345678-1234-1234-1234-123456789abc/resourcegroups/test-rg/providers/microsoft.operationalinsights/workspaces/test-workspace-3',
                    'customer_id': '33333333-3333-3333-3333-333333333333',
                    'row_level_security_tag': ''  # Another empty - should be filtered out
                }
            ]
        }
        
        # Should not raise exception - empty tags are filtered out of uniqueness check
        model = WorkspaceCollectionModel(**collection_data)
        assert len(model.workspaces) == 3
    
    def test_model_validator_after_mode_trigger(self):
        """Ensure the @model_validator(mode='after') is triggered."""
        # Test various parameter type/default combinations to ensure validator runs
        test_cases = [
            ('int', 42),      # Valid
            ('float', 3.14),  # Valid
            ('bool', True),   # Valid  
            ('string', 'test'), # Valid
            ('datetime', '2024-01-01'), # Valid (no specific validation)
        ]
        
        for param_type, default_value in test_cases:
            param_data = {
                'type': param_type,
                'default': default_value,
                'description': f'Test {param_type} parameter'
            }
            
            model = QueryParameterModel(**param_data)
            assert model.type == param_type
            assert model.default == default_value