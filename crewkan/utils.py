# utils.py - Shared utilities for CrewKan

import logging
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import yaml
import uuid

from crewkan.file_locking import FileLock, LockError

logger = logging.getLogger(__name__)

# Schema file paths
SCHEMA_DIR = Path(__file__).parent / "schemas"
BOARD_SCHEMA = SCHEMA_DIR / "board_schema.yaml"
AGENTS_SCHEMA = SCHEMA_DIR / "agents_schema.yaml"
TASK_SCHEMA = SCHEMA_DIR / "task_schema.yaml"

# Current schema version
SCHEMA_VERSION = 1

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 0.1  # seconds


class YAMLError(Exception):
    """Raised when YAML operations fail."""
    pass


class SchemaValidationError(Exception):
    """Raised when schema validation fails."""
    pass


def now_iso():
    """Return current time in ISO format with Z suffix."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_schema(data: Dict[str, Any], schema_path: Path, file_path: Path) -> None:
    """
    Validate data against a yamale schema.
    
    Args:
        data: Data to validate
        schema_path: Path to schema file
        file_path: Path to file being validated (for error messages)
    
    Raises:
        SchemaValidationError: If validation fails
    """
    try:
        import yamale
    except ImportError:
        logger.warning("yamale not available, skipping schema validation")
        return
    
    if not schema_path.exists():
        logger.warning(f"Schema file {schema_path} not found, skipping validation")
        return
    
    try:
        schema = yamale.make_schema(schema_path)
        # Convert dict to YAML string for yamale (yamale.make_data expects a string, not a dict)
        yaml_str = yaml.dump(data, default_flow_style=False)
        yaml_data = yamale.make_data(content=yaml_str)
        yamale.validate(schema, yaml_data)
        logger.debug(f"Schema validation passed for {file_path}")
    except yamale.YamaleError as e:
        error_msg = f"Schema validation failed for {file_path}: {e}"
        logger.error(error_msg)
        raise SchemaValidationError(error_msg) from e


def _ensure_version(data: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
    """
    Ensure data has a version field. Adds version if missing.
    
    Args:
        data: Data dictionary
        file_path: Path to file (for logging)
    
    Returns:
        Data with version field
    """
    if "version" not in data:
        logger.debug(f"Adding version field to {file_path}")
        data["version"] = SCHEMA_VERSION
    return data


def load_yaml(
    path: Path,
    default=None,
    validate_schema: bool = True,
    use_lock: bool = True,
    retry_on_error: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Load YAML file with error handling, retry logic, and optional schema validation.
    
    Args:
        path: Path to YAML file
        default: Default value if file doesn't exist
        validate_schema: Whether to validate against schema
        use_lock: Whether to use file locking
        retry_on_error: Whether to retry on errors
    
    Returns:
        Loaded data or default value
    
    Raises:
        YAMLError: If file is corrupted and cannot be loaded
        SchemaValidationError: If schema validation fails
    """
    if not path.exists():
        return default
    
    # Determine schema based on file path
    schema_path = None
    if "board.yaml" in str(path):
        schema_path = BOARD_SCHEMA
    elif "agents.yaml" in str(path):
        schema_path = AGENTS_SCHEMA
    elif path.parent.name in ["todo", "doing", "done", "backlog", "blocked"]:
        schema_path = TASK_SCHEMA
    
    lock = FileLock(path) if use_lock else None
    
    def _do_load():
        try:
            with path.open("r", encoding="utf-8") as f:
                content = f.read()
            
            if not content.strip():
                logger.warning(f"Empty file {path}, returning default")
                return default
            
            try:
                data = yaml.safe_load(content)
            except yaml.YAMLError as e:
                error_msg = (
                    f"YAML parsing error in {path}: {e}\n"
                    f"File may be corrupted. Consider restoring from backup or git history."
                )
                logger.error(error_msg)
                raise YAMLError(error_msg) from e
            
            if data is None:
                logger.warning(f"YAML file {path} parsed to None, returning default")
                return default
            
            if not isinstance(data, dict):
                error_msg = f"Expected dict in {path}, got {type(data).__name__}"
                logger.error(error_msg)
                raise YAMLError(error_msg)
            
            # Ensure version field exists
            data = _ensure_version(data, path)
            
            # Validate schema if requested
            if validate_schema and schema_path:
                _validate_schema(data, schema_path, path)
            
            return data
        
        except (YAMLError, SchemaValidationError):
            raise
        except Exception as e:
            error_msg = f"Unexpected error loading {path}: {e}"
            logger.error(error_msg, exc_info=True)
            raise YAMLError(error_msg) from e
    
    # Retry logic
    if retry_on_error:
        for attempt in range(MAX_RETRIES):
            try:
                if lock:
                    with lock:
                        return _do_load()
                else:
                    return _do_load()
            except (YAMLError, SchemaValidationError):
                raise  # Don't retry on validation errors
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(
                        f"Error loading {path} (attempt {attempt + 1}/{MAX_RETRIES}): {e}. "
                        f"Retrying in {RETRY_DELAY}s..."
                    )
                    time.sleep(RETRY_DELAY)
                else:
                    error_msg = f"Failed to load {path} after {MAX_RETRIES} attempts: {e}"
                    logger.error(error_msg)
                    raise YAMLError(error_msg) from e
    else:
        if lock:
            with lock:
                return _do_load()
        else:
            return _do_load()
    
    return default


