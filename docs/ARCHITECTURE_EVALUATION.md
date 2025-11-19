# CrewKan Team Architecture Evaluation

## Current State Analysis

### Current Architecture
- **Orchestration**: LangGraph manages all agents in a single process
- **Workflow Logic**: Hardcoded in `run_crewkanteam.py`:
  - Priority-based task selection
  - Column transitions (backlog → todo → doing → done)
  - Follow-up task detection and reassignment
  - Supertool selection logic
  - File tracking and completion comments
- **Tools Available**: 
  - LangChain tools via `make_board_tools()` (board operations)
  - LangChain tools via `make_supertool_tools()` (supertools)
  - **No MCP server** for board operations (only LangChain tools exist)

### Current Issues
1. **Debugging Difficulty**: All agents run in one process, hard to isolate issues
2. **Tight Coupling**: Workflow logic is hardcoded, not flexible
3. **Single Point of Failure**: One process crash affects all agents
4. **Limited Observability**: Can't easily see individual agent activity
5. **Complex State Management**: LangGraph state adds overhead for simple file-based coordination

---

## Proposal 1: Independent Agent Processes

### Approach
Replace LangGraph orchestration with independent Python processes/threads. Each agent runs as a separate program that:
- Reads from the same board directory
- Uses `BoardClient` for operations
- Operates autonomously based on system prompt instructions

### Benefits ✅

1. **Better Debugging**
   - Each agent has its own process/logs
   - Can attach debugger to specific agent
   - See individual agent output clearly
   - Isolate failures to specific agents

2. **Simpler Architecture**
   - No LangGraph state management
   - No complex graph coordination
   - File-based coordination (already using filesystem)
   - Natural parallelism

3. **Scalability**
   - Can run agents on different machines
   - Easy to add/remove agents dynamically
   - No single process bottleneck
   - Can scale individual agents independently

4. **Fault Tolerance**
   - One agent crash doesn't affect others
   - Can restart individual agents
   - Natural isolation

5. **Development Experience**
   - Can test agents independently
   - Easier to develop new agents
   - Clear separation of concerns

### Implementation Options

#### Option A: Multiprocessing (Recommended)
```python
# Each agent runs in separate process
# Shared board directory for coordination
# Simple loop: check board → work → update board
```

**Pros:**
- True parallelism
- Process isolation
- Can run on different machines (shared filesystem)

**Cons:**
- More complex than threading
- Need to handle process lifecycle

#### Option B: Multithreading
```python
# Each agent runs in separate thread
# Shared board directory
```

**Pros:**
- Simpler than multiprocessing
- Shared memory (if needed)

**Cons:**
- GIL limits true parallelism in Python
- Less isolation than processes

#### Option C: Separate Python Programs (Best for Production)
```python
# Each agent is a standalone script
# Can be run independently or via supervisor
# Example: python -m crewkan.agent_runner --agent-id developer --board-root boards/crewkanteam
```

**Pros:**
- Maximum flexibility
- Can run anywhere (different machines, containers)
- Easy to deploy/manage individually
- Natural for production

**Cons:**
- Need process management (supervisor, systemd, etc.)

### Recommended: Option C (Separate Programs)
- Most flexible and production-ready
- Can still use multiprocessing for local testing
- Natural fit for containerized deployments

---

## Proposal 2: LLM-Driven Workflow (Reduce Coded Logic)

### Approach
Move workflow logic from code to LLM system prompt. Agent uses tools to:
- Get tasks (`list_my_issues`)
- Work on tasks (supertools)
- Update tasks (`move_issue`, `add_comment`)
- Reassign tasks (`reassign_issue`)
- Create follow-up tasks (`create_issue`)

### Benefits ✅

1. **Flexibility**
   - LLM can adapt to different workflows
   - No hardcoded assumptions
   - Can handle edge cases naturally

2. **Maintainability**
   - Less code to maintain
   - Changes via prompt updates, not code changes
   - Easier to experiment with workflows

3. **Natural Language Instructions**
   - Can describe complex workflows in prompts
   - Easier for non-developers to modify
   - More intuitive

4. **Agent Autonomy**
   - Agents make decisions based on context
   - Can handle unexpected situations
   - More intelligent behavior

### Current Tool Availability

**✅ Available as LangChain Tools:**
- `list_my_issues` - Get assigned tasks
- `move_issue` - Change task status
- `update_issue_field` - Update task fields
- `add_comment_to_issue` - Add comments
- `reassign_issue` - Reassign to other agents
- `create_issue` - Create new tasks
- `list_events` - Check notifications
- Supertool tools (cline, deep-research, etc.)

**❌ Missing:**
- MCP server for board operations (only LangChain tools exist)
- `get_issue_details` tool (exists in BoardClient but not exposed)

### Required Changes

1. **Expose Missing Tools**
   - Add `get_issue_details` to LangChain tools
   - Consider creating MCP server for board operations (optional, LangChain tools work fine)

2. **Create System Prompt Template**
   ```python
   SYSTEM_PROMPT = """
   You are {agent_id}, a {role} agent working on a CrewKan board.
   
   Your workspace: {workspace_path}
   Board location: {board_root}
   
   Workflow:
   1. Check for tasks assigned to you using list_my_issues
   2. Prioritize tasks in "doing" column first, then "todo"
   3. Move task to "doing" when starting work
   4. Use appropriate supertools to complete work
   5. Add comments to track progress
   6. Move to "done" when complete
   7. If task description mentions reassignment, use reassign_issue
   8. If follow-up tasks needed, create them with create_issue
   
   Available tools: {tool_descriptions}
   """
   ```

