"""Tests for test utilities module."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from tests.test_utils import (
    get_test_metadata_defaults,
    load_test_workspace_config_with_metadata,
    resolve_environment_variables,
    resolve_test_config_metadata,
)


class TestEnvironmentVariableResolution:
    """Test environment variable resolution functionality."""

    def test_resolve_environment_variables_with_defaults(self):
        """Test resolving environment variables with default values."""
        text = "${HOME:-/default/home}"
        result = resolve_environment_variables(text)

        # Should use environment value if set, otherwise default
        expected = os.environ.get("HOME", "/default/home")
        assert result == expected

    def test_resolve_environment_variables_missing_var(self):
        """Test resolving missing environment variables uses defaults."""
        text = "${NONEXISTENT_VAR:-default_value}"
        result = resolve_environment_variables(text)
        assert result == "default_value"

    def test_resolve_environment_variables_no_default(self):
        """Test resolving environment variables without defaults."""
        text = "${NONEXISTENT_VAR}"
        result = resolve_environment_variables(text, {"NONEXISTENT_VAR": "from_defaults"})
        assert result == "from_defaults"

    def test_resolve_environment_variables_multiple(self):
        """Test resolving multiple environment variables in one string."""
        text = "User: ${USER:-unknown}, Home: ${HOME:-/tmp}"
        result = resolve_environment_variables(text)

        expected_user = os.environ.get("USER", "unknown")
        expected_home = os.environ.get("HOME", "/tmp")
        expected = f"User: {expected_user}, Home: {expected_home}"
        assert result == expected

    def test_resolve_environment_variables_no_variables(self):
        """Test text without environment variables passes through unchanged."""
        text = "This is just plain text"
        result = resolve_environment_variables(text)
        assert result == text


class TestMetadataDefaults:
    """Test metadata default value generation."""

    def test_get_test_metadata_defaults(self):
        """Test that metadata defaults are generated correctly."""
        defaults = get_test_metadata_defaults()

        # Check required keys exist
        required_keys = ["PACKAGE_VERSION", "BUILD_TIMESTAMP", "BUILD_USER", "TEST_ENVIRONMENT"]
        for key in required_keys:
            assert key in defaults
            assert defaults[key]  # Should not be empty

        # Check version is from package
        from sentinel_log_aggregator.version import __version__

        assert defaults["PACKAGE_VERSION"] == __version__

        # Check timestamp format (YYYY-MM-DD)
        import re

        timestamp_pattern = r"\d{4}-\d{2}-\d{2}"
        assert re.match(timestamp_pattern, defaults["BUILD_TIMESTAMP"])


class TestConfigMetadataResolution:
    """Test configuration metadata resolution."""

    def test_resolve_test_config_metadata(self):
        """Test resolving metadata in configuration dictionary."""
        config = {
            "workspaces": [{"test": "data"}],
            "metadata": {
                "version": "${PACKAGE_VERSION:-0.0.1}",
                "last_updated": "${BUILD_TIMESTAMP:-2020-01-01}",
                "environment": "${TEST_ENVIRONMENT:-test}",
                "static_field": "unchanged",
            },
        }

        result = resolve_test_config_metadata(config)

        # Check that metadata was resolved
        metadata = result["metadata"]
        assert metadata["static_field"] == "unchanged"
        assert metadata["version"] != "${PACKAGE_VERSION:-0.0.1}"  # Should be resolved
        assert metadata["environment"] != "${TEST_ENVIRONMENT:-test}"  # Should be resolved

        # Check workspaces unchanged
        assert result["workspaces"] == config["workspaces"]

    def test_resolve_test_config_metadata_no_metadata(self):
        """Test resolving config without metadata section."""
        config = {"workspaces": [{"test": "data"}]}
        result = resolve_test_config_metadata(config)
        assert result == config


class TestWorkspaceConfigLoading:
    """Test loading workspace configuration with dynamic metadata."""

    def test_load_test_workspace_config_with_metadata(self):
        """Test loading the actual test workspace configuration."""
        config = load_test_workspace_config_with_metadata()

        # Check basic structure
        assert "workspaces" in config
        assert "metadata" in config
        assert isinstance(config["workspaces"], list)
        assert len(config["workspaces"]) > 0

        # Check metadata resolution
        metadata = config["metadata"]
        assert "version" in metadata
        assert "last_updated" in metadata
        assert "test_environment" in metadata

        # Version should be resolved to actual package version
        from sentinel_log_aggregator.version import __version__

        assert metadata["version"] == __version__

        # Should not contain unresolved environment variables
        for key, value in metadata.items():
            if isinstance(value, str):
                assert "${" not in value, f"Unresolved variable in {key}: {value}"

    def test_load_test_workspace_config_custom_path(self):
        """Test loading workspace config from custom path."""
        # Create temporary config file
        test_config = {
            "workspaces": [{"test": "workspace"}],
            "metadata": {
                "version": "${PACKAGE_VERSION:-1.0}",
                "environment": "${TEST_ENVIRONMENT:-dev}",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config, f)
            temp_path = f.name

        try:
            config = load_test_workspace_config_with_metadata(temp_path)

            # Check resolution worked
            assert config["metadata"]["version"] != "${PACKAGE_VERSION:-1.0}"
            assert config["metadata"]["environment"] != "${TEST_ENVIRONMENT:-dev}"

        finally:
            Path(temp_path).unlink()  # Clean up


if __name__ == "__main__":
    pytest.main([__file__])
