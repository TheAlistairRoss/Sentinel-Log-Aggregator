# Development Setup Guide

This guide covers setting up a development environment for the Microsoft Sentinel Log Aggregator project.

## Prerequisites

- Python 3.8+ (3.11 recommended)
- Git
- Azure CLI (for authentication during development)
- VS Code (recommended) with Python extension

## Initial Setup

### 1. Clone and Setup Repository

```bash
git clone <repository-url>
cd "Sentinel Log Aggregator"

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Windows CMD
.\.venv\Scripts\activate.bat
# Linux/macOS
source .venv/bin/activate

# Upgrade pip and install build tools
python -m pip install --upgrade pip setuptools wheel
```

### 2. Install Development Dependencies

```bash
# Option A: Install with all optional dependencies (recommended)
pip install -e ".[dev,security,docs]"

# Option B: Use the development helper script
python scripts/dev.py install-dev

# Option C: Install from requirements files (if available)
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

**What gets installed:**
- **Core dependencies**: Azure SDK libraries, aiohttp, PyYAML, etc.
- **Development tools**: pytest, black, isort, flake8, mypy
- **Pre-commit framework**: Automatic code quality checks
- **Security tools**: bandit, safety, pip-audit, semgrep
- **Documentation tools**: Sphinx, sphinx-rtd-theme

### 3. Install Pre-Commit Hooks (Critical!)

Pre-commit hooks enforce code quality and security standards automatically:

```bash
# Install pre-commit hooks into .git/hooks/
pre-commit install

# Also install commit message hooks for conventional commits
pre-commit install --hook-type commit-msg

# Verify installation
pre-commit --version

# Test hooks on all files (optional but recommended)
pre-commit run --all-files
```

**Why pre-commit is essential:**
- ✅ Catches issues before they reach CI/CD
- ✅ Enforces consistent code formatting (black, isort)
- ✅ Runs security scans (bandit, detect-secrets, trufflehog)
- ✅ Validates commit messages (conventional commits)
- ✅ Prevents committing secrets or sensitive data
- ✅ Runs tests on pre-push (optional)

**Without pre-commit installed:**
- ❌ Commits will fail with "pre-commit not found" error
- ❌ Must use `--no-verify` flag (bypasses all checks)
- ❌ Code quality issues caught late in CI/CD pipeline

### 4. Alternative: Quick Setup Script

For Windows users, an automated setup script is available:

```powershell
# Run automated setup (PowerShell)
.\scripts\setup-dev.ps1

# Skip virtual environment creation (if already exists)
.\scripts\setup-dev.ps1 -SkipVenv

# Skip test execution
.\scripts\setup-dev.ps1 -SkipTests
```

**What the script does:**
- ✅ Validates Python 3.11+ is installed
- ✅ Creates virtual environment (`.venv`)
- ✅ Upgrades pip, setuptools, and wheel
- ✅ Installs all dependencies (dev, security, docs)
- ✅ Installs and configures pre-commit hooks
- ✅ Creates `.env` template file
- ✅ Runs initial test suite validation

Or use the platform-agnostic Python helper script for manual setup:

```bash
# Install everything and set up pre-commit
python scripts/dev.py install-dev
python scripts/dev.py pre-commit-install

# Run initial checks to verify setup
python scripts/dev.py check
```

### 3. Configure Environment

Create a `.env` file in the project root:

```bash
# Azure Configuration (for development/testing)
DCR_LOGS_INGESTION_ENDPOINT=https://your-dcr-endpoint.monitor.azure.com
DCR_IMMUTABLE_ID=dcr-your-immutable-id

# Development Settings
LOG_LEVEL=DEBUG
MAX_CONCURRENT_QUERIES=3
QUERY_TIMEOUT_SECONDS=300

# Test Configuration
AZURE_SUBSCRIPTION_ID=your-test-subscription-id
AZURE_TENANT_ID=your-tenant-id
```

### 4. Validate Setup

```bash
# Quick validation
python scripts/dev.py check

# Or run checks individually:

# Code formatting check
python scripts/dev.py format-check

# Linting
python scripts/dev.py lint

# Tests with coverage
python scripts/dev.py test

# Security scans
python scripts/dev.py security

