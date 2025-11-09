# Streamlit UI Testing Best Practices

Based on research and our experience with CrewKan form submission bugs.

## Key Principles

### 1. **Test Real User Interactions**
- Use Playwright for browser-based testing (real user simulation)
- Use AppTest for unit-style testing (faster but may miss browser issues)
- Don't bypass the UI (e.g., using BoardClient directly) unless testing backend separately

### 2. **Verify Form Submission Flow**
- Check that form submission is detected (`if submitted:` triggers)
- Verify form values are available when processing
- Check for success/error messages in UI
- Verify backend processing (check logs or filesystem)

### 3. **Handle Streamlit's Form Behavior**
- `clear_on_submit=True`: Form values cleared AFTER form block runs
  - Capture values immediately inside `if submitted:` block
  - Don't rely on form values after the form block
- Form submitter key persists in session state
  - Clear it after processing to avoid duplicate submissions
  - Check both `submitted` and session state key

### 4. **Wait for Async Operations**
- Streamlit reruns are async - wait for page updates
- Check for success indicators (messages, task appearing)
- Use polling with timeout instead of fixed waits

### 5. **Comprehensive Logging**
- Log all form interactions
- Log form submission detection
- Log backend processing
- Save logs to files for debugging

## Testing Checklist

### Form Submission Test Should:
- [ ] Fill ALL form fields (not just title/description)
- [ ] Click submit button
- [ ] Wait for form processing (polling, not fixed timeout)
- [ ] Verify task count increased
- [ ] Verify task exists in filesystem
- [ ] Verify task has correct values
- [ ] Check for success message in UI
- [ ] Verify form was cleared (optional - depends on UX)
- [ ] Check logs for form submission indicators

### Error Handling Test Should:
- [ ] Test empty required fields
- [ ] Test invalid values
- [ ] Verify error messages appear
- [ ] Verify task was NOT created on error

## Common Pitfalls

### 1. **Not Capturing Form Values**
```python
# ❌ BAD - values cleared before processing
if submitted:
    # title might be empty here if clear_on_submit=True
    create_task(title, ...)

# ✅ GOOD - capture immediately
if submitted:
    captured_title = title  # Capture before form clears
    create_task(captured_title, ...)
```

### 2. **Not Waiting for Processing**
```python
# ❌ BAD - fixed timeout
submit_button.click()
page.wait_for_timeout(3000)  # Might not be enough

# ✅ GOOD - poll for success
submit_button.click()
for i in range(10):
    if "Created task" in page.inner_text("body"):
        break
    page.wait_for_timeout(500)
```

### 3. **Not Verifying Submission**
```python
# ❌ BAD - only check end result
assert task_exists  # Doesn't verify form worked

# ✅ GOOD - verify process
assert task_count_increased
assert success_message_shown
assert task_has_correct_values
```

### 4. **Bypassing Form Submission**
```python
# ❌ BAD - bypasses form entirely
client.create_task(...)  # Doesn't test form

# ✅ GOOD - test actual form
fill_form_fields()
click_submit()
verify_task_created()
```

## Recommended Test Structure

```python
def test_form_submission():
    # 1. Setup
    page.goto(server)
    wait_for_page_load()
    
    # 2. Count before
    tasks_before = count_tasks()
    
    # 3. Fill form
    fill_all_form_fields()
    take_screenshot("before_submit")
    
    # 4. Submit
    click_submit_button()
    
    # 5. Wait for processing (polling)
    wait_for_success_indicator()
    take_screenshot("after_submit")
    
    # 6. Verify
    tasks_after = count_tasks()
    assert tasks_after > tasks_before
    assert task_exists_with_correct_values()
    assert success_message_shown()
    
    # 7. Check logs
    assert "FORM SUBMITTED" in log_file
    assert "create_task()" in log_file
```

## Logging in Tests

```python
# Set up logging
log_file = Path("tmp/test.log")
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[logging.FileHandler(log_file)]
)

# In test
logger.info("Starting form submission test")
logger.info(f"Filled title: {title}")
logger.info("Clicked submit")
logger.info(f"Tasks before: {before}, after: {after}")

# Verify logs
with open(log_file) as f:
    assert "FORM SUBMITTED" in f.read()
```

## References

- Streamlit App Testing: https://docs.streamlit.io/develop/concepts/app-testing
- Playwright Best Practices: https://playwright.dev/python/docs/best-practices
- Streamlit Forms: https://docs.streamlit.io/develop/api-reference/widgets/st.form

