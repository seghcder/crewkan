"""
Supertool executor with permission validation and constraint enforcement.
"""

import logging
import asyncio
import time
from pathlib import Path
from typing import Optional, Dict, Any
from crewkan.agent_framework.base import (
    Supertool,
    SupertoolContext,
    SupertoolResult,
    SupertoolError,
)
from crewkan.agent_framework.registry import get_registry
from crewkan.agent_framework.workspace import AgentWorkspace
from crewkan.agent_framework.credentials import CredentialManager
from crewkan.board_core import BoardClient

logger = logging.getLogger(__name__)


class SupertoolExecutor:
    """
    Executes supertools with permission validation and constraint enforcement.
    
    Responsibilities:
    - Validate agent has permission to use the supertool
    - Enforce execution constraints (timeouts, resource limits)
    - Manage workspace isolation
    - Inject credentials into context
    - Handle errors and return structured results
    """
    
    def __init__(self, board_root: Path, agent_id: str):
        """
        Initialize executor for an agent.
        
        Args:
            board_root: Root directory of the board
            agent_id: ID of the agent
        """
        self.board_root = Path(board_root).resolve()
        self.agent_id = agent_id
        self.board_client = BoardClient(self.board_root, agent_id)
        self.workspace = AgentWorkspace(self.board_root, agent_id)
        self.credential_manager = CredentialManager(self.board_root)
        self.registry = get_registry()
    
    def can_use_tool(self, tool_id: str) -> bool:
        """
        Check if agent has permission to use a supertool.
        
        Args:
            tool_id: Supertool identifier
            
        Returns:
            True if agent can use the tool
        """
        agent = self.board_client.get_agent(self.agent_id)
        if not agent:
            return False
        
        # Check if tool is in agent's allowed supertools
        supertools_config = agent.get("supertools", {})
        allowed = supertools_config.get("allowed", [])
        
        # If no supertools configured, agent has no access
        if allowed is None:
            return False
        
        # Empty list means no access
        if isinstance(allowed, list) and len(allowed) == 0:
            return False
        
        # Check if tool_id is in allowed list
        return tool_id in allowed
    
    def get_agent_constraints(self) -> Dict[str, Any]:
        """
        Get execution constraints for the agent.
        
        Returns:
            Dictionary of constraints
        """
        agent = self.board_client.get_agent(self.agent_id)
        if not agent:
            return {}
        
        supertools_config = agent.get("supertools", {})
        return supertools_config.get("constraints", {})
    
    async def execute(
        self,
        tool_id: str,
        issue_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> SupertoolResult:
        """
        Execute a supertool.
        
        Args:
            tool_id: Supertool identifier
            issue_id: Optional issue ID being worked on
            execution_id: Optional execution identifier for isolation
            additional_context: Optional additional context data
            
        Returns:
            SupertoolResult with execution results
            
        Raises:
            SupertoolError: If execution fails or is not permitted
        """
        # Validate permission
        if not self.can_use_tool(tool_id):
            raise SupertoolError(
                f"Agent {self.agent_id} does not have permission to use supertool {tool_id}"
            )
        
        # Get tool instance
        # Registry returns tool class, need to instantiate
        tool_class = self.registry.get_tool_class(tool_id)
        if not tool_class:
            raise SupertoolError(f"Supertool {tool_id} not found in registry")
        tool = tool_class()
        
        # Get constraints
        constraints = self.get_agent_constraints()
        
        # Get issue details if provided
        issue_details = None
        if issue_id:
            try:
                issue_details = self.board_client.get_issue_details(issue_id)
            except Exception as e:
                logger.warning(f"Could not get issue details for {issue_id}: {e}")
        
        # Get credentials for this tool
        required_creds = tool.get_required_credentials()
        credentials = self.credential_manager.merge_credentials(
            self.agent_id, tool_id, required_creds
        )
        
        # Create execution context
        exec_path = self.workspace.get_execution_path(execution_id)
        context = SupertoolContext(
            workspace_path=exec_path,
            agent_id=self.agent_id,
            issue_id=issue_id,
            issue_details=issue_details,
            credentials=credentials,
            constraints=constraints,
            board_root=self.board_root,
            metadata=additional_context or {},
        )
        
        # Validate context
        try:
            tool.validate_context(context)
        except SupertoolError as e:
            return SupertoolResult(
                success=False,
                output="",
                error=str(e),
            )
        
        # Execute with timeout if specified
        max_time = constraints.get("max_execution_time")
        start_time = time.time()
        
        try:
            if max_time:
                result = await asyncio.wait_for(
                    tool.execute(context),
                    timeout=max_time,
                )
            else:
                result = await tool.execute(context)
            
            result.execution_time = time.time() - start_time
            return result
            
        except asyncio.TimeoutError:
            return SupertoolResult(
                success=False,
                output="",
                error=f"Execution timed out after {max_time} seconds",
                execution_time=time.time() - start_time,
            )
        except SupertoolError as e:
            return SupertoolResult(
                success=False,
                output="",
                error=str(e),
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            logger.exception(f"Unexpected error executing supertool {tool_id}")
            return SupertoolResult(
                success=False,
                output="",
                error=f"Unexpected error: {str(e)}",
                execution_time=time.time() - start_time,
            )
    
    def list_available_tools(self) -> Dict[str, Dict]:
        """
        List all supertools available to this agent.
        
        Returns:
            Dictionary mapping tool_id to tool metadata
        """
        agent = self.board_client.get_agent(self.agent_id)
        if not agent:
            return {}
        
        supertools_config = agent.get("supertools", {})
        allowed = supertools_config.get("allowed", [])
        
        if not allowed:
            return {}
        
        all_tools = self.registry.list_all()
        return {tool_id: metadata for tool_id, metadata in all_tools.items() if tool_id in allowed}




