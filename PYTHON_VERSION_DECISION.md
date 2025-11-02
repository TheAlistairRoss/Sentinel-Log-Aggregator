# Python Version Support Decision

## Current Status
**Supported Python Version**: 3.11 only

## Background
As of November 2, 2025, the project has been updated to support only Python 3.11 to resolve CI/CD compatibility issues and maintain stability.

## Changes Made
1. **CI/CD Workflow**: Updated test matrix to only test Python 3.11
2. **Package Metadata**: Updated `pyproject.toml` classifiers to only list Python 3.11
3. **Requirements**: Updated comments to reflect Python 3.11 only requirement
4. **Black Configuration**: Already configured for Python 3.11 target

## Rationale
- **Stability**: Python 3.11 is well-supported across all Azure SDK packages
- **CI/CD Reliability**: Eliminates compatibility issues with newer Python versions
- **Maintenance**: Reduces testing overhead and version-specific bug fixing
- **Azure SDK Compatibility**: Python 3.11 has excellent support in Azure ecosystem

## Future Considerations
- Monitor Azure SDK and dependency support for Python 3.12/3.13
- Consider re-adding newer Python versions when ecosystem is fully compatible
- Evaluate community demand for newer Python version support

## Files Updated
- `.github/workflows/ci-cd.yml` - Test matrix simplified to Python 3.11 only
- `pyproject.toml` - Removed Python 3.12, 3.13, 3.14 classifiers
- `requirements.txt` - Updated comment to reflect Python 3.11 requirement

This decision prioritizes stability and reliability over cutting-edge Python version support.