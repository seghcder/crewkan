# CrewKan Event System

## Overview

CrewKan includes a file-based event system for agent notifications. This allows agents to be notified of task completions, assignments, and other events without relying on any specific orchestration framework (like LangGraph).

## Design Principles

1. **Framework Agnostic**: Works with LangGraph, LangChain, or any other system
2. **File-Based**: Uses YAML files in `events/<agent_id>/` directories
3. **Simple**: Easy to understand and debug
4. **Reliable**: Filesystem is the source of truth

## Event Structure

Events are stored as YAML files in `events/<agent_id>/<event_id>.yaml`:

```yaml
id: EVT-123
type: task_completed
created_at: "2025-01-01T12:00:00Z"
created_by: worker1
notify_agent: ceo
status: pending  # pending, read, archived
data:
  task_id: T-456
  task_title: "Research market trends"
  task_description: "..."
  completed_by: worker1
  completion_notes: "Research completed successfully"
  completed_at: "2025-01-01T12:00:00Z"
```

## Event Types

- `task_completed`: Task moved to "done" column
- `task_assigned`: Task assigned to an agent (future)
- `task_updated`: Task fields updated (future)
- `task_blocked`: Task moved to "blocked" (future)

## Usage

### Creating Events

Events are automatically created when tasks are moved to "done":

```python
from crewkan.board_core import BoardClient

client = BoardClient(board_root, "worker1")
client.move_task("T-123", "done")  # Automatically creates completion event
```

### Checking for Events

```python
from crewkan.board_events import list_pending_events

events = list_pending_events(board_root, "ceo")
for event in events:
    print(f"Task {event['data']['task_id']} completed by {event['data']['completed_by']}")
```

### Marking Events as Read

```python
from crewkan.board_events import mark_event_read

mark_event_read(board_root, "ceo", "EVT-123")
```

### Using with LangChain Tools

```python
from crewkan.board_langchain_tools import make_event_tools

event_tools = make_event_tools(board_root, "ceo")
# Add to agent's tool list
```

## Task Requestor Tracking

When a task is created, the `requested_by` field tracks who should be notified:

```python
client.create_task(
    title="Research market trends",
    assignees=["worker1"],
    requested_by="ceo"  # CEO will be notified when task is done
)
```

When the task is moved to "done", an event is automatically created for the `requested_by` agent.

## Integration with LangGraph

See `examples/langgraph_ceo_delegation.py` for a complete example of:
- CEO creating and delegating tasks
- Workers processing tasks in parallel
- CEO receiving completion notifications

## Directory Structure

```
board_root/
├── board.yaml
├── agents/
├── tasks/
├── events/
│   ├── ceo/
│   │   ├── EVT-123.yaml
│   │   └── EVT-124.yaml
│   ├── worker1/
│   │   └── EVT-125.yaml
│   └── worker2/
│       └── EVT-126.yaml
└── workspaces/
```

## Future Enhancements

- Event filtering and search
- Event expiration/cleanup
- Event priorities
- Event batching
- Webhook notifications (optional)

