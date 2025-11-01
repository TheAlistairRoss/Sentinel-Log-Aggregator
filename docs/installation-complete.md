---
title: Complete Installation Guide
description: Comprehensive installation guide for Sentinel Log Aggregator including GitHub releases, PyPI, development installation, and troubleshooting.
ms.date: 11/01/2025
ms.topic: how-to
ms.service: microsoft-sentinel
---

# Complete Installation Guide

This guide covers all installation methods for the Sentinel Log Aggregator package, from stable releases to development installations.

## 📦 Installation Methods

### 1. Install from PyPI (Recommended for Production)

Install the latest stable release from the Python Package Index:

```bash
# Install the latest stable version
pip install sentinel-log-aggregator

# Install with all optional dependencies
pip install sentinel-log-aggregator[security,docs]

# Install specific version
pip install sentinel-log-aggregator==0.1.0
```

### 2. Install from GitHub Releases (Version-Controlled)

Install directly from GitHub releases for version control and access to pre-releases:

```bash
# Install latest release from GitHub
pip install https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/releases/latest/download/sentinel_log_aggregator-0.1.0-py3-none-any.whl

# Install specific version from GitHub
pip install https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/releases/download/v0.1.0/sentinel_log_aggregator-0.1.0-py3-none-any.whl

# Install from tarball (source distribution)
pip install https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/releases/download/v0.1.0/sentinel-log-aggregator-0.1.0.tar.gz
```

### 3. Install from Git Repository (Latest Development)

Install the latest development version directly from the main branch:

```bash
# Install from main branch
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git

# Install from specific branch
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git@develop

# Install from specific commit
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git@abc123f

# Install with development dependencies
pip install "git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git[dev,security]"
```

### 4. Development Installation (Editable)

For contributors and developers who want to make changes to the source code:

```bash
# Clone the repository
git clone https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git
cd Sentinel-Log-Aggregator

# Install in editable mode with development dependencies
pip install -e ".[dev,security,docs]"

# Install pre-commit hooks for development
pre-commit install
```

## 🔧 Installation Verification

After installation, verify that the package is working correctly:

### Command Line Verification

```bash
# Check version
sentinel-aggregator --version

# Display help
sentinel-aggregator --help

# Validate configuration (if you have config files)
sentinel-aggregator validate --workspace-config config/workspaces.yaml
```

### Python API Verification

```python
import sentinel_log_aggregator
from sentinel_log_aggregator import SentinelAggregatorClient

# Check version
print(f"Installed version: {sentinel_log_aggregator.__version__}")

# Test basic import
client = SentinelAggregatorClient()
print("✅ Package imported successfully!")
```

## 📋 Version Management

### Available Versions

Check available versions on different platforms:

```bash
# Check PyPI versions
pip index versions sentinel-log-aggregator

# List GitHub releases using curl
curl -s https://api.github.com/repos/TheAlistairRoss/Sentinel-Log-Aggregator/releases | grep -o '"tag_name": "[^"]*' | cut -d'"' -f4
```

### Version Constraints

Use version constraints in your requirements files:

```txt
# requirements.txt

# Exact version
sentinel-log-aggregator==0.1.0

# Compatible version (recommended)
sentinel-log-aggregator~=0.1.0

# Minimum version
sentinel-log-aggregator>=0.1.0

# Version range
sentinel-log-aggregator>=0.1.0,<1.0.0
```

### Pre-release Versions

Install pre-release versions for testing:

```bash
# Install latest pre-release
pip install --pre sentinel-log-aggregator

# Install specific pre-release
pip install sentinel-log-aggregator==0.2.0a1
```

## 🐍 Virtual Environment Setup

Always use virtual environments for isolation:

### Using venv (Built-in)

```bash
# Create virtual environment
python -m venv sentinel-env

# Activate (Linux/macOS)
source sentinel-env/bin/activate

# Activate (Windows)
sentinel-env\Scripts\activate

# Install package
pip install sentinel-log-aggregator

# Deactivate when done
deactivate
```

### Using conda

```bash
# Create conda environment
conda create -n sentinel-env python=3.11

# Activate environment
conda activate sentinel-env

# Install from PyPI (conda-forge doesn't have it yet)
pip install sentinel-log-aggregator

# Or install from GitHub
pip install git+https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator.git
```

## 🚨 Troubleshooting

### Common Installation Issues

#### Issue: "No module named 'sentinel_log_aggregator'"

**Solution:**
```bash
# Verify installation
pip list | grep sentinel

# Reinstall if missing
pip install --force-reinstall sentinel-log-aggregator
```

#### Issue: Azure SDK conflicts

**Solution:**
```bash
# Upgrade Azure SDK packages
pip install --upgrade azure-identity azure-monitor-query azure-monitor-ingestion

# Or install with constraints
pip install sentinel-log-aggregator --constraint constraints.txt
```

#### Issue: Permission errors on Windows

**Solution:**
```bash
# Install for current user only
pip install --user sentinel-log-aggregator

# Or run as administrator (not recommended)
```

#### Issue: SSL certificate errors

**Solution:**
```bash
# Upgrade certificates
pip install --upgrade certifi

# Or install with trusted hosts (temporary fix)
pip install --trusted-host pypi.org --trusted-host pypi.python.org sentinel-log-aggregator
```

### Getting Help

If you encounter issues:

1. **Check the [Issues page](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/issues)** for known problems
2. **Check compatibility** with your Python version (3.8+ required)
3. **Update pip** to the latest version: `pip install --upgrade pip`
4. **Create a new issue** with detailed error information if needed

## 📈 Upgrade Guidelines

### Upgrading to New Versions

```bash
# Upgrade to latest version
pip install --upgrade sentinel-log-aggregator

# Upgrade to specific version
pip install --upgrade sentinel-log-aggregator==0.2.0

# Check what would be upgraded
pip list --outdated | grep sentinel
```

### Breaking Changes

Always check the [CHANGELOG.md](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/blob/main/CHANGELOG.md) before upgrading for:

- Breaking API changes
- Configuration file format changes
- Deprecated features
- New requirements

### Safe Upgrade Process

1. **Backup your configuration files**
2. **Test in a development environment first**
3. **Read the changelog for breaking changes**
4. **Update your code for any API changes**
5. **Run your test suite after upgrading**

---

For more information, see the [project documentation](https://thealistairross.github.io/Sentinel-Log-Aggregator/) or [GitHub repository](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator).