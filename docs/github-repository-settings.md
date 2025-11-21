# GitHub Repository Settings Configuration Guide

This document provides step-by-step instructions for configuring your GitHub repository settings to align with enterprise security standards and best practices for the Microsoft Sentinel Log Aggregator project.

## 🔧 Repository Settings Configuration

### 1. General Settings

Navigate to **Settings** → **General**

#### Repository Details
- **Description**: "Azure SDK-compliant Python client library for aggregating logs from multiple Microsoft Sentinel workspaces"
- **Website**: `https://thealistairross.github.io/Sentinel-Log-Aggregator/`
- **Topics**: Add relevant topics:
  ```
  microsoft-sentinel, azure, security-analytics, log-aggregation, 
  python, azure-sdk, cybersecurity, siem, kql, azure-monitor
  ```

#### Features
- ✅ **Wikis**: Disabled (using docs/ directory)
- ✅ **Issues**: Enabled
- ✅ **Sponsorships**: Optional
- ✅ **Preserving this repository**: Disabled
- ✅ **Discussions**: Enabled (recommended for community)

#### Pull Requests
- ✅ **Allow merge commits**: Enabled
- ✅ **Allow squash merging**: Enabled (recommended)
- ✅ **Allow rebase merging**: Enabled
- ✅ **Always suggest updating pull request branches**: Enabled
- ✅ **Allow auto-merge**: Enabled
- ✅ **Automatically delete head branches**: Enabled

### 2. Security Settings

Navigate to **Settings** → **Security**

#### Security Features
- ✅ **Dependency graph**: Enabled
- ✅ **Dependabot alerts**: Enabled
- ✅ **Dependabot security updates**: Enabled
- ✅ **Dependabot version updates**: Enabled (configure schedule)
- ✅ **Code scanning**: Enabled
- ✅ **Secret scanning**: Enabled
- ✅ **Secret scanning push protection**: Enabled

#### Private Vulnerability Reporting
- ✅ **Enable private vulnerability reporting**: Enabled

### 3. Branch Protection Rules

Navigate to **Settings** → **Branches**

#### Main Branch Protection Rules
Create a rule for `main` branch:

```yaml
Branch name pattern: main

Protect matching branches:
✅ Restrict pushes that create files larger than 100MB
✅ Require a pull request before merging
  - Required approving reviews: 1
  - ✅ Dismiss stale pull request approvals when new commits are pushed
  - ✅ Require review from code owners
  - ❌ Restrict reviews to users with push access
  - ❌ Allow specified actors to bypass required pull requests

✅ Require status checks to pass before merging
  - ✅ Require branches to be up to date before merging
  - Required status checks:
    - test (3.8)
    - test (3.9)
    - test (3.10) 
    - test (3.11)
    - security-comprehensive
    - codeql
    - build
    - security-scan

✅ Require signed commits
✅ Require linear history
✅ Include administrators
❌ Allow force pushes (Everyone)
❌ Allow deletions
```

#### Develop Branch Protection Rules
Create a rule for `develop` branch:

```yaml
Branch name pattern: develop

Protect matching branches:
✅ Restrict pushes that create files larger than 100MB
✅ Require a pull request before merging
  - Required approving reviews: 1
  - ✅ Dismiss stale pull request approvals when new commits are pushed
  - ❌ Require review from code owners (more flexible for development)

✅ Require status checks to pass before merging
  - Required status checks:
    - test (3.8)
    - test (3.9)
    - test (3.10)
    - test (3.11)
    - security-comprehensive

❌ Require signed commits (optional for development)
❌ Require linear history (allow merge commits in develop)
✅ Include administrators
✅ Allow force pushes (Administrators only)
❌ Allow deletions
```

### 4. Actions Settings

Navigate to **Settings** → **Actions** → **General**

#### Actions Permissions
```yaml
Actions permissions:
◉ Allow all actions and reusable workflows

Fork pull request workflows:
✅ Run workflows from fork pull requests
◉ Require approval for first-time contributors who are new to GitHub
```

#### Workflow Permissions
```yaml
Workflow permissions:
◉ Read repository contents and metadata permissions

✅ Allow GitHub Actions to create and approve pull requests: NO
```

#### Artifact and Log Retention
```yaml
Artifact and log retention: 90 days (default)
```

### 5. Pages Settings

Navigate to **Settings** → **Pages**

