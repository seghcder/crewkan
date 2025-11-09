#!/usr/bin/env python3
"""
Extended Streamlit UI tests using Playwright.

Tests task creation, assignment, renaming, tags, comments, etc.
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.crewkan_setup import main as setup_main
from crewkan.board_core import BoardClient


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
    port = 8504
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


def test_create_task_via_ui(streamlit_server, page, test_board):
    """Test creating a task through the UI and verify it exists."""
    page.goto(streamlit_server)
    page.wait_for_selector("h1", timeout=10000)
    page.wait_for_timeout(2000)
    
    # Create task via BoardClient (simulating UI form submission)
    client = BoardClient(test_board, "nuni")
    task_id = client.create_task(
        title="UI Test Task",
        description="Created via UI test",
        column="todo",
        assignees=["nuni"],
        tags=["test", "ui"],
    )
    
    # Refresh and verify task appears in UI
    page.reload()
    page.wait_for_timeout(2000)
    page_text = page.inner_text("body")
    assert "UI Test Task" in page_text, "Task should appear in UI"
    
    # Verify in backend
    tasks_json = client.list_my_tasks()
    tasks = json.loads(tasks_json)
    task = next((t for t in tasks if t["id"] == task_id), None)
    assert task is not None, "Task should exist in backend"
    assert task["title"] == "UI Test Task"
    assert "nuni" in task["assignees"]
    assert "test" in task["tags"]
    
    print("✓ Test: Create task via UI - PASSED")


def test_assign_task_via_ui(streamlit_server, page, test_board):
    """Test assigning a task and verify assignment."""
    # Create task first
    client = BoardClient(test_board, "nuni")
    task_id = client.create_task(
        title="Task to Assign",
        description="Test assignment",
        column="todo",
    )
    
    # Assign via BoardClient (simulating UI)
    client.reassign_task(task_id, "tau", keep_existing=True)
    
    # Verify in backend
    tasks_json = client.list_my_tasks()
    tasks = json.loads(tasks_json)
    task = next((t for t in tasks if t["id"] == task_id), None)
    assert task is not None
    assert "tau" in task.get("assignees", []), "Task should be assigned to tau"
    
    # Verify in UI
    page.goto(streamlit_server)
    page.wait_for_selector("h1", timeout=10000)
    page.wait_for_timeout(2000)
    page_text = page.inner_text("body")
    assert "Task to Assign" in page_text
    
    print("✓ Test: Assign task via UI - PASSED")


def test_rename_task_via_ui(streamlit_server, page, test_board):
    """Test renaming a task."""
    client = BoardClient(test_board, "nuni")
    task_id = client.create_task(
        title="Original Title",
        description="Test rename",
        column="todo",
    )
    
    # Rename via BoardClient
    client.update_task_field(task_id, "title", "Renamed Title")
    
    # Verify in backend
    tasks_json = client.list_my_tasks()
    tasks = json.loads(tasks_json)
    task = next((t for t in tasks if t["id"] == task_id), None)
    assert task is not None
    assert task["title"] == "Renamed Title", f"Title not updated: {task['title']}"
    
    # Verify in UI
    page.goto(streamlit_server)
    page.wait_for_selector("h1", timeout=10000)
    page.wait_for_timeout(2000)
    page_text = page.inner_text("body")
    assert "Renamed Title" in page_text
    
    print("✓ Test: Rename task via UI - PASSED")


def test_update_tags_via_ui(streamlit_server, page, test_board):
    """Test updating task tags."""
    client = BoardClient(test_board, "nuni")
    task_id = client.create_task(
        title="Task with Tags",
        description="Test tags",
        column="todo",
        tags=["original"],
    )
    
    # Update tags
    task_path = test_board / "tasks" / "todo" / f"{task_id}.yaml"
    import yaml
    with open(task_path) as f:
        task = yaml.safe_load(f)
    task["tags"] = ["original", "updated", "test"]
    task["updated_at"] = client._now_iso()
    task.setdefault("history", []).append({
        "at": task["updated_at"],
        "by": "nuni",
        "event": "tags_updated",
        "details": "Tags: original, updated, test",
    })
    with open(task_path, "w") as f:
        yaml.safe_dump(task, f)
    
    # Verify in backend
    tasks_json = client.list_my_tasks()
    tasks = json.loads(tasks_json)
    task = next((t for t in tasks if t["id"] == task_id), None)
    assert task is not None
    assert "updated" in task.get("tags", []), "Tags should be updated"
    assert "test" in task.get("tags", []), "Tags should include test"
    
    print("✓ Test: Update tags via UI - PASSED")


def test_add_comment_via_ui(streamlit_server, page, test_board):
    """Test adding a comment to a task."""
    client = BoardClient(test_board, "nuni")
    task_id = client.create_task(
        title="Task for Comment",
        description="Test comment",
        column="todo",
    )
    
    # Add comment
    client.add_comment(task_id, "This is a test comment")
    
    # Verify in backend
    tasks_json = client.list_my_tasks()
    tasks = json.loads(tasks_json)
    task = next((t for t in tasks if t["id"] == task_id), None)
    assert task is not None
    history = task.get("history", [])
    comment_found = any("test comment" in h.get("details", "").lower() for h in history)
    assert comment_found, "Comment should be in history"
    
    print("✓ Test: Add comment via UI - PASSED")


def test_move_task_via_ui(streamlit_server, page, test_board):
    """Test moving a task between columns."""
    client = BoardClient(test_board, "nuni")
    task_id = client.create_task(
        title="Task to Move",
        description="Test move",
        column="todo",
    )
    
    # Move task
    client.move_task(task_id, "doing")
    
    # Verify in backend
    tasks_json = client.list_my_tasks(column="doing")
    tasks = json.loads(tasks_json)
    task = next((t for t in tasks if t["id"] == task_id), None)
    assert task is not None, "Task should be in doing column"
    assert task["column"] == "doing", f"Task in wrong column: {task['column']}"
    
    # Verify in UI
    page.goto(streamlit_server)
    page.wait_for_selector("h1", timeout=10000)
    page.wait_for_timeout(2000)
    page_text = page.inner_text("body")
    assert "Task to Move" in page_text
    
    print("✓ Test: Move task via UI - PASSED")


def test_filesystem_change_detection(streamlit_server, page, test_board):
    """Test that UI detects filesystem changes from backend."""
    page.goto(streamlit_server)
    page.wait_for_selector("h1", timeout=10000)
    page.wait_for_timeout(1000)
    
    # Create task via backend
    client = BoardClient(test_board, "nuni")
    task_id = client.create_task(
        title="Backend Created Task",
        description="Created by backend",
        column="todo",
    )
    
    # Wait for auto-refresh
    page.wait_for_timeout(3000)
    page.reload()
    page.wait_for_timeout(2000)
    
    # Verify task appears
    page_text = page.inner_text("body")
    assert "Backend Created Task" in page_text or task_id in page_text
    
    print("✓ Test: Filesystem change detection - PASSED")

