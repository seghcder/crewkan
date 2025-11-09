# Streamlit Coverage Limitations and Solutions

## Problem

Streamlit UI code (`crewkan_ui.py`) shows low coverage (36%) even though much of the code is executed when the UI runs. This is due to Streamlit's unique execution model.

## Why Coverage is Low

### 1. **Subprocess Execution**
When Streamlit runs, it executes in a separate process. Coverage.py doesn't track code in subprocesses unless explicitly configured.

**Example**: Playwright tests start Streamlit via `subprocess.Popen()`, so coverage doesn't track the UI code execution.

### 2. **Reactive Execution Model**
Streamlit re-runs the entire script from top to bottom on each user interaction. However:
- Some code paths only execute on specific interactions
- Session state can cause code to skip certain branches
- Widget state affects which code runs

### 3. **Framework Limitations**
- Streamlit's execution context is different from standard Python scripts
- Coverage tools may not properly track code executed in Streamlit's runtime
- Some code executes but isn't recognized by coverage tools

## Solutions Implemented

### 1. **Direct Function Testing**
We test individual UI functions directly (not via Streamlit):

```python
from crewkan.crewkan_ui import load_board, create_task, move_task
# These functions are tested directly, so coverage tracks them
```

**Coverage**: ~36% (helper functions are covered, but `main()` is not)

### 2. **Streamlit AppTest Framework**
We use Streamlit's native testing framework to execute `main()`:

```python
from streamlit.testing.v1 import AppTest

at = AppTest.from_file("crewkan/crewkan_ui.py")
at.run()  # This executes main() and tracks coverage
```

**Coverage**: Improves coverage of `main()` function execution paths.

**File**: `tests/test_streamlit_main_coverage.py`

### 3. **Comprehensive Coverage Test**
`tests/test_coverage_comprehensive.py` includes:
- Direct function calls (for helper functions)
- AppTest execution (for `main()` function)
- Error path testing
- Edge case testing

## What Gets Covered

### ✅ Covered (via direct function calls)
- `get_board_root()`
- `load_board()`
- `load_agents()`
- `iter_tasks()`
- `create_task()`
- `move_task()`
- `assign_task()`

### ⚠️ Partially Covered (via AppTest)
- `main()` function:
  - Initial page load ✅
  - Column rendering ✅
  - Form rendering ✅
  - Filesystem change detection initialization ✅
  - Error handling ✅
  - Filter rendering ✅

### ❌ Not Covered (requires user interaction)
- Form submission handling (requires actual form interaction)
- Button clicks (requires user interaction)
- Widget state changes (requires user interaction)
- Session state transitions (requires multiple interactions)

## Improving Coverage

### Option 1: Use AppTest for Interactions
```python
at = AppTest.from_file("crewkan/crewkan_ui.py")
at.run()

# Interact with form
at.text_input("Title *").input("Test Task").run()
at.form_submit_button("Create Task").click().run()
```

**Limitation**: AppTest has limited interaction capabilities.

### Option 2: Subprocess Coverage Tracking
Configure coverage to track subprocesses:

```python
cov = coverage.Coverage(
    source=["crewkan"],
    concurrency=["subprocess"],  # Track subprocesses
)
```

**Limitation**: Requires careful setup and may not work with Streamlit's execution model.

### Option 3: Accept Framework Limitations
Recognize that:
- Some code paths require actual user interaction
- Playwright tests verify functionality (even if coverage doesn't track it)
- 36% coverage for UI code is reasonable given the framework constraints

## Current Status

- **Overall Coverage**: 54%
- **UI Coverage**: 36%
- **Helper Functions**: Well covered
- **Main Function**: Partially covered via AppTest

## Recommendations

1. **Continue using AppTest** for `main()` function coverage
2. **Accept that some paths require user interaction** - these are tested via Playwright
3. **Focus on testing logic** rather than UI rendering
4. **Document coverage limitations** (this file)

## Testing Strategy

1. **Unit Tests**: Test helper functions directly (good coverage)
2. **Integration Tests**: Use AppTest for main function (partial coverage)
3. **E2E Tests**: Use Playwright for full user interactions (no coverage tracking, but functional verification)

## References

- [Streamlit Testing Documentation](https://docs.streamlit.io/develop/concepts/app-testing)
- [Coverage.py Subprocess Tracking](https://coverage.readthedocs.io/en/latest/subprocess.html)
- [Streamlit Testing Best Practices](tests/STREAMLIT_TESTING_BEST_PRACTICES.md)

