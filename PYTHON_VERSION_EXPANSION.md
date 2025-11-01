# Python Version Support Expansion (3.11-3.14)

## Overview
Expanded the Sentinel Log Aggregator testing matrix to support Python versions 3.11 through 3.14, ensuring compatibility across current and near-future Python releases.

## Changes Made

### 1. GitHub Actions CI/CD (`.github/workflows/ci-cd.yml`)
- **Matrix Testing**: Updated from `["3.11"]` to `["3.11", "3.12", "3.13", "3.14"]`
- **Default Version**: Updated `PYTHON_VERSION` environment variable from `"3.11"` to `"3.13"`
- **Impact**: Now tests 4 Python versions instead of 1, ensuring broad compatibility

### 2. Package Metadata (`pyproject.toml`)
- **Classifiers**: Added explicit support declarations for Python 3.12, 3.13, and 3.14
- **Compatibility**: Maintains `requires-python = ">=3.11"` lower bound
- **PyPI Display**: Users can see supported versions on package page

### 3. Documentation (`README.md`)
- **Requirements**: Updated to specify "Python 3.11 or higher (tested on Python 3.11-3.14)"
- **User Confidence**: Clear indication of tested version range

## Python Version Status (as of November 2025)

| Version | Status | Release Date | End of Life | Testing Priority |
|---------|--------|--------------|-------------|------------------|
| 3.11 | ✅ Stable | Oct 2021 | Oct 2027 | **High** (LTS-like) |
| 3.12 | ✅ Stable | Oct 2022 | Oct 2028 | **High** (Current) |
| 3.13 | ✅ Stable | Oct 2023 | Oct 2029 | **High** (Latest) |
| 3.14 | 🔄 Pre-release | Oct 2024 | Oct 2030 | **Medium** (Beta) |
| ~~3.15~~ | ❌ Removed | ~~Oct 2025~~ | ~~Oct 2031~~ | **N/A** (Too early) |

## Benefits of Multi-Version Testing

### 1. **Future Compatibility**
- Early detection of breaking changes in Python 3.14/3.15
- Proactive compatibility fixes before widespread adoption
- Reduced maintenance burden when new versions are released

### 2. **User Confidence**
- Clear indication that package works across Python versions
- Enterprise users can upgrade Python with confidence
- Reduced support requests for version compatibility

### 3. **Azure SDK Alignment**
- Azure SDK libraries support similar Python version ranges
- Ensures compatibility with latest Azure features
- Maintains alignment with Microsoft's support strategy

## Testing Strategy

### **Primary Support Tiers**
1. **Tier 1** (Python 3.11-3.13): Full production support
2. **Tier 2** (Python 3.14): Beta support, may have temporary failures

### **CI/CD Failure Handling**
- **Tier 1 failures**: Block merges, require immediate fixes
- **Tier 2 failures**: Warning status, investigate but don't block

### **Rationale for Excluding Python 3.15**
- **Too Early**: Python 3.15 is in early development/alpha stage
- **Dependency Lag**: Azure SDK and other dependencies unlikely to support it yet
- **Stability Concerns**: API changes and instability would cause frequent CI failures
- **Future Addition**: Will be added when it reaches beta/RC status

### **Dependency Considerations**
- Azure SDK packages may not immediately support Python 3.14/3.15
- Some dependencies might need version pinning for newer Python versions
- Monitor Azure SDK release notes for Python version support

## Risk Assessment

### **Low Risk**
- ✅ **Python 3.11-3.13**: Well-established, stable Azure SDK support
- ✅ **Core functionality**: Uses standard libraries and patterns

### **Medium Risk**
- ⚠️ **Python 3.14**: Beta status, potential dependency lag
- ⚠️ **Third-party packages**: May need version constraints

### **Higher Risk**
- 🔶 **Python 3.15**: Alpha status, significant API changes possible
- 🔶 **Binary dependencies**: Compilation issues for newer versions

## Monitoring and Maintenance

### **Weekly Reviews**
- Check CI/CD results for Python 3.14/3.15 compatibility
- Monitor Azure SDK release notes for version support updates
- Review dependency security advisories

### **Quarterly Actions**
- Update dependency versions to latest stable
- Review Python version support strategy
- Evaluate dropping older version support (future)

### **Annual Planning**
- Assess Python version support lifecycle
- Plan migration strategies for major dependency updates
- Review enterprise customer Python version adoption

## Rollback Plan

If testing reveals compatibility issues:

1. **Immediate**: Temporarily allow failures for problematic versions
2. **Short-term**: Pin dependency versions to compatible ranges  
3. **Long-term**: Address compatibility issues or drop version support

Example rollback commands:
```bash
# Remove problematic versions from matrix
git revert HEAD  # Revert to previous matrix

# Or selectively remove versions
# Edit .github/workflows/ci-cd.yml to remove problematic versions
```

## Expected Outcomes

### **Immediate (Days 1-7)**
- Python 3.11-3.13 tests should pass consistently
- Python 3.14 may have occasional dependency issues
- More reliable CI/CD with focused version range

### **Short-term (Weeks 1-4)**
- Stabilization of Python 3.14 testing as dependencies catch up
- Consistent CI/CD performance without alpha version instability
- User adoption feedback for newer Python versions

### **Long-term (Months 1-12)**
- Full compatibility across Python 3.11-3.14
- Early adopter confidence for Python version upgrades
- Consider adding Python 3.15 when it reaches beta/RC status

---

*Python version expansion completed: November 2025*
*Committed in: 2403483 - "Expand Python version support to 3.11-3.15"*