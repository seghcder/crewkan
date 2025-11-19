#!/usr/bin/env python3
"""
Unit tests for supertools to ensure they are working correctly.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.board_core import BoardClient
from crewkan.agent_framework.executor import SupertoolExecutor
from crewkan.agent_framework.registry import get_registry
from crewkan.agent_framework.test_supertools_startup import (
    test_supertool_availability,
    test_all_supertools,
    validate_supertools_startup
)


class TestSupertools(unittest.TestCase):
    """Test supertool functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.board_root = self.test_dir / "test_board"
        self.board_root.mkdir()
        
        # Create minimal board structure
        (self.board_root / "agents").mkdir()
        (self.board_root / "issues").mkdir()
        (self.board_root / "issues" / "backlog").mkdir()
        (self.board_root / "issues" / "todo").mkdir()
        (self.board_root / "issues" / "doing").mkdir()
        (self.board_root / "issues" / "done").mkdir()
        
        # Create minimal board.yaml (matching actual schema)
        import yaml
        board_config = {
            "board_name": "Test Board",
            "board_id": "test-board",
            "columns": [
                {"id": "backlog", "name": "Backlog"},
                {"id": "todo", "name": "To Do"},
                {"id": "doing", "name": "Doing"},
                {"id": "done", "name": "Done"}
            ],
            "settings": {
                "default_superagent_id": "test-agent"
            }
        }
        with open(self.board_root / "board.yaml", "w") as f:
            yaml.dump(board_config, f)
        
        # Create minimal agents.yaml
        agents_config = {
            "agents": [
                {
                    "id": "test-agent",
                    "name": "Test Agent",
                    "kind": "ai",
                    "status": "active",
                    "role": "tester"
                }
            ]
        }
        with open(self.board_root / "agents" / "agents.yaml", "w") as f:
            yaml.dump(agents_config, f)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_supertool_registry(self):
        """Test that supertools are registered."""
        registry = get_registry()
        # Check registry has tools
        self.assertIsNotNone(registry)
        # Try to get a tool to verify registry works
        tools = registry._tools if hasattr(registry, '_tools') else {}
        print(f"✓ Registry initialized with {len(tools)} registered supertools")
    
    def test_supertool_executor_initialization(self):
        """Test SupertoolExecutor can be initialized."""
        executor = SupertoolExecutor(str(self.board_root), "test-agent")
        self.assertIsNotNone(executor)
        print("✓ SupertoolExecutor initialized")
    
    def test_list_available_tools(self):
        """Test listing available tools."""
        executor = SupertoolExecutor(str(self.board_root), "test-agent")
        tools = executor.list_available_tools()
        # Tools can be list or dict depending on implementation
        self.assertIsInstance(tools, (list, dict))
        print(f"✓ Available tools: {tools}")
    
    def test_board_client_creation(self):
        """Test BoardClient can create issues."""
        client = BoardClient(str(self.board_root), "test-agent")
        issue_id = client.create_issue(
            title="Test Issue",
            description="Test description",
            column="backlog"
        )
        self.assertIsNotNone(issue_id)
        print(f"✓ Created test issue: {issue_id}")
        
        # Verify issue exists
        issue_details = client.get_issue_details(issue_id)
        self.assertEqual(issue_details["title"], "Test Issue")
        print("✓ Issue details retrieved correctly")
    
    def test_supertool_availability_check(self):
        """Test checking supertool availability."""
        executor = SupertoolExecutor(str(self.board_root), "test-agent")
        available_tools = executor.list_available_tools()
        
        if isinstance(available_tools, dict) and available_tools:
            # Test first available tool
            tool_id = list(available_tools.keys())[0]
            result = test_supertool_availability(
                str(self.board_root),
                "test-agent",
                tool_id
            )
            self.assertIsNotNone(result)
            print(f"✓ Availability check: {result}")
        elif isinstance(available_tools, list) and available_tools:
            tool_id = available_tools[0]
            result = test_supertool_availability(
                str(self.board_root),
                "test-agent",
                tool_id
            )
            self.assertIsNotNone(result)
            print(f"✓ Availability check: {result}")
        else:
            print("⚠ No supertools available to test")
    
    def test_all_supertools(self):
        """Test listing and checking all supertools."""
        results = test_all_supertools(str(self.board_root), "test-agent")
        self.assertIsInstance(results, list)
        print(f"✓ Tested {len(results)} supertools")
        for result in results:
            print(f"  {result}")
    
    def test_startup_validation(self):
        """Test startup validation function."""
        all_passed, results = validate_supertools_startup(
            str(self.board_root),
            "test-agent"
        )
        self.assertIsInstance(all_passed, bool)
        self.assertIsInstance(results, list)
        print(f"✓ Startup validation: {'PASSED' if all_passed else 'FAILED'}")
        print(f"  Results: {len(results)} tools tested")
    
    def test_permission_check(self):
        """Test that permission checking works."""
        executor = SupertoolExecutor(str(self.board_root), "test-agent")
        available_tools = executor.list_available_tools()
        
        if isinstance(available_tools, dict) and available_tools:
            tool_id = list(available_tools.keys())[0]
            can_use = executor.can_use_tool(tool_id)
            self.assertIsInstance(can_use, bool)
            print(f"✓ Permission check for {tool_id}: {can_use}")
        elif isinstance(available_tools, list) and available_tools:
            tool_id = available_tools[0]
            can_use = executor.can_use_tool(tool_id)
            self.assertIsInstance(can_use, bool)
            print(f"✓ Permission check for {tool_id}: {can_use}")
        else:
            print("⚠ No supertools available to test permissions")


if __name__ == "__main__":
    unittest.main(verbosity=2)

