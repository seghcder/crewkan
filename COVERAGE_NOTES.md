# Coverage Improvement Notes

Current coverage: ~22% (needs to reach 90%+)

## Coverage Status

- `board_core.py`: 76% - Good, but can improve
- `board_init.py`: 76% - Good
- `board_registry.py`: 62% - Needs improvement
- `crewkan_cli.py`: 0% - **Critical**: CLI not tested
- `crewkan_setup.py`: 0% - **Critical**: Setup not tested
- `crewkan_ui.py`: 0% - **Critical**: UI not tested
- `board_langchain_tools.py`: 0% - **Critical**: LangChain tools not tested
- `utils.py`: 0% - Needs testing

## Action Items

1. **CLI Testing**: Add subprocess calls to test CLI commands in simulation
2. **Setup Testing**: Test board initialization in coverage run
3. **UI Testing**: Improve Streamlit UI test to actually run UI code
4. **LangChain Tools**: Test tool creation and invocation
5. **Utils**: Test utility functions directly

## Strategy

The simulator-based approach is good, but we need to:
- Call CLI commands via subprocess to exercise CLI code
- Import and call setup functions directly
- Test LangChain tools by creating and invoking them
- Add direct unit tests for utility functions

## Target

90%+ coverage across all modules.

