#!/usr/bin/env python3
"""
Test native kanban board drag-and-drop with Playwright.

Tests:
- Drag and drop a task between columns
- Verify task moves in filesystem
- Verify UI updates
"""

import tempfile
import shutil
import time
import subprocess
import os
from pathlib import Path
import sys
import pytest
import json

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
    
    # Create a test task in 'todo' column
    client = BoardClient(board_dir, "nuni")
    task_id = client.create_issue(
        title="Test Drag Task",
        description="Task to test drag and drop",
        column="todo",
        assignees=["nuni"],
        priority="high",
        tags=["test", "drag-drop"],
    )
    
    yield board_dir, task_id
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture(scope="function")
def streamlit_server(test_board):
    """Start Streamlit server for testing."""
    board_dir, task_id = test_board
    port = 8505  # Use different port to avoid conflicts
    env = os.environ.copy()
    env["CREWKAN_BOARD_ROOT"] = str(board_dir)
    
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


def test_drag_drop_task(streamlit_server, page, test_board):
    """Test dragging and dropping a task between columns."""
    board_dir, task_id = test_board
    
    # Create screenshot directory
    screenshot_dir = Path(__file__).parent.parent / "tmp" / "test_runs"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🌐 Navigating to: {streamlit_server}")
    page.goto(streamlit_server)
    
    # Wait for page to load
    print("⏳ Waiting for page to load...")
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(3000)  # Extra wait for Streamlit to render
    
    # Take initial screenshot
    screenshot_path = screenshot_dir / "drag_drop_01_initial.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"📸 Screenshot saved: {screenshot_path}")
    
    # Find the kanban iframe
    print("🔍 Looking for kanban board iframe...")
    iframe = page.wait_for_selector('iframe', timeout=10000)
    iframe_content = iframe.content_frame()
    
    if not iframe_content:
        raise AssertionError("Could not access iframe content")
    
    print("✅ Found iframe")
    
    # Wait for iframe content to load
    iframe_content.wait_for_load_state("networkidle", timeout=10000)
    iframe_content.wait_for_timeout(2000)
    
    # Find the task card in 'todo' column
    print(f"🔍 Looking for task card with ID: {task_id}")
    
    # Try multiple selectors
    task_selectors = [
        f'.task-card[data-task-id="{task_id}"]',
        f'[data-task-id="{task_id}"]',
        '.task-card',
    ]
    
    task_card = None
    for selector in task_selectors:
        try:
            task_card = iframe_content.wait_for_selector(selector, timeout=3000)
            if task_card:
                print(f"✅ Found task card with selector: {selector}")
                break
        except:
            continue
    
    if not task_card:
        # Take screenshot for debugging
        screenshot_path = screenshot_dir / "drag_drop_error_no_task.png"
        iframe.screenshot(path=str(screenshot_path))
        raise AssertionError(f"Could not find task card for task {task_id}")
    
    # Find the target column (e.g., 'doing')
    print("🔍 Looking for target column 'doing'...")
    target_column = iframe_content.wait_for_selector('.kanban-column[data-column-id="doing"]', timeout=5000)
    
    if not target_column:
        raise AssertionError("Could not find target column 'doing'")
    
    print("✅ Found target column")
    
    # Get initial task location
    initial_path = board_dir / "issues" / "todo" / f"{task_id}.yaml"
    if not initial_path.exists():
        initial_path = board_dir / "tasks" / "todo" / f"{task_id}.yaml"
    
    assert initial_path.exists(), f"Task file should exist at {initial_path}"
    print(f"✅ Task file exists at: {initial_path}")
    
    # Perform drag and drop
    print("🖱️ Performing drag and drop...")
    
    # Get bounding boxes relative to iframe
    task_box = task_card.bounding_box()
    target_box = target_column.bounding_box()
    
    print(f"  Task card position (iframe): {task_box}")
    print(f"  Target column position (iframe): {target_box}")
    
    # Get iframe position on page
    iframe_box = iframe.bounding_box()
    print(f"  Iframe position: {iframe_box}")
    
    # Calculate absolute positions on page
    task_center_x = iframe_box['x'] + task_box['x'] + task_box['width'] / 2
    task_center_y = iframe_box['y'] + task_box['y'] + task_box['height'] / 2
    target_center_x = iframe_box['x'] + target_box['x'] + target_box['width'] / 2
    target_center_y = iframe_box['y'] + target_box['y'] + target_box['height'] / 2
    
    print(f"  Absolute task position: ({task_center_x}, {task_center_y})")
    print(f"  Absolute target position: ({target_center_x}, {target_center_y})")
    
    # Set up console log capture BEFORE drag and drop
    console_logs = []
    def handle_console(msg):
        log_text = f"{msg.type}: {msg.text}"
        console_logs.append(log_text)
        print(f"  📋 Console: {log_text}")
    page.on("console", handle_console)
    
    # Also try to capture iframe console (may not work due to sandboxing)
    iframe_console_logs = []
    
    # Perform drag and drop using Playwright's locator drag_to method
    # Convert ElementHandle to Locator for drag_to
    print("  Using drag_to method with locators...")
    task_card_locator = iframe_content.locator(f'.task-card[data-task-id="{task_id}"]')
    target_column_locator = iframe_content.locator('.kanban-column[data-column-id="doing"]')
    
    # Use locator's drag_to method
    task_card_locator.drag_to(target_column_locator)
    
    print("✅ Drag and drop performed")
    
    # Wait for the move to complete - check for URL change or page reload
    print("⏳ Waiting for task move to complete...")
    
    # Wait for URL to change (postMessage should trigger navigation)
    try:
        page.wait_for_url("**/kanban_event=**", timeout=5000)
        print("  ✅ URL changed with kanban_event!")
    except:
        print("  ⚠️ URL did not change within timeout")
    
    # Wait a bit more for Streamlit to process
    page.wait_for_timeout(2000)
    
    # Check if page reloaded
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
        print("  ✅ Page reloaded")
    except:
        print("  ⚠️ Page did not reload")
    
    # Check URL for query params
    current_url = page.url
    print(f"  Current URL: {current_url}")
    if "kanban_event" in current_url:
        print("  ✅ kanban_event found in URL!")
        # Extract and print the event
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(current_url)
        params = parse_qs(parsed.query)
        if "kanban_event" in params:
            event_str = params["kanban_event"][0]
            print(f"  Event data: {event_str[:100]}...")
    else:
        print("  ⚠️ kanban_event NOT found in URL")
    
    # Take screenshot after drop
    screenshot_path = screenshot_dir / "drag_drop_02_after_drop.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"📸 Screenshot saved: {screenshot_path}")
    
    # Verify task moved in filesystem
    print("🔍 Verifying task moved in filesystem...")
    
    # Check if task is now in 'doing' column
    new_path_issues = board_dir / "issues" / "doing" / f"{task_id}.yaml"
    new_path_tasks = board_dir / "tasks" / "doing" / f"{task_id}.yaml"
    
    # Wait a bit more for filesystem update
    max_wait = 10
    for i in range(max_wait):
        if new_path_issues.exists() or new_path_tasks.exists():
            break
        time.sleep(0.5)
    
    moved = new_path_issues.exists() or new_path_tasks.exists()
    old_exists = initial_path.exists()
    
    print(f"  Old location exists: {old_exists}")
    print(f"  New location (issues) exists: {new_path_issues.exists()}")
    print(f"  New location (tasks) exists: {new_path_tasks.exists()}")
    
    if moved:
        print("✅ Task successfully moved to 'doing' column")
        # Verify old file is gone (or still there if it's a copy)
        if not old_exists:
            print("✅ Old task file removed")
    else:
        print("⚠️ Task file not found in new location")
        print(f"  Looking for: {new_path_issues} or {new_path_tasks}")
    
    # Print console logs
    if console_logs:
        print("\n📋 Console logs (last 30):")
        for log in console_logs[-30:]:  # Last 30 logs
            print(f"  {log}")
    else:
        print("  ⚠️ No console logs captured")
    
    # Check if there are any errors in console
    error_logs = [log for log in console_logs if "error" in log.lower() or "❌" in log]
    if error_logs:
        print("\n❌ Error logs found:")
        for log in error_logs:
            print(f"  {log}")
    
    # Assert task moved
    assert moved, f"Task should be in 'doing' column. Checked: {new_path_issues}, {new_path_tasks}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--headed", "-s"])

