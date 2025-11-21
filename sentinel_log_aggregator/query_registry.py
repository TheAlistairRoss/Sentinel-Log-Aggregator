"""
Query registry and management system for Microsoft Sentinel Log Aggregator.

This module provides a centralized system for managing KQL queries, supporting
both YAML-based query definitions and runtime query registration.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Type

import yaml

from .models import KQLQueryDefinition, QueryParameter


@dataclass
class QueryMetadata:
    """Metadata for query registration and discovery."""

    name: str
    description: str
    stream_name: str
    destination_stream: str
    file_path: Optional[Path] = None
    version: str = "1.0"
    tags: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.tags is None:
            self.tags = []


class QueryRegistry:
    """
    Central registry for managing KQL queries.

    Supports both programmatic registration and YAML-based query definitions.
    """

    def __init__(self) -> None:
        self._queries: Dict[str, KQLQueryDefinition] = {}
        self._metadata: Dict[str, QueryMetadata] = {}
        self.logger = logging.getLogger(__name__)

    def register_query(
        self, query_class: Type[KQLQueryDefinition], metadata: Optional[QueryMetadata] = None
    ) -> None:
        """
        Register a query class with optional metadata.

        Args:
            query_class: The query class to register
            metadata: Optional metadata for the query
        """
        query_instance = query_class()
        query_name = query_instance.name

        if query_name in self._queries:
            self.logger.warning(f"Query '{query_name}' is already registered. Overwriting.")

        self._queries[query_name] = query_instance

        if metadata:
            self._metadata[query_name] = metadata
        else:
            # Auto-generate metadata from query instance
            self._metadata[query_name] = QueryMetadata(
                name=query_instance.name,
                description=query_instance.description,
                stream_name=query_instance.stream_name,
                destination_stream=query_instance.destination_stream,
            )

        self.logger.debug(f"Registered query: {query_name}")

    def load_from_yaml(self, yaml_path: Path) -> None:
        """
        Load query definition from YAML file.

        Args:
            yaml_path: Path to the YAML query definition file
        """
        if not yaml_path.exists():
            raise FileNotFoundError(f"Query file not found: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            query_data = yaml.safe_load(f)

        # Create dynamic query class from YAML
        query_instance = self._create_query_from_yaml(query_data, yaml_path)

        # Register the query
        metadata = QueryMetadata(
            name=query_data["name"],
            description=query_data.get("description", ""),
            stream_name=query_data.get("stream_name", ""),
            destination_stream=query_data.get("destination_stream", ""),
            file_path=yaml_path,
            version=query_data.get("version", "1.0"),
            tags=query_data.get("tags", []),
        )

        self._queries[query_instance.name] = query_instance
        self._metadata[query_instance.name] = metadata

        self.logger.debug(f"Loaded query from YAML: {query_instance.name}")

    def _create_query_from_yaml(self, query_data: dict, file_path: Path) -> KQLQueryDefinition:
        """Create a KQL query instance from YAML data."""

        class YamlQuery(KQLQueryDefinition):
            def __init__(self) -> None:
                super().__init__(
                    name=query_data["name"],
                    destination_stream=query_data.get("destination_stream", ""),
                    description=query_data.get("description", ""),
                    stream_name=query_data.get("stream_name", ""),
                )

                # Add parameters from YAML
                for param_name, param_config in query_data.get("parameters", {}).items():
                    self.add_parameter(
                        param_name,
                        param_config.get("type", "string"),
                        required=param_config.get("required", False),
                        default=param_config.get("default"),
                        description=param_config.get("description", ""),
                    )

                self._query_text: str = str(query_data.get("query", ""))

            def get_query(self) -> str:
                return self._query_text

        return YamlQuery()

    def load_queries_from_directory(self, directory: Path, recursive: bool = True) -> None:
        """
        Load all YAML query files from a directory.

        Args:
            directory: Directory containing YAML query files
            recursive: Whether to search subdirectories recursively
        """
        if not directory.exists():
            self.logger.warning(f"Query directory not found: {directory}")
            return

        if recursive:
            yaml_files = list(directory.rglob("*.yaml")) + list(directory.rglob("*.yml"))
        else:
            yaml_files = list(directory.glob("*.yaml")) + list(directory.glob("*.yml"))

        for yaml_file in yaml_files:
            try:
                self.load_from_yaml(yaml_file)
            except Exception as e:
                self.logger.error(f"Failed to load query from {yaml_file}: {e}")

    def load_query_from_path(
        self, query_path: str, base_directory: Optional[Path] = None
    ) -> Optional[KQLQueryDefinition]:
        """
        Load a query from a relative or absolute path.

        Args:
            query_path: Path to the query file (relative or absolute)
            base_directory: Base directory for resolving relative paths

        Returns:
            Loaded query definition or None if loading failed
        """
        try:
            # Convert to Path object
            path_obj = Path(query_path)

            # If it's not absolute and we have a base directory, make it relative to base
            if not path_obj.is_absolute() and base_directory:
                path_obj = base_directory / path_obj

            if not path_obj.exists():
                self.logger.warning(f"Query file not found: {path_obj}")
                return None

            # Load the query
            self.load_from_yaml(path_obj)

            # Return the loaded query (get the name from the loaded file)
            with open(path_obj, "r", encoding="utf-8") as f:
                query_data = yaml.safe_load(f)
            query_name = query_data.get("name")

            return self._queries.get(query_name) if query_name else None

        except Exception as e:
            self.logger.error(f"Failed to load query from path {query_path}: {e}")
            return None

    def get_query(self, name: str) -> Optional[KQLQueryDefinition]:
        """Get a query by name."""
        return self._queries.get(name)

    def list_queries(self) -> List[str]:
        """List all registered query names."""
        return list(self._queries.keys())

    def get_metadata(self, name: str) -> Optional[QueryMetadata]:
        """Get metadata for a query."""
        return self._metadata.get(name)

    def validate_all_queries(self) -> Dict[str, List[str]]:
        """
        Validate all registered queries.

        Returns:
            Dictionary mapping query names to lists of validation errors
        """
        validation_results = {}

        for name, query in self._queries.items():
            errors = []

            # Check required fields
            if not query.name:
                errors.append("Query name is required")
            if not query.destination_stream:
                errors.append("Destination stream is required")
            if not query.get_query().strip():
                errors.append("Query text is required")

            # Check parameter validation
            query_text = query.get_query()
            for param_name in query.parameters:
                placeholder = f"{{{param_name}}}"
                if placeholder not in query_text:
                    errors.append(f"Parameter '{param_name}' is defined but not used in query")

            validation_results[name] = errors

        return validation_results


# Global registry instance
query_registry = QueryRegistry()


def register_query(
    metadata: Optional[QueryMetadata] = None,
) -> Callable[[Type[KQLQueryDefinition]], Type[KQLQueryDefinition]]:
    """
    Decorator for registering query classes.

    Args:
        metadata: Optional metadata for the query
    """

    def decorator(query_class: Type[KQLQueryDefinition]) -> Type[KQLQueryDefinition]:
        query_registry.register_query(query_class, metadata)
        return query_class

    return decorator


def get_available_queries() -> Dict[str, KQLQueryDefinition]:
    """Get all available queries from the registry."""
    return {
        name: query
        for name in query_registry.list_queries()
        if (query := query_registry.get_query(name)) is not None
    }
