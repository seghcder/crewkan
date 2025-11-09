#!/usr/bin/env python3

import streamlit as st
from pathlib import Path
import yaml
from datetime import datetime, timezone
import uuid
import os

# Adjust or make this a config/ENV var
BOARD_ROOT = Path(os.getenv("CREWKAN_BOARD_ROOT", "crewkan_board")).resolve()


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
    if not tasks_root.exists():
        return
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
                st.rerun()

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
                            st.rerun()

                    # Assign task
                    assign_to = st.selectbox(
                        "Assign to agent",
                        ["(none)"] + [a["id"] for a in agents],
                        key=f"assign_select_{tid}",
                    )
                    if st.button("Assign", key=f"assign_btn_{tid}"):
                        if assign_to != "(none)":
                            assign_task(task, path, assign_to)
                            st.rerun()


if __name__ == "__main__":
    main()

