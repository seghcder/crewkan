#!/usr/bin/env python3
"""
Test agent logging setup without requiring LangChain.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.agent_framework.logging_utils import setup_agent_logging


def test_logging(agent_id: str, board_root: str):
    """Test that agent logging works."""
    print(f"Testing logging for agent: {agent_id}")
    print(f"Board root: {board_root}")
    print()
    
    # Set up logging
    agent_logger = setup_agent_logging(agent_id, board_root)
    
    # Test logging
    agent_logger.info("Test log message 1")
    agent_logger.info("Test log message 2")
    agent_logger.warning("Test warning message")
    agent_logger.error("Test error message")
    
    # Check log file
    from crewkan.agent_framework.workspace import AgentWorkspace
    workspace = AgentWorkspace(Path(board_root), agent_id)
    workspace_path = workspace.get_workspace_path()
    log_file = workspace_path / f"{agent_id}.log"
    
    print(f"Log file: {log_file}")
    print(f"Log file exists: {log_file.exists()}")
    
    if log_file.exists():
        print("\nLog file contents:")
        print("-" * 60)
        print(log_file.read_text())
        print("-" * 60)
        print("\n✓ Logging test passed!")
    else:
        print("\n✗ Log file was not created")
    
    return log_file.exists()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test agent logging")
    parser.add_argument(
        "--board-root",
        type=str,
        default="boards/crewkanteam",
        help="Board root directory"
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        default="docs",
        help="Agent ID to test"
    )
    
    args = parser.parse_args()
    
    success = test_logging(args.agent_id, args.board_root)
    sys.exit(0 if success else 1)