# Pre-commit hooks
python scripts/dev.py pre-commit-run
```

## Understanding Pre-Commit Hooks

### What Runs on Every Commit

The `.pre-commit-config.yaml` file defines **20+ automated checks**:

#### Code Quality (Always Run)
- **black** - Code formatting (100 char line length)
- **isort** - Import sorting
- **flake8** - Linting with docstring checks
- **mypy** - Type checking
- **pydocstyle** - Docstring style validation

#### Security (Always Run)
- **bandit** - Python security issues
- **detect-secrets** - Secret detection
- **trufflehog** - Advanced secret scanning
- **safety** - Package vulnerability scanning
- **semgrep** - SAST (Static Application Security Testing)

#### File Checks (Always Run)
- **trailing-whitespace** - Removes trailing whitespace
- **end-of-file-fixer** - Ensures newline at EOF
- **check-yaml** - Validates YAML syntax
- **check-json** - Validates JSON syntax
- **check-merge-conflict** - Detects merge conflicts
- **check-case-conflict** - Detects case conflicts
- **debug-statements** - Finds forgotten debug code
- **yamllint** - YAML linting
- **hadolint** - Dockerfile linting (if present)

#### Commit Message (commit-msg hook)
- **commitizen** - Enforces [conventional commits](https://www.conventionalcommits.org/)
  - `feat:` - New features
  - `fix:` - Bug fixes
  - `docs:` - Documentation changes
  - `refactor:` - Code refactoring
  - `test:` - Test additions/modifications
  - `chore:` - Maintenance tasks

#### Tests (Pre-Push Only)
- **pytest** - Full test suite (only runs on `git push`)

### Pre-Commit Commands

```bash
# Install hooks (required once after clone)
pre-commit install
pre-commit install --hook-type commit-msg

# Run hooks manually on staged files
pre-commit run

# Run hooks on all files (not just staged)
pre-commit run --all-files

# Run specific hook
pre-commit run black
pre-commit run bandit

# Update hooks to latest versions
pre-commit autoupdate

# Skip hooks for emergency commits (not recommended)
git commit --no-verify -m "emergency fix"

# Uninstall hooks (not recommended)
pre-commit uninstall
```

### Typical Pre-Commit Output

```bash
$ git commit -m "feat: add new feature"

[INFO] Installing environment for https://github.com/psf/black.
[INFO] Once installed this environment will be reused.
[INFO] This may take a few minutes...

black....................................................................Passed
isort....................................................................Passed
flake8...................................................................Passed
bandit...................................................................Passed
detect-secrets...........................................................Passed
trailing-whitespace......................................................Passed
end-of-file-fixer........................................................Passed
check-yaml...............................................................Passed
check-json...............................................................Passed
commitizen...............................................................Passed

[develop abc1234] feat: add new feature
 3 files changed, 42 insertions(+), 5 deletions(-)
```

### Common Pre-Commit Issues

#### Issue: "pre-commit not found"
```bash
# Solution: Install pre-commit
pip install pre-commit
pre-commit install
```

#### Issue: Hooks failing on first run
```bash
# Pre-commit needs to download hook environments
# This is normal and happens once per hook
# Just wait for installation to complete
```

#### Issue: Black/isort formatting failures
```bash
# Hooks auto-fix formatting issues
# Just add the fixed files and commit again
git add .
git commit -m "your message"
```

#### Issue: Security scan false positives
```bash
# Add to .secrets.baseline or .bandit config
# Then update baseline:
detect-secrets scan > .secrets.baseline
```

#### Issue: Slow pre-commit
```bash
# Clean and reinstall hooks
pre-commit clean
pre-commit gc
pre-commit install
```

## Development Workflow

### Development Helper Scripts

The repository provides two helper scripts to streamline development tasks:

#### 1. `scripts/setup-dev.ps1` (Windows PowerShell)

**Purpose**: Automated first-time setup for Windows developers

```powershell
# Full automated setup
.\scripts\setup-dev.ps1

