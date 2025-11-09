# Coverage Improvement Notes

**Current Coverage: 39%** (Target: 50% → Final: 90%+)

## Coverage Status

- `board_core.py`: **79%** ✅ (Good)
- `board_init.py`: **83%** ✅ (Good)
- `board_langchain_tools.py`: **66%** ⚠️ (Needs improvement)
- `board_registry.py`: **56%** ⚠️ (Needs improvement)
- `crewkan_cli.py`: **26%** ❌ (Critical - needs direct function calls)
- `crewkan_setup.py`: **0%** ❌ (Critical - needs direct function calls)
- `crewkan_ui.py`: **14%** ❌ (Critical - needs direct function calls)
- `logging_config.py`: **0%** (New module, needs testing)
- `utils.py`: **100%** ✅ (Perfect)

## Why Coverage is Low for CLI/UI/Setup

**Problem**: These modules are called via subprocess in tests, so coverage doesn't track them.

**Solution**: 
- Created `test_coverage_comprehensive.py` which imports and calls functions directly
- This gives accurate coverage for these modules
- `test_all.py` runs both: comprehensive (for coverage) and subprocess (for actual testing)

## Recent Improvements

1. ✅ **Comprehensive Coverage Test**: Imports functions directly for accurate tracking
2. ✅ **Unified Test Runner**: `test_all.py` runs all tests with coverage
3. ✅ **Logging Added**: All modules now have logging support
4. ✅ **UI Create Task Fixed**: Now uses BoardClient properly

## Action Items for 50% Coverage

### Immediate (to reach 50%)
1. **CLI Functions**: Import and call more CLI functions directly in coverage test
2. **Setup Functions**: Import and call setup functions directly
3. **UI Functions**: Import and call more UI functions directly
4. **Logging Config**: Test logging configuration

### Medium Term (to reach 70%)
1. **Error Handling**: Test error paths in all modules
2. **Edge Cases**: Test boundary conditions
3. **Registry Operations**: Test more registry functions

### Long Term (to reach 90%+)
1. **All Code Paths**: Ensure every branch is tested
2. **Integration Tests**: Full end-to-end scenarios
3. **Performance Tests**: Load testing

## Running Coverage

```bash
# Comprehensive coverage (imports functions directly)
PYTHONPATH=. python tests/test_coverage_comprehensive.py

# All tests with coverage
PYTHONPATH=. python tests/test_all.py --coverage

# View HTML report
open htmlcov/index.html
```

## Strategy

1. **Direct Imports**: Import and call functions directly for coverage
2. **Subprocess Tests**: Keep subprocess tests for actual functionality validation
3. **Combined Approach**: Use both methods - comprehensive for coverage, subprocess for real testing

## Target Progress

- ✅ Current: **39%** (up from 25%)
- ⏳ Next milestone: **50%** (in progress)
- 🎯 Final target: **90%+**

