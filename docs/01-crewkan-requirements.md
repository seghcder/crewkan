# CrewKan – System Requirements Specification (Storage-Independent)

### CrewKan – System Requirements Specification (Storage-Independent)

#### 1. Purpose

CrewKan is a task and coordination system for hybrid **human + AI agent networks** running an organisation.

The system must:

* Provide a Trello-like board model for tasks.
* Allow multiple boards (e.g. CEO board + project sub-boards).
* Be **storage-agnostic**: same interfaces regardless of backend (filesystem, NoSQL, Postgres, future).
* Be **agent-first**: every operation is scoped to a specific agent (human or AI).

This document defines the behaviour and interfaces of CrewKan independently of any concrete storage implementation.

---

#### 2. Scope

CrewKan covers:

* Core domain concepts: **Agents**, **Boards**, **Tasks**, **Workspaces**, **Board Registry**.
* Functional behaviour for:

  * Managing agents and boards
  * Creating, updating, and routing tasks
  * Multi-board orchestration (parent/child boards)
* Interfaces:

  * A **Board Service API** (logical interface)
  * A Web UI (e.g. Streamlit)
  * AI agent tools (e.g. LangChain)

Out of scope:

* Authentication/authorization mechanics (left to host environment).
* Specific storage technology details (handled in instantiation concepts).

---

#### 3. Core Concepts

##### 3.1 Agent

An **Agent** is any actor that can:

* Be assigned tasks
* Call CrewKan interfaces (human or AI process)

Attributes:

* `id`: globally unique string
* `name`: human-readable display name
* `role`: free-text description (e.g. “Infra Architect Agent”)
* `kind`: `"human"` or `"ai"`
* `status`: `"active"`, `"inactive"`, `"suspended"`
* `skills`: optional list of tags
* `metadata`: arbitrary key/value map (email, external IDs, etc.)

Special roles:

* **Superagent**: a designated agent (human or AI) that receives escalated tasks by default.

---

##### 3.2 Board

A **Board** is a named collection of tasks organised in **columns**.

Attributes:

* `id`: unique within an organisation
* `name`: human-readable name
* `columns`: ordered list of column definitions:

  * `id` (e.g. `"backlog"`, `"todo"`, `"doing"`, `"blocked"`, `"done"`)
  * `name` (display label)
  * `wip_limit` (optional integer or null)
* `settings`:

  * `default_priority` (e.g. `"medium"`)
  * `default_superagent_id` (optional)
  * additional implementation-independent settings as required

Each board has:

* A set of **tasks** belonging to that board
* A set of **participating agents** (subset of global agents)

---

##### 3.3 Task

A **Task** represents a unit of work.

Attributes (minimum):

* `id`: stable unique identifier
* `board_id`: owning board
* `title`
* `description`
* `status` / `column`: current column id
* `priority`: e.g. `"low"|"medium"|"high"`
* `tags`: list of free-text tags
* `assignees`: list of agent ids
* `dependencies`: list of other task ids
* `created_at`, `updated_at`
* `due_date`: optional
* `history`: ordered list of events

History events (examples):

* `event: "created"`, `"moved"`, `"updated"`, `"comment"`, `"reassigned"`
* `by`: agent id
* `at`: timestamp
* `details`: free text or structured info

---

##### 3.4 Workspace / Working Set

An **Agent Workspace** is a view of tasks an agent is actively focusing on.

Conceptually:

* For each agent, CrewKan maintains a **working set** of tasks (zero or more).
* A task can be in multiple working sets (shared work).
* Workspace membership is distinct from assignment; it’s a “currently working on” signal.

The representation of workspaces is implementation-dependent, but the semantics must be:

* `start_work(agent_id, task_id[, column])` – puts a task into an agent’s workspace and can optionally move it to a target column (e.g. `"doing"`).
* `stop_work(agent_id, task_id)` – removes the task from that agent’s workspace without necessarily changing its column.

---

##### 3.5 Board Registry and Hierarchy

CrewKan supports multiple boards per organisation and optional parent/child relationships.

A **Board Registry** conceptually tracks:

* `id`, `path_or_locator` (implementation-specific)
* `owner_agent`
* `status`: `"active"`, `"archived"`, `"deleted"`
* Optional `parent_board_id`

Examples:

* A **CEO board** that tracks high-level initiatives.
* Each initiative spawns a **sub-board** dedicated to that initiative.

---

#### 4. Functional Requirements

##### 4.1 Agent Management