# Options
.\scripts\setup-dev.ps1 -SkipVenv   # Use existing virtual environment
.\scripts\setup-dev.ps1 -SkipTests  # Skip initial test run
```

**What it does:**
1. ✅ Validates Python 3.11+ installed
2. ✅ Creates virtual environment (`.venv`)
3. ✅ Activates virtual environment
4. ✅ Upgrades pip, setuptools, wheel
5. ✅ Installs all dependencies: `pip install -e ".[dev,security,docs]"`
6. ✅ Installs pre-commit hooks: `pre-commit install`
7. ✅ Creates `.env` template file
8. ✅ Runs initial tests to verify setup

#### 2. `scripts/dev.py` (Cross-Platform Python)

**Purpose**: Common development tasks and CI/CD alignment

```bash
# Installation
python scripts/dev.py install-dev         # Install all dependencies
python scripts/dev.py pre-commit-install  # Install pre-commit hooks

# Code Quality (matches CI/CD pipeline)
python scripts/dev.py format              # Auto-format code (black + isort)
python scripts/dev.py format-check        # Check formatting only (CI/CD mode)
python scripts/dev.py lint                # Run flake8 + mypy

# Testing
python scripts/dev.py test                # Run tests with coverage

# Security
python scripts/dev.py security            # Run bandit, safety, pip-audit

# Build & Docs
python scripts/dev.py build               # Build package
python scripts/dev.py docs                # Build Sphinx documentation

# Pre-commit
python scripts/dev.py pre-commit-run      # Run pre-commit on all files

# All-in-One
python scripts/dev.py check               # Run ALL checks (format-check + lint + test + security)
```

#### Available Commands Reference

| Command | Description | Matches CI/CD |
|---------|-------------|---------------|
| `clean` | Remove build artifacts and cache files | ❌ |
| `install-dev` | Install development dependencies | ✅ |
| `format` | Auto-format with black + isort | ❌ (CI checks only) |
| `format-check` | Check formatting without changes | ✅ |
| `lint` | Run flake8 + mypy | ✅ |
| `test` | Run pytest with coverage | ✅ |
| `security` | Run security scans (bandit, safety, pip-audit) | ✅ |
| `build` | Build package distribution | ✅ |
| `docs` | Build Sphinx documentation | ✅ |
| `pre-commit-install` | Install git pre-commit hooks | ✅ |
| `pre-commit-run` | Run pre-commit on all files | ✅ |
| `check` | Run all checks (comprehensive validation) | ✅ |

**Recommended Workflow:**

```bash
# Before starting work
python scripts/dev.py format               # Format your code
python scripts/dev.py lint                 # Check for issues

# Before committing
python scripts/dev.py check                # Run all checks
git add .
git commit -m "feat: your change"          # Pre-commit hooks run automatically

# Before pushing
python scripts/dev.py check                # Final validation
git push origin your-branch
```

### Code Quality Standards

The project enforces strict code quality standards:

- **Formatting**: Black with 100-character line limit
- **Import Sorting**: isort with Black profile
- **Linting**: flake8 with additional plugins
- **Type Checking**: mypy with strict optional
- **Security**: Bandit security scanner
- **Testing**: pytest with minimum 80% coverage

### Pre-commit Hooks

Pre-commit hooks automatically run on every commit. **This is not optional** - the repository is configured to require these checks.

#### When Pre-Commit Runs

```bash
# Automatic: On every git commit
git commit -m "your message"  # Hooks run automatically

# Manual: Test before committing
pre-commit run --all-files

# Skip (emergency only, not recommended)
git commit --no-verify -m "emergency fix"
```

#### What Happens Without Pre-Commit

If you haven't run `pre-commit install`, you'll see this error:

```bash
$ git commit -m "my change"
pre-commit not found. Did you forget to activate your virtualenv?
```

**Solution**: Always run `pre-commit install` after cloning the repository.

#### Pre-Commit vs CI/CD

Pre-commit hooks and CI/CD pipelines run the **same checks**:

| Check | Pre-Commit (Local) | CI/CD (GitHub Actions) |
|-------|-------------------|------------------------|
| black | ✅ Auto-fix | ✅ Check only (fails if not formatted) |
| isort | ✅ Auto-fix | ✅ Check only (fails if not sorted) |
| flake8 | ✅ Check | ✅ Check |
| mypy | ✅ Check | ✅ Check |
| bandit | ✅ Check | ✅ Check |
| security scans | ✅ Check | ✅ Check |
| tests | 🔶 On push | ✅ Always |

**Key insight**: Pre-commit catches issues **before** CI/CD, saving time and CI/CD minutes.

### Testing Strategy

The project uses a comprehensive testing approach:

#### Unit Tests
```bash
# Run all unit tests
pytest tests/ -v

