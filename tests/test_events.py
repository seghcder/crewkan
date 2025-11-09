#!/usr/bin/env python3
"""
Test event notification system.
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.board_init import init_board
from crewkan.board_core import BoardClient
from crewkan.board_events import (
    create_event,
    create_completion_event,
    create_assignment_event,
    list_pending_events,
    mark_event_read,
    archive_event,
    get_event,
    clear_all_events,
)
from crewkan.board_langchain_tools import make_event_tools


def test_event_system():
    """Test the event notification system."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "event_test_board"
    
    try:
        # Set up board
        init_board(
            board_dir,
            board_id="event-test",
            board_name="Event Test Board",
            owner_agent_id="ceo",
            default_superagent_id="ceo",
        )
        
        # Add agents
        from crewkan.crewkan_cli import cmd_add_agent
        import argparse
        
        class Args:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        cmd_add_agent(Args(root=str(board_dir), id="ceo", name="CEO", role="Manager", kind="ai"))
        cmd_add_agent(Args(root=str(board_dir), id="worker1", name="Worker 1", role="Developer", kind="ai"))
        
        # Create a task
        client = BoardClient(board_dir, "ceo")
        task_id = client.create_task(
            "Test Task",
            "Test description",
            "todo",
            ["worker1"],  # Assign to worker1 - should create assignment event
        )
        
        # Check for assignment event
        events = list_pending_events(board_dir, "worker1", event_type="task_assigned")
        assert len(events) > 0, "Should have assignment event"
        assignment_event = events[0]
        assert assignment_event["type"] == "task_assigned"
        assert assignment_event["data"]["task_id"] == task_id
        
        # Mark event as read
        event_id = assignment_event["id"]
        success = mark_event_read(board_dir, "worker1", event_id)
        assert success, "Should mark event as read"
        
        # Verify it's no longer pending
        events_after = list_pending_events(board_dir, "worker1", event_type="task_assigned")
        assert len(events_after) == 0, "Event should no longer be pending"
        
        # Move task to done - should create completion event
        client_worker = BoardClient(board_dir, "worker1")
        client_worker.move_task(task_id, "done")
        
        # Check for completion event (notifying CEO)
        completion_events = list_pending_events(board_dir, "ceo", event_type="task_completed")
        assert len(completion_events) > 0, "Should have completion event"
        completion_event = completion_events[0]
        assert completion_event["type"] == "task_completed"
        assert completion_event["data"]["task_id"] == task_id
        
        # Test clear_all_events
        cleared = clear_all_events(board_dir, "ceo")
        assert cleared > 0, "Should clear events"
        
        # Verify all cleared
        remaining = list_pending_events(board_dir, "ceo")
        assert len(remaining) == 0, "All events should be cleared"
        
        # Test event tools
        event_tools = make_event_tools(str(board_dir), "ceo")
        assert len(event_tools) == 4, "Should have 4 event tools"
        
        tool_names = [t.name for t in event_tools]
        assert "list_events" in tool_names
        assert "mark_event_read" in tool_names
        assert "get_event" in tool_names
        assert "clear_all_events" in tool_names
        
        print("✓ Event system tests passed")
        
    finally:
        if board_dir.exists():
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_event_system()

