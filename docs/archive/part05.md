
How about CrewKan. ok, abstract out from this a generic requirements specification doc thats independent of the implementation. then a second "instantiation" concept doc that conceptualises the filesystem based implementation. but also write a second instantiation concept doc that conceptualises a NoSQL implementation but keeps the same interfaces (UI with streamlit, Langchain tool). Im going to move these into their own repo so I can set up full testing framework etc. during board instatitation the user can choose which concept to use (filesystem, postgres, or some future to come optical quantum representation). this is part of the "meta requirements" I guess. 


--------------

Let’s go with **CrewKan** then. Nice and short.

Below are three documents you can drop straight into a repo:

1. `01-crewkan-requirements.md` – storage-agnostic requirements
2. `02-crewkan-fs-concept.md` – filesystem/YAML instantiation concept
3. `03-crewkan-nosql-concept.md` – NoSQL instantiation concept

You can tweak numbering/names to suit your doc style.

---

## 01-crewkan-requirements.md

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

## 02-crewkan-fs-concept.md

### CrewKan Filesystem/YAML Instantiation Concept

#### 1. Purpose

This document describes how the storage-agnostic CrewKan requirements are instantiated using:

* A **regular filesystem**
* **YAML** files as the primary data format

The goal is to be:

* Git-friendly (easy diffs, branches, PRs)
* Simple to inspect and modify manually
* Easy for local AI agents to manipulate without a database server

---

#### 2. Mapping of Concepts to Filesystem

At a high level, each **Board** is rooted at a directory with a defined structure.

Example:

```text
boards/
  ceo/
    board.yaml
    agents.yaml
    tasks/
      backlog/
      todo/
      doing/
      blocked/
      done/
    workspaces/
      nuni/
      tau/
    archive/
      tasks/
```

##### 2.1 Board Root

For each board, the root directory contains at minimum:

* `board.yaml` – board metadata and columns
* `agents.yaml` – participating agents for this board
* `tasks/` – canonical storage for tasks
* `workspaces/` – per-agent working sets (symlinks)
* `archive/` – archived tasks

---

##### 2.2 Board Definition (`board.yaml`)

Example:

```yaml
board_name: "CEO Coordination Board"
board_id: "ceo"
version: 1

columns:
  - id: backlog
    name: "Backlog"
    wip_limit: null
  - id: todo
    name: "To Do"
    wip_limit: 10
  - id: doing
    name: "Doing"
    wip_limit: 5
  - id: blocked
    name: "Blocked"
    wip_limit: 5
  - id: done
    name: "Done"
    wip_limit: null

settings:
  default_priority: "medium"
  default_superagent_id: "ceo-agent"
  task_filename_prefix: "T"
```

---

##### 2.3 Agents (`agents.yaml`)

Per-board agent list:

```yaml
agents:
  - id: "ceo-agent"
    name: "CEO Agent"
    role: "Top-level coordinator"
    kind: "ai"
    status: "active"
    skills: ["coordination"]
    metadata: {}

  - id: "sean"
    name: "Sean"
    role: "Founder / Architect"
    kind: "human"
    status: "active"
    skills: ["architecture", "strategy"]
    metadata: {}
```

Global agents (across boards) may be stored elsewhere; the filesystem instantiation is responsible for reconciling them as needed.

---

##### 2.4 Tasks (`tasks/<column>/*.yaml`)

Each task is stored as a YAML file in a directory named by its column.

Example directory layout:

```text
tasks/
  todo/
    T-20251109-aaaaaa.yaml
  doing/
    T-20251109-bbbbbb.yaml
  done/
```

Task file example:

```yaml
id: "T-20251109-aaaaaa"
board_id: "ceo"
title: "Launch Hospital A analytics initiative"
description: "Define scope, create sub-board, and identify initial agents."
status: "todo"
column: "todo"
priority: "high"
tags:
  - "hospital-a"
  - "analytics"
assignees:
  - "ceo-agent"
dependencies: []
created_at: "2025-11-09T03:14:15Z"
updated_at: "2025-11-09T03:14:15Z"
due_date: null
history:
  - at: "2025-11-09T03:14:15Z"
    by: "ceo-agent"
    event: "created"
    details: "Task created in column todo"
metadata:
  sub_board_id: "hospital-a-analytics"
```

---

##### 2.5 Workspaces (Symlink-Based Working Sets)

Workspaces provide a fast per-agent view by using **symlinks**.

Layout:

```text
workspaces/
  nuni/
    doing/
      T-20251109-xxxxxx.yaml -> ../../../tasks/doing/T-20251109-xxxxxx.yaml
  tau/
    doing/
      T-20251110-yyyyyy.yaml -> ../../../tasks/doing/T-20251110-yyyyyy.yaml
```

