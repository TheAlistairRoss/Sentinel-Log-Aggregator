#!/usr/bin/env python3
"""
Local build and development helper script for Sentinel Log Aggregator.
Provides easy commands for common development tasks.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌ {description} failed!")
        sys.exit(1)
    print(f"✅ {description} completed successfully!")


def clean():
    """Clean build artifacts and cache files."""
    print("🧹 Cleaning build artifacts...")
    
    # Remove build directories
    dirs_to_remove = [
        "build/",
        "dist/", 
        "*.egg-info/",
        ".pytest_cache/",
        ".mypy_cache/",
        "__pycache__/",
        "htmlcov/",
        "reports/"
    ]
    
    for pattern in dirs_to_remove:
        subprocess.run(f"rm -rf {pattern}", shell=True)
    
    # Remove cache files
    subprocess.run("find . -name '*.pyc' -delete", shell=True)
    subprocess.run("find . -name '*.pyo' -delete", shell=True)
    subprocess.run("find . -name '__pycache__' -type d -exec rm -rf {} +", shell=True)
    
    print("✅ Cleanup completed!")


def install_dev():
    """Install development dependencies."""
    run_command("pip install -e '.[dev,security,docs]'", "Installing development dependencies")


def format_code():
    """Format code with black and isort."""
    run_command("black sentinel_log_aggregator/ tests/ scripts/", "Formatting code with black")
    run_command("isort sentinel_log_aggregator/ tests/ scripts/", "Sorting imports with isort")


def lint():
    """Run linting checks."""
    run_command("flake8 sentinel_log_aggregator/ tests/", "Running flake8 linting")
    run_command("mypy sentinel_log_aggregator/", "Running mypy type checking")


def test():
    """Run the test suite."""
    run_command("pytest tests/ -v --cov=sentinel_log_aggregator --cov-report=html --cov-report=term", 
                "Running test suite")


def security():
    """Run security scans."""
    run_command("python run_security_scan.py", "Running comprehensive security scan")


def build():
    """Build the package."""
    clean()
    run_command("python -m build", "Building package")
    
    # Validate the build
    run_command("twine check dist/*", "Validating package")
    
    print("\n📦 Package built successfully!")
    print("📁 Artifacts available in: dist/")


def docs():
    """Build documentation."""
    run_command("sphinx-build -b html docs/ docs/_build/html", "Building documentation")
    print("📚 Documentation built in: docs/_build/html/")


def pre_commit_install():
    """Install pre-commit hooks."""
    run_command("pre-commit install", "Installing pre-commit hooks")


def pre_commit_run():
    """Run pre-commit hooks on all files."""
    run_command("pre-commit run --all-files", "Running pre-commit hooks")


def check():
    """Run all checks (format, lint, test, security)."""
    format_code()
    lint()
    test()
    security()
    print("\n🎉 All checks passed!")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="Sentinel Log Aggregator Development Helper")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Add subcommands
    subparsers.add_parser("clean", help="Clean build artifacts and cache files")
    subparsers.add_parser("install-dev", help="Install development dependencies")
    subparsers.add_parser("format", help="Format code with black and isort")
    subparsers.add_parser("lint", help="Run linting checks")
    subparsers.add_parser("test", help="Run the test suite")
    subparsers.add_parser("security", help="Run security scans")
    subparsers.add_parser("build", help="Build the package")
    subparsers.add_parser("docs", help="Build documentation")
    subparsers.add_parser("pre-commit-install", help="Install pre-commit hooks")
    subparsers.add_parser("pre-commit-run", help="Run pre-commit hooks on all files")
    subparsers.add_parser("check", help="Run all checks (format, lint, test, security)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Map commands to functions
    commands = {
        "clean": clean,
        "install-dev": install_dev,
        "format": format_code,
        "lint": lint,
        "test": test,
        "security": security,
        "build": build,
        "docs": docs,
        "pre-commit-install": pre_commit_install,
        "pre-commit-run": pre_commit_run,
        "check": check,
    }
    
    if args.command in commands:
        commands[args.command]()
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()