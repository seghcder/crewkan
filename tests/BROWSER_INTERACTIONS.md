# Browser Interaction Tests - Where We Fill Fields and Click Buttons

This document shows exactly where in the test code we're interacting with the browser (filling form fields, clicking buttons) using Playwright.

## Test Files with Browser Interactions

### 1. `test_streamlit_ui_playwright.py` - Direct Browser Interactions

**Lines 107-183**: `test_create_task_via_ui()` function

This is the main test that actually fills in form fields and clicks buttons:

```python
# Line 109: Navigate to the page
page.goto(streamlit_server)

# Lines 120-135: Find the title input field using multiple selectors
title_selectors = [
    'input[aria-label*="Title" i]',
    'input[placeholder*="Title" i]',
    'textarea[aria-label*="Title" i]',
    'input[type="text"]',
    '.stTextInput input',
]

title_input = None
for selector in title_selectors:
    try:
        title_input = page.wait_for_selector(selector, timeout=2000)
        if title_input:
            break
    except:
        continue

# Line 139: FILL IN THE TITLE FIELD
if title_input:
    title_input.fill("Test Task from Playwright")
    page.wait_for_timeout(500)

# Lines 143-152: Find and fill description field
desc_selectors = [
    'textarea[aria-label*="Description" i]',
    'textarea[placeholder*="Description" i]',
    '.stTextArea textarea',
]
for selector in desc_selectors:
    desc_input = page.query_selector(selector)
    if desc_input:
        # Line 151: FILL IN THE DESCRIPTION FIELD
        desc_input.fill("This is a test task created via Playwright")
        break

# Lines 154-164: Find and click submit button
submit_selectors = [
    'button:has-text("Create task")',
    'button:has-text("Create")',
    'button[type="submit"]',
    'form button[type="submit"]',
]
for selector in submit_selectors:
    submit_button = page.query_selector(selector)
    if submit_button:
        # Line 164: CLICK THE SUBMIT BUTTON
        submit_button.click()
        page.wait_for_timeout(3000)  # Wait for form submission
```

**Key Browser Interaction Lines:**
- **Line 139**: `title_input.fill("Test Task from Playwright")` - Fills title field
- **Line 151**: `desc_input.fill("...")` - Fills description field  
- **Line 164**: `submit_button.click()` - Clicks the submit button

### 2. `test_streamlit_extended.py` - Uses BoardClient (No Direct Browser Interaction)

**Lines 85-116**: `test_create_task_via_ui()`

This test does NOT fill in form fields directly. Instead, it:
- Uses `BoardClient` to create tasks (line 92-99)
- Then verifies the task appears in the UI (line 102-105)

```python
# Line 92-99: Creates task via BoardClient (backend), not browser
client = BoardClient(test_board, "nuni")
task_id = client.create_task(
    title="UI Test Task",
    description="Created via UI test",
    column="todo",
    assignees=["nuni"],
    tags=["test", "ui"],
)

# Line 102: Reloads page to see the task
page.reload()
```

**Note**: This test doesn't actually test the form submission - it tests that tasks created via backend appear in the UI.

### 3. `test_streamlit_ui_comprehensive.py` - Uses AppTest (Different Approach)

**Lines 42-90**: `test_ui_create_task()`

This uses Streamlit's `AppTest` API (not Playwright), which simulates UI interactions:

```python
# Lines 63-70: Fill in form using AppTest API
with at.sidebar.form("new_task_form"):
    at.text_input("Title").input("Test Task from UI").run()  # Fill title
    at.text_area("Description").input("This is a test task").run()  # Fill description
    at.selectbox("Column").select("todo").run()  # Select column
    at.selectbox("Priority").select("high").run()  # Select priority
    at.text_input("Tags (comma separated)").input("test,ui").run()  # Fill tags
    at.multiselect("Assignees").select(["nuni"]).run()  # Select assignees
    at.form_submit_button("Create task").click().run()  # Click submit
```

**Key Interaction Lines:**
- **Line 64**: `at.text_input("Title").input("...")` - Fills title
- **Line 65**: `at.text_area("Description").input("...")` - Fills description
- **Line 70**: `at.form_submit_button("Create task").click()` - Clicks submit

### 4. `test_abstracted.py` - StreamlitInterface (Partial Implementation)

**Lines 246-287**: `StreamlitInterface.create_task()`

This class is meant to interact with the UI, but currently has a fallback:

```python
# Lines 260-261: Attempts to find and fill title field
title_input = self.page.wait_for_selector('input[type="text"], .stTextInput input', timeout=5000)
title_input.fill(title)

# Lines 264-266: Attempts to fill description
desc_input = self.page.query_selector('textarea')
if desc_input:
    desc_input.fill(f"Test task: {title}")

# Lines 270-278: FALLBACK - Uses BoardClient instead of completing form
# This is because Streamlit selectboxes are hard to interact with via Playwright
client = ctx.get_client(...)
task_id = client.create_task(...)  # Creates via backend, not form
```

## Summary

**Tests that actually fill form fields and click buttons:**

1. ✅ **`test_streamlit_ui_playwright.py`** (lines 139, 151, 164)
   - Uses Playwright directly
   - Fills title, description
   - Clicks submit button
   - **This is the most complete browser interaction test**

2. ✅ **`test_streamlit_ui_comprehensive.py`** (lines 64-70)
   - Uses Streamlit's AppTest API
   - Fills all form fields
   - Clicks submit
   - **This is a different testing approach (not real browser)**

**Tests that DON'T fill form fields:**

1. ❌ **`test_streamlit_extended.py`**
   - Uses BoardClient (backend) instead
   - Only verifies UI displays tasks

2. ⚠️ **`test_abstracted.py` StreamlitInterface**
   - Attempts to fill fields but falls back to BoardClient
   - Incomplete implementation

## Recommendation

To properly test the create task form, we should:
1. Complete the implementation in `test_streamlit_ui_playwright.py` to handle all form fields
2. Or improve `test_streamlit_extended.py` to actually fill in the form instead of using BoardClient
3. The form field selectors may need updating based on the current UI structure

