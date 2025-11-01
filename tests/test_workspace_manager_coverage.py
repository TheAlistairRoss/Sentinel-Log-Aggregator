"""
Additional tests for workspace_manager.py to improve coverage.

This file contains tests specifically designed to cover the missing lines
and edge cases in the workspace_manager module to achieve better test coverage.
"""

import tempfile
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from sentinel_log_aggregator.exceptions import ConfigurationError
from sentinel_log_aggregator.models import WorkspaceConfig
from sentinel_log_aggregator.security_utils import SecurityError
from sentinel_log_aggregator.workspace_manager import WorkspaceManager, WorkspaceSet


class TestWorkspaceSetCoverage:
    """Additional tests for WorkspaceSet to improve coverage."""

    @pytest.fixture
    def diverse_workspaces(self):
        """Create diverse workspace configurations for testing."""
        return [
            WorkspaceConfig(
                resource_id="/subscriptions/sub1/resourcegroups/rg1/providers/microsoft.operationalinsights/workspaces/ws1",
                customer_id="11111111-1111-1111-1111-111111111111",
                parameters={
                    "row_level_security_tag": "prod",
                    "environment": "production",
                    "region": "eastus",
                },
                queries_list=["query_incident_summary", "query_workspace_usage"],
            ),
            WorkspaceConfig(
                resource_id="/subscriptions/sub1/resourcegroups/rg2/providers/microsoft.operationalinsights/workspaces/ws2",
                customer_id="22222222-2222-2222-2222-222222222222",
                parameters={
                    "row_level_security_tag": "dev",
                    "environment": "development",
                    "region": "westus",
                },
                queries_list=["query_incident_summary"],
            ),
            WorkspaceConfig(
                resource_id="/subscriptions/sub2/resourcegroups/rg1/providers/microsoft.operationalinsights/workspaces/ws3",
                customer_id="33333333-3333-3333-3333-333333333333",
                parameters={
                    "row_level_security_tag": "",
                    "environment": "test",
                },  # Empty security tag
                queries_list=["query_workspace_usage", "query_security_alerts"],
            ),
            WorkspaceConfig(
                resource_id="/subscriptions/sub2/resourcegroups/rg3/providers/microsoft.operationalinsights/workspaces/ws4",
                customer_id="44444444-4444-4444-4444-444444444444",
                parameters={},  # Empty parameters
                queries_list=[],  # No queries
            ),
        ]

    def test_subscription_ids_with_none_values(self, diverse_workspaces):
        """Test subscription_ids method with workspaces that have None subscription_id."""
        # Create workspace with missing subscription info
        workspace_no_sub = WorkspaceConfig(
            resource_id="invalid-resource-id-format",
            customer_id="55555555-5555-5555-5555-555555555555",
            parameters={"row_level_security_tag": "test"},
            queries_list=["query_test"],
        )
        workspaces = diverse_workspaces + [workspace_no_sub]
        workspace_set = WorkspaceSet(workspaces)

        subscription_ids = workspace_set.subscription_ids()
        assert "sub1" in subscription_ids
        assert "sub2" in subscription_ids
        # Should not include None values
        assert None not in subscription_ids

    def test_resource_groups_with_none_values(self, diverse_workspaces):
        """Test resource_groups method with workspaces that have None resource_group."""
        workspace_no_rg = WorkspaceConfig(
            resource_id="invalid-resource-id-format",
            customer_id="55555555-5555-5555-5555-555555555555",
            parameters={"row_level_security_tag": "test"},
            queries_list=["query_test"],
        )
        workspaces = diverse_workspaces + [workspace_no_rg]
        workspace_set = WorkspaceSet(workspaces)

        resource_groups = workspace_set.resource_groups()
        assert "rg1" in resource_groups
        assert "rg2" in resource_groups
        assert "rg3" in resource_groups
        # Should not include None values
        assert None not in resource_groups

    def test_aliases_with_empty_security_tags(self, diverse_workspaces):
        """Test aliases method with empty security tags."""
        workspace_set = WorkspaceSet(diverse_workspaces)
        aliases = workspace_set.aliases()

        # Should include empty string for workspace with no security tag
        assert "prod" in aliases
        assert "dev" in aliases
        assert "" in aliases  # Empty security tag should be included

    def test_filter_by_alias_empty_string(self, diverse_workspaces):
        """Test filtering by empty alias."""
        workspace_set = WorkspaceSet(diverse_workspaces)
        filtered = workspace_set.filter_by_alias("")

        # Should match workspaces with empty security tag or no security tag parameter
        assert (
            filtered.count() == 2
        )  # ws3 has empty string, ws4 has no parameter (defaults to empty)
        assert filtered.workspaces[0].customer_id == "33333333-3333-3333-3333-333333333333"

    def test_filter_by_parameter_missing_parameter(self, diverse_workspaces):
        """Test filtering by parameter that doesn't exist in some workspaces."""
        workspace_set = WorkspaceSet(diverse_workspaces)
        filtered = workspace_set.filter_by_parameter("region", "eastus")

        assert filtered.count() == 1
        assert filtered.workspaces[0].customer_id == "11111111-1111-1111-1111-111111111111"

    def test_filter_by_parameter_none_value(self, diverse_workspaces):
        """Test filtering by parameter with None value."""
        workspace_set = WorkspaceSet(diverse_workspaces)
        filtered = workspace_set.filter_by_parameter("nonexistent", None)

        # Should return workspaces where the parameter doesn't exist or is None
        assert (
            filtered.count() == 4
        )  # All workspaces don't have "nonexistent" parameter    def test_has_query_empty_queries_list(self, diverse_workspaces):
        """Test has_query with workspace that has empty queries list."""
        workspace_set = WorkspaceSet(diverse_workspaces)
        filtered = workspace_set.has_query("query_incident_summary")

        assert filtered.count() == 2  # Only two workspaces have this query

    def test_display_with_logger(self, diverse_workspaces, caplog):
        """Test display method with provided logger."""
        import logging

        # Set caplog to capture at INFO level
        caplog.set_level(logging.INFO)

        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.INFO)

        workspace_set = WorkspaceSet([diverse_workspaces[0]])  # Use just one workspace
        workspace_set.display(logger)

        # Check that info messages were logged - should contain workspace name "ws1"
        assert any(
            "ws1" in record.message for record in caplog.records
        ), f"Expected 'ws1' in logs, got: {[r.message for r in caplog.records]}"

    def test_display_without_logger(self, diverse_workspaces, caplog):
        """Test display method without logger (should use default)."""
        import logging

        # Set caplog to capture at INFO level and ensure the module logger is captured
        caplog.set_level(logging.INFO, logger="sentinel_log_aggregator.workspace_manager")

        workspace_set = WorkspaceSet([diverse_workspaces[0]])
        workspace_set.display()

        # Should use default logger and contain workspace name "ws1"
        assert any(
            "ws1" in record.message for record in caplog.records
        ), f"Expected 'ws1' in logs, got: {[r.message for r in caplog.records]}"

    def test_to_configs_returns_copy(self, diverse_workspaces):
        """Test that to_configs returns a copy, not the original list."""
        workspace_set = WorkspaceSet(diverse_workspaces)
        configs = workspace_set.to_configs()

        # Modify the returned list
        configs.append(
            WorkspaceConfig(resource_id="/test", customer_id="test", parameters={}, queries_list=[])
        )

        # Original workspace_set should be unchanged
        assert len(workspace_set.workspaces) == 4
        assert len(configs) == 5


