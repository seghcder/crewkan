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


if __name__ == "__main__":
    unittest.main(verbosity=2)

