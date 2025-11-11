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

# Import kanban component - required
try:
    from streamlit_kanban_board_goviceversa import kanban_board
except ImportError:
    raise ImportError("streamlit-kanban-board-goviceversa is required. Install with: pip install streamlit-kanban-board-goviceversa")

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


def transform_columns_to_stages(columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Transform board columns to kanban component stages format."""
    # Default colors for columns (can be customized)
    default_colors = {
        "backlog": "#95a5a6",
        "todo": "#3498db",
        "doing": "#f39c12",
        "blocked": "#e74c3c",
        "done": "#27ae60",
    }
    
    stages = []
    for col in columns:
        col_id = col.get("id", "")
        col_name = col.get("name", col_id)
        # Use default color or generate one based on column name
        color = default_colors.get(col_id, "#3498db")
        stages.append({
            "id": col_id,
            "name": col_name,
            "color": color,
        })
    return stages


def transform_tasks_to_deals(tasks_by_column: Dict[str, List[Tuple[Path, Dict[str, Any]]]], stages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Transform tasks to kanban component deals format with permissions for drag-drop."""
    deals = []
    stage_ids = [s["id"] for s in stages]
    
    for col_id, task_list in tasks_by_column.items():
        for path, task in task_list:
            task_id = task.get("id", "")
            title = task.get("title", "Untitled Task")
            assignees = task.get("assignees", [])
            priority = task.get("priority", "medium")
            tags = task.get("tags", [])
            due_date = task.get("due_date", "")
            
            # Create complete dla_permissions structure to enable drag-drop
            # Component requires this exact structure - padlock appears if missing/incomplete
            stage_permissions = {}
            for stage_id in stage_ids:
                stage_permissions[stage_id] = {
                    "allowed": True,
                    "reason": "",
                    "warning": "",
                    "visual_hint": {
                        "color": "green",
                        "icon": None,
                        "text": "",
                    },
                }
            
            # Create deal object matching component's expected format
            # CRITICAL: All these fields must be present and correct for drag to work
            deal = {
                "id": task_id,
                "stage": col_id,
                "deal_id": task_id,  # Component expects deal_id field
                "company_name": title,  # Component expects company_name field
                "title": title,  # Keep original field for reference
                "assignees": ", ".join(assignees) if assignees else "",
                "priority": priority,
                "tags": ", ".join(tags) if tags else "",
                "due_date": due_date,
                # These fields control drag ability - both must be True
                "ready_to_be_moved": True,  # CRITICAL: Must be True
                "ic_review_completed": True,  # CRITICAL: Must be True to avoid padlock
                "_path": str(path),  # Store path for later use (internal field)
                "_task_data": task,  # Store full task data (internal field)
                # Complete DLA V2 permissions structure - required for drag to work
                # Padlock appears if this structure is missing or incomplete
                "dla_permissions": {
                    "deal_info": {
                        "currency": "USD",
                        "amount": 0,
                        "current_stage": col_id,
                        "deal_id": task_id,
                    },
                    "user_info": {
                        "username": "ui",
                        "role": "admin",  # Must be admin or have sufficient permissions
                        "role_level": "admin",
                        "authority_type": "unlimited",
                        "authority_amount": 999999999,
                        "ic_threshold": 0,
                    },
                    "stage_permissions": stage_permissions,  # All stages must have allowed=True
                    "summary": {
                        "can_touch_deal": True,  # CRITICAL: Must be True
                        "can_approve": True,
                        "can_reject": False,
                        "needs_ic_review": False,  # CRITICAL: Must be False
                        "blocked_reason": None,  # CRITICAL: Must be None
                    },
                    "ui_hints": {
                        "allowed_drop_zones": stage_ids,  # All stages allowed
                        "blocked_drop_zones": [],  # No blocked zones
                        "drag_enabled": True,  # CRITICAL: Must be True
                        "can_drag_from_current_stage": True,  # CRITICAL: Must be True
                    },
                },
            }
            
            # Debug: Log if permissions look wrong
            if not deal["dla_permissions"]["ui_hints"]["drag_enabled"]:
                logger.warning(f"Task {task_id} has drag_enabled=False")
            if deal["dla_permissions"]["summary"]["needs_ic_review"]:
                logger.warning(f"Task {task_id} needs_ic_review=True (will show padlock)")
            if not deal["ready_to_be_moved"]:
                logger.warning(f"Task {task_id} ready_to_be_moved=False (will show padlock)")
            deals.append(deal)
    return deals


def render_task_details_page(task_id: str, task_data: dict, path: Path) -> None:
    """Render a detailed task view page (Jira-style layout)."""
    board_root = get_board_root()
    agents = load_agents()
    agent_map = {a["id"]: a for a in agents}
    
    # Get comments directly from task history (don't use BoardClient which expects "issues" dir)
    comments = []
    for entry in task_data.get("history", []):
        if entry.get("event") == "comment":
            comments.append({
                "comment_id": entry.get("comment_id", ""),
                "at": entry.get("at", ""),
                "by": entry.get("by", ""),
                "details": entry.get("details", ""),
            })
    
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
                move_task(task_data, path, new_col)
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
                    assign_task(task_data, path, new_assignee)
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
                        import uuid
                        comment_id = f"C-{uuid.uuid4().hex[:8]}"
                        task_data["updated_at"] = now_iso()
                        comment_entry = {
                            "comment_id": comment_id,
                            "at": task_data["updated_at"],
                            "by": "ui",  # UI user
                            "event": "comment",
                            "details": new_comment.strip(),
                        }
                        task_data.setdefault("history", []).append(comment_entry)
                        save_yaml(path, task_data)
                        st.success(f"Comment added (ID: {comment_id})")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                        logger.error(f"Error adding comment: {e}", exc_info=True)
        
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
            background-color: #000000;
        }
        .main .block-container {
            background-color: #000000;
            padding-top: 1rem;
        }
        h1, h2, h3, h4, h5, h6, p, div, span {
            color: #ffffff;
        }
        </style>
    """, unsafe_allow_html=True)
    
    logger.info("=== Main function called ===")
    logger.info(f"Session state keys: {list(st.session_state.keys())}")

    # Check if we're viewing a task details page
    if "viewing_task" in st.session_state:
        task_id = st.session_state["viewing_task"]
        # Find the task - search all tasks
        task_found = False
        for path, task in iter_tasks():
            if task.get("id") == task_id:
                render_task_details_page(task_id, task, path)
                task_found = True
                return
        # Task not found, clear and show board
        if not task_found:
            logger.warning(f"Task {task_id} not found, clearing viewing_task")
            if "viewing_task" in st.session_state:
                del st.session_state["viewing_task"]
            st.error(f"Task {task_id} not found")
            st.rerun()

    # Smart filesystem change detection
    if "last_check" not in st.session_state:
        st.session_state.last_check = time.time()
        st.session_state.last_file_hash = None
    
    current_time = time.time()
    # Check every 3 seconds
    if current_time - st.session_state.last_check > 3.0:
        st.session_state.last_check = current_time
        
        board_root = get_board_root()
        tasks_root = board_root / "tasks"
        
        if tasks_root.exists():
            latest_mtime = 0
            for task_file in tasks_root.rglob("*.yaml"):
                if task_file.is_file():
                    mtime = task_file.stat().st_mtime
                    latest_mtime = max(latest_mtime, mtime)
            
            last_mtime = st.session_state.get("last_task_mtime", 0)
            
            if latest_mtime > last_mtime:
                logger.info(f"Filesystem change detected (mtime: {latest_mtime} > {last_mtime})")
                st.session_state["last_task_mtime"] = latest_mtime
                st.rerun()

    board = load_board()
    agents = load_agents()
    columns = board.get("columns", [])
    col_ids = [c["id"] for c in columns]

    # Load all tasks (no filtering for now - can add filters later)
    tasks_by_column = {cid: [] for cid in col_ids}
    for path, task in iter_tasks():
        col = task.get("column")
        if col not in tasks_by_column:
            continue
        tasks_by_column[col].append((path, task))

    # Transform data for kanban component
    stages = transform_columns_to_stages(columns)
    deals = transform_tasks_to_deals(tasks_by_column, stages)
    
    # Create a mapping from deal_id to (path, task) for quick lookup
    deal_to_task_map = {}
    for col_id, task_list in tasks_by_column.items():
        for path, task in task_list:
            deal_to_task_map[task.get("id", "")] = (path, task)
    
    # Render kanban board natively - no custom containers
    # The component will render its own UI including filters and controls
    try:
        # Provide user_info to component for permissions
        user_info = {
            "username": "ui",
            "role": "admin",
            "email": "ui@crewkan.local",
        }
        
        # Call component directly - let it render natively with its own UI
        result = kanban_board(
            stages=stages,
            deals=deals,
            key="crewkan_board",
            height=800,
            allow_empty_stages=True,
            show_tooltips=True,
            user_info=user_info,
        )
        
        # Add buttons after component renders (using Streamlit's native layout)
        # These will appear below the kanban board
        button_col1, button_col2 = st.columns(2)
        with button_col1:
            if st.button("➕ New Task", type="primary", use_container_width=True, key="new_task_btn"):
                st.session_state["show_new_task_modal"] = True
        with button_col2:
            if st.button("🔄 Refresh", use_container_width=True, key="refresh_btn"):
                st.session_state["last_task_mtime"] = 0
                st.rerun()
        
        # New task form (appears below buttons if modal is open)
        if st.session_state.get("show_new_task_modal", False):
            with st.expander("➕ Create New Task", expanded=True):
                with st.form("new_task_form", clear_on_submit=False):
                    title = st.text_input("Title *", key="modal_task_title")
                    description = st.text_area("Description", height=100, key="modal_task_desc")
                    column_id = st.selectbox("Column", col_ids, key="modal_task_column")
                    priority = st.selectbox("Priority", ["low", "medium", "high"], index=1, key="modal_task_priority")
                    tag_str = st.text_input("Tags (comma separated)", key="modal_task_tags")
                    assignee_multiselect = st.multiselect(
                        "Assignees",
                        [a["id"] for a in agents] if agents else [],
                        key="modal_task_assignees",
                    )
                    due_date_str = st.text_input("Due date (optional text)", value="", key="modal_task_due")
                    
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
        
        # Handle drag-and-drop: task moved to different column
        if result and result.get("moved_deal"):
            moved = result["moved_deal"]
            deal_id = moved.get("deal_id") or moved.get("id")
            from_stage = moved.get("from_stage")
            to_stage = moved.get("to_stage")
            
            if deal_id and deal_id in deal_to_task_map:
                path, task = deal_to_task_map[deal_id]
                current_col = task.get("column", task.get("status"))
                
                # Only move if actually changed
                if to_stage and to_stage != current_col:
                    logger.info(f"Drag-drop: Moving task {deal_id} from {current_col} to {to_stage}")
                    try:
                        move_task(task, path, to_stage)
                        st.success(f"Moved task to {to_stage}")
                        # Update last modification time to prevent immediate refresh
                        board_root = get_board_root()
                        tasks_root = board_root / "tasks" / to_stage
                        task_file = tasks_root / f"{deal_id}.yaml"
                        if task_file.exists():
                            st.session_state["last_task_mtime"] = task_file.stat().st_mtime
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Error moving task via drag-drop: {e}", exc_info=True)
                        st.error(f"Error moving task: {e}")
        
        # Handle click: show task details
        if result and result.get("clicked_deal"):
            clicked = result["clicked_deal"]
            deal_id = clicked.get("deal_id") or clicked.get("id")
            
            if deal_id and deal_id in deal_to_task_map:
                path, task = deal_to_task_map[deal_id]
                logger.info(f"Task clicked: {deal_id}")
                st.session_state["viewing_task"] = deal_id
                st.rerun()
            else:
                logger.warning(f"Clicked deal {deal_id} not found in deal_to_task_map")
                st.warning(f"Task {deal_id} not found")
                    
    except Exception as e:
        logger.error(f"Error rendering kanban board: {e}", exc_info=True)
        st.error(f"Error rendering kanban board: {e}")
        import traceback
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
