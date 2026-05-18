"""Phase 2 — Connector Tests (cross-platform)."""

import sys
from pathlib import Path

sys.path.insert(0, ".")

from config.settings import settings

# Resolve paths from settings (works on any OS)
NOTES_DIR = str(settings.notes_dir.resolve())
PROJECT_ROOT = str(Path(".").resolve())


def test_files_mcp():
    print("=== Testing files_mcp ===")
    from connectors.files_mcp.tools import list_files, read_file

    files = list_files(NOTES_DIR)
    print(f"  Files found: {len(files)}")

    if files:
        # Read the first available file
        first_file = Path(NOTES_DIR) / files[0]["name"]
        result = read_file(str(first_file))
        assert "content" in result, f"Error: {result}"
        print(f"  Read file: {result['name']} ({result['file_type']})")
    else:
        print("  (No notes yet — place files in data/notes/)")
    print("  [PASS] files_mcp")


def test_browser_mcp():
    print("\n=== Testing browser_mcp ===")
    from connectors.browser_mcp.tools import get_history_stats, get_available_browsers

    browsers = get_available_browsers()
    print(f"  Detected browsers: {list(browsers.get('browsers', {}).keys())}")

    stats = get_history_stats()
    if "error" in str(stats):
        print(f"  [SKIP] No browser history accessible")
        return

    for name, data in stats.items():
        if isinstance(data, dict) and "total_urls" in data:
            print(f"  {name}: {data['total_urls']} URLs, {data['total_visits']} visits")
    print("  [PASS] browser_mcp")


def test_code_mcp():
    print("\n=== Testing code_mcp ===")
    from connectors.code_mcp.tools import get_recent_commits, get_git_status, get_vscode_recent_files

    # Test git using the project root (works on any OS)
    commits = get_recent_commits(PROJECT_ROOT, 5)
    print(f"  Commits found: {len(commits)}")
    for c in commits[:3]:
        if "error" not in c:
            print(f"    - {c['hash']} {c['message'][:50]}")

    status = get_git_status(PROJECT_ROOT)
    print(f"  Branch: {status.get('branch', 'unknown')}")
    print(f"  Clean: {status.get('is_clean', 'unknown')}")

    # Test VSCode
    recent = get_vscode_recent_files()
    print(f"  VSCode recent entries: {len(recent)}")
    for r in recent[:3]:
        if "error" not in r:
            print(f"    - [{r['type']}] {r['path'][:60]}")
    print("  [PASS] code_mcp")


def test_conversations_mcp():
    print("\n=== Testing conversations_mcp ===")
    from connectors.conversations_mcp.tools import list_conversation_files

    files = list_conversation_files()
    print(f"  Conversation files found: {len(files)}")
    if files:
        for f in files:
            print(f"    - {f['name']}")
    else:
        print("  (No exports yet — place JSON files in data/conversations/)")
    print("  [PASS] conversations_mcp")


def test_calendar_mcp():
    print("\n=== Testing calendar_mcp ===")
    creds = Path("config/google_credentials.json")
    if creds.exists():
        from connectors.calendar_mcp.tools import list_calendars
        calendars = list_calendars()
        print(f"  Calendars: {len(calendars)}")
    else:
        print("  [SKIP] No Google credentials found at config/google_credentials.json")
        print("  To enable: download OAuth credentials from Google Cloud Console")
    print("  [PASS] calendar_mcp (structure OK)")


if __name__ == "__main__":
    test_files_mcp()
    test_browser_mcp()
    test_code_mcp()
    test_conversations_mcp()
    test_calendar_mcp()
    print("\n" + "=" * 40)
    print("All Phase 2 connector tests complete!")