# Run specific test file
pytest tests/test_sentinel_client.py -v

# Run with coverage
pytest tests/ --cov=sentinel_log_aggregator --cov-report=html
```

#### Integration Tests
```bash
# Run integration tests (requires Azure credentials)
pytest tests/ -m integration -v

# Skip integration tests
pytest tests/ -m "not integration" -v
```

#### Performance Tests
```bash
# Run performance tests
pytest tests/ -m slow -v

# Skip slow tests during development
pytest tests/ -m "not slow" -v
```

### Running GitHub Actions Locally (Pre-Push Validation)

**Before pushing to GitHub**, validate your changes locally using `act` to run GitHub Actions workflows in a Docker container. This catches issues before they fail in CI/CD.

> **⚠️ Prerequisites**: Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) to be installed and running.

#### 1. Install Act

```bash
# Windows (PowerShell as Administrator)
winget install nektos.act

# Or using Chocolatey
choco install act-cli

# Or using Scoop
scoop install act

# Verify installation (may need to restart shell)
act --version
```

#### 2. Create Fresh Test Environment

Always test in a clean virtual environment to match CI/CD conditions:

```bash
# Create fresh test environment
python -m venv .venv-test

# Windows
.\.venv-test\Scripts\Activate.ps1

# Linux/macOS  
source .venv-test/bin/activate

# Install dependencies
python -m pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"

# Run full test suite
pytest tests/ -v --cov=sentinel_log_aggregator --cov-report=html
```

#### 3. Run Workflows Locally

```bash
# List available workflows
act -l

# Run all workflows on push event
act push

# Run specific workflow
act push -W .github/workflows/ci-cd.yml

# Run security workflow
act push -W .github/workflows/security.yml

# Dry run (see what would execute)
act push -n

# Run specific job
act -j test

# Run with verbose output
act push -v
```

#### 4. Configuration

The project includes `.actrc` configuration (not committed to git):

```ini
# .actrc - Act configuration
-P ubuntu-latest=catthehacker/ubuntu:act-latest
--container-architecture linux/amd64
--bind
--container-daemon-socket -
```

#### 5. Pre-Push Checklist

Before pushing to GitHub, ensure:

- [ ] Fresh venv created and dependencies installed
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Coverage meets threshold (80%): `pytest --cov`
- [ ] Code formatted: `black sentinel_log_aggregator/ tests/`
- [ ] Imports sorted: `isort sentinel_log_aggregator/ tests/`
- [ ] Linting clean: `flake8 sentinel_log_aggregator/`
- [ ] Type checking: `mypy sentinel_log_aggregator/`
- [ ] Security scan: `bandit -r sentinel_log_aggregator/`
- [ ] Act workflows pass: `act push`

#### 6. Cleanup

```bash
# After validation, clean up test environment
deactivate
Remove-Item -Recurse -Force .venv-test  # Windows
rm -rf .venv-test  # Linux/macOS
```

#### Common Act Issues

**Docker not running:**
```bash
# Start Docker Desktop or Docker daemon
# Then retry act command
```

**Image pull failures:**
```bash
# Pull image manually
docker pull catthehacker/ubuntu:act-latest

# Or use smaller image
act push -P ubuntu-latest=node:16-buster-slim
```

**Permission issues (Linux/macOS):**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Code Organization

```
sentinel_log_aggregator/
├── __init__.py              # Package exports and public API
├── cli.py                   # Command-line interface
├── client_options.py        # Azure SDK-compliant configuration
├── exceptions.py            # Custom exception hierarchy
├── logging_utils.py         # Enhanced logging with correlation IDs
├── models.py               # Data models and query definitions
├── query_engine.py         # Core batch query execution
├── query_registry.py       # Centralized query management
├── responses.py            # Response models and status enums
├── security_utils.py       # Security validation and sanitization
├── sentinel_client.py      # Azure SDK-compliant client
├── validation.py           # Pydantic validation models
├── version.py             # Version information
└── workspace_manager.py   # Multi-workspace configuration
```

### Adding New Features

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/new-feature-name
   ```

