# CrewKan Agent Process and Validation

This document describes the process for agents to run, test, and validate CrewKan.

## Prerequisites

1. Python 3.8+
2. Virtual environment (recommended)
3. Dependencies installed

## Setup

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Development Dependencies

```bash
pip install coverage pytest streamlit
```

## Running Tests

### Simulation Test

Run the full simulation with arbitrary agents and tasks:

```bash
# Quick test
PYTHONPATH=. python tests/test_simulation.py --agents 5 --tasks 100 --boards 2 --cycles 20

# Full test (1000 tasks)
PYTHONPATH=. python tests/test_simulation.py --agents 10 --tasks 1000 --boards 3 --cycles 50
```

### Coverage Test

Run coverage analysis:

```bash
PYTHONPATH=. python tests/test_coverage.py
```

This will:
1. Run the simulation with coverage tracking
2. Generate a coverage report
3. Create HTML report in `htmlcov/index.html`
4. Display coverage percentage

Target: **90%+ coverage**

### Streamlit UI Test

Test the Streamlit UI:

```bash
PYTHONPATH=. python tests/test_streamlit_ui.py
```

Or manually:

```bash
# Set up a test board
python -m crewkan.crewkan_setup --root ./test_board --with-sample-agents

# Set environment variable
export CREWKAN_BOARD_ROOT=./test_board

# Run UI
streamlit run crewkan/crewkan_ui.py
```

## Requirements Validation

Follow the process in `docs/REQUIREMENTS_VALIDATION.md`:

1. Review each requirement
2. Check evidence (code location)
3. Run test steps
4. Mark as validated
5. Document any gaps

## LangChain Integration Test

### Setup

1. Create `.env` file with Azure OpenAI credentials:
```bash
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

2. Install LangChain dependencies:
```bash
pip install langchain-openai langchain
```

### Run Test

```bash
PYTHONPATH=. python tests/test_langchain_agent.py
```

## Continuous Validation

### Pre-Commit Checklist

- [ ] All tests pass
- [ ] Coverage >= 90%
- [ ] No linting errors
- [ ] Requirements validation updated
- [ ] Documentation updated

### Branch Workflow

1. Create feature branch: `git checkout -b feature/name`
2. Make changes
3. Run tests: `python tests/test_coverage.py`
4. Update requirements validation if needed
5. Commit with descriptive message
6. Push and create PR

### Main Branch Protection

- All tests must pass
- Coverage must be >= 90%
- Requirements validation must be current

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'crewkan'`:
- Ensure `PYTHONPATH=.` is set
- Or install in development mode: `pip install -e .`

### Coverage Issues

If coverage is below 90%:
1. Review `htmlcov/index.html` to see uncovered lines
2. Add test cases to cover missing code
3. Update simulation to exercise uncovered paths

### Streamlit Issues

If Streamlit tests fail:
- Ensure streamlit >= 1.28.0: `pip install 'streamlit>=1.28.0'`
- Check that test board is properly set up

## Future Enhancements

See `BACKLOG.md` for planned improvements and production readiness items.

