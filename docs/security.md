# Security Policy

## Supported Versions

This open-source project provides security updates for the following versions:

| Version | Supported          | Python Versions |
| ------- | ------------------ | --------------- |
| 1.x.x   | ✅ Fully supported | 3.8, 3.9, 3.10, 3.11 |
| 0.x.x   | ❌ No longer supported | - |

## Security Standards

This project follows Microsoft's Security Development Lifecycle (SDL) and implements:

- **Static Application Security Testing (SAST)**: Bandit, Semgrep, CodeQL
- **Software Composition Analysis (SCA)**: Safety, pip-audit, dependency review
- **Secrets Detection**: TruffleHog, detect-secrets
- **Infrastructure Security**: Trivy scanning
- **Regular Security Scans**: Automated weekly security assessments

## Reporting a Vulnerability

### For High-Severity Vulnerabilities (Recommended)

Please use GitHub's private vulnerability reporting for sensitive security issues:

1. Go to the [Security tab](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/security) of this repository
2. Click "Report a vulnerability"
3. Fill out the private advisory form
4. Submit your report

This ensures the vulnerability is handled privately until a fix is available.

### For Lower-Severity Issues

For security improvements, questions, or lower-severity issues, you can:

1. Create a [security issue](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/issues/new?template=security_issue.yml) using our template
2. Email: [security contact if you have one]
3. Start a [GitHub Discussion](https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/discussions) for security questions

### What to Include

When reporting a vulnerability, please include:

- **Description**: Clear description of the vulnerability
- **Impact**: Potential impact and attack scenarios
- **Reproduction**: Step-by-step instructions to reproduce
- **Environment**: Affected versions, Python versions, deployment context
- **Proof of Concept**: Code snippets or examples (if safe to share)
- **Suggested Fix**: If you have recommendations

### Response Timeline

We aim to respond to security reports within:

- **Critical vulnerabilities**: 24 hours
- **High severity**: 3 business days  
- **Medium/Low severity**: 7 business days
- **Security improvements**: 14 business days

### Security Update Process

1. **Acknowledgment**: We'll acknowledge receipt of your report
2. **Investigation**: We'll investigate and validate the issue
3. **Fix Development**: We'll develop and test a fix
4. **Coordinated Disclosure**: We'll work with you on disclosure timing
5. **Release**: We'll release the fix and security advisory
6. **Credit**: We'll acknowledge your contribution (if desired)

## Security Best Practices for Users

### Authentication
- **Use Managed Identity** when running in Azure (recommended)
- **Use Azure CLI** for local development (`az login`)
- **Use Service Principal** for CI/CD with proper secret management
- **Never hardcode credentials** in configuration files

### Configuration Security
- Store sensitive configuration in Azure Key Vault
- Use environment variables for secrets (not configuration files)
- Validate all configuration inputs
- Use least-privilege access principles

### Azure Integration Security
- Ensure proper RBAC permissions on Sentinel workspaces
- Use Data Collection Rule (DCR) endpoints with proper authentication
- Monitor access logs and audit trails
- Implement network security controls where applicable

### Deployment Security
- Keep dependencies updated (use Dependabot alerts)
- Scan container images if using containerized deployment
- Follow Azure security baselines for hosting services
- Implement proper logging and monitoring

## Security Scanning Tools

This project includes comprehensive security scanning:

### Continuous Scanning
- **Pre-commit hooks**: Security checks before each commit
- **CI/CD pipeline**: Security validation on every push/PR
- **Weekly scans**: Automated security assessments
- **Dependency monitoring**: Continuous vulnerability tracking

### Tools Integrated
- **Bandit**: Python security linter
- **Safety**: Python package vulnerability database
- **pip-audit**: PyPI security advisory database
- **Semgrep**: Static analysis security tool
- **CodeQL**: GitHub's semantic code analysis
- **TruffleHog**: Secrets detection
- **Trivy**: Vulnerability scanner
- **detect-secrets**: Baseline secrets detection

## Vulnerability Disclosure Policy

We follow responsible disclosure principles:

1. **Private Reporting**: Use private channels for sensitive issues
2. **Coordinated Timeline**: Work together on disclosure timing
3. **Public Disclosure**: After fixes are available and deployed
4. **Attribution**: Credit researchers who report issues responsibly

## Security Contact

For urgent security matters or if you need to reach us securely:

- **GitHub Security Advisories**: Preferred method
- **GitHub Issues**: For non-sensitive security topics
- **Project Maintainer**: @TheAlistairRoss

## Legal

This security policy is provided in good faith. We appreciate responsible disclosure and will work with security researchers to address legitimate security concerns.

---

*Last updated: [Current Date]*
*This policy may be updated periodically - please check for the latest version.*