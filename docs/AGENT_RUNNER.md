# Agent Runner - Standalone Agent Execution

The new agent runner system allows each CrewKan agent to run independently, using LangChain agents with system prompts instead of hardcoded workflow logic.

## Architecture

### Key Components

1. **`crewkan/agent_runner.py`** - Standalone agent runner script
   - Each agent runs as an independent process
   - Uses LangChain AgentExecutor with board tools + supertools
   - Loads system prompts from agent YAML or generates defaults
   - Checks `.shutdown_requested` file for graceful shutdown

2. **`examples/run_crewkanteam_multiprocess.py`** - Multiprocessing coordinator
   - Launches multiple agent processes in parallel
   - Monitors process health
   - Coordinates graceful shutdown

3. **System Prompts** - LLM-driven workflow
   - Loaded from agent YAML `system_prompt` field
   - Supports relative paths (e.g., `../../prompts/developer.txt`)
   - Falls back to generated prompt based on agent role/skills

## Usage

### Running a Single Agent

```bash
python3 crewkan/agent_runner.py \
  --agent-id developer \
  --board-root boards/crewkanteam \
  --max-iterations 10 \
  --poll-interval 5.0
```

### Running Multiple Agents (Multiprocessing)

```bash
python3 examples/run_crewkanteam_multiprocess.py \
  --board-root boards/crewkanteam \
  --max-duration 3600 \
  --poll-interval 5.0
```

### Testing Setup

Before running agents, validate the setup:

```bash
python3 examples/test_agent_runner_setup.py \
  --board-root boards/crewkanteam \
  --agent-id developer
```

## Agent Configuration

### System Prompt in Agent YAML

Add a `system_prompt` field to your agent configuration:

```yaml
agents:
  - id: developer
    name: Core Developer
    role: Core Framework Developer
    kind: ai
    status: active
    system_prompt: "../../prompts/developer.txt"  # Relative path from board root
    # OR
    system_prompt: "You are a developer agent. Work on coding tasks..."  # Inline text
    supertools:
      allowed:
        - cline
```

### Default System Prompt

If no `system_prompt` is specified, a default prompt is generated based on:
- Agent name and role
- Agent skills
- Workspace paths
- Available supertools

## Workflow

The agent workflow is now LLM-driven:

1. **Check assigned tasks** - Agent uses `list_my_issues()` to see tasks
2. **Prioritize work** - LLM decides what to work on:
   - Complete tasks in "doing" first
   - Start tasks in "todo" 
   - Move tasks from "backlog" to "todo"
3. **Do work** - Agent uses appropriate tools:
   - Board tools for task management
   - Supertools (cline, deep-research, etc.) for specialized work
4. **Track progress** - Agent adds comments and updates tasks
5. **Complete** - Agent moves tasks to "done" when finished

## Tools Available

### Board Tools
- `list_my_issues` - List assigned issues
- `move_issue` - Move issues between columns
- `add_comment_to_issue` - Add progress comments
- `reassign_issue` - Reassign to other agents
- `create_issue` - Create new tasks
- `update_issue_field` - Update issue fields

### Supertools
- `cline` - Code generation and editing
- `deep-research` - Multi-step research
- `web-search` - Web search capabilities
- `browser-automation` - Browser control
- And more (see `crewkan/agent_framework/supertools/`)

## Graceful Shutdown

Agents check for a `.shutdown_requested` file in the board root:

```json
{
  "requested_at": 1234567890.0,
  "deadline": 1234567950.0,
  "grace_period": 60
}
```

When detected, agents finish current work and stop gracefully.

## Testing Supertools

Before running agents, validate supertools:

```bash
python3 crewkan/agent_framework/test_supertools_startup.py \
  --board-root boards/crewkanteam \
  --agent-id developer \
  --required-tools cline
```

## Differences from LangGraph Version

### Removed Hardcoded Logic
- ❌ Priority sorting (`get_priority_value`)
- ❌ Hardcoded workflow steps (backlog→todo→doing→done)
- ❌ Pattern matching for reassignment
- ❌ Supertool selection logic

### New LLM-Driven Approach
- ✅ System prompts guide agent behavior
- ✅ LLM decides workflow based on context
- ✅ Flexible task handling
- ✅ Better reasoning for complex cases

## Example: Running with Test Tasks

1. Create test tasks:
```python
from crewkan.board_core import BoardClient

client = BoardClient("boards/crewkanteam", "sean")
client.create_issue(
    title="Create README for agent_runner.py",
    description="Write documentation...",
    column="todo",
    assignees=["docs"],
    priority="medium"
)
```

2. Run the docs agent:
```bash
python3 crewkan/agent_runner.py \
  --agent-id docs \
  --board-root boards/crewkanteam \
  --max-iterations 5
```

3. Monitor progress:
```bash
# Check board activity log
tail -f boards/crewkanteam/board_activity.log

# Or check issues
python3 -c "
from crewkan.board_core import BoardClient
import json
client = BoardClient('boards/crewkanteam', 'docs')
tasks = json.loads(client.list_my_issues(column='doing'))
print(tasks)
"
```

## Troubleshooting

### Agent Not Processing Tasks
- Check agent status is "active"
- Verify agent has tasks assigned
- Check board activity log for errors
- Validate supertools if using them

### Import Errors
- Ensure dependencies are installed: `pip install -r requirements.txt`
- Check Python path includes project root
- Verify LangChain version compatibility

### LLM Errors
- Check Azure OpenAI credentials in environment
- Verify API endpoint and deployment name
- Check API rate limits

## Migration from LangGraph

The old `examples/run_crewkanteam.py` is deprecated but kept for reference. To migrate:

1. Update agent YAML with `system_prompt` if needed
2. Use `agent_runner.py` for single agents
3. Use `run_crewkanteam_multiprocess.py` for multiple agents
4. Remove hardcoded workflow logic (now handled by LLM)

