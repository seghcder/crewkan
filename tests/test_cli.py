#!/usr/bin/env python3
"""
CLI testing suite.

Tests all CLI commands to ensure they work correctly.
"""

import tempfile
import shutil
import subprocess
import sys
from pathlib import Path
import yaml
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def run_cli_command(cmd: list[str], board_dir: Path) -> tuple[int, str, str]:
    """Run a CLI command and return exit code, stdout, stderr."""
    # Set PYTHONPATH to include parent directory
    env = os.environ.copy()
    parent_dir = str(Path(__file__).resolve().parent.parent)
    env["PYTHONPATH"] = parent_dir + (os.pathsep + env.get("PYTHONPATH", ""))
    
    full_cmd = [sys.executable, "-m", "crewkan.crewkan_cli", "--root", str(board_dir)] + cmd
    result = subprocess.run(
        full_cmd,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


def setup_test_board(board_dir: Path) -> None:
    """Set up a test board."""
    from crewkan.crewkan_setup import main as setup_main
    import sys
    
    old_argv = sys.argv
    sys.argv = ["crewkan_setup", "--root", str(board_dir), "--with-sample-agents", "--force"]
    try:
        setup_main()
    finally:
        sys.argv = old_argv


def test_list_agents():
    """Test list-agents command."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "test_board"
    
    try:
        setup_test_board(board_dir)
        
        exit_code, stdout, stderr = run_cli_command(["list-agents"], board_dir)
        
        assert exit_code == 0, f"Command failed: {stderr}"
        assert "nuni" in stdout, "Should list nuni agent"
        assert "tau" in stdout, "Should list tau agent"
        
        print("✓ Test: list-agents - PASSED")
        return True
    except Exception as e:
        print(f"✗ Test: list-agents - FAILED: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)


def test_add_agent():
    """Test add-agent command."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "test_board"
    
    try:
        setup_test_board(board_dir)
        
        exit_code, stdout, stderr = run_cli_command(
            ["add-agent", "--id", "test-agent", "--name", "Test Agent", "--role", "Tester", "--kind", "ai"],
            board_dir
        )
        
        assert exit_code == 0, f"Command failed: {stderr}"
        
        # Verify agent was added
        agents_path = board_dir / "agents" / "agents.yaml"
        with open(agents_path) as f:
            agents_data = yaml.safe_load(f)
        
        agent_ids = [a["id"] for a in agents_data["agents"]]
        assert "test-agent" in agent_ids, "Agent should be added"
        
        # Verify agent details
        test_agent = next(a for a in agents_data["agents"] if a["id"] == "test-agent")
        assert test_agent["name"] == "Test Agent"
        assert test_agent["role"] == "Tester"
        assert test_agent["kind"] == "ai"
        
        print("✓ Test: add-agent - PASSED")
        return True
    except Exception as e:
        print(f"✗ Test: add-agent - FAILED: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)


def test_remove_agent():
    """Test remove-agent command."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "test_board"
    
    try:
        setup_test_board(board_dir)
        
        # Remove an agent
        exit_code, stdout, stderr = run_cli_command(["remove-agent", "--id", "nuni"], board_dir)
        
        assert exit_code == 0, f"Command failed: {stderr}"
        
        # Verify agent was removed
        agents_path = board_dir / "agents" / "agents.yaml"
        with open(agents_path) as f:
            agents_data = yaml.safe_load(f)
        
        agent_ids = [a["id"] for a in agents_data["agents"]]
        assert "nuni" not in agent_ids, "Agent should be removed"
        assert "tau" in agent_ids, "Other agent should remain"
        
        print("✓ Test: remove-agent - PASSED")
        return True
    except Exception as e:
        print(f"✗ Test: remove-agent - FAILED: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)


def test_new_task():
    """Test new-task command."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "test_board"
    
    try:
        setup_test_board(board_dir)
        
        exit_code, stdout, stderr = run_cli_command(
            [
                "new-task",
                "--title", "Test Task",
                "--description", "Test description",
                "--column", "todo",
                "--assignee", "nuni",
                "--priority", "high",
                "--tags", "test,cli",
            ],
            board_dir
        )
        
        assert exit_code == 0, f"Command failed: {stderr}"
        assert "Created task" in stdout, "Should indicate task was created"
        
        # Verify task was created
        tasks_dir = board_dir / "tasks" / "todo"
        task_files = list(tasks_dir.glob("*.yaml"))
        assert len(task_files) > 0, "Task file should exist"
        
        # Verify task content
        with open(task_files[0]) as f:
            task = yaml.safe_load(f)
        
        assert task["title"] == "Test Task"
        assert task["description"] == "Test description"
        assert "nuni" in task["assignees"]
        assert task["priority"] == "high"
        assert "test" in task["tags"]
        assert "cli" in task["tags"]
        
        print("✓ Test: new-task - PASSED")
        return True
    except Exception as e:
        print(f"✗ Test: new-task - FAILED: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)


def test_move_task():
    """Test move-task command."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "test_board"
    
    try:
        setup_test_board(board_dir)
        
        # Create a task first
        exit_code, stdout, stderr = run_cli_command(
            ["new-task", "--title", "Task to Move", "--column", "todo"],
            board_dir
        )
        assert exit_code == 0
        
        # Get task ID from output - format is "Created task T-... in column todo"
        import re
        match = re.search(r'T-\d{8}-\d{6}-[a-f0-9]{6}', stdout)
        assert match, f"Could not find task ID in output: {stdout}"
        task_id = match.group(0)
        
        # Move the task
        exit_code, stdout, stderr = run_cli_command(
            ["move-task", "--id", task_id, "--column", "doing"],
            board_dir
        )
        
        assert exit_code == 0, f"Command failed: {stderr}"
        assert "Moved" in stdout or "moved" in stdout.lower(), "Should indicate task was moved"
        
        # Verify task moved
        doing_dir = board_dir / "tasks" / "doing"
        todo_dir = board_dir / "tasks" / "todo"
        
        assert (doing_dir / f"{task_id}.yaml").exists(), "Task should be in doing"
        assert not (todo_dir / f"{task_id}.yaml").exists(), "Task should not be in todo"
        
        print("✓ Test: move-task - PASSED")
        return True
    except Exception as e:
        print(f"✗ Test: move-task - FAILED: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)


def test_assign_task():
    """Test assign-task command."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "test_board"
    
    try:
        setup_test_board(board_dir)
        
        # Create a task
        exit_code, stdout, stderr = run_cli_command(
            ["new-task", "--title", "Task to Assign", "--column", "todo"],
            board_dir
        )
        import re
        match = re.search(r'T-\d{8}-\d{6}-[a-f0-9]{6}', stdout)
        assert match, f"Could not find task ID in output: {stdout}"
        task_id = match.group(0)
        
        # Assign task
        exit_code, stdout, stderr = run_cli_command(
            ["assign-task", "--id", task_id, "--assignee", "tau"],
            board_dir
        )
        
        assert exit_code == 0, f"Command failed: {stderr}"
        
        # Verify assignment
        tasks_dir = board_dir / "tasks" / "todo"
        task_files = list(tasks_dir.glob("*.yaml"))
        with open(task_files[0]) as f:
            task = yaml.safe_load(f)
        
        assert "tau" in task["assignees"], "Task should be assigned to tau"
        
        print("✓ Test: assign-task - PASSED")
        return True
    except Exception as e:
        print(f"✗ Test: assign-task - FAILED: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)


def test_list_tasks():
    """Test list-tasks command."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "test_board"
    
    try:
        setup_test_board(board_dir)
        
        # Create some tasks
        run_cli_command(["new-task", "--title", "Task 1", "--column", "todo", "--assignee", "nuni"], board_dir)
        run_cli_command(["new-task", "--title", "Task 2", "--column", "doing", "--assignee", "tau"], board_dir)
        
        # List all tasks
        exit_code, stdout, stderr = run_cli_command(["list-tasks"], board_dir)
        
        assert exit_code == 0, f"Command failed: {stderr}"
        assert "Task 1" in stdout
        assert "Task 2" in stdout
        
        # List tasks by column
        exit_code, stdout, stderr = run_cli_command(["list-tasks", "--column", "todo"], board_dir)
        
        assert exit_code == 0
        assert "Task 1" in stdout
        assert "Task 2" not in stdout
        
        # List tasks by agent
        exit_code, stdout, stderr = run_cli_command(["list-tasks", "--agent", "nuni"], board_dir)
        
        assert exit_code == 0
        assert "Task 1" in stdout
        assert "Task 2" not in stdout
        
        print("✓ Test: list-tasks - PASSED")
        return True
    except Exception as e:
        print(f"✗ Test: list-tasks - FAILED: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)


def test_validate():
    """Test validate command."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "test_board"
    
    try:
        setup_test_board(board_dir)
        
        # Create a valid task
        run_cli_command(["new-task", "--title", "Valid Task", "--column", "todo", "--assignee", "nuni"], board_dir)
        
        # Validate should pass
        exit_code, stdout, stderr = run_cli_command(["validate"], board_dir)
        
        assert exit_code == 0, f"Validation should pass: {stderr}"
        assert "Errors: 0" in stdout or "errors: 0" in stdout.lower()
        
        print("✓ Test: validate - PASSED")
        return True
    except Exception as e:
        print(f"✗ Test: validate - FAILED: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)


def test_start_stop_task():
    """Test start-task and stop-task commands."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "test_board"
    
    try:
        setup_test_board(board_dir)
        
        # Create a task
        exit_code, stdout, stderr = run_cli_command(
            ["new-task", "--title", "Task to Work On", "--column", "todo"],
            board_dir
        )
        import re
        match = re.search(r'T-\d{8}-\d{6}-[a-f0-9]{6}', stdout)
        assert match, f"Could not find task ID in output: {stdout}"
        task_id = match.group(0)
        
        # Start work
        exit_code, stdout, stderr = run_cli_command(
            ["start-task", "--id", task_id, "--agent", "nuni", "--column", "doing"],
            board_dir
        )
        
        assert exit_code == 0, f"Command failed: {stderr}"
        
        # Verify workspace symlink created
        workspace_link = board_dir / "workspaces" / "nuni" / "doing" / f"{task_id}.yaml"
        assert workspace_link.exists() or workspace_link.is_symlink(), "Workspace symlink should exist"
        
        # Stop work
        exit_code, stdout, stderr = run_cli_command(
            ["stop-task", "--id", task_id, "--agent", "nuni"],
            board_dir
        )
        
        assert exit_code == 0
        
        # Verify symlink removed
        assert not workspace_link.exists(), "Workspace symlink should be removed"
        
        print("✓ Test: start-task/stop-task - PASSED")
        return True
    except Exception as e:
        print(f"✗ Test: start-task/stop-task - FAILED: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)


def run_all_cli_tests():
    """Run all CLI tests."""
    print("Running CLI tests...\n")
    
    tests = [
        test_list_agents,
        test_add_agent,
        test_remove_agent,
        test_new_task,
        test_move_task,
        test_assign_task,
        test_list_tasks,
        test_validate,
        test_start_stop_task,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} - FAILED: {e}")
            failed += 1
    
    print(f"\n=== Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_cli_tests()
    sys.exit(0 if success else 1)

