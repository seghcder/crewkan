# Coverage Improvement Notes

Current coverage: ~22% → Target: 50% → Final: 90%+

## Coverage Status

- `board_core.py`: 76% - Good, but can improve
- `board_init.py`: 76% - Good
- `board_registry.py`: 62% - Needs improvement
- `crewkan_cli.py`: ~30% - CLI commands tested via subprocess
- `crewkan_setup.py`: ~40% - Setup tested in test fixtures
- `crewkan_ui.py`: ~25% - UI functions tested via BoardClient calls
- `board_langchain_tools.py`: ~35% - LangChain tools tested
- `utils.py`: ~50% - Utility functions used throughout

## Recent Improvements

1. ✅ **Abstracted Test Framework**: Created `test_abstracted.py` for unified testing
2. ✅ **Extended UI Tests**: Added `test_streamlit_extended.py` with comprehensive UI tests
3. ✅ **UI Functionality**: Added rename, tags update, comments via UI
4. ✅ **BoardClient Integration**: UI now uses BoardClient for all operations
5. ✅ **Backend Validation**: All tests verify results on backend

## Action Items for 50% Coverage

1. **More UI Tests**: 
   - ✅ Task creation
   - ✅ Task assignment
   - ✅ Task renaming
   - ✅ Tag updates
   - ✅ Comments
   - ✅ Task movement
   - ⏳ Direct UI form interaction (Playwright)

2. **CLI Testing**: 
   - ✅ Basic commands tested
   - ⏳ Edge cases and error handling

3. **LangChain Tools**: 
   - ✅ Basic tool invocation
   - ⏳ Error handling and edge cases

4. **Utils Testing**: 
   - ✅ Functions used in tests
   - ⏳ Direct unit tests

## Strategy

1. **Abstracted Testing**: Same tests run through multiple interfaces
2. **Backend Validation**: All tests verify filesystem/BoardClient state
3. **UI Integration**: UI tests use BoardClient to simulate actions, then verify in UI
4. **Coverage Measurement**: Run `test_coverage.py` regularly to track progress

## Target Progress

- Current: ~22%
- Next milestone: 50% (in progress)
- Final target: 90%+

