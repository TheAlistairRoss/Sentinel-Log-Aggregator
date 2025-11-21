"""
Tests for query registry and management system.

Provides comprehensive testing for query registration, YAML-based query loading,
query metadata management, validation, and discovery functionality.
"""

import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml

from sentinel_log_aggregator.models import KQLQueryDefinition, QueryParameter
from sentinel_log_aggregator.query_registry import (
    QueryMetadata,
    QueryRegistry,
    get_available_queries,
    query_registry,
    register_query,
)


class TestQueryMetadata:
    """Test QueryMetadata dataclass functionality."""

    def test_query_metadata_basic_creation(self):
        """Test basic QueryMetadata creation."""
        metadata = QueryMetadata(
            name="test_query",
            description="Test query description",
            stream_name="test_stream",
            destination_stream="Custom-Test_CL",
        )

        assert metadata.name == "test_query"
        assert metadata.description == "Test query description"
        assert metadata.stream_name == "test_stream"
        assert metadata.destination_stream == "Custom-Test_CL"
        assert metadata.version == "1.0"
        assert metadata.tags == []
        assert metadata.file_path is None

    def test_query_metadata_with_optional_fields(self):
        """Test QueryMetadata creation with optional fields."""
        file_path = Path("/test/path/query.yaml")
        metadata = QueryMetadata(
            name="test_query",
            description="Test query description",
            stream_name="test_stream",
            destination_stream="Custom-Test_CL",
            file_path=file_path,
            version="2.0",
            tags=["test", "security"],
        )

        assert metadata.file_path == file_path
        assert metadata.version == "2.0"
        assert metadata.tags == ["test", "security"]

    def test_query_metadata_tags_default_initialization(self):
        """Test that tags are properly initialized as empty list."""
        metadata = QueryMetadata(
            name="test_query",
            description="Test query description",
            stream_name="test_stream",
            destination_stream="Custom-Test_CL",
            tags=None,
        )

        assert metadata.tags == []


class TestQueryRegistry:
    """Test QueryRegistry functionality."""

    @pytest.fixture
    def registry(self):
        """Create a fresh QueryRegistry instance for testing."""
        return QueryRegistry()

    @pytest.fixture
    def sample_query_class(self):
        """Create a sample query class for testing."""

        class SampleQuery(KQLQueryDefinition):
            def __init__(self):
                super().__init__(
                    name="sample_query",
                    destination_stream="Custom-Sample_CL",
                    description="Sample test query",
                    stream_name="sample_stream",
                )
                self.add_parameter("param1", "string", required=True)
                self.add_parameter("param2", "int", default=10)

            def get_query(self) -> str:
                return "print 'Hello {param1}', {param2}"

        return SampleQuery

    def test_registry_initialization(self, registry):
        """Test QueryRegistry initialization."""
        assert len(registry._queries) == 0
        assert len(registry._metadata) == 0
        assert registry.logger is not None

    def test_register_query_basic(self, registry, sample_query_class):
        """Test basic query registration."""
        registry.register_query(sample_query_class)

        assert "sample_query" in registry._queries
        assert "sample_query" in registry._metadata

        query = registry.get_query("sample_query")
        assert query is not None
        assert query.name == "sample_query"
        assert query.destination_stream == "Custom-Sample_CL"

    def test_register_query_with_metadata(self, registry, sample_query_class):
        """Test query registration with custom metadata."""
        metadata = QueryMetadata(
            name="sample_query",
            description="Custom description",
            stream_name="custom_stream",
            destination_stream="Custom-Sample_CL",
            tags=["test", "sample"],
        )

        registry.register_query(sample_query_class, metadata)

        stored_metadata = registry.get_metadata("sample_query")
        assert stored_metadata.description == "Custom description"
        assert stored_metadata.tags == ["test", "sample"]

    def test_register_query_overwrite_warning(self, registry, sample_query_class):
        """Test warning when overwriting existing query."""
        with patch.object(registry.logger, "warning") as mock_warning:
            registry.register_query(sample_query_class)
            registry.register_query(sample_query_class)  # Register again

            mock_warning.assert_called_with(
                "Query 'sample_query' is already registered. Overwriting."
            )

    def test_list_queries(self, registry, sample_query_class):
        """Test listing all registered queries."""
        assert registry.list_queries() == []

        registry.register_query(sample_query_class)
        query_names = registry.list_queries()

        assert len(query_names) == 1
        assert "sample_query" in query_names

    def test_get_nonexistent_query(self, registry):
        """Test getting a nonexistent query returns None."""
        query = registry.get_query("nonexistent")
        assert query is None

        metadata = registry.get_metadata("nonexistent")
        assert metadata is None


