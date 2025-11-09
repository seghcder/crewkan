# CrewKan

A task management system for hybrid human + AI agent networks.

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

Initialize a board:

```bash
python -m crewkan.ai_board_setup --root ./ai_board --with-sample-agents
```

Use the CLI:

```bash
python -m crewkan.ai_board_cli --root ./ai_board list-agents
python -m crewkan.ai_board_cli --root ./ai_board new-task --title "Test task" --column todo
python -m crewkan.ai_board_cli --root ./ai_board list-tasks
```