class TestWorkspaceManagerCoverage:
    """Additional tests for WorkspaceManager to improve coverage."""

    @pytest.fixture
    def complex_workspaces(self):
        """Create complex workspace configurations for testing."""
        return [
            WorkspaceConfig(
                resource_id="/subscriptions/sub1/resourcegroups/rg1/providers/microsoft.operationalinsights/workspaces/prod-ws",
                customer_id="11111111-1111-1111-1111-111111111111",
                parameters={"row_level_security_tag": "PROD", "environment": "production"},
                queries_list=["query_incident_summary", "query_workspace_usage"],
            ),
            WorkspaceConfig(
                resource_id="/subscriptions/sub1/resourcegroups/rg2/providers/microsoft.operationalinsights/workspaces/dev-ws",
                customer_id="22222222-2222-2222-2222-222222222222",
                parameters={"row_level_security_tag": "DEV", "environment": "development"},
                queries_list=["query_incident_summary", "query_security_alerts"],
            ),
            WorkspaceConfig(
                resource_id="/subscriptions/sub2/resourcegroups/rg1/providers/microsoft.operationalinsights/workspaces/test-ws",
                customer_id="33333333-3333-3333-3333-333333333333",
                parameters={"row_level_security_tag": "TEST"},
                queries_list=["query_workspace_usage"],
            ),
        ]

    def test_get_workspace_by_customer_id_found(self, complex_workspaces):
        """Test getting workspace by customer ID when it exists."""
        manager = WorkspaceManager(complex_workspaces)
        workspace = manager.get_workspace_by_customer_id("22222222-2222-2222-2222-222222222222")

        assert workspace is not None
        assert workspace.parameters["row_level_security_tag"] == "DEV"

    def test_get_workspace_by_customer_id_not_found(self, complex_workspaces):
        """Test getting workspace by customer ID when it doesn't exist."""
        manager = WorkspaceManager(complex_workspaces)
        workspace = manager.get_workspace_by_customer_id("99999999-9999-9999-9999-999999999999")

        assert workspace is None

    def test_get_workspace_by_resource_id_found(self, complex_workspaces):
        """Test getting workspace by resource ID when it exists."""
        manager = WorkspaceManager(complex_workspaces)
        resource_id = "/subscriptions/sub1/resourcegroups/rg1/providers/microsoft.operationalinsights/workspaces/prod-ws"
        workspace = manager.get_workspace_by_resource_id(resource_id)

        assert workspace is not None
        assert workspace.parameters["row_level_security_tag"] == "PROD"

    def test_get_workspace_by_resource_id_not_found(self, complex_workspaces):
        """Test getting workspace by resource ID when it doesn't exist."""
        manager = WorkspaceManager(complex_workspaces)
        workspace = manager.get_workspace_by_resource_id("/nonexistent/resource/id")

        assert workspace is None

    def test_get_workspace_by_alias_found(self, complex_workspaces):
        """Test getting workspace by alias when it exists."""
        manager = WorkspaceManager(complex_workspaces)
        workspace = manager.get_workspace_by_alias("TEST")

        assert workspace is not None
        assert workspace.customer_id == "33333333-3333-3333-3333-333333333333"

    def test_get_workspace_by_alias_not_found(self, complex_workspaces):
        """Test getting workspace by alias when it doesn't exist."""
        manager = WorkspaceManager(complex_workspaces)
        workspace = manager.get_workspace_by_alias("NONEXISTENT")

        assert workspace is None

    def test_get_alias_by_customer_id_found(self, complex_workspaces):
        """Test getting alias by customer ID when workspace exists."""
        manager = WorkspaceManager(complex_workspaces)
        alias = manager.get_alias_by_customer_id("11111111-1111-1111-1111-111111111111")

        assert alias == "PROD"

    def test_get_alias_by_customer_id_not_found(self, complex_workspaces):
        """Test getting alias by customer ID when workspace doesn't exist."""
        manager = WorkspaceManager(complex_workspaces)
        alias = manager.get_alias_by_customer_id("99999999-9999-9999-9999-999999999999")

        assert alias == ""

    def test_get_alias_by_resource_id_found(self, complex_workspaces):
        """Test getting alias by resource ID when workspace exists."""
        manager = WorkspaceManager(complex_workspaces)
        resource_id = "/subscriptions/sub2/resourcegroups/rg1/providers/microsoft.operationalinsights/workspaces/test-ws"
        alias = manager.get_alias_by_resource_id(resource_id)

        assert alias == "TEST"

    def test_get_alias_by_resource_id_not_found(self, complex_workspaces):
        """Test getting alias by resource ID when workspace doesn't exist."""
        manager = WorkspaceManager(complex_workspaces)
        alias = manager.get_alias_by_resource_id("/nonexistent/resource/id")

        assert alias == ""

    def test_reports_summary(self, complex_workspaces):
        """Test reports summary generation."""
        manager = WorkspaceManager(complex_workspaces)
        summary = manager.reports_summary()

        assert "query_incident_summary" in summary
        assert summary["query_incident_summary"] == 2  # Two workspaces have this query
        assert "query_workspace_usage" in summary
        assert summary["query_workspace_usage"] == 2  # Two workspaces have this query
        assert "query_security_alerts" in summary
        assert summary["query_security_alerts"] == 1  # One workspace has this query

    def test_get_subscription_summary(self, complex_workspaces):
        """Test subscription summary generation."""
        manager = WorkspaceManager(complex_workspaces)
        summary = manager.get_subscription_summary()

        assert "sub1" in summary
        assert summary["sub1"]["workspace_count"] == 2
        assert len(summary["sub1"]["workspaces"]) == 2
        assert "rg1" in summary["sub1"]["resource_groups"]
        assert "rg2" in summary["sub1"]["resource_groups"]

        assert "sub2" in summary
        assert summary["sub2"]["workspace_count"] == 1
        assert len(summary["sub2"]["workspaces"]) == 1

    def test_validate_configuration_no_workspaces(self):
        """Test validation with no workspaces configured."""
        manager = WorkspaceManager()
        errors = manager.validate_configuration()

        assert len(errors) == 1
        assert "No workspaces configured" in errors[0]

    def test_validate_configuration_missing_fields(self):
        """Test validation with workspaces missing required fields."""
        invalid_workspace = WorkspaceConfig(
            resource_id="",  # Empty resource ID
            customer_id="",  # Empty customer ID
            parameters={},
            queries_list=[],  # Empty queries list
        )

        manager = WorkspaceManager([invalid_workspace])
        errors = manager.validate_configuration()

        assert len(errors) >= 3  # Should have multiple errors
        assert any("customer_id is required" in error for error in errors)
        assert any("resource_id is required" in error for error in errors)
        assert any("queries_list cannot be empty" in error for error in errors)

    def test_validate_configuration_duplicates(self, complex_workspaces):
        """Test validation with duplicate customer IDs and resource IDs."""
        # Create duplicate workspace
        duplicate_workspace = WorkspaceConfig(
            resource_id=complex_workspaces[0].resource_id,  # Same resource ID
            customer_id=complex_workspaces[0].customer_id,  # Same customer ID
            parameters={"row_level_security_tag": "PROD"},  # Same security tag
            queries_list=["query_test"],
        )

        workspaces = complex_workspaces + [duplicate_workspace]
        manager = WorkspaceManager(workspaces)
        errors = manager.validate_configuration()

        assert any("Duplicate customer_id" in error for error in errors)
        assert any("Duplicate resource_id" in error for error in errors)
        assert any("Duplicate row_level_security_tag" in error for error in errors)

    def test_validate_configuration_invalid_resource_id_format(self):
        """Test validation with invalid resource ID format."""
        invalid_workspace = WorkspaceConfig(
            resource_id="",  # Empty resource ID format
            customer_id="11111111-1111-1111-1111-111111111111",
            parameters={},
            queries_list=["query_test"],
        )

        manager = WorkspaceManager([invalid_workspace])
        errors = manager.validate_configuration()

        # Check for resource ID validation error - should mention workspace name extraction failure
        assert any(
            "cannot extract workspace name" in error for error in errors
        ), f"Expected workspace name extraction error, got: {errors}"

    def test_display_summary_with_errors(self, caplog):
        """Test display_summary when configuration has errors."""
        invalid_workspace = WorkspaceConfig(
            resource_id="", customer_id="", parameters={}, queries_list=[]
        )

        manager = WorkspaceManager([invalid_workspace])
        manager.display_summary()

        # Should log errors and return early
        assert any("Configuration errors found" in record.message for record in caplog.records)

    def test_display_summary_valid_configuration(self, complex_workspaces, caplog):
        """Test display_summary with valid configuration."""
        import logging

        # Set caplog to capture at INFO level for the workspace_manager module
        caplog.set_level(logging.INFO, logger="sentinel_log_aggregator.workspace_manager")

        manager = WorkspaceManager(complex_workspaces)
        manager.display_summary()

        # Should log workspace summary information - check for "Reports configured" message
        assert any(
            "Reports configured" in record.message for record in caplog.records
        ), f"Expected 'Reports configured' in logs, got: {[r.message for r in caplog.records]}"
        assert any("Subscriptions" in record.message for record in caplog.records)

    def test_from_dict_list_legacy_format_conversion(self):
        """Test from_dict_list with legacy format (row_level_security_tag as direct field)."""
        workspace_dicts = [
            {
                "resource_id": "/subscriptions/test/resourcegroups/test/providers/microsoft.operationalinsights/workspaces/test",
                "customer_id": "11111111-1111-1111-1111-111111111111",
                "row_level_security_tag": "LEGACY",  # Legacy format
                "queries_list": ["query_test"],
            }
        ]

        manager = WorkspaceManager.from_dict_list(workspace_dicts)
        workspace = manager.workspaces[0]

        # Should convert to parameters format
        assert "row_level_security_tag" not in workspace.__dict__
        assert workspace.parameters["row_level_security_tag"] == "LEGACY"

    def test_from_dict_list_both_formats(self):
        """Test from_dict_list when both legacy and new formats are present."""
        workspace_dicts = [
            {
                "resource_id": "/subscriptions/test/resourcegroups/test/providers/microsoft.operationalinsights/workspaces/test",
                "customer_id": "11111111-1111-1111-1111-111111111111",
                "row_level_security_tag": "LEGACY",  # Legacy format
                "parameters": {"environment": "test"},  # New format also present
                "queries_list": ["query_test"],
            }
        ]

        manager = WorkspaceManager.from_dict_list(workspace_dicts)
        workspace = manager.workspaces[0]

        # Should move legacy field to parameters
        assert workspace.parameters["row_level_security_tag"] == "LEGACY"
        assert workspace.parameters["environment"] == "test"

    def test_save_to_file(self, complex_workspaces, tmp_path):
        """Test saving workspace configuration to file."""
        manager = WorkspaceManager(complex_workspaces)
        output_file = tmp_path / "saved_workspaces.yaml"

        manager.save_to_file(output_file)

        assert output_file.exists()

        # Verify file contents
        with open(output_file, "r") as f:
            saved_data = yaml.safe_load(f)

        assert "workspaces" in saved_data
        assert "metadata" in saved_data
        assert saved_data["metadata"]["workspace_count"] == 3
        assert len(saved_data["workspaces"]) == 3