def save_yaml(
    path: Path,
    data: dict,
    validate_schema: bool = True,
    use_lock: bool = True,
    retry_on_error: bool = True,
    create_backup: bool = True,
) -> None:
    """
    Save data to YAML file with error handling, retry logic, and optional schema validation.
    
    Args:
        path: Path to YAML file
        data: Data to save
        validate_schema: Whether to validate against schema before saving
        use_lock: Whether to use file locking
        retry_on_error: Whether to retry on errors
        create_backup: Whether to create backup of existing file
    
    Raises:
        SchemaValidationError: If schema validation fails
        YAMLError: If save operation fails
    """
    # Ensure version field exists
    data = _ensure_version(data, path)
    
    # Determine schema based on file path
    schema_path = None
    if "board.yaml" in str(path):
        schema_path = BOARD_SCHEMA
    elif "agents.yaml" in str(path):
        schema_path = AGENTS_SCHEMA
    elif path.parent.name in ["todo", "doing", "done", "backlog", "blocked"]:
        schema_path = TASK_SCHEMA
    
    # Validate schema before saving
    if validate_schema and schema_path:
        _validate_schema(data, schema_path, path)
    
    lock = FileLock(path) if use_lock else None
    
    def _do_save():
        try:
            # Create backup if file exists and backup requested
            if create_backup and path.exists():
                backup_path = path.with_suffix(path.suffix + ".bak")
                try:
                    import shutil
                    shutil.copy2(path, backup_path)
                    logger.debug(f"Created backup: {backup_path}")
                except Exception as e:
                    logger.warning(f"Failed to create backup: {e}")
            
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temporary file first, then rename (atomic operation)
            temp_path = path.with_suffix(path.suffix + ".tmp")
            try:
                with temp_path.open("w", encoding="utf-8") as f:
                    yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)
                
                # Atomic rename
                temp_path.replace(path)
                logger.debug(f"Saved {path}")
            except Exception as e:
                # Clean up temp file on error
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass
                raise
            
        except Exception as e:
            error_msg = f"Failed to save {path}: {e}"
            logger.error(error_msg, exc_info=True)
            raise YAMLError(error_msg) from e
    
    # Retry logic
    if retry_on_error:
        for attempt in range(MAX_RETRIES):
            try:
                if lock:
                    with lock:
                        _do_save()
                        return
                else:
                    _do_save()
                    return
            except (SchemaValidationError, YAMLError):
                raise  # Don't retry on validation errors
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(
                        f"Error saving {path} (attempt {attempt + 1}/{MAX_RETRIES}): {e}. "
                        f"Retrying in {RETRY_DELAY}s..."
                    )
                    time.sleep(RETRY_DELAY)
                else:
                    error_msg = f"Failed to save {path} after {MAX_RETRIES} attempts: {e}"
                    logger.error(error_msg)
                    raise YAMLError(error_msg) from e
    else:
        if lock:
            with lock:
                _do_save()
        else:
            _do_save()


def generate_task_id(prefix="T"):
    """Generate a unique task ID with timestamp and random suffix."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    return f"{prefix}-{ts}-{suffix}"

