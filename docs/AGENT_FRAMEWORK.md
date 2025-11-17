# Agent Framework - Supertool Integration

## Overview

The Agent Framework allows CrewKan agents to use powerful tools (supertools) while maintaining clear separation of concerns: supertools execute tasks, agents coordinate and update the board.

## Architecture

### Core Components

1. **Supertool**: Abstract base class for all supertools
2. **SupertoolRegistry**: Central registry for tool registration and discovery
3. **SupertoolExecutor**: Validates permissions, manages execution, enforces constraints
4. **AgentWorkspace**: Provides isolated execution environments per agent
5. **CredentialManager**: Handles secure credential storage and injection

### Design Principles

- **Separation of Concerns**: Supertools execute, agents coordinate
- **Extensibility**: Easy to add new supertools via decorator
- **Security**: Permission-based access, credential isolation
- **Maintainability**: Clear interfaces, comprehensive logging
- **Agent Autonomy**: LLM-driven tool selection within constraints
- **Workspace Isolation**: Each agent has isolated execution environment

## Creating a Supertool

### Basic Example

```python
from crewkan.agent_framework import Supertool, SupertoolContext, SupertoolResult
from crewkan.agent_framework.registry import register_supertool

@register_supertool("my-tool")
class MySupertool(Supertool):
    def __init__(self):
        super().__init__(
            tool_id="my-tool",
            name="My Tool",
            description="Does something useful",
        )
    
    def get_required_credentials(self) -> list[str]:
        return ["api_key"]  # List required credential keys
    
    async def execute(self, context: SupertoolContext) -> SupertoolResult:
        # Access credentials
        api_key = context.credentials.get("api_key")
        
        # Access workspace
        workspace_path = context.workspace_path
        
        # Access issue details if working on an issue
        issue_details = context.issue_details
        
        # Execute your tool logic
        # ...
        
        # Return result
        return SupertoolResult(
            success=True,
            output="Task completed successfully",
            data={"result": "some data"},
        )
```

### Supertool Context

The `SupertoolContext` provides:

- `workspace_path`: Isolated workspace directory for this execution
- `agent_id`: ID of the agent executing the tool
- `issue_id`: Optional issue ID being worked on
- `issue_details`: Full issue details if available
- `credentials`: Dictionary of available credentials
- `constraints`: Execution constraints (timeouts, resource limits, etc.)
- `board_root`: Board root directory (for reference only)
- `metadata`: Additional context from agent

### Supertool Result

Return a `SupertoolResult` with:

- `success`: Boolean indicating success/failure
- `output`: Main output string
- `data`: Optional structured data dictionary
- `artifacts`: Optional list of file paths created
- `error`: Error message if failed
- `metadata`: Additional metadata
- `execution_time`: Execution time in seconds

## Agent Configuration

### Adding Supertools to Agents

Edit `agents/agents.yaml`:

```yaml
agents:
  - id: my-agent
    name: My Agent
    role: Developer
    kind: ai
    status: active
    supertools:
      allowed:
        - cline
        - web-search
        - browser-automation
      constraints:
        max_execution_time: 1800  # 30 minutes
        allowed_domains:
          - example.com
          - api.example.com
```

### Credential Management

Credentials are stored per-agent in `credentials/{agent_id}.yaml`:

```yaml
api_key: "secret-key"
supertools:
  cline:
    # Tool-specific credentials
  web-search:
    search_api_key: "search-key"
```

## Using Supertools in Agents

### Direct Execution

```python
from crewkan.agent_framework import SupertoolExecutor

executor = SupertoolExecutor(board_root, agent_id)

# Execute a supertool
result = await executor.execute(
    tool_id="cline",
    issue_id="I-123",
    additional_context={
        "prompt": "Fix the bug in main.py",
    }
)

if result.success:
    print(result.output)
else:
    print(f"Error: {result.error}")
```

### LangChain Integration

```python
from crewkan.agent_framework.langchain_tools import make_supertool_tools

# Get LangChain tools for available supertools
tools = make_supertool_tools(board_root, agent_id)

# Use with LangChain agent
from langchain.agents import create_agent
agent = create_agent(llm, tools, ...)
```

## Example Supertools

### Coding Tools

- **ClineSupertool** (`cline`): CLI-based coding assistant
- **ContinueSupertool** (`continue`): Continue.dev integration

### Research Tools

- **DeepResearchSupertool** (`deep-research`): Multi-step research with reasoning
- **WebSearchSupertool** (`web-search`): Web search capabilities

### Automation Tools

- **BrowserAutomationSupertool** (`browser-automation`): Browser control (Playwright/Selenium)
- **TaskLineSupertool** (`taskline`): Task automation framework

### MCP Integration

- **MCPServerSupertool** (`mcp-server`): Generic MCP server integration

## Security Considerations

1. **Permission-Based Access**: Agents can only use supertools they're explicitly granted
2. **Credential Isolation**: Credentials are stored per-agent and injected securely
3. **Workspace Isolation**: Each execution runs in an isolated workspace
4. **Constraint Enforcement**: Timeouts and resource limits are enforced
5. **Domain Restrictions**: Web-based tools can be restricted to specific domains

## Best Practices

1. **Tool Selection**: Let agents choose tools based on task context
2. **Error Handling**: Always handle errors gracefully and return meaningful messages
3. **Logging**: Log important operations for debugging and auditing
4. **Resource Management**: Clean up temporary files and resources
5. **Testing**: Test supertools in isolation before integrating

## Troubleshooting

### Tool Not Available

- Check agent's `supertools.allowed` list in `agents.yaml`
- Verify tool is registered (import the supertool module)
- Check logs for registration errors

### Credential Issues

- Verify credentials exist in `credentials/{agent_id}.yaml`
- Check required credential keys match tool's `get_required_credentials()`
- Ensure credentials are properly formatted

### Execution Failures

- Check execution constraints (timeouts, resource limits)
- Verify workspace permissions
- Review logs for detailed error messages

## Future Enhancements

- Supertool versioning
- Dependency management
- Performance metrics
- Testing framework
- Marketplace/discovery UI




