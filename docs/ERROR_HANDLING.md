# CrewKan Error Handling & Reliability

## Overview

CrewKan now includes comprehensive error handling, file locking, schema validation, and corruption recovery mechanisms to ensure data integrity in multi-agent environments.

## Features

### 1. File Locking

**Purpose**: Prevent read-update-write race conditions when multiple agents/processes access the same files concurrently.

**Implementation**: Uses `.lck` files as semaphores.

**Usage**:
```python
from crewkan.file_locking import FileLock

# Automatic locking in load_yaml/save_yaml (default: use_lock=True)
data = load_yaml(path, use_lock=True)
save_yaml(path, data, use_lock=True)

# Manual locking for critical sections
with FileLock(file_path, timeout=30.0):
    # Critical section
    data = load_yaml(file_path, use_lock=False)  # Lock already held
    data["counter"] += 1
    save_yaml(file_path, data, use_lock=False)
```

**Features**:
- Automatic stale lock detection (locks older than 5 minutes are removed)
- Configurable timeout (default: 30 seconds)
- Context manager support
- Thread-safe

### 2. Schema Validation

**Purpose**: Ensure YAML files conform to expected structure before saving/loading.

**Implementation**: Uses `yamale` library with schema files in `crewkan/schemas/`.

**Schema Files**:
- `board_schema.yaml` - Validates board.yaml structure
- `agents_schema.yaml` - Validates agents.yaml structure
- `task_schema.yaml` - Validates task YAML files

**Usage**:
```python
# Automatic validation (default: validate_schema=True)
data = load_yaml(path, validate_schema=True)
save_yaml(path, data, validate_schema=True)

# Disable validation if needed
data = load_yaml(path, validate_schema=False)
```

**Graceful Degradation**: If `yamale` is not installed, validation is skipped with a warning (does not fail).

### 3. Versioning

**Purpose**: Track schema versions for future migration support.

**Implementation**: All YAML files automatically get a `version` field (default: 1).

**Automatic Version Addition**:
- Missing `version` fields are automatically added on load
- Version is included in all saves

**Future Use**: Version field enables schema migration logic in future releases.

### 4. Retry Logic

**Purpose**: Handle transient file system errors (e.g., network filesystems, concurrent access).

**Configuration**:
- `MAX_RETRIES = 3` (default)
- `RETRY_DELAY = 0.1` seconds (default)

**Usage**:
```python
# Automatic retry (default: retry_on_error=True)
data = load_yaml(path, retry_on_error=True)
save_yaml(path, data, retry_on_error=True)
```

**Behavior**:
- Retries on transient errors (OSError, IOError)
- Does NOT retry on validation errors (YAMLError, SchemaValidationError)
- Logs warnings for each retry attempt

### 5. Corruption Detection & Recovery

**Purpose**: Detect and handle corrupted YAML files gracefully.

**Detection**:
- YAML parsing errors are caught and wrapped in `YAMLError` with helpful messages
- Empty files are detected and return default values
- Wrong data types (e.g., list instead of dict) are detected

**Error Messages**:
- Include file path
- Suggest recovery actions (restore from backup, git history)
- Provide context about the error

**Example**:
```python
try:
    data = load_yaml(path)
except YAMLError as e:
    # Error message includes:
    # - File path
    # - Parsing error details
    # - Recovery suggestions
    logger.error(f"Corrupted file: {e}")
    # Attempt recovery from backup
    backup_path = path.with_suffix(path.suffix + ".bak")
    if backup_path.exists():
        data = load_yaml(backup_path)
```

### 6. Backup Creation

**Purpose**: Create backups before overwriting files to enable recovery.

**Implementation**: Automatic `.bak` file creation before writes.

**Usage**:
```python
# Automatic backup (default: create_backup=True)
save_yaml(path, data, create_backup=True)

# Disable backup if needed
save_yaml(path, data, create_backup=False)
```

**Backup Location**: Same directory as original file with `.bak` extension.

### 7. Atomic Writes

**Purpose**: Prevent partial file writes from corrupting data.

**Implementation**: Write to temporary file (`.tmp`), then atomic rename.

**Process**:
1. Write data to `file.yaml.tmp`
2. Validate write succeeded
3. Atomically rename `file.yaml.tmp` → `file.yaml`
4. Clean up temp file on error

### 8. Enhanced Error Messages

**Purpose**: Provide context-rich error messages for debugging.

**Features**:
- Include file paths in all errors
- Suggest recovery actions
- Provide error context (what operation failed, why)
- Link to logs for detailed information

**Example**:
```
BoardError: Failed to load board.yaml from /path/to/board: YAML parsing error in /path/to/board/board.yaml: ...
File may be corrupted. Check logs for details.
```

## Error Types

### YAMLError
Raised when YAML parsing fails or file operations fail.

### SchemaValidationError
Raised when schema validation fails (only if `yamale` is installed and validation is enabled).

### LockError
Raised when file locking operations fail (timeout, permission issues).

### BoardError
Raised by `BoardClient` when board operations fail, wraps underlying errors with context.

## Testing

Comprehensive tests in `tests/test_file_corruption.py`:

- `test_corrupted_board_yaml()` - Corrupted board.yaml handling
- `test_corrupted_agents_yaml()` - Corrupted agents.yaml handling
- `test_corrupted_task_yaml()` - Corrupted task file handling
- `test_empty_yaml_file()` - Empty file handling
- `test_malformed_yaml_structure()` - Wrong data type handling
- `test_schema_validation_failure()` - Schema validation
- `test_file_locking_prevents_race_condition()` - Locking prevents races
- `test_stale_lock_recovery()` - Stale lock cleanup
- `test_backup_creation()` - Backup file creation
- `test_retry_logic()` - Retry mechanism

## Configuration

All error handling features can be configured:

```python
# Load with custom settings
data = load_yaml(
    path,
    validate_schema=True,    # Enable schema validation
    use_lock=True,            # Enable file locking
    retry_on_error=True,      # Enable retry logic
)

# Save with custom settings
save_yaml(
    path,
    data,
    validate_schema=True,     # Validate before saving
    use_lock=True,            # Lock during write
    retry_on_error=True,      # Retry on errors
    create_backup=True,       # Create backup
)
```

## Best Practices

1. **Always use locking for critical operations**: Prevents race conditions
2. **Enable schema validation in production**: Catches data corruption early
3. **Keep backups enabled**: Enables recovery from corruption
4. **Monitor logs**: Error messages provide context for debugging
5. **Handle YAMLError gracefully**: Implement recovery logic (backup restore, etc.)

## Future Enhancements

- [ ] Transaction-like behavior for multi-file operations
- [ ] Automatic backup rotation (keep last N backups)
- [ ] Schema migration based on version field
- [ ] Checksums for integrity verification
- [ ] Distributed locking for network filesystems

