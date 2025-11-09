What’s a good python framework to visualize it? Like streamlit maybe. Also, let’s create a working area for each agent and maybe we symlink wip files into their area. Or the other way… the master board is made of symlinked files with the actual file in the agent dirs. Work out which better.

-------------

Good question combo: “how do we *see* this thing” and “where should the truth live”.

I’ll split it into:

1. Framework choices (and why I’d pick Streamlit first)
2. Symlink architecture: where the canonical tasks live
3. Updated filesystem layout with agent workspaces
4. Python: workspace + symlink helpers (CLI-style)
5. A minimal Streamlit UI to visualize/manage the board

---

## 1. Frameworks to visualize the board

In Python land, these are the most practical options:

* **Streamlit**

  * Fastest path to “Trello-ish” web UI: columns, filters, buttons.
  * Good for AI agents too (simple HTTP, no JS needed on your side).
  * Hot-reload + easy deployment (local, container, whatever).

* **Textual** (TUI framework)

  * If you want a nice terminal app (rich widgets, columns, mouse support).
  * Great for SSH-only environments, but less “clickable dashboard” than Streamlit.

* **FastAPI + something (React/Vue/etc.)**

  * Best for long-term productization.
  * Overkill if you just want a dev-facing “board viewer” right now.

* **Panel/Dash/Plotly/NiceGUI**

  * All viable, but Streamlit has the lowest friction for forms + buttons + layout.

Given your constraints (filesystem + YAML + git; agent-friendly), **I’d start with Streamlit**, and maybe later wrap the same underlying Python library with a FastAPI if you need more structured APIs.

---

## 2. Symlink direction: where is the source of truth?

You suggested two possibilities:

1. **Master board is canonical.**

   * Tasks live under `tasks/<column>/...yaml`.
   * Each agent gets a workspace where we create **symlinks to canonical task files** they’re actively working on.

2. **Agent dirs are canonical.**

   * Tasks live under `workspaces/<agent>/...yaml`.
   * The master board (columns) is a collection of symlinks back to agent files.

I’d strongly recommend **Option 1 (master board canonical)**:

* The **board is the single source of truth**. Git diff history lines up with the conceptual board structure.
* It is trivial to answer “show me all `doing` tasks”, “backlog count”, etc. by just walking `tasks/`.
* Agents can collaborate on a task: multiple workspaces can link to the same file.
* All mutation flows (CLI, Streamlit, other AI agents) can treat `tasks/` as canonical.

Agent workspaces then become **views** / “checkouts” of canonical tasks.

---

## 3. Updated filesystem layout with workspaces

Let’s extend the previous layout:

```text
ai_board/
  board.yaml
  agents/
    agents.yaml

  tasks/                 # canonical truth
    backlog/
      T-20251109-aaaaaa.yaml
    todo/
      T-20251109-bbbbbb.yaml
    doing/
      T-20251109-cccccc.yaml
    done/

  workspaces/            # agent-centric views, mainly symlinks
    nuni/
      doing/
        T-20251109-cccccc.yaml -> ../../../tasks/doing/T-20251109-cccccc.yaml
    tau/
      todo/
        T-20251110-dddddd.yaml -> ../../../tasks/todo/T-20251110-dddddd.yaml

  archive/
    tasks/
      2025-11/
        T-20251001-zzzzzz.yaml
```

Conventions:

* `tasks/` = canonical task files (what you actually commit, diff, etc.).
* `workspaces/<agent>/<column>/` = symlinks for tasks that agent is “actively holding” in that column.

  * You could also just use `workspaces/<agent>/` without column subdirs; I like mirroring columns because it’s self-documenting.

Operations:

* **Start work** on a task for agent A:

  * Ensure task is in `doing` (or move it there).
  * Create symlink in `workspaces/A/doing/<task_id>.yaml` pointing to `tasks/doing/<task_id>.yaml`.

* **Stop work** (optional):

  * Remove symlink from `workspaces/A/...`
  * Optional: move back to `todo` or leave in `doing` depending on your flow.

This keeps:

* “Board view” simple.
* “Agent view” lightweight and git-safe (symlinks are small; changes still happen in canonical files).

---

## 4. Python: workspace + symlink helpers

Here’s how you can bolt workspace operations onto the earlier CLI design.

### 4.1. Helpers for symlinks and workspaces

These functions assume the same `ai_board_cli.py` from before, but you can drop them into a shared `board_lib.py` or similar.

