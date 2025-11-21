#!/usr/bin/env python3
"""
Local security scanning script for Sentinel Log Aggregator
Runs comprehensive security analysis tools aligned with Microsoft SDL
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def run_command(cmd: List[str], description: str) -> Tuple[bool, str]:
    """Run a command and return success status and output."""
    print(f"\n🔍 Running {description}...")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=Path(__file__).parent, timeout=300
        )

        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True, result.stdout
        else:
            print(f"❌ {description} failed with return code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False, result.stderr

    except subprocess.TimeoutExpired:
        print(f"⏰ {description} timed out after 5 minutes")
        return False, "Timeout"
    except Exception as e:
        print(f"💥 {description} failed with exception: {e}")
        return False, str(e)


def check_tool_installed(tool: str) -> bool:
    """Check if a security tool is installed."""
    try:
        subprocess.run([tool, "--version"], capture_output=True, timeout=10)
        return True
    except:
        return False


def install_security_tools():
    """Install required security tools."""
    print("📦 Installing security tools...")

    tools = ["bandit[toml]", "safety", "pip-audit", "semgrep", "detect-secrets", "pip-licenses"]

    for tool in tools:
        success, _ = run_command(
            [sys.executable, "-m", "pip", "install", tool], f"Installing {tool}"
        )
        if not success:
            print(f"⚠️  Failed to install {tool}")


def run_bandit() -> Dict:
    """Run Bandit security scanner."""
    success, output = run_command(
        [
            "bandit",
            "-r",
            "sentinel_log_aggregator/",
            "-f",
            "json",
            "-o",
            "reports/bandit-report.json",
        ],
        "Bandit SAST scan",
    )

    # Also run with console output
    run_command(
        ["bandit", "-r", "sentinel_log_aggregator/", "--severity-level", "medium"],
        "Bandit console output",
    )

    return {"tool": "bandit", "success": success, "report": "reports/bandit-report.json"}


def run_safety() -> Dict:
    """Run Safety dependency vulnerability scanner."""
    success, output = run_command(
        ["safety", "check", "--json", "--output", "reports/safety-report.json"],
        "Safety dependency scan",
    )

    # Also run with console output
    run_command(["safety", "check", "--short-report"], "Safety console output")

    return {"tool": "safety", "success": success, "report": "reports/safety-report.json"}


def run_pip_audit() -> Dict:
    """Run pip-audit official Python security auditor."""
    success, output = run_command(
        ["pip-audit", "--format=json", "--output=reports/pip-audit-report.json"],
        "pip-audit security scan",
    )

    # Also run with console output
    run_command(["pip-audit", "--desc"], "pip-audit console output")

    return {"tool": "pip-audit", "success": success, "report": "reports/pip-audit-report.json"}


def run_semgrep() -> Dict:
    """Run Semgrep advanced static analysis."""
    success, output = run_command(
        [
            "semgrep",
            "--config=auto",
            "--json",
            "--output=reports/semgrep-report.json",
            "sentinel_log_aggregator/",
        ],
        "Semgrep SAST scan",
    )

    return {"tool": "semgrep", "success": success, "report": "reports/semgrep-report.json"}


def run_detect_secrets() -> Dict:
    """Run detect-secrets for secrets scanning."""
    # Create baseline if it doesn't exist
    if not os.path.exists(".secrets.baseline"):
        run_command(
            ["detect-secrets", "scan", "--baseline", ".secrets.baseline"],
            "Creating secrets baseline",
        )

    success, output = run_command(
        ["detect-secrets", "scan", "--baseline", ".secrets.baseline", "--force-use-all-plugins"],
        "Secrets detection scan",
    )

    return {"tool": "detect-secrets", "success": success, "report": ".secrets.baseline"}


def run_license_check() -> Dict:
    """Check license compliance."""
    success, output = run_command(
        ["pip-licenses", "--format=json", "--output-file=reports/licenses.json"],
        "License compliance check",
    )

    # Also run summary
    run_command(["pip-licenses", "--summary"], "License summary")

    return {"tool": "pip-licenses", "success": success, "report": "reports/licenses.json"}


def generate_summary_report(results: List[Dict]):
    """Generate a summary security report."""
    print("\n" + "=" * 60)
    print("🛡️  SECURITY SCAN SUMMARY REPORT")
    print("=" * 60)

    total_scans = len(results)
    successful_scans = sum(1 for r in results if r["success"])

    print(f"\n📊 Overall Status: {successful_scans}/{total_scans} scans completed successfully")

    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['tool']:<15} - Report: {result['report']}")

    print(f"\n📁 All reports saved in: {Path.cwd() / 'reports'}")

    # Count issues if possible
    try:
        if os.path.exists("reports/bandit-report.json"):
            with open("reports/bandit-report.json") as f:
                bandit_data = json.load(f)
                issue_count = len(bandit_data.get("results", []))
                print(f"   • Bandit found {issue_count} potential security issues")

        if os.path.exists("reports/safety-report.json"):
            with open("reports/safety-report.json") as f:
                safety_data = json.load(f)
                vuln_count = len(safety_data.get("report", {}).get("vulnerabilities", []))
                print(f"   • Safety found {vuln_count} known vulnerabilities")

    except Exception as e:
        print(f"   ⚠️  Could not parse some reports: {e}")

    print("\n💡 Next steps:")
    print("   1. Review detailed reports in the 'reports/' directory")
    print("   2. Address any HIGH or CRITICAL severity findings")
    print("   3. Update .bandit and .safety-policy files to ignore false positives")
    print("   4. Run 'pre-commit run --all-files' to validate fixes")


def main():
    """Main security scanning orchestrator."""
    print("🔒 Starting Microsoft SDL Security Analysis")
    print("=" * 50)

    # Create reports directory
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    # Check if we're in the right directory
    if not Path("sentinel_log_aggregator").exists():
        print("❌ Please run this script from the project root directory")
        sys.exit(1)

    # Install tools if needed
    if not all(check_tool_installed(tool) for tool in ["bandit", "safety", "pip-audit"]):
        install_security_tools()

    # Run all security scans
    results = []

    # Core security scans aligned with Microsoft SDL
    security_scans = [
        ("Static Application Security Testing", run_bandit),
        ("Dependency Vulnerability Scanning", run_safety),
        ("Python Security Auditing", run_pip_audit),
        ("Advanced Static Analysis", run_semgrep),
        ("Secrets Detection", run_detect_secrets),
        ("License Compliance", run_license_check),
    ]

    for scan_name, scan_func in security_scans:
        print(f"\n{'='*20} {scan_name} {'='*20}")
        try:
            result = scan_func()
            results.append(result)
        except Exception as e:
            print(f"💥 Failed to run {scan_name}: {e}")
            results.append({"tool": scan_name, "success": False, "report": "N/A"})

    # Generate summary
    generate_summary_report(results)

    # Return appropriate exit code
    failed_scans = [r for r in results if not r["success"]]
    if failed_scans:
        print(f"\n⚠️  {len(failed_scans)} security scans failed or found issues")
        sys.exit(1)
    else:
        print("\n🎉 All security scans completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