#### GitHub Pages Configuration
```yaml
Source: Deploy from a branch
Branch: gh-pages / (root)
Custom domain: (optional)
✅ Enforce HTTPS: Enabled
```

### 6. Environments

Navigate to **Settings** → **Environments**

#### Production Environment
Create environment named `production`:

```yaml
Environment name: production

Protection rules:
✅ Required reviewers: [TheAlistairRoss]
✅ Wait timer: 0 minutes
✅ Required branches: main

Environment secrets:
- PYPI_API_TOKEN (for PyPI publishing)
- TEST_PYPI_API_TOKEN (for test PyPI)
```

#### Development Environment
Create environment named `development`:

```yaml
Environment name: development

Protection rules:
❌ Required reviewers: (no restrictions)
❌ Wait timer: (no restrictions)
✅ Required branches: develop, main

Environment secrets:
- TEST_AZURE_SUBSCRIPTION_ID
- TEST_AZURE_CLIENT_ID (if needed)
```

### 7. Webhooks and Services

Navigate to **Settings** → **Webhooks**

Consider adding webhooks for:
- **Slack notifications** (for team collaboration)
- **Security monitoring tools** (if using external tools)
- **Project management integration** (Azure DevOps, Jira, etc.)

### 8. Repository Secrets

Navigate to **Settings** → **Secrets and variables** → **Actions**

#### Repository Secrets
Configure the following secrets:

```yaml
Required Secrets:
- PYPI_API_TOKEN: PyPI publishing token
- TEST_PYPI_API_TOKEN: Test PyPI publishing token

Optional Secrets (for enhanced integration):
- AZURE_CLIENT_ID: Service principal for integration tests
- AZURE_CLIENT_SECRET: Service principal secret
- AZURE_TENANT_ID: Azure tenant ID
- CODECOV_TOKEN: Code coverage reporting
```

#### Repository Variables
Configure the following variables:

```yaml
Variables:
- PYTHON_VERSION: "3.11"
- TEST_COVERAGE_THRESHOLD: "95"
- SECURITY_SCAN_SCHEDULE: "0 2 * * 1"
```

### 9. Dependabot Configuration

Create `.github/dependabot.yml`:

```yaml
version: 2
updates:
  # Python dependencies
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "04:00"
    open-pull-requests-limit: 10
    reviewers:
      - "TheAlistairRoss"
    commit-message:
      prefix: "deps"
      include: "scope"

  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "04:00"
    open-pull-requests-limit: 5
    reviewers:
      - "TheAlistairRoss"
    commit-message:
      prefix: "ci"
      include: "scope"
```

## 🔍 Verification Checklist

After configuring all settings, verify the following:

### Security Verification
- [ ] Security tab shows active scanning
- [ ] Branch protection rules are enforced
- [ ] Secret scanning is detecting test secrets
- [ ] Dependabot alerts are visible
- [ ] Code scanning results appear in Security tab

### Workflow Verification
- [ ] CI/CD workflow triggers correctly
- [ ] Security workflow runs on schedule
- [ ] Branch protection blocks merges without required checks
- [ ] Pull request template appears correctly
- [ ] Issue templates are available

### Documentation Verification
- [ ] GitHub Pages deploys successfully
- [ ] SECURITY.md appears in Security tab
- [ ] CODEOWNERS enforces review requirements
- [ ] All links in templates work correctly

### Integration Verification
- [ ] PyPI publishing works (test with pre-release)
- [ ] Coverage reporting integrates properly
- [ ] Security scans upload SARIF results
- [ ] Artifacts are created and stored correctly

## 🚀 Additional Recommendations

### Repository Insights
Configure **Insights** → **Community Standards**:
- All recommended files should show ✅ (green checkmarks)
- Community profile should be 100% complete

### Labels Management
Navigate to **Issues** → **Labels** and ensure these labels exist:
- `bug`, `enhancement`, `documentation`, `security`
- `triage`, `workflow`, `dependencies`, `breaking-change`
- `good first issue`, `help wanted`, `question`
- `priority-high`, `priority-medium`, `priority-low`

### Milestones and Projects
Consider creating:
- **Milestones** for version releases (v1.0.0, v1.1.0, etc.)
- **Projects** for feature tracking and roadmap management

### Notifications
Configure personal notification preferences:
- Watch the repository for all activity
- Enable email notifications for security alerts
- Set up mobile notifications for critical issues

---

This configuration ensures your repository follows enterprise security standards, provides excellent developer experience, and integrates seamlessly with your comprehensive CI/CD and security workflows.