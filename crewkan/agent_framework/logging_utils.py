"""
Agent logging utilities that don't require LangChain.
"""

import logging
from pathlib import Path
from crewkan.agent_framework.workspace import AgentWorkspace


def setup_agent_logging(agent_id: str, board_root: str) -> logging.Logger:
    """
    Set up agent-specific logging to a file in the agent's workspace directory.
    
    Args:
        agent_id: Agent ID
        board_root: Board root directory
        
    Returns:
        Configured logger instance
    """
    # Get agent workspace
    workspace = AgentWorkspace(Path(board_root), agent_id)
    workspace_path = workspace.get_workspace_path()
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    # Create agent-specific logger
    agent_logger = logging.getLogger(f"crewkan.agent.{agent_id}")
    agent_logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    agent_logger.handlers = []
    
    # File handler for agent-specific log
    log_file = workspace_path / f"{agent_id}.log"
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setLevel(logging.INFO)
    
    # Console handler for immediate feedback
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    agent_logger.addHandler(file_handler)
    agent_logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    agent_logger.propagate = False
    
    root_logger = logging.getLogger(__name__)
    root_logger.info(f"Agent {agent_id} logging to {log_file}")
    
    return agent_logger

