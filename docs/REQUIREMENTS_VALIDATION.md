# CrewKan Requirements Validation Guide

This document provides a systematic way for agents to validate that all requirements from `01-crewkan-requirements.md` have been implemented in the selected instantiation (filesystem/YAML).

## Requirements Framework

Each requirement is numbered and mapped to implementation evidence.

### R1: Core Concepts

#### R1.1 Agent
- [ ] **R1.1.1** Agent has `id`, `name`, `role`, `kind`, `status`, `skills`, `metadata`
  - Evidence: `crewkan/board_core.py` - `BoardClient._agent_index`
  - Test: Create agent via CLI, verify all fields
- [ ] **R1.1.2** Agent `kind` supports "human" and "ai"
  - Evidence: `crewkan/crewkan_cli.py` - `cmd_add_agent` with `--kind` argument
  - Test: Create agents with both kinds, verify in agents.yaml
- [ ] **R1.1.3** Superagent concept supported
  - Evidence: `crewkan/board_core.py` - `get_default_superagent_id()`
  - Test: Set superagent in board.yaml, verify escalation works

#### R1.2 Board
- [ ] **R1.2.1** Board has `id`, `name`, `columns`, `settings`
  - Evidence: `crewkan/board_init.py` - `init_board()` creates board.yaml
  - Test: Create board, verify structure
- [ ] **R1.2.2** Columns have `id`, `name`, `wip_limit`
  - Evidence: `crewkan/board_init.py` - `DEFAULT_COLUMNS`
  - Test: Verify column structure in created board
- [ ] **R1.2.3** Settings include `default_priority`, `default_superagent_id`
  - Evidence: `crewkan/board_init.py` - board.yaml settings
  - Test: Verify settings in board.yaml

#### R1.3 Task
- [ ] **R1.3.1** Task has all required attributes (id, title, description, status, column, priority, tags, assignees, dependencies, timestamps, history)
  - Evidence: `crewkan/board_core.py` - `create_task()` method
  - Test: Create task, verify all fields present
- [ ] **R1.3.2** History events track: created, moved, updated, comment, reassigned
  - Evidence: `crewkan/board_core.py` - history append in all operations
  - Test: Perform operations, verify history entries

#### R1.4 Workspace
- [ ] **R1.4.1** `start_work()` adds task to workspace
  - Evidence: `crewkan/crewkan_cli.py` - `cmd_start_task()` creates symlink
  - Test: Start work, verify symlink exists
- [ ] **R1.4.2** `stop_work()` removes task from workspace
  - Evidence: `crewkan/crewkan_cli.py` - `cmd_stop_task()` removes symlink
  - Test: Stop work, verify symlink removed

#### R1.5 Board Registry
- [ ] **R1.5.1** Registry tracks board id, path, owner_agent, status, parent_board_id
  - Evidence: `crewkan/board_registry.py` - `BoardRegistry` class
  - Test: Register boards, verify registry.yaml

### R2: Functional Requirements

#### R2.1 Agent Management
- [ ] **R2.1.1** Create agents
  - Evidence: `crewkan/crewkan_cli.py` - `cmd_add_agent()`
  - Test: `python -m crewkan.crewkan_cli add-agent --id test --name Test`
- [ ] **R2.1.2** List agents
  - Evidence: `crewkan/crewkan_cli.py` - `cmd_list_agents()`
  - Test: `python -m crewkan.crewkan_cli list-agents`
- [ ] **R2.1.3** Remove agents
  - Evidence: `crewkan/crewkan_cli.py` - `cmd_remove_agent()`
  - Test: Remove agent, verify removed from agents.yaml
- [ ] **R2.1.4** Mark agents inactive
  - Evidence: Agent status field in agents.yaml
  - Test: Update agent status to inactive

#### R2.2 Board Management
- [ ] **R2.2.1** Create board
  - Evidence: `crewkan/board_init.py` - `init_board()`
  - Test: `python -c "from crewkan.board_init import init_board; init_board(...)"`
- [ ] **R2.2.2** Register board in registry
  - Evidence: `crewkan/board_registry.py` - `register_board()`
  - Test: Register board, verify in registry.yaml
- [ ] **R2.2.3** Archive board
  - Evidence: `crewkan/board_registry.py` - `archive_board()`
  - Test: Archive board, verify status changed

#### R2.3 Task Lifecycle
- [ ] **R2.3.1** Create task
  - Evidence: `crewkan/board_core.py` - `create_task()`
  - Test: Create task via CLI or BoardClient
- [ ] **R2.3.2** Read task
  - Evidence: `crewkan/board_core.py` - `find_task()`
  - Test: Retrieve task by ID
- [ ] **R2.3.3** Update task fields (title, description, priority, due_date)
  - Evidence: `crewkan/board_core.py` - `update_task_field()`
  - Test: Update each field, verify change
- [ ] **R2.3.4** Move task between columns
  - Evidence: `crewkan/board_core.py` - `move_task()`
  - Test: Move task, verify file location and column field
- [ ] **R2.3.5** Assign/reassign task
  - Evidence: `crewkan/board_core.py` - `reassign_task()`
  - Test: Assign to agent, reassign, verify assignees
- [ ] **R2.3.6** Add comment
  - Evidence: `crewkan/board_core.py` - `add_comment()`
  - Test: Add comment, verify in history
- [ ] **R2.3.7** Query tasks (by column, assignee, priority, tags)
  - Evidence: `crewkan/board_core.py` - `list_my_tasks()` with filters
  - Test: Query with various filters

