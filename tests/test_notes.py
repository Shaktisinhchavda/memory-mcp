"""Tests for the notes tool."""

import sys
sys.path.insert(0, ".")

from core_mcp.tools.notes import list_notes, read_note


def test_list_notes():
    """Test that list_notes finds our sample notes."""
    notes = list_notes()
    print(f"Found {len(notes)} notes:")
    for note in notes:
        print(f"  - {note['name']} ({note['size_bytes']} bytes)")
    assert len(notes) >= 4, f"Expected at least 4 notes, got {len(notes)}"
    print("✅ test_list_notes passed")


def test_read_note():
    """Test that we can read a specific note."""
    result = read_note("project-ideas.md")
    assert "error" not in result, f"Error: {result.get('error')}"
    assert "content" in result
    assert "AI Personal Assistant" in result["content"]
    print(f"✅ test_read_note passed (read {result['size_bytes']} bytes)")


def test_read_note_not_found():
    """Test error handling for missing notes."""
    result = read_note("nonexistent.md")
    assert "error" in result
    assert "available_notes" in result
    print(f"✅ test_read_note_not_found passed")


if __name__ == "__main__":
    test_list_notes()
    test_read_note()
    test_read_note_not_found()
    print("\n🎉 All notes tests passed!")
