# Native Drag-and-Drop Implementation Plan

## Approach

Use Streamlit's `st.components.v1.html` with HTML5 drag-and-drop API to create a native Kanban board without external dependencies.

## Advantages

1. **No External Dependencies**: Pure HTML/CSS/JavaScript
2. **Full Control**: Complete control over styling and behavior
3. **Simple**: No complex React build process
4. **Maintainable**: Easy to understand and modify
5. **Native Browser API**: Uses standard HTML5 drag-and-drop

## Implementation Strategy

### 1. Create HTML Component
- Use `st.components.v1.html` to render Kanban board
- HTML5 drag-and-drop API for interactions
- CSS for styling (black background, modern look)
- JavaScript to handle drag events

### 2. Communication with Streamlit
- Use `st.components.v1.html` with `args` to pass data
- Use `key` parameter for state management
- Return move events via component value
- Handle moves in Python and update filesystem

### 3. Features to Implement
- ✅ Drag tasks between columns
- ✅ Visual feedback during drag
- ✅ Click tasks to view details
- ✅ Black background theme
- ✅ Full-height container
- ✅ New Task button
- ✅ Refresh button

### 4. Data Flow
```
Python → HTML (via args) → User drags → JavaScript event → 
Return value → Python handles move → Update filesystem → Rerun
```

## File Structure

```
crewkan/
├── crewkan_ui.py (modified)
└── kanban_native/
    └── kanban.html (HTML/CSS/JS component)
```

## Next Steps

1. Create HTML component with drag-and-drop
2. Integrate into crewkan_ui.py
3. Handle move events
4. Style with black background
5. Test drag-and-drop functionality

