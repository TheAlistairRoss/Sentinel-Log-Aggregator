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
# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Install Development Tools

```bash
# Install pre-commit hooks
pre-commit install

# Install commitizen for conventional commits
pip install commitizen

# Verify installation
pre-commit --version
cz version
```

### 3. Configure Environment

Create a `.env` file in the project root:

```bash
# Azure Configuration (for development/testing)
DCR_LOGS_INGESTION_ENDPOINT=https://your-dcr-endpoint.monitor.azure.com
DCR_RULE_ID=dcr-your-rule-id

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
# Run code quality checks
black --check sentinel_log_aggregator/ tests/
isort --check-only sentinel_log_aggregator/ tests/
flake8 sentinel_log_aggregator/ tests/
mypy sentinel_log_aggregator/

# Run security checks
bandit -r sentinel_log_aggregator/

# Run tests
pytest tests/ -v --cov=sentinel_log_aggregator
```

## Development Workflow

### Code Quality Standards

The project enforces strict code quality standards:

- **Formatting**: Black with 100-character line limit
- **Import Sorting**: isort with Black profile
- **Linting**: flake8 with additional plugins
- **Type Checking**: mypy with strict optional
- **Security**: Bandit security scanner
- **Testing**: pytest with minimum 80% coverage

### Pre-commit Hooks

Pre-commit hooks automatically run on every commit:

```bash
# Manual pre-commit run
pre-commit run --all-files

# Skip pre-commit for emergency commits (not recommended)
git commit --no-verify -m "emergency fix"
```

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