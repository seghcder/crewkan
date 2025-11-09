# CrewKan Test Suite

## Setup

### Install Test Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install test dependencies
pip install -r tests/requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Running Tests

### CLI Tests
```bash
PYTHONPATH=. python tests/test_cli.py
```

### Streamlit UI Tests (Playwright)
```bash
# Run all UI tests
PYTHONPATH=. pytest tests/test_streamlit_ui_playwright.py -v

# Run specific test
PYTHONPATH=. pytest tests/test_streamlit_ui_playwright.py::test_ui_loads -v

# Run with visible browser (for debugging)
PYTHONPATH=. pytest tests/test_streamlit_ui_playwright.py -v --headed
```

### LangChain Agent Tests
```bash
# Requires .env file with Azure OpenAI credentials
PYTHONPATH=. python tests/test_langchain_agent.py
```

### Simulation Tests
```bash
PYTHONPATH=. python tests/test_simulation.py
```

### Coverage Tests
```bash
PYTHONPATH=. python tests/test_coverage.py
```

## Test Files

- `test_cli.py` - CLI command tests (9 tests, all passing)
- `test_streamlit_ui_playwright.py` - Playwright-based UI tests
- `test_streamlit_ui_comprehensive.py` - Streamlit testing utilities (legacy)
- `test_langchain_agent.py` - LangChain integration tests
- `test_simulation.py` - Full system simulation
- `test_coverage.py` - Code coverage measurement

## Notes

- Playwright tests require a Streamlit server to be running (handled automatically by fixtures)
- UI tests create temporary boards for each test
- LangChain tests require valid Azure OpenAI credentials in `.env` file

