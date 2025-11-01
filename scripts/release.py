#!/usr/bin/env python3
"""
Version management and release script for Sentinel Log Aggregator.
Automates version bumping, changelog updates, and release preparation.
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


def get_current_version() -> str:
    """Get the current version from version.py."""
    version_file = Path("sentinel_log_aggregator/version.py")
    with open(version_file, "r") as f:
        content = f.read()

    match = re.search(r'__version__ = "([^"]+)"', content)
    if not match:
        raise ValueError("Could not find version in version.py")

    return match.group(1)


def parse_version(version: str) -> Tuple[int, int, int, Optional[str]]:
    """Parse a semantic version string."""
    pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-\.]+))?$"
    match = re.match(pattern, version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")

    major, minor, patch, pre_release = match.groups()
    return int(major), int(minor), int(patch), pre_release


def bump_version(current_version: str, bump_type: str) -> str:
    """Bump version according to semantic versioning."""
    major, minor, patch, pre_release = parse_version(current_version)

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    elif bump_type == "alpha":
        if pre_release and "alpha" in pre_release:
            # Bump alpha version
            alpha_match = re.search(r"alpha\.(\d+)", pre_release)
            if alpha_match:
                alpha_num = int(alpha_match.group(1)) + 1
            else:
                alpha_num = 2
        else:
            alpha_num = 1
        return f"{major}.{minor}.{patch + 1}-alpha.{alpha_num}"
    elif bump_type == "beta":
        if pre_release and "beta" in pre_release:
            # Bump beta version
            beta_match = re.search(r"beta\.(\d+)", pre_release)
            if beta_match:
                beta_num = int(beta_match.group(1)) + 1
            else:
                beta_num = 2
        else:
            beta_num = 1
        return f"{major}.{minor}.{patch + 1}-beta.{beta_num}"
    elif bump_type == "rc":
        if pre_release and "rc" in pre_release:
            # Bump RC version
            rc_match = re.search(r"rc\.(\d+)", pre_release)
            if rc_match:
                rc_num = int(rc_match.group(1)) + 1
            else:
                rc_num = 2
        else:
            rc_num = 1
        return f"{major}.{minor}.{patch + 1}-rc.{rc_num}"
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")


def update_version_file(new_version: str):
    """Update the version in version.py."""
    version_file = Path("sentinel_log_aggregator/version.py")
    with open(version_file, "r") as f:
        content = f.read()

    new_content = re.sub(r'__version__ = "[^"]+"', f'__version__ = "{new_version}"', content)

    with open(version_file, "w") as f:
        f.write(new_content)

    print(f"Updated version.py to {new_version}")


def update_changelog(new_version: str):
    """Update CHANGELOG.md with new version."""
    changelog_file = Path("CHANGELOG.md")

    if not changelog_file.exists():
        print("CHANGELOG.md not found, skipping changelog update")
        return

    with open(changelog_file, "r") as f:
        content = f.read()

    # Find the [Unreleased] section and replace it
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Add new unreleased section and move content to new version
    unreleased_pattern = r"## \[Unreleased\].*?(?=## \[|\Z)"
    unreleased_match = re.search(unreleased_pattern, content, re.DOTALL)

    if unreleased_match:
        unreleased_content = unreleased_match.group(0)

        # Extract the changes from unreleased
        changes_pattern = r"## \[Unreleased\]\s*\n(.*?)(?=\n## \[|\Z)"
        changes_match = re.search(changes_pattern, unreleased_content, re.DOTALL)

        if changes_match:
            changes = changes_match.group(1).strip()
        else:
            changes = ""

        # Create new unreleased section and version section
        new_unreleased = "## [Unreleased]\n\n"
        new_version_section = f"## [{new_version}] - {date_str}\n\n{changes}\n\n"

        # Replace the unreleased section
        new_content = re.sub(
            unreleased_pattern, new_unreleased + new_version_section, content, flags=re.DOTALL
        )

        # Update the links section at the bottom
        # Add new version link
        version_link = f"[{new_version}]: https://github.com/TheAlistairRoss/Sentinel-Log-Aggregator/releases/tag/v{new_version}"

        # Find the last line and add before it
        lines = new_content.split("\n")
        if lines and lines[-1].startswith("["):
            lines.insert(-1, version_link)
            new_content = "\n".join(lines)
        else:
            new_content += f"\n{version_link}"

        with open(changelog_file, "w") as f:
            f.write(new_content)

        print(f"Updated CHANGELOG.md for version {new_version}")
    else:
        print("Could not find [Unreleased] section in CHANGELOG.md")


def run_tests():
    """Run the test suite to ensure everything is working."""
    print("Running test suite...")
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/", "-v"], capture_output=True, text=True
    )

    if result.returncode != 0:
        print("Tests failed!")
        print(result.stdout)
        print(result.stderr)
        return False

    print("All tests passed!")
    return True


def run_security_scan():
    """Run security scans before release."""
    print("Running security scans...")

    # Run bandit
    result = subprocess.run(
        ["bandit", "-r", "sentinel_log_aggregator/", "-q"], capture_output=True, text=True
    )
    if result.returncode != 0:
        print("Bandit security scan failed!")
        print(result.stdout)
        return False

    print("Security scans passed!")
    return True


def build_package():
    """Build the package."""
    print("Building package...")

    # Clean previous builds
    subprocess.run(["rm", "-rf", "dist/", "build/", "*.egg-info"], shell=True)

    # Build
    result = subprocess.run(["python", "-m", "build"], capture_output=True, text=True)

    if result.returncode != 0:
        print("Package build failed!")
        print(result.stdout)
        print(result.stderr)
        return False

    print("Package built successfully!")
    return True


def create_git_tag(version: str):
    """Create a git tag for the version."""
    tag_name = f"v{version}"

    # Check if tag already exists
    result = subprocess.run(["git", "tag", "-l", tag_name], capture_output=True, text=True)

    if result.stdout.strip():
        print(f"Tag {tag_name} already exists!")
        return False

    # Create tag
    result = subprocess.run(
        ["git", "tag", "-a", tag_name, "-m", f"Release {version}"], capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"Failed to create tag {tag_name}")
        print(result.stderr)
        return False

    print(f"Created git tag {tag_name}")
    return True


def main():
    """Main release management function."""
    parser = argparse.ArgumentParser(description="Sentinel Log Aggregator Release Management")
    parser.add_argument(
        "action", choices=["version", "bump", "release", "build"], help="Action to perform"
    )
    parser.add_argument(
        "--type",
        choices=["major", "minor", "patch", "alpha", "beta", "rc"],
        help="Type of version bump",
    )
    parser.add_argument("--version", help="Specific version to set")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--skip-security", action="store_true", help="Skip security scans")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without doing it"
    )

    args = parser.parse_args()

    if args.action == "version":
        current = get_current_version()
        print(f"Current version: {current}")
        return

    elif args.action == "bump":
        if not args.type and not args.version:
            print("Must specify --type or --version for bump action")
            sys.exit(1)

        current = get_current_version()
        print(f"Current version: {current}")

        if args.version:
            new_version = args.version
        else:
            new_version = bump_version(current, args.type)

        print(f"New version: {new_version}")

        if not args.dry_run:
            update_version_file(new_version)
            update_changelog(new_version)
            print("Version bumped successfully!")
        else:
            print("(Dry run - no changes made)")

    elif args.action == "build":
        if not args.skip_tests:
            if not run_tests():
                sys.exit(1)

        if not args.skip_security:
            if not run_security_scan():
                sys.exit(1)

        if not build_package():
            sys.exit(1)

        print("Build completed successfully!")

    elif args.action == "release":
        if not args.type and not args.version:
            print("Must specify --type or --version for release action")
            sys.exit(1)

        current = get_current_version()
        print(f"Current version: {current}")

        if args.version:
            new_version = args.version
        else:
            new_version = bump_version(current, args.type)

        print(f"Preparing release {new_version}")

        if args.dry_run:
            print("(Dry run - no changes made)")
            return

        # Update version and changelog
        update_version_file(new_version)
        update_changelog(new_version)

        # Run tests and security scans
        if not args.skip_tests:
            if not run_tests():
                sys.exit(1)

        if not args.skip_security:
            if not run_security_scan():
                sys.exit(1)

        # Build package
        if not build_package():
            sys.exit(1)

        # Commit changes
        subprocess.run(["git", "add", "sentinel_log_aggregator/version.py", "CHANGELOG.md"])
        subprocess.run(["git", "commit", "-m", f"Bump version to {new_version}"])

        # Create tag
        if not create_git_tag(new_version):
            sys.exit(1)

        print(f"\n🎉 Release {new_version} prepared successfully!")
        print("\nNext steps:")
        print("1. Review the changes")
        print("2. Push to GitHub: git push && git push --tags")
        print("3. GitHub Actions will automatically create the release and publish to PyPI")


if __name__ == "__main__":
    main()
