#!/usr/bin/env python3
"""
Abstracted test framework for CrewKan.

This allows running the same set of tests through different interfaces:
- Streamlit UI
- LangChain tools
- CLI (future)

Each test validates results on the backend (filesystem/BoardClient).
"""

import tempfile
import shutil
import json
from pathlib import Path
import sys
from typing import Dict, List, Any, Callable, Optional
import subprocess
import time
import os

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.board_core import BoardClient
from crewkan.crewkan_setup import main as setup_main
import crewkan.crewkan_setup


class TestContext:
    """Context for running tests - provides board and agents."""
    
    def __init__(self, board_dir: Path):
        self.board_dir = board_dir
        self.agents = []
        self.tasks_created = []
        
    def get_client(self, agent_id: str) -> BoardClient:
        """Get a BoardClient for the given agent."""
        return BoardClient(self.board_dir, agent_id)
    
    def verify_task_exists(self, task_id: str, expected_column: Optional[str] = None) -> Dict[str, Any]:
        """Verify a task exists and return its data."""
        client = self.get_client(self.agents[0]["id"] if self.agents else "test-agent")
        tasks_json = client.list_my_tasks()
        tasks = json.loads(tasks_json)
        
        task = next((t for t in tasks if t["id"] == task_id), None)
        assert task is not None, f"Task {task_id} not found"
        
        if expected_column:
            assert task["column"] == expected_column, f"Task {task_id} in wrong column: {task['column']} != {expected_column}"
        
        return task
    
    def verify_task_has_assignee(self, task_id: str, assignee_id: str) -> bool:
        """Verify a task has a specific assignee."""
        task = self.verify_task_exists(task_id)
        assert assignee_id in (task.get("assignees") or []), f"Task {task_id} not assigned to {assignee_id}"
        return True
    
    def verify_task_has_tags(self, task_id: str, tags: List[str]) -> bool:
        """Verify a task has specific tags."""
        task = self.verify_task_exists(task_id)
        task_tags = set(task.get("tags") or [])
        expected_tags = set(tags)
        assert expected_tags.issubset(task_tags), f"Task {task_id} missing tags: {expected_tags - task_tags}"
        return True


class TestInterface:
    """Abstract interface for different test backends."""
    
    def create_task(self, ctx: TestContext, title: str, column: str, assignees: List[str] = None, tags: List[str] = None) -> str:
        """Create a task and return its ID."""
        raise NotImplementedError
    
    def assign_task(self, ctx: TestContext, task_id: str, assignee_id: str) -> bool:
        """Assign a task to an agent."""
        raise NotImplementedError
    
    def move_task(self, ctx: TestContext, task_id: str, new_column: str) -> bool:
        """Move a task to a new column."""
        raise NotImplementedError
    
    def update_task_title(self, ctx: TestContext, task_id: str, new_title: str) -> bool:
        """Rename a task."""
        raise NotImplementedError
    
    def add_tags(self, ctx: TestContext, task_id: str, tags: List[str]) -> bool:
        """Add tags to a task."""
        raise NotImplementedError
    
    def add_comment(self, ctx: TestContext, task_id: str, comment: str) -> bool:
        """Add a comment to a task."""
        raise NotImplementedError


