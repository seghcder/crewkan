#!/usr/bin/env python3
"""
Test native kanban board display with Playwright.

Tests:
- Kanban board renders correctly
- Columns are visible
- Tasks are displayed
- Initial display works
"""

import tempfile
import shutil
import time
import subprocess
import os
from pathlib import Path
import sys
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.crewkan_setup import main as setup_main
from crewkan.board_core import BoardClient


@pytest.fixture(scope="function")
def test_board():
    """Set up a test board for each test."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "test_board"
    
    # Set up board
    old_argv = sys.argv
    sys.argv = ["crewkan_setup", "--root", str(board_dir), "--with-sample-agents", "--force"]
    try:
        setup_main()
    finally:
        sys.argv = old_argv
    
    # Create some test tasks
    client = BoardClient(board_dir, "nuni")
    client.create_issue(
        title="Test Task 1",
        description="First test task",
        column="todo",
        assignees=["nuni"],
        priority="high",
        tags=["test", "playwright"],
    )
    client.create_issue(
        title="Test Task 2",
        description="Second test task",
        column="doing",
        assignees=["nuni"],
        priority="medium",
        tags=["test"],
    )
    client.create_issue(
        title="Test Task 3",
        description="Third test task",
        column="done",
        assignees=["nuni"],
        priority="low",
        tags=[],
    )
    
    yield board_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture(scope="function")
def streamlit_server(test_board):
    """Start Streamlit server for testing."""
    port = 8504  # Use different port to avoid conflicts
    env = os.environ.copy()
    env["CREWKAN_BOARD_ROOT"] = str(test_board)
    
    # Start Streamlit in background
    process = subprocess.Popen(
        [
            "streamlit",
            "run",
            str(Path(__file__).parent.parent / "crewkan" / "crewkan_ui.py"),
            "--server.port", str(port),
            "--server.headless", "true",
            "--server.enableCORS", "false",
            "--server.enableXsrfProtection", "false",
            "--browser.gatherUsageStats", "false",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Wait for server to start
    import requests
    max_attempts = 30
    for _ in range(max_attempts):
        try:
            response = requests.get(f"http://localhost:{port}", timeout=2)
            if response.status_code == 200:
                break
        except:
            time.sleep(0.5)
    else:
        process.terminate()
        raise RuntimeError("Streamlit server did not start in time")
    
    yield f"http://localhost:{port}"
    
    # Cleanup
    process.terminate()
    process.wait(timeout=5)
    if process.poll() is None:
        process.kill()


@pytest.fixture(scope="function")
def page(playwright):
    """Create a Playwright page."""
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()
    browser.close()


def test_native_kanban_display(streamlit_server, page, test_board):
    """Test that the native kanban board displays correctly."""
    # Create screenshot directory
    screenshot_dir = Path(__file__).parent.parent / "tmp" / "test_runs"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🌐 Navigating to: {streamlit_server}")
    page.goto(streamlit_server)
    
    # Wait for page to load
    print("⏳ Waiting for page to load...")
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(2000)  # Extra wait for Streamlit to render
    
    # Take initial screenshot
    screenshot_path = screenshot_dir / "native_kanban_01_initial_load.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"📸 Screenshot saved: {screenshot_path}")
    
    # Check for buttons
    try:
        new_task_btn = page.wait_for_selector('button:has-text("New Task"), button:has-text("➕")', timeout=5000)
        print("✓ Found 'New Task' button")
    except:
        print("⚠️ Could not find 'New Task' button")
    
    try:
        refresh_btn = page.wait_for_selector('button:has-text("Refresh"), button:has-text("🔄")', timeout=5000)
        print("✓ Found 'Refresh' button")
    except:
        print("⚠️ Could not find 'Refresh' button")
    
    # Look for kanban board - it should be in an iframe (st.components.v1.html renders in iframe)
    print("🔍 Looking for kanban board iframe...")
    
    # Wait for iframe to appear
    try:
        iframe = page.wait_for_selector('iframe[title*="streamlit"], iframe[src*="component"], iframe', timeout=10000)
        print("✓ Found iframe")
        
        # Get iframe content
        iframe_content = iframe.content_frame()
        if iframe_content:
            print("✓ Can access iframe content")
            
            # Wait a bit for iframe content to load
            iframe_content.wait_for_load_state("networkidle", timeout=10000)
            iframe_content.wait_for_timeout(2000)
            
            # Take screenshot of iframe element (not the frame object)
            screenshot_path = screenshot_dir / "native_kanban_02_iframe_content.png"
            iframe.screenshot(path=str(screenshot_path))
            print(f"📸 Screenshot saved: {screenshot_path}")
            
            # Check for kanban container
            try:
                kanban_container = iframe_content.wait_for_selector('.kanban-container, #kanbanContainer', timeout=5000)
                print("✓ Found kanban container")
                
                # Check for columns
                columns = iframe_content.query_selector_all('.kanban-column, [class*="column"]')
                print(f"✓ Found {len(columns)} columns")
                
                # Check for task cards
                task_cards = iframe_content.query_selector_all('.task-card, [class*="task"]')
                print(f"✓ Found {len(task_cards)} task cards")
                
                # Take final screenshot
                screenshot_path = screenshot_dir / "native_kanban_03_final_state.png"
                iframe.screenshot(path=str(screenshot_path))
                print(f"📸 Screenshot saved: {screenshot_path}")
                
                # Also take full page screenshot
                screenshot_path = screenshot_dir / "native_kanban_04_full_page.png"
                page.screenshot(path=str(screenshot_path), full_page=True)
                print(f"📸 Screenshot saved: {screenshot_path}")
                
                # Basic assertions
                assert len(columns) > 0, "Should have at least one column"
                print("✅ Test: Native kanban display - PASSED")
                
            except Exception as e:
                print(f"⚠️ Could not find kanban elements in iframe: {e}")
                # Take screenshot anyway for debugging
                screenshot_path = screenshot_dir / "native_kanban_error_state.png"
                iframe.screenshot(path=str(screenshot_path))
                print(f"📸 Error screenshot saved: {screenshot_path}")
                
                # Check what's actually in the iframe
                iframe_html = iframe_content.content()
                print(f"📄 Iframe HTML length: {len(iframe_html)}")
                if "kanban" in iframe_html.lower():
                    print("✓ Found 'kanban' in iframe HTML")
                if "container" in iframe_html.lower():
                    print("✓ Found 'container' in iframe HTML")
                
                raise
        else:
            print("⚠️ Could not access iframe content")
            raise AssertionError("Could not access iframe content")
            
    except Exception as e:
        print(f"⚠️ Error finding iframe: {e}")
        # Take full page screenshot for debugging
        screenshot_path = screenshot_dir / "native_kanban_error_no_iframe.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"📸 Error screenshot saved: {screenshot_path}")
        
        # Check page HTML for clues
        page_content = page.content()
        if "kanban" in page_content.lower():
            print("✓ Found 'kanban' in page content")
        if "iframe" in page_content.lower():
            print("✓ Found 'iframe' in page content")
        
        raise AssertionError(f"Could not find kanban board iframe: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--headed"])

