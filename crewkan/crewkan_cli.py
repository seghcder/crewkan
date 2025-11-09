#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml

from crewkan.utils import load_yaml, save_yaml, now_iso, generate_task_id
from crewkan.board_core import BoardClient, BoardError


def load_board(root: Path) -> Dict[str, Any]:
    board = load_yaml(root / "board.yaml")
    if board is None:
        raise RuntimeError(f"No board.yaml found in {root}")
    return board


def load_agents(root: Path) -> Dict[str, Any]:
    agents = load_yaml(root / "agents" / "agents.yaml", default={"agents": []})
    if "agents" not in agents:
        agents["agents"] = []
    return agents


def save_agents(root: Path, agents: Dict[str, Any]) -> None:
    save_yaml(root / "agents" / "agents.yaml", agents)


def get_column_ids(board: Dict[str, Any]) -> List[str]:
    return [c["id"] for c in board.get("columns", [])]


def find_task_file(root: Path, task_id: str) -> Path:
    tasks_root = root / "tasks"
    for path in tasks_root.rglob("*.yaml"):
        data = load_yaml(path)
        if isinstance(data, dict) and data.get("id") == task_id:
            return path
    raise RuntimeError(f"Task {task_id} not found under {tasks_root}")


# Workspace utilities

def create_symlink(target: Path, link_path: Path):
    """
    Create a symlink link_path -> target.
    Overwrites any existing file/symlink at link_path.
    """
    link_path.parent.mkdir(parents=True, exist_ok=True)
    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()
    link_path.symlink_to(target)


def remove_symlink(link_path: Path):
    if link_path.is_symlink():
        link_path.unlink()


# Agent commands

