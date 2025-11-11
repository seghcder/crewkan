"""
Native Kanban Board Component for CrewKan

Bi-directional Streamlit component with HTML5 drag-and-drop API.
Uses components.declare_component() for proper event communication.
"""

import streamlit.components.v1 as components
from pathlib import Path
import os

# Determine if we're in development or production
# Default to production if build exists, otherwise dev mode
_build_dir = Path(__file__).parent / "frontend" / "build"
_has_build = _build_dir.exists() and (_build_dir / "index.js").exists()
_RELEASE = os.getenv("KANBAN_COMPONENT_RELEASE", "true" if _has_build else "false").lower() == "true"

# Get the path to the frontend directory
_component_dir = Path(__file__).parent
_frontend_dir = _component_dir / "frontend"

if not _RELEASE:
    # Development mode: use dev server
    _component_func = components.declare_component(
        "kanban_board",
        url="http://localhost:3001"
    )
else:
    # Production mode: use built files
    build_dir = _frontend_dir / "build"
    if not build_dir.exists():
        raise RuntimeError(
            f"Frontend build directory not found: {build_dir}\n"
            "Please run 'npm run build' in the frontend directory."
        )
    _component_func = components.declare_component(
        "kanban_board",
        path=str(build_dir)
    )

def kanban_board(columns, tasks, height=800, key=None):
    """
    Render a native Kanban board with drag-and-drop support.
    
    Parameters
    ----------
    columns : list of dict
        Column definitions. Each dict should have:
        - id: str - Column identifier
        - name: str - Display name
        - color: str - Hex color for column header (optional)
    
    tasks : list of dict
        Task definitions. Each dict should have:
        - id: str - Task identifier
        - title: str - Task title
        - column: str - Column ID where task belongs
        - priority: str - "high", "medium", or "low" (optional)
        - tags: list of str - Task tags (optional)
    
    height : int, default=800
        Height of the board in pixels
    
    key : str, optional
        Unique key for component state management
    
    Returns
    -------
    dict or None
        Component return value with:
        - type: "move" or "click"
        - taskId: Task ID
        - fromColumn: Source column (for moves)
        - toColumn: Target column (for moves)
        - timestamp: int - Event timestamp
    """
    
    # Call the component and return its value
    return _component_func(
        columns=columns,
        tasks=tasks,
        height=height,
        key=key
    )

