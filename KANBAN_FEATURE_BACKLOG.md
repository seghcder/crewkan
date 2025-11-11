# Kanban Component Feature Backlog

Based on `streamlit-kanban-board-goviceversa` capabilities and CrewKan requirements from `docs/01-crewkan-requirements.md`.

## Current Implementation Status

✅ **Implemented:**
- Basic drag-and-drop between columns
- Task display with title, ID, assignees, priority, tags
- Click to view task details
- Full-screen kanban board (no sidebar)
- Modal for creating new tasks
- Refresh functionality
- Filesystem change detection

## Potential Features to Explore

### 1. Role-Based Permissions & Access Control
**Requirement:** Section 3.1 (Agent), Section 4.1 (Agent Management)

**Component Feature:** `permission_matrix`, `user_info` with role-based permissions

**Implementation Ideas:**
- Map CrewKan agent roles to component's permission system
- Restrict drag-drop based on agent permissions
- Show/hide tasks based on agent access
- Implement "superagent" escalation permissions

**Priority:** Medium
**Effort:** Medium

---

### 2. WIP Limits Enforcement
**Requirement:** Section 3.2 (Board columns with `wip_limit`)

**Component Feature:** Visual indicators, validation functions

**Implementation Ideas:**
- Display WIP limit count on column headers
- Warn when dragging task would exceed WIP limit
- Block drag-drop if WIP limit reached (via `drag_validation_function`)
- Visual indicators (color coding) for columns at/over limit

**Priority:** High
**Effort:** Low-Medium

---

### 3. Business Rules Engine
**Requirement:** Section 4.3 (Task Lifecycle), Section 4.5 (Multi-Board Orchestration)

**Component Feature:** `business_rules` parameter

