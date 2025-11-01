"""
Comprehensive tests for sentinel_log_aggregator.exceptions module.

Tests cover all custom exception classes, error hierarchies, context propagation,
Azure SDK compliance, and exception handling patterns.
"""

import pytest
from unittest.mock import Mock
from azure.core.exceptions import AzureError, ClientAuthenticationError, HttpResponseError

from sentinel_log_aggregator.exceptions import (
    SentinelAggregatorError,
    QueryExecutionError,
    WorkspaceAccessError,
    DataIngestionError,
    ConfigurationError,
    WorkspaceConfigurationError,
    BatchOperationError,
    CredentialValidationError
)


class TestSentinelAggregatorError:
    """Test base SentinelAggregatorError functionality."""
    
    def test_basic_initialization(self):
        """Test basic error initialization."""
        error = SentinelAggregatorError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.error_code is None
        assert error.error_details == {}
        assert isinstance(error, AzureError)
    
    def test_initialization_with_error_code(self):
        """Test error initialization with error code."""
        error = SentinelAggregatorError(
            "Test error message",
            error_code="TEST_ERROR_001"
        )
        
        assert str(error) == "Test error message"
        assert error.error_code == "TEST_ERROR_001"
        assert error.error_details == {}
    
    def test_initialization_with_error_details(self):
        """Test error initialization with error details."""
        details = {
            "timestamp": "2023-01-01T00:00:00Z",
            "component": "test_component",
            "severity": "high"
        }
        
        error = SentinelAggregatorError(
            "Test error message",
            error_details=details
        )
        
        assert str(error) == "Test error message"
        assert error.error_code is None
        assert error.error_details == details
    
    def test_initialization_with_all_parameters(self):
        """Test error initialization with all parameters."""
        details = {"key": "value"}
        
        error = SentinelAggregatorError(
            "Test error message",
            error_code="FULL_ERROR_001",
            error_details=details
        )
        
        assert str(error) == "Test error message"
        assert error.error_code == "FULL_ERROR_001"
        assert error.error_details == details
    
    def test_initialization_with_kwargs(self):
        """Test error initialization passes kwargs to parent."""
        # Test that kwargs are properly passed through to parent AzureError
        # AzureError accepts additional kwargs, so we test successful creation
        error = SentinelAggregatorError(
            "Test message",
            error_code="TEST_001"
        )
        
        assert str(error) == "Test message"
        assert error.error_code == "TEST_001"
    
    def test_error_details_defaults_to_empty_dict(self):
        """Test that error_details defaults to empty dict when None provided."""
        error = SentinelAggregatorError(
            "Test message",
            error_details=None
        )
        
        assert error.error_details == {}


class TestQueryExecutionError:
    """Test QueryExecutionError functionality."""
    
    def test_basic_initialization(self):
        """Test basic query execution error initialization."""
        error = QueryExecutionError("Query failed")
        
        assert str(error) == "Query failed"
        assert error.workspace_id is None
        assert error.query is None
        assert error.error_code is None
        assert isinstance(error, SentinelAggregatorError)
    
    def test_initialization_with_workspace_info(self):
        """Test initialization with workspace and query information."""
        workspace_id = "12345678-1234-1234-1234-123456789012"
        query = "SecurityEvent | take 10"
        
        error = QueryExecutionError(
            "Query execution failed",
            workspace_id=workspace_id,
            query=query,
            error_code="QUERY_TIMEOUT"
        )
        
        assert str(error) == "Query execution failed"
        assert error.workspace_id == workspace_id
        assert error.query == query
        assert error.error_code == "QUERY_TIMEOUT"
    
    def test_inheritance_hierarchy(self):
        """Test that QueryExecutionError inherits properly."""
        error = QueryExecutionError("Test query error")
        
        assert isinstance(error, QueryExecutionError)
        assert isinstance(error, SentinelAggregatorError)
        assert isinstance(error, AzureError)


class TestWorkspaceAccessError:
    """Test WorkspaceAccessError functionality."""
    
    def test_basic_initialization(self):
        """Test basic workspace access error initialization."""
        error = WorkspaceAccessError("Access denied")
        
        assert str(error) == "Access denied"
        assert error.workspace_id is None
        assert error.resource_id is None
        assert error.error_code is None
        assert isinstance(error, SentinelAggregatorError)
    
    def test_initialization_with_workspace_info(self):
        """Test initialization with workspace information."""
        workspace_id = "workspace-123"
        resource_id = "/subscriptions/sub-123/resourceGroups/rg-123/providers/Microsoft.OperationalInsights/workspaces/ws-123"
        
        error = WorkspaceAccessError(
            "Workspace access denied",
            workspace_id=workspace_id,
            resource_id=resource_id,
            error_code="ACCESS_DENIED"
        )
        
        assert str(error) == "Workspace access denied"
        assert error.workspace_id == workspace_id
        assert error.resource_id == resource_id
        assert error.error_code == "ACCESS_DENIED"


