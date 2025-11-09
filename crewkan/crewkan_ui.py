#!/usr/bin/env python3

import streamlit as st
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
import os
import sys
import time
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.utils import load_yaml, save_yaml, now_iso, generate_task_id
from crewkan.board_core import BoardClient, BoardError

# Set up logging to file in tmp directory
log_dir = Path(__file__).resolve().parent.parent.parent / "tmp"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"crewkan_ui_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stderr),  # Also log to stderr
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"=== CrewKan UI Starting ===")
logger.info(f"Log file: {log_file}")
logger.info(f"Python: {sys.executable}")
logger.info(f"Working directory: {os.getcwd()}")

# Get board root from environment variable (re-evaluated each time)
def get_board_root() -> Path:
    """Get the board root directory from environment or default."""
    board_root = os.getenv("CREWKAN_BOARD_ROOT", "crewkan_board")
    return Path(board_root).resolve()

BOARD_ROOT = get_board_root()  # Initial value, but functions should call get_board_root()


def load_board():
    board_root = get_board_root()
    board = load_yaml(board_root / "board.yaml")
    if not board:
        st.error(f"No board.yaml found in {board_root}")
        st.stop()
    return board


def load_agents():
    board_root = get_board_root()
    agents = load_yaml(board_root / "agents" / "agents.yaml", default={"agents": []})
    if "agents" not in agents:
        agents["agents"] = []
    return agents["agents"]




