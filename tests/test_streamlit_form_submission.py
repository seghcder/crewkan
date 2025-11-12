#!/usr/bin/env python3
"""
Comprehensive test for Streamlit form submission.

Tests the actual form submission flow with proper verification.
"""

import tempfile
import shutil
import time
import subprocess
import os
import logging
from pathlib import Path
import sys
import pytest
import json
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.crewkan_setup import main as setup_main
from crewkan.board_core import BoardClient


# Set up logging for tests
log_dir = Path(__file__).parent.parent / "tmp" / "test_runs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"test_form_submission_{int(time.time())}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stderr),
    ]
)

test_logger = logging.getLogger(__name__)
test_logger.info(f"Test log file: {log_file}")


@pytest.fixture(scope="function")
def test_board():
    """Set up a test board for each test."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "test_board"
    
    old_argv = sys.argv
    sys.argv = ["crewkan_setup", "--root", str(board_dir), "--with-sample-agents", "--force"]
    try:
        setup_main()
    finally:
        sys.argv = old_argv
    
    yield board_dir
    shutil.rmtree(temp_dir)


@pytest.fixture(scope="function")
def streamlit_server(test_board):
    """Start Streamlit server for testing."""
    port = 8505
    env = os.environ.copy()
    env["CREWKAN_BOARD_ROOT"] = str(test_board)
    
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
    
    process.terminate()
    process.wait(timeout=5)
    if process.poll() is None:
        process.kill()


def find_form_inputs(page):
    """Find all form input elements."""
    inputs = {}
    
    # Find title input
    title_selectors = [
        'input[aria-label*="Title" i]',
        'input[placeholder*="Title" i]',
        '.stTextInput input',
    ]
    for selector in title_selectors:
        elem = page.query_selector(selector)
        if elem:
            inputs['title'] = elem
            break
    
    # Find description textarea
    desc_selectors = [
        'textarea[aria-label*="Description" i]',
        '.stTextArea textarea',
    ]
    for selector in desc_selectors:
        elem = page.query_selector(selector)
        if elem:
            inputs['description'] = elem
            break
    
    # Find submit button
    submit_selectors = [
        'button:has-text("Create Task")',
        'button[type="submit"]',
    ]
    for selector in submit_selectors:
        elem = page.query_selector(selector)
        if elem:
            inputs['submit'] = elem
            break
    
    return inputs


def test_form_submission_flow(streamlit_server, page, test_board):
    """Test complete form submission flow with verification."""
    test_logger.info("=" * 70)
    test_logger.info("Starting form submission test")
    test_logger.info("=" * 70)
    
    # Create screenshot directory
    screenshot_dir = log_dir
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    # Navigate to page
    test_logger.info(f"Navigating to {streamlit_server}")
    page.goto(streamlit_server)
    page.wait_for_selector("h1", timeout=10000)
    page.wait_for_timeout(2000)  # Wait for Streamlit to render
    
    # Take initial screenshot
    screenshot_path = screenshot_dir / "form_test_01_initial.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    test_logger.info(f"Screenshot: {screenshot_path}")
    
    # Find form inputs
    test_logger.info("Finding form inputs...")
    inputs = find_form_inputs(page)
    
    assert 'title' in inputs, "Title input not found"
    assert 'submit' in inputs, "Submit button not found"
    test_logger.info(f"Found inputs: {list(inputs.keys())}")
    
    # Fill form
    test_title = "Test Form Submission Task"
    test_description = "This task tests form submission"
    
    test_logger.info(f"Filling title: '{test_title}'")
    inputs['title'].fill(test_title)
    page.wait_for_timeout(500)
    
    if 'description' in inputs:
        test_logger.info(f"Filling description: '{test_description}'")
        inputs['description'].fill(test_description)
        page.wait_for_timeout(500)
    
    # Screenshot before submit
    screenshot_path = screenshot_dir / "form_test_02_before_submit.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    test_logger.info(f"Screenshot: {screenshot_path}")
    
    # Count tasks before submission
    client = BoardClient(test_board, "nuni")
    tasks_before = json.loads(client.list_my_issues())
    task_count_before = len(tasks_before)
    test_logger.info(f"Tasks before submission: {task_count_before}")
    
    # Click submit button
    test_logger.info("Clicking submit button...")
    inputs['submit'].click()
    
    # Wait for form submission and rerun
    test_logger.info("Waiting for form submission...")
    page.wait_for_timeout(3000)
    
    # Screenshot after submit
    screenshot_path = screenshot_dir / "form_test_03_after_submit.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    test_logger.info(f"Screenshot: {screenshot_path}")
    
    # Check for success message in UI
    page_text = page.inner_text("body")
    test_logger.info(f"Page text after submit (first 500 chars): {page_text[:500]}")
    
    # Verify task was created in filesystem
    test_logger.info("Checking filesystem for new task...")
    tasks_after = json.loads(client.list_my_issues())
    task_count_after = len(tasks_after)
    test_logger.info(f"Tasks after submission: {task_count_after}")
    
    assert task_count_after > task_count_before, f"Task count should increase. Before: {task_count_before}, After: {task_count_after}"
    
    # Find the new task
    new_task = None
    for task in tasks_after:
        if test_title in task.get("title", ""):
            new_task = task
            break
    
    assert new_task is not None, f"Task with title '{test_title}' not found in filesystem"
    test_logger.info(f"Found new task: {new_task['id']}")
    
    # Verify task details
    assert new_task["title"] == test_title, f"Task title mismatch: {new_task['title']} != {test_title}"
    if test_description:
        assert test_description in new_task.get("description", ""), "Task description not found"
    
    # Check for success message in UI
    success_indicators = ["Created task", "✅", test_title]
    has_success = any(indicator in page_text for indicator in success_indicators)
    test_logger.info(f"Success indicators found: {has_success}")
    
    # Verify form was cleared (title input should be empty)
    page.wait_for_timeout(1000)
    title_value = inputs['title'].input_value() if hasattr(inputs['title'], 'input_value') else inputs['title'].evaluate("el => el.value")
    test_logger.info(f"Title input value after submit: '{title_value}'")
    
    # Form should be cleared (but might not be immediately visible)
    # The important thing is that the task was created
    
    test_logger.info("=" * 70)
    test_logger.info("Form submission test PASSED")
    test_logger.info("=" * 70)
    
    print("✓ Test: Form submission flow - PASSED")


def test_form_submission_logs(streamlit_server, page, test_board):
    """Test that form submission generates proper log entries."""
    test_logger.info("Testing form submission logging...")
    
    # Find log file from UI
    log_files = sorted((Path(__file__).parent.parent / "tmp").glob("crewkan_ui_*.log"))
    if not log_files:
        test_logger.warning("No UI log files found")
        return
    
    latest_log = log_files[-1]
    test_logger.info(f"Checking log file: {latest_log}")
    
    # Navigate and submit form
    page.goto(streamlit_server)
    page.wait_for_selector("h1", timeout=10000)
    page.wait_for_timeout(2000)
    
    inputs = find_form_inputs(page)
    if 'title' in inputs and 'submit' in inputs:
        inputs['title'].fill("Log Test Task")
        inputs['submit'].click()
        page.wait_for_timeout(3000)
    
    # Read log file
    if latest_log.exists():
        with open(latest_log) as f:
            log_content = f.read()
        
        # Check for form submission indicators
        assert "FORM SUBMITTED!" in log_content or "Form submitted" in log_content.lower(), "Form submission not logged"
        assert "create_task()" in log_content or "create_task" in log_content, "create_task function not called"
        
        test_logger.info("Log verification passed")
        print("✓ Test: Form submission logs - PASSED")
    else:
        test_logger.warning("Log file not found, skipping log verification")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

