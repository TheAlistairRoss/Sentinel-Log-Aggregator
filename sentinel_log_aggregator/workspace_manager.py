"""
Workspace management for Microsoft Sentinel Log Aggregator.

This module provides functionality for managing multiple Sentinel workspace configurations,
including filtering by queries, extracting metadata, and providing convenient access patterns.
The WorkspaceConfig model uses a flexible parameters dictionary for workspace-specific
settings including row-level security tags, environment designations, and custom values.
"""

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Collection, Dict, List, Optional, Set, Tuple, Union

import yaml

from .logging_formatter import SentinelLogFormatter
from .models import WorkspaceConfig
from .security_utils import (
    SecureLogger,
    sanitize_log_output,
    validate_azure_resource_id,
    validate_file_path,
    validate_workspace_id,
)
from .validation import WorkspaceCollectionModel, validate_workspace_config


class WorkspaceSet:
    """
    A set of workspaces with convenient methods for data extraction and filtering.

    Provides a fluent interface for working with collections of workspace configurations.
    Supports filtering by workspace parameters including row-level security tags,
    environment settings, and custom parameter values through the parameters dictionary.
    """

    def __init__(self, workspaces: List[WorkspaceConfig]):
        """
        Initialize workspace set.

        Args:
            workspaces: List of workspace configurations
        """
        self.workspaces = workspaces

    def ids(self) -> List[str]:
        """Get list of workspace customer IDs."""
        return [ws.customer_id for ws in self.workspaces]

    def names(self) -> List[str]:
        """Get list of workspace names extracted from resource IDs."""
        return [ws.workspace_name for ws in self.workspaces]

    def aliases(self) -> List[str]:
        """Get list of row-level security tag aliases from parameters."""
        return [ws.parameters.get("row_level_security_tag", "") for ws in self.workspaces]

    def resource_ids(self) -> List[str]:
        """Get list of full Azure resource IDs."""
        return [ws.resource_id for ws in self.workspaces]

    def subscription_ids(self) -> List[str]:
        """Get list of unique subscription IDs."""
        return list(set(ws.subscription_id for ws in self.workspaces if ws.subscription_id))

    def resource_groups(self) -> List[str]:
        """Get list of unique resource group names."""
        return list(set(ws.resource_group for ws in self.workspaces if ws.resource_group))

    def details(self) -> List[Dict[str, Any]]:
        """
        Get detailed workspace information as dictionaries.

        Returns:
            List of dictionaries with workspace details
        """
        return [
            {
                "customer_id": ws.customer_id,
                "resource_id": ws.resource_id,
                "workspace_name": ws.workspace_name,
                "alias": ws.parameters.get("row_level_security_tag", ""),
                "subscription_id": ws.subscription_id,
                "resource_group": ws.resource_group,
                "queries": ws.queries_list,
                "parameters": ws.parameters,
            }
            for ws in self.workspaces
        ]

    def count(self) -> int:
        """Get count of workspaces in this set."""
        return len(self.workspaces)

    def filter_by_subscription(self, subscription_id: str) -> "WorkspaceSet":
        """
        Filter workspaces by subscription ID.

        Args:
            subscription_id: Azure subscription ID

        Returns:
            New WorkspaceSet with filtered workspaces
        """
        filtered = [ws for ws in self.workspaces if ws.subscription_id == subscription_id]
        return WorkspaceSet(filtered)

    def filter_by_resource_group(self, resource_group: str) -> "WorkspaceSet":
        """
        Filter workspaces by resource group.

        Args:
            resource_group: Azure resource group name

        Returns:
            New WorkspaceSet with filtered workspaces
        """
        filtered = [ws for ws in self.workspaces if ws.resource_group == resource_group]
        return WorkspaceSet(filtered)

    def filter_by_alias(self, alias: str) -> "WorkspaceSet":
        """
        Filter workspaces by row-level security tag alias.

        Args:
            alias: Row-level security tag

        Returns:
            New WorkspaceSet with filtered workspaces
        """
        filtered = [
            ws for ws in self.workspaces if ws.parameters.get("row_level_security_tag", "") == alias
        ]
        return WorkspaceSet(filtered)

    def filter_by_parameter(self, param_name: str, param_value: Any) -> "WorkspaceSet":
        """
        Filter workspaces by any parameter value.

        Args:
            param_name: Name of the parameter to filter by
            param_value: Value to match

        Returns:
            New WorkspaceSet with filtered workspaces
        """
        filtered = [ws for ws in self.workspaces if ws.parameters.get(param_name) == param_value]
        return WorkspaceSet(filtered)

    def has_query(self, query_name: str) -> "WorkspaceSet":
        """
        Filter workspaces that include a specific query.

        Args:
            query_name: Name of the query to filter by

        Returns:
            New WorkspaceSet with workspaces that include the query
        """
        filtered = [ws for ws in self.workspaces if query_name in ws.queries_list]
        return WorkspaceSet(filtered)

    def display(self, logger: Optional[logging.Logger] = None) -> None:
        """
        Display workspace information using logger or print.

        Args:
            logger: Optional logger instance (prints to console if None)
        """
        if logger is None:
            logger = logging.getLogger(__name__)

        for ws_detail in self.details():
            logger.info(f"-{ws_detail['workspace_name']}")
            logger.info(f"    ID: {ws_detail['customer_id']}")
            logger.info(f"    Alias: {ws_detail['alias']}")
            logger.info(f"    Subscription: {ws_detail['subscription_id']}")
            logger.info(f"    Resource Group: {ws_detail['resource_group']}")
            logger.info(f"    Queries: {', '.join(ws_detail['queries'])}")

    def to_configs(self) -> List[WorkspaceConfig]:
        """Get the underlying WorkspaceConfig objects."""
        return self.workspaces.copy()


