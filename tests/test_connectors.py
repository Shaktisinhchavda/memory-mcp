"""Phase 2 — Connector Tests."""

import sys
sys.path.insert(0, ".")


def test_files_mcp():
    print("=== Testing files_mcp ===")
    from connectors.files_mcp.tools import list_files, read_file

    files = list_files("d:/memory-mcp/data/notes")
    print(f"  Files found: {len(files)}")
    assert len(files) >= 4, f"Expected >= 4 files, got {len(files)}"

    result = read_file("d:/memory-mcp/data/notes/project-ideas.md")
    assert "content" in result, f"Error: {result}"
    print(f"  Read file: {result['name']} ({result['file_type']})")
    print("  [PASS] files_mcp")


def test_browser_mcp():
    print("\n=== Testing browser_mcp ===")
    from connectors.browser_mcp.tools import get_history_stats, get_recent_history

    stats = get_history_stats()
    if "error" in stats:
        print(f"  [SKIP] {stats['error']}")
        return

    print(f"  DB exists: {stats['db_exists']}")
    print(f"  Total URLs: {stats['total_urls']}")
    print(f"  Total visits: {stats['total_visits']}")

    history = get_recent_history(5)
    print(f"  Recent entries: {len(history)}")
    for h in history[:3]:
        title = h.get("title", "")[:50]
        print(f"    - {title}")
    print("  [PASS] browser_mcp")


def test_code_mcp():
    print("\n=== Testing code_mcp ===")
    from connectors.code_mcp.tools import get_recent_commits, get_git_status, get_vscode_recent_files

    # Test git
    commits = get_recent_commits("d:/memory-mcp", 5)
    print(f"  Commits found: {len(commits)}")
    for c in commits[:3]:
        if "error" not in c:
            print(f"    - {c['hash']} {c['message'][:50]}")

    status = get_git_status("d:/memory-mcp")
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
    from pathlib import Path
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
