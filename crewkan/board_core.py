# board_core.py

import json
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
import yaml

from crewkan.utils import load_yaml, save_yaml, now_iso, generate_task_id, generate_issue_id

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

        try:
            self.board = load_yaml(self.root / "board.yaml") or {}
        except Exception as e:
            raise BoardError(
                f"Failed to load board.yaml from {self.root}: {e}. "
                f"File may be corrupted. Check logs for details."
            ) from e
        
        try:
            self.agents_data = load_yaml(
                self.root / "agents" / "agents.yaml",
                default={"agents": []}
            )
        except Exception as e:
            raise BoardError(
                f"Failed to load agents.yaml from {self.root}: {e}. "
                f"File may be corrupted. Check logs for details."
            ) from e
        
        if "agents" not in self.agents_data:
            self.agents_data["agents"] = []

        self._agent_index = {a["id"]: a for a in self.agents_data["agents"]}

        if self.agent_id not in self._agent_index:
            raise BoardError(f"Unknown agent id '{self.agent_id}'")

        self.columns = [c["id"] for c in self.board.get("columns", [])]
        self.settings = self.board.get("settings", {})
        # Support both tasks/ (old) and issues/ (new) directories
        self.tasks_root = self.root / "tasks"  # Keep for backwards compatibility
        self.issues_root = self.root / "issues"  # New primary directory
        self.workspaces_root = self.root / "workspaces"

    # ------------------------------------------------------------------
    # Agent / board helpers
    # ------------------------------------------------------------------

    def get_default_superagent_id(self) -> str | None:
        return self.settings.get("default_superagent_id")

    def get_board_owner_id(self) -> str | None:
        """Get the board owner agent ID from settings, or None if not set.
        
        For backwards compatibility, if owner_agent_id is not in settings,
        returns the default_superagent_id as a fallback.
        """
        owner_id = self.settings.get("owner_agent_id")
        if owner_id:
            return owner_id
        # Fallback to default_superagent_id for backwards compatibility
        return self.settings.get("default_superagent_id")

    def is_board_owner(self, agent_id: str | None = None) -> bool:
        """Check if the given agent (or current agent) is the board owner."""
        agent_id = agent_id or self.agent_id
        owner_id = self.get_board_owner_id()
        return owner_id == agent_id if owner_id else False

    def get_agent(self, agent_id: str) -> dict | None:
        return self._agent_index.get(agent_id)

    def list_agents(self) -> list[dict]:
        """Get list of all agents on the board."""
        return list(self._agent_index.values())
    
    def get_task_details(self, task_id: str) -> dict:
        """Get full task details including history/comments.
        DEPRECATED: Use get_issue_details() instead. Kept for backwards compatibility.
        """
        return self.get_issue_details(task_id)

    def get_issue_details(self, issue_id: str) -> dict:
        """Get full issue details including history/comments."""
        path, issue = self.find_issue(issue_id)
        return issue

    # ------------------------------------------------------------------
    # Task discovery
    # ------------------------------------------------------------------

    def iter_tasks(self):
        """
        Yield (path, data) for all task YAML files.
        DEPRECATED: Use iter_issues() instead. Kept for backwards compatibility.
        """
        # Check issues/ first (new), then tasks/ (old)
        if self.issues_root.exists():
            for path in self.issues_root.rglob("*.yaml"):
                data = load_yaml(path)
                if isinstance(data, dict):
                    yield path, data
        if self.tasks_root.exists():
            for path in self.tasks_root.rglob("*.yaml"):
                data = load_yaml(path)
                if isinstance(data, dict):
                    yield path, data

    def iter_issues(self):
        """
        Yield (path, data) for all issue YAML files.
        Checks issues/ directory first, then tasks/ for backwards compatibility.
        """
        # Check issues/ first (new), then tasks/ (old)
        if self.issues_root.exists():
            for path in self.issues_root.rglob("*.yaml"):
                data = load_yaml(path)
                if isinstance(data, dict):
                    yield path, data
        if self.tasks_root.exists():
            for path in self.tasks_root.rglob("*.yaml"):
                data = load_yaml(path)
                if isinstance(data, dict):
                    yield path, data

    def find_task(self, task_id: str) -> tuple[Path, dict]:
        """
        Locate a task by id. Returns (path, data) or raises BoardError.
        DEPRECATED: Use find_issue() instead. Kept for backwards compatibility.
        """
        return self.find_issue(task_id)

    def find_issue(self, issue_id: str) -> tuple[Path, dict]:
        """
        Locate an issue by id. Returns (path, data) or raises BoardError.
        Checks issues/ directory first, then tasks/ for backwards compatibility.
        """
        # Check issues/ first (new)
        if self.issues_root.exists():
            for path in self.issues_root.rglob("*.yaml"):
                data = load_yaml(path)
                if isinstance(data, dict) and data.get("id") == issue_id:
                    return path, data
        # Fall back to tasks/ (old)
        if self.tasks_root.exists():
            for path in self.tasks_root.rglob("*.yaml"):
                data = load_yaml(path)
                if isinstance(data, dict) and data.get("id") == issue_id:
                    return path, data
        raise BoardError(f"Issue '{issue_id}' not found")

    # ------------------------------------------------------------------
    # Public operations used by tools
    # ------------------------------------------------------------------

    def list_my_tasks(self, column: str | None = None, limit: int = 50) -> str:
        """
        Return tasks assigned to this agent, optionally filtered by column.
        DEPRECATED: Use list_my_issues() instead. Kept for backwards compatibility.
        """
        return self.list_my_issues(column, limit)

    def list_my_issues(self, column: str | None = None, limit: int = 50) -> str:
        """
        Return issues assigned to this agent, optionally filtered by column.
        Returns a JSON string of a list of issue summaries.
        """
        results = []
        for _, issue in self.iter_issues():
            assignees = issue.get("assignees") or []
            if self.agent_id not in assignees:
                continue
            if column and issue.get("column") != column:
                continue

            results.append(
                {
                    "id": issue.get("id"),
                    "title": issue.get("title"),
                    "column": issue.get("column"),
                    "issue_type": issue.get("issue_type", "task"),  # Default to "task" for backwards compatibility
                    "priority": issue.get("priority"),
                    "assignees": assignees,
                    "due_date": issue.get("due_date"),
                    "tags": issue.get("tags") or [],
                }
            )
            if len(results) >= limit:
                break

        return json.dumps(results, indent=2)

    def move_task(self, task_id: str, new_column: str, notify_on_completion: bool = True) -> str:
        """
        Move a task to another column.
        DEPRECATED: Use move_issue() instead. Kept for backwards compatibility.
        """
        return self.move_issue(task_id, new_column, notify_on_completion)

    def move_issue(self, issue_id: str, new_column: str, notify_on_completion: bool = True) -> str:
        logger.info(f"Moving issue {issue_id} to column {new_column} (agent: {self.agent_id})")
        """
        Move an issue to another column.
        
        Args:
            issue_id: Issue ID to move
            new_column: Target column
            notify_on_completion: If True and moving to "done", create completion event
        """
        if new_column not in self.columns:
            raise BoardError(f"Unknown column '{new_column}'")

        path, issue = self.find_issue(issue_id)
        old_column = issue.get("column", issue.get("status"))

        if old_column == new_column:
            return f"Issue {issue_id} is already in column '{new_column}'."

        issue["column"] = new_column
        issue["status"] = new_column
        issue["updated_at"] = now_iso()
        issue.setdefault("history", []).append(
            {
                "at": issue["updated_at"],
                "by": self.agent_id,
                "event": "moved",
                "details": f"{old_column} -> {new_column}",
            }
        )

        # Determine target directory (issues/ for new, tasks/ for old)
        # If issue is in issues/, move to issues/; if in tasks/, move to tasks/
        if "issues" in str(path):
            new_dir = self.issues_root / new_column
        else:
            new_dir = self.tasks_root / new_column
        new_dir.mkdir(parents=True, exist_ok=True)
        new_path = new_dir / path.name

        save_yaml(new_path, issue)
        if new_path != path:
            path.unlink()

        # Optional: update workspace symlinks
        self._update_workspace_links(issue_id, old_column, new_column)
        
        # If moving to "done" and notification enabled, create completion event
        if new_column == "done" and notify_on_completion:
            # Determine who to notify: original requestor or default superagent
            notify_agent = None
            
            # Check if issue has a "requested_by" field (set when issue is created/delegated)
            requested_by = issue.get("requested_by")
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
                        task_id=issue_id,  # Events still use task_id for now
                        completed_by=self.agent_id,
                        notify_agent=notify_agent,
                    )
                    logger.info(f"Created completion event for issue {issue_id}, notifying {notify_agent}")
                except Exception as e:
                    logger.warning(f"Failed to create completion event: {e}")

        logger.debug(f"Moved issue {issue_id} from {old_column} to {new_column}")
        return f"Moved issue {issue_id} from '{old_column}' to '{new_column}'."

    def update_task_field(self, task_id: str, field: str, value: str) -> str:
        """
        Update a simple top-level field.
        DEPRECATED: Use update_issue_field() instead. Kept for backwards compatibility.
        """
        return self.update_issue_field(task_id, field, value)

    def update_issue_field(self, issue_id: str, field: str, value: str) -> str:
        logger.info(f"Updating issue {issue_id} field {field} (agent: {self.agent_id})")
        """
        Update a simple top-level field (title, description, issue_type, priority, due_date, tags).
        For tags, value should be comma-separated string.
        """
        allowed_fields = {"title", "description", "issue_type", "priority", "due_date", "tags"}
        if field not in allowed_fields:
            raise BoardError(f"Field '{field}' not allowed. Allowed: {', '.join(sorted(allowed_fields))}")

        path, issue = self.find_issue(issue_id)
        old_value = issue.get(field)
        
        # Handle tags specially - convert comma-separated string to list
        if field == "tags":
            if isinstance(value, str):
                issue[field] = [t.strip() for t in value.split(",") if t.strip()]
            elif isinstance(value, list):
                issue[field] = value
            else:
                raise BoardError(f"Tags must be string or list, got {type(value)}")
        else:
            issue[field] = value
        
        issue["updated_at"] = now_iso()
        issue.setdefault("history", []).append(
            {
                "at": issue["updated_at"],
                "by": self.agent_id,
                "event": "updated",
                "details": f"{field}: '{old_value}' -> '{issue[field]}'",
            }
        )
        save_yaml(path, issue)
        return f"Updated issue {issue_id} field '{field}' from '{old_value}' to '{issue[field]}'."

    def add_comment(self, task_id: str, comment: str) -> str:
        """
        Add a new comment event.
        Works with both tasks and issues (backwards compatible).
        """
        import uuid
        from crewkan.utils import now_iso
        
        path, issue = self.find_issue(task_id)  # find_issue works for both
        comment_id = f"C-{uuid.uuid4().hex[:8]}"
        issue["updated_at"] = now_iso()
        comment_entry = {
            "comment_id": comment_id,
            "at": issue["updated_at"],
            "by": self.agent_id,
            "event": "comment",
            "details": comment,
        }
        issue.setdefault("history", []).append(comment_entry)
        save_yaml(path, issue)
        return comment_id
    
    def get_comments(self, task_id: str) -> list[dict]:
        """
        Get all comments for a task/issue.
        Works with both tasks and issues (backwards compatible).
        Returns a list of comment dictionaries with comment_id, at, by, and details.
        """
        path, issue = self.find_issue(task_id)  # find_issue works for both
        comments = []
        for entry in issue.get("history", []):
            if entry.get("event") == "comment":
                comments.append({
                    "comment_id": entry.get("comment_id", ""),  # Backwards compatible
                    "at": entry.get("at", ""),
                    "by": entry.get("by", ""),
                    "details": entry.get("details", ""),
                })
        return comments

    def reassign_task(
        self,
        task_id: str,
        new_assignee_id: str | None = None,
        to_superagent: bool = False,
        keep_existing: bool = False,
    ) -> str:
        """
        Reassign a task.
        DEPRECATED: Use reassign_issue() instead. Kept for backwards compatibility.
        """
        return self.reassign_issue(task_id, new_assignee_id, to_superagent, keep_existing)

    def reassign_issue(
        self,
        issue_id: str,
        new_assignee_id: str | None = None,
        to_superagent: bool = False,
        keep_existing: bool = False,
    ) -> str:
        logger.info(f"Reassigning issue {issue_id} to {new_assignee_id or 'superagent'} (agent: {self.agent_id})")
        """
        Reassign an issue. If to_superagent is True, ignore new_assignee_id and
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

        path, issue = self.find_issue(issue_id)
        assignees = set(issue.get("assignees") or [])

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

        issue["assignees"] = sorted(assignees)
        issue["updated_at"] = now_iso()
        issue.setdefault("history", []).append(
            {
                "at": issue["updated_at"],
                "by": self.agent_id,
                "event": "reassigned",
                "details": changed,
            }
        )
        save_yaml(path, issue)
        
        # Create assignment events for newly assigned agents
        if not keep_existing:
            # All assignees are new
            for assignee in assignees:
                if assignee != self.agent_id:  # Don't notify self
                    try:
                        from crewkan.board_events import create_assignment_event
                        create_assignment_event(
                            board_root=self.root,
                            task_id=issue_id,  # Events still use task_id for now
                            assigned_to=assignee,
                            assigned_by=self.agent_id,
                        )
                        logger.info(f"Created assignment event for issue {issue_id}, notifying {assignee}")
                    except Exception as e:
                        logger.warning(f"Failed to create assignment event: {e}")
        else:
            # Only notify newly added assignees
            old_assignees_set = set(old_assignees)
            for assignee in assignees:
                if assignee not in old_assignees_set and assignee != self.agent_id:
                    try:
                        from crewkan.board_events import create_assignment_event
                        create_assignment_event(
                            board_root=self.root,
                            task_id=issue_id,  # Events still use task_id for now
                            assigned_to=assignee,
                            assigned_by=self.agent_id,
                        )
                        logger.info(f"Created assignment event for issue {issue_id}, notifying {assignee}")
                    except Exception as e:
                        logger.warning(f"Failed to create assignment event: {e}")
        
        return f"Reassigned issue {issue_id}: {changed}"

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
        Create a new task.
        DEPRECATED: Use create_issue() instead. Kept for backwards compatibility.
        Creates issue with default issue_type="task".
        """
        return self.create_issue(
            title=title,
            description=description,
            column=column,
            assignees=assignees,
            priority=priority,
            tags=tags,
            due_date=due_date,
            requested_by=requested_by,
            issue_type="task",  # Default for backwards compatibility
        )

    def create_issue(
        self,
        title: str,
        description: str = "",
        column: str = "backlog",
        assignees: list[str] | None = None,
        priority: str | None = None,
        tags: list[str] | None = None,
        due_date: str | None = None,
        requested_by: str | None = None,
        issue_type: str | None = None,
    ) -> str:
        """
        Create a new issue. Returns the new issue id.
        
        Args:
            title: Issue title
            description: Issue description
            column: Target column (default: "backlog")
            assignees: List of assignee agent IDs (default: current agent)
            priority: Priority level (default: from board settings)
            tags: List of tags
            due_date: Due date string
            requested_by: Agent who requested this issue (default: current agent)
            issue_type: Type of issue - epic, user_story, task, bug, feature, improvement
                       (default: from board settings or "task")
        """
        if column not in self.columns:
            raise BoardError(f"Unknown column '{column}'")

        assignees = assignees or [self.agent_id]
        for a in assignees:
            if a not in self._agent_index:
                raise BoardError(f"Unknown assignee id '{a}'")

        # Use issue_filename_prefix if available, otherwise task_filename_prefix for backwards compatibility
        prefix = self.settings.get("issue_filename_prefix") or self.settings.get("task_filename_prefix", "I")
        issue_id: str = generate_issue_id(prefix)
        created_at = now_iso()

        # Determine requested_by (use parameter if provided, otherwise use creating agent)
        requested_by_agent = requested_by if requested_by is not None else self.agent_id
        
        # Determine issue_type (use parameter, then board default, then "task")
        default_issue_type = self.settings.get("default_issue_type", "task")
        final_issue_type = issue_type or default_issue_type
        
        issue = {
            "id": issue_id,
            "title": title,
            "description": description or "",
            "status": column,
            "column": column,
            "issue_type": final_issue_type,
            "priority": priority or self.settings.get("default_priority", "medium"),
            "tags": tags or [],
            "assignees": assignees,
            "dependencies": [],
            "created_at": created_at,
            "updated_at": created_at,
            "due_date": due_date,
            "requested_by": requested_by_agent,  # Track who requested this issue
            "history": [
                {
                    "at": created_at,
                    "by": self.agent_id,
                    "event": "created",
                    "details": f"Issue created in column {column}",
                }
            ],
        }

        # Use issues/ directory for new issues
        col_dir = self.issues_root / column
        col_dir.mkdir(parents=True, exist_ok=True)
        path = col_dir / f"{issue_id}.yaml"
        save_yaml(path, issue)
        logger.debug(f"Created issue {issue_id} at {path}")
        
        # Create assignment events for assigned agents (except creator)
        for assignee in assignees:
            if assignee != self.agent_id:  # Don't notify self
                try:
                    from crewkan.board_events import create_assignment_event
                    create_assignment_event(
                        board_root=self.root,
                        task_id=issue_id,  # Events still use task_id for now
                        assigned_to=assignee,
                        assigned_by=self.agent_id,
                    )
                    logger.info(f"Created assignment event for issue {issue_id}, notifying {assignee}")
                except Exception as e:
                    logger.warning(f"Failed to create assignment event: {e}")
        
        return issue_id

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

