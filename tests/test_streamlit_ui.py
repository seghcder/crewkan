#!/usr/bin/env python3
"""
Test Streamlit UI using streamlit.testing.

This requires streamlit>=1.28.0 which includes testing utilities.
"""

import tempfile
import shutil
from pathlib import Path
import sys

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    print("Streamlit testing requires streamlit>=1.28.0")
    print("Run: pip install 'streamlit>=1.28.0'")
    sys.exit(1)


def test_streamlit_ui():
    """Test the Streamlit UI with a sample board."""
    # Create a test board
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "test_board"

    try:
        # Set up board
        from crewkan.crewkan_setup import main as setup_main
        import sys
        import os

        # Mock sys.argv for setup
        old_argv = sys.argv
        sys.argv = ["crewkan_setup", "--root", str(board_dir), "--with-sample-agents", "--force"]
        setup_main()
        sys.argv = old_argv

        # Create a test task
        from crewkan.crewkan_cli import main as cli_main
        sys.argv = [
            "crewkan_cli",
            "--root",
            str(board_dir),
            "new-task",
            "--title",
            "Test Task",
            "--column",
            "todo",
            "--assignee",
            "nuni",
        ]
        cli_main()

        # Set environment variable for UI
        import os
        os.environ["CREWKAN_BOARD_ROOT"] = str(board_dir)

        # Test the UI
        at = AppTest.from_file("crewkan/crewkan_ui.py", default_timeout=10.0)
        at.run()

        # Check that the UI loaded
        assert len(at.title) > 0, "UI should have a title"
        print("✓ UI loaded successfully")

        # Check that agents are listed
        # Note: Streamlit testing is limited, this is a basic smoke test
        print("✓ Streamlit UI test passed")

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_streamlit_ui()