Semantics:

* A symlink exists for each task currently in that agent’s workspace.
* Directory name under `workspaces/<agent>/` mirrors the column id of the canonical task.
* Operations:

  * `start_work(agent_id, task_id, target_column)`:

    * Move the canonical task file into the `tasks/<target_column>/` directory.
    * Create or update symlink at `workspaces/<agent>/<target_column>/<id>.yaml`.
  * `stop_work(agent_id, task_id)`:

    * Remove any symlink(s) for that task under `workspaces/<agent>/`.

This keeps:

* **Canonical truth** in `tasks/`
* **Per-agent views** in `workspaces/`

---

##### 2.6 Archive

Archived tasks:

```text
archive/
  tasks/
    2025-11/
      T-20251001-zzzzzz.yaml
```

When archiving a board or tasks:

* Move task YAML files from `tasks/` into dated subdirectories under `archive/tasks/`.
* Keep references (task ids) for reporting and history.

---

#### 3. Board Registry

The filesystem instantiation can keep a central registry, e.g. at:

`boards/registry.yaml`:

```yaml
boards:
  - id: "ceo"
    path: "boards/ceo"
    owner_agent: "ceo-agent"
    status: "active"

  - id: "hospital-a-analytics"
    path: "boards/hospital-a-analytics"
    owner_agent: "nuni"
    status: "active"
    parent_board_id: "ceo"
```

This registry is optional for minimal setups, but recommended for multi-board orchestration.

---

#### 4. Board Service API Binding

The filesystem instantiation must provide a **Board Service API adapter** implementing the storage-agnostic operations using:

* Directory traversal (`Path.rglob`, etc.)
* YAML parsing and writing
* Atomic file writes (e.g. write to temp file then rename) to reduce corruption risk

Examples:

* `list_my_tasks`:

  * Traverse `tasks/**.yaml`
  * Parse each YAML, filter by `assignees` and `column`

* `move_task`:

  * Load YAML for the task file
  * Update fields
  * Move the file to the new column directory
  * Update symlinks in `workspaces/`

The Streamlit UI and LangChain tools call this adapter, not the filesystem directly.

---

#### 5. Concurrency and Git

Filesystem constraints:

* Multiple writers may concurrently modify YAML files; conflict resolution is delegated to:

  * Git merges (for human workflows)
  * Careful design of agent operations (e.g. small, atomic changes)

Recommended patterns:

* One operation writes one file at a time.
* Use optimistic locking where possible (e.g. version checks within YAML).
* For heavy concurrency scenarios, prefer the NoSQL or DB instantiation.

---

---

## 03-crewkan-nosql-concept.md

### CrewKan NoSQL Instantiation Concept

#### 1. Purpose

This document describes a CrewKan instantiation using a **NoSQL document store** as the underlying storage, while preserving:

* The same **Board Service API**
* The same **UI** (Streamlit)
* The same **LangChain tools**

Examples of suitable NoSQL backends:

* MongoDB
* DynamoDB
* Couchbase
* Other JSON/document-based stores

The concepts here are backend-neutral; each concrete implementation will map them to vendor-specific features.

---

#### 2. Data Model

##### 2.1 Collections

Recommended top-level collections:

* `boards`
* `agents`
* `tasks`
* `workspaces` (optional; can be embedded in tasks)
* `board_registry`

Each document is a JSON representation of the storage-agnostic entities.

---

##### 2.2 Agents

Collection: `agents`

Document shape (example):

```json
{
  "_id": "sean",
  "name": "Sean",
  "role": "Founder / Architect",
  "kind": "human",
  "status": "active",
  "skills": ["architecture", "strategy"],
  "metadata": {
    "email": "sean@example.com"
  }
}
```

Boards may maintain their own subset or references to global agent ids.

---

##### 2.3 Boards

Collection: `boards`

Example:

```json
{
  "_id": "ceo",
  "name": "CEO Coordination Board",
  "version": 1,
  "columns": [
    { "id": "backlog", "name": "Backlog", "wip_limit": null },
    { "id": "todo", "name": "To Do", "wip_limit": 10 },
    { "id": "doing", "name": "Doing", "wip_limit": 5 },
    { "id": "blocked", "name": "Blocked", "wip_limit": 5 },
    { "id": "done", "name": "Done", "wip_limit": null }
  ],
  "settings": {
    "default_priority": "medium",
    "default_superagent_id": "ceo-agent",
    "task_filename_prefix": "T"
  }
}
```

---

##### 2.4 Tasks

Collection: `tasks`

Example:

