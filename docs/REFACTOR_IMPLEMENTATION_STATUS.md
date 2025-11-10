# Tasks → Issues Refactoring Implementation Status

## Strategy: Dual API Approach

To minimize risk and allow gradual migration, we'll:
1. Add new issue methods alongside existing task methods
2. Task methods will delegate to issue methods internally
3. Support both `tasks/` and `issues/` directories
4. New boards use `issues/` by default
5. Old boards continue using `tasks/` (backwards compatible)

## Phase 1: Core Infrastructure ✅

- [x] Create `issue_schema.yaml` with `issue_type` field
- [x] Add `generate_issue_id()` function (keep `generate_task_id()` for compatibility)
- [x] Update schema detection in `utils.py` to support both schemas
- [x] Add `issues_root` to BoardClient (keep `tasks_root` for compatibility)

## Phase 2: Core API Methods (In Progress)

### BoardClient Methods to Add:
- [ ] `iter_issues()` - iterate issues from issues/ directory
- [ ] `find_issue()` - find issue by ID (check issues/ first, then tasks/)
- [ ] `create_issue()` - create new issue with issue_type
- [ ] `list_my_issues()` - list issues assigned to agent
- [ ] `move_issue()` - move issue between columns
- [ ] `update_issue_field()` - update issue fields (including issue_type)
- [ ] `reassign_issue()` - reassign issue
- [ ] `get_issue_details()` - get full issue details
- [ ] `add_comment()` - works on issues (already works)
- [ ] `get_comments()` - works on issues (already works)

### Task Methods (Keep for Compatibility):
- [ ] Update `iter_tasks()` to also check `issues/` directory
- [ ] Update `find_task()` to check `issues/` first, then `tasks/`
- [ ] Update `create_task()` to delegate to `create_issue()` with default type
- [ ] Update other task methods to delegate to issue methods

## Phase 3: Board Settings

- [ ] Add `issue_filename_prefix` (default: "I")
- [ ] Add `default_issue_type` (default: "task")
- [ ] Add `issue_types` list to board settings
- [ ] Keep `task_filename_prefix` for backwards compatibility

## Phase 4: CLI Commands

- [ ] Add `cmd_new_issue()` command
- [ ] Add `cmd_move_issue()` command
- [ ] Add `cmd_assign_issue()` command
- [ ] Keep old task commands as aliases

## Phase 5: UI Updates

- [ ] Add issue type selector to create form
- [ ] Update labels: "Task" → "Issue"
- [ ] Update function names
- [ ] Display issue type in issue cards

## Phase 6: LangChain Tools

- [ ] Add new issue tools
- [ ] Keep old task tools as aliases

## Phase 7: Examples & Tests

- [ ] Update CEO delegation example
- [ ] Update all tests
- [ ] Verify backwards compatibility

## Implementation Notes

Starting with Phase 2 - adding issue methods to BoardClient that work with the new `issues/` directory structure while maintaining backwards compatibility with `tasks/`.

