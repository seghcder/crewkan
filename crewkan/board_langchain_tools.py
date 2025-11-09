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

class ListMyTasksInput(BaseModel):
    column: Optional[str] = Field(
        default=None,
        description="Optional column id to filter tasks (e.g. 'todo', 'doing', 'done').",
    )
    limit: int = Field(
        default=50,
        description="Maximum number of tasks to return.",
    )


class MoveTaskInput(BaseModel):
    task_id: str = Field(..., description="The id of the task to move.")
    new_column: str = Field(..., description="Target column id (e.g. 'doing', 'done').")


class UpdateTaskFieldInput(BaseModel):
    task_id: str = Field(..., description="The id of the task to update.")
    field: str = Field(
        ...,
        description="Field to update: 'title', 'description', 'priority', or 'due_date'.",
    )
    value: str = Field(..., description="New value for the field.")


class AddCommentInput(BaseModel):
    task_id: str = Field(..., description="The id of the task to comment on.")
    comment: str = Field(..., description="The comment text.")


class ReassignTaskInput(BaseModel):
    task_id: str = Field(..., description="The id of the task to reassign.")
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


class CreateTaskInput(BaseModel):
    title: str = Field(..., description="Title of the new task.")
    description: Optional[str] = Field(
        default="",
        description="Description of the new task.",
    )
    column: str = Field(
        default="backlog",
        description="Column id to create the task in (e.g. 'backlog', 'todo').",
    )
    assignees: Optional[List[str]] = Field(
        default=None,
        description="Optional list of assignee ids. If omitted, defaults to current agent.",
    )
    priority: Optional[str] = Field(
        default=None,
        description="Priority (low, medium, high).",
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Optional list of tags.",
    )
    due_date: Optional[str] = Field(
        default=None,
        description="Optional due date (free-form string, e.g. '2025-12-31').",
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

    def list_my_tasks_tool(column: Optional[str] = None, limit: int = 50) -> str:
        """
        Return tasks assigned to this agent as JSON.
        """
        try:
            return client.list_my_tasks(column=column, limit=limit)
        except BoardError as e:
            return json.dumps({"error": str(e)})

    def move_task_tool(task_id: str, new_column: str) -> str:
        """
        Move a task to another column.
        """
        try:
            return client.move_task(task_id, new_column)
        except BoardError as e:
            return f"ERROR: {e}"

    def update_task_field_tool(task_id: str, field: str, value: str) -> str:
        """
        Update one top-level field on a task (title, description, priority, due_date).
        """
        try:
            return client.update_task_field(task_id, field, value)
        except BoardError as e:
            return f"ERROR: {e}"

    def add_comment_tool(task_id: str, comment: str) -> str:
        """
        Add a comment to a task's history.
        """
        try:
            return client.add_comment(task_id, comment)
        except BoardError as e:
            return f"ERROR: {e}"

    def reassign_task_tool(
        task_id: str,
        new_assignee_id: Optional[str] = None,
        to_superagent: bool = False,
        keep_existing: bool = False,
    ) -> str:
        """
        Reassign a task to another agent or to the default superagent.
        """
        try:
            return client.reassign_task(
                task_id=task_id,
                new_assignee_id=new_assignee_id,
                to_superagent=to_superagent,
                keep_existing=keep_existing,
            )
        except BoardError as e:
            return f"ERROR: {e}"

    def create_task_tool(
        title: str,
        description: str = "",
        column: str = "backlog",
        assignees: Optional[List[str]] = None,
        priority: Optional[str] = None,
        tags: Optional[List[str]] = None,
        due_date: Optional[str] = None,
    ) -> str:
        """
        Create a new task and return its id.
        """
        try:
            task_id = client.create_task(
                title=title,
                description=description,
                column=column,
                assignees=assignees,
                priority=priority,
                tags=tags,
                due_date=due_date,
            )
            return f"Created task {task_id}"
        except BoardError as e:
            return f"ERROR: {e}"

    tools: list[BaseTool] = [
        StructuredTool.from_function(
            name="list_my_tasks",
            func=list_my_tasks_tool,
            args_schema=ListMyTasksInput,
            description=(
                "List tasks assigned to this agent, optionally filtered by column. "
                "Returns a JSON list of task summaries."
            ),
        ),
        StructuredTool.from_function(
            name="move_task",
            func=move_task_tool,
            args_schema=MoveTaskInput,
            description=(
                "Move a task to another column on the board. "
                "Use this when changing task status, such as moving from 'todo' to 'doing' or 'done'."
            ),
        ),
        StructuredTool.from_function(
            name="update_task_field",
            func=update_task_field_tool,
            args_schema=UpdateTaskFieldInput,
            description=(
                "Update a single top-level field on a task. "
                "Allowed fields: title, description, priority, due_date."
            ),
        ),
        StructuredTool.from_function(
            name="add_comment_to_task",
            func=add_comment_tool,
            args_schema=AddCommentInput,
            description=(
                "Add a comment to a task. "
                "Use this to record progress, decisions, or questions."
            ),
        ),
        StructuredTool.from_function(
            name="reassign_task",
            func=reassign_task_tool,
            args_schema=ReassignTaskInput,
            description=(
                "Reassign a task to another agent or to the default superagent. "
                "Set to_superagent=true to escalate to the board's default superagent."
            ),
        ),
        StructuredTool.from_function(
            name="create_task",
            func=create_task_tool,
            args_schema=CreateTaskInput,
            description=(
                "Create a new task on the board. "
                "If assignees are omitted, the current agent will be assigned."
            ),
        ),
    ]

    return tools

