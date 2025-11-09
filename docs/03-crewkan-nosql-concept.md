# CrewKan NoSQL Instantiation Concept

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
