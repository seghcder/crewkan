#!/usr/bin/env python3
"""
Comprehensive coverage test that includes all test types.

This imports and calls functions directly (not via subprocess) so coverage tracks them.
"""

import sys
import tempfile
import shutil
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
    print("\n[1/6] Testing setup functions...")
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
    except Exception as e:
        print(f"  ✗ Board initialization error: {e}")
    finally:
        if test_board.exists():
            shutil.rmtree(temp_dir)
    
    # 2. Import and call CLI functions directly
    print("\n[2/6] Testing CLI functions...")
    test_board = temp_dir / "coverage_test_board"
    try:
        init_board(test_board, "test", "Test", "test-agent", "test-agent")
        
        from crewkan.crewkan_cli import (
            cmd_list_agents,
            cmd_add_agent,
            cmd_new_task,
            cmd_list_tasks,
            cmd_move_task,
            cmd_assign_task,
        )
        import argparse
        
        # Create mock args
        class MockArgs:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        # Test list agents
        args = MockArgs(root=str(test_board))
        cmd_list_agents(args)
        
        # Test add agent
        args = MockArgs(root=str(test_board), id="coverage-agent", name="Coverage Agent", role="Tester", kind="ai")
        cmd_add_agent(args)
        
        # Test new task
        args = MockArgs(
            root=str(test_board),
            title="Coverage Test Task",
            description="Test",
            column="todo",
            assignee=["coverage-agent"],
            priority="high",
            tags="test,coverage",
            due_date=None,
            id=None,
        )
        cmd_new_task(args)
        
        # Test list tasks
        args = MockArgs(root=str(test_board), column=None, agent=None)
        cmd_list_tasks(args)
        
        print("  ✓ CLI functions tested")
    except Exception as e:
        print(f"  ✗ CLI functions error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if test_board.exists():
            shutil.rmtree(temp_dir)
    
    # 3. Import and call UI functions directly
    print("\n[3/6] Testing UI functions...")
    test_board = temp_dir / "coverage_test_board"
    try:
        init_board(test_board, "test", "Test", "test-agent", "test-agent")
        
        from crewkan.crewkan_ui import (
            load_board,
            load_agents,
            create_task,
            move_task,
            assign_task,
        )
        import os
        
        # Set environment variable
        os.environ["CREWKAN_BOARD_ROOT"] = str(test_board)
        
        # Test load functions
        board = load_board()
        agents = load_agents()
        
        # Test create task
        task_id = create_task(
            "UI Coverage Test",
            "Test description",
            "todo",
            ["test-agent"],
            "high",
            "test,ui",
            None,
        )
        
        # Test move task
        import yaml
        task_path = test_board / "tasks" / "todo" / f"{task_id}.yaml"
        with open(task_path) as f:
            task_data = yaml.safe_load(f)
        move_task(task_data, task_path, "doing")
        
        # Test assign task
        task_path = test_board / "tasks" / "doing" / f"{task_id}.yaml"
        with open(task_path) as f:
            task_data = yaml.safe_load(f)
        assign_task(task_data, task_path, "test-agent")
        
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
    
    # 4. Test BoardClient operations
    print("\n[4/6] Testing BoardClient operations...")
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
        
        print("  ✓ BoardClient operations tested")
    except Exception as e:
        print(f"  ✗ BoardClient error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if test_board.exists():
            shutil.rmtree(temp_dir)
    
    # 5. Test LangChain tools
    print("\n[5/6] Testing LangChain tools...")
    test_board = temp_dir / "coverage_test_board"
    try:
        init_board(test_board, "test", "Test", "test-agent", "test-agent")
        
        from crewkan.board_langchain_tools import make_board_tools
        
        tools = make_board_tools(str(test_board), "test-agent")
        
        # Call tools directly
        if tools:
            list_tool = next((t for t in tools if t.name == "list_my_tasks"), None)
            if list_tool:
                list_tool.invoke({"column": None, "limit": 10})
        
        print("  ✓ LangChain tools tested")
    except Exception as e:
        print(f"  ✗ LangChain tools error: {e}")
    finally:
        if test_board.exists():
            shutil.rmtree(temp_dir)
    
    # 6. Test simulation
    print("\n[6/6] Testing simulation...")
    try:
        from tests.test_simulation import run_simulation
        run_simulation(num_agents=3, num_tasks=20, num_boards=1, work_cycles=5)
        print("  ✓ Simulation tested")
    except Exception as e:
        print(f"  ✗ Simulation error: {e}")
    
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

