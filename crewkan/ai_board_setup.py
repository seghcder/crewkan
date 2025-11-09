#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys
import yaml

DEFAULT_COLUMNS = [
    {"id": "backlog", "name": "Backlog", "wip_limit": None},
    {"id": "todo", "name": "To Do", "wip_limit": 10},
    {"id": "doing", "name": "Doing", "wip_limit": 5},
    {"id": "done", "name": "Done", "wip_limit": None},
]

DEFAULT_AGENTS = {
    "agents": []
}

DEFAULT_BOARD = {
    "board_name": "AI Company Board",
    "version": 1,
    "columns": DEFAULT_COLUMNS,
    "settings": {
        "default_priority": "medium",
        "task_filename_prefix": "T",
        "timezone": "UTC",
    },
}


def write_yaml(path: Path, data: dict, overwrite: bool = False):
    if path.exists() and not overwrite:
        print(f"Skip existing file: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)
    print(f"Wrote {path}")


def ensure_dirs(root: Path, columns):
    (root / "agents").mkdir(parents=True, exist_ok=True)
    (root / "tasks").mkdir(parents=True, exist_ok=True)
    (root / "archive" / "tasks").mkdir(parents=True, exist_ok=True)

    for col in columns:
        col_id = col["id"]
        (root / "tasks" / col_id).mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(
        description="Initialize an AI agent task board on the filesystem."
    )
    parser.add_argument(
        "--root",
        type=str,
        default="ai_board",
        help="Root directory for the board (default: ai_board)",
    )
    parser.add_argument(
        "--with-sample-agents",
        action="store_true",
        help="Create a couple of sample agents.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing YAML files if they exist.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    print(f"Initializing board at: {root}")

    # Prepare default board and agents
    board_data = DEFAULT_BOARD

    if args.with_sample_agents:
        agents_data = {
            "agents": [
                {
                    "id": "nuni",
                    "name": "Nuni",
                    "role": "Hospital AI Orchestrator",
                    "status": "active",
                    "skills": ["infection_control", "analytics"],
                    "metadata": {},
                },
                {
                    "id": "tau",
                    "name": "Tau",
                    "role": "Infrastructure Architect Agent",
                    "status": "active",
                    "skills": ["infra_arch", "terraform", "devops"],
                    "metadata": {},
                },
            ]
        }
    else:
        agents_data = DEFAULT_AGENTS

    ensure_dirs(root, board_data["columns"])

    write_yaml(root / "board.yaml", board_data, overwrite=args.force)
    write_yaml(root / "agents" / "agents.yaml", agents_data, overwrite=args.force)

    print("Done.")


if __name__ == "__main__":
    sys.exit(main())

