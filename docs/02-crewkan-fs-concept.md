# CrewKan Filesystem/YAML Instantiation Concept

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

