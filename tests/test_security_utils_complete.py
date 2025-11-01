"""
Comprehensive tests for security_utils.py to achieve 100% coverage.
Targets ALL missing lines for 100% coverage.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from sentinel_log_aggregator.security_utils import (
    SecureLogger,
    SecurityError,
    generate_correlation_id,
    hash_sensitive_data,
    sanitize_log_output,
    sanitize_user_input,
    validate_azure_resource_id,
    validate_file_path,
    validate_kql_query,
    validate_workspace_id,
)


class TestSecurityUtilsComplete:
    """Tests to achieve 100% coverage for security_utils.py"""

    def test_sanitize_log_output_list_handling_line_58(self):
        """Test line 58: List handling in sanitize_log_output"""
        # Test the list handling branch on line 58
        data = {
            "normal_list": [
                {"customer_id": "12345678-1234-1234-1234-123456789012"},
                {"customer_id": "87654321-4321-4321-4321-210987654321"},
            ]
        }

        result = sanitize_log_output(data)

        # Should recursively sanitize list items
        assert isinstance(result["normal_list"], list)
        assert len(result["normal_list"]) == 2
        assert result["normal_list"][0]["customer_id"] == "12345678..."
        assert result["normal_list"][1]["customer_id"] == "87654321..."

    def test_sanitize_log_output_non_dict_return_line_67(self):
        """Test line 67: Return for non-dict input"""
        # Test when input is not a dict (line 67 return statement)
        test_cases = ["simple string", 12345, ["list", "of", "items"], None, True]

        for test_input in test_cases:
            result = sanitize_log_output(test_input)
            assert result == test_input  # Should return unchanged for non-dict

    def test_validate_kql_query_excessive_unions_line_133(self):
        """Test line 133: Excessive UNION operations validation"""
        # Create a query with more than 50 UNION operations to trigger line 133
        unions = " UNION ".join([f"Table{i}" for i in range(52)])  # 51 UNIONs
        query = f"SecurityEvent | union {unions}"

        with pytest.raises(SecurityError, match="excessive UNION operations"):
            validate_kql_query(query)

    def test_validate_azure_resource_id_invalid_format_line_174(self):
        """Test line 174: Invalid resource ID format"""
        # Test various invalid resource ID formats that should trigger line 174
        invalid_resource_ids = [
            "/invalid/format",
            "/subscriptions/",
            "/subscriptions/abc/providers/Microsoft.Something/invalid",
            "",
            "not-a-resource-id",
        ]

        for invalid_id in invalid_resource_ids:
            with pytest.raises(SecurityError):
                validate_azure_resource_id(invalid_id)

    def test_validate_file_path_suspicious_chars_line_247(self):
        """Test line 247: Suspicious characters in file path validation"""
        # Test file paths with suspicious characters (should hit line 247)
        suspicious_paths = [
            "config<.yaml",
            "config>.yaml",
            "config|.yaml",
            "config&.yaml",
            "config;.yaml",
            "config`.yaml",
            "config$.yaml",
        ]

        for path in suspicious_paths:
            with pytest.raises(SecurityError, match="suspicious characters"):
                validate_file_path(path)

    def test_validate_file_path_extension_check_line_263(self):
        """Test line 263: File extension validation"""
        # Test file paths with invalid extensions (should hit line 263)
        invalid_extensions = [
            "config.txt",
            "config.exe",
            "config.bat",
            "config.sh",
            "config",  # No extension
        ]

        for path in invalid_extensions:
            with pytest.raises(SecurityError, match="File extension not allowed"):
                validate_file_path(path, allowed_extensions=[".yaml", ".yml"])

    def test_sanitize_user_input_max_length_line_283(self):
        """Test line 283: Maximum length validation in sanitize_user_input"""
        # Test input that exceeds maximum length (should hit line 283)
        long_input = "x" * 1001  # Exceeds default max_length of 1000

        with pytest.raises(SecurityError, match="exceeds maximum length"):
            sanitize_user_input(long_input)

        # Test with custom max_length
        medium_input = "x" * 101
        with pytest.raises(SecurityError, match="exceeds maximum length"):
            sanitize_user_input(medium_input, max_length=100)

    def test_comprehensive_security_edge_cases(self):
        """Comprehensive test for edge cases across all functions"""

        # Test sanitize_log_output with nested structures
        complex_data = {
            "level1": {
                "level2": {
                    "customer_id": "12345678-1234-1234-1234-123456789012",
                    "nested_list": [
                        {"workspace_id": "sensitive_workspace_id_long"},
                        {"another_field": "normal_value"},
                    ],
                }
            }
        }

        result = sanitize_log_output(complex_data)
        assert result["level1"]["level2"]["customer_id"] == "12345678..."
        assert result["level1"]["level2"]["nested_list"][0]["workspace_id"] == "sensitiv..."

        # Test KQL query with exactly 50 unions (should pass)
        unions_50 = " UNION ".join([f"Table{i}" for i in range(50)])  # 49 UNIONs
        query_50 = f"SecurityEvent | union {unions_50}"
        assert validate_kql_query(query_50) == True

        # Test valid Azure resource ID
        valid_resource_id = "/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/test/providers/Microsoft.OperationalInsights/workspaces/test"
        assert validate_azure_resource_id(valid_resource_id) == True

        # Test valid file path
        valid_file = "config.yaml"
        assert validate_file_path(valid_file) == True

        # Test valid user input
        valid_input = "Hello World"
        result = sanitize_user_input(valid_input)
        assert result == "Hello World"

    def test_edge_case_combinations(self):
        """Test edge case combinations to ensure all branches are covered"""

        # Test empty and None values in sanitize_log_output
        edge_data = {
            "empty_string": "",
            "none_value": None,
            "short_sensitive": "ab",  # Less than 8 chars
            "empty_list": [],
            "empty_dict": {},
        }

        result = sanitize_log_output(
            edge_data, sensitive_fields=["empty_string", "short_sensitive"]
        )
        assert result["empty_string"] == "***"  # Short sensitive field
        assert result["short_sensitive"] == "***"  # Short sensitive field
        assert result["none_value"] is None
        assert result["empty_list"] == []
        assert result["empty_dict"] == {}


class TestSecurityUtilsErrorConditions:
    """Test error conditions and exception paths"""

    def test_validate_kql_query_all_dangerous_operations(self):
        """Test all dangerous operations in KQL validation"""
        # Test actual dangerous operations from the code
        dangerous_operations = [
            ".drop table test",
            ".delete table test",
            ".create table test",
            ".alter table test",
            ".set something",
            ".append something",
            ".ingest something",
            "external_table()",
            "sql_request()",
            "evaluate python()",
            "evaluate r()",
            "exec()",
            "sp_executesql",
            "xp_cmdshell",
            ".show files",
            ".export something",
            ".import something",
        ]

        for operation in dangerous_operations:
            query = f"SecurityEvent | where condition | {operation}"
            with pytest.raises(SecurityError, match="potentially dangerous operation"):
                validate_kql_query(query)

    def test_validate_kql_query_empty_query_line_84(self):
        """Test line 84: Empty query validation"""
        with pytest.raises(SecurityError, match="Query cannot be empty"):
            validate_kql_query("")

        with pytest.raises(SecurityError, match="Query cannot be empty"):
            validate_kql_query("   ")  # Whitespace only

        with pytest.raises(SecurityError, match="Query cannot be empty"):
            validate_kql_query(None)

    def test_validate_kql_query_length_limit_line_123(self):
        """Test line 123: Query length limit validation"""
        # Create a query longer than 100KB
        long_query = "SecurityEvent | where " + "x" * 100001
        with pytest.raises(SecurityError, match="exceeds maximum allowed length"):
            validate_kql_query(long_query)

    def test_validate_kql_query_excessive_joins_line_128(self):
        """Test line 128: Excessive JOIN operations validation"""
        # Create a query with more than 20 JOINs
        joins = " ".join([f"| join Table{i}" for i in range(22)])  # 22 JOINs
        query = f"SecurityEvent {joins}"
        with pytest.raises(SecurityError, match="excessive JOIN operations"):
            validate_kql_query(query)

    def test_validate_azure_resource_id_empty_line_164(self):
        """Test line 164: Empty resource ID validation"""
        with pytest.raises(SecurityError, match="Resource ID cannot be empty"):
            validate_azure_resource_id("")

        with pytest.raises(SecurityError, match="Resource ID cannot be empty"):
            validate_azure_resource_id(None)

    def test_validate_azure_resource_id_line_174_suspicious_pattern_detection(self):
        """Test line 174: Test suspicious pattern detection after passing format validation"""
        # Use a mock to bypass format validation and directly test suspicious pattern detection
        with patch("sentinel_log_aggregator.security_utils.re.match") as mock_match:
            # Make format validation pass
            mock_match.return_value = True

            # Now test suspicious pattern detection (which should hit line 174)
            suspicious_resource_ids = [
                "/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/group../providers/Microsoft.Something/workspace/test",  # Path traversal
                "/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/group/providers/Microsoft.Something/<script/test",  # Script injection
                "/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/group/providers/Microsoft.Something/javascript:alert/test",  # JavaScript protocol
                "/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/group/providers/Microsoft.Something/data:text/test",  # Data protocol
                "/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/group/providers/Microsoft.Something/vbscript:alert/test",  # VBScript protocol
            ]

            for resource_id in suspicious_resource_ids:
                with pytest.raises(SecurityError, match="suspicious pattern"):
                    validate_azure_resource_id(resource_id)

    def test_validate_workspace_id_invalid_guid_line_201(self):
        """Test line 201: Invalid GUID format validation to hit line 201"""
        # Mock to ensure we hit line 201 specifically - the return True
        with patch("sentinel_log_aggregator.security_utils.re.match") as mock_match:
            # Test when regex fails (returns None/False)
            mock_match.return_value = None

            with pytest.raises(SecurityError, match="Invalid workspace ID format"):
                validate_workspace_id("invalid-workspace-id")

    def test_validate_workspace_id_valid_guid_line_201_return_true(self):
        """Test line 201: Valid GUID returning True"""
        # Test a valid GUID that should pass and hit line 201 return True
        valid_guid = "12345678-1234-1234-1234-123456789012"
        result = validate_workspace_id(valid_guid)
        assert result == True

    def test_validate_workspace_id_empty_line_192(self):
        """Test line 192: Empty workspace ID validation"""
        with pytest.raises(SecurityError, match="Workspace ID cannot be empty"):
            validate_workspace_id("")

        with pytest.raises(SecurityError, match="Workspace ID cannot be empty"):
            validate_workspace_id(None)

    def test_generate_correlation_id_line_211(self):
        """Test line 211: Generate correlation ID"""
        correlation_id = generate_correlation_id()
        assert isinstance(correlation_id, str)
        assert len(correlation_id) == 32  # 16 bytes as hex = 32 chars

        # Generate multiple IDs to ensure they're unique
        ids = [generate_correlation_id() for _ in range(10)]
        assert len(set(ids)) == 10  # All should be unique

    def test_hash_sensitive_data_lines_225_229(self):
        """Test lines 225-229: Hash sensitive data function"""
        data = "sensitive_information"

        # Test with default salt
        hash1 = hash_sensitive_data(data)
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA-256 produces 64 character hex string

        # Test with custom salt
        hash2 = hash_sensitive_data(data, salt="custom_salt")
        assert isinstance(hash2, str)
        assert len(hash2) == 64
        assert hash1 != hash2  # Different salts should produce different hashes

        # Test consistency
        hash3 = hash_sensitive_data(data)
        assert hash1 == hash3  # Same data and salt should produce same hash

    def test_validate_file_path_edge_cases(self):
        """Test validate_file_path with various edge cases"""

        # Test empty file path
        with pytest.raises(SecurityError, match="cannot be empty"):
            validate_file_path("")

        # Test path traversal
        with pytest.raises(SecurityError, match="dangerous patterns"):
            validate_file_path("../config.yaml")

        # Test absolute path
        with pytest.raises(SecurityError, match="dangerous patterns"):
            validate_file_path("/etc/passwd")

        # Test valid cases
        valid_paths = ["config.yaml", "subfolder/config.yml", "data.json"]

        for path in valid_paths:
            assert validate_file_path(path) == True

    def test_sanitize_user_input_injection_patterns(self):
        """Test sanitize_user_input with injection patterns"""
        # Test non-string input first (line 283)
        with pytest.raises(SecurityError, match="must be a string"):
            sanitize_user_input(12345)

        # Test various injection attempts that should be detected
        injection_inputs = [
            "<script>alert('xss')</script>",  # Script tags
            "javascript:alert('xss')",  # JavaScript protocol
            "vbscript:alert('xss')",  # VBScript protocol
            "onclick=alert('xss')",  # Event handler
            "expression(alert('xss'))",  # CSS expression
        ]

        for malicious_input in injection_inputs:
            with pytest.raises(SecurityError, match="potentially malicious"):
                sanitize_user_input(malicious_input)

    def test_secure_logger_all_methods_lines_311_335(self):
        """Test SecureLogger class - lines 311-335"""
        # Create a mock logger
        mock_logger = MagicMock()
        secure_logger = SecureLogger(mock_logger)

        # Test info method (lines 315-317)
        secure_logger.info(
            "Test message", extra={"customer_id": "12345678-1234-1234-1234-123456789012"}
        )
        mock_logger.info.assert_called_once()

        # Test error method (lines 321-323)
        mock_logger.reset_mock()
        secure_logger.error(
            "Error message", extra={"workspace_id": "sensitive_workspace"}, exc_info=True
        )
        mock_logger.error.assert_called_once()

        # Test warning method (lines 327-329)
        mock_logger.reset_mock()
        secure_logger.warning("Warning message", extra={"token": "secret_token"})
        mock_logger.warning.assert_called_once()

        # Test debug method (lines 333-335)
        mock_logger.reset_mock()
        secure_logger.debug("Debug message", extra={"password": "secret_password"})
        mock_logger.debug.assert_called_once()

        # Test methods without extra parameter
        mock_logger.reset_mock()
        secure_logger.info("Simple message")
        secure_logger.error("Simple error", exc_info=False)
        secure_logger.warning("Simple warning")
        secure_logger.debug("Simple debug")

        assert mock_logger.info.call_count == 1
        assert mock_logger.error.call_count == 1
        assert mock_logger.warning.call_count == 1
        assert mock_logger.debug.call_count == 1
