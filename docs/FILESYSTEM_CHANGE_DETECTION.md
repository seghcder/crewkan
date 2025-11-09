# Filesystem Change Detection in CrewKan UI

## Problem

We need to detect when backend agents create/update tasks so the UI can refresh automatically, but this must not interfere with form submission.

## Solution

### Smart Change Detection

Instead of aggressive polling that calls `st.rerun()` every 2 seconds, we use:

1. **Modification Time (mtime) Comparison**
   - Check the latest modification time of all task files
   - Compare with last known modification time
   - Only trigger refresh if files actually changed

2. **Form Processing Protection**
   - Set `form_processing` flag when form is submitted
   - Set `in_form_context` flag when form is visible
   - Skip auto-refresh checks when these flags are set

3. **Less Frequent Polling**
   - Check every 3 seconds (instead of 2)
   - Only check when not processing forms
   - Update mtime after successful task creation to prevent immediate refresh

4. **Manual Refresh Button**
   - Users can manually refresh when needed
   - Always available, doesn't interfere with forms

## Implementation

```python
# Only check if not processing form
form_processing = st.session_state.get("form_processing", False)

if not form_processing:
    # Check every 3 seconds
    if current_time - st.session_state.last_check > 3.0:
        # Get latest mtime of all task files
        latest_mtime = max(task_file.stat().st_mtime for task_file in tasks)
        
        # Compare with last known
        if latest_mtime > st.session_state.get("last_task_mtime", 0):
            # Only rerun if not in form context
            if not st.session_state.get("in_form_context", False):
                st.rerun()
```

## Streamlit File Watcher Configuration

Streamlit has its own file watcher (watchdog/inotify) that monitors Python files for changes. This is separate from our board file monitoring.

### Configuration Options

You can configure Streamlit's file watcher in `~/.streamlit/config.toml`:

```toml
[server]
fileWatcherType = "auto"  # Options: auto, watchdog, poll, none
```

- `auto`: Use watchdog if available, fall back to polling
- `watchdog`: Force use of watchdog module
- `poll`: Use polling (slower but more reliable)
- `none`: Disable file watching entirely

### For Production

In production, you might want to disable Streamlit's file watcher:

```toml
[server]
fileWatcherType = "none"
```

This prevents Streamlit from watching Python files for changes (which we don't need in production).

## Alternative Approaches

### 1. **WebSocket/SSE (Server-Sent Events)**
- More real-time updates
- Requires additional infrastructure
- Overkill for filesystem-based board

### 2. **Watchdog Library**
- Could use Python's `watchdog` library directly
- More efficient than polling
- Requires additional dependency
- More complex to implement

### 3. **Streamlit's Experimental Features**
- `st.experimental_rerun()` (deprecated)
- `st.rerun()` (current)
- Auto-refresh via `@st.cache` invalidation

## Current Approach Benefits

✅ **Simple**: Uses built-in Python `stat()` calls
✅ **Non-intrusive**: Doesn't interfere with form submission
✅ **Efficient**: Only checks mtime, not file contents
✅ **Reliable**: Works even if watchdog has issues
✅ **User Control**: Manual refresh button always available

## Future Improvements

1. **Configurable Polling Interval**: Make the 3-second interval configurable
2. **Watchdog Integration**: Use watchdog for more efficient monitoring
3. **WebSocket Updates**: Real-time updates for multi-user scenarios
4. **Debouncing**: Prevent multiple rapid refreshes

## Testing

The filesystem change detection is tested in:
- `tests/test_streamlit_extended.py::test_filesystem_change_detection`
- `tests/test_streamlit_ui_comprehensive.py::test_filesystem_change_detection`

These tests verify that:
- Backend-created tasks appear in UI
- UI refreshes when filesystem changes
- Form submission is not interrupted