class WorkspaceManager:
    """
    Manage workspace configurations with clean interface and validation.

    Provides high-level operations for working with multiple Sentinel workspaces,
    including filtering, validation, and query association management. Supports
    flexible parameter-based configuration where workspace-specific settings
    are stored in the parameters dictionary for maximum flexibility.
    """

    def __init__(self, workspace_configs: Optional[List[WorkspaceConfig]] = None):
        """
        Initialize workspace manager.

        Args:
            workspace_configs: List of workspace configurations
        """
        self.workspaces = workspace_configs or []
        self.logger = SecureLogger(logging.getLogger(__name__))
        self._validation_errors: List[str] = []  # Track validation errors

    def count(self) -> int:
        """Get the number of workspaces."""
        return len(self.workspaces)

    def has_validation_errors(self) -> bool:
        """Check if there were validation errors during loading."""
        return len(self._validation_errors) > 0

    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors that occurred during loading."""
        return self._validation_errors.copy()

    def add_workspace(self, workspace: WorkspaceConfig) -> "WorkspaceManager":
        """
        Add a workspace configuration.

        Args:
            workspace: Workspace configuration to add

        Returns:
            Self for method chaining
        """
        # Validate workspace configuration for security
        validate_workspace_id(workspace.customer_id)
        if workspace.resource_id:
            validate_azure_resource_id(workspace.resource_id)

        self.workspaces.append(workspace)
        return self

    def add_workspaces(self, workspaces: List[WorkspaceConfig]) -> "WorkspaceManager":
        """
        Add multiple workspace configurations.

        Args:
            workspaces: List of workspace configurations to add

        Returns:
            Self for method chaining
        """
        self.workspaces.extend(workspaces)
        return self

    def for_query(self, query_name: str) -> WorkspaceSet:
        """
        Get workspaces configured for a specific query.

        Args:
            query_name: Name of the query

        Returns:
            WorkspaceSet containing workspaces that include the query
        """
        matching = [ws for ws in self.workspaces if query_name in ws.queries_list]
        return WorkspaceSet(matching)

    def with_query(self, query_name: str) -> "WorkspaceManager":
        """
        Filter workspaces that have a specific query configured.
        Returns a new WorkspaceManager instance for method chaining.

        Args:
            query_name: Name of the query to filter by

        Returns:
            New WorkspaceManager with filtered workspaces
        """
        matching = [ws for ws in self.workspaces if query_name in ws.queries_list]
        return WorkspaceManager(matching)

    def with_workspace_ids(self, customer_ids: List[str]) -> "WorkspaceManager":
        """
        Filter workspaces by customer IDs.
        Returns a new WorkspaceManager instance for method chaining.

        Args:
            customer_ids: List of workspace customer IDs to include

        Returns:
            New WorkspaceManager with filtered workspaces
        """
        matching = [ws for ws in self.workspaces if ws.customer_id in customer_ids]
        return WorkspaceManager(matching)

    def aggregation_only(self) -> "WorkspaceManager":
        """
        Filter to only include aggregation workspaces.
        Returns a new WorkspaceManager instance for method chaining.

        Returns:
            New WorkspaceManager with only aggregation workspaces
        """
        matching = [ws for ws in self.workspaces if ws.aggregation_workspace]
        return WorkspaceManager(matching)

    def for_subscription(self, subscription_id: str) -> WorkspaceSet:
        """
        Get workspaces in a specific subscription.

        Args:
            subscription_id: Azure subscription ID

        Returns:
            WorkspaceSet containing workspaces in the subscription
        """
        return self.all().filter_by_subscription(subscription_id)

    def unique_reports(self) -> List[str]:
        """
        Get list of unique report/query names across all workspaces.

        Returns:
            List of unique report names
        """
        all_reports = set()
        for workspace in self.workspaces:
            all_reports.update(workspace.queries_list)
        return list(all_reports)

    def unique_subscriptions(self) -> List[str]:
        """
        Get list of unique subscription IDs across all workspaces.

        Returns:
            List of unique subscription IDs
        """
        return self.all().subscription_ids()

    def all(self) -> WorkspaceSet:
        """
        Get all workspaces as a WorkspaceSet.

        Returns:
            WorkspaceSet containing all workspaces
        """
        return WorkspaceSet(self.workspaces)

    def get_workspace_by_customer_id(self, customer_id: str) -> Optional[WorkspaceConfig]:
        """
        Get workspace configuration by customer ID.

        Args:
            customer_id: Log Analytics workspace customer ID

        Returns:
            WorkspaceConfig if found, None otherwise
        """
        for workspace in self.workspaces:
            if workspace.customer_id == customer_id:
                return workspace
        return None

    def get_workspace_by_resource_id(self, resource_id: str) -> Optional[WorkspaceConfig]:
        """
        Get workspace configuration by full Azure resource ID.

        Args:
            resource_id: Full Azure resource ID

        Returns:
            WorkspaceConfig if found, None otherwise
        """
        for workspace in self.workspaces:
            if workspace.resource_id == resource_id:
                return workspace
        return None

    def get_workspace_by_alias(self, alias: str) -> Optional[WorkspaceConfig]:
        """
        Get workspace configuration by row-level security tag alias.

        Args:
            alias: Row-level security tag

        Returns:
            WorkspaceConfig if found, None otherwise
        """
        for workspace in self.workspaces:
            if workspace.parameters.get("row_level_security_tag", "") == alias:
                return workspace
        return None

    def get_alias_by_customer_id(self, customer_id: str) -> str:
        """
        Get row-level security tag alias by customer ID.

        Args:
            customer_id: Log Analytics workspace customer ID

        Returns:
            Row-level security tag or empty string if not found
        """
        workspace = self.get_workspace_by_customer_id(customer_id)
        return workspace.parameters.get("row_level_security_tag", "") if workspace else ""

    def get_alias_by_resource_id(self, resource_id: str) -> str:
        """
        Get row-level security tag alias by resource ID.

        Args:
            resource_id: Full Azure resource ID

        Returns:
            Row-level security tag or empty string if not found
        """
        workspace = self.get_workspace_by_resource_id(resource_id)
        return workspace.parameters.get("row_level_security_tag", "") if workspace else ""

    def get_aggregation_workspace(self) -> Optional[WorkspaceConfig]:
        """
        Get the workspace designated for health data and aggregated logs.

        Returns:
            The workspace with aggregation_workspace=True, or None if not found

        Raises:
            ValueError: If more than one workspace is marked as aggregation workspace
        """
        aggregation_workspaces = [ws for ws in self.workspaces if ws.aggregation_workspace]

        if len(aggregation_workspaces) == 0:
            return None

        if len(aggregation_workspaces) > 1:
            workspace_names = [ws.workspace_name for ws in aggregation_workspaces]
            raise ValueError(
                f"Multiple aggregation workspaces found: {', '.join(workspace_names)}. "
                f"Only one workspace can have 'aggregation_workspace: true'."
            )

        return aggregation_workspaces[0]

    def reports_summary(self) -> Dict[str, int]:
        """
        Get summary of all reports and their workspace counts.

        Returns:
            Dictionary mapping report names to workspace counts
        """
        all_reports = set()
        for workspace in self.workspaces:
            all_reports.update(workspace.queries_list)

        report_counts = {}
        for report in all_reports:
            report_counts[report] = len(self.for_query(report).workspaces)

        return report_counts

    def validate_configuration(self) -> List[str]:
        """
        Validate workspace configuration and return list of validation errors.

        Returns:
            List of validation error messages
        """
        errors = []

        if not self.workspaces:
            errors.append("No workspaces configured")
            return errors

        seen_customer_ids = set()
        seen_resource_ids = set()
        seen_aliases = set()

        for i, workspace in enumerate(self.workspaces):
            workspace_identifier = f"Workspace {i + 1}"

            # Check required fields
            if not workspace.customer_id:
                errors.append(f"{workspace_identifier}: customer_id is required")

            if not workspace.resource_id:
                errors.append(f"{workspace_identifier}: resource_id is required")

            if not workspace.queries_list:
                errors.append(f"{workspace_identifier}: queries_list cannot be empty")

            # Check for duplicates
            if workspace.customer_id in seen_customer_ids:
                errors.append(
                    f"{workspace_identifier}: Duplicate customer_id '{workspace.customer_id}'"
                )
            seen_customer_ids.add(workspace.customer_id)

            if workspace.resource_id in seen_resource_ids:
                errors.append(
                    f"{workspace_identifier}: Duplicate resource_id '{workspace.resource_id}'"
                )
            seen_resource_ids.add(workspace.resource_id)

            # Check for duplicate security tags in parameters
            alias = workspace.parameters.get("row_level_security_tag", "")
            if alias and alias in seen_aliases:
                errors.append(f"{workspace_identifier}: Duplicate row_level_security_tag '{alias}'")
            if alias:
                seen_aliases.add(alias)

            # Validate resource ID format
            try:
                if not workspace.workspace_name:
                    errors.append(
                        f"{workspace_identifier}: Invalid resource_id format - cannot extract workspace name"
                    )
            except Exception:
                errors.append(f"{workspace_identifier}: Invalid resource_id format")

        return errors

    def get_subscription_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Get summary of workspaces grouped by subscription.

        Returns:
            Dictionary mapping subscription IDs to workspace summaries
        """
        subscription_summary: Dict[str, Dict[str, Any]] = {}

        for workspace in self.workspaces:
            sub_id = workspace.subscription_id
            if sub_id:
                if sub_id not in subscription_summary:
                    subscription_summary[sub_id] = {
                        "workspace_count": 0,
                        "workspaces": [],
                        "resource_groups": set(),
                        "reports": set(),
                    }

                subscription_summary[sub_id]["workspace_count"] += 1
                subscription_summary[sub_id]["workspaces"].append(
                    {
                        "name": workspace.workspace_name,
                        "customer_id": workspace.customer_id,
                        "alias": workspace.parameters.get("row_level_security_tag", ""),
                        "parameters": workspace.parameters,
                    }
                )
                subscription_summary[sub_id]["resource_groups"].add(workspace.resource_group)
                subscription_summary[sub_id]["reports"].update(workspace.queries_list)

        # Convert sets to lists for serialization
        for sub_data in subscription_summary.values():
            sub_data["resource_groups"] = list(sub_data["resource_groups"])
            sub_data["reports"] = list(sub_data["reports"])

        return subscription_summary

    def display_summary(self) -> None:
        """Display comprehensive workspace configuration summary."""
        errors = self.validate_configuration()
        reports = self.reports_summary()
        subscription_summary = self.get_subscription_summary()

        formatter = SentinelLogFormatter()
        msg = formatter.format_workspace_config(
            workspace_count=len(self.workspaces),
            report_count=len(reports),
            subscription_count=len(subscription_summary),
            error_count=len(errors),
        )
        self.logger.info(msg)

        if errors:
            self.logger.error(f"Configuration errors found: {len(errors)}")
            for error in errors:
                self.logger.error(f"-{error}")
            return

        # Reports summary
        self.logger.info(f"Reports configured: {len(reports)}")
        for report, count in reports.items():
            self.logger.info(f"-{report}: {count} workspace(s)")

        # Subscription summary
        self.logger.info(f"Subscriptions: {len(subscription_summary)}")
        for sub_id, sub_data in subscription_summary.items():
            self.logger.info(f"-{sub_id}: {sub_data['workspace_count']} workspace(s)")

    @classmethod
    def from_dict_list(cls, workspace_dicts: List[Dict[str, Any]]) -> "WorkspaceManager":
        """
        Create WorkspaceManager from list of dictionaries.

        Args:
            workspace_dicts: List of workspace configuration dictionaries

        Returns:
            WorkspaceManager instance
        """
        workspaces = []
        for workspace_dict in workspace_dicts:
            # Handle legacy format with row_level_security_tag as direct field
            if "row_level_security_tag" in workspace_dict and "parameters" not in workspace_dict:
                workspace_dict = workspace_dict.copy()
                row_level_security_tag = workspace_dict.pop("row_level_security_tag")
                workspace_dict["parameters"] = {"row_level_security_tag": row_level_security_tag}
            elif "row_level_security_tag" in workspace_dict and "parameters" in workspace_dict:
                # Move row_level_security_tag to parameters if both exist
                workspace_dict = workspace_dict.copy()
                row_level_security_tag = workspace_dict.pop("row_level_security_tag")
                if "parameters" not in workspace_dict:
                    workspace_dict["parameters"] = {}
                workspace_dict["parameters"]["row_level_security_tag"] = row_level_security_tag

            workspace = WorkspaceConfig(**workspace_dict)
            workspaces.append(workspace)

        return cls(workspaces)

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """
        Convert workspace configurations to list of dictionaries.

        Returns:
            List of workspace configuration dictionaries
        """
        return [asdict(workspace) for workspace in self.workspaces]

    @classmethod
    def from_file(cls, config_file: Union[str, Path]) -> "WorkspaceManager":
        """
        Create WorkspaceManager from YAML configuration file.

        Args:
            config_file: Path to workspace configuration file

        Returns:
            WorkspaceManager instance

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            ValueError: If file format is unsupported or configuration is invalid
        """
        logger = SecureLogger(logging.getLogger(__name__))

        # Convert to Path object if string
        if isinstance(config_file, str):
            config_file = Path(config_file)

        # Validate file path for security
        validate_file_path(str(config_file), [".yaml", ".yml"])

        if not config_file.exists():
            raise FileNotFoundError(f"Workspace configuration file not found: {config_file}")

        # Determine file format from extension
        file_extension = config_file.suffix.lower()

        if file_extension not in [".yaml", ".yml"]:
            raise ValueError(
                f"Unsupported configuration file format: {file_extension}. Supported formats: .yaml, .yml"
            )

        with open(config_file, "r", encoding="utf-8") as f:
            logger.debug("Loading YAML workspace configuration")
            config_data = yaml.safe_load(f)

            # For debug troubleshooting, use raw logger to show full content without sanitization
            raw_logger = logging.getLogger(__name__)

            # Log the loaded YAML content for debugging
            import yaml as yaml_module

            formatted_yaml = yaml_module.dump(
                config_data, default_flow_style=False, sort_keys=False, indent=2, width=None
            )
            raw_logger.debug(f"Loaded YAML content:\n{formatted_yaml}")

            # Handle new YAML structure with 'workspaces' key
            if isinstance(config_data, dict) and "workspaces" in config_data:
                workspace_data = config_data["workspaces"]
                # Log metadata if present
                if "metadata" in config_data:
                    metadata = config_data["metadata"]
                    logger.debug(
                        f"Configuration metadata: version={metadata.get('version', 'unknown')}"
                    )
            else:
                # Legacy format - direct list
                workspace_data = config_data

        # Validate configuration using Pydantic
        try:
            if isinstance(config_data, dict) and "workspaces" in config_data:
                validated_config = validate_workspace_config(config_data)
                workspace_data = [ws.model_dump() for ws in validated_config.workspaces]
            else:
                # Legacy format - wrap in expected structure
                wrapped_config = {"workspaces": workspace_data}
                validated_config = validate_workspace_config(wrapped_config)
                workspace_data = [ws.model_dump() for ws in validated_config.workspaces]

            logger.debug(f"Configuration validation successful: {len(workspace_data)} workspaces")

            # Create and return workspace manager with successful validation
            return cls.from_dict_list(workspace_data)

        except Exception as e:
            logger.error(f"Pydantic validation failed: {e}")
            # Fallback to basic validation but track the failure
            if not isinstance(workspace_data, list):
                raise ValueError(
                    f"Workspace configuration must be a list of workspace objects, got: {type(workspace_data)}"
                )

            # Create workspace manager with validation failure flag
            manager = cls.from_dict_list(workspace_data)
            manager._validation_errors = [str(e)]  # Track validation errors
            return manager

    def save_to_file(self, config_file: Path) -> None:
        """
        Save workspace configurations to YAML file.

        Args:
            config_file: Path where to save the configuration
        """
        config_data = {
            "workspaces": self.to_dict_list(),
            "metadata": {
                "version": "1.0",
                "description": "Microsoft Sentinel workspaces configuration for log aggregation",
                "workspace_count": len(self.workspaces),
            },
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)


def load_workspace_config(config_file: Path) -> List[WorkspaceConfig]:
    """
    Load workspace configuration from YAML file (convenience function).

    Args:
        config_file: Path to workspace configuration file

    Returns:
        List of WorkspaceConfig objects
    """
    manager = WorkspaceManager.from_file(config_file)
    return manager.workspaces