**Implementation Ideas:**
- Enforce column transition rules (e.g., can't skip from "todo" to "done")
- Auto-assign tasks based on rules
- Auto-move tasks based on conditions (e.g., all dependencies complete)
- Multi-board orchestration rules (CEO board → sub-board transitions)

**Priority:** Medium
**Effort:** High

---

### 4. Advanced Filtering & Search
**Requirement:** Section 4.3 (Query tasks by board, column, assignee, priority, tags)

**Component Feature:** Built-in search/filter UI in component

**Implementation Ideas:**
- Filter by agent (already in component UI)
- Filter by priority, tags, due date
- Search by task title/description
- Save filter presets

**Priority:** Medium
**Effort:** Low

---

### 5. Task Priority & Status Indicators
**Requirement:** Section 3.3 (Task priority, status)

**Component Feature:** Visual hints, color coding, badges

**Implementation Ideas:**
- Color-code cards by priority (high=red, medium=yellow, low=green)
- Show priority badges on cards
- Visual indicators for blocked tasks
- Due date warnings (red for overdue, yellow for soon)

**Priority:** Low-Medium
**Effort:** Low

---

### 6. Drag Validation & Restrictions
**Requirement:** Section 4.3 (Move task between columns with validation)

**Component Feature:** `drag_validation_function`, `drag_restrictions`

**Implementation Ideas:**
- Validate dependencies before allowing move to "doing"
- Prevent moving blocked tasks
- Require certain fields (e.g., assignee) before moving to "doing"
- Custom validation messages

**Priority:** Medium
**Effort:** Medium

---

### 7. Stage Visibility Control
**Requirement:** Section 4.2 (Archive boards, hide columns)

**Component Feature:** `default_visible_stages`

**Implementation Ideas:**
- Hide archived columns
- Show/hide columns based on user preferences
- Collapsible columns
- Custom column visibility per agent

**Priority:** Low
**Effort:** Low

---

### 8. Task Details in Card Tooltips
**Requirement:** Section 3.3 (Task attributes: description, assignees, tags, due_date)

**Component Feature:** `show_tooltips=True` (already enabled)

**Implementation Ideas:**
- Enhanced tooltips showing full task details on hover
- Quick preview of description, assignees, tags
- Due date display in tooltip
- Click-to-expand card details

**Priority:** Low
**Effort:** Low

---

### 9. Multi-Board View
**Requirement:** Section 3.5 (Board Registry and Hierarchy), Section 4.5 (Multi-Board Orchestration)

**Component Feature:** Multiple board instances

**Implementation Ideas:**
- Tab-based view for multiple boards
- Parent-child board relationships visualization
- Cross-board task references
- Summary view of sub-board status

**Priority:** Low (future)
**Effort:** High

---

### 10. Workspace Integration
**Requirement:** Section 3.4 (Workspace / Working Set), Section 4.4 (Workspaces)

**Component Feature:** Custom filtering, visual indicators

**Implementation Ideas:**
- Highlight tasks in agent's workspace
- Filter view to show only workspace tasks
- Visual indicator (badge/icon) for workspace tasks
- Quick "start work" / "stop work" actions

**Priority:** Medium
**Effort:** Medium

---

### 11. Task Assignment UI
**Requirement:** Section 4.3 (Assign / reassign tasks)

**Component Feature:** Custom actions, modal dialogs

**Implementation Ideas:**
- Right-click context menu for assignment
- Drag task to agent avatar to assign
- Quick assign buttons on cards
- Bulk assignment

**Priority:** Medium
**Effort:** Medium

---

### 12. Comments & Activity Feed
**Requirement:** Section 4.3 (Comment on tasks)

**Component Feature:** Custom card rendering, modals

**Implementation Ideas:**
- Show comment count badge on cards
- Quick comment add from card
- Activity feed in sidebar (when enabled)
- @mention agents in comments

**Priority:** Low-Medium
**Effort:** Medium

---

### 13. Dependencies Visualization
**Requirement:** Section 3.3 (Task dependencies)

**Component Feature:** Custom rendering, visual hints

**Implementation Ideas:**
- Show dependency indicators on cards
- Visual links between dependent tasks
- Block drag if dependencies not met
- Dependency graph view

**Priority:** Medium
**Effort:** High

---

### 14. Bulk Operations
**Requirement:** Section 4.3 (Query tasks with pagination)

**Component Feature:** Selection, batch operations

**Implementation Ideas:**
- Multi-select tasks
- Bulk move, assign, tag
- Bulk archive/delete
- Export selected tasks

**Priority:** Low
**Effort:** Medium

---

### 15. Custom Column Colors & Styling
**Requirement:** Section 3.2 (Custom columns)

**Component Feature:** `stages` with custom colors

**Implementation Ideas:**
- User-configurable column colors
- Board-specific color schemes
- Dark/light theme support
- Custom card styling per column

**Priority:** Low
**Effort:** Low

---

### 16. Task Templates
**Requirement:** Section 4.3 (Create task with defaults)

**Component Feature:** Pre-filled forms, templates

**Implementation Ideas:**
- Task templates for common task types
- Quick create with template
- Default values per column
- Clone existing task

**Priority:** Low
**Effort:** Low-Medium

---

### 17. Analytics & Reporting
**Requirement:** Section 4.2 (Archive boards for reporting)

**Component Feature:** Data export, statistics

**Implementation Ideas:**
- Column statistics (task count, average time)
- Burndown charts
- Agent workload visualization
- Export board data for reporting

**Priority:** Low (future)
**Effort:** High

---

### 18. Real-time Collaboration
**Requirement:** Section 6 (Non-functional: Performance, Observability)

**Component Feature:** WebSocket integration (if component supports)

**Implementation Ideas:**
- Real-time updates when other users move tasks
- Presence indicators (who's viewing board)
- Live collaboration on tasks
- Conflict resolution for simultaneous edits

**Priority:** Low (future)
**Effort:** Very High

---

## Implementation Priority Summary

**High Priority:**
1. WIP Limits Enforcement (#2)

**Medium Priority:**
2. Role-Based Permissions (#1)
3. Business Rules Engine (#3)
4. Advanced Filtering & Search (#4)
5. Drag Validation & Restrictions (#6)
6. Workspace Integration (#10)
7. Task Assignment UI (#11)
8. Dependencies Visualization (#13)

**Low Priority:**
9. Task Priority & Status Indicators (#5)
10. Stage Visibility Control (#7)
11. Task Details in Card Tooltips (#8)
12. Comments & Activity Feed (#12)
13. Bulk Operations (#14)
14. Custom Column Colors & Styling (#15)
15. Task Templates (#16)

**Future:**
16. Multi-Board View (#9)
17. Analytics & Reporting (#17)
18. Real-time Collaboration (#18)

---

## Notes

- Component documentation: https://pypi.org/project/streamlit-kanban-board-goviceversa/
- Component uses DLA V2 permissions architecture (pre-computed permissions)
- Component supports custom validation functions and business rules
- Many features require understanding component's React implementation
- Some features may require component modifications or custom Streamlit components