def iter_tasks():
    board_root = get_board_root()
    tasks_root = board_root / "tasks"
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

        board_root = get_board_root()
        new_dir = board_root / "tasks" / new_column
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
    """Create a task using BoardClient for proper updates."""
    logger.info("=" * 50)
    logger.info("create_task() FUNCTION CALLED")
    logger.info(f"  title: '{title}'")
    logger.info(f"  description: '{description}'")
    logger.info(f"  column_id: {column_id}")
    logger.info(f"  assignee_ids: {assignee_ids}")
    logger.info(f"  priority: {priority}")
    logger.info(f"  tags: '{tags}'")
    logger.info(f"  due_date_str: {due_date_str}")
    logger.info("=" * 50)
    
    try:
        # Use BoardClient for proper task creation
        logger.info("Loading agents...")
        agents = load_agents()
        logger.info(f"Loaded {len(agents)} agents: {[a.get('id') for a in agents]}")
        
        if not agents:
            error_msg = "No agents found in board. Please create at least one agent first."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        default_agent = agents[0]["id"]
        logger.info(f"Using agent: {default_agent}")
        
        board_root = get_board_root()
        logger.info(f"Board root: {board_root}")
        
        logger.info("Creating BoardClient...")
        client = BoardClient(board_root, default_agent)
        logger.info("BoardClient created successfully")
        
        logger.info("Calling client.create_task()...")
        task_id = client.create_task(
            title=title,
            description=description or "",
            column=column_id,
            assignees=assignee_ids,
            priority=priority or None,
            tags=[t.strip() for t in tags.split(",") if t.strip()] if tags else [],
            due_date=due_date_str or None,
        )
        logger.info(f"✅ Successfully created task {task_id} via BoardClient")
        logger.info(f"Task file should be at: {board_root / 'tasks' / column_id / f'{task_id}.yaml'}")
        return task_id
    except Exception as e:
        # Fallback to direct creation
        logger.warning(f"BoardClient create_task failed, using fallback: {e}", exc_info=True)
        logger.info("Attempting fallback creation method...")
        
        board = load_board()
        if not board:
            error_msg = "Cannot create task: board not loaded"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        prefix = board.get("settings", {}).get("task_filename_prefix", "T")
        task_id: str = generate_task_id(prefix)
        created_at = now_iso()
        logger.info(f"Generated task ID: {task_id}")

        task = {
            "id": task_id,
            "title": title,
            "description": description or "",
            "status": column_id,
            "column": column_id,
            "priority": priority or board.get("settings", {}).get("default_priority", "medium"),
            "tags": [t.strip() for t in tags.split(",") if t.strip()] if tags else [],
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

        board_root = get_board_root()
        col_dir = board_root / "tasks" / column_id
        logger.info(f"Creating task directory: {col_dir}")
        col_dir.mkdir(parents=True, exist_ok=True)
        path = col_dir / f"{task_id}.yaml"
        logger.info(f"Saving task to: {path}")
        save_yaml(path, task)
        logger.info(f"✅ Successfully created task {task_id} via fallback method")
        logger.info(f"Task file saved to: {path}")
        return task_id


def main() -> None:
    st.set_page_config(page_title="AI Agent Board", layout="wide")
    
    logger.info("=== Main function called ===")
    logger.info(f"Session state keys: {list(st.session_state.keys())}")

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

    # New task form - improved with better error handling
    st.sidebar.header("New task")
    
    logger.debug(f"Setting up form. Agents available: {[a['id'] for a in agents]}")
    
    # Show any previous error/success message
    if "create_task_message" in st.session_state:
        msg_type = st.session_state.get("create_task_message_type", "info")
        msg = st.session_state["create_task_message"]
        logger.info(f"Showing message: {msg_type} - {msg}")
        if msg_type == "success":
            st.sidebar.success(msg)
            # Also show a toast notification
            st.toast(msg, icon="✅")
        elif msg_type == "error":
            st.sidebar.error(msg)
            st.toast(msg, icon="❌")
        # Clear message after showing
        del st.session_state["create_task_message"]
        del st.session_state["create_task_message_type"]
    
    with st.sidebar.form("new_task_form", clear_on_submit=True):
        title = st.text_input("Title *", key="new_task_title")
        description = st.text_area("Description", height=100, key="new_task_desc")
        column_id = st.selectbox("Column", col_ids, key="new_task_column")
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=1, key="new_task_priority")
        tag_str = st.text_input("Tags (comma separated)", key="new_task_tags")
        assignee_multiselect = st.multiselect(
            "Assignees",
            [a["id"] for a in agents] if agents else [],
            key="new_task_assignees",
        )
        due_date_str = st.text_input("Due date (optional text)", value="", key="new_task_due")
        
        submitted = st.form_submit_button("Create Task", type="primary", use_container_width=True)
        
        # Process form submission immediately when button is clicked
        # With clear_on_submit=True, form values are cleared AFTER this block runs
        # So we capture and process values while they're still available
        if submitted:
            # Capture form values immediately (they'll be cleared after this block)
            captured_title = title
            captured_description = description
            captured_column = column_id
            captured_priority = priority
            captured_tags = tag_str
            captured_assignees = assignee_multiselect
            captured_due_date = due_date_str
            logger.info("=" * 50)
            logger.info("FORM SUBMITTED!")
            logger.info(f"Title: '{captured_title}'")
            logger.info(f"Description: '{captured_description}'")
            logger.info(f"Column: {captured_column}")
            logger.info(f"Priority: {captured_priority}")
            logger.info(f"Tags: '{captured_tags}'")
            logger.info(f"Assignees: {captured_assignees}")
            logger.info(f"Due date: '{captured_due_date}'")
            logger.info("=" * 50)
            
            if not captured_title or not captured_title.strip():
                logger.warning("Form submitted but title is empty")
                st.session_state["create_task_message"] = "⚠️ Title is required."
                st.session_state["create_task_message_type"] = "error"
                st.rerun()
            else:
                try:
                    logger.info(f"Attempting to create task: '{captured_title.strip()}'")
                    task_id = create_task(
                        captured_title.strip(),
                        captured_description.strip() if captured_description else "",
                        captured_column,
                        captured_assignees,
                        captured_priority,
                        captured_tags.strip() if captured_tags else "",
                        captured_due_date.strip() or None,
                    )
                    logger.info(f"✅ Task created successfully: {task_id}")
                    success_msg = f"✅ Created task {task_id}"
                    st.session_state["create_task_message"] = success_msg
                    st.session_state["create_task_message_type"] = "success"
                    # Show immediate confirmation
                    st.toast(success_msg, icon="✅")
                    logger.info("Triggering rerun after successful task creation")
                    # Form will be cleared automatically by clear_on_submit=True
                    st.rerun()
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"❌ Failed to create task: {error_msg}", exc_info=True)
                    st.session_state["create_task_message"] = f"❌ Error: {error_msg}"
                    st.session_state["create_task_message_type"] = "error"
                    st.toast(f"Error: {error_msg}", icon="❌")
                    # Store full error for debugging
                    st.session_state["create_task_error_details"] = str(e)
                    import traceback
                    st.session_state["create_task_traceback"] = traceback.format_exc()
                    logger.error(f"Full traceback:\n{st.session_state['create_task_traceback']}")
                    # Form will be cleared automatically, but we rerun to show error
                    st.rerun()
    
    # Show error details if available
    if "create_task_error_details" in st.session_state:
        with st.sidebar.expander("Error details", expanded=False):
            st.code(st.session_state.get("create_task_traceback", "No traceback available"))
        # Clear after showing
        del st.session_state["create_task_error_details"]
        if "create_task_traceback" in st.session_state:
            del st.session_state["create_task_traceback"]

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