class TestYAMLQueryLoading:
    """Test YAML-based query loading functionality."""

    @pytest.fixture
    def registry(self):
        """Create a fresh QueryRegistry instance for testing."""
        return QueryRegistry()

    @pytest.fixture
    def sample_yaml_content(self):
        """Create sample YAML query content."""
        return {
            "name": "yaml_test_query",
            "description": "Test query loaded from YAML",
            "stream_name": "yaml_stream",
            "destination_stream": "Custom-YamlTest_CL",
            "version": "1.5",
            "tags": ["yaml", "test"],
            "parameters": {
                "workspace_id": {
                    "type": "string",
                    "required": True,
                    "description": "Workspace ID parameter",
                },
                "days_back": {"type": "int", "default": 30, "description": "Days to look back"},
            },
            "query": "SecurityEvent | where TimeGenerated > ago({days_back}d) | where Computer contains '{workspace_id}'",
        }

    def test_load_from_yaml_success(self, registry, sample_yaml_content):
        """Test successful YAML query loading."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(sample_yaml_content, f)
            yaml_path = Path(f.name)

        try:
            registry.load_from_yaml(yaml_path)

            # Check query was loaded
            assert "yaml_test_query" in registry._queries
            query = registry.get_query("yaml_test_query")
            assert query.name == "yaml_test_query"
            assert query.description == "Test query loaded from YAML"
            assert query.destination_stream == "Custom-YamlTest_CL"

            # Check metadata
            metadata = registry.get_metadata("yaml_test_query")
            assert metadata.version == "1.5"
            assert metadata.tags == ["yaml", "test"]
            assert metadata.file_path == yaml_path

            # Check parameters
            assert "workspace_id" in query.parameters
            assert "days_back" in query.parameters
            assert query.parameters["workspace_id"].required == True
            assert query.parameters["days_back"].default == 30

            # Check query text
            expected_query = "SecurityEvent | where TimeGenerated > ago({days_back}d) | where Computer contains '{workspace_id}'"
            assert query.get_query() == expected_query

        finally:
            yaml_path.unlink()

    def test_load_from_yaml_file_not_found(self, registry):
        """Test error handling when YAML file doesn't exist."""
        nonexistent_path = Path("/nonexistent/query.yaml")

        with pytest.raises(FileNotFoundError, match="Query file not found"):
            registry.load_from_yaml(nonexistent_path)

    def test_load_from_yaml_minimal_content(self, registry):
        """Test loading YAML with minimal required content."""
        minimal_content = {"name": "minimal_query", "query": "print 'minimal'"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(minimal_content, f)
            yaml_path = Path(f.name)

        try:
            registry.load_from_yaml(yaml_path)

            query = registry.get_query("minimal_query")
            assert query.name == "minimal_query"
            assert query.get_query() == "print 'minimal'"

            # Check defaults
            metadata = registry.get_metadata("minimal_query")
            assert metadata.description == ""
            assert metadata.version == "1.0"
            assert metadata.tags == []

        finally:
            yaml_path.unlink()

    def test_load_queries_from_directory(self, registry):
        """Test loading multiple queries from a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create multiple YAML files
            query1 = {"name": "query1", "query": "print 'query1'"}
            query2 = {"name": "query2", "query": "print 'query2'"}

            (temp_path / "query1.yaml").write_text(yaml.dump(query1))
            (temp_path / "query2.yml").write_text(yaml.dump(query2))
            (temp_path / "not_yaml.txt").write_text("not a yaml file")

            registry.load_queries_from_directory(temp_path)

            # Check both queries were loaded
            assert "query1" in registry.list_queries()
            assert "query2" in registry.list_queries()
            assert len(registry.list_queries()) == 2

    def test_load_queries_from_nonexistent_directory(self, registry):
        """Test handling of nonexistent directory."""
        nonexistent_dir = Path("/nonexistent/directory")

        with patch.object(registry.logger, "warning") as mock_warning:
            registry.load_queries_from_directory(nonexistent_dir)
            mock_warning.assert_called_with(f"Query directory not found: {nonexistent_dir}")

    def test_load_queries_directory_with_invalid_yaml(self, registry):
        """Test handling of invalid YAML files in directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create valid and invalid YAML files
            valid_query = {"name": "valid_query", "query": "print 'valid'"}
            (temp_path / "valid.yaml").write_text(yaml.dump(valid_query))
            (temp_path / "invalid.yaml").write_text("invalid: yaml: content: [")

            with patch.object(registry.logger, "error") as mock_error:
                registry.load_queries_from_directory(temp_path)

                # Valid query should be loaded
                assert "valid_query" in registry.list_queries()

                # Error should be logged for invalid file
                assert mock_error.called


class TestQueryValidation:
    """Test query validation functionality."""

    @pytest.fixture
    def registry(self):
        """Create a fresh QueryRegistry instance for testing."""
        return QueryRegistry()

    def test_validate_all_queries_success(self, registry):
        """Test validation of valid queries."""

        class ValidQuery(KQLQueryDefinition):
            def __init__(self):
                super().__init__(
                    name="valid_query",
                    destination_stream="Custom-Valid_CL",
                    description="Valid test query",
                    stream_name="valid_stream",
                )
                self.add_parameter("param1", "string")

            def get_query(self) -> str:
                return "print 'Hello {param1}'"

        registry.register_query(ValidQuery)
        validation_results = registry.validate_all_queries()

        assert "valid_query" in validation_results
        assert validation_results["valid_query"] == []  # No errors

    def test_validate_query_missing_name(self, registry):
        """Test validation of query with missing name."""

        class InvalidQuery(KQLQueryDefinition):
            def __init__(self):
                super().__init__(
                    name="",  # Empty name
                    destination_stream="Custom-Invalid_CL",
                    description="Invalid test query",
                    stream_name="invalid_stream",
                )

            def get_query(self) -> str:
                return "print 'test'"

        registry.register_query(InvalidQuery)
        validation_results = registry.validate_all_queries()

        errors = validation_results[""]
        assert "Query name is required" in errors

    def test_validate_query_missing_destination_stream(self, registry):
        """Test validation of query with missing destination stream."""

        class InvalidQuery(KQLQueryDefinition):
            def __init__(self):
                super().__init__(
                    name="invalid_query",
                    destination_stream="",  # Empty destination stream
                    description="Invalid test query",
                    stream_name="invalid_stream",
                )

            def get_query(self) -> str:
                return "print 'test'"

        registry.register_query(InvalidQuery)
        validation_results = registry.validate_all_queries()

        errors = validation_results["invalid_query"]
        assert "Destination stream is required" in errors

    def test_validate_query_empty_query_text(self, registry):
        """Test validation of query with empty query text."""

        class InvalidQuery(KQLQueryDefinition):
            def __init__(self):
                super().__init__(
                    name="invalid_query",
                    destination_stream="Custom-Invalid_CL",
                    description="Invalid test query",
                    stream_name="invalid_stream",
                )

            def get_query(self) -> str:
                return "   "  # Whitespace only

        registry.register_query(InvalidQuery)
        validation_results = registry.validate_all_queries()

        errors = validation_results["invalid_query"]
        assert "Query text is required" in errors

    def test_validate_query_unused_parameter(self, registry):
        """Test validation of query with unused parameter."""

        class InvalidQuery(KQLQueryDefinition):
            def __init__(self):
                super().__init__(
                    name="invalid_query",
                    destination_stream="Custom-Invalid_CL",
                    description="Invalid test query",
                    stream_name="invalid_stream",
                )
                self.add_parameter("unused_param", "string")

            def get_query(self) -> str:
                return "print 'test'"  # No {unused_param} placeholder

        registry.register_query(InvalidQuery)
        validation_results = registry.validate_all_queries()

        errors = validation_results["invalid_query"]
        assert "Parameter 'unused_param' is defined but not used in query" in errors


class TestQueryRegistryDecorator:
    """Test the register_query decorator functionality."""

    def test_register_query_decorator_basic(self):
        """Test basic decorator functionality."""
        # Clear registry for clean test
        query_registry._queries.clear()
        query_registry._metadata.clear()

        @register_query()
        class DecoratedQuery(KQLQueryDefinition):
            def __init__(self):
                super().__init__(
                    name="decorated_query",
                    destination_stream="Custom-Decorated_CL",
                    description="Decorated test query",
                    stream_name="decorated_stream",
                )

            def get_query(self) -> str:
                return "print 'decorated'"

        # Check query was registered
        assert "decorated_query" in query_registry._queries
        query = query_registry.get_query("decorated_query")
        assert query.name == "decorated_query"

    def test_register_query_decorator_with_metadata(self):
        """Test decorator with custom metadata."""
        # Clear registry for clean test
        query_registry._queries.clear()
        query_registry._metadata.clear()

        metadata = QueryMetadata(
            name="decorated_query_meta",
            description="Decorated query with metadata",
            stream_name="decorated_stream",
            destination_stream="Custom-DecoratedMeta_CL",
            tags=["decorated", "metadata"],
        )

        @register_query(metadata)
        class DecoratedQueryWithMeta(KQLQueryDefinition):
            def __init__(self):
                super().__init__(
                    name="decorated_query_meta",
                    destination_stream="Custom-DecoratedMeta_CL",
                    description="Decorated query with metadata",
                    stream_name="decorated_stream",
                )

            def get_query(self) -> str:
                return "print 'decorated with metadata'"

        # Check metadata was applied
        stored_metadata = query_registry.get_metadata("decorated_query_meta")
        assert stored_metadata.tags == ["decorated", "metadata"]


class TestGlobalFunctions:
    """Test global registry functions."""

    def test_get_available_queries(self):
        """Test get_available_queries function."""
        # Clear registry for clean test
        query_registry._queries.clear()
        query_registry._metadata.clear()

        class TestQuery(KQLQueryDefinition):
            def __init__(self):
                super().__init__(
                    name="test_global_query",
                    destination_stream="Custom-TestGlobal_CL",
                    description="Test global query",
                    stream_name="test_global_stream",
                )

            def get_query(self) -> str:
                return "print 'global test'"

        query_registry.register_query(TestQuery)

        available_queries = get_available_queries()
        assert "test_global_query" in available_queries
        assert isinstance(available_queries["test_global_query"], KQLQueryDefinition)


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_yaml_loading_with_malformed_content(self):
        """Test handling of malformed YAML content."""
        registry = QueryRegistry()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            yaml_path = Path(f.name)

        try:
            with pytest.raises(yaml.YAMLError):
                registry.load_from_yaml(yaml_path)
        finally:
            yaml_path.unlink()

    def test_yaml_loading_missing_required_fields(self):
        """Test handling of YAML missing required fields."""
        registry = QueryRegistry()

        # Missing 'name' field
        incomplete_content = {"description": "Query without name"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(incomplete_content, f)
            yaml_path = Path(f.name)

        try:
            with pytest.raises(KeyError):
                registry.load_from_yaml(yaml_path)
        finally:
            yaml_path.unlink()
