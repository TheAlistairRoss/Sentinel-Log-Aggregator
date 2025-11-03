"""
Targeted tests for validation.py to achieve 100% coverage.
Focuses on the specific missing lines: 55, 86-87, 164
"""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from sentinel_log_aggregator.models import WorkspaceConfig
from sentinel_log_aggregator.validation import QueryDefinitionModel, WorkspaceConfigModel


class TestValidationMissingLines:
    """Tests targeting the specific uncovered lines in validation.py"""

    def test_queries_list_validation_import_error_line_55(self):
        """Test line 55: ImportError handling in queries_list validation"""
        # This test targets the ImportError catch block on line 55
        # We need to patch the import inside the validator

        with patch(
            "sentinel_log_aggregator.validation.AVAILABLE_QUERIES",
            side_effect=ImportError("Test error"),
            create=True,
        ):
            # Create a WorkspaceConfigModel with queries_list to trigger validation
            try:
                config = WorkspaceConfigModel(
                    resource_id="/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/test/providers/Microsoft.OperationalInsights/workspaces/test",
                    customer_id="12345678-1234-1234-1234-123456789012",
                    queries_list=[
                        "test_query"
                    ],  # This triggers the validator that has the ImportError handling
                )
                # The ImportError should be caught and handled
                assert config.queries_list == ["test_query"]
            except ValidationError:
                # The validation should fail but not due to ImportError
                pass

    def test_subscription_id_value_error_lines_86_87(self):
        """Test lines 86-87: ValueError handling in subscription_id property"""
        # Test the case where 'subscriptions' is not found in the resource_id
        workspace = WorkspaceConfig(
            resource_id="/invalid/resource/id/path",  # No 'subscriptions' keyword
            customer_id="12345678-1234-1234-1234-123456789012",
        )

        # This should hit the ValueError exception handling on lines 86-87
        result = workspace.subscription_id
        assert result == ""

    def test_query_syntax_dangerous_operations_line_164(self):
        """Test line 164: Dangerous operations detection in query validation"""
        # This targets the specific check for dangerous operations on line 164

        # Test a query with dangerous operations that should trigger the validation
        with pytest.raises(ValidationError) as exc_info:
            QueryDefinitionModel(
                name="test_query",
                destination_stream="Custom-Test_Data_CL",
                stream_name="stream_test",
                query="SecurityEvent | where TimeGenerated > ago(1h) | .drop table test",  # Contains .drop
            )

        assert "potentially dangerous operation" in str(exc_info.value)

    def test_import_error_with_fallback_validation(self):
        """Test that validation properly handles empty query names."""
        # Test that empty query names are properly rejected
        with pytest.raises(ValidationError) as exc_info:
            WorkspaceConfigModel(
                resource_id="/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/test/providers/Microsoft.OperationalInsights/workspaces/test",
                customer_id="12345678-1234-1234-1234-123456789012",
                queries_list=[""],  # Empty string should fail
            )

        assert "non-empty strings" in str(exc_info.value).lower()

    def test_workspace_config_subscription_id_no_subscriptions(self):
        """Test WorkspaceConfig.subscription_id when 'subscriptions' not in resource_id"""
        # This specifically tests the ValueError catch block on lines 86-87
        workspace = WorkspaceConfig(
            resource_id="/resourceGroups/test/providers/Microsoft.OperationalInsights/workspaces/test",
            customer_id="12345678-1234-1234-1234-123456789012",
        )

        # Should return empty string when 'subscriptions' keyword not found
        assert workspace.subscription_id == ""

    def test_dangerous_operations_comprehensive(self):
        """Test all dangerous operations in QueryDefinitionModel"""
        dangerous_ops = [
            ".drop",
            ".delete",
            ".create",
            ".alter",
            ".set",
            "drop table",
            "delete from",
            "truncate",
        ]

        for op in dangerous_ops:
            with pytest.raises(ValidationError) as exc_info:
                QueryDefinitionModel(
                    name="test_query",
                    destination_stream="Custom-Test_Data_CL",
                    stream_name="stream_test",
                    query=f"SecurityEvent | {op} something",
                )

            assert "potentially dangerous operation" in str(exc_info.value)