```python
# workspace_utils.py (or inside your main CLI module)
import os
from pathlib import Path
from datetime import datetime, timezone
import yaml

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def find_task_file(root: Path, task_id: str) -> Path:
    tasks_root = root / "tasks"
    for p in tasks_root.rglob("*.yaml"):
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict) and data.get("id") == task_id:
            return p
    raise RuntimeError(f"Task {task_id} not found under {tasks_root}")
```

### 4.2. Start / stop work commands

Add two new CLI subcommands to your existing `ai_board_cli.py`:

```python
def cmd_start_task(args):
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


def cmd_stop_task(args):
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
```

And wire them into the argument parser:

```python
def build_parser():
    parser = argparse.ArgumentParser(
        description="Filesystem-based task board for AI agents."
    )
    parser.add_argument(
        "--root",
        type=str,
        default="ai_board",
        help="Root directory for the board (default: ai_board)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ... existing subcommands ...

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
```

Usage:

```bash
# Agent nuni starts working on a task (moves to doing, creates symlink)
python ai_board_cli.py start-task --id T-20251109-3fae2c --agent nuni

# Agent nuni stops work (just removes workspace link)
python ai_board_cli.py stop-task --id T-20251109-3fae2c --agent nuni
```

---

## 5. Minimal Streamlit UI for the board

Here’s a basic `ai_board_ui.py` to visualize:

* Columns and tasks (kanban-ish)
* Filter by agent
* Simple actions: move task between columns, assign to agent, create new tasks

It reads/writes the same YAML structure as the CLI.

