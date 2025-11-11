#!/usr/bin/env python3

import streamlit as st
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
import os
import sys
import time
import logging
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.utils import load_yaml, save_yaml, now_iso, generate_task_id
from crewkan.board_core import BoardClient, BoardError
from crewkan.kanban_native import kanban_board

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

# Filter out noisy third-party loggers BEFORE creating our logger
logging.getLogger("watchdog").setLevel(logging.WARNING)
logging.getLogger("watchdog.observers").setLevel(logging.WARNING)
logging.getLogger("watchdog.observers.inotify_buffer").setLevel(logging.WARNING)
logging.getLogger("watchdog.observers.inotify").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

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
    """Iterate over all tasks from both 'tasks' and 'issues' directories."""
    board_root = get_board_root()
    
    # Check both 'tasks' and 'issues' directories for backwards compatibility
    for dir_name in ["tasks", "issues"]:
        tasks_root = board_root / dir_name
        if not tasks_root.exists():
            continue
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


def render_task_details_page(task_id: str, task_data: dict, path: Path) -> None:
    """Render a detailed task view page (Jira-style layout)."""
    board_root = get_board_root()
    agents = load_agents()
    agent_map = {a["id"]: a for a in agents}
    
    # Get BoardClient for API calls
    default_agent = agents[0]["id"] if agents else "ui"
    client = BoardClient(board_root, default_agent)
    
    # Get comments
    comments = client.get_comments(task_id)
    
    # Back button
    if st.button("← Back to Board", key="back_to_board"):
        if "viewing_task" in st.session_state:
            del st.session_state["viewing_task"]
        st.rerun()
    
    st.title(task_data.get("title", "Untitled Task"))
    
    # Layout: Left 1/3 for attributes, Right 2/3 for main content
    left_col, right_col = st.columns([1, 2])
    
    with left_col:
        st.header("Attributes")
        
        # Task ID
        st.markdown(f"**Task ID:**")
        st.code(task_data.get("id", ""), language=None)
        
        # Status/Column
        column = task_data.get("column", task_data.get("status", "unknown"))
        st.markdown(f"**Status:** {column}")
        
        # Priority
        priority = task_data.get("priority", "medium")
        priority_colors = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        st.markdown(f"**Priority:** {priority_colors.get(priority, '⚪')} {priority}")
        
        # Assignees
        assignees = task_data.get("assignees", [])
        st.markdown(f"**Assignees:**")
        if assignees:
            for assignee_id in assignees:
                agent = agent_map.get(assignee_id, {})
                agent_name = agent.get("name", assignee_id)
                st.markdown(f"- {agent_name} ({assignee_id})")
        else:
            st.markdown("_None_")
        
        # Tags
        tags = task_data.get("tags", [])
        st.markdown(f"**Tags:**")
        if tags:
            st.markdown(", ".join([f"`{tag}`" for tag in tags]))
        else:
            st.markdown("_None_")
        
        # Due Date
        due_date = task_data.get("due_date")
        if due_date:
            st.markdown(f"**Due Date:** {due_date}")
        
        # Created/Updated
        st.markdown("---")
        created_at = task_data.get("created_at", "")
        updated_at = task_data.get("updated_at", "")
        if created_at:
            st.markdown(f"**Created:** {created_at}")
        if updated_at:
            st.markdown(f"**Updated:** {updated_at}")
        
        # Requested By
        requested_by = task_data.get("requested_by")
        if requested_by:
            agent = agent_map.get(requested_by, {})
            agent_name = agent.get("name", requested_by)
            st.markdown(f"**Requested by:** {agent_name}")
        
        # Quick Actions
        st.markdown("---")
        st.header("Quick Actions")
        
        # Move task
        board = load_board()
        columns = board.get("columns", [])
        col_ids = [c["id"] for c in columns]
        current_col = task_data.get("column", task_data.get("status", ""))
        new_col = st.selectbox(
            "Move to:",
            [c for c in col_ids if c != current_col],
            key=f"detail_move_{task_id}",
        )
        if st.button("Move Task", key=f"detail_move_btn_{task_id}"):
            try:
                client.move_task(task_id, new_col)
                st.success(f"Moved to {new_col}")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
        
        # Reassign
        new_assignee = st.selectbox(
            "Reassign to:",
            ["(none)"] + [a["id"] for a in agents],
            key=f"detail_reassign_{task_id}",
        )
        if st.button("Reassign", key=f"detail_reassign_btn_{task_id}"):
            if new_assignee != "(none)":
                try:
                    client.reassign_task(task_id, new_assignee, keep_existing=False)
                    st.success(f"Reassigned to {new_assignee}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    with right_col:
        # Description
        st.header("Description")
        description = task_data.get("description", "")
        if description:
            st.markdown(description)
        else:
            st.markdown("_No description_")
        
        st.markdown("---")
        
        # Comments Section
        st.header("Comments")
        
        # Add new comment
        with st.expander("Add Comment", expanded=False):
            new_comment = st.text_area("Comment", key=f"new_comment_{task_id}", height=100)
            if st.button("Post Comment", key=f"post_comment_{task_id}"):
                if new_comment.strip():
                    try:
                        comment_id = client.add_comment(task_id, new_comment.strip())
                        st.success(f"Comment added (ID: {comment_id})")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        # Display comments
        if comments:
            for comment in comments:
                comment_id = comment.get("comment_id", "")
                comment_by = comment.get("by", "unknown")
                comment_at = comment.get("at", "")
                comment_details = comment.get("details", "")
                
                agent = agent_map.get(comment_by, {})
                agent_name = agent.get("name", comment_by)
                
                with st.container():
                    st.markdown(f"**{agent_name}** ({comment_by})")
                    if comment_id:
                        st.caption(f"Comment ID: {comment_id} | {comment_at}")
                    else:
                        st.caption(comment_at)
                    st.markdown(comment_details)
                    st.markdown("---")
        else:
            st.markdown("_No comments yet_")
        
        # History (all events)
        st.markdown("---")
        st.header("History")
        history = task_data.get("history", [])
        if history:
            for entry in reversed(history):  # Show newest first
                event = entry.get("event", "")
                event_by = entry.get("by", "unknown")
                event_at = entry.get("at", "")
                event_details = entry.get("details", "")
                
                agent = agent_map.get(event_by, {})
                agent_name = agent.get("name", event_by)
                
                st.markdown(f"**{event.upper()}** by {agent_name} at {event_at}")
                if event_details:
                    st.caption(event_details)
                st.markdown("---")
        else:
            st.markdown("_No history_")


def main() -> None:
    # Configure page for full-screen kanban
    st.set_page_config(
        page_title="AI Agent Board",
        layout="wide",
        initial_sidebar_state="collapsed",  # Hide sidebar by default
    )
    
    # Hide sidebar and set black background
    st.markdown("""
        <style>
        [data-testid="stSidebar"] {
            display: none;
        }
        .stApp {
            margin-top: 0rem;
            background-color: #000000 !important;
            min-height: 100vh;
        }
        .main .block-container {
            background-color: #000000 !important;
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 100%;
        }
        .stApp > header {
            background-color: #000000;
        }
        [data-testid="stHeader"] {
            background-color: #000000;
        }
        [data-testid="stToolbar"] {
            background-color: #000000;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # CRITICAL: Add postMessage listener in MAIN page context (before any iframes)
    # Streamlit's st.markdown() with unsafe_allow_html may not execute scripts
    # Use st.components.v1.html to inject a script that sets up listener in main window
    import streamlit.components.v1 as components
    
    # Create a script that runs in an iframe but injects listener into main window
    listener_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body>
        <script>
            // This script runs in an iframe, but we inject the listener into the main window
            try {
                if (window.top && window.top !== window) {
                    console.log('🔧 KANBAN: Injecting listener into main window from iframe');
                    
                    // Inject script into main window
                    const script = window.top.document.createElement('script');
                    script.textContent = `
                        (function() {
                            console.log('🔧 KANBAN: Listener script injected into main window');
                            
                            function handleKanbanMessage(event) {
                                console.log('📨 KANBAN: Listener received message');
                                console.log('📨 KANBAN: Event data:', event.data);
                                console.log('📨 KANBAN: Event origin:', event.origin);
                                
                                if (event.data && event.data.type === 'kanban_event') {
                                    console.log('✅ KANBAN: Processing kanban_event');
                                    const kanbanEvent = event.data.event;
                                    console.log('✅ KANBAN: Event details:', kanbanEvent);
                                    
                                    const params = new URLSearchParams(window.location.search);
                                    params.set('kanban_event', JSON.stringify(kanbanEvent));
                                    const newUrl = window.location.pathname + '?' + params.toString();
                                    console.log('🔄 KANBAN: Navigating to:', newUrl);
                                    window.location.href = newUrl;
                                } else {
                                    console.log('ℹ️ KANBAN: Ignoring message (not kanban_event)');
                                }
                            }
                            
                            // Add listener to main window
                            window.addEventListener('message', handleKanbanMessage, true);
                            window.addEventListener('message', handleKanbanMessage, false);
                            console.log('✅ KANBAN: Listeners added to main window');
                        })();
                    `;
                    window.top.document.head.appendChild(script);
                    console.log('✅ KANBAN: Script injected into main window');
                } else {
                    console.warn('⚠️ KANBAN: Cannot access window.top');
                }
            } catch (e) {
                console.error('❌ KANBAN: Error injecting listener:', e);
            }
        </script>
    </body>
    </html>
    """
    
    # Render the listener component (invisible, height 0)
    components.html(listener_html, height=0)
    
    logger.info("=== Main function called ===")
    logger.info(f"Session state keys: {list(st.session_state.keys())}")

    # Check if we're viewing a task details page
    if "viewing_task" in st.session_state:
        task_id = st.session_state["viewing_task"]
        # Find the task
        for path, task in iter_tasks():
            if task.get("id") == task_id:
                render_task_details_page(task_id, task, path)
                return
        # Task not found, clear and show board
        del st.session_state["viewing_task"]
        st.rerun()

    # Buttons at top
    button_col1, button_col2, button_col3 = st.columns([1, 1, 4])
    with button_col1:
        if st.button("➕ New Task", type="primary", use_container_width=True, key="new_task_btn"):
            st.session_state["show_new_task_modal"] = True
            st.rerun()
    with button_col2:
        if st.button("🔄 Refresh", use_container_width=True, key="refresh_btn"):
            st.session_state["last_task_mtime"] = 0
            st.rerun()
    with button_col3:
        st.write("")  # Spacer

    # Smart filesystem change detection - only check when not processing form submission
    # Initialize last check time
    if "last_check" not in st.session_state:
        st.session_state.last_check = time.time()
        st.session_state.last_file_hash = None
    
    # Only check for filesystem changes if we're not in the middle of form processing
    # This prevents interference with form submission
    form_processing = st.session_state.get("form_processing", False)
    
    if not form_processing:
        current_time = time.time()
        # Check every 3 seconds (less frequent to reduce interference)
        if current_time - st.session_state.last_check > 3.0:
            st.session_state.last_check = current_time
            
            # Check if task files have changed by comparing file modification times
            board_root = get_board_root()
            tasks_root = board_root / "tasks"
            
            if tasks_root.exists():
                # Get latest modification time of any task file
                latest_mtime = 0
                for task_file in tasks_root.rglob("*.yaml"):
                    if task_file.is_file():
                        mtime = task_file.stat().st_mtime
                        latest_mtime = max(latest_mtime, mtime)
                
                # Compare with last known modification time
                last_mtime = st.session_state.get("last_task_mtime", 0)
                
                if latest_mtime > last_mtime:
                    logger.info(f"Filesystem change detected (mtime: {latest_mtime} > {last_mtime})")
                    st.session_state["last_task_mtime"] = latest_mtime
                    # Only rerun if we're not in a form context
                    if not st.session_state.get("in_form_context", False):
                        st.rerun()

    board = load_board()
    agents = load_agents()
    columns = board.get("columns", [])
    col_ids = [c["id"] for c in columns]

    # New task form (modal-style, appears if button clicked)
    if st.session_state.get("show_new_task_modal", False):
        with st.expander("➕ Create New Task", expanded=True):
            with st.form("new_task_form", clear_on_submit=False):
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
                
                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("Create Task", type="primary", use_container_width=True)
                with col2:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        st.session_state["show_new_task_modal"] = False
                        st.rerun()
                
                if submitted:
                    if not title or not title.strip():
                        st.error("Title is required")
                    else:
                        try:
                            task_id = create_task(
                                title.strip(),
                                description.strip() if description else "",
                                column_id,
                                assignee_multiselect,
                                priority,
                                tag_str.strip() if tag_str else "",
                                due_date_str.strip() or None,
                            )
                            st.success(f"✅ Created task {task_id}")
                            st.session_state["show_new_task_modal"] = False
                            # Update last modification time
                            board_root = get_board_root()
                            tasks_root = board_root / "tasks" / column_id
                            task_file = tasks_root / f"{task_id}.yaml"
                            if task_file.exists():
                                st.session_state["last_task_mtime"] = task_file.stat().st_mtime
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error creating task: {e}")
                            logger.error(f"Error creating task: {e}", exc_info=True)

    # Load all tasks
    all_tasks = []
    task_path_map = {}  # Map task_id to (path, task) for quick lookup
    
    for path, task in iter_tasks():
        col = task.get("column")
        if col not in col_ids:
            continue
        all_tasks.append(task)
        task_path_map[task.get("id")] = (path, task)

    # Prepare columns for kanban component
    kanban_columns = []
    default_colors = {
        "backlog": "#95a5a6",
        "todo": "#3498db",
        "doing": "#f39c12",
        "blocked": "#e74c3c",
        "done": "#27ae60",
    }
    
    for col in columns:
        col_id = col.get("id", "")
        col_name = col.get("name", col_id)
        color = default_colors.get(col_id, "#3498db")
        kanban_columns.append({
            "id": col_id,
            "name": col_name,
            "color": color,
        })

    # Prepare tasks for kanban component
    kanban_tasks = []
    for task in all_tasks:
        task_col = task.get("column", "")
        task_id = task.get("id", "")
        task_title = task.get("title", "Untitled")
        
        # Log for debugging
        logger.debug(f"Preparing task: {task_id} - '{task_title}' in column '{task_col}'")
        
        kanban_tasks.append({
            "id": task_id,
            "title": task_title,
            "column": task_col,
            "priority": task.get("priority", "medium"),
            "tags": task.get("tags", []),
        })
    
    logger.info(f"Prepared {len(kanban_tasks)} tasks for kanban board")
    logger.info(f"Columns: {[c['id'] for c in kanban_columns]}")
    logger.info(f"Task columns: {[t['column'] for t in kanban_tasks]}")

    # Initialize session state for kanban events if not exists
    if "kanban_events" not in st.session_state:
        st.session_state["kanban_events"] = []
    
    # Check for kanban events from query parameters (set by JavaScript)
    query_params = st.query_params
    logger.debug(f"Checking query params: {dict(query_params)}")
    
    # Also check session state for events (set by postMessage handler)
    if "pending_kanban_event" in st.session_state:
        event = st.session_state["pending_kanban_event"]
        logger.info(f"🎯 Found pending kanban event in session state: {event}")
        del st.session_state["pending_kanban_event"]
        # Process it as if it came from query params
        query_params = {"kanban_event": [json.dumps(event)]}
    
    if "kanban_event" in query_params:
        logger.info(f"🎯 Found kanban_event in query params: {query_params['kanban_event']}")
        try:
            event = json.loads(query_params["kanban_event"])
            logger.info(f"📋 Parsed event: {event}")
            event_type = event.get("type")
            logger.info(f"📋 Event type: {event_type}")
            
            if event_type == "move":
                task_id = event.get("taskId")
                from_column = event.get("fromColumn")
                to_column = event.get("toColumn")
                
                logger.info(f"🔄 Move event - Task: {task_id}, From: {from_column}, To: {to_column}")
                logger.info(f"📋 Task path map keys: {list(task_path_map.keys())[:10]}...")  # Show first 10
                
                if task_id and task_id in task_path_map:
                    path, task = task_path_map[task_id]
                    logger.info(f"✅ Task found in map. Path: {path}")
                    logger.info(f"Drag-drop: Moving task {task_id} from {from_column} to {to_column}")
                    try:
                        move_task(task, path, to_column)
                        logger.info(f"✅ Successfully moved task {task_id} to {to_column}")
                        # Update last modification time
                        board_root = get_board_root()
                        # Check both tasks and issues directories
                        for dir_name in ["tasks", "issues"]:
                            tasks_root = board_root / dir_name / to_column
                            task_file = tasks_root / f"{task_id}.yaml"
                            if task_file.exists():
                                st.session_state["last_task_mtime"] = task_file.stat().st_mtime
                                logger.info(f"✅ Updated mtime from {task_file}")
                                break
                        # Clear query param and rerun
                        logger.info("🧹 Clearing query params and rerunning...")
                        st.query_params.clear()
                        st.rerun()
                    except Exception as e:
                        logger.error(f"❌ Error moving task: {e}", exc_info=True)
                        st.error(f"Error moving task: {e}")
                        st.query_params.clear()
                else:
                    logger.warning(f"⚠️ Task {task_id} not found in task_path_map")
                    logger.warning(f"  Available task IDs: {list(task_path_map.keys())[:10]}")
                    st.query_params.clear()
            
            elif event_type == "click":
                task_id = event.get("taskId")
                logger.info(f"🖱️ Click event - Task: {task_id}")
                if task_id and task_id in task_path_map:
                    logger.info(f"Task clicked: {task_id}")
                    st.query_params.clear()
                    st.session_state["viewing_task"] = task_id
                    st.rerun()
                else:
                    logger.warning(f"⚠️ Task {task_id} not found for click")
                    st.query_params.clear()
        except Exception as e:
            logger.error(f"❌ Error processing kanban event: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            st.query_params.clear()
    else:
        logger.debug("No kanban_event in query params")

    # Render native kanban board
    try:
        kanban_board(
            columns=kanban_columns,
            tasks=kanban_tasks,
            height=800,
            key="native_kanban_board",
        )
                    
    except Exception as e:
        logger.error(f"Error rendering kanban board: {e}", exc_info=True)
        st.error(f"Error rendering kanban board: {e}")
        import traceback
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()

