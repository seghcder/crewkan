#!/usr/bin/env python3

import streamlit as st
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.utils import load_yaml, save_yaml, now_iso, generate_task_id
from crewkan.board_core import BoardClient, BoardError

# Adjust or make this a config/ENV var
BOARD_ROOT = Path(os.getenv("CREWKAN_BOARD_ROOT", "crewkan_board")).resolve()


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




def iter_tasks():
    tasks_root = BOARD_ROOT / "tasks"
    if not tasks_root.exists():
        return
    for path in tasks_root.rglob("*.yaml"):
        data = load_yaml(path)
        if isinstance(data, dict):
            yield path, data


def move_task(task_data: Dict[str, Any], task_path: Path, new_column: str) -> None:
    """Move task using BoardClient for proper updates."""
    try:
        # Use BoardClient for proper move
        board_root = task_path.parent.parent.parent
        agents = load_agents()
        default_agent = agents[0]["id"] if agents else "ui"
        
        client = BoardClient(board_root, default_agent)
        client.move_task(task_data["id"], new_column)
    except Exception as e:
        # Fallback to direct update
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


def assign_task(task_data: Dict[str, Any], task_path: Path, agent_id: str) -> None:
    """Assign task using BoardClient for proper updates."""
    try:
        # Use BoardClient for proper assignment
        board_root = task_path.parent.parent.parent
        agents = load_agents()
        default_agent = agents[0]["id"] if agents else "ui"
        
        client = BoardClient(board_root, default_agent)
        client.reassign_task(task_data["id"], agent_id, keep_existing=True)
    except Exception as e:
        # Fallback to direct update
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


def create_task(title: str, description: str, column_id: str, assignee_ids: List[str], priority: str, tags: str, due_date_str: Optional[str]) -> str:
    board = load_board()
    prefix = board.get("settings", {}).get("task_filename_prefix", "T")
    task_id: str = generate_task_id(prefix)
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


def main() -> None:
    st.set_page_config(page_title="AI Agent Board", layout="wide")

    st.title("AI Agent Task Board")

    # Auto-refresh if filesystem changes detected
    if "last_check" not in st.session_state:
        st.session_state.last_check = time.time()
    
    # Check for filesystem changes (simple polling)
    current_time = time.time()
    if current_time - st.session_state.last_check > 2.0:  # Check every 2 seconds
        st.session_state.last_check = current_time
        # Trigger rerun if board files changed (Streamlit will handle this)
        st.rerun()

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

                # Display task - filename in dropdown, not in top description
                with st.expander(f"{title}", expanded=False):
                    st.caption(f"ID: {tid} | File: {path.name}")
                    st.markdown(f"**Priority:** {priority}")
                    st.markdown(f"**Assignees:** {assignees or '-'}")
                    st.markdown(f"**Tags:** {tags or '-'}")
                    if due:
                        st.markdown(f"**Due:** {due}")
                    desc = task.get("description", "")
                    if desc:
                        st.markdown("---")
                        st.markdown(desc)

                    # Rename task
                    new_title = st.text_input(
                        "Rename task",
                        value=title,
                        key=f"rename_input_{tid}",
                    )
                    if st.button("Rename", key=f"rename_btn_{tid}"):
                        if new_title and new_title != title:
                            try:
                                board_root = path.parent.parent.parent
                                agents = load_agents()
                                default_agent = agents[0]["id"] if agents else "ui"
                                client = BoardClient(board_root, default_agent)
                                client.update_task_field(tid, "title", new_title)
                                st.success(f"Renamed to: {new_title}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error renaming: {e}")

                    # Update tags
                    new_tags_str = st.text_input(
                        "Tags (comma separated)",
                        value=tags,
                        key=f"tags_input_{tid}",
                    )
                    if st.button("Update Tags", key=f"tags_btn_{tid}"):
                        if new_tags_str != tags:
                            try:
                                board_root = path.parent.parent.parent
                                agents = load_agents()
                                default_agent = agents[0]["id"] if agents else "ui"
                                client = BoardClient(board_root, default_agent)
                                # Tags need to be updated as a list
                                new_tags = [t.strip() for t in new_tags_str.split(",") if t.strip()] if new_tags_str else []
                                # Update task directly for tags (update_task_field expects string)
                                task["tags"] = new_tags
                                task["updated_at"] = now_iso()
                                task.setdefault("history", []).append({
                                    "at": task["updated_at"],
                                    "by": "ui",
                                    "event": "tags_updated",
                                    "details": f"Tags: {', '.join(new_tags)}",
                                })
                                save_yaml(path, task)
                                st.success("Tags updated")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating tags: {e}")

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
                    
                    # Add comment
                    comment_text = st.text_area(
                        "Add comment",
                        key=f"comment_input_{tid}",
                        height=60,
                    )
                    if st.button("Add Comment", key=f"comment_btn_{tid}"):
                        if comment_text.strip():
                            try:
                                board_root = path.parent.parent.parent
                                agents = load_agents()
                                default_agent = agents[0]["id"] if agents else "ui"
                                client = BoardClient(board_root, default_agent)
                                client.add_comment(tid, comment_text.strip())
                                st.success("Comment added")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error adding comment: {e}")


if __name__ == "__main__":
    main()