* Create, update, and list agents.
* Support `kind = "human"` and `kind = "ai"`.
* Ability to mark agents inactive without deleting their historical references.
* Ability to identify the **default superagent** (for escalations).

---

##### 4.2 Board Management

* Create a new board with:

  * Name
  * Initial columns
  * Optional default settings
* Register boards in the Board Registry.
* Allow boards to specify a parent board (for hierarchy).
* Archive a board:

  * Prevent new tasks by default
  * Keep tasks readable for reporting
* Query all boards, and filter by status or owner_agent.

---

##### 4.3 Task Lifecycle

For each board:

* Create a task with:

  * Required: `title`, initial `column` or default
  * Optional: `description`, `priority`, `tags`, `assignees`, `due_date`
* Read task details by id.
* Update fields:

  * `title`, `description`, `priority`, `due_date`
* Move task between columns:

  * Enforce column existence
  * Respect WIP limits (warn or fail according to configuration)
* Assign / reassign:

  * Add or replace assignees
  * Reassign to another agent
  * Escalate to superagent (`to_superagent`)
* Comment:

  * Add free-text comments to `history`
* Query tasks:

  * By board, column, assignee, priority, tags
  * Pagination for large result sets

---

##### 4.4 Workspaces

* `start_work(agent_id, task_id[, target_column])`

  * Optionally move task into a working column (e.g. `"doing"`)
  * Add task to agent’s workspace
* `stop_work(agent_id, task_id)`

  * Remove task from workspace (no mandatory column change)
* List workspace tasks per agent (`list_workspace(agent_id)`).

The UI and tools may choose to surface workspace tasks in a dedicated view.

---

##### 4.5 Multi-Board Orchestration

* CEO board tasks may reference sub-boards via metadata fields (e.g. `sub_board_id`).
* Tools must be able to:

  * Discover sub-boards linked to a CEO task
  * Summarise the state of a sub-board (e.g. number of tasks by column, key risks)

The exact summary semantics can evolve but must be independent of storage backend.

---

#### 5. Interfaces

CrewKan exposes a **logical Board Service API** used by:

* A Web UI (e.g. Streamlit app)
* AI agents (e.g. LangChain tools)
* Potentially other consumers (CLI, other services)

This API is logical; each implementation must provide conformant functions/endpoints.

##### 5.1 Core Board Service Operations (logical)

At minimum, the API must support:

* `list_my_tasks(agent_id, board_id, column=None, limit=N)`
* `move_task(agent_id, board_id, task_id, new_column)`
* `update_task_field(agent_id, board_id, task_id, field, value)`
* `add_comment(agent_id, board_id, task_id, comment)`
* `reassign_task(agent_id, board_id, task_id, new_assignee_id=None, to_superagent=False, keep_existing=False)`
* `create_task(agent_id, board_id, title, description, column, assignees, priority, tags, due_date)`
* `start_work(agent_id, board_id, task_id, target_column=None)`
* `stop_work(agent_id, board_id, task_id)`
* `list_boards()` and `get_board(board_id)`
* `create_board(owner_agent_id, name, columns, settings)`
* `archive_board(board_id)`

For AI tooling (e.g. LangChain):

* Each tool instance is bound to a specific `(board_root_or_locator, agent_id)`.
* Tools must perform operations **as that agent** (for audit/history).

---

#### 6. Non-Functional Requirements

* **Storage-agnostic**: Behaviour of the Board Service API must not depend on the storage backend.
* **Deterministic semantics**:

  * Task operations should be idempotent when appropriate (e.g. moving to same column).
* **Testability**:

  * Must be possible to run the same integration test suite against different backends (filesystem, NoSQL, Postgres, etc.).
* **Observability**:

  * Implementations must be able to log operations (at least for debugging), including `agent_id` and `board_id`.
* **Performance**:

  * Reasonable latency for human and AI usage in typical small-to-medium organisations.
* **Versioning**:

  * Schema evolution should be supported via versioned documents/structures, but the API should remain stable.

---

#### 7. Meta Requirements and Pluggable Backends

* CrewKan must support **pluggable backends**:

  * Filesystem + YAML
  * NoSQL document store
  * Relational DB (e.g. Postgres)
  * Future representations (e.g. “optical quantum representation”)

* Board instantiation must allow selecting a backend via configuration, e.g.:

  ```yaml
  crewkan:
    storage:
      kind: "filesystem"    # or "nosql", "postgres", "custom"
      config:
        # backend-specific settings
  ```

* The Web UI (Streamlit) and AI tools (LangChain) must call only the logical Board Service API; they must not depend on the backend type.

---

---

