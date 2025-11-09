what should we call this system? also, do an online search and see if there is anything close to this in scope? Im also thinking that one or more agents could also create instances of this board for any subactivity - ie there is one run by the "CEO" agent for top level entity co-ordination but others may be sponteneously created and removed. all it needs is an empty directory to be specified. probably the code initially will be a git repo we can submodule into ./ext/ dir for a given org repo

-----

I’d lean toward a name that makes it obvious it’s:

* filesystem / git–native
* multi-agent / multi-board
* a kind of “OS for work” rather than just a todo list

I’ll do:

1. Name ideas (with a recommended one)
2. What’s out there that’s close in scope (from the web search)
3. How the “many boards / CEO board / sub-boards” pattern could work with empty dirs + git submodule

---

## 1. What should we call it?

Some options that fit what you’ve built so far:

### My top pick: **“AgentDeck”**

Short, pronounceable, and captures:

* “Deck” like a kanban deck / board of cards
* “Agent” foregrounds that the users are AI+humans
* Nothing major I can see using *exactly* that name in this space (there are plenty of “agent” and “deck” things, but not this specific combo as a task system).

Repo names you could use:

* `agentdeck` – core library / CLI / LangChain tools
* `agentdeck-starter` – template repo you submodule into `./ext/`
* `agentdeck-boards-<org>` – an org’s actual boards repo if you want it separate

### Other decent candidates

In case you want a different flavour:

* **OpsLoom** – evokes weaving agent work into a fabric, but “loom” is a bit busy in agent space already (Loom Agent framework, etc.). ([PyPI][1])
* **CrewKanban** – focuses more on the company-as-crew vibe, but “Crewboard / CrewBoard” is already a product in HR/yacht land. ([yachtcloud.com][2])
* **BoardFS** – very literal: board + filesystem. Great as an internal package name, maybe less fun as a product name.
* **AgentKanbanFS** – extremely descriptive, not pretty; good for the GitHub repo that’s clearly experimental.

I’d personally go with **AgentDeck** as the umbrella name and keep the internal Python package something boring like `agentdeck_fs` or `agentdeck_board`.

---

## 2. What’s already close to this idea?

From a quick sweep, here are the nearest neighbours:

### Filesystem / git-native task boards

* **Flatban** – “a filesystem-based Kanban project management system” that stores tasks as Markdown files, explicitly designed to be git-friendly and AI-assistant-friendly. It’s very close on the *filesystem + git + Kanban* axis, though it doesn’t seem focused on multi-agent orchestration plus LangChain tools per agent. ([GitHub][3])

* **dotbrd / spec** – “an open, filesystem-based” organisational spec where a directory tree encodes projects that can then be visualised as Gantt, Kanban, calendars etc. It’s more of a generic spec/format than a concrete “agents running a company” setup, but philosophically aligned. ([GitHub][4])

### Agent-centric task systems

* **ATLAS MCP server** – “Adaptive Task & Logic Automation System”, a task/project/knowledge system specifically for LLM agents with a 3-node architecture. It’s more like a server + MCP endpoint than a pure git+YAML board, but conceptually similar (agents + persistent tasks). ([GitHub][5])

* **Agentic Sync** – explicitly branded as an “agentic task management system” for developers and AI agents to collaborate, but appears more app-like and GTD-style rather than “boards encoded in the repo’s filesystem that agents can spawn ad-hoc.” ([GitHub][6])

* **LangChain Deep Agents / task_mAIstro** – LangChain has deep agents with `write_todos` and filesystem tooling that let agents create and manage todo lists in a virtual FS; task_mAIstro is an AI task manager built on LangGraph. They’re conceptually close on “agents manage tasks via tools,” but not specifically “YAML on your repo’s filesystem as the canonical board, with symlinks and git workflows.” ([GitHub][7])

### Agentic workflows + git

* **GitHub Agentic Workflows / smart-workflows** – use AI to author or steer GitHub Actions (YAML workflows) and automation across repos. Very close on “agents + git + YAML”, but they’re orchestrating CI/CD and repo automations, not modelling your org’s kanban state in the repo itself. ([GitHub Next][8])

So: the *ingredients* exist in different places, but I didn’t see something that’s:

> “Trello-like boards, defined entirely as YAML files & directories in a repo, git-first, with LangChain tools bound per agent (human or AI), and the ability for agents to spawn new boards just by choosing an empty directory.”

That combination still looks pretty fresh.

---

## 3. Multi-board / CEO board / ephemeral sub-boards

Your idea of “one board per activity, spawning boards on demand” maps really nicely onto the filesystem model.

### 3.1. Overall repo layout

Something like:

```text
org-repo/
  ext/
    agentdeck/              # git submodule with all the generic code / tools

  boards/
    ceo/                    # CEO-level coordination board
      board.yaml
      agents.yaml
      tasks/
      workspaces/
      archive/

    hospital-a-analytics/   # sub-board created by some agent for a project
      board.yaml
      agents.yaml           # or a subset + references to global agents
      tasks/
      workspaces/

    infra-migration/        # another ad-hoc board
      board.yaml
      agents.yaml
      tasks/
      workspaces/
```

