"""
Logging configuration for CrewKan.

Sets up Python's native logging with appropriate levels and formatting.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level=logging.INFO,
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None,
) -> None:
    """
    Set up logging configuration for CrewKan.
    
    Args:
        level: Logging level (default: INFO)
        log_file: Optional file to write logs to
        format_string: Optional custom format string
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    handlers = [logging.StreamHandler(sys.stderr)]
    
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=handlers,
    )
    
    # Set specific loggers
    logging.getLogger("crewkan").setLevel(level)
    
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given name."""
    return logging.getLogger(f"crewkan.{name}")