3. **Simplify Agent Loop**
   ```python
   async def agent_loop(agent_id: str, board_root: str):
       llm = get_llm(agent_id)
       tools = make_board_tools(board_root, agent_id) + make_supertool_tools(board_root, agent_id)
       agent = create_agent(llm, tools, system_prompt=get_system_prompt(agent_id, board_root))
       
       while True:
           # Simple loop: agent decides what to do
           result = await agent.ainvoke({"input": "What should I work on next?"})
           await asyncio.sleep(5)  # Brief pause between iterations
   ```

### Challenges ⚠️

1. **Reliability**
   - LLM might make mistakes
   - Need validation/error handling
   - May need some guardrails

2. **Consistency**
   - Different agents might behave differently
   - Need clear instructions
   - May need examples/few-shot prompts

3. **Performance**
   - LLM calls add latency
   - Need efficient prompting
   - Consider caching

4. **Cost**
   - More LLM calls
   - Need to optimize prompt size
   - Consider cheaper models for simple decisions

### Hybrid Approach (Recommended)
- **Core workflow**: LLM-driven (flexible)
- **Critical guardrails**: Code-based (reliable)
  - Validate column transitions
  - Ensure tasks aren't lost
  - Handle errors gracefully
  - Rate limiting

---

## Combined Architecture Proposal

### Recommended: Independent LLM-Driven Agents

```python
# Structure:
# crewkan/
#   agent_runner.py          # Standalone agent program
#   agent_framework/
#     llm_agent.py           # LLM agent with tools
#     system_prompts.py      # Prompt templates
#   board_langchain_tools.py # Board tools (already exists)
```

### Agent Runner (Standalone Program)
```python
# crewkan/agent_runner.py
async def main():
    agent_id = sys.argv[1]
    board_root = sys.argv[2]
    
    # Initialize LLM agent with tools
    agent = create_llm_agent(agent_id, board_root)
    
    # Simple loop
    while True:
        try:
            await agent.work_cycle()
            await asyncio.sleep(5)
        except KeyboardInterrupt:
            break
```

### LLM Agent
```python
# crewkan/agent_framework/llm_agent.py
class LLMAgent:
    def __init__(self, agent_id: str, board_root: str):
        self.agent_id = agent_id
        self.board_root = board_root
        self.llm = get_llm(agent_id)
        self.tools = self._load_tools()
        self.system_prompt = self._load_system_prompt()
        self.agent = create_agent(self.llm, self.tools, self.system_prompt)
    
    async def work_cycle(self):
        # Agent decides what to do based on board state
        result = await self.agent.ainvoke({
            "input": "Review your assigned tasks and work on the highest priority item."
        })
        return result
```

### System Prompt Template
```python
# crewkan/agent_framework/system_prompts.py
def get_agent_system_prompt(agent_id: str, board_root: str) -> str:
    agent_info = get_agent_info(board_root, agent_id)
    workspace_path = get_workspace_path(board_root, agent_id)
    
    return f"""
You are {agent_info['name']}, a {agent_info['role']} agent.

Your workspace: {workspace_path}
Board location: {board_root}

WORKFLOW:
1. Check assigned tasks: Use list_my_issues() to see your tasks
2. Prioritize: Work on tasks in "doing" first, then "todo"
3. Start work: Move task to "doing" with move_issue()
4. Do work: Use appropriate supertools (cline, deep-research, etc.)
5. Track progress: Add comments with add_comment_to_issue()
6. Complete: Move to "done" with move_issue()
7. Follow-ups: If task mentions reassignment, use reassign_issue()
8. New tasks: Create follow-up tasks with create_issue() if needed

AVAILABLE TOOLS:
{format_tool_descriptions(get_tools(board_root, agent_id))}

Be proactive, efficient, and communicate clearly through comments.
"""
```

---

## Migration Path

### Phase 1: Extract Agent Logic
1. Create `agent_runner.py` standalone program
2. Extract agent loop from `run_crewkanteam.py`
3. Test single agent independently

### Phase 2: Add LLM-Driven Workflow
1. Create system prompt template
2. Replace hardcoded logic with LLM calls
3. Keep critical guardrails in code

### Phase 3: Multi-Process Orchestration
1. Create supervisor script to run multiple agents
2. Test with all agents running independently
3. Remove LangGraph dependency

### Phase 4: Production Ready
1. Add process management (systemd, supervisor, etc.)
2. Add monitoring/logging
3. Add graceful shutdown
4. Documentation

---

## Evaluation Summary

### Proposal 1: Independent Processes ✅ **STRONGLY RECOMMENDED**
- **Feasibility**: High - board is already file-based
- **Benefits**: Significant (debugging, scalability, fault tolerance)
- **Effort**: Medium - need to refactor but straightforward
- **Risk**: Low - can test incrementally

### Proposal 2: LLM-Driven Workflow ✅ **RECOMMENDED**
- **Feasibility**: High - tools already exist
- **Benefits**: High (flexibility, maintainability)
- **Effort**: Medium - need prompt engineering
- **Risk**: Medium - need validation/guardrails

### Combined Approach ✅ **BEST OPTION**
- Independent processes + LLM-driven workflow
- Maximum flexibility and debuggability
- Natural fit for production
- Can implement incrementally

---

## Next Steps

1. **Create proof-of-concept**: Single agent runner with LLM-driven workflow
2. **Test independently**: Run one agent, verify it works correctly
3. **Add system prompts**: Move workflow logic to prompts
4. **Scale up**: Run multiple agents independently
5. **Remove LangGraph**: Once proven, remove old orchestration