def cmd_list_agents(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    agents = load_agents(root)
    if not agents["agents"]:
        print("No agents defined.")
        return
    for a in agents["agents"]:
        print(f"{a['id']:15} {a.get('status','?'):8} {a.get('role','')} ({a.get('name','')})")


def cmd_add_agent(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    agents = load_agents(root)

    if any(a["id"] == args.id for a in agents["agents"]):
        print(f"Agent with id {args.id} already exists.")
        return

    agent = {
        "id": args.id,
        "name": args.name or args.id,
        "role": args.role or "",
        "kind": args.kind or "ai",
        "status": "active",
        "skills": [],
        "metadata": {},
    }
    agents["agents"].append(agent)
    save_agents(root, agents)
    print(f"Added agent {args.id}")


def cmd_remove_agent(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    agents = load_agents(root)
    before = len(agents["agents"])
    agents["agents"] = [a for a in agents["agents"] if a["id"] != args.id]
    after = len(agents["agents"])
    if after == before:
        print(f"No agent with id {args.id} found.")
    else:
        save_agents(root, agents)
        print(f"Removed agent {args.id}")


# Task commands

def cmd_new_task(args: argparse.Namespace) -> None:
    """Create a new task using BoardClient."""
    root = Path(args.root).resolve()
    
    # Use BoardClient for task creation (need a default agent)
    try:
        # Try to get first agent or create a temporary one
        agents = load_agents(root)
        if not agents["agents"]:
            raise RuntimeError("No agents defined. Create an agent first.")
        agent_id = agents["agents"][0]["id"]
    except Exception:
        agent_id = "cli"  # Fallback
    
    try:
        client = BoardClient(root, agent_id)
    except BoardError:
        # If agent doesn't exist, use CLI as fallback
        board = load_board(root)
        col_ids = get_column_ids(board)
        
        if args.column not in col_ids:
            raise RuntimeError(f"Unknown column '{args.column}'. Valid columns: {', '.join(col_ids)}")
        
        # Fallback to direct file creation
        assignees = args.assignee or []
        valid_agent_ids = {a["id"] for a in agents["agents"]}
        for a in assignees:
            if a not in valid_agent_ids:
                raise RuntimeError(f"Unknown agent id '{a}'")
        
        prefix = board.get("settings", {}).get("task_filename_prefix", "T")
        task_id = args.id or generate_task_id(prefix=prefix)
        created_at = now_iso()
        
        task = {
            "id": task_id,
            "title": args.title,
            "description": args.description or "",
            "status": args.column,
            "column": args.column,
            "priority": args.priority or board.get("settings", {}).get("default_priority", "medium"),
            "tags": args.tags.split(",") if args.tags else [],
            "assignees": assignees,
            "dependencies": [],
            "created_at": created_at,
            "updated_at": created_at,
            "due_date": args.due_date,
            "history": [
                {
                    "at": created_at,
                    "by": "cli",
                    "event": "created",
                    "details": f"Task created in column {args.column}",
                }
            ],
        }
        
        col_dir = root / "tasks" / args.column
        col_dir.mkdir(parents=True, exist_ok=True)
        path = col_dir / f"{task_id}.yaml"
        save_yaml(path, task)
        
        print(f"Created task {task_id} in column {args.column}")
        print(f"File: {path}")
        return
    
    # Use BoardClient
    task_id = client.create_task(
        title=args.title,
        description=args.description or "",
        column=args.column,
        assignees=args.assignee or [],
        priority=args.priority,
        tags=args.tags.split(",") if args.tags else [],
        due_date=args.due_date,
    )
    print(f"Created task {task_id} in column {args.column}")


def cmd_move_task(args: argparse.Namespace) -> None:
    """Move a task using BoardClient."""
    root = Path(args.root).resolve()
    
    # Get agent for BoardClient
    agents = load_agents(root)
    if not agents["agents"]:
        raise RuntimeError("No agents defined.")
    agent_id = agents["agents"][0]["id"]
    
    try:
        client = BoardClient(root, agent_id)
        result = client.move_task(args.id, args.column)
        print(result)
    except BoardError as e:
        raise RuntimeError(str(e))


def cmd_assign_task(args: argparse.Namespace) -> None:
    """Assign task using BoardClient."""
    root = Path(args.root).resolve()
    
    # Get agent for BoardClient
    agents = load_agents(root)
    if not agents["agents"]:
        raise RuntimeError("No agents defined.")
    agent_id = agents["agents"][0]["id"]
    
    try:
        client = BoardClient(root, agent_id)
        # Assign to first assignee, keeping existing
        for assignee in args.assignee:
            result = client.reassign_task(args.id, assignee, keep_existing=True)
        print(f"Assigned {args.id} to: {', '.join(args.assignee)}")
    except BoardError as e:
        raise RuntimeError(str(e))


def cmd_list_tasks(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    board = load_board(root)
    col_filter = args.column
    agent_filter = args.agent

    col_ids = get_column_ids(board)
    if col_filter and col_filter not in col_ids:
        raise RuntimeError(f"Unknown column '{col_filter}'. Valid: {', '.join(col_ids)}")

    tasks_root = root / "tasks"
    count = 0
    for path in tasks_root.rglob("*.yaml"):
        task = load_yaml(path)
        if not isinstance(task, dict):
            continue

        if col_filter and task.get("column") != col_filter:
            continue

        if agent_filter and agent_filter not in (task.get("assignees") or []):
            continue

        count += 1
        col = task.get("column", "?")
        tid = task.get("id", path.name)
        title = task.get("title", "")
        assignees = ",".join(task.get("assignees") or [])
        print(f"{tid:28} [{col:7}] {title} (assignees: {assignees})")

    if count == 0:
        print("No matching tasks.")


def cmd_validate(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    board = load_board(root)
    agents = load_agents(root)

    col_ids = set(get_column_ids(board))
    valid_agent_ids = {a["id"] for a in agents["agents"]}

    tasks_root = root / "tasks"
    errors = 0
    warnings = 0

    for path in tasks_root.rglob("*.yaml"):
        task = load_yaml(path)
        if not isinstance(task, dict):
            print(f"ERROR: {path} is not a dict")
            errors += 1
            continue

        tid = task.get("id", path.name)
        col = task.get("column")
        status = task.get("status")

        # Check column/status
        if col not in col_ids:
            print(f"ERROR: Task {tid} has unknown column '{col}' (file: {path})")
            errors += 1

        if status not in col_ids:
            print(f"WARNING: Task {tid} has status '{status}' not in board columns")
            warnings += 1

        # Check directory matches column
        try:
            parent_col = path.parent.name
            if col and parent_col != col:
                print(
                    f"WARNING: Task {tid} column '{col}' does not match dir '{parent_col}' (file: {path})"
                )
                warnings += 1
        except Exception:
            pass

        # Check assignees
        for a in task.get("assignees") or []:
            if a not in valid_agent_ids:
                print(f"WARNING: Task {tid} has unknown assignee '{a}'")
                warnings += 1

    print(f"Validation complete. Errors: {errors}, Warnings: {warnings}")
    if errors or warnings:
        sys.exit(1)


def cmd_start_task(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    agents = load_agents(root)
    board = load_board(root)

    valid_ids = {a["id"] for a in agents["agents"]}
    if args.agent not in valid_ids:
        raise RuntimeError(f"Unknown agent '{args.agent}'")

    # Locate the task
    task_path = find_task_file(root, args.id)
    task = load_yaml(task_path)

    col_ids = get_column_ids(board)
    target_column = args.column or "doing"
    if target_column not in col_ids:
        raise RuntimeError(f"Unknown column '{target_column}'")

    # Move task into the target column (if needed)
    old_column = task.get("column", task.get("status"))
    if old_column != target_column:
        new_dir = root / "tasks" / target_column
        new_dir.mkdir(parents=True, exist_ok=True)
        new_path = new_dir / task_path.name

        task["column"] = target_column
        task["status"] = target_column
        task["updated_at"] = now_iso()
        task.setdefault("history", []).append(
            {
                "at": task["updated_at"],
                "by": "cli",
                "event": "moved",
                "details": f"{old_column} -> {target_column}",
            }
        )

        save_yaml(new_path, task)
        if new_path != task_path:
            task_path.unlink()
        task_path = new_path

    # Create workspace symlink
    ws_link = root / "workspaces" / args.agent / target_column / task_path.name
    create_symlink(task_path, ws_link)

    print(f"Agent {args.agent} started work on {args.id} in column {target_column}")
    print(f"Workspace link: {ws_link}")


def cmd_stop_task(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()

    # Workspace link (we don't need to touch canonical file)
    # We just need to know which column it's in; user passes it or we search.
    agent_ws_root = root / "workspaces" / args.agent

    if args.column:
        link = agent_ws_root / args.column / f"{args.id}.yaml"
        if not link.exists():
            print(f"No workspace link found for {args.id} in {args.column} for agent {args.agent}")
            return
        remove_symlink(link)
        print(f"Agent {args.agent} stopped work on {args.id} in column {args.column}")
    else:
        # Search all columns under this agent's workspace
        found = False
        if agent_ws_root.exists():
            for p in agent_ws_root.rglob(f"{args.id}.yaml"):
                if p.is_symlink():
                    remove_symlink(p)
                    print(f"Removed workspace link: {p}")
                    found = True
        if not found:
            print(f"No workspace link found for {args.id} for agent {args.agent}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Filesystem-based task board for AI agents."
    )
    parser.add_argument(
        "--root",
        type=str,
        default="crewkan_board",
        help="Root directory for the board (default: crewkan_board)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # Agents
    p_list_agents = sub.add_parser("list-agents", help="List all agents")
    p_list_agents.set_defaults(func=cmd_list_agents)

    p_add_agent = sub.add_parser("add-agent", help="Add a new agent")
    p_add_agent.add_argument("--id", required=True, help="Agent id (stable)")
    p_add_agent.add_argument("--name", help="Agent name")
    p_add_agent.add_argument("--role", help="Agent role")
    p_add_agent.add_argument("--kind", choices=["ai", "human"], default="ai", help="Agent kind (ai or human)")
    p_add_agent.set_defaults(func=cmd_add_agent)

    p_remove_agent = sub.add_parser("remove-agent", help="Remove an agent")
    p_remove_agent.add_argument("--id", required=True, help="Agent id")
    p_remove_agent.set_defaults(func=cmd_remove_agent)

    # Tasks
    p_new_task = sub.add_parser("new-task", help="Create a new task")
    p_new_task.add_argument("--title", required=True, help="Task title")
    p_new_task.add_argument("--description", help="Task description")
    p_new_task.add_argument(
        "--column", required=True, help="Column id to create task in"
    )
    p_new_task.add_argument(
        "--assignee",
        action="append",
        help="Agent id to assign (can repeat)",
    )
    p_new_task.add_argument(
        "--priority",
        choices=["low", "medium", "high"],
        help="Task priority",
    )
    p_new_task.add_argument(
        "--tags",
        help="Comma-separated tags (e.g. infra,analytics)",
    )
    p_new_task.add_argument(
        "--due-date",
        help="Due date (free-form string, e.g. 2025-11-30)",
    )
    p_new_task.add_argument(
        "--id",
        help="Optional explicit task id; otherwise auto-generated",
    )
    p_new_task.set_defaults(func=cmd_new_task)

    p_move_task = sub.add_parser("move-task", help="Move a task to another column")
    p_move_task.add_argument("--id", required=True, help="Task id")
    p_move_task.add_argument("--column", required=True, help="Target column id")
    p_move_task.set_defaults(func=cmd_move_task)

    p_assign_task = sub.add_parser("assign-task", help="Assign agents to a task")
    p_assign_task.add_argument("--id", required=True, help="Task id")
    p_assign_task.add_argument(
        "--assignee",
        required=True,
        action="append",
        help="Agent id to assign (can repeat)",
    )
    p_assign_task.set_defaults(func=cmd_assign_task)

    p_list_tasks = sub.add_parser("list-tasks", help="List tasks")
    p_list_tasks.add_argument(
        "--column",
        help="Filter by column id",
    )
    p_list_tasks.add_argument(
        "--agent",
        help="Filter by agent id",
    )
    p_list_tasks.set_defaults(func=cmd_list_tasks)

    p_validate = sub.add_parser("validate", help="Validate board structure")
    p_validate.set_defaults(func=cmd_validate)

    # Workspace commands
    p_start_task = sub.add_parser("start-task", help="Agent starts work on a task")
    p_start_task.add_argument("--id", required=True, help="Task id")
    p_start_task.add_argument("--agent", required=True, help="Agent id")
    p_start_task.add_argument(
        "--column",
        help="Column to move task into (default: doing)",
    )
    p_start_task.set_defaults(func=cmd_start_task)

    p_stop_task = sub.add_parser("stop-task", help="Agent stops work on a task (remove workspace link)")
    p_stop_task.add_argument("--id", required=True, help="Task id")
    p_stop_task.add_argument("--agent", required=True, help="Agent id")
    p_stop_task.add_argument(
        "--column",
        help="Column the task is in (if omitted, search all)",
    )
    p_stop_task.set_defaults(func=cmd_stop_task)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

