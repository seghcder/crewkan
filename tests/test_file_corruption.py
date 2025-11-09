#!/usr/bin/env python3
"""
Test file corruption scenarios and recovery mechanisms.
"""

import sys
import tempfile
import shutil
from pathlib import Path
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.board_init import init_board
from crewkan.board_core import BoardClient, BoardError
from crewkan.utils import load_yaml, save_yaml, YAMLError, SchemaValidationError
from crewkan.file_locking import FileLock, LockError


def test_corrupted_board_yaml():
    """Test handling of corrupted board.yaml file."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "corrupt_board"
    
    try:
        # Initialize board
        init_board(board_dir, "test", "Test Board", "test-agent", "test-agent")
        
        # Corrupt board.yaml
        board_yaml = board_dir / "board.yaml"
        board_yaml.write_text("invalid yaml: [unclosed bracket\n", encoding="utf-8")
        
        # Try to load - should raise YAMLError
        with pytest.raises(YAMLError) as exc_info:
            load_yaml(board_yaml)
        
        assert "corrupted" in str(exc_info.value).lower() or "parsing error" in str(exc_info.value).lower()
        
        # Try to create BoardClient - should raise BoardError with context
        with pytest.raises(BoardError) as exc_info:
            BoardClient(board_dir, "test-agent")
        
        assert "board.yaml" in str(exc_info.value)
        assert "corrupted" in str(exc_info.value).lower() or "Failed to load" in str(exc_info.value)
        
    finally:
        shutil.rmtree(temp_dir)


def test_corrupted_agents_yaml():
    """Test handling of corrupted agents.yaml file."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "corrupt_agents"
    
    try:
        # Initialize board
        init_board(board_dir, "test", "Test Board", "test-agent", "test-agent")
        
        # Corrupt agents.yaml
        agents_yaml = board_dir / "agents" / "agents.yaml"
        agents_yaml.write_text("agents:\n  - id: test-agent\n    name: [unclosed\n", encoding="utf-8")
        
        # Try to load - should raise YAMLError
        with pytest.raises(YAMLError) as exc_info:
            load_yaml(agents_yaml)
        
        assert "corrupted" in str(exc_info.value).lower() or "parsing error" in str(exc_info.value).lower()
        
        # Try to create BoardClient - should raise BoardError with context
        with pytest.raises(BoardError) as exc_info:
            BoardClient(board_dir, "test-agent")
        
        assert "agents.yaml" in str(exc_info.value)
        
    finally:
        shutil.rmtree(temp_dir)


def test_corrupted_task_yaml():
    """Test handling of corrupted task YAML file."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "corrupt_task"
    
    try:
        # Initialize board and create a task
        init_board(board_dir, "test", "Test Board", "test-agent", "test-agent")
        client = BoardClient(board_dir, "test-agent")
        task_id = client.create_task("Test Task", "Description", "todo", ["test-agent"])
        
        # Find task file
        task_path = board_dir / "tasks" / "todo" / f"{task_id}.yaml"
        assert task_path.exists()
        
        # Corrupt task file
        task_path.write_text("id: T-123\n  title: [unclosed\n", encoding="utf-8")
        
        # Try to load - should raise YAMLError
        with pytest.raises(YAMLError) as exc_info:
            load_yaml(task_path)
        
        assert "corrupted" in str(exc_info.value).lower() or "parsing error" in str(exc_info.value).lower()
        
        # Try to find task - should handle gracefully
        with pytest.raises(BoardError) as exc_info:
            client.find_task(task_id)
        
        assert "not found" in str(exc_info.value).lower()
        
    finally:
        shutil.rmtree(temp_dir)


def test_empty_yaml_file():
    """Test handling of empty YAML file."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "empty_yaml"
    
    try:
        # Initialize board
        init_board(board_dir, "test", "Test Board", "test-agent", "test-agent")
        
        # Create empty board.yaml
        board_yaml = board_dir / "board.yaml"
        board_yaml.write_text("", encoding="utf-8")
        
        # Should return default or None
        result = load_yaml(board_yaml, default={})
        assert result == {}
        
    finally:
        shutil.rmtree(temp_dir)


