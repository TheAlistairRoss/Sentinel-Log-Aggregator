# Sentinel Log Aggregator Documentation

Welcome to the comprehensive documentation for the Microsoft Sentinel Log Aggregator - a production-ready Python package for aggregating logs from multiple Sentinel workspaces.

## 📚 Documentation Structure

### Getting Started
1. **[Overview](overview.md)** - Introduction, features, architecture, and use cases
2. **[Quick Start - CLI](quickstart-cli.md)** - Get running with CLI in 5 minutes
3. **[Quick Start - SDK](quickstart-sdk.md)** - Integrate SDK into your Python app
4. **[Authentication](authentication.md)** - Set up Azure credentials and permissions

### Reference Guides
5. **[CLI Reference](cli-reference.md)** - Complete CLI commands, arguments, and examples
6. **[SDK Reference](sdk-reference.md)** - Python API, classes, and methods
7. **[CLI Advanced Usage](cli-advanced.md)** - Advanced CLI patterns and automation
8. **[SDK Advanced Usage](sdk-advanced.md)** - Advanced SDK patterns and customization

### Configuration
9. **[Workspace Configuration](workspace-configuration.md)** - Configure workspaces YAML file
10. **[Query Configuration](query-configuration.md)** - Define custom KQL queries
11. **[Environment Variables](environment-variables.md)** - ENV file structure and reference

### Operations
12. **[Troubleshooting](troubleshooting.md)** - Common issues, error messages, and solutions
13. **[Health Logging](health-logging-deployment.md)** - Deploy monitoring infrastructure
14. **[Security](security.md)** - Security best practices and compliance

### Development
15. **[Installation (Development)](installation.md)** - Development environment setup
16. **[Workflows](workflows.md)** - CI/CD pipeline documentation
17. **[Packaging](packaging.md)** - Package release process

## 🚀 Quick Navigation

### I want to...
- **Use the CLI** → Start with [Quick Start CLI](quickstart-cli.md)
- **Use the Python SDK** → Start with [Quick Start SDK](quickstart-sdk.md)
- **Set up authentication** → See [Authentication Guide](authentication.md)
- **Configure workspaces** → See [Workspace Configuration](workspace-configuration.md)
- **Create custom queries** → See [Query Configuration](query-configuration.md)
- **Troubleshoot errors** → See [Troubleshooting](troubleshooting.md)
- **Contribute** → See [Development Guide](development.md)

## 📖 Documentation Status

| Document | Status | Last Updated |
|----------|--------|--------------|
| Overview | ✅ Complete | Nov 2025 |
| Quick Start Guides | ✅ Complete | Nov 2025 |
| Authentication | ✅ Complete | Nov 2025 |
| CLI Reference | ✅ Complete | Nov 2025 |
| SDK Reference | ✅ Complete | Nov 2025 |
| Configuration Files | ✅ Complete | Nov 2025 |
| Troubleshooting | ✅ Complete | Nov 2025 |

## 🔧 System Requirements

- **Python**: 3.8 or later
- **Azure SDK**: Installed automatically
- **Authentication**: Azure credentials (Managed Identity, Service Principal, or Azure CLI)
- **Permissions**: Log Analytics Reader + Monitoring Metrics Publisher

## 💡 Support

- **Issues**: [GitHub Issues](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/discussions)
3. Check security scanning requirements in workflows documentation

### For Maintainers
1. [workflows.md](workflows.md) contains complete automation documentation
2. [packaging.md](packaging.md) covers release and distribution management
3. Security compliance details in workflows documentation

## Documentation Standards

All documentation follows Microsoft Learn style guidelines:
- Clear, concise language
- Structured with proper headings
- Code examples with syntax highlighting
- Step-by-step procedures
- Troubleshooting sections
- Regular updates with project changes

---

*For questions about documentation, create an issue with the `documentation` label.*