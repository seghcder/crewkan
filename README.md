# CrewKan

**A task management system for hybrid human + AI agent networks.**

CrewKan provides a Trello-like Kanban board system designed specifically for coordinating work between human and AI agents. Built with storage-agnostic architecture, it enables seamless task management whether you're using filesystem storage, NoSQL databases, or traditional relational databases.

**Version**: 0.2.0

## Why CrewKan?

CrewKan is uniquely designed for the era of AI agents working alongside humans:

- **Agent-First Design**: Every operation is scoped to a specific agent (human or AI), providing complete audit trails and accountability
- **Storage-Agnostic**: Same interfaces work with filesystem, NoSQL, or PostgreSQL backends - choose what fits your infrastructure
- **Git-Friendly**: Filesystem implementation uses YAML files that are perfect for version control, code reviews, and collaboration
- **AI-Native Integration**: Built-in LangChain and LangGraph tools let AI agents manage tasks autonomously
- **Event System**: Framework-agnostic event notifications keep agents informed of task completions and assignments
- **Multi-Board Hierarchy**: Organize work across CEO boards, project sub-boards, and team boards with parent-child relationships

## Key Features

- **Trello-like Kanban Boards**: Organize tasks in customizable columns with WIP limits
- **Hybrid Agent Support**: Manage both human and AI agents with unified interfaces
- **Task Lifecycle Management**: Create, assign, move, comment, and track tasks through their complete lifecycle
- **Agent Workspaces**: Each agent has a personalized view of tasks they're actively working on
- **Streamlit Web UI**: Beautiful, auto-refreshing web interface for visualizing and managing boards
- **CLI Tools**: Command-line interface for automation and scripting
- **LangChain Integration**: Ready-to-use tools for AI agents to interact with boards
- **Event Notifications**: File-based event system for agent-to-agent communication
- **Error Handling**: Robust file locking, schema validation, retry logic, and corruption detection
- **Complete Audit Trail**: Full history of all task changes with timestamps and agent attribution

## Use Cases

### CEO Delegation and Coordination

Coordinate high-level initiatives across multiple teams. CEO agents create tasks and delegate to worker agents, receiving notifications when work completes. See `examples/langgraph_ceo_delegation.py` for a complete implementation.

### Hybrid Human + AI Teams

Manage projects where human team members and AI agents collaborate on the same board. Assign tasks to either humans or AI agents seamlessly.

### Multi-Agent Orchestration

Orchestrate complex workflows with multiple AI agents working in parallel. Each agent can have its own workspace while contributing to shared boards.

### Project Management with AI Assistance

Use AI agents to help prioritize, assign, and track project tasks while maintaining human oversight and control.

## Requirements

- Python 3.8 or higher
- Virtual environment (recommended)

## Installation

### Basic Installation

```bash
# Clone the repository
git clone <repository-url>
cd crewkan

# Create and activate virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Development Installation

For development, you may also want to install additional testing dependencies:

```bash
pip install coverage pytest playwright
```

### Optional Dependencies

Some features require additional packages:

- **LangChain Integration**: Already included in `requirements.txt`
- **Azure OpenAI**: Requires `.env` file with credentials (see examples)
- **UI Testing**: Requires Playwright (`pip install playwright && playwright install`)

## Quick Start

### 1. Initialize a Board

Create a new board with sample agents:

```bash
python -m crewkan.crewkan_setup --root ./crewkan_board --with-sample-agents
```

This creates a board directory with:

- Board configuration (`board.yaml`)
- Sample agents (`agents/agents.yaml`)
- Task directories for each column
- Workspace directories for agents

### 2. Set Environment Variable (Optional)

For convenience, set the board root as an environment variable:

```bash
export CREWKAN_BOARD_ROOT=./crewkan_board
```

### 3. Use the CLI

List available agents:

```bash
python -m crewkan.crewkan_cli --root ./crewkan_board list-agents
```

Create a new task:

```bash
python -m crewkan.crewkan_cli --root ./crewkan_board new-task --title "Test task" --column todo
```

List all tasks:

```bash
python -m crewkan.crewkan_cli --root ./crewkan_board list-tasks
```

### 4. Launch the Web UI

Start the Streamlit interface:

```bash
streamlit run crewkan/crewkan_ui.py
```

The UI will automatically detect the board if `CREWKAN_BOARD_ROOT` is set, or you can specify it in the UI.

### First Steps Workflow

1. **Create a board** using `crewkan_setup`
2. **Add your agents** (human or AI) using the CLI or by editing `agents/agents.yaml`
3. **Create initial tasks** using the CLI or UI
4. **Assign tasks** to agents
5. **Move tasks** through columns as work progresses
6. **View agent workspaces** to see what each agent is working on

## Advanced Usage

### LangChain / LangGraph Integration

CrewKan provides LangChain tools that AI agents can use to interact with boards:

```python
from crewkan.langchain_tools import get_crewkan_tools
from langchain_openai import ChatOpenAI

# Initialize tools for a specific agent and board
tools = get_crewkan_tools(
    board_root="./crewkan_board",
    agent_id="ai-agent-1"
)

# Use with LangChain agent
llm = ChatOpenAI(model="gpt-4")
agent = initialize_agent(tools, llm, agent="zero-shot-react-description")
```

Available tools include:

- `list_tasks` - List tasks with filtering
- `move_task` - Move tasks between columns
- `update_task_field` - Update task properties
- `add_comment` - Add comments to tasks
- `reassign_task` - Assign or reassign tasks
- `create_task` - Create new tasks
- `list_events` - Check for event notifications
- `mark_event_read` - Mark events as read

See `examples/langgraph_ceo_delegation.py` for a complete LangGraph implementation.

### Event System

CrewKan includes a file-based event system for agent notifications:

```python
from crewkan.board_core import BoardClient

