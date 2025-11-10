# board_langchain_tools.py

import logging
from typing import Optional, List
import json
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool, BaseTool

from crewkan.board_core import BoardClient, BoardError

# Set up logging
logger = logging.getLogger(__name__)


# -----------------------------
# Pydantic schemas for tools
# -----------------------------

class ListMyIssuesInput(BaseModel):
    column: Optional[str] = Field(
        default=None,
        description="Optional column id to filter issues (e.g. 'todo', 'doing', 'done').",
    )
    limit: int = Field(
        default=50,
        description="Maximum number of issues to return.",
    )


class MoveIssueInput(BaseModel):
    issue_id: str = Field(..., description="The id of the issue to move.")
    new_column: str = Field(..., description="Target column id (e.g. 'doing', 'done').")


class UpdateIssueFieldInput(BaseModel):
    issue_id: str = Field(..., description="The id of the issue to update.")
    field: str = Field(
        ...,
        description="Field to update: 'title', 'description', 'issue_type', 'priority', or 'due_date'.",
    )
    value: str = Field(..., description="New value for the field.")


class AddCommentInput(BaseModel):
    issue_id: str = Field(..., description="The id of the issue to comment on.")
    comment: str = Field(..., description="The comment text.")


class ReassignIssueInput(BaseModel):
    issue_id: str = Field(..., description="The id of the issue to reassign.")
    new_assignee_id: Optional[str] = Field(
        default=None,
        description="New assignee id. Ignored if to_superagent is true.",
    )
    to_superagent: bool = Field(
        default=False,
        description="If true, ignore new_assignee_id and reassign to the board's default superagent.",
    )
    keep_existing: bool = Field(
        default=False,
        description="If true, keep existing assignees and add the new one.",
    )


class CreateIssueInput(BaseModel):
    title: str = Field(..., description="Title of the new issue.")
    description: Optional[str] = Field(
        default="",
        description="Description of the new issue.",
    )
    column: str = Field(
        default="backlog",
        description="Column id to create the issue in (e.g. 'backlog', 'todo').",
    )
    assignees: Optional[List[str]] = Field(
        default=None,
        description="Optional list of assignee ids. If omitted, defaults to current agent.",
    )
    priority: Optional[str] = Field(
        default=None,
        description="Priority (low, medium, high).",
    )
    issue_type: Optional[str] = Field(
        default=None,
        description="Issue type: epic, user_story, task, bug, feature, improvement.",
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Optional list of tags.",
    )
    due_date: Optional[str] = Field(
        default=None,
        description="Optional due date (free-form string, e.g. '2025-12-31').",
    )
    requested_by: Optional[str] = Field(
        default=None,
        description="Agent ID that requested this issue (for completion notifications).",
    )


# -----------------------------
# Factory for agent-specific tools
# -----------------------------

def make_board_tools(board_root: str, agent_id: str) -> list[BaseTool]:
    """
    Create a set of LangChain tools bound to a specific agent_id.
    The underlying BoardClient will act on behalf of that agent.
    """
    client = BoardClient(board_root, agent_id)

    def list_my_issues_tool(column: Optional[str] = None, limit: int = 50) -> str:
        """
        Return issues assigned to this agent as JSON.
        """
        try:
            return client.list_my_issues(column=column, limit=limit)
        except BoardError as e:
            return json.dumps({"error": str(e)})

    def move_issue_tool(issue_id: str, new_column: str) -> str:
        """
        Move an issue to another column.
        """
        try:
            return client.move_issue(issue_id, new_column)
        except BoardError as e:
            return f"ERROR: {e}"

    def update_issue_field_tool(issue_id: str, field: str, value: str) -> str:
        """
        Update one top-level field on an issue (title, description, issue_type, priority, due_date).
        """
        try:
            return client.update_issue_field(issue_id, field, value)
        except BoardError as e:
            return f"ERROR: {e}"

    def add_comment_tool(issue_id: str, comment: str) -> str:
        """
        Add a comment to an issue's history.
        """
        try:
            return client.add_comment(issue_id, comment)
        except BoardError as e:
            return f"ERROR: {e}"

    def reassign_issue_tool(
        issue_id: str,
        new_assignee_id: Optional[str] = None,
        to_superagent: bool = False,
        keep_existing: bool = False,
    ) -> str:
        """
        Reassign an issue to another agent or to the default superagent.
        """
        try:
            return client.reassign_issue(
                issue_id=issue_id,
                new_assignee_id=new_assignee_id,
                to_superagent=to_superagent,
                keep_existing=keep_existing,
            )
        except BoardError as e:
            return f"ERROR: {e}"

    def create_issue_tool(
        title: str,
        description: str = "",
        column: str = "backlog",
        assignees: Optional[List[str]] = None,
        priority: Optional[str] = None,
        issue_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        due_date: Optional[str] = None,
        requested_by: Optional[str] = None,
    ) -> str:
        """
        Create a new issue and return its id.
        """
        try:
            issue_id = client.create_issue(
                title=title,
                description=description,
                column=column,
                assignees=assignees,
                priority=priority,
                issue_type=issue_type,
                tags=tags,
                due_date=due_date,
                requested_by=requested_by or agent_id,  # Default to current agent if not specified
            )
            return f"Created issue {issue_id}"
        except BoardError as e:
            return f"ERROR: {e}"

    tools: list[BaseTool] = [
        StructuredTool.from_function(
            name="list_my_issues",
            func=list_my_issues_tool,
            args_schema=ListMyIssuesInput,
            description=(
                "List issues assigned to this agent, optionally filtered by column. "
                "Returns a JSON list of issue summaries."
            ),
        ),
        StructuredTool.from_function(
            name="move_issue",
            func=move_issue_tool,
            args_schema=MoveIssueInput,
            description=(
                "Move an issue to another column on the board. "
                "Use this when changing issue status, such as moving from 'todo' to 'doing' or 'done'."
            ),
        ),
        StructuredTool.from_function(
            name="update_issue_field",
            func=update_issue_field_tool,
            args_schema=UpdateIssueFieldInput,
            description=(
                "Update a single top-level field on an issue. "
                "Allowed fields: title, description, issue_type, priority, due_date."
            ),
        ),
        StructuredTool.from_function(
            name="add_comment_to_issue",
            func=add_comment_tool,
            args_schema=AddCommentInput,
            description=(
                "Add a comment to an issue. "
                "Use this to record progress, decisions, or questions."
            ),
        ),
        StructuredTool.from_function(
            name="reassign_issue",
            func=reassign_issue_tool,
            args_schema=ReassignIssueInput,
            description=(
                "Reassign an issue to another agent or to the default superagent. "
                "Set to_superagent=true to escalate to the board's default superagent."
            ),
        ),
        StructuredTool.from_function(
            name="create_issue",
            func=create_issue_tool,
            args_schema=CreateIssueInput,
            description=(
                "Create a new issue on the board. "
                "If assignees are omitted, the current agent will be assigned. "
                "Issue types: epic, user_story, task, bug, feature, improvement."
            ),
        ),
    ]

    return tools


