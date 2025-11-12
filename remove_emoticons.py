#!/usr/bin/env python
"""Script to remove emoticons from source files."""

import re
from pathlib import Path

# Pattern to match emoticons
EMOTICON_PATTERN = re.compile(r"[🔍🚀✅❌⏰📤📋🔧⚠️📅🔐💾📊⏭️⏱️ℹ️⚙️]\s*")

# Files to process
FILES = [
    Path("sentinel_log_aggregator/cli.py"),
    Path("sentinel_log_aggregator/logging_utils.py"),
    Path("sentinel_log_aggregator/query_engine.py"),
    Path("sentinel_log_aggregator/health_logger.py"),
    Path("sentinel_log_aggregator/time_range_calculator.py"),
    Path("sentinel_log_aggregator/workspace_manager.py"),
]


def remove_emoticons_from_file(file_path: Path) -> bool:
    """Remove emoticons from a file. Returns True if file was modified."""
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return False

    try:
        content = file_path.read_text(encoding="utf-8")
        original_content = content

        # Remove emoticons (and optional space after them)
        content = EMOTICON_PATTERN.sub("", content)

        if content != original_content:
            file_path.write_text(content, encoding="utf-8")
            lines_changed = sum(
                1 for line in original_content.splitlines() if EMOTICON_PATTERN.search(line)
            )
            print(f"✓ {file_path}: Removed emoticons from {lines_changed} lines")
            return True
        else:
            print(f"  {file_path}: No emoticons found")
            return False

    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}")
        return False


def main():
    """Main function."""
    print("Removing emoticons from Python source files...\n")

    modified_count = 0
    for file_path in FILES:
        if remove_emoticons_from_file(file_path):
            modified_count += 1

    print(f"\n{'='*60}")
    print(f"Summary: Modified {modified_count}/{len(FILES)} files")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
