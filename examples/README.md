# CrewKan Examples

## LangGraph CEO Delegation

`langgraph_ceo_delegation.py` demonstrates:

1. **CEO Agent**: Creates tasks and delegates them to workers
2. **Worker Agents**: Process tasks in parallel (worker1, worker2, worker3)
3. **Event System**: CEO receives notifications when tasks are completed

### How It Works

1. CEO creates tasks with `requested_by="ceo"` field
2. Tasks are assigned to workers
3. Workers process tasks and move them to "done"
4. When a task is moved to "done", an event is automatically created in `events/ceo/`
5. CEO checks for events using `list_events` tool

### Running the Example

```bash
# Set up OpenAI API key
export OPENAI_API_KEY=your-key-here

# Run the example
python examples/langgraph_ceo_delegation.py
```

### Key Features Demonstrated

- **Task Delegation**: CEO creates tasks and assigns to workers
- **Parallel Processing**: Multiple workers process tasks simultaneously
- **Event Notifications**: File-based event system for completion notifications
- **Framework Agnostic**: Events work with any orchestration system

### Event System

The event system is file-based and framework-agnostic:

- Events stored in `events/<agent_id>/<event_id>.yaml`
- Automatically created when tasks move to "done"
- Agents can check for events using `list_events` tool
- Events can be marked as read or archived

See `docs/EVENT_SYSTEM.md` for full documentation.

