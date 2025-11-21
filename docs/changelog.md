# Changelog

All notable changes to the Sentinel Log Aggregator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- No unreleased changes

## [1.0.0] - 2025-11-21

### Initial Release

First stable release of the Microsoft Sentinel Log Aggregator - an open-source, community-maintained tool for aggregating logs across multiple Microsoft Sentinel workspaces.

#### Core Features

**Multi-Workspace Aggregation**
- Query and aggregate data across multiple Microsoft Sentinel workspaces
- Centralized reporting with data transformation and normalization
- Row-level security tagging for data isolation and multi-tenancy support

**Azure SDK Compliance**
- Follows Microsoft Azure SDK design guidelines and patterns
- Native Azure authentication with managed identity, service principal, and Azure CLI support
- Integration with Azure Monitor Query and Ingestion services
- Distributed tracing and Application Insights integration

**Batch Processing**
- Configurable time-based batching for efficient data processing
- Async/await patterns with configurable concurrency limits
- Memory-efficient streaming data upload
- Incremental processing with last successful timestamp tracking

**Interfaces**
- Command-line interface (CLI) for easy operation and automation
- Python SDK for programmatic integration
- Configuration via environment variables, YAML files, or code

**Query Management**
- Flexible query organization with custom directory structures
- Parameterized KQL queries with runtime substitution
- Built-in queries for common security analytics use cases
- Support for custom query development

**Reliability & Observability**
- Comprehensive error handling with service-specific exceptions
- Detailed logging with correlation ID tracking
- Health monitoring and diagnostics
- Long-running operation (LRO) support with progress tracking
- Execution history and status tracking

**Security & Compliance**
- Comprehensive security scanning (Bandit, Safety, Semgrep, CodeQL)
- SBOM (Software Bill of Materials) generation
- License compliance checking
- Secrets detection and prevention
- Microsoft SDL-compliant security pipeline

**Quality Assurance**
- 97%+ test coverage with unit and integration tests
- Full type hints for better IDE support
- Pre-commit hooks for code quality
- Automated CI/CD pipelines

#### Technical Requirements
- Python 3.11 or higher
- Azure subscription with Microsoft Sentinel workspaces
- Appropriate Azure RBAC permissions

#### License
Released under the MIT License. This is a community-maintained open-source project.

[Unreleased]: https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/releases/tag/v1.0.0