def test_malformed_yaml_structure():
    """Test handling of YAML that parses but has wrong structure."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "malformed"
    
    try:
        # Initialize board
        init_board(board_dir, "test", "Test Board", "test-agent", "test-agent")
        
        # Create board.yaml with wrong structure (list instead of dict)
        board_yaml = board_dir / "board.yaml"
        board_yaml.write_text("- item1\n- item2\n", encoding="utf-8")
        
        # Should raise YAMLError
        with pytest.raises(YAMLError) as exc_info:
            load_yaml(board_yaml)
        
        assert "Expected dict" in str(exc_info.value)
        
    finally:
        shutil.rmtree(temp_dir)


def test_schema_validation_failure():
    """Test schema validation catches invalid data."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "schema_test"
    
    try:
        # Initialize board
        init_board(board_dir, "test", "Test Board", "test-agent", "test-agent")
        
        # Create invalid board.yaml (missing required fields)
        board_yaml = board_dir / "board.yaml"
        invalid_data = {
            "board_name": "Test",
            # Missing board_id and columns
        }
        
        # Should raise SchemaValidationError when saving with validation
        with pytest.raises(SchemaValidationError):
            save_yaml(board_yaml, invalid_data, validate_schema=True)
        
        # Should succeed without validation
        save_yaml(board_yaml, invalid_data, validate_schema=False)
        
    finally:
        shutil.rmtree(temp_dir)


def test_file_locking_prevents_race_condition():
    """Test that file locking prevents read-update-write race conditions."""
    import threading
    import time
    
    temp_dir = Path(tempfile.mkdtemp())
    test_file = temp_dir / "test.yaml"
    
    try:
        # Initial data
        initial_data = {"counter": 0, "version": 1}
        save_yaml(test_file, initial_data)
        
        # Simulate concurrent updates
        errors = []
        updates = []
        
        def update_counter(thread_id: int):
            """Update counter in a loop."""
            try:
                for i in range(10):
                    lock = FileLock(test_file, timeout=5.0)
                    with lock:
                        data = load_yaml(test_file, default={"counter": 0, "version": 1})
                        data["counter"] = data.get("counter", 0) + 1
                        data["updates"] = data.get("updates", [])
                        data["updates"].append(f"thread_{thread_id}_update_{i}")
                        save_yaml(test_file, data, use_lock=False)  # Lock already held
                        time.sleep(0.01)  # Small delay to increase chance of race condition
                    updates.append((thread_id, i))
            except Exception as e:
                errors.append((thread_id, e))
        
        # Start multiple threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=update_counter, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Check results
        final_data = load_yaml(test_file)
        assert final_data["counter"] == 30  # 3 threads * 10 updates each
        assert len(final_data.get("updates", [])) == 30
        
        # Should have no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
    finally:
        shutil.rmtree(temp_dir)


def test_stale_lock_recovery():
    """Test that stale locks are automatically recovered."""
    import os
    import time
    
    temp_dir = Path(tempfile.mkdtemp())
    test_file = temp_dir / "test.yaml"
    
    try:
        # Create a stale lock (old lock file)
        lock_file = test_file.with_suffix(test_file.suffix + ".lck")
        lock_file.write_text("1234567890\n", encoding="utf-8")  # Old timestamp
        
        # Manually set mtime to be old
        old_time = time.time() - 400  # 400 seconds ago
        os.utime(lock_file, (old_time, old_time))
        
        # Try to acquire lock - should succeed after removing stale lock
        lock = FileLock(test_file, timeout=5.0)
        assert lock.acquire(), "Should acquire lock after removing stale lock"
        lock.release()
        
    finally:
        shutil.rmtree(temp_dir)


def test_backup_creation():
    """Test that backups are created when saving files."""
    temp_dir = Path(tempfile.mkdtemp())
    test_file = temp_dir / "test.yaml"
    
    try:
        # Create initial file
        initial_data = {"data": "initial", "version": 1}
        save_yaml(test_file, initial_data, create_backup=False)
        
        # Save with backup
        new_data = {"data": "updated", "version": 1}
        save_yaml(test_file, new_data, create_backup=True)
        
        # Check backup exists
        backup_file = test_file.with_suffix(test_file.suffix + ".bak")
        assert backup_file.exists(), "Backup file should exist"
        
        # Check backup contains old data
        backup_data = load_yaml(backup_file, validate_schema=False)
        assert backup_data["data"] == "initial"
        
        # Check main file contains new data
        main_data = load_yaml(test_file)
        assert main_data["data"] == "updated"
        
    finally:
        shutil.rmtree(temp_dir)


def test_retry_logic():
    """Test that retry logic works for transient errors."""
    temp_dir = Path(tempfile.mkdtemp())
    test_file = temp_dir / "test.yaml"
    
    try:
        # This test would require mocking file operations to simulate transient failures
        # For now, just verify retry parameters are used
        data = {"test": "data", "version": 1}
        save_yaml(test_file, data, retry_on_error=True)
        
        loaded = load_yaml(test_file, retry_on_error=True)
        assert loaded == data
        
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