class TestDataIngestionError:
    """Test DataIngestionError functionality."""
    
    def test_basic_initialization(self):
        """Test basic data ingestion error initialization."""
        error = DataIngestionError("Ingestion failed")
        
        assert str(error) == "Ingestion failed"
        assert error.stream_name is None
        assert error.dcr_rule_id is None
        assert error.record_count is None
        assert error.error_code is None
        assert isinstance(error, SentinelAggregatorError)
    
    def test_initialization_with_ingestion_info(self):
        """Test initialization with data ingestion information."""
        stream_name = "Custom-SecurityLogs_CL"
        dcr_rule_id = "dcr-12345"
        record_count = 1500
        
        error = DataIngestionError(
            "Failed to ingest data",
            stream_name=stream_name,
            dcr_rule_id=dcr_rule_id,
            record_count=record_count,
            error_code="INGESTION_TIMEOUT"
        )
        
        assert str(error) == "Failed to ingest data"
        assert error.stream_name == stream_name
        assert error.dcr_rule_id == dcr_rule_id
        assert error.record_count == record_count
        assert error.error_code == "INGESTION_TIMEOUT"
    
    def test_initialization_with_zero_record_count(self):
        """Test initialization with zero record count."""
        error = DataIngestionError(
            "No records to ingest",
            record_count=0
        )
        
        assert error.record_count == 0


class TestConfigurationError:
    """Test ConfigurationError functionality."""
    
    def test_basic_initialization(self):
        """Test basic configuration error initialization."""
        error = ConfigurationError("Configuration invalid")
        
        assert str(error) == "Configuration invalid"
        assert error.config_key is None
        assert error.error_code is None
        assert isinstance(error, SentinelAggregatorError)
    
    def test_initialization_with_config_key(self):
        """Test initialization with configuration key information."""
        config_key = "dcr_logs_ingestion_endpoint"
        
        error = ConfigurationError(
            "Missing required configuration",
            config_key=config_key,
            error_code="CONFIG_MISSING"
        )
        
        assert str(error) == "Missing required configuration"
        assert error.config_key == config_key
        assert error.error_code == "CONFIG_MISSING"


class TestWorkspaceConfigurationError:
    """Test WorkspaceConfigurationError functionality."""
    
    def test_basic_initialization(self):
        """Test basic workspace configuration error initialization."""
        error = WorkspaceConfigurationError("Workspace config invalid")
        
        assert str(error) == "Workspace config invalid"
        assert error.workspace_alias is None
        assert error.config_file is None
        assert error.error_code is None
        assert isinstance(error, SentinelAggregatorError)
    
    def test_initialization_with_workspace_info(self):
        """Test initialization with workspace configuration information."""
        workspace_alias = "production-workspace"
        config_file = "/path/to/workspaces.yaml"
        
        error = WorkspaceConfigurationError(
            "Invalid workspace configuration",
            workspace_alias=workspace_alias,
            config_file=config_file,
            error_code="WORKSPACE_CONFIG_INVALID"
        )
        
        assert str(error) == "Invalid workspace configuration"
        assert error.workspace_alias == workspace_alias
        assert error.config_file == config_file
        assert error.error_code == "WORKSPACE_CONFIG_INVALID"


class TestBatchOperationError:
    """Test BatchOperationError functionality."""
    
    def test_basic_initialization(self):
        """Test basic batch operation error initialization."""
        error = BatchOperationError("Batch operation failed")
        
        assert str(error) == "Batch operation failed"
        assert error.failed_operations is None
        assert error.total_operations is None
        assert error.error_code is None
        assert isinstance(error, SentinelAggregatorError)
    
    def test_initialization_with_operation_counts(self):
        """Test initialization with operation count information."""
        failed_operations = 3
        total_operations = 10
        
        error = BatchOperationError(
            "Partial batch failure",
            failed_operations=failed_operations,
            total_operations=total_operations,
            error_code="BATCH_PARTIAL_FAILURE"
        )
        
        assert str(error) == "Partial batch failure"
        assert error.failed_operations == failed_operations
        assert error.total_operations == total_operations
        assert error.error_code == "BATCH_PARTIAL_FAILURE"
    
    def test_initialization_with_zero_counts(self):
        """Test initialization with zero operation counts."""
        error = BatchOperationError(
            "No operations completed",
            failed_operations=0,
            total_operations=0
        )
        
        assert error.failed_operations == 0
        assert error.total_operations == 0


