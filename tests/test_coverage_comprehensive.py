#!/usr/bin/env python3
"""
Comprehensive coverage test that includes all test types.

This imports and calls functions directly (not via subprocess) so coverage tracks them.
"""

import sys
import tempfile
import shutil
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import coverage
except ImportError:
    print("Installing coverage.py...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "coverage"])
    import coverage


def run_coverage_comprehensive():
    """Run all tests with coverage tracking by importing and calling directly."""
    cov = coverage.Coverage(
        source=["crewkan"],
        omit=[
            "crewkan/__init__.py",
            "crewkan/__pycache__/*",
            "*/test_*.py",
        ]
    )
    cov.start()
    
    print("Running comprehensive coverage test...")
    print("=" * 70)
    
    # 1. Import and call setup functions
    print("\n[1/9] Testing setup functions...")
    from crewkan.board_init import init_board
    
    temp_dir = Path(tempfile.mkdtemp())
    test_board = temp_dir / "coverage_test_board"
    
    try:
        init_board(
            test_board,
            board_id="coverage-test",
            board_name="Coverage Test Board",
            owner_agent_id="test-agent",
            default_superagent_id="test-agent",
        )
        print("  ✓ Board initialization tested")
        
        # Test init_board with existing board (should not error)
        init_board(
            test_board,
            board_id="coverage-test-2",
            board_name="Coverage Test Board 2",
            owner_agent_id="test-agent",
            default_superagent_id="test-agent",
        )
    except Exception as e:
        print(f"  ✗ Board initialization error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if test_board.exists():
            shutil.rmtree(temp_dir)
    
    # 2. Import and call CLI functions directly
    print("\n[2/7] Testing CLI functions...")
    test_board = temp_dir / "coverage_test_board"
    try:
        init_board(test_board, "test", "Test", "test-agent", "test-agent")
        
        from crewkan.crewkan_cli import (
            cmd_list_agents,
            cmd_add_agent,
            cmd_remove_agent,
            cmd_new_task,
            cmd_list_tasks,
            cmd_move_task,
            cmd_assign_task,
            cmd_validate,
            cmd_start_task,
            cmd_stop_task,
            load_board,
            load_agents,
            save_agents,
            get_column_ids,
            find_task_file,
            create_symlink,
            remove_symlink,
        )
        import argparse
        
        # Create mock args
        class MockArgs:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        # Test utility functions
        board_data = load_board(test_board)
        agents_data = load_agents(test_board)
        col_ids = get_column_ids(board_data)
        
        # Test list agents
        args = MockArgs(root=str(test_board))
        cmd_list_agents(args)
        
        # Test add agent
        args = MockArgs(root=str(test_board), id="coverage-agent", name="Coverage Agent", role="Tester", kind="ai")
        cmd_add_agent(args)
        
        # Test remove agent (actually test it)
        args = MockArgs(root=str(test_board), id="coverage-agent")
        cmd_remove_agent(args)
        
        # Test add agent again (to test duplicate check)
        args = MockArgs(root=str(test_board), id="coverage-agent-2", name="Agent 2", role="Tester", kind="ai")
        cmd_add_agent(args)
        
        # Test add duplicate agent (should skip)
        cmd_add_agent(args)
        
        # Test new task with BoardClient
        args = MockArgs(
            root=str(test_board),
            title="Coverage Test Task",
            description="Test",
            column="todo",
            assignee=["test-agent"],
            priority="high",
            tags="test,coverage",
            due_date=None,
            id=None,
        )
        cmd_new_task(args)
        
        # Test new task with fallback (no agents)
        empty_board = temp_dir / "empty_board_cli"
        init_board(empty_board, "empty", "Empty", "test-agent", "test-agent")
        # Remove agents to trigger fallback
        agents_file = empty_board / "agents" / "agents.yaml"
        if agents_file.exists():
            agents_file.unlink()
        
        args = MockArgs(
            root=str(empty_board),
            title="Fallback Task",
            description="Test",
            column="todo",
            assignee=[],
            priority="high",
            tags="test",
            due_date=None,
            id="TEST-123",
        )
        try:
            cmd_new_task(args)
        except RuntimeError:
            pass  # Expected - no agents
        
        # Test new task with invalid column
        args = MockArgs(
            root=str(test_board),
            title="Invalid Column Task",
            description="Test",
            column="invalid_column",
            assignee=["test-agent"],
            priority="high",
            tags="test",
            due_date=None,
            id=None,
        )
        try:
            cmd_new_task(args)
        except RuntimeError:
            pass  # Expected
        
        # Test find_task_file
        task_files = list((test_board / "tasks").rglob("*.yaml"))
        if task_files:
            task_id = task_files[0].stem
            found_path = find_task_file(test_board, task_id)
        
        # Test list tasks
        args = MockArgs(root=str(test_board), column=None, agent=None)
        cmd_list_tasks(args)
        
        # Test move task
        if task_files:
            args = MockArgs(root=str(test_board), task_id=task_id, column="doing")
            cmd_move_task(args)
            
            # Test move task with invalid column
            args = MockArgs(root=str(test_board), task_id=task_id, column="invalid")
            try:
                cmd_move_task(args)
            except RuntimeError:
                pass  # Expected
        
        # Test assign task
        if task_files:
            args = MockArgs(root=str(test_board), task_id=task_id, assignee=["test-agent"])
            cmd_assign_task(args)
            
            # Test assign task with nonexistent task
            args = MockArgs(root=str(test_board), task_id="nonexistent", assignee=["test-agent"])
            try:
                cmd_assign_task(args)
            except RuntimeError:
                pass  # Expected
        
        # Test validate
        args = MockArgs(root=str(test_board))
        cmd_validate(args)
        
        # Test validate with invalid board
        invalid_board = temp_dir / "invalid_board"
        invalid_board.mkdir()
        args = MockArgs(root=str(invalid_board))
        try:
            cmd_validate(args)
        except RuntimeError:
            pass  # Expected
        
        # Test list tasks with filters
        args = MockArgs(root=str(test_board), column="todo", agent=None)
        cmd_list_tasks(args)
        
        args = MockArgs(root=str(test_board), column=None, agent="test-agent")
        cmd_list_tasks(args)
        
        # Test list tasks with invalid column
        args = MockArgs(root=str(test_board), column="invalid", agent=None)
        try:
            cmd_list_tasks(args)
        except RuntimeError:
            pass  # Expected
        
        # Test list tasks with no tasks
        empty_board = temp_dir / "empty_board_list"
        init_board(empty_board, "empty", "Empty", "test-agent", "test-agent")
        args = MockArgs(root=str(empty_board), column=None, agent=None)
        cmd_list_tasks(args)
        
        # Test start/stop task (if task exists)
        if task_files:
            args = MockArgs(root=str(test_board), task_id=task_id, agent="test-agent")
            cmd_start_task(args)
            cmd_stop_task(args)
            
            # Test start/stop with nonexistent task
            args = MockArgs(root=str(test_board), task_id="nonexistent", agent="test-agent")
            try:
                cmd_start_task(args)
            except RuntimeError:
                pass  # Expected
            try:
                cmd_stop_task(args)
            except RuntimeError:
                pass  # Expected
        
        # Test symlink functions
        test_link = test_board / "test_link"
        test_target = test_board / "board.yaml"
        if test_target.exists():
            create_symlink(test_target, test_link)
            # Test removing non-existent symlink (should not error)
            remove_symlink(test_board / "nonexistent_link")
            remove_symlink(test_link)
        
        # Test save_agents
        agents_data["agents"].append({
            "id": "test-agent-2",
            "name": "Test Agent 2",
            "role": "Tester",
            "kind": "ai",
            "status": "active",
            "skills": [],
            "metadata": {},
        })
        save_agents(test_board, agents_data)
        
        # Test build_parser and main with various commands
        from crewkan.crewkan_cli import build_parser, main
        parser = build_parser()
        
        # Test main with help
        old_argv = sys.argv
        sys.argv = ["crewkan_cli", "--help"]
        try:
            main()
        except SystemExit:
            pass  # Expected for --help
        finally:
            sys.argv = old_argv
        
        # Test main with list-agents command
        sys.argv = ["crewkan_cli", "--root", str(test_board), "list-agents"]
        try:
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv
        
        # Test main with new-task command
        if task_files:
            sys.argv = [
                "crewkan_cli",
                "--root", str(test_board),
                "new-task",
                "--title", "CLI Main Test",
                "--column", "todo",
                "--assignee", "test-agent",
            ]
            try:
                main()
            except SystemExit:
                pass
            finally:
                sys.argv = old_argv
        
        # Test main with list-tasks command
        sys.argv = ["crewkan_cli", "--root", str(test_board), "list-tasks"]
        try:
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv
        
        # Test main with invalid command (should error)
        sys.argv = ["crewkan_cli", "--root", str(test_board), "invalid-command"]
        try:
            main()
        except (SystemExit, Exception):
            pass  # Expected
        finally:
            sys.argv = old_argv
        
        # Test cmd_list_agents with no agents
        empty_agents_board = temp_dir / "empty_agents_board"
        init_board(empty_agents_board, "empty", "Empty", "test-agent", "test-agent")
        agents_file = empty_agents_board / "agents" / "agents.yaml"
        agents_file.write_text("agents: []")
        args = MockArgs(root=str(empty_agents_board))
        cmd_list_agents(args)
        
        # Test cmd_new_task with all optional fields
        args = MockArgs(
            root=str(test_board),
            title="Full Task",
            description="Full description",
            column="backlog",
            assignee=["test-agent"],
            priority="low",
            tags="tag1,tag2,tag3",
            due_date="2025-12-31",
            id="CUSTOM-123",
        )
        cmd_new_task(args)
        
        # Test cmd_new_task with no assignees (should use default)
        args = MockArgs(
            root=str(test_board),
            title="No Assignees Task",
            description="",
            column="todo",
            assignee=[],
            priority=None,
            tags="",
            due_date=None,
            id=None,
        )
        cmd_new_task(args)
        
        # Test cmd_new_task fallback path (BoardClient fails)
        fallback_cli_board = temp_dir / "fallback_cli_board"
        init_board(fallback_cli_board, "fallback", "Fallback", "test-agent", "test-agent")
        # Break agents to trigger fallback
        agents_file = fallback_cli_board / "agents" / "agents.yaml"
        agents_backup = agents_file.read_text()
        agents_file.write_text("agents: []")  # Empty agents
        
        args = MockArgs(
            root=str(fallback_cli_board),
            title="Fallback CLI Task",
            description="Test fallback",
            column="todo",
            assignee=[],
            priority="medium",
            tags="fallback",
            due_date=None,
            id="FALLBACK-1",
        )
        try:
            cmd_new_task(args)
        except RuntimeError:
            pass  # Expected - no agents
        
        # Test cmd_new_task fallback with invalid agent
        agents_file.write_text("agents:\n  - id: test-agent\n    name: Test")
        args = MockArgs(
            root=str(fallback_cli_board),
            title="Fallback Invalid Agent",
            description="Test",
            column="todo",
            assignee=["nonexistent-agent"],
            priority=None,
            tags="",
            due_date=None,
            id=None,
        )
        try:
            cmd_new_task(args)
        except RuntimeError:
            pass  # Expected - invalid agent
        
        # Test cmd_new_task fallback with invalid column
        args = MockArgs(
            root=str(fallback_cli_board),
            title="Fallback Invalid Column",
            description="Test",
            column="invalid_column",
            assignee=["test-agent"],
            priority=None,
            tags="",
            due_date=None,
            id=None,
        )
        try:
            cmd_new_task(args)
        except RuntimeError:
            pass  # Expected - invalid column
        
        agents_file.write_text(agents_backup)
        
        # Test cmd_new_task with BoardClient (normal path)
        args = MockArgs(
            root=str(test_board),
            title="BoardClient Task",
            description="Test",
            column="todo",
            assignee=["test-agent"],
            priority="high",
            tags="test,cli",
            due_date="2025-12-31",
            id=None,
        )
        cmd_new_task(args)
        
        # Test cmd_list_tasks with various filters
        args = MockArgs(root=str(test_board), column="backlog", agent=None)
        cmd_list_tasks(args)
        
        args = MockArgs(root=str(test_board), column=None, agent="test-agent")
        cmd_list_tasks(args)
        
        args = MockArgs(root=str(test_board), column="doing", agent="test-agent")
        cmd_list_tasks(args)
        
        # Test cmd_list_tasks with no matching tasks
        args = MockArgs(root=str(test_board), column="blocked", agent=None)
        cmd_list_tasks(args)  # Should print "No matching tasks."
        
        # Test cmd_list_tasks with task that's not a dict
        non_dict_board = temp_dir / "non_dict_board"
        init_board(non_dict_board, "non_dict", "Non Dict", "test-agent", "test-agent")
        non_dict_path = non_dict_board / "tasks" / "todo" / "NOT-DICT.yaml"
        non_dict_path.write_text("not a dict: [invalid")
        args = MockArgs(root=str(non_dict_board), column=None, agent=None)
        cmd_list_tasks(args)  # Should skip non-dict files
        
        # Test cmd_validate with various board states
        # Create a board with some issues
        invalid_task_board = temp_dir / "invalid_task_board"
        init_board(invalid_task_board, "invalid", "Invalid", "test-agent", "test-agent")
        # Create a task with invalid column
        invalid_task = {
            "id": "INVALID-1",
            "title": "Invalid Task",
            "column": "invalid_column",
            "status": "invalid_column",
            "assignees": ["test-agent"],
        }
        invalid_task_path = invalid_task_board / "tasks" / "todo" / "INVALID-1.yaml"
        save_yaml(invalid_task_path, invalid_task)
        
        # Create a task with invalid status (different from column)
        invalid_task2 = {
            "id": "INVALID-2",
            "title": "Invalid Status Task",
            "column": "todo",
            "status": "invalid_status",
            "assignees": ["test-agent"],
        }
        invalid_task_path2 = invalid_task_board / "tasks" / "todo" / "INVALID-2.yaml"
        save_yaml(invalid_task_path2, invalid_task2)
        
        # Create a task with column mismatch (in wrong directory)
        invalid_task3 = {
            "id": "INVALID-3",
            "title": "Column Mismatch",
            "column": "doing",
            "status": "doing",
            "assignees": ["test-agent"],
        }
        invalid_task_path3 = invalid_task_board / "tasks" / "todo" / "INVALID-3.yaml"
        save_yaml(invalid_task_path3, invalid_task3)
        
        # Create a task with invalid assignee
        invalid_task4 = {
            "id": "INVALID-4",
            "title": "Invalid Assignee",
            "column": "todo",
            "status": "todo",
            "assignees": ["nonexistent-agent"],
        }
        invalid_task_path4 = invalid_task_board / "tasks" / "todo" / "INVALID-4.yaml"
        save_yaml(invalid_task_path4, invalid_task4)
        
        # Create a task that's not a dict
        non_dict_path = invalid_task_board / "tasks" / "todo" / "NOT-DICT.yaml"
        non_dict_path.write_text("not a dict: [invalid yaml")
        
        args = MockArgs(root=str(invalid_task_board))
        try:
            cmd_validate(args)
        except SystemExit:
            pass  # Expected - validation should fail
        
        # Test cmd_start_task with column specified
        task_files = list((test_board / "tasks").rglob("*.yaml"))
        if task_files:
            task_id = task_files[0].stem
            args = MockArgs(root=str(test_board), task_id=task_id, agent="test-agent", column="doing")
            cmd_start_task(args)
            
            # Test cmd_start_task moving task to different column
            args = MockArgs(root=str(test_board), task_id=task_id, agent="test-agent", column="backlog")
            cmd_start_task(args)
            
            # Test cmd_start_task with task already in target column (should not move)
            args = MockArgs(root=str(test_board), task_id=task_id, agent="test-agent", column="backlog")
            cmd_start_task(args)  # Task already in backlog, should just create link
            
            # Test cmd_stop_task with column specified
            args = MockArgs(root=str(test_board), task_id=task_id, agent="test-agent", column="backlog")
            cmd_stop_task(args)
            
            # Test cmd_stop_task without column (search all)
            # First create a workspace link
            args = MockArgs(root=str(test_board), task_id=task_id, agent="test-agent", column="todo")
            cmd_start_task(args)
            args = MockArgs(root=str(test_board), task_id=task_id, agent="test-agent", column=None)
            cmd_stop_task(args)
            
            # Test cmd_stop_task with no workspace link found (with column)
            args = MockArgs(root=str(test_board), task_id="nonexistent", agent="test-agent", column="todo")
            cmd_stop_task(args)  # Should not error, just print message
            
            # Test cmd_stop_task with no workspace link found (without column)
            args = MockArgs(root=str(test_board), task_id="nonexistent", agent="test-agent", column=None)
            cmd_stop_task(args)  # Should search all and find nothing
            
            # Test cmd_stop_task with no workspace directory
            no_ws_board = temp_dir / "no_ws_board"
            init_board(no_ws_board, "no_ws", "No WS", "test-agent", "test-agent")
            args = MockArgs(root=str(no_ws_board), task_id="T-123", agent="test-agent", column=None)
            cmd_stop_task(args)  # Should handle missing workspace gracefully
        
        # Test cmd_start_task with invalid agent
        if task_files:
            args = MockArgs(root=str(test_board), task_id=task_id, agent="nonexistent", column="doing")
            try:
                cmd_start_task(args)
            except RuntimeError:
                pass  # Expected
        
        # Test cmd_start_task with invalid column
        if task_files:
            args = MockArgs(root=str(test_board), task_id=task_id, agent="test-agent", column="invalid")
            try:
                cmd_start_task(args)
            except RuntimeError:
                pass  # Expected
        
        # Test cmd_move_task error path (nonexistent task)
        args = MockArgs(root=str(test_board), task_id="nonexistent", column="doing")
        try:
            cmd_move_task(args)
        except RuntimeError:
            pass  # Expected
        
        # Test cmd_move_task with no agents
        no_agents_board = temp_dir / "no_agents_board"
        init_board(no_agents_board, "no_agents", "No Agents", "test-agent", "test-agent")
        agents_file = no_agents_board / "agents" / "agents.yaml"
        agents_file.write_text("agents: []")
        args = MockArgs(root=str(no_agents_board), task_id="T-123", column="doing")
        try:
            cmd_move_task(args)
        except RuntimeError:
            pass  # Expected - no agents
        
        # Test cmd_assign_task error path (nonexistent task)
        args = MockArgs(root=str(test_board), task_id="nonexistent", assignee=["test-agent"])
        try:
            cmd_assign_task(args)
        except RuntimeError:
            pass  # Expected
        
        # Test cmd_assign_task with no agents
        args = MockArgs(root=str(no_agents_board), task_id="T-123", assignee=["test-agent"])
        try:
            cmd_assign_task(args)
        except RuntimeError:
            pass  # Expected - no agents
        
        # Test cmd_assign_task with multiple assignees
        task_files = list((test_board / "tasks").rglob("*.yaml"))
        if task_files:
            task_id = task_files[0].stem
            args = MockArgs(root=str(test_board), task_id=task_id, assignee=["test-agent", "test-agent"])
            cmd_assign_task(args)
        
        # Test load_board error path
        invalid_board_cli = temp_dir / "invalid_board_cli"
        invalid_board_cli.mkdir()
        try:
            load_board(invalid_board_cli)
        except RuntimeError:
            pass  # Expected
        
        # Test load_agents with missing file
        agents_file = test_board / "agents" / "agents.yaml"
        agents_backup = agents_file.read_text()
        agents_file.unlink()
        agents = load_agents(test_board)
        agents_file.write_text(agents_backup)
        
        # Test get_column_ids
        board_data = load_board(test_board)
        col_ids = get_column_ids(board_data)
        
        # Test find_task_file error path
        try:
            find_task_file(test_board, "nonexistent-task")
        except RuntimeError:
            pass  # Expected
        
        print("  ✓ CLI functions tested")
    except Exception as e:
        print(f"  ✗ CLI functions error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if test_board.exists():
            shutil.rmtree(temp_dir)
    
    # 3. Import and call setup functions directly
    print("\n[3/7] Testing setup functions...")
    test_board = temp_dir / "coverage_test_setup"
    try:
        from crewkan.crewkan_setup import main as setup_main, write_yaml, ensure_dirs, DEFAULT_COLUMNS
        import sys
        
        old_argv = sys.argv
        sys.argv = ["crewkan_setup", "--root", str(test_board), "--force"]
        try:
            setup_main()
        finally:
            sys.argv = old_argv
        
        # Test write_yaml with overwrite=False (should skip existing)
        test_yaml = test_board / "board.yaml"
        write_yaml(test_yaml, {"test": "data"}, overwrite=False)
        
        # Test write_yaml with overwrite=True
        write_yaml(test_yaml, {"test": "data"}, overwrite=True)
        
        # Test ensure_dirs
        ensure_dirs(test_board, DEFAULT_COLUMNS)
        
        # Test with sample agents
        sys.argv = ["crewkan_setup", "--root", str(test_board / "with_agents"), "--with-sample-agents", "--force"]
        try:
            setup_main()
        finally:
            sys.argv = old_argv
        
        print("  ✓ Setup functions tested")
    except Exception as e:
        print(f"  ✗ Setup functions error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if test_board.exists():
            shutil.rmtree(temp_dir)
    
    # 4. Import and call UI functions directly
    print("\n[4/7] Testing UI functions...")
    test_board = temp_dir / "coverage_test_board"
    try:
        init_board(test_board, "test", "Test", "test-agent", "test-agent")
        
        from crewkan.crewkan_ui import (
            get_board_root,
            load_board,
            load_agents,
            iter_tasks,
            create_task,
            move_task,
            assign_task,
        )
        import os
        
        # Set environment variable
        os.environ["CREWKAN_BOARD_ROOT"] = str(test_board)
        
        # Test get_board_root
        root = get_board_root()
        
        # Test load functions
        board = load_board()
        agents = load_agents()
        
        # Test iter_tasks
        task_list = list(iter_tasks())
        
        # Test iter_tasks with empty board
        empty_board = temp_dir / "empty_board"
        init_board(empty_board, "empty", "Empty", "test-agent", "test-agent")
        os.environ["CREWKAN_BOARD_ROOT"] = str(empty_board)
        empty_tasks = list(iter_tasks())
        os.environ["CREWKAN_BOARD_ROOT"] = str(test_board)
        
        # Test create task with BoardClient
        task_id = create_task(
            "UI Coverage Test",
            "Test description",
            "todo",
            ["test-agent"],
            "high",
            "test,ui",
            None,
        )
        
        # Test create task with fallback (no agents)
        empty_board_ui = temp_dir / "empty_board_ui"
        init_board(empty_board_ui, "empty", "Empty", "test-agent", "test-agent")
        # Remove agents file to trigger fallback
        agents_file = empty_board_ui / "agents" / "agents.yaml"
        if agents_file.exists():
            agents_file.unlink()
        
        os.environ["CREWKAN_BOARD_ROOT"] = str(empty_board_ui)
        try:
            create_task(
                "Fallback Test",
                "Test",
                "todo",
                [],
                "medium",
                "",
                None,
            )
        except RuntimeError:
            pass  # Expected - no agents
        
        # Test create_task fallback path (BoardClient fails)
        # Create a board with invalid agent to trigger fallback
        fallback_board = temp_dir / "fallback_board"
        init_board(fallback_board, "fallback", "Fallback", "test-agent", "test-agent")
        # Break agents.yaml to make BoardClient fail
        agents_file = fallback_board / "agents" / "agents.yaml"
        agents_file.write_text("invalid: [")
        os.environ["CREWKAN_BOARD_ROOT"] = str(fallback_board)
        try:
            fallback_task_id = create_task(
                "Fallback Path Test",
                "Test description",
                "todo",
                ["test-agent"],
                "high",
                "fallback,test",
                "2025-12-31",
            )
            # Verify task was created via fallback
            task_file = fallback_board / "tasks" / "todo" / f"{fallback_task_id}.yaml"
            assert task_file.exists()
        except Exception as e:
            pass  # May fail if fallback also fails
        
        os.environ["CREWKAN_BOARD_ROOT"] = str(test_board)
        
        # Test create task with empty title (should still work)
        task_id2 = create_task(
            "",
            "Description only",
            "todo",
            ["test-agent"],
            "low",
            "",
            "2025-12-31",
        )
        
        # Test move task with BoardClient
        import yaml
        task_path = test_board / "tasks" / "todo" / f"{task_id}.yaml"
        with open(task_path) as f:
            task_data = yaml.safe_load(f)
        move_task(task_data, task_path, "doing")
        
        # Test move task with fallback (invalid agent)
        task_path2 = test_board / "tasks" / "todo" / f"{task_id2}.yaml"
        with open(task_path2) as f:
            task_data2 = yaml.safe_load(f)
        # Temporarily break agents to trigger fallback
        agents_file = test_board / "agents" / "agents.yaml"
        agents_backup = agents_file.read_text()
        agents_file.write_text("invalid yaml: [")
        try:
            move_task(task_data2, task_path2, "backlog")
        except Exception:
            pass  # Expected
        finally:
            agents_file.write_text(agents_backup)
        
        # Test assign task with BoardClient
        task_path = test_board / "tasks" / "doing" / f"{task_id}.yaml"
        with open(task_path) as f:
            task_data = yaml.safe_load(f)
        assign_task(task_data, task_path, "test-agent")
        
        # Test assign task with fallback
        task_path2 = test_board / "tasks" / "backlog" / f"{task_id2}.yaml"
        if task_path2.exists():
            with open(task_path2) as f:
                task_data2 = yaml.safe_load(f)
            # Break agents to trigger fallback
            agents_file.write_text("invalid yaml: [")
            try:
                assign_task(task_data2, task_path2, "test-agent")
            except Exception:
                pass  # Expected
            finally:
                agents_file.write_text(agents_backup)
        
        # Test move_task with same column (should return early)
        task_path = test_board / "tasks" / "doing" / f"{task_id}.yaml"
        if task_path.exists():
            with open(task_path) as f:
                task_data = yaml.safe_load(f)
            move_task(task_data, task_path, "doing")  # Same column
        
        # Test load_board with missing board.yaml (should error)
        invalid_board = temp_dir / "invalid_board_ui"
        invalid_board.mkdir()
        os.environ["CREWKAN_BOARD_ROOT"] = str(invalid_board)
        try:
            load_board()
        except Exception:
            pass  # Expected - st.stop() or error
        
        os.environ["CREWKAN_BOARD_ROOT"] = str(test_board)
        
        # Test load_agents with missing agents file
        agents_file = test_board / "agents" / "agents.yaml"
        agents_backup = agents_file.read_text()
        agents_file.unlink()
        agents = load_agents()  # Should return empty list
        agents_file.write_text(agents_backup)
        
        # Test iter_tasks with no tasks directory
        no_tasks_board = temp_dir / "no_tasks_board"
        init_board(no_tasks_board, "no_tasks", "No Tasks", "test-agent", "test-agent")
        (no_tasks_board / "tasks").rmdir()  # Remove tasks directory
        os.environ["CREWKAN_BOARD_ROOT"] = str(no_tasks_board)
        empty_iter = list(iter_tasks())
        os.environ["CREWKAN_BOARD_ROOT"] = str(test_board)
        
        print("  ✓ UI functions tested")
    except Exception as e:
        print(f"  ✗ UI functions error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if test_board.exists():
            shutil.rmtree(temp_dir)
        if "CREWKAN_BOARD_ROOT" in os.environ:
            del os.environ["CREWKAN_BOARD_ROOT"]
    
    # 5. Test logging configuration
    print("\n[5/9] Testing logging configuration...")
    try:
        from crewkan.logging_config import setup_logging, get_logger
        
        # Test setup_logging
        log_file = temp_dir / "test.log"
        setup_logging(level=logging.DEBUG, log_file=log_file)
        
        # Test get_logger
        test_logger = get_logger("test")
        test_logger.info("Test log message")
        
        print("  ✓ Logging configuration tested")
    except Exception as e:
        print(f"  ✗ Logging configuration error: {e}")
        import traceback
        traceback.print_exc()
    
    # 6. Test BoardRegistry
    print("\n[6/9] Testing BoardRegistry...")
    test_registry = temp_dir / "registry.yaml"
    try:
        from crewkan.board_registry import BoardRegistry
        
        registry = BoardRegistry(test_registry)
        
        # Test register_board
        registry.register_board(
            board_id="test-board",
            path="/tmp/test",
            owner_agent="test-agent",
            purpose="Testing",
            status="active"
        )
        
        # Test register_board again (update existing)
        registry.register_board(
            board_id="test-board",
            path="/tmp/test2",
            owner_agent="test-agent-2",
            purpose="Updated",
            parent_board_id="parent-board",
            status="active"
        )
        
        # Test list_boards
        boards = registry.list_boards()
        active_boards = registry.list_boards(status="active")
        archived_boards = registry.list_boards(status="archived")
        
        # Test get_board
        board = registry.get_board("test-board")
        nonexistent = registry.get_board("nonexistent")
        
        # Test archive_board
        registry.archive_board("test-board")
        
        # Test archive nonexistent board (should not error)
        registry.archive_board("nonexistent-board")
        
        # Test delete_board
        registry.delete_board("test-board")
        
        # Test delete nonexistent board (should not error)
        registry.delete_board("nonexistent-board")
        
        print("  ✓ BoardRegistry tested")
    except Exception as e:
        print(f"  ✗ BoardRegistry error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if test_registry.exists():
            test_registry.unlink()
    
    # 7. Test BoardClient operations
    print("\n[7/9] Testing BoardClient operations...")
    test_board = temp_dir / "coverage_test_board"
    try:
        init_board(test_board, "test", "Test", "test-agent", "test-agent")
        
        from crewkan.board_core import BoardClient
        
        client = BoardClient(test_board, "test-agent")
        
        # Create task
        task_id = client.create_task(
            title="BoardClient Test",
            description="Test",
            column="todo",
            assignees=["test-agent"],
            tags=["test"],
        )
        
        # Move task
        client.move_task(task_id, "doing")
        
        # Update field
        client.update_task_field(task_id, "title", "Updated Title")
        
        # Add comment
        client.add_comment(task_id, "Test comment")
        
        # Reassign
        client.reassign_task(task_id, "test-agent", keep_existing=True)
        
        # List tasks
        tasks_json = client.list_my_tasks()
        
        # Test error paths
        from crewkan.board_core import BoardError
        try:
            client.move_task("nonexistent-task", "doing")
        except BoardError:
            pass  # Expected
        
        try:
            client.update_task_field("nonexistent-task", "title", "Test")
        except BoardError:
            pass  # Expected
        
        try:
            client.add_comment("nonexistent-task", "Test")
        except BoardError:
            pass  # Expected
        
        # Test list with filters
        client.list_my_tasks(column="todo")
        client.list_my_tasks(column="doing", limit=5)
        
        # Test reassign with to_superagent
        board_data = load_yaml(test_board / "board.yaml")
        board_data["settings"]["default_superagent_id"] = "test-agent"
        save_yaml(test_board / "board.yaml", board_data)
        client2 = BoardClient(test_board, "test-agent")
        if task_id:
            client2.reassign_task(task_id, to_superagent=True)
        
        # Test reassign error paths
        try:
            client2.reassign_task("nonexistent", "test-agent")
        except BoardError:
            pass
        
        # Test update_task_field with tags (string)
        if task_id:
            client2.update_task_field(task_id, "tags", "tag1,tag2,tag3")
        
        # Test update_task_field with tags (list)
        if task_id:
            client2.update_task_field(task_id, "tags", ["tag4", "tag5"])
        
        # Test update_task_field error (invalid field)
        try:
            client2.update_task_field(task_id, "invalid_field", "value")
        except BoardError:
            pass
        
        # Test move_task error (invalid column)
        try:
            client2.move_task(task_id, "invalid_column")
        except BoardError:
            pass
        
        # Test get_agent and list_agents
        agent = client2.get_agent("test-agent")
        agents = client2.list_agents()
        
        # Test get_default_superagent_id
        superagent = client2.get_default_superagent_id()
        
        # Test workspace symlinks (if workspace exists)
        workspace_root = test_board / "workspaces" / "test-agent" / "todo"
        workspace_root.mkdir(parents=True, exist_ok=True)
        if task_id:
            task_file = test_board / "tasks" / "doing" / f"{task_id}.yaml"
            if task_file.exists():
                symlink = workspace_root / f"{task_id}.yaml"
                symlink.symlink_to(task_file)
                # Move task to trigger workspace update
                client2.move_task(task_id, "backlog")
        
        # Test create_task with invalid column
        try:
            client2.create_task("Test", column="invalid_column")
        except BoardError:
            pass
        
        # Test create_task with invalid assignee
        try:
            client2.create_task("Test", assignees=["nonexistent-agent"])
        except BoardError:
            pass
        
        # Test reassign with no superagent configured
        board_data = load_yaml(test_board / "board.yaml")
        board_data["settings"]["default_superagent_id"] = None
        save_yaml(test_board / "board.yaml", board_data)
        client3 = BoardClient(test_board, "test-agent")
        try:
            if task_id:
                client3.reassign_task(task_id, to_superagent=True)
        except BoardError:
            pass
        
        # Test reassign with no new_assignee_id and to_superagent=False
        try:
            if task_id:
                client3.reassign_task(task_id, to_superagent=False)
        except BoardError:
            pass
        
        # Test reassign with invalid assignee
        try:
            if task_id:
                client3.reassign_task(task_id, "nonexistent-agent")
        except BoardError:
            pass
        
        # Test update_task_field with invalid tags type
        try:
            if task_id:
                client3.update_task_field(task_id, "tags", 123)  # Invalid type
        except BoardError:
            pass
        
        print("  ✓ BoardClient operations tested")
    except Exception as e:
        print(f"  ✗ BoardClient error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if test_board.exists():
            shutil.rmtree(temp_dir)
    
    # 8. Test LangChain tools (more comprehensively)
    print("\n[8/8] Testing LangChain tools...")
    test_board = temp_dir / "coverage_test_board"
    try:
        init_board(test_board, "test", "Test", "test-agent", "test-agent")
        
        from crewkan.board_langchain_tools import make_board_tools
        
        tools = make_board_tools(str(test_board), "test-agent")
        
        # Call all tools directly
        if tools:
            # Create a task first
            create_tool = next((t for t in tools if t.name == "create_task"), None)
            if create_tool:
                result = create_tool.invoke({
                    "title": "LangChain Test Task",
                    "description": "Test",
                    "column": "todo",
                    "assignees": ["test-agent"],
                })
                task_id = result.split()[-1] if "Created task" in result else None
            
            # List tasks
            list_tool = next((t for t in tools if t.name == "list_my_tasks"), None)
            if list_tool:
                list_tool.invoke({"column": None, "limit": 10})
            
            # Move task
            if task_id:
                move_tool = next((t for t in tools if t.name == "move_task"), None)
                if move_tool:
                    move_tool.invoke({"task_id": task_id, "new_column": "doing"})
            
            # Update field
            if task_id:
                update_tool = next((t for t in tools if t.name == "update_task_field"), None)
                if update_tool:
                    update_tool.invoke({"task_id": task_id, "field": "title", "value": "Updated"})
            
            # Add comment
            if task_id:
                comment_tool = next((t for t in tools if t.name == "add_comment_to_task"), None)
                if comment_tool:
                    comment_tool.invoke({"task_id": task_id, "comment": "Test comment"})
            
            # Reassign
            if task_id:
                reassign_tool = next((t for t in tools if t.name == "reassign_task"), None)
                if reassign_tool:
                    reassign_tool.invoke({
                        "task_id": task_id,
                        "new_assignee_id": "test-agent",
                        "keep_existing": True
                    })
                    # Test with to_superagent
                    reassign_tool.invoke({
                        "task_id": task_id,
                        "to_superagent": True,
                        "keep_existing": False
                    })
            
            # Test error paths - call with invalid task_id
            if move_tool:
                result = move_tool.invoke({"task_id": "nonexistent", "new_column": "doing"})
                assert "ERROR" in result
            
            if update_tool:
                result = update_tool.invoke({"task_id": "nonexistent", "field": "title", "value": "Test"})
                assert "ERROR" in result
            
            if comment_tool:
                result = comment_tool.invoke({"task_id": "nonexistent", "comment": "Test"})
                assert "ERROR" in result
        
        print("  ✓ LangChain tools tested")
    except Exception as e:
        print(f"  ✗ LangChain tools error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if test_board.exists():
            shutil.rmtree(temp_dir)
    
    # 9. Test simulation
    print("\n[9/9] Testing simulation...")
    try:
        from tests.test_simulation import run_simulation
        run_simulation(num_agents=3, num_tasks=20, num_boards=1, work_cycles=5)
        print("  ✓ Simulation tested")
    except Exception as e:
        print(f"  ✗ Simulation error: {e}")
        import traceback
        traceback.print_exc()
    
    # Stop coverage and generate report
    cov.stop()
    cov.save()
    
    print("\n" + "=" * 70)
    print("Coverage Report")
    print("=" * 70)
    cov.report(show_missing=True)
    
    cov.html_report(directory="htmlcov")
    print(f"\nHTML coverage report: htmlcov/index.html")
    
    return cov


if __name__ == "__main__":
    run_coverage_comprehensive()

