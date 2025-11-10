# Refactoring Plan: Tasks → Issues with Customizable Issue Types

## Overview
Rename "tasks" to "issues" throughout the codebase and add customizable issue types (epic, user story, task, bug, etc.).

## Scope Analysis

### 1. File/Directory Structure Changes
- [ ] `tasks/` directory → `issues/`
- [ ] `task_schema.yaml` → `issue_schema.yaml`
- [ ] Function names: `generate_task_id` → `generate_issue_id`
- [ ] File prefix: `task_filename_prefix` → `issue_filename_prefix` (default: "I" instead of "T")

### 2. Core API Changes (board_core.py)
- [ ] `create_task()` → `create_issue()`
- [ ] `find_task()` → `find_issue()`
- [ ] `iter_tasks()` → `iter_issues()`
- [ ] `list_my_tasks()` → `list_my_issues()`
- [ ] `move_task()` → `move_issue()`
- [ ] `update_task_field()` → `update_issue_field()`
- [ ] `reassign_task()` → `reassign_issue()`
- [ ] `get_task_details()` → `get_issue_details()`
- [ ] `add_comment()` (stays same, but works on issues)
- [ ] `get_comments()` (stays same, but works on issues)
- [ ] `tasks_root` → `issues_root`
- [ ] Variable names: `task_id` → `issue_id`, `task` → `issue`

### 3. Schema Changes
- [ ] `task_schema.yaml` → `issue_schema.yaml`
- [ ] Add `issue_type` field (enum: epic, user_story, task, bug, feature, etc.)
- [ ] Update schema validation
- [ ] Update `utils.py` to recognize `issues/` directory

### 4. Board Settings Changes
- [ ] `task_filename_prefix` → `issue_filename_prefix`
- [ ] Add `default_issue_type` setting
- [ ] Add `issue_types` list to board settings (customizable types)

### 5. CLI Changes (crewkan_cli.py)
- [ ] `cmd_new_task()` → `cmd_new_issue()`
- [ ] `cmd_start_task()` → `cmd_start_issue()`
- [ ] `cmd_stop_task()` → `cmd_stop_issue()`
- [ ] `cmd_move_task()` → `cmd_move_issue()`
- [ ] `cmd_assign_task()` → `cmd_assign_issue()`
- [ ] Update all command help text

### 6. UI Changes (crewkan_ui.py)
- [ ] `create_task()` → `create_issue()`
- [ ] `move_task()` → `move_issue()`
- [ ] `assign_task()` → `assign_issue()`
- [ ] All UI labels: "Task" → "Issue"
- [ ] Add issue type selector in create form
- [ ] Display issue type in issue cards
- [ ] Update task details page → issue details page

### 7. LangChain Tools (board_langchain_tools.py)
- [ ] All tool names: `*_task` → `*_issue`
- [ ] Tool descriptions updated
- [ ] Input schemas updated

### 8. Examples
- [ ] `langgraph_ceo_delegation.py`: Update all task references
- [ ] `test_work_resumption.py`: Update references
- [ ] All examples updated

### 9. Tests
- [ ] All test files updated
- [ ] Test function names updated
- [ ] Test data updated

### 10. Documentation
- [ ] All docs updated (requirements, concepts, etc.)
- [ ] README updated
- [ ] API documentation updated

## Implementation Strategy

### Phase 1: Core Infrastructure
1. Update schema to add `issue_type` field
2. Update `utils.py` for issue ID generation
3. Rename core methods in `board_core.py`
4. Update directory structure references

### Phase 2: API & CLI
1. Update all BoardClient methods
2. Update CLI commands
3. Update LangChain tools

### Phase 3: UI
1. Update UI functions
2. Add issue type selector
3. Update all labels and displays

### Phase 4: Examples & Tests
1. Update all examples
2. Update all tests
3. Verify everything works

### Phase 5: Documentation
1. Update all documentation
2. Update README
3. Migration guide if needed

## Issue Types Configuration

### Default Issue Types
- `epic`: Large feature or initiative
- `user_story`: User-facing feature
- `task`: General work item
- `bug`: Defect or issue
- `feature`: New functionality
- `improvement`: Enhancement to existing feature

### Configuration
- Board settings: `issue_types` list (customizable)
- Default: `default_issue_type` setting (default: "task")
- Schema: `issue_type: enum(...)` with required=False (defaults to "task")

## Backwards Compatibility

### Migration Path
- Keep `tasks/` directory support for existing boards (read-only or migration)
- Or: Provide migration script to rename `tasks/` → `issues/`
- Update file prefix from "T-" to "I-" for new issues

### Compatibility Layer (Optional)
- Keep old method names as aliases that call new methods
- Deprecation warnings for old names

## Testing Checklist

- [ ] Create issue with different types
- [ ] List issues
- [ ] Move issues between columns
- [ ] Update issue fields
- [ ] Reassign issues
- [ ] Add comments to issues
- [ ] Get issue details
- [ ] UI create/update/display
- [ ] CLI commands
- [ ] LangChain tools
- [ ] CEO delegation example
- [ ] All existing tests pass

## Risk Assessment

**High Risk:**
- Breaking existing boards (need migration)
- Breaking existing code using API
- Test failures

**Mitigation:**
- Comprehensive testing
- Migration script
- Backwards compatibility layer
- Clear documentation