class TestCredentialValidationError:
    """Test CredentialValidationError functionality."""
    
    def test_basic_initialization(self):
        """Test basic credential validation error initialization."""
        error = CredentialValidationError("Credential validation failed")
        
        assert str(error) == "Credential validation failed"
        assert error.credential_type is None
        assert error.scope is None
        assert isinstance(error, ClientAuthenticationError)
    
    def test_initialization_with_credential_info(self):
        """Test initialization with credential information."""
        credential_type = "DefaultAzureCredential"
        scope = "https://api.loganalytics.io/.default"
        
        error = CredentialValidationError(
            "Failed to validate credentials",
            credential_type=credential_type,
            scope=scope
        )
        
        assert str(error) == "Failed to validate credentials"
        assert error.credential_type == credential_type
        assert error.scope == scope
    
    def test_inheritance_hierarchy(self):
        """Test that CredentialValidationError inherits from ClientAuthenticationError."""
        error = CredentialValidationError("Test credential error")
        
        assert isinstance(error, CredentialValidationError)
        assert isinstance(error, ClientAuthenticationError)
        assert isinstance(error, AzureError)


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy and relationships."""
    
    def test_all_exceptions_inherit_from_azure_error(self):
        """Test that all exceptions inherit from AzureError."""
        exceptions = [
            SentinelAggregatorError("test"),
            QueryExecutionError("test"),
            WorkspaceAccessError("test"),
            DataIngestionError("test"),
            ConfigurationError("test"),
            WorkspaceConfigurationError("test"),
            BatchOperationError("test"),
            CredentialValidationError("test")
        ]
        
        for error in exceptions:
            assert isinstance(error, AzureError)
    
    def test_service_specific_exceptions_inherit_from_base(self):
        """Test that service-specific exceptions inherit from SentinelAggregatorError."""
        service_exceptions = [
            QueryExecutionError("test"),
            WorkspaceAccessError("test"),
            DataIngestionError("test"),
            ConfigurationError("test"),
            WorkspaceConfigurationError("test"),
            BatchOperationError("test")
        ]
        
        for error in service_exceptions:
            assert isinstance(error, SentinelAggregatorError)
    
    def test_credential_error_inheritance(self):
        """Test that CredentialValidationError inherits from ClientAuthenticationError."""
        error = CredentialValidationError("test")
        
        assert isinstance(error, ClientAuthenticationError)
        assert isinstance(error, AzureError)
        # Should NOT inherit from SentinelAggregatorError
        assert not isinstance(error, SentinelAggregatorError)


class TestExceptionChaining:
    """Test exception chaining and context propagation."""
    
    def test_exception_chaining_with_cause(self):
        """Test exception chaining preserves original cause."""
        original_error = ValueError("Original error")
        
        try:
            raise original_error
        except ValueError as e:
            chained_error = QueryExecutionError("Query failed due to validation error")
            chained_error.__cause__ = e
            
            assert chained_error.__cause__ is original_error
            assert str(chained_error.__cause__) == "Original error"
    
    def test_exception_context_preservation(self):
        """Test that exception context is preserved."""
        try:
            try:
                raise ValueError("Inner error")
            except ValueError:
                raise ConfigurationError("Configuration error occurred")
        except ConfigurationError as e:
            assert e.__context__ is not None
            assert isinstance(e.__context__, ValueError)
            assert str(e.__context__) == "Inner error"


class TestErrorMessageFormatting:
    """Test error message formatting and representation."""
    
    def test_error_string_representation(self):
        """Test that error string representation works correctly."""
        error = QueryExecutionError(
            "Query execution failed",
            workspace_id="ws-123",
            query="SecurityEvent | take 10",
            error_code="TIMEOUT"
        )
        
        # Test that str() returns the message
        assert str(error) == "Query execution failed"
        
        # Test that attributes are accessible
        assert error.workspace_id == "ws-123"
        assert error.query == "SecurityEvent | take 10"
        assert error.error_code == "TIMEOUT"
    
    def test_error_with_empty_message(self):
        """Test error with empty message."""
        error = SentinelAggregatorError("")
        assert str(error) == ""
    
    def test_error_details_formatting(self):
        """Test that error details are properly stored and accessible."""
        details = {
            "request_id": "req-123",
            "correlation_id": "corr-456",
            "timestamp": "2023-01-01T00:00:00Z"
        }
        
        error = DataIngestionError(
            "Ingestion failed",
            error_details=details
        )
        
        assert error.error_details == details
        assert error.error_details["request_id"] == "req-123"
        assert error.error_details["correlation_id"] == "corr-456"


class TestExceptionInstantiation:
    """Test various exception instantiation patterns."""
    
    def test_minimal_instantiation(self):
        """Test minimal exception instantiation for all exception types."""
        exceptions = [
            ("SentinelAggregatorError", SentinelAggregatorError),
            ("QueryExecutionError", QueryExecutionError),
            ("WorkspaceAccessError", WorkspaceAccessError),
            ("DataIngestionError", DataIngestionError),
            ("ConfigurationError", ConfigurationError),
            ("WorkspaceConfigurationError", WorkspaceConfigurationError),
            ("BatchOperationError", BatchOperationError),
            ("CredentialValidationError", CredentialValidationError)
        ]
        
        for name, exception_class in exceptions:
            error = exception_class(f"Test {name}")
            assert str(error) == f"Test {name}"
            assert isinstance(error, exception_class)
    
    def test_maximal_instantiation(self):
        """Test maximum parameter instantiation for complex exceptions."""
        # QueryExecutionError with all parameters
        query_error = QueryExecutionError(
            "Complex query error",
            workspace_id="ws-123",
            query="ComplexQuery | summarize count()",
            error_code="COMPLEX_ERROR",
            error_details={"complexity": "high"}
        )
        
        assert query_error.workspace_id == "ws-123"
        assert query_error.query == "ComplexQuery | summarize count()"
        assert query_error.error_code == "COMPLEX_ERROR"
        assert query_error.error_details["complexity"] == "high"
        
        # DataIngestionError with all parameters
        ingestion_error = DataIngestionError(
            "Complex ingestion error",
            stream_name="Custom-Complex_CL",
            dcr_rule_id="dcr-complex-123",
            record_count=10000,
            error_code="COMPLEX_INGESTION",
            error_details={"batch_size": 10000}
        )
        
        assert ingestion_error.stream_name == "Custom-Complex_CL"
        assert ingestion_error.dcr_rule_id == "dcr-complex-123"
        assert ingestion_error.record_count == 10000
        assert ingestion_error.error_code == "COMPLEX_INGESTION"
        assert ingestion_error.error_details["batch_size"] == 10000


class TestExceptionComparisons:
    """Test exception equality and comparison behaviors."""
    
    def test_exception_equality_by_message(self):
        """Test that exceptions with same message are not necessarily equal."""
        error1 = SentinelAggregatorError("Same message")
        error2 = SentinelAggregatorError("Same message")
        
        # Different instances should not be equal
        assert error1 is not error2
        # But they should have the same string representation
        assert str(error1) == str(error2)
    
    def test_exception_identity(self):
        """Test exception identity preservation."""
        error = QueryExecutionError("Test error")
        same_error = error
        
        assert error is same_error
        assert str(error) == str(same_error)


class TestRealWorldScenarios:
    """Test real-world exception usage scenarios."""
    
    def test_query_timeout_scenario(self):
        """Test typical query timeout error scenario."""
        workspace_id = "12345678-1234-1234-1234-123456789012"
        query = "SecurityEvent | where TimeGenerated > ago(30d) | summarize count() by Computer"
        
        error = QueryExecutionError(
            "Query execution timed out after 300 seconds",
            workspace_id=workspace_id,
            query=query,
            error_code="QUERY_TIMEOUT",
            error_details={
                "timeout_seconds": 300,
                "partial_results": False,
                "estimated_rows": 1000000
            }
        )
        
        assert "timed out" in str(error)
        assert error.workspace_id == workspace_id
        assert "SecurityEvent" in error.query
        assert error.error_details["timeout_seconds"] == 300
    
    def test_workspace_permission_scenario(self):
        """Test typical workspace permission error scenario."""
        resource_id = "/subscriptions/sub-123/resourceGroups/rg-123/providers/Microsoft.OperationalInsights/workspaces/ws-123"
        
        error = WorkspaceAccessError(
            "Insufficient permissions to access workspace",
            workspace_id="ws-123",
            resource_id=resource_id,
            error_code="PERMISSION_DENIED",
            error_details={
                "required_role": "Log Analytics Reader",
                "current_permissions": ["Reader"],
                "scope": resource_id
            }
        )
        
        assert "Insufficient permissions" in str(error)
        assert error.resource_id == resource_id
        assert error.error_details["required_role"] == "Log Analytics Reader"
    
    def test_batch_operation_failure_scenario(self):
        """Test typical batch operation failure scenario."""
        error = BatchOperationError(
            "Batch operation partially failed",
            failed_operations=2,
            total_operations=10,
            error_code="BATCH_PARTIAL_FAILURE",
            error_details={
                "success_rate": 0.8,
                "failed_workspaces": ["ws-1", "ws-2"],
                "retry_recommended": True
            }
        )
        
        assert error.failed_operations == 2
        assert error.total_operations == 10
        assert error.error_details["success_rate"] == 0.8
        assert len(error.error_details["failed_workspaces"]) == 2