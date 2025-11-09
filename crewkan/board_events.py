# board_events.py

"""
File-based event system for CrewKan.

Events are stored as YAML files in `events/<agent_id>/` directories.
This allows agents to be notified of task completions, assignments, etc.
without relying on any specific orchestration framework.

Event Structure:
{
    "id": "event-123",
    "type": "task_completed",
    "task_id": "T-456",
    "created_at": "2025-01-01T12:00:00Z",
    "created_by": "worker1",
    "notify_agent": "ceo",
    "status": "pending",  # pending, read, archived
    "data": {
        "task_title": "...",
        "completed_by": "worker1",
        "completion_notes": "..."
    }
}
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from crewkan.utils import load_yaml, save_yaml, now_iso, generate_task_id

# Set up logging
logger = logging.getLogger(__name__)


def get_events_dir(board_root: Path, agent_id: str) -> Path:
    """Get the events directory for an agent."""
    return Path(board_root) / "events" / agent_id


def create_event(
    board_root: str | Path,
    event_type: str,
    notify_agent: str,
    created_by: str,
    data: Dict[str, Any],
    event_id: Optional[str] = None,
) -> str:
    """
    Create an event and store it in the notify_agent's events directory.
    
    Args:
        board_root: Root directory of the board
        event_type: Type of event (e.g., "task_completed", "task_assigned")
        notify_agent: Agent ID to notify
        created_by: Agent ID that created the event
        data: Event-specific data
        event_id: Optional event ID (auto-generated if not provided)
    
    Returns:
        Event ID
    """
    board_root = Path(board_root).resolve()
    events_dir = get_events_dir(board_root, notify_agent)
    events_dir.mkdir(parents=True, exist_ok=True)
    
    event_id = event_id or generate_task_id(prefix="EVT")
    event_file = events_dir / f"{event_id}.yaml"
    
    event = {
        "id": event_id,
        "type": event_type,
        "created_at": now_iso(),
        "created_by": created_by,
        "notify_agent": notify_agent,
        "status": "pending",
        "data": data,
    }
    
    save_yaml(event_file, event)
    logger.info(f"Created event {event_id} of type {event_type} for agent {notify_agent}")
    
    return event_id


def create_completion_event(
    board_root: str | Path,
    task_id: str,
    completed_by: str,
    notify_agent: str,
    completion_notes: Optional[str] = None,
) -> str:
    """
    Create a task completion event.
    
    This is called when a task is moved to "done" to notify the original requestor.
    
    Args:
        board_root: Root directory of the board
        task_id: ID of the completed task
        completed_by: Agent ID that completed the task
        notify_agent: Agent ID to notify (typically the original requestor)
        completion_notes: Optional notes about the completion
    
    Returns:
        Event ID
    """
    # Load task to get details
    from crewkan.board_core import BoardClient, BoardError
    
    try:
        client = BoardClient(board_root, completed_by)
        path, task = client.find_task(task_id)
        
        data = {
            "task_id": task_id,
            "task_title": task.get("title", ""),
            "task_description": task.get("description", ""),
            "completed_by": completed_by,
            "completion_notes": completion_notes,
            "completed_at": now_iso(),
        }
    except BoardError:
        # Task not found, create minimal event
        data = {
            "task_id": task_id,
            "completed_by": completed_by,
            "completion_notes": completion_notes,
            "completed_at": now_iso(),
        }
    
    return create_event(
        board_root=board_root,
        event_type="task_completed",
        notify_agent=notify_agent,
        created_by=completed_by,
        data=data,
    )


def list_pending_events(
    board_root: str | Path,
    agent_id: str,
    event_type: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    List pending events for an agent.
    
    Args:
        board_root: Root directory of the board
        agent_id: Agent ID to get events for
        event_type: Optional filter by event type
        limit: Maximum number of events to return
    
    Returns:
        List of event dictionaries
    """
    board_root = Path(board_root).resolve()
    events_dir = get_events_dir(board_root, agent_id)
    
    if not events_dir.exists():
        return []
    
    events = []
    for event_file in sorted(events_dir.glob("*.yaml"), key=lambda p: p.stat().st_mtime, reverse=True):
        event = load_yaml(event_file)
        if not isinstance(event, dict):
            continue
        
        if event.get("status") != "pending":
            continue
        
        if event_type and event.get("type") != event_type:
            continue
        
        events.append(event)
        
        if len(events) >= limit:
            break
    
    return events


def mark_event_read(
    board_root: str | Path,
    agent_id: str,
    event_id: str,
) -> bool:
    """
    Mark an event as read.
    
    Args:
        board_root: Root directory of the board
        agent_id: Agent ID that owns the event
        event_id: Event ID to mark as read
    
    Returns:
        True if event was found and marked, False otherwise
    """
    board_root = Path(board_root).resolve()
    events_dir = get_events_dir(board_root, agent_id)
    event_file = events_dir / f"{event_id}.yaml"
    
    if not event_file.exists():
        return False
    
    event = load_yaml(event_file)
    if not isinstance(event, dict):
        return False
    
    event["status"] = "read"
    event["read_at"] = now_iso()
    save_yaml(event_file, event)
    
    logger.info(f"Marked event {event_id} as read for agent {agent_id}")
    return True


def archive_event(
    board_root: str | Path,
    agent_id: str,
    event_id: str,
) -> bool:
    """
    Archive an event (move to archived status).
    
    Args:
        board_root: Root directory of the board
        agent_id: Agent ID that owns the event
        event_id: Event ID to archive
    
    Returns:
        True if event was found and archived, False otherwise
    """
    board_root = Path(board_root).resolve()
    events_dir = get_events_dir(board_root, agent_id)
    event_file = events_dir / f"{event_id}.yaml"
    
    if not event_file.exists():
        return False
    
    event = load_yaml(event_file)
    if not isinstance(event, dict):
        return False
    
    event["status"] = "archived"
    event["archived_at"] = now_iso()
    save_yaml(event_file, event)
    
    logger.info(f"Archived event {event_id} for agent {agent_id}")
    return True


def get_event(
    board_root: str | Path,
    agent_id: str,
    event_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Get a specific event by ID.
    
    Args:
        board_root: Root directory of the board
        agent_id: Agent ID that owns the event
        event_id: Event ID to retrieve
    
    Returns:
        Event dictionary or None if not found
    """
    board_root = Path(board_root).resolve()
    events_dir = get_events_dir(board_root, agent_id)
    event_file = events_dir / f"{event_id}.yaml"
    
    if not event_file.exists():
        return None
    
    return load_yaml(event_file)

