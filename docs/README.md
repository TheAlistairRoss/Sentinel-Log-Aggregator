# Documentation Index

This directory contains comprehensive documentation for the Microsoft Sentinel Log Aggregator project.

## Available Documentation

### Setup and Installation
- **[installation.md](installation.md)** - Complete installation guide with requirements and setup instructions
- **[packaging.md](packaging.md)** - Package distribution guide for development and release management

### Development and Operations
- **[workflows.md](workflows.md)** - Complete GitHub Actions workflows documentation including:
  - CI/CD Pipeline (6 jobs: test, integration-test, build, security-scan, documentation, release)
  - Security Scanning (Microsoft SDL compliance with 12+ security tools)
  - Troubleshooting and best practices

### Generated Documentation
- **API Documentation** - Generated from code docstrings during CI/CD
- **Sphinx Documentation** - Built automatically and deployed to GitHub Pages

## Quick Reference

### For Users
1. Start with [installation.md](installation.md) for setup
2. See main README.md for usage examples
3. Use `sentinel-aggregator --help` for CLI reference

### For Contributors
1. Review [workflows.md](workflows.md) for CI/CD understanding
2. See [packaging.md](packaging.md) for release processes
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