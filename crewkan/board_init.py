# board_init.py

from pathlib import Path
from typing import Optional, List, Dict, Any
from crewkan.board_core import BoardError
from crewkan.utils import load_yaml, save_yaml


DEFAULT_COLUMNS = [
    {"id": "backlog", "name": "Backlog", "wip_limit": None},
    {"id": "todo", "name": "To Do", "wip_limit": 10},
    {"id": "doing", "name": "Doing", "wip_limit": 5},
    {"id": "blocked", "name": "Blocked", "wip_limit": 5},
    {"id": "done", "name": "Done", "wip_limit": None},
]


def init_board(
    root: Path,
    board_id: str,
    board_name: str,
    owner_agent_id: str,
    default_superagent_id: Optional[str] = None,
    columns: Optional[list[dict]] = None,
    force: bool = False,
) -> Path:
    """
    Create a new board in `root` (must be empty or non-existent).
    Writes board.yaml, agents.yaml stubs, and creates tasks/ etc.

    Args:
        root: Directory path for the board (will be created if doesn't exist)
        board_id: Unique identifier for the board
        board_name: Human-readable name
        owner_agent_id: Agent id of the board owner
        default_superagent_id: Optional default superagent for escalations
        columns: Optional list of column definitions (uses defaults if None)
        force: If True, overwrite existing files

    Returns:
        Path to the created board root
    """
    root = Path(root).resolve()

    # Check if directory exists and is not empty
    if root.exists():
        if not force:
            # Check if it's empty or only has .git
            items = [p for p in root.iterdir() if p.name != ".git"]
            if items:
                raise BoardError(
                    f"Directory {root} exists and is not empty. Use force=True to overwrite."
                )
    else:
        root.mkdir(parents=True, exist_ok=True)

    columns = columns or DEFAULT_COLUMNS

    # Create board.yaml
    board_data = {
        "board_id": board_id,
        "board_name": board_name,
        "version": 1,
        "columns": columns,
        "settings": {
            "default_priority": "medium",
            "task_filename_prefix": "T",
            "timezone": "UTC",
            "default_superagent_id": default_superagent_id,
        },
    }
    save_yaml(root / "board.yaml", board_data)

    # Create agents.yaml with just the owner
    agents_data = {
        "agents": [
            {
                "id": owner_agent_id,
                "name": owner_agent_id,
                "role": "Board Owner",
                "kind": "ai",  # Default, can be updated later
                "status": "active",
                "skills": [],
                "metadata": {},
            }
        ]
    }
    if default_superagent_id and default_superagent_id != owner_agent_id:
        # Add superagent if different from owner
        agents_data["agents"].append(
            {
                "id": default_superagent_id,
                "name": default_superagent_id,
                "role": "Superagent",
                "kind": "ai",
                "status": "active",
                "skills": [],
                "metadata": {},
            }
        )

    (root / "agents").mkdir(parents=True, exist_ok=True)
    save_yaml(root / "agents" / "agents.yaml", agents_data)

    # Create task directories
    (root / "tasks").mkdir(parents=True, exist_ok=True)
    for col in columns:
        col_id = col["id"]
        (root / "tasks" / col_id).mkdir(parents=True, exist_ok=True)

    # Create workspaces and archive directories
    (root / "workspaces").mkdir(parents=True, exist_ok=True)
    (root / "archive" / "tasks").mkdir(parents=True, exist_ok=True)

    return root