You can also keep a small registry at `boards/registry.yaml`:

```yaml
boards:
  - id: "ceo"
    path: "boards/ceo"
    owner_agent: "ceo-agent"
    purpose: "Top-level cross-org coordination"
  - id: "hospital-a-analytics"
    path: "boards/hospital-a-analytics"
    owner_agent: "nuni"
    parent_board: "ceo"
  - id: "infra-migration"
    path: "boards/infra-migration"
    owner_agent: "tau"
    parent_board: "ceo"
```

The **AgentDeck core** lives in its own repo (submodule) and doesn’t care how many board roots you mount it into.

### 3.2. Board creation from an empty directory

In the core library (submodule), you already have a `BoardClient`. Add a simple:

```python
def init_board(root: Path, owner_agent_id: str, name: str, columns: list[str] | None = None):
    """
    Create a new board in `root` (must be empty or non-existent).
    Writes board.yaml, agents.yaml stubs, and creates tasks/ etc.
    """
    ...
```

Flow for an AI/human “CEO” agent spawning a sub-board:

1. Decide on a path (e.g. `boards/hospital-a-analytics`).
2. Call a LangChain tool like `create_board(board_id, path, name, owner_agent_id)`.
3. That tool:

   * Ensures the target directory is empty or creates it.
   * Writes a standard `board.yaml` template (with default columns).
   * Writes an `agents.yaml` referencing:

     * Local project agents; or
     * A subset of global agents; or
     * Just the owner + a default superagent, to keep it minimal.
4. Optionally add an entry to `boards/registry.yaml`.
5. Optionally create a CEO-board task that points at the new board:

   ```yaml
   tags: ["sub-board:hospital-a-analytics"]
   metadata:
     board_ref: "hospital-a-analytics"
   ```

From there, any agent can be pointed at:

```python
BoardClient(board_root="boards/hospital-a-analytics", agent_id="nuni")
```

and use the exact same `list_my_tasks`, `move_task`, `reassign_task` tools you already have.

### 3.3. CEO board vs sub-boards

Pattern that works nicely:

* **CEO board** handles *coordination tasks*:

  * “Spin up analytics program for Hospital A”
  * “Launch infra migration sub-program”

* Each such task, when large enough, gets its own sub-board. You can:

  * Keep the CEO task as a “parent task” with a link to the sub-board.
  * Let agents automatically update the CEO task’s comments with status summaries pulled from the sub-board (via another tool like `summarize_board_status(board_id)`).

* When a sub-board is “done”, you can:

  * Move its directory under `boards/archive/`
  * Set a flag in `boards/registry.yaml` (`status: archived`).
  * Mark the parent CEO task as `done` and add a link.

### 3.4. Git submodule story

Your instinct lines up well with how people are starting to structure agent tooling:

* `agentdeck` (core) is its own repo:

  * Python library
  * CLI
  * LangChain tools
  * Maybe a Streamlit UI

* Each org repo adds it as a submodule in `./ext/agentdeck`:

  ```bash
  git submodule add git@github.com:you/agentdeck.git ext/agentdeck
  ```

* In the org repo, agents (or devs) import from that:

  ```python
  from ext.agentdeck.board_langchain_tools import make_board_tools
  ```

* You can even standardise a small wrapper config:

  ```python
  # org_repo/agentdeck_config.py
  AGENTDECK_DEFAULT_BOARD = "boards/ceo"
  ```

So from any agent process you can mount:

```python
ceo_tools = make_board_tools("boards/ceo", agent_id="ceo-agent")
infra_tools = make_board_tools("boards/infra-migration", agent_id="tau")
```

No central DB, no migration scripts – everything is just in the repo, under version control, and boards are created/deleted by manipulating directories plus a couple of YAML files.

---

If you like, next step we can sketch:

* A `create_board` / `destroy_board` LangChain tool pair.
* And a simple “board registry” tool so the CEO agent can discover all active sub-boards and curate them.

[1]: https://pypi.org/project/loom-agent/?utm_source=chatgpt.com "loom-agent · PyPI"
[2]: https://yachtcloud.com/products/crewboard/?utm_source=chatgpt.com "Discover CrewBoard by YachtCloud | Technology for luxury"
[3]: https://github.com/gelform/flatban?utm_source=chatgpt.com "GitHub - gelform/flatban: A filesystem-based Kanban project management ..."
[4]: https://github.com/dotbrd/spec?utm_source=chatgpt.com "GitHub - dotbrd/spec: Specification for an open, filesystem-based ..."
[5]: https://github.com/cyanheads/atlas-mcp-server?utm_source=chatgpt.com "ATLAS: Task Management System - GitHub"
[6]: https://github.com/Next-AI-Labs-Inc/Agentic-Sync?utm_source=chatgpt.com "GitHub - Next-AI-Labs-Inc/Agentic-Sync: Agentic Task Management System"
[7]: https://github.com/langchain-ai/deepagents?utm_source=chatgpt.com "GitHub - langchain-ai/deepagents"
[8]: https://githubnext.com/projects/agentic-workflows/?utm_source=chatgpt.com "Agentic Workflows - GitHub Next"
