# CrewKan

A task management system for hybrid human + AI agent networks.

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

Initialize a board:

```bash
python -m crewkan.crewkan_setup --root ./crewkan_board --with-sample-agents
```

Use the CLI:

```bash
python -m crewkan.crewkan_cli --root ./crewkan_board list-agents
python -m crewkan.crewkan_cli --root ./crewkan_board new-task --title "Test task" --column todo
python -m crewkan.crewkan_cli --root ./crewkan_board list-tasks
```

Run the Streamlit UI:

```bash
streamlit run crewkan/crewkan_ui.py
```

