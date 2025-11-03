"""Utilities for test configuration and setup."""

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Add the package root to Python path for testing
package_root = Path(__file__).parent.parent
sys.path.insert(0, str(package_root))

from sentinel_log_aggregator.version import __version__


def resolve_environment_variables(text: str, default_values: Dict[str, str] = None) -> str:
    """
    Resolve environment variables in text using ${VAR_NAME:-default} syntax.
    
    Args:
        text: Text containing environment variable references
        default_values: Optional dictionary of default values
        
    Returns:
        Text with environment variables resolved
        
    Examples:
        >>> resolve_environment_variables("${HOME:-/default}")
        "/home/user"  # if HOME is set
        
        >>> resolve_environment_variables("${MISSING:-default}")
        "default"  # if MISSING is not set
    """
    if default_values is None:
        default_values = {}
    
    def replace_var(match):
        var_expr = match.group(1)
        if ":-" in var_expr:
            var_name, default_value = var_expr.split(":-", 1)
        else:
            var_name = var_expr
            default_value = default_values.get(var_name, "")
        
        return os.environ.get(var_name, default_value)
    
    # Pattern to match ${VAR_NAME:-default} or ${VAR_NAME}
    pattern = r'\$\{([^}]+)\}'
    return re.sub(pattern, replace_var, text)


def get_test_metadata_defaults() -> Dict[str, str]:
    """
    Get default values for test configuration metadata.
    
    Returns:
        Dictionary of default metadata values
    """
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    return {
        "PACKAGE_VERSION": __version__,
        "BUILD_TIMESTAMP": current_time,
        "BUILD_USER": "test-automation",
        "TEST_ENVIRONMENT": "development",
    }


def resolve_test_config_metadata(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve environment variables in test configuration metadata.
    
    Args:
        config_data: Configuration dictionary (will be modified in place)
        
    Returns:
        Updated configuration dictionary
    """
    if "metadata" not in config_data:
        return config_data
    
    defaults = get_test_metadata_defaults()
    metadata = config_data["metadata"]
    
    # Resolve environment variables in metadata values
    for key, value in metadata.items():
        if isinstance(value, str):
            metadata[key] = resolve_environment_variables(value, defaults)
    
    return config_data


def load_test_workspace_config_with_metadata(config_path: str = None) -> Dict[str, Any]:
    """
    Load test workspace configuration with resolved metadata.
    
    Args:
        config_path: Path to configuration file (defaults to tests_workspaces.yaml)
        
    Returns:
        Configuration dictionary with resolved metadata
    """
    import yaml
    
    if config_path is None:
        config_path = Path(__file__).parent / "data" / "workspaces" / "tests_workspaces.yaml"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    return resolve_test_config_metadata(config_data)


if __name__ == "__main__":
    # Example usage
    config = load_test_workspace_config_with_metadata()
    print("Test configuration metadata:")
    for key, value in config.get("metadata", {}).items():
        print(f"  {key}: {value}")