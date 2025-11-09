# file_locking.py

"""
File locking mechanism using .lck files as semaphores.

This provides basic protection against read-update-write race conditions
in multi-process/multi-agent scenarios.
"""

import logging
import time
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Default timeout for acquiring locks (seconds)
DEFAULT_LOCK_TIMEOUT = 30.0
# Default retry interval (seconds)
DEFAULT_RETRY_INTERVAL = 0.1
# Maximum lock age before considering stale (seconds)
MAX_LOCK_AGE = 300  # 5 minutes


class LockError(Exception):
    """Raised when lock operations fail."""
    pass


class FileLock:
    """
    A simple file-based lock using .lck files.
    
    Usage:
        with FileLock(path):
            # Critical section
            ...
    """
    
    def __init__(
        self,
        file_path: Path,
        timeout: float = DEFAULT_LOCK_TIMEOUT,
        retry_interval: float = DEFAULT_RETRY_INTERVAL,
    ):
        self.file_path = Path(file_path).resolve()
        self.lock_path = self.file_path.with_suffix(self.file_path.suffix + ".lck")
        self.timeout = timeout
        self.retry_interval = retry_interval
    
    def _is_lock_stale(self) -> bool:
        """Check if lock file is stale (older than MAX_LOCK_AGE)."""
        if not self.lock_path.exists():
            return False
        
        try:
            lock_age = time.time() - self.lock_path.stat().st_mtime
            return lock_age > MAX_LOCK_AGE
        except OSError:
            return False
    
    def _acquire(self) -> bool:
        """Try to acquire the lock. Returns True if successful."""
        # Check if lock exists and is not stale
        if self.lock_path.exists():
            if self._is_lock_stale():
                logger.warning(
                    f"Stale lock detected for {self.file_path}, removing it. "
                    f"Lock age: {time.time() - self.lock_path.stat().st_mtime:.1f}s"
                )
                try:
                    self.lock_path.unlink()
                except OSError as e:
                    logger.warning(f"Failed to remove stale lock: {e}")
                    return False
            else:
                return False  # Lock is held by another process
        
        # Try to create lock file
        try:
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            self.lock_path.write_text(f"{time.time()}\n", encoding="utf-8")
            return True
        except OSError as e:
            logger.debug(f"Failed to create lock file: {e}")
            return False
    
    def acquire(self) -> bool:
        """
        Acquire the lock, waiting up to timeout seconds.
        Returns True if lock was acquired, False otherwise.
        """
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            if self._acquire():
                logger.debug(f"Acquired lock for {self.file_path}")
                return True
            time.sleep(self.retry_interval)
        
        logger.warning(
            f"Failed to acquire lock for {self.file_path} "
            f"within {self.timeout}s timeout"
        )
        return False
    
    def release(self):
        """Release the lock by removing the lock file."""
        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
                logger.debug(f"Released lock for {self.file_path}")
        except OSError as e:
            logger.warning(f"Failed to release lock for {self.file_path}: {e}")
            raise LockError(f"Failed to release lock: {e}")
    
    @contextmanager
    def __enter__(self):
        """Context manager entry."""
        if not self.acquire():
            raise LockError(
                f"Could not acquire lock for {self.file_path} "
                f"within {self.timeout}s"
            )
        try:
            yield self
        finally:
            self.release()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
        return False


def acquire_file_lock(
    file_path: Path,
    timeout: float = DEFAULT_LOCK_TIMEOUT,
) -> FileLock:
    """
    Acquire a lock for a file. Returns a FileLock context manager.
    
    Usage:
        with acquire_file_lock(path):
            # Critical section
            ...
    """
    return FileLock(file_path, timeout=timeout)