#### R2.4 Workspaces
- [ ] **R2.4.1** `start_work()` optionally moves task to target column
  - Evidence: `crewkan/crewkan_cli.py` - `cmd_start_task()` moves if needed
  - Test: Start work with different source columns
- [ ] **R2.4.2** `stop_work()` doesn't change column
  - Evidence: `crewkan/crewkan_cli.py` - `cmd_stop_task()` only removes symlink
  - Test: Stop work, verify column unchanged

#### R2.5 Multi-Board Orchestration
- [ ] **R2.5.1** Multiple boards can exist
  - Evidence: `crewkan/board_registry.py` - supports multiple boards
  - Test: Create multiple boards, verify all exist
- [ ] **R2.5.2** Parent/child board relationships
  - Evidence: `crewkan/board_registry.py` - `parent_board_id` field
  - Test: Create child board with parent, verify relationship

### R3: Interfaces

#### R3.1 Board Service API
- [ ] **R3.1.1** `list_my_tasks()`
  - Evidence: `crewkan/board_core.py` - `list_my_tasks()`
  - Test: Call method, verify JSON output
- [ ] **R3.1.2** `move_task()`
  - Evidence: `crewkan/board_core.py` - `move_task()`
  - Test: Move task, verify result
- [ ] **R3.1.3** `update_task_field()`
  - Evidence: `crewkan/board_core.py` - `update_task_field()`
  - Test: Update field, verify change
- [ ] **R3.1.4** `add_comment()`
  - Evidence: `crewkan/board_core.py` - `add_comment()`
  - Test: Add comment, verify in history
- [ ] **R3.1.5** `reassign_task()`
  - Evidence: `crewkan/board_core.py` - `reassign_task()`
  - Test: Reassign with various options
- [ ] **R3.1.6** `create_task()`
  - Evidence: `crewkan/board_core.py` - `create_task()`
  - Test: Create task, verify all fields
- [ ] **R3.1.7** `start_work()` / `stop_work()`
  - Evidence: `crewkan/crewkan_cli.py` - workspace commands
  - Test: Start/stop work, verify symlinks

#### R3.2 Web UI (Streamlit)
- [ ] **R3.2.1** UI displays boards and tasks
  - Evidence: `crewkan/crewkan_ui.py` - main UI code
  - Test: Run `streamlit run crewkan/crewkan_ui.py`, verify display
- [ ] **R3.2.2** UI allows creating tasks
  - Evidence: `crewkan/crewkan_ui.py` - `create_task()` function
  - Test: Create task via UI, verify created
- [ ] **R3.2.3** UI allows moving tasks
  - Evidence: `crewkan/crewkan_ui.py` - `move_task()` function
  - Test: Move task via UI, verify moved
- [ ] **R3.2.4** UI allows assigning tasks
  - Evidence: `crewkan/crewkan_ui.py` - `assign_task()` function
  - Test: Assign task via UI, verify assigned

#### R3.3 LangChain Tools
- [ ] **R3.3.1** Tools can be created for an agent
  - Evidence: `crewkan/board_langchain_tools.py` - `make_board_tools()`
  - Test: Create tools, verify all tools present
- [ ] **R3.3.2** Each tool is bound to agent_id
  - Evidence: `crewkan/board_langchain_tools.py` - BoardClient initialized with agent_id
  - Test: Create tools for different agents, verify isolation
- [ ] **R3.3.3** All Board Service operations available as tools
  - Evidence: `crewkan/board_langchain_tools.py` - all tools defined
  - Test: Verify tool list matches API operations

### R4: Filesystem Instantiation Specific

#### R4.1 Directory Structure
- [ ] **R4.1.1** Board root contains board.yaml, agents/, tasks/, workspaces/, archive/
  - Evidence: `crewkan/board_init.py` - `init_board()` creates structure
  - Test: Create board, verify directory structure
- [ ] **R4.1.2** Tasks stored in tasks/<column>/*.yaml
  - Evidence: `crewkan/board_core.py` - tasks saved to column directories
  - Test: Create task, verify file location
- [ ] **R4.1.3** Workspaces use symlinks
  - Evidence: `crewkan/crewkan_cli.py` - `create_symlink()` function
  - Test: Start work, verify symlink created

#### R4.2 YAML Format
- [ ] **R4.2.1** board.yaml follows schema
  - Evidence: `crewkan/board_init.py` - board.yaml structure
  - Test: Verify YAML structure matches requirements doc
- [ ] **R4.2.2** agents.yaml follows schema
  - Evidence: `crewkan/board_init.py` - agents.yaml structure
  - Test: Verify agents.yaml structure
- [ ] **R4.2.3** Task YAML files follow schema
  - Evidence: `crewkan/board_core.py` - task structure
  - Test: Verify task YAML structure

#### R4.3 Board Registry
- [ ] **R4.3.1** Registry stored at boards/registry.yaml
  - Evidence: `crewkan/board_registry.py` - registry path
  - Test: Register board, verify registry.yaml created
- [ ] **R4.3.2** Registry tracks all required fields
  - Evidence: `crewkan/board_registry.py` - `register_board()` fields
  - Test: Verify registry entries

## Validation Process

1. Run the test simulation: `python tests/test_simulation.py --agents 10 --tasks 1000 --boards 3 --cycles 50`
2. Run coverage test: `python tests/test_coverage.py`
3. Manually verify each requirement using the evidence and test steps above
4. Check off requirements as validated
5. Document any gaps or issues

## Coverage Target

- Code coverage: 90%+ (measured via `tests/test_coverage.py`)
- Requirements coverage: 100% (all requirements validated)

