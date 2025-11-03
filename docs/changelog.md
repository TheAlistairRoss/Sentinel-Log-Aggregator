# Changelog

All notable changes to the Sentinel Log Aggregator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive security analysis tools (Bandit, Safety, pip-audit, Semgrep, CodeQL)
- Microsoft SDL-compliant security pipeline
- Pre-commit hooks for automated security scanning
- Local security scanning script (`run_security_scan.py`)
- Enhanced CI/CD pipeline with security integration
- SBOM (Software Bill of Materials) generation
- License compliance checking
- Comprehensive documentation following Microsoft Learn standards

### Changed
- Enhanced test coverage to 97.56% with comprehensive workspace manager tests
- Improved error handling and logging throughout the codebase
- Updated dependency management and removed unused packages

### Security
- Added comprehensive static analysis security testing (SAST)
- Implemented software composition analysis (SCA) for dependencies
- Enhanced secrets detection and prevention
- Added container and infrastructure security scanning

## [0.1.0] - 2025-11-01

### Added
- Initial release of Microsoft Sentinel Log Aggregator
- Azure SDK-compliant Python library for multi-workspace log aggregation
- Core query engine with batch processing capabilities
- Azure Monitor client with authentication and retry logic
- Workspace management system with configuration support
- Command-line interface (CLI) for easy operation
- SDK interface for programmatic usage
- Comprehensive test suite with high coverage
- Type hints and static analysis support
- Configuration management via environment variables and YAML
- Async/await patterns for optimal performance
- Row-level security tagging for data isolation
- Correlation ID tracking for audit trails
- Memory-efficient streaming data upload
- Error tracking and execution monitoring

### Features
- **Multi-workspace Support**: Aggregate logs from multiple Microsoft Sentinel workspaces
- **Batch Processing**: Configurable time-based batching for efficient data processing
- **Azure Integration**: Native Azure SDK integration with managed identity support
- **Concurrent Execution**: Async query execution with configurable concurrency limits
- **Streaming Upload**: Immediate data upload to avoid memory issues
- **Configuration Management**: Flexible configuration via environment variables or YAML files
- **CLI Interface**: Easy-to-use command-line interface for operations
- **SDK Interface**: Programmatic access for integration into larger systems
- **Comprehensive Testing**: 97.56% test coverage with unit and integration tests
- **Type Safety**: Full type hints for better IDE support and code quality

### Technical Details
- **Python Version**: 3.8+ support
- **Azure SDK**: Uses latest Azure Monitor Query and Ingestion SDKs
- **Authentication**: DefaultAzureCredential with fallback options
- **Performance**: Async/await patterns with configurable concurrency
- **Monitoring**: Comprehensive logging and execution tracking
- **Security**: Row-level security tags and audit trail support

[Unreleased]: https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/releases/tag/v0.1.0