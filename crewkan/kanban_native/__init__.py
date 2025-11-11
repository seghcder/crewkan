"""
Native Kanban Board Component for CrewKan

Uses HTML5 drag-and-drop API via Streamlit's HTML component.
No external dependencies, full control over styling and behavior.
"""

import streamlit.components.v1 as components
from pathlib import Path
import json

# Get the path to the HTML file
_component_dir = Path(__file__).parent
_html_path = _component_dir / "kanban.html"

# Read HTML content
with open(_html_path, 'r', encoding='utf-8') as f:
    _html_template = f.read()

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
    """
    
    # Inject data into HTML as embedded JSON
    # This is more reliable than trying to pass via args
    data_script = f"""
    <script>
        window.kanbanData = {json.dumps({
            "columns": columns,
            "tasks": tasks,
            "height": height
        })};
    </script>
    """
    
    # Insert data script before closing </head>
    html_content = _html_template.replace('</head>', data_script + '</head>')
    
    # Note: Initialization is handled in the main script block
    # The data script is injected before </head>, and the main script
    # will pick it up when it runs
    
    # Note: st.components.v1.html doesn't support return values directly
    # We'll use session state for communication instead
    # The HTML component will trigger reruns via JavaScript
    
    # Prepare data for HTML component
    # Note: components.html() doesn't support 'key' parameter
    components.html(
        html_content,
        height=height,
    )
    
    # Return None - events will be handled via session state
    return None

