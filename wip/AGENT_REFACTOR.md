# Agent Refactor Summary

## Overview

Refactored CrewKan team from LangGraph orchestration to independent agent processes. Each agent now runs as a standalone LangChain agent with system prompts, using board tools and supertools to process tasks autonomously.

## What Was Done

### Core Changes

1. **Replaced LangGraph with Independent Agents**
   - Removed LangGraph state graph orchestration
   - Created standalone agent runner (`crewkan/agent_runner.py`)
   - Each agent runs independently in its own process

2. **LLM-Driven Workflow**
   - Removed hardcoded workflow logic:
     - Priority sorting (`get_priority_value`)
     - Hardcoded workflow steps (backlog→todo→doing→done)
     - Pattern matching for reassignment
     - Supertool selection logic
   - Replaced with system prompts that guide LLM behavior
   - Agents decide workflow based on context

3. **Agent-Specific Logging**
   - Each agent logs to its own workspace directory
   - Log files: `workspaces/{agent_id}/{agent_id}.log`
   - Uses native Python logging with file and console handlers

4. **System Prompt Support**
   - Added `system_prompt` field to agent schema
   - Supports inline text or file paths (relative to board root)
   - Falls back to generated prompt based on agent role/skills

5. **Multiprocessing Coordinator**
   - Created `examples/run_crewkanteam_multiprocess.py`
   - Launches multiple agent processes in parallel
   - Monitors process health
   - Coordinates graceful shutdown

### New Files Created

- `crewkan/agent_runner.py` - Standalone agent runner
- `crewkan/agent_framework/logging_utils.py` - Agent logging utilities
- `crewkan/agent_framework/test_supertools_startup.py` - Supertool testing
- `examples/run_crewkanteam_multiprocess.py` - Multiprocess coordinator
- `examples/test_agent_runner_setup.py` - Setup validation
- `examples/monitor_agent_progress.py` - Progress monitoring
- `examples/test_agent_logging.py` - Logging tests
- `docs/AGENT_RUNNER.md` - Comprehensive documentation

### Modified Files

- `crewkan/schemas/agents_schema.yaml` - Added `system_prompt` field
- `crewkan/board_core.py` - Added `get_agent_system_prompt()` method
- `tests/test_supertools.py` - Enhanced test coverage
- `examples/run_crewkanteam.py` - Added deprecation notice

## How to Run

### Prerequisites

1. **Activate Virtual Environment**
   ```bash
   source venv/bin/activate
   ```

2. **Set Environment Variables**
   ```bash
   export AZURE_OPENAI_API_KEY=your_key
   export AZURE_OPENAI_ENDPOINT=your_endpoint
   export AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment
   export AZURE_OPENAI_API_VERSION=2024-02-15-preview  # optional
   ```

### Running a Single Agent Independently

Run one agent in standalone mode:

```bash
python3 crewkan/agent_runner.py \
  --agent-id docs \
  --board-root boards/crewkanteam \
  --max-iterations 10 \
  --poll-interval 5.0
```

**Arguments:**
- `--agent-id`: Agent ID to run (e.g., `docs`, `developer`, `tester`)
- `--board-root`: Board root directory
- `--max-iterations`: Maximum number of cycles (optional, default: unlimited)
- `--poll-interval`: Seconds between cycles (default: 5.0)

**What Happens:**
1. Agent loads configuration from board
2. Sets up logging to `workspaces/{agent_id}/{agent_id}.log`
3. Creates LangChain agent with board tools + supertools
4. Loads system prompt (from YAML or generates default)
5. Runs cycles: checks tasks, works on them, updates board
6. Checks `.shutdown_requested` file for graceful shutdown

### Running Multiple Agents (Multiprocess)

Run all active AI agents in parallel:

```bash
python3 examples/run_crewkanteam_multiprocess.py \
  --board-root boards/crewkanteam \
  --max-duration 3600 \
  --poll-interval 5.0
```

**Arguments:**
- `--board-root`: Board root directory
- `--max-duration`: Maximum duration in seconds (optional)
- `--poll-interval`: Seconds between agent cycles (default: 5.0)

**What Happens:**
1. Discovers all active AI agents on board
2. Launches each agent in separate process
3. Monitors process health
4. Prints status updates periodically
5. Coordinates graceful shutdown across all agents

### Monitoring Agent Progress

Monitor multiple agents in real-time:

```bash
python3 examples/monitor_agent_progress.py \
  --board-root boards/crewkanteam \
  --agents docs developer tester \
  --interval 5
```

**Arguments:**
- `--board-root`: Board root directory
- `--agents`: List of agent IDs to monitor
- `--interval`: Update interval in seconds (default: 5)

**Shows:**
- Board status (tasks by column)
- Per-agent task counts
- Recent log entries from each agent

### Testing Setup

Validate agent setup before running:

```bash
python3 examples/test_agent_runner_setup.py \
  --board-root boards/crewkanteam \
  --agent-id docs
```

Tests:
- BoardClient initialization
- System prompt loading
- Board tools creation
- Supertools availability
- Workspace access
- Task access

### Testing Supertools

Validate supertools before agent execution:

```bash
python3 crewkan/agent_framework/test_supertools_startup.py \
  --board-root boards/crewkanteam \
  --agent-id developer \
  --required-tools cline
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

## Architecture

### Agent Workflow (LLM-Driven)

1. **Check assigned tasks** - Agent uses `list_my_issues()` tool
2. **Prioritize work** - LLM decides:
   - Complete tasks in "doing" first
   - Start tasks in "todo"
   - Move tasks from "backlog" to "todo"
3. **Do work** - Agent uses:
   - Board tools for task management
   - Supertools (cline, deep-research, etc.) for specialized work
4. **Track progress** - Agent adds comments and updates tasks
5. **Complete** - Agent moves tasks to "done"

### Logging

Each agent logs to its workspace directory:
- File: `workspaces/{agent_id}/{agent_id}.log`
- Format: Timestamped with agent name, level, and message
- Both file and console output

### Graceful Shutdown

Agents check for `.shutdown_requested` file in board root:
```json
{
  "requested_at": 1234567890.0,
  "deadline": 1234567950.0,
  "grace_period": 60
}
```

When detected, agents finish current work and stop gracefully.

## Work In Progress

### Known Issues

1. **Supertool Async Execution**
   - Supertool tools return coroutine objects instead of executing
   - Need to wrap async supertool functions properly for LangChain
   - Currently agents can use supertools but may see coroutine objects in responses

2. **LangChain 1.0 API Migration**
   - Using `create_agent()` from LangChain 1.0
   - Some API differences from older versions
   - May need adjustments for tool execution patterns

3. **Error Handling**
   - Basic error handling in place
   - Could be more robust for LLM errors, tool failures, network issues
   - Need better retry logic

### Improvements Needed

1. **Supertool Integration**
   - Fix async supertool execution
   - Ensure supertools execute properly when called by agents
   - Add better error handling for supertool failures

2. **System Prompt Templates**
   - Create example system prompt files for different agent types
   - Document best practices for writing system prompts
   - Add prompt validation

3. **Monitoring & Observability**
   - Add metrics collection (tasks processed, time per task, etc.)
   - Better visualization of agent activity
   - Alerting for agent failures

4. **Testing**
   - Add integration tests for agent workflow
   - Test with actual LLM calls (mocked or real)
   - Test multiprocess coordination

5. **Documentation**
   - Add more examples of system prompts
   - Document troubleshooting common issues
   - Add migration guide from LangGraph version

## Remaining Tasks

### High Priority

- [ ] Fix async supertool execution (wrap coroutines properly)
- [ ] Add retry logic for LLM and tool failures
- [ ] Create example system prompt files
- [ ] Add integration tests

### Medium Priority

- [ ] Improve error messages and logging
- [ ] Add metrics and observability
- [ ] Optimize agent cycle performance
- [ ] Add agent health checks

### Low Priority

- [ ] Add agent configuration validation
- [ ] Create system prompt templates library
- [ ] Add agent performance profiling
- [ ] Document migration from LangGraph

## Testing Status

### Verified Working

✅ Single agent execution
✅ Multiprocess coordinator
✅ Agent-specific logging
✅ System prompt loading
✅ Board tools integration
✅ Task processing workflow
✅ Graceful shutdown

### Needs Testing

⚠️ Supertool execution (async issue)
⚠️ Long-running agent sessions
⚠️ Error recovery
⚠️ Concurrent agent coordination
⚠️ Performance under load

## Migration Notes

### From LangGraph Version

The old `examples/run_crewkanteam.py` is deprecated but kept for reference.

**Key Differences:**
- No state graph - agents run independently
- No hardcoded workflow - LLM decides based on prompts
- No shared state - board files provide coordination
- Simpler architecture - easier to debug and maintain

**Migration Steps:**
1. Update agent YAML with `system_prompt` if needed
2. Use `agent_runner.py` for single agents
3. Use `run_crewkanteam_multiprocess.py` for multiple agents
4. Monitor agent logs in workspace directories

## Examples

### Example: Running Docs Agent

```bash
# Activate venv
source venv/bin/activate

# Run docs agent for 5 iterations
python3 crewkan/agent_runner.py \
  --agent-id docs \
  --board-root boards/crewkanteam \
  --max-iterations 5 \
  --poll-interval 3

# Check logs
tail -f boards/crewkanteam/workspaces/docs/docs.log
```

### Example: Running All Agents

```bash
# Run all agents for 1 hour
python3 examples/run_crewkanteam_multiprocess.py \
  --board-root boards/crewkanteam \
  --max-duration 3600 \
  --poll-interval 5

# Monitor in another terminal
python3 examples/monitor_agent_progress.py \
  --board-root boards/crewkanteam \
  --agents docs developer tester \
  --interval 10
```

### Example: Custom System Prompt

Create `boards/crewkanteam/prompts/developer.txt`:
```
You are a skilled developer agent specializing in Python and system architecture.

Your workflow:
1. Always check "doing" tasks first
2. Review code before making changes
3. Write tests for new features
4. Document your work clearly

Use cline supertool for code generation and refactoring.
```

Update agent YAML:
```yaml
- id: developer
  system_prompt: "prompts/developer.txt"
```

## Troubleshooting

### Agent Not Processing Tasks

- Check agent status is "active" in agents.yaml
- Verify agent has tasks assigned
- Check agent log file for errors
- Validate supertools if using them

### Import Errors

- Ensure venv is activated: `source venv/bin/activate`
- Check dependencies: `pip install -r requirements.txt`
- Verify Python path includes project root

### LLM Errors

- Check Azure OpenAI credentials
- Verify API endpoint and deployment name
- Check API rate limits
- Review error messages in agent log

### Supertool Issues

- Validate supertools: `test_supertools_startup.py`
- Check agent permissions in agents.yaml
- Verify credentials are configured
- Review supertool logs

## Next Steps

1. Fix async supertool execution
2. Add comprehensive integration tests
3. Create system prompt examples
4. Improve error handling and recovery
5. Add monitoring and metrics

## References

- `docs/AGENT_RUNNER.md` - Detailed agent runner documentation
- `REFACTOR_SUMMARY.md` - Implementation summary
- `TESTING_SUMMARY.md` - Testing documentation
- `examples/` - Example scripts and tests