client = BoardClient("./crewkan_board", "worker1")

# Move task to done - automatically creates event
client.move_task("T-123", "done")

# Check for events (as CEO agent)
ceo_client = BoardClient("./crewkan_board", "ceo")
events = ceo_client.list_events()
for event in events:
    print(f"Event: {event['type']} - {event['data']['task_title']}")
    ceo_client.mark_event_read(event['id'])
```

Events are automatically created when:

- Tasks are moved to "done" (notifies `requested_by` agent)
- Tasks are assigned to agents

See `docs/EVENT_SYSTEM.md` for complete documentation.

### Multi-Board Orchestration

Create hierarchical board structures:

```python
# Create CEO board
ceo_board = BoardClient("./ceo_board", "ceo-agent")
ceo_board.create_board("CEO Coordination Board", columns=[...])

# Create sub-board for a project
project_board = BoardClient("./project_board", "ceo-agent")
project_board.create_board("Project Alpha", parent_board_id="ceo")
```

### Programmatic API Usage

Use the BoardClient directly in your code:

```python
from crewkan.board_core import BoardClient

# Initialize client for a specific agent
client = BoardClient("./crewkan_board", "agent-id")

# Create a task
task_id = client.create_task(
    title="Implement feature X",
    description="Add new functionality",
    column="todo",
    priority="high",
    assignees=["developer-1"]
)

# Move task
client.move_task(task_id, "doing")

# Add comment
client.add_comment(task_id, "Starting implementation")

# Update task
client.update_task_field(task_id, "priority", "medium")

# Get agent workspace
workspace = client.list_workspace("developer-1")
```

## Architecture Overview

CrewKan is built with a **storage-agnostic architecture** that separates the logical Board Service API from the underlying storage implementation. This means:

- **Same API** works with filesystem, NoSQL, or PostgreSQL
- **Same UI** (Streamlit) works with any backend
- **Same Tools** (LangChain) work with any backend

### Core Concepts

- **Agents**: Human or AI actors that can be assigned tasks and perform operations
- **Boards**: Collections of tasks organized in columns (like Trello boards)
- **Tasks**: Units of work with lifecycle, assignment, and history
- **Workspaces**: Agent-specific views of tasks they're actively working on
- **Board Registry**: Central registry for discovering and managing multiple boards

### Storage Implementations

Currently implemented:

- **Filesystem**: YAML-based storage, git-friendly, perfect for local development

Planned (concepts documented):

- **NoSQL**: MongoDB, DynamoDB, or other document stores
- **PostgreSQL**: Relational database backend

See `docs/01-crewkan-requirements.md` for the complete storage-agnostic specification, and `docs/02-crewkan-fs-concept.md` for filesystem implementation details.

## Documentation

### Getting Started

- **AGENT_PROCESS.md** - Setup guide and agent process documentation
- **REQUIREMENTS_VALIDATION.md** - Requirements validation process

### Core Documentation

- **01-crewkan-requirements.md** - Storage-agnostic system requirements specification
- **02-crewkan-fs-concept.md** - Filesystem/YAML implementation concept
- **03-crewkan-nosql-concept.md** - NoSQL implementation concept

### Feature Documentation

- **EVENT_SYSTEM.md** - Event system for agent notifications
- **ERROR_HANDLING.md** - Error handling, file locking, and reliability features
- **FILESYSTEM_CHANGE_DETECTION.md** - How the UI detects filesystem changes

### Examples

- **examples/README.md** - Example implementations and use cases
- **examples/langgraph_ceo_delegation.py** - Complete LangGraph CEO delegation example

### Project Information

- **RELEASE_NOTES.md** - Release information and feature history
- **MAINTENANCE.md** - Versioning and maintenance guide
- **BACKLOG.md** - Future enhancements and roadmap

## Contributing

### Development Setup

1. Clone the repository
2. Create a virtual environment and install dependencies (see Installation)
3. Install development dependencies: `pip install coverage pytest playwright`
4. Run tests to verify setup: `PYTHONPATH=. python tests/test_all.py --coverage`

### Running Tests

Run all tests with coverage:

```bash
PYTHONPATH=. python tests/test_all.py --coverage
```

Run tests without coverage:

```bash
PYTHONPATH=. python tests/test_all.py --no-coverage
```

See `tests/README.md` for individual test suites.

### Code Quality

- Add type hints to all new functions
- Add docstrings to public functions/classes
- Maintain or improve test coverage
- Follow existing code patterns

### Contributing Ideas

See `BACKLOG.md` for planned features and areas where contributions are welcome. High-priority items include:

- Test coverage improvements (target: 90%+)
- Additional storage backends (NoSQL, PostgreSQL)
- UI/UX enhancements
- Documentation improvements

## Project Status

**Current Version**: 0.2.0

CrewKan is in active development. The filesystem backend is production-ready with comprehensive error handling, file locking, and schema validation. AI agent integration is fully functional with LangChain and LangGraph.

See `RELEASE_NOTES.md` for detailed version history and `BACKLOG.md` for planned features.

## License

[Add license information if applicable]

---

For questions, issues, or contributions, please refer to the documentation in the `docs/` directory or check the `BACKLOG.md` for known limitations and future plans.