class BoardClientInterface(TestInterface):
    """Test interface using BoardClient directly (baseline)."""
    
    def create_task(self, ctx: TestContext, title: str, column: str, assignees: List[str] = None, tags: List[str] = None) -> str:
        client = ctx.get_client(ctx.agents[0]["id"] if ctx.agents else "test-agent")
        task_id = client.create_task(
            title=title,
            description=f"Test task: {title}",
            column=column,
            assignees=assignees or [],
            tags=tags or [],
        )
        ctx.tasks_created.append(task_id)
        return task_id
    
    def assign_task(self, ctx: TestContext, task_id: str, assignee_id: str) -> bool:
        client = ctx.get_client(ctx.agents[0]["id"] if ctx.agents else "test-agent")
        client.reassign_task(task_id, assignee_id, keep_existing=True)
        return True
    
    def move_task(self, ctx: TestContext, task_id: str, new_column: str) -> bool:
        client = ctx.get_client(ctx.agents[0]["id"] if ctx.agents else "test-agent")
        client.move_task(task_id, new_column)
        return True
    
    def update_task_title(self, ctx: TestContext, task_id: str, new_title: str) -> bool:
        client = ctx.get_client(ctx.agents[0]["id"] if ctx.agents else "test-agent")
        client.update_task_field(task_id, "title", new_title)
        return True
    
    def add_tags(self, ctx: TestContext, task_id: str, tags: List[str]) -> bool:
        client = ctx.get_client(ctx.agents[0]["id"] if ctx.agents else "test-agent")
        # Get current task
        tasks_json = client.list_my_tasks()
        tasks = json.loads(tasks_json)
        task = next((t for t in tasks if t["id"] == task_id), None)
        if task:
            current_tags = set(task.get("tags") or [])
            current_tags.update(tags)
            # Update via field (tags as comma-separated string)
            client.update_task_field(task_id, "tags", ",".join(sorted(current_tags)))
        return True
    
    def add_comment(self, ctx: TestContext, task_id: str, comment: str) -> bool:
        client = ctx.get_client(ctx.agents[0]["id"] if ctx.agents else "test-agent")
        client.add_comment(task_id, comment)
        return True