2. **Write Tests First** (TDD approach)
   ```bash
   # Create test file
   touch tests/test_new_feature.py
   
   # Write failing tests
   pytest tests/test_new_feature.py -v
   ```

3. **Implement Feature**
   - Follow existing code patterns
   - Use type hints extensively
   - Add comprehensive docstrings
   - Include error handling

4. **Validate Implementation**
   ```bash
   # Run tests
   pytest tests/test_new_feature.py -v
   
   # Check coverage
   pytest tests/ --cov=sentinel_log_aggregator --cov-fail-under=80
   
   # Run all quality checks
   pre-commit run --all-files
   ```

5. **Create Pull Request**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   git push origin feature/new-feature-name
   ```

### Debugging

#### VS Code Configuration

The project includes VS Code configurations:

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "envFile": "${workspaceFolder}/.env"
        },
        {
            "name": "Python: CLI Debug",
            "type": "python",
            "request": "launch",
            "module": "sentinel_log_aggregator.cli",
            "args": ["--help"],
            "console": "integratedTerminal",
            "envFile": "${workspaceFolder}/.env"
        }
    ]
}
```

#### Logging Configuration

Enable debug logging during development:

```python
from sentinel_log_aggregator.logging_utils import configure_logging

configure_logging(level="DEBUG", enable_structured=True)
```

#### Azure SDK Logging

Enable Azure SDK debug logging:

```python
import logging
logging.getLogger('azure').setLevel(logging.DEBUG)
```

## CI/CD Pipeline

### GitHub Actions Workflow

The project uses GitHub Actions for CI/CD:

- **Test**: Runs on Python 3.8-3.11 with full test suite
- **Integration Test**: Runs integration tests with Azure credentials
- **Build**: Creates Python package and validates
- **Security Scan**: Trivy vulnerability scanning
- **Documentation**: Builds and deploys documentation
- **Release**: Publishes to PyPI on version tags

### Local CI Simulation

```bash
# Simulate CI pipeline locally
act -j test

# Run specific job
act -j security-scan
```

### Release Process

1. **Update Version**
   ```bash
   # Update version.py
   echo '__version__ = "1.2.3"' > sentinel_log_aggregator/version.py
   ```

2. **Create Release**
   ```bash
   git add .
   git commit -m "chore: bump version to 1.2.3"
   git tag v1.2.3
   git push origin main --tags
   ```

3. **Monitor Release**
   - GitHub Actions will automatically build and publish
   - Check PyPI for package availability
   - Verify documentation deployment

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Ensure package is installed in development mode
pip install -e .
```

#### Authentication Issues
```bash
# Login to Azure CLI
az login

# Set default subscription
az account set --subscription "your-subscription-id"
```

#### Test Failures
```bash
# Clear pytest cache
pytest --cache-clear

# Run specific failing test with verbose output
pytest tests/test_specific.py::test_function -vvs
```

#### Pre-commit Issues
```bash
# Update pre-commit hooks
pre-commit autoupdate

# Clean and reinstall
pre-commit clean
pre-commit install
```

### Performance Optimization

#### Memory Usage
- Use generators for large datasets
- Implement streaming uploads
- Clear variables after processing

#### Query Performance
- Use appropriate batch sizes
- Implement proper concurrency limits
- Monitor Azure throttling

#### Logging Performance
- Use structured logging
- Avoid excessive debug logging in production
- Implement log rotation

## Best Practices

### Security
- Never commit secrets or credentials
- Use Azure Key Vault for production secrets
- Validate all user inputs
- Sanitize log outputs

### Code Quality
- Write self-documenting code
- Use type hints extensively
- Follow Azure SDK patterns
- Implement comprehensive error handling

### Testing
- Aim for 90%+ test coverage
- Write both unit and integration tests
- Use proper mocking for external services
- Test error conditions

### Documentation
- Keep documentation up to date
- Include code examples
- Document configuration options
- Provide troubleshooting guides

## Additional Resources

- [Azure SDK for Python Guidelines](https://azure.github.io/azure-sdk/python_design.html)
- [Python Packaging Guide](https://packaging.python.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Microsoft Sentinel Documentation](https://docs.microsoft.com/en-us/azure/sentinel/)