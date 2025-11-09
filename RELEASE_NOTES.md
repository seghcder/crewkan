# CrewKan Release Notes

## Version 0.2.0

**Release Date**: 2025-11-09

### New Features

#### Error Handling & Reliability
- **File Locking**: `.lck` file-based semaphores prevent read-update-write race conditions
- **Schema Validation**: YAML schema validation using `yamale` (board, agents, tasks)
- **Versioning**: Automatic version field addition to all YAML files (enables future migrations)
- **Retry Logic**: Automatic retry on transient file system errors (3 retries, configurable)
- **Corruption Detection**: Enhanced error messages with recovery suggestions
- **Backup Creation**: Automatic `.bak` file creation before overwrites
- **Atomic Writes**: Temporary file → atomic rename prevents partial writes

#### Event System Enhancements
- **Event Tools**: LangChain tools for event management (list_events, mark_event_read, get_event, clear_all_events)
- **Assignment Notifications**: Automatic event creation when tasks are assigned
- **Enhanced LangGraph Example**: Updated CEO delegation example to use event tools

### Improvements

- **Error Messages**: Context-rich error messages with file paths and recovery suggestions
- **BoardClient Error Handling**: Wrapped file operations with better error context
- **Test Coverage**: Added comprehensive corruption and error handling tests
- **Documentation**: New `ERROR_HANDLING.md` guide

### Technical Details

- **New Dependencies**: `yamale>=4.0.0` for schema validation
- **New Modules**: `crewkan/file_locking.py`, `crewkan/schemas/`
- **Backward Compatible**: All new features are optional and can be disabled

### Migration Notes

- No migration needed - version field automatically added to existing files
- Schema validation is optional (gracefully degrades if yamale not installed)
- File locking is enabled by default but can be disabled per-operation

---

## Version 0.1.0

**Release Date**: 2025-11-09

### Key Features

#### Core Functionality
- **Filesystem-based Task Board**: Trello-like board using YAML files and directories
- **Git-friendly**: Designed for frequent commits and version control
- **Multi-Board Support**: Create and manage multiple boards with hierarchical relationships
- **Board Registry**: Central registry for discovering and managing boards

#### Agent Management
- **Human/AI Agent Support**: Support for both human and AI agents with distinct roles
- **Agent Workspaces**: Agent-specific views of tasks using symbolic links
- **Superagent Support**: Default superagent for task escalation

#### Task Management
- **Full Task Lifecycle**: Create, read, update, move, assign, comment on tasks
- **Task Dependencies**: Support for task dependencies (structure in place)
- **Task History**: Complete audit trail of all task changes
- **Priority and Tags**: Task prioritization and tagging system

#### User Interfaces
- **Streamlit UI**: Web-based interface for visualizing and managing the board
  - Multi-column Kanban view
  - Task creation and editing
  - Task assignment and movement
  - Task renaming
  - Tag updates
  - Comment system
  - Auto-refresh on filesystem changes
- **CLI Interface**: Command-line tools for board management
  - Agent management (list, add, remove)
  - Task management (create, list, move, assign)
  - Board validation
  - Workspace management

#### AI Integration
- **LangChain Tools**: Integration with LangChain for AI agents
  - List tasks
  - Move tasks
  - Update task fields
  - Add comments
  - Reassign tasks
  - Create tasks
- **Azure OpenAI Support**: Tested with Azure OpenAI deployments

#### Testing & Quality
- **Comprehensive Test Suite**: 
  - CLI tests (9 tests)
  - UI tests via Playwright (7 tests)
  - Simulation tests
  - Abstracted test framework
  - LangChain integration tests
- **Code Coverage**: 25% coverage with framework for improvement
- **Unified Test Runner**: Single command to run all tests with coverage

#### Developer Experience
- **Logging**: Python native logging throughout codebase
- **Type Hints**: Type annotations on main functions
- **Shared Utilities**: Consolidated utility functions in `utils.py`
- **Documentation**: Comprehensive documentation in `docs/` directory

### Technical Details

- **Storage**: Filesystem-based (YAML files)
- **Language**: Python 3.8+
- **Dependencies**: PyYAML, Streamlit, LangChain, Playwright (for testing)
- **Architecture**: Storage-agnostic API design (filesystem implementation complete)

### Known Limitations

- Drag-and-drop in Streamlit UI not implemented (would require custom JavaScript)
- WIP limits not enforced (structure in place)
- Task dependencies not fully implemented (structure in place)
- NoSQL/Postgres backends not yet implemented (concepts documented)

### Migration Notes

- Initial release - no migration needed
- Board format version: 1
- Agent format version: 1

### Contributors

Initial implementation and testing framework.