# -----------------------------
# Event tools for notifications
# -----------------------------

def make_event_tools(board_root: str, agent_id: str) -> list[BaseTool]:
    """
    Create tools for checking and managing events/notifications.
    """
    from crewkan.board_events import (
        list_pending_events,
        mark_event_read,
        archive_event,
        get_event,
    )
    
    def list_events_tool(event_type: Optional[str] = None, limit: int = 10) -> str:
        """List pending events/notifications for this agent."""
        try:
            events = list_pending_events(board_root, agent_id, event_type=event_type, limit=limit)
            return json.dumps(events, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def mark_event_read_tool(event_id: str) -> str:
        """Mark an event as read."""
        try:
            success = mark_event_read(board_root, agent_id, event_id)
            return f"Event {event_id} marked as read" if success else f"Event {event_id} not found"
        except Exception as e:
            return f"ERROR: {e}"
    
    def get_event_tool(event_id: str) -> str:
        """Get details of a specific event."""
        try:
            event = get_event(board_root, agent_id, event_id)
            if event:
                return json.dumps(event, indent=2)
            return f"Event {event_id} not found"
        except Exception as e:
            return f"ERROR: {e}"
    
    def clear_all_events_tool() -> str:
        """Mark all pending events as read."""
        try:
            events = list_pending_events(board_root, agent_id, limit=1000)
            cleared = 0
            for event in events:
                if mark_event_read(board_root, agent_id, event["id"]):
                    cleared += 1
            return f"Cleared {cleared} events"
        except Exception as e:
            return f"ERROR: {e}"
    
    class ListEventsInput(BaseModel):
        event_type: Optional[str] = Field(
            default=None,
            description="Optional filter by event type (e.g., 'task_completed', 'task_assigned').",
        )
        limit: int = Field(
            default=10,
            description="Maximum number of events to return.",
        )
    
    class EventIdInput(BaseModel):
        event_id: str = Field(..., description="Event ID to operate on.")
    
    tools: list[BaseTool] = [
        StructuredTool.from_function(
            name="list_events",
            func=list_events_tool,
            args_schema=ListEventsInput,
            description=(
                "List pending events/notifications for this agent. "
                "Use this to check for task completions, assignments, etc. "
                "Returns a JSON list of events."
            ),
        ),
        StructuredTool.from_function(
            name="mark_event_read",
            func=mark_event_read_tool,
            args_schema=EventIdInput,
            description="Mark an event as read after processing it.",
        ),
        StructuredTool.from_function(
            name="get_event",
            func=get_event_tool,
            args_schema=EventIdInput,
            description="Get details of a specific event by ID.",
        ),
        StructuredTool.from_function(
            name="clear_all_events",
            func=clear_all_events_tool,
            args_schema=None,
            description="Mark all pending events as read. Use this to clear your notification inbox.",
        ),
    ]
    
    return tools

