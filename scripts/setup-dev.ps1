# Development Environment Setup Script for Windows PowerShell
# This script automates the initial setup of the development environment

param(
    [switch]$SkipVenv,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Setting up Sentinel Log Aggregator development environment..." -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "📋 Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.11 or higher from https://www.python.org/" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Found: $pythonVersion" -ForegroundColor Green

# Check if Python version is 3.11+
$versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
$majorVersion = [int]$matches[1]
$minorVersion = [int]$matches[2]

if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 11)) {
    Write-Host "❌ Python 3.11 or higher is required (found $pythonVersion)" -ForegroundColor Red
    exit 1
}

# Create virtual environment
if (-not $SkipVenv) {
    if (Test-Path ".venv") {
        Write-Host "⚠️  Virtual environment already exists at .venv" -ForegroundColor Yellow
        $response = Read-Host "Do you want to recreate it? (y/N)"
        if ($response -eq "y" -or $response -eq "Y") {
            Write-Host "🗑️  Removing existing virtual environment..." -ForegroundColor Yellow
            Remove-Item -Recurse -Force .venv
        } else {
            Write-Host "✅ Using existing virtual environment" -ForegroundColor Green
            $SkipVenv = $true
        }
    }
    
    if (-not $SkipVenv) {
        Write-Host "📦 Creating virtual environment..." -ForegroundColor Yellow
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
            exit 1
        }
        Write-Host "✅ Virtual environment created" -ForegroundColor Green
    }
}

# Activate virtual environment
Write-Host "🔄 Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to activate virtual environment" -ForegroundColor Red
    Write-Host "Try running: .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Virtual environment activated" -ForegroundColor Green

# Upgrade pip and install build tools
Write-Host "⬆️  Upgrading pip and build tools..." -ForegroundColor Yellow
python -m pip install --upgrade pip setuptools wheel | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to upgrade pip" -ForegroundColor Red
    exit 1
}
Write-Host "✅ pip, setuptools, and wheel upgraded" -ForegroundColor Green

# Install package in development mode with all optional dependencies
Write-Host "📦 Installing package with development dependencies..." -ForegroundColor Yellow
Write-Host "   This may take a few minutes on first run..." -ForegroundColor Cyan
pip install -e ".[dev,security,docs]" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Package and dependencies installed" -ForegroundColor Green

# Install pre-commit hooks
Write-Host "🪝 Installing pre-commit hooks..." -ForegroundColor Yellow
pre-commit install | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install pre-commit hooks" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Pre-commit hooks installed" -ForegroundColor Green

# Install commit message hooks
Write-Host "🪝 Installing commit message hooks..." -ForegroundColor Yellow
pre-commit install --hook-type commit-msg | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Failed to install commit-msg hooks (optional)" -ForegroundColor Yellow
} else {
    Write-Host "✅ Commit message hooks installed" -ForegroundColor Green
}

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "📝 Creating .env template..." -ForegroundColor Yellow
    @"
# Azure Configuration (for development/testing)
DCR_LOGS_INGESTION_ENDPOINT=https://your-dcr-endpoint.monitor.azure.com
DCR_IMMUTABLE_ID=dcr-your-immutable-id

# Development Settings
LOG_LEVEL=DEBUG
MAX_CONCURRENT_QUERIES=3
QUERY_TIMEOUT_SECONDS=300

# Test Configuration (optional)
# AZURE_SUBSCRIPTION_ID=your-test-subscription-id
# AZURE_TENANT_ID=your-tenant-id
"@ | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✅ .env template created (please update with your values)" -ForegroundColor Green
} else {
    Write-Host "✅ .env file already exists" -ForegroundColor Green
}

# Run initial tests (optional)
if (-not $SkipTests) {
    Write-Host ""
    Write-Host "🧪 Running initial tests to verify setup..." -ForegroundColor Yellow
    pytest tests/ -v --tb=short -x
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Some tests failed (this may be normal if Azure credentials aren't configured)" -ForegroundColor Yellow
    } else {
        Write-Host "✅ All tests passed!" -ForegroundColor Green
    }
}

# Summary
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  ✨ Development Environment Setup Complete! ✨               ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Update .env file with your Azure configuration" -ForegroundColor White
Write-Host "  2. Run tests: " -NoNewline -ForegroundColor White
Write-Host "pytest tests/ -v" -ForegroundColor Cyan
Write-Host "  3. Format code: " -NoNewline -ForegroundColor White
Write-Host "python scripts/dev.py format" -ForegroundColor Cyan
Write-Host "  4. Run all checks: " -NoNewline -ForegroundColor White
Write-Host "python scripts/dev.py check" -ForegroundColor Cyan
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  • Activate venv: " -NoNewline -ForegroundColor White
Write-Host ".\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "  • Run pre-commit: " -NoNewline -ForegroundColor White
Write-Host "pre-commit run --all-files" -ForegroundColor Cyan
Write-Host "  • Help: " -NoNewline -ForegroundColor White
Write-Host "python scripts/dev.py --help" -ForegroundColor Cyan
Write-Host ""
Write-Host "📚 Documentation: docs/development.md" -ForegroundColor Cyan
Write-Host ""
