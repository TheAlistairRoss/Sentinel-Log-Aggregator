## 📋 Pull Request Checklist

Thank you for contributing to the Microsoft Sentinel Log Aggregator! Please ensure your pull request meets the following requirements:

### Pre-submission Requirements
- [ ] I have read the [Contributing Guidelines](../README.md#contributing)
- [ ] I have reviewed the [Workflow Documentation](../docs/workflows.md)
- [ ] My code follows the project's coding standards
- [ ] I have tested my changes locally

### Code Quality Requirements
- [ ] All tests pass (`pytest tests/`)
- [ ] Code coverage meets requirements (>95%)
- [ ] Security scans pass (no high/critical vulnerabilities)
- [ ] Code is formatted with Black and isort
- [ ] Type checking passes with MyPy
- [ ] Pre-commit hooks pass

### Security Requirements
- [ ] No hardcoded secrets or credentials
- [ ] Security tools (Bandit, Safety, pip-audit) pass
- [ ] Changes follow security best practices
- [ ] Sensitive data is properly handled

### Documentation Requirements
- [ ] Code is documented with docstrings (Google style)
- [ ] Public APIs have comprehensive documentation
- [ ] README.md updated if needed
- [ ] Changelog updated for user-facing changes (docs/changelog.md)

## 📝 Pull Request Details

### Change Type
<!-- Mark the type of change -->
- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] 🚀 New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that breaks existing functionality)
- [ ] 📖 Documentation update
- [ ] 🔧 Maintenance/refactoring
- [ ] 🔒 Security improvement
- [ ] ⚡ Performance improvement

### Description
<!-- Provide a clear and concise description of what this PR does -->

### Related Issues
<!-- Link to related issues using keywords like "Fixes #123" or "Addresses #456" -->

### Changes Made
<!-- List the main changes made in this PR -->
- 
- 
- 

### Testing Performed
<!-- Describe the testing you performed -->
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed
- [ ] Tested with different Python versions
- [ ] Tested with Azure services

### Breaking Changes
<!-- If this is a breaking change, describe what breaks and how to migrate -->
- [ ] This PR introduces breaking changes
- [ ] Migration guide provided
- [ ] Version bump required

### Screenshots/Output
<!-- If applicable, add screenshots or example output -->

## 🔍 Review Focus Areas

Please pay special attention to the following areas during review:

- [ ] Security implications
- [ ] Performance impact
- [ ] API design consistency
- [ ] Error handling
- [ ] Azure integration patterns
- [ ] Documentation completeness

## 📊 Performance Impact

<!-- If applicable, describe any performance implications -->
- [ ] No performance impact expected
- [ ] Performance improvements included
- [ ] Performance impact assessed and acceptable
- [ ] Performance tests included

## 🚀 Post-merge Tasks

<!-- List any tasks that need to be completed after merging -->
- [ ] Update deployment documentation
- [ ] Create/update examples
- [ ] Announce breaking changes
- [ ] Update related repositories

---

**For maintainers:**
- [ ] Branch protection rules satisfied
- [ ] All CI/CD checks pass
- [ ] Security scans clean
- [ ] Documentation builds successfully
- [ ] Ready for merge