```json
{
  "_id": "T-20251109-aaaaaa",
  "board_id": "ceo",
  "title": "Launch Hospital A analytics initiative",
  "description": "Define scope, create sub-board, and identify initial agents.",
  "status": "todo",
  "column": "todo",
  "priority": "high",
  "tags": ["hospital-a", "analytics"],
  "assignees": ["ceo-agent"],
  "dependencies": [],
  "created_at": "2025-11-09T03:14:15Z",
  "updated_at": "2025-11-09T03:14:15Z",
  "due_date": null,
  "history": [
    {
      "at": "2025-11-09T03:14:15Z",
      "by": "ceo-agent",
      "event": "created",
      "details": "Task created in column todo"
    }
  ],
  "metadata": {
    "sub_board_id": "hospital-a-analytics"
  }
}
```

Indexes (recommended):

* `{ board_id: 1, column: 1 }` – for column-based queries
* `{ assignees: 1, board_id: 1 }` – for agent-centric queries
* Additional secondary indexes as needed for performance (e.g. tags, priority)

---

##### 2.5 Workspaces

Two possible design options:

1. **Embedded in tasks**

   * Each task stores a list of agents who have it in their workspace:

     ```json
     "workspace_agents": ["nuni", "tau"]
     ```

   * `start_work` adds the agent id to `workspace_agents` while optionally moving the task column.

   * `stop_work` removes the agent id.

2. **Dedicated `workspaces` collection**

   * Each document represents an `(agent_id, task_id)` pair:

     ```json
     {
       "_id": "nuni::T-20251109-aaaaaa",
       "agent_id": "nuni",
       "task_id": "T-20251109-aaaaaa",
       "board_id": "ceo",
       "created_at": "2025-11-09T04:00:00Z",
       "column_snapshot": "doing"
     }
     ```

   * `start_work` inserts or updates a workspace document.

   * `stop_work` deletes the workspace document(s).

Either approach is acceptable as long as the Board Service API semantics are preserved.

---

##### 2.6 Board Registry

Collection: `board_registry`

Example:

```json
{
  "_id": "ceo",
  "path_or_locator": "nosql://crewkan/boards/ceo",
  "owner_agent": "ceo-agent",
  "status": "active",
  "parent_board_id": null
}
```

For sub-boards:

```json
{
  "_id": "hospital-a-analytics",
  "path_or_locator": "nosql://crewkan/boards/hospital-a-analytics",
  "owner_agent": "nuni",
  "status": "active",
  "parent_board_id": "ceo"
}
```

---

#### 3. Board Service API Binding

The NoSQL instantiation provides an adapter that maps each logical Board Service operation to database operations.

Examples:

* `list_my_tasks(agent_id, board_id, column=None, limit=N)`:

  * Query `tasks` with:

    * `board_id = board_id`
    * `assignees` array contains `agent_id`
    * Optional `column = column`
  * Paginate via limit/offset or cursor

* `move_task`:

  * Update `column` and `status` fields in the `tasks` collection
  * Append a `history` event
  * Optionally update any `workspaces` representation

* `add_comment`:

  * Append a new `history` entry to the `history` array with `event = "comment"`

* `reassign_task`:

  * Modify the `assignees` array according to the rules in the requirements doc
  * Append a `history` event

* `create_task`:

  * Insert a new document in `tasks` with all required fields
  * Use an ID-generation strategy compatible with the global `task_id` format (e.g. application-generated IDs).

The Streamlit UI and LangChain tools operate against this adapter; they do not need to know that NoSQL is being used.

---

#### 4. Concurrency and Consistency

Compared to the filesystem instantiation, NoSQL provides:

* Atomic document-level updates
* Optional optimistic locking / version fields if needed
* Better support for concurrent writers (AI agents + humans)

Guidelines:

* For single-task operations, rely on atomic updates.
* For multi-document operations (e.g. moving many tasks), consider transactions if the backend supports them.
* Ensure that the observable behaviour (history, field changes) matches the storage-agnostic requirements.

---

#### 5. Configuration and Backend Selection

Board instantiation chooses the NoSQL backend via configuration, for example:

```yaml
crewkan:
  storage:
    kind: "nosql"
    config:
      provider: "mongo"
      uri: "mongodb://localhost:27017"
      database: "crewkan"
```

The same configuration shape can later support:

* `kind: "filesystem"` with a `root_path`
* `kind: "postgres"` with DSN
* `kind: "quantum_optical"` with whatever future config is required

All higher-level code (UI, LangChain, tests) must depend only on:

* The **logical Board Service API**
* The configuration specifying which backend adapter is active

---

If you’d like, next step we can sketch a minimal `BoardService` interface in Python (class or protocol) and a small factory that picks `FilesystemBoardService` or `NoSQLBoardService` based on that `crewkan.storage.kind` config, so your tests can parametrise backends cleanly.