```python
#!/usr/bin/env python3

import streamlit as st
from pathlib import Path
import yaml
from datetime import datetime, timezone
import uuid

# Adjust or make this a config/ENV var
BOARD_ROOT = Path("ai_board").resolve()


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_yaml(path: Path, default=None):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def load_board():
    board = load_yaml(BOARD_ROOT / "board.yaml")
    if not board:
        st.error(f"No board.yaml found in {BOARD_ROOT}")
        st.stop()
    return board


def load_agents():
    agents = load_yaml(BOARD_ROOT / "agents" / "agents.yaml", default={"agents": []})
    if "agents" not in agents:
        agents["agents"] = []
    return agents["agents"]


def generate_task_id(prefix="T"):
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    return f"{prefix}-{ts}-{suffix}"


def iter_tasks():
    tasks_root = BOARD_ROOT / "tasks"
    for path in tasks_root.rglob("*.yaml"):
        data = load_yaml(path)
        if isinstance(data, dict):
            yield path, data


def move_task(task_data, task_path: Path, new_column: str):
    old_column = task_data.get("column", task_data.get("status"))
    if old_column == new_column:
        return

    task_data["column"] = new_column
    task_data["status"] = new_column
    task_data["updated_at"] = now_iso()
    task_data.setdefault("history", []).append(
        {
            "at": task_data["updated_at"],
            "by": "ui",
            "event": "moved",
            "details": f"{old_column} -> {new_column}",
        }
    )

    new_dir = BOARD_ROOT / "tasks" / new_column
    new_dir.mkdir(parents=True, exist_ok=True)
    new_path = new_dir / task_path.name
    save_yaml(new_path, task_data)
    if new_path != task_path:
        task_path.unlink()


def assign_task(task_data, task_path: Path, agent_id: str):
    assignees = set(task_data.get("assignees") or [])
    assignees.add(agent_id)
    task_data["assignees"] = sorted(assignees)
    task_data["updated_at"] = now_iso()
    task_data.setdefault("history", []).append(
        {
            "at": task_data["updated_at"],
            "by": "ui",
            "event": "assigned",
            "details": f"Assigned {agent_id}",
        }
    )
    save_yaml(task_path, task_data)


def create_task(title, description, column_id, assignee_ids, priority, tags, due_date_str):
    board = load_board()
    prefix = board.get("settings", {}).get("task_filename_prefix", "T")
    task_id = generate_task_id(prefix)
    created_at = now_iso()

    task = {
        "id": task_id,
        "title": title,
        "description": description or "",
        "status": column_id,
        "column": column_id,
        "priority": priority or board.get("settings", {}).get("default_priority", "medium"),
        "tags": tags.split(",") if tags else [],
        "assignees": assignee_ids,
        "dependencies": [],
        "created_at": created_at,
        "updated_at": created_at,
        "due_date": due_date_str or None,
        "history": [
            {
                "at": created_at,
                "by": "ui",
                "event": "created",
                "details": f"Task created in column {column_id}",
            }
        ],
    }

    col_dir = BOARD_ROOT / "tasks" / column_id
    col_dir.mkdir(parents=True, exist_ok=True)
    path = col_dir / f"{task_id}.yaml"
    save_yaml(path, task)
    return task_id


def main():
    st.set_page_config(page_title="AI Agent Board", layout="wide")

    st.title("AI Agent Task Board")

    board = load_board()
    agents = load_agents()
    columns = board.get("columns", [])
    col_ids = [c["id"] for c in columns]

    # Sidebar filters
    st.sidebar.header("Filters")

    agent_options = ["(all)"] + [a["id"] for a in agents]
    selected_agent = st.sidebar.selectbox("Filter by agent", agent_options)

    col_filter_options = ["(all)"] + col_ids
    selected_column_filter = st.sidebar.selectbox("Filter by column", col_filter_options)

    # New task form
    st.sidebar.header("New task")

    with st.sidebar.form("new_task_form"):
        title = st.text_input("Title")
        description = st.text_area("Description", height=100)
        column_id = st.selectbox("Column", col_ids)
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=1)
        tag_str = st.text_input("Tags (comma separated)")
        assignee_multiselect = st.multiselect(
            "Assignees",
            [a["id"] for a in agents],
        )
        due_date_str = st.text_input("Due date (optional text)", value="")
        submitted = st.form_submit_button("Create task")
        if submitted:
            if not title:
                st.warning("Title is required.")
            else:
                task_id = create_task(
                    title,
                    description,
                    column_id,
                    assignee_multiselect,
                    priority,
                    tag_str,
                    due_date_str.strip() or None,
                )
                st.success(f"Created task {task_id}")
                st.experimental_rerun()

    # Load tasks and filter
    tasks_by_column = {cid: [] for cid in col_ids}
    for path, task in iter_tasks():
        col = task.get("column")
        if col not in tasks_by_column:
            continue

        if selected_agent != "(all)":
            if selected_agent not in (task.get("assignees") or []):
                continue

        if selected_column_filter != "(all)" and col != selected_column_filter:
            continue

        tasks_by_column[col].append((path, task))

    # Render columns as horizontal layout
    cols = st.columns(len(columns)) if columns else []

    for idx, col_def in enumerate(columns):
        cid = col_def["id"]
        cname = col_def.get("name", cid)
        col_tasks = tasks_by_column.get(cid, [])

        with cols[idx]:
            st.subheader(cname)
            if not col_tasks:
                st.write("_No tasks_")
                continue

            for path, task in col_tasks:
                tid = task.get("id")
                title = task.get("title", "")
                assignees = ", ".join(task.get("assignees") or [])
                priority = task.get("priority", "medium")
                tags = ", ".join(task.get("tags") or [])
                due = task.get("due_date") or ""

                with st.expander(f"{tid}: {title}", expanded=False):
                    st.markdown(f"**Priority:** {priority}")
                    st.markdown(f"**Assignees:** {assignees or '-'}")
                    st.markdown(f"**Tags:** {tags or '-'}")
                    if due:
                        st.markdown(f"**Due:** {due}")
                    desc = task.get("description", "")
                    if desc:
                        st.markdown("---")
                        st.markdown(desc)

                    # Move task
                    target_col = st.selectbox(
                        "Move to column",
                        ["(no change)"] + col_ids,
                        key=f"move_select_{tid}",
                    )
                    if st.button("Move", key=f"move_btn_{tid}"):
                        if target_col != "(no change)":
                            move_task(task, path, target_col)
                            st.experimental_rerun()

                    # Assign task
                    assign_to = st.selectbox(
                        "Assign to agent",
                        ["(none)"] + [a["id"] for a in agents],
                        key=f"assign_select_{tid}",
                    )
                    if st.button("Assign", key=f"assign_btn_{tid}"):
                        if assign_to != "(none)":
                            assign_task(task, path, assign_to)
                            st.experimental_rerun()


if __name__ == "__main__":
    main()
```

Run it:

```bash
streamlit run ai_board_ui.py
```

That gives you:

* A multi-column layout (one per board column).
* Expandable task “cards”.
* Buttons to move and assign tasks.
* A sidebar to create tasks and filter by agent/column.

---

If you’d like, next step we can:

* Make Streamlit also surface **agent workspaces** (e.g., show which tasks are “checked out” by which agent via symlinks).
* Factor the CLI and UI onto a shared `board_lib.py` so the logic isn’t duplicated and your agents can call it as a Python library or via MCP.