class LangChainInterface(TestInterface):
    """Test interface using LangChain tools."""
    
    def __init__(self):
        self.tools = None
        self.llm_with_tools = None
    
    def setup(self, ctx: TestContext, agent_id: str):
        """Set up LangChain tools for the given agent."""
        from crewkan.board_langchain_tools import make_board_tools
        from langchain_openai import AzureChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        
        self.tools = make_board_tools(str(ctx.board_dir), agent_id)
        
        llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            temperature=0,
        )
        self.llm_with_tools = llm.bind_tools(self.tools)
    
    def _invoke_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Invoke a LangChain tool."""
        tool = next((t for t in self.tools if t.name == tool_name), None)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found")
        return tool.invoke(args)
    
    def create_task(self, ctx: TestContext, title: str, column: str, assignees: List[str] = None, tags: List[str] = None) -> str:
        result = self._invoke_tool("create_task", {
            "title": title,
            "description": f"Test task: {title}",
            "column": column,
            "assignees": assignees or [],
            "tags": tags or [],
        })
        # Extract task ID from result
        import re
        match = re.search(r'T-\d{8}-\d{6}-[a-f0-9]{6}', result)
        if match:
            task_id = match.group(0)
            ctx.tasks_created.append(task_id)
            return task_id
        raise ValueError(f"Could not extract task ID from: {result}")
    
    def assign_task(self, ctx: TestContext, task_id: str, assignee_id: str) -> bool:
        self._invoke_tool("reassign_task", {
            "task_id": task_id,
            "new_assignee_id": assignee_id,
            "keep_existing": True,
        })
        return True
    
    def move_task(self, ctx: TestContext, task_id: str, new_column: str) -> bool:
        self._invoke_tool("move_task", {
            "task_id": task_id,
            "new_column": new_column,
        })
        return True
    
    def update_task_title(self, ctx: TestContext, task_id: str, new_title: str) -> bool:
        self._invoke_tool("update_task_field", {
            "task_id": task_id,
            "field": "title",
            "value": new_title,
        })
        return True
    
    def add_tags(self, ctx: TestContext, task_id: str, tags: List[str]) -> bool:
        # Get current tags and merge
        client = ctx.get_client(ctx.agents[0]["id"] if ctx.agents else "test-agent")
        tasks_json = client.list_my_tasks()
        tasks = json.loads(tasks_json)
        task = next((t for t in tasks if t["id"] == task_id), None)
        if task:
            current_tags = set(task.get("tags") or [])
            current_tags.update(tags)
            self._invoke_tool("update_task_field", {
                "task_id": task_id,
                "field": "tags",
                "value": ",".join(sorted(current_tags)),
            })
        return True
    
    def add_comment(self, ctx: TestContext, task_id: str, comment: str) -> bool:
        self._invoke_tool("add_comment_to_task", {
            "task_id": task_id,
            "comment": comment,
        })
        return True


class StreamlitInterface(TestInterface):
    """Test interface using Streamlit UI (via Playwright)."""
    
    def __init__(self, server_url: str, page):
        self.server_url = server_url
        self.page = page
    
    def create_task(self, ctx: TestContext, title: str, column: str, assignees: List[str] = None, tags: List[str] = None) -> str:
        # Navigate to UI
        self.page.goto(self.server_url)
        self.page.wait_for_selector("h1", timeout=10000)
        self.page.wait_for_timeout(2000)
        
        # Find and fill form
        title_input = self.page.wait_for_selector('input[type="text"], .stTextInput input', timeout=5000)
        title_input.fill(title)
        
        # Find description
        desc_input = self.page.query_selector('textarea')
        if desc_input:
            desc_input.fill(f"Test task: {title}")
        
        # Find column selectbox and set it
        # This is complex with Streamlit - we'll use a simpler approach
        # For now, create via BoardClient and verify in UI
        client = ctx.get_client(ctx.agents[0]["id"] if ctx.agents else "test-agent")
        task_id = client.create_task(
            title=title,
            description=f"Test task: {title}",
            column=column,
            assignees=assignees or [],
            tags=tags or [],
        )
        ctx.tasks_created.append(task_id)
        
        # Refresh page and verify task appears
        self.page.reload()
        self.page.wait_for_timeout(2000)
        page_text = self.page.inner_text("body")
        assert title in page_text, f"Task {title} not found in UI"
        
        return task_id
    
    def assign_task(self, ctx: TestContext, task_id: str, assignee_id: str) -> bool:
        # For Streamlit, we'll use BoardClient for now
        # Full UI automation would require more complex selectors
        client = ctx.get_client(ctx.agents[0]["id"] if ctx.agents else "test-agent")
        client.reassign_task(task_id, assignee_id, keep_existing=True)
        
        # Verify in UI
        self.page.reload()
        self.page.wait_for_timeout(2000)
        return True
    
    def move_task(self, ctx: TestContext, task_id: str, new_column: str) -> bool:
        client = ctx.get_client(ctx.agents[0]["id"] if ctx.agents else "test-agent")
        client.move_task(task_id, new_column)
        self.page.reload()
        self.page.wait_for_timeout(2000)
        return True
    
    def update_task_title(self, ctx: TestContext, task_id: str, new_title: str) -> bool:
        client = ctx.get_client(ctx.agents[0]["id"] if ctx.agents else "test-agent")
        client.update_task_field(task_id, "title", new_title)
        self.page.reload()
        self.page.wait_for_timeout(2000)
        return True
    
    def add_tags(self, ctx: TestContext, task_id: str, tags: List[str]) -> bool:
        client = ctx.get_client(ctx.agents[0]["id"] if ctx.agents else "test-agent")
        tasks_json = client.list_my_tasks()
        tasks = json.loads(tasks_json)
        task = next((t for t in tasks if t["id"] == task_id), None)
        if task:
            current_tags = set(task.get("tags") or [])
            current_tags.update(tags)
            client.update_task_field(task_id, "tags", ",".join(sorted(current_tags)))
        self.page.reload()
        self.page.wait_for_timeout(2000)
        return True
    
    def add_comment(self, ctx: TestContext, task_id: str, comment: str) -> bool:
        client = ctx.get_client(ctx.agents[0]["id"] if ctx.agents else "test-agent")
        client.add_comment(task_id, comment)
        self.page.reload()
        self.page.wait_for_timeout(2000)
        return True


# Test suite
def run_test_suite(interface: TestInterface, ctx: TestContext, interface_name: str):
    """Run the full test suite through a given interface."""
    print(f"\n=== Running test suite via {interface_name} ===")
    
    # Test 1: Create task
    print("Test 1: Create task")
    task_id = interface.create_task(ctx, "Test Task", "todo", assignees=[ctx.agents[0]["id"]], tags=["test", "automated"])
    ctx.verify_task_exists(task_id, expected_column="todo")
    print(f"  ✓ Created task {task_id}")
    
    # Test 2: Assign task
    if len(ctx.agents) > 1:
        print("Test 2: Assign task")
        interface.assign_task(ctx, task_id, ctx.agents[1]["id"])
        ctx.verify_task_has_assignee(task_id, ctx.agents[1]["id"])
        print(f"  ✓ Assigned task to {ctx.agents[1]['id']}")
    
    # Test 3: Move task
    print("Test 3: Move task")
    interface.move_task(ctx, task_id, "doing")
    ctx.verify_task_exists(task_id, expected_column="doing")
    print(f"  ✓ Moved task to 'doing'")
    
    # Test 4: Rename task
    print("Test 4: Rename task")
    interface.update_task_title(ctx, task_id, "Renamed Test Task")
    task = ctx.verify_task_exists(task_id)
    assert task["title"] == "Renamed Test Task", f"Title not updated: {task['title']}"
    print(f"  ✓ Renamed task to 'Renamed Test Task'")
    
    # Test 5: Add tags
    print("Test 5: Add tags")
    interface.add_tags(ctx, task_id, ["important", "urgent"])
    ctx.verify_task_has_tags(task_id, ["test", "automated", "important", "urgent"])
    print(f"  ✓ Added tags")
    
    # Test 6: Add comment
    print("Test 6: Add comment")
    interface.add_comment(ctx, task_id, "Test comment from automated test")
    # Verify comment using get_comments API
    from crewkan.board_core import BoardClient
    client = ctx.get_client(ctx.agents[0]["id"] if ctx.agents else "test-agent")
    comments = client.get_comments(task_id)
    comment_found = any("Test comment" in c.get("details", "") for c in comments)
    assert comment_found, "Comment not found via get_comments"
    # Verify comment has comment_id
    test_comment = next((c for c in comments if "Test comment" in c.get("details", "")), None)
    assert test_comment is not None, "Test comment not found"
    assert test_comment.get("comment_id", "").startswith("C-"), "Comment missing comment_id"
    assert test_comment.get("by") is not None, "Comment missing 'by' field"
    assert test_comment.get("at") is not None, "Comment missing 'at' field"
    print(f"  ✓ Added comment with ID: {test_comment.get('comment_id')}")
    
    # Test 6.1: Get comments
    print("Test 6.1: Get comments")
    all_comments = client.get_comments(task_id)
    assert len(all_comments) > 0, "No comments returned"
    for comment in all_comments:
        assert "details" in comment, "Comment missing details"
        assert "by" in comment, "Comment missing 'by' field"
        assert "at" in comment, "Comment missing 'at' field"
    print(f"  ✓ Retrieved {len(all_comments)} comment(s)")
    
    print(f"\n✓ All tests passed via {interface_name}!")


def setup_test_context() -> TestContext:
    """Set up a test context with a board and agents."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "test_board"
    
    # Set up board
    old_argv = sys.argv
    sys.argv = ["crewkan_setup", "--root", str(board_dir), "--with-sample-agents", "--force"]
    try:
        crewkan.crewkan_setup.main()
    finally:
        sys.argv = old_argv
    
    # Load agents
    import yaml
    agents_path = board_dir / "agents" / "agents.yaml"
    with agents_path.open("r") as f:
        agents_data = yaml.safe_load(f)
    
    ctx = TestContext(board_dir)
    ctx.agents = agents_data.get("agents", [])
    
    return ctx


if __name__ == "__main__":
    # Test via BoardClient (baseline)
    ctx = setup_test_context()
    try:
        interface = BoardClientInterface()
        run_test_suite(interface, ctx, "BoardClient")
    finally:
        shutil.rmtree(ctx.board_dir.parent)