class TestWorkspaceManagerFileOperationsCoverage:
    """Test file operations and edge cases for WorkspaceManager."""

    def test_from_file_with_metadata(self, tmp_path):
        """Test loading file with metadata section."""
        yaml_content = {
            "metadata": {"version": "2.0", "description": "Test configuration"},
            "workspaces": [
                {
                    "resource_id": "/subscriptions/test/resourcegroups/test/providers/microsoft.operationalinsights/workspaces/test",
                    "customer_id": "11111111-1111-1111-1111-111111111111",
                    "parameters": {"row_level_security_tag": "test"},
                    "queries_list": ["query_test"],
                }
            ],
        }

        yaml_file = tmp_path / "test_with_metadata.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)

        with patch("sentinel_log_aggregator.workspace_manager.SecureLogger") as mock_logger_class:
            mock_logger = MagicMock()
            mock_logger_class.return_value = mock_logger

            manager = WorkspaceManager.from_file(yaml_file)

            # Should log metadata information
            mock_logger.debug.assert_any_call("📊 Configuration metadata: version=2.0")

    def test_from_file_validation_fallback(self, tmp_path):
        """Test loading file when Pydantic validation fails but basic validation passes."""
        yaml_content = [
            {
                "resource_id": "/subscriptions/test/resourcegroups/test/providers/microsoft.operationalinsights/workspaces/test",
                "customer_id": "11111111-1111-1111-1111-111111111111",
                "parameters": {"row_level_security_tag": "test"},
                "queries_list": ["query_test"],
            }
        ]

        yaml_file = tmp_path / "test_validation_fallback.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)

        # Mock validate_workspace_config to raise an exception
        with patch(
            "sentinel_log_aggregator.workspace_manager.validate_workspace_config"
        ) as mock_validate:
            mock_validate.side_effect = Exception("Pydantic validation failed")

            with patch(
                "sentinel_log_aggregator.workspace_manager.SecureLogger"
            ) as mock_logger_class:
                mock_logger = MagicMock()
                mock_logger_class.return_value = mock_logger

                manager = WorkspaceManager.from_file(yaml_file)

                # Should log warning about validation fallback
                mock_logger.warning.assert_called_once()
                assert "Pydantic validation failed" in str(mock_logger.warning.call_args)

                # Should still create manager
                assert manager.count() == 1

    def test_from_file_invalid_workspace_data_type(self, tmp_path):
        """Test loading file with invalid workspace data type."""
        yaml_content = {"workspaces": "not a list"}  # Should be a list

        yaml_file = tmp_path / "invalid_data_type.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)

        with pytest.raises(ValueError, match="Workspace configuration must be a list"):
            WorkspaceManager.from_file(yaml_file)

    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_from_file_permission_error(self, mock_open, mock_exists):
        """Test handling of permission errors when reading files."""
        with pytest.raises(PermissionError):
            WorkspaceManager.from_file(Path("test.yaml"))

    def test_load_workspace_config_convenience_function(self, tmp_path):
        """Test the convenience function load_workspace_config."""
        from sentinel_log_aggregator.workspace_manager import load_workspace_config

        yaml_content = [
            {
                "resource_id": "/subscriptions/test/resourcegroups/test/providers/microsoft.operationalinsights/workspaces/test",
                "customer_id": "11111111-1111-1111-1111-111111111111",
                "parameters": {"row_level_security_tag": "test"},
                "queries_list": ["query_test"],
            }
        ]

        yaml_file = tmp_path / "convenience_test.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)

        workspaces = load_workspace_config(yaml_file)

        assert len(workspaces) == 1
        assert isinstance(workspaces[0], WorkspaceConfig)
        assert workspaces[0].parameters["row_level_security_tag"] == "test"


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling scenarios."""

    def test_workspace_with_no_subscription_id(self):
        """Test workspace that cannot extract subscription ID."""
        workspace = WorkspaceConfig(
            resource_id="malformed-resource-id",
            customer_id="11111111-1111-1111-1111-111111111111",
            parameters={},
            queries_list=["query_test"],
        )

        # Should handle gracefully without crashing
        workspace_set = WorkspaceSet([workspace])
        subscription_ids = workspace_set.subscription_ids()
        assert len(subscription_ids) == 0

    def test_workspace_with_no_resource_group(self):
        """Test workspace that cannot extract resource group."""
        workspace = WorkspaceConfig(
            resource_id="malformed-resource-id",
            customer_id="11111111-1111-1111-1111-111111111111",
            parameters={},
            queries_list=["query_test"],
        )

        # Should handle gracefully without crashing
        workspace_set = WorkspaceSet([workspace])
        resource_groups = workspace_set.resource_groups()
        assert len(resource_groups) == 0

    def test_empty_workspace_set_operations(self):
        """Test all operations on empty WorkspaceSet."""
        empty_set = WorkspaceSet([])

        assert empty_set.count() == 0
        assert empty_set.ids() == []
        assert empty_set.names() == []
        assert empty_set.aliases() == []
        assert empty_set.resource_ids() == []
        assert empty_set.subscription_ids() == []
        assert empty_set.resource_groups() == []
        assert empty_set.details() == []

        # Filter operations should return empty sets
        assert empty_set.filter_by_subscription("test").count() == 0
        assert empty_set.filter_by_resource_group("test").count() == 0
        assert empty_set.filter_by_alias("test").count() == 0
        assert empty_set.filter_by_parameter("test", "value").count() == 0
        assert empty_set.has_query("test").count() == 0

    def test_workspace_manager_empty_operations(self):
        """Test WorkspaceManager operations with empty workspace list."""
        manager = WorkspaceManager()

        assert manager.unique_reports() == []
        assert manager.unique_subscriptions() == []
        assert manager.reports_summary() == {}
        assert manager.get_subscription_summary() == {}

        # Lookup operations should return None or empty string
        assert manager.get_workspace_by_customer_id("test") is None
        assert manager.get_workspace_by_resource_id("test") is None
        assert manager.get_workspace_by_alias("test") is None
        assert manager.get_alias_by_customer_id("test") == ""
        assert manager.get_alias_by_resource_id("test") == ""
