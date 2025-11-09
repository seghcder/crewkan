# CrewKan

A task management system for hybrid human + AI agent networks.

**Version**: 0.1.0

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

## Running Tests

Run all tests with coverage:

```bash
PYTHONPATH=. python tests/test_all.py --coverage
```

Run tests without coverage:

```bash
PYTHONPATH=. python tests/test_all.py --no-coverage
```

See `tests/README.md` for individual test suites.

## Documentation

- **RELEASE_NOTES.md** - Release information and features
- **MAINTENANCE.md** - Versioning and maintenance guide
- **BACKLOG.md** - Future enhancements
- **docs/** - Detailed documentation
  - `AGENT_PROCESS.md` - Agent process guide
  - `REQUIREMENTS_VALIDATION.md` - Requirements validation
  - `01-crewkan-requirements.md` - Core requirements
  - `02-crewkan-fs-concept.md` - Filesystem implementation concept
  - `03-crewkan-nosql-concept.md` - NoSQL implementation concept

