"""
Workspace management for agent isolation.
"""

import logging
from pathlib import Path
from typing import Optional
import shutil

logger = logging.getLogger(__name__)


class AgentWorkspace:
    """
    Manages per-agent workspace directories.
    
    Provides isolation for supertool execution and integration with
    CrewKan's existing workspace system.
    """
    
    def __init__(self, board_root: Path, agent_id: str):
        """
        Initialize workspace manager for an agent.
        
        Args:
            board_root: Root directory of the board
            agent_id: ID of the agent
        """
        self.board_root = Path(board_root).resolve()
        self.agent_id = agent_id
        self.workspace_root = self.board_root / "workspaces" / agent_id
        self.workspace_root.mkdir(parents=True, exist_ok=True)
    
    def get_workspace_path(self) -> Path:
        """
        Get the workspace root path for this agent.
        
        Returns:
            Path to agent's workspace directory
        """
        return self.workspace_root
    
    def get_execution_path(self, execution_id: Optional[str] = None) -> Path:
        """
        Get a path for a specific execution (for isolation).
        
        Args:
            execution_id: Optional execution identifier
            
        Returns:
            Path to execution directory
        """
        if execution_id:
            exec_path = self.workspace_root / "executions" / execution_id
            exec_path.mkdir(parents=True, exist_ok=True)
            return exec_path
        return self.workspace_root
    
    def cleanup_execution(self, execution_id: str, keep_artifacts: bool = False) -> None:
        """
        Clean up an execution directory.
        
        Args:
            execution_id: Execution identifier
            keep_artifacts: If True, keep artifacts subdirectory
        """
        exec_path = self.workspace_root / "executions" / execution_id
        if not exec_path.exists():
            return
        
        if keep_artifacts and (exec_path / "artifacts").exists():
            # Move artifacts to workspace root
            artifacts_dest = self.workspace_root / "artifacts" / execution_id
            artifacts_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(exec_path / "artifacts"), str(artifacts_dest))
        
        shutil.rmtree(exec_path)
        logger.debug(f"Cleaned up execution directory: {execution_id}")
    
    def ensure_artifacts_dir(self, execution_id: Optional[str] = None) -> Path:
        """
        Ensure an artifacts directory exists and return its path.
        
        Args:
            execution_id: Optional execution identifier
            
        Returns:
            Path to artifacts directory
        """
        if execution_id:
            artifacts_path = self.get_execution_path(execution_id) / "artifacts"
        else:
            artifacts_path = self.workspace_root / "artifacts"
        
        artifacts_path.mkdir(parents=True, exist_ok=True)
        return artifacts_path
    
    def list_artifacts(self, execution_id: Optional[str] = None) -> list[Path]:
        """
        List all artifacts in the workspace.
        
        Args:
            execution_id: Optional execution identifier
            
        Returns:
            List of artifact paths
        """
        if execution_id:
            artifacts_path = self.get_execution_path(execution_id) / "artifacts"
        else:
            artifacts_path = self.workspace_root / "artifacts"
        
        if not artifacts_path.exists():
            return []
        
        return list(artifacts_path.rglob("*"))
    
    def get_workspace_info(self) -> dict:
        """
        Get information about the workspace.
        
        Returns:
            Dictionary with workspace information
        """
        return {
            "agent_id": self.agent_id,
            "workspace_path": str(self.workspace_root),
            "exists": self.workspace_root.exists(),
            "size": self._get_dir_size(self.workspace_root) if self.workspace_root.exists() else 0,
        }
    
    def _get_dir_size(self, path: Path) -> int:
        """Calculate total size of directory in bytes."""
        total = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    total += entry.stat().st_size
        except Exception as e:
            logger.warning(f"Error calculating directory size: {e}")
        return total




