"""
Base classes and interfaces for the supertool framework.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SupertoolError(Exception):
    """Base exception for supertool-related errors."""
    pass


@dataclass
class SupertoolContext:
    """
    Execution context provided to supertools.
    
    Supertools receive this context but cannot modify the board directly.
    They execute their task and return results to the agent.
    """
    workspace_path: Path
    """Path to the agent's workspace directory."""
    
    agent_id: str
    """ID of the agent executing the supertool."""
    
    issue_id: Optional[str] = None
    """ID of the issue being worked on (if any)."""
    
    issue_details: Optional[Dict[str, Any]] = None
    """Full issue details (if working on an issue)."""
    
    credentials: Dict[str, Any] = field(default_factory=dict)
    """Credentials available to this supertool execution."""
    
    constraints: Dict[str, Any] = field(default_factory=dict)
    """Execution constraints (timeouts, resource limits, etc.)."""
    
    board_root: Optional[Path] = None
    """Root directory of the board (for reference, not modification)."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata for the execution context."""


@dataclass
class SupertoolResult:
    """
    Structured result returned by supertools.
    
    Agents interpret these results and update the board accordingly.
    """
    success: bool
    """Whether the execution was successful."""
    
    output: str
    """Main output/result of the execution."""
    
    data: Optional[Dict[str, Any]] = None
    """Structured data (if any)."""
    
    artifacts: Optional[list[Path]] = None
    """Paths to any files created during execution."""
    
    error: Optional[str] = None
    """Error message if success is False."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the execution."""
    
    execution_time: Optional[float] = None
    """Execution time in seconds."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "success": self.success,
            "output": self.output,
            "data": self.data,
            "artifacts": [str(p) for p in (self.artifacts or [])],
            "error": self.error,
            "metadata": self.metadata,
            "execution_time": self.execution_time,
        }


class Supertool(ABC):
    """
    Abstract base class for all supertools.
    
    Supertools execute tasks but do not modify the board directly.
    They receive a context and return structured results.
    """
    
    def __init__(self, tool_id: str, name: str, description: str):
        """
        Initialize a supertool.
        
        Args:
            tool_id: Unique identifier for this supertool
            name: Human-readable name
            description: Description of what this supertool does
        """
        self.tool_id = tool_id
        self.name = name
        self.description = description
    
    @abstractmethod
    async def execute(self, context: SupertoolContext) -> SupertoolResult:
        """
        Execute the supertool with the given context.
        
        Args:
            context: Execution context with workspace, credentials, etc.
            
        Returns:
            SupertoolResult with execution results
            
        Raises:
            SupertoolError: If execution fails
        """
        pass
    
    def get_required_credentials(self) -> list[str]:
        """
        Return list of credential keys required by this supertool.
        
        Returns:
            List of credential key names (e.g., ["api_key", "endpoint"])
        """
        return []
    
    def validate_context(self, context: SupertoolContext) -> None:
        """
        Validate that the context has required credentials and settings.
        
        Args:
            context: Context to validate
            
        Raises:
            SupertoolError: If context is invalid
        """
        required = self.get_required_credentials()
        missing = [key for key in required if key not in context.credentials]
        if missing:
            raise SupertoolError(
                f"Missing required credentials for {self.tool_id}: {', '.join(missing)}"
            )
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Return metadata about this supertool.
        
        Returns:
            Dictionary with tool metadata
        """
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "required_credentials": self.get_required_credentials(),
        }

