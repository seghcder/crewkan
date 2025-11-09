# board_core.py

import json
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
import yaml

from crewkan.utils import load_yaml, save_yaml, now_iso, generate_task_id

# Set up logging
logger = logging.getLogger(__name__)


class BoardError(Exception):
    pass


class BoardClient:
    """
    Core client for filesystem-based board. All operations go through here.

    - root: root directory of the board (contains board.yaml, agents/, tasks/, etc)
    - agent_id: the logical agent (human or AI) that is using this client
    """

    def __init__(self, root: str | Path, agent_id: str) -> None:
        self.root = Path(root).resolve()
        self.agent_id = agent_id

        self.board = load_yaml(self.root / "board.yaml") or {}
        self.agents_data = load_yaml(self.root / "agents" / "agents.yaml", default={"agents": []})
        if "agents" not in self.agents_data:
            self.agents_data["agents"] = []

        self._agent_index = {a["id"]: a for a in self.agents_data["agents"]}

        if self.agent_id not in self._agent_index:
            raise BoardError(f"Unknown agent id '{self.agent_id}'")

        self.columns = [c["id"] for c in self.board.get("columns", [])]
        self.settings = self.board.get("settings", {})
        self.tasks_root = self.root / "tasks"
        self.workspaces_root = self.root / "workspaces"

    # ------------------------------------------------------------------
    # Agent / board helpers
    # ------------------------------------------------------------------

    def get_default_superagent_id(self) -> str | None:
        return self.settings.get("default_superagent_id")

    def get_agent(self, agent_id: str) -> dict | None:
        return self._agent_index.get(agent_id)

    def list_agents(self) -> list[dict]:
        return list(self._agent_index.values())

    # ------------------------------------------------------------------
    # Task discovery
    # ------------------------------------------------------------------

    def iter_tasks(self):
        """
        Yield (path, data) for all task YAML files.
        """
        if not self.tasks_root.exists():
            return
        for path in self.tasks_root.rglob("*.yaml"):
            data = load_yaml(path)
            if isinstance(data, dict):
                yield path, data

    def find_task(self, task_id: str) -> tuple[Path, dict]:
        """
        Locate a task by id. Returns (path, data) or raises BoardError.
        """
        for path, data in self.iter_tasks():
            if data.get("id") == task_id:
                return path, data
        raise BoardError(f"Task '{task_id}' not found")

    # ------------------------------------------------------------------
    # Public operations used by tools
    # ------------------------------------------------------------------

    def list_my_tasks(self, column: str | None = None, limit: int = 50) -> str:
        """
        Return tasks assigned to this agent, optionally filtered by column.
        Returns a JSON string of a list of task summaries.
        """
        results = []
        for _, task in self.iter_tasks():
            assignees = task.get("assignees") or []
            if self.agent_id not in assignees:
                continue
            if column and task.get("column") != column:
                continue

            results.append(
                {
                    "id": task.get("id"),
                    "title": task.get("title"),
                    "column": task.get("column"),
                    "priority": task.get("priority"),
                    "assignees": assignees,
                    "due_date": task.get("due_date"),
                    "tags": task.get("tags") or [],
                }
            )
            if len(results) >= limit:
                break

        return json.dumps(results, indent=2)

    def move_task(self, task_id: str, new_column: str, notify_on_completion: bool = True) -> str:
        logger.info(f"Moving task {task_id} to column {new_column} (agent: {self.agent_id})")
        """
        Move a task to another column.
        
        Args:
            task_id: Task ID to move
            new_column: Target column
            notify_on_completion: If True and moving to "done", create completion event
        """
        if new_column not in self.columns:
            raise BoardError(f"Unknown column '{new_column}'")

        path, task = self.find_task(task_id)
        old_column = task.get("column", task.get("status"))

        if old_column == new_column:
            return f"Task {task_id} is already in column '{new_column}'."

        task["column"] = new_column
        task["status"] = new_column
        task["updated_at"] = now_iso()
        task.setdefault("history", []).append(
            {
                "at": task["updated_at"],
                "by": self.agent_id,
                "event": "moved",
                "details": f"{old_column} -> {new_column}",
            }
        )

        new_dir = self.tasks_root / new_column
        new_dir.mkdir(parents=True, exist_ok=True)
        new_path = new_dir / path.name

        save_yaml(new_path, task)
        if new_path != path:
            path.unlink()

        # Optional: update workspace symlinks
        self._update_workspace_links(task_id, old_column, new_column)
        
        # If moving to "done" and notification enabled, create completion event
        if new_column == "done" and notify_on_completion:
            # Determine who to notify: original requestor or default superagent
            notify_agent = None
            
            # Check if task has a "requested_by" field (set when task is created/delegated)
            requested_by = task.get("requested_by")
            if requested_by and requested_by in self._agent_index:
                notify_agent = requested_by
            else:
                # Fall back to default superagent
                notify_agent = self.get_default_superagent_id()
            
            if notify_agent and notify_agent != self.agent_id:
                try:
                    from crewkan.board_events import create_completion_event
                    create_completion_event(
                        board_root=self.root,
                        task_id=task_id,
                        completed_by=self.agent_id,
                        notify_agent=notify_agent,
                    )
                    logger.info(f"Created completion event for task {task_id}, notifying {notify_agent}")
                except Exception as e:
                    logger.warning(f"Failed to create completion event: {e}")

        logger.debug(f"Moved task {task_id} from {old_column} to {new_column}")
        return f"Moved task {task_id} from '{old_column}' to '{new_column}'."

    def update_task_field(self, task_id: str, field: str, value: str) -> str:
        logger.info(f"Updating task {task_id} field {field} (agent: {self.agent_id})")
        """
        Update a simple top-level field (title, description, priority, due_date, tags).
        For tags, value should be comma-separated string.
        """
        allowed_fields = {"title", "description", "priority", "due_date", "tags"}
        if field not in allowed_fields:
            raise BoardError(f"Field '{field}' not allowed. Allowed: {', '.join(sorted(allowed_fields))}")

        path, task = self.find_task(task_id)
        old_value = task.get(field)
        
        # Handle tags specially - convert comma-separated string to list
        if field == "tags":
            if isinstance(value, str):
                task[field] = [t.strip() for t in value.split(",") if t.strip()]
            elif isinstance(value, list):
                task[field] = value
            else:
                raise BoardError(f"Tags must be string or list, got {type(value)}")
        else:
            task[field] = value
        
        task["updated_at"] = now_iso()
        task.setdefault("history", []).append(
            {
                "at": task["updated_at"],
                "by": self.agent_id,
                "event": "updated",
                "details": f"{field}: '{old_value}' -> '{task[field]}'",
            }
        )
        save_yaml(path, task)
        return f"Updated task {task_id} field '{field}' from '{old_value}' to '{task[field]}'."

    def add_comment(self, task_id: str, comment: str) -> str:
        logger.info(f"Adding comment to task {task_id} (agent: {self.agent_id})")
        """
        Add a new comment event to the task history.
        """
        path, task = self.find_task(task_id)
        task["updated_at"] = now_iso()
        task.setdefault("history", []).append(
            {
                "at": task["updated_at"],
                "by": self.agent_id,
                "event": "comment",
                "details": comment,
            }
        )
        save_yaml(path, task)
        return f"Added comment to task {task_id}."

    def reassign_task(
        self,
        task_id: str,
        new_assignee_id: str | None = None,
        to_superagent: bool = False,
        keep_existing: bool = False,
    ) -> str:
        logger.info(f"Reassigning task {task_id} to {new_assignee_id or 'superagent'} (agent: {self.agent_id})")
        """
        Reassign a task. If to_superagent is True, ignore new_assignee_id and
        reassign to the board's default superagent.
        """
        if to_superagent:
            new_assignee_id = self.get_default_superagent_id()
            if not new_assignee_id:
                raise BoardError("No default_superagent_id configured on board.")

        if not new_assignee_id:
            raise BoardError("new_assignee_id is required unless to_superagent is True.")

        if new_assignee_id not in self._agent_index:
            raise BoardError(f"Unknown assignee id '{new_assignee_id}'")

        path, task = self.find_task(task_id)
        assignees = set(task.get("assignees") or [])

        if not keep_existing:
            # Remove all existing assignees, including self
            old_assignees = list(assignees)
            assignees = {new_assignee_id}
            changed = f"{old_assignees} -> [{new_assignee_id}]"
        else:
            # Add new assignee but keep others
            old_assignees = list(assignees)
            assignees.add(new_assignee_id)
            changed = f"{old_assignees} -> {sorted(assignees)}"

        task["assignees"] = sorted(assignees)
        task["updated_at"] = now_iso()
        task.setdefault("history", []).append(
            {
                "at": task["updated_at"],
                "by": self.agent_id,
                "event": "reassigned",
                "details": changed,
            }
        )
        save_yaml(path, task)
        return f"Reassigned task {task_id}: {changed}"

    def create_task(
        self,
        title: str,
        description: str = "",
        column: str = "backlog",
        assignees: list[str] | None = None,
        priority: str | None = None,
        tags: list[str] | None = None,
        due_date: str | None = None,
        requested_by: str | None = None,
    ) -> str:
        """
        Create a new task. Returns the new task id.
        """
        if column not in self.columns:
            raise BoardError(f"Unknown column '{column}'")

        assignees = assignees or [self.agent_id]
        for a in assignees:
            if a not in self._agent_index:
                raise BoardError(f"Unknown assignee id '{a}'")

        prefix = self.settings.get("task_filename_prefix", "T")
        task_id: str = generate_task_id(prefix)
        created_at = now_iso()

        # Determine requested_by (use parameter if provided, otherwise use creating agent)
        requested_by_agent = requested_by if requested_by is not None else self.agent_id
        
        task = {
            "id": task_id,
            "title": title,
            "description": description or "",
            "status": column,
            "column": column,
            "priority": priority or self.settings.get("default_priority", "medium"),
            "tags": tags or [],
            "assignees": assignees,
            "dependencies": [],
            "created_at": created_at,
            "updated_at": created_at,
            "due_date": due_date,
            "requested_by": requested_by_agent,  # Track who requested this task
            "history": [
                {
                    "at": created_at,
                    "by": self.agent_id,
                    "event": "created",
                    "details": f"Task created in column {column}",
                }
            ],
        }

        col_dir = self.tasks_root / column
        col_dir.mkdir(parents=True, exist_ok=True)
        path = col_dir / f"{task_id}.yaml"
        save_yaml(path, task)
        logger.debug(f"Created task {task_id} at {path}")
        return task_id

    # ------------------------------------------------------------------
    # Workspace symlinks (optional for LangChain but handy)
    # ------------------------------------------------------------------

    def _update_workspace_links(self, task_id: str, old_column: str, new_column: str):
        """
        If you are using per-agent workspaces with symlinks, you can keep them
        in sync here. This implementation is minimal: it renames the symlink
        path if the column changes.
        """
        # For simplicity, we just update the current agent's workspace.
        agent_ws_root = self.workspaces_root / self.agent_id
        if not agent_ws_root.exists():
            return

        old_link = agent_ws_root / old_column / f"{task_id}.yaml"
        if old_link.is_symlink():
            target = old_link.resolve()
            old_link.unlink()
            new_link = agent_ws_root / new_column / f"{task_id}.yaml"
            new_link.parent.mkdir(parents=True, exist_ok=True)
            new_link.symlink_to(target)

