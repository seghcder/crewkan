"""
LangChain tool conversion for supertools.
"""

import logging
from typing import List, Optional
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field
from crewkan.agent_framework.executor import SupertoolExecutor
from crewkan.agent_framework.base import SupertoolResult

logger = logging.getLogger(__name__)


class SupertoolInvokeInput(BaseModel):
    """Input schema for supertool invocation."""
    tool_id: str = Field(description="The ID of the supertool to execute")
    issue_id: Optional[str] = Field(None, description="Optional issue ID being worked on")
    execution_id: Optional[str] = Field(None, description="Optional execution ID for isolation")
    additional_context: Optional[dict] = Field(None, description="Additional context data")


def make_supertool_tools(
    board_root: str,
    agent_id: str,
) -> List[BaseTool]:
    """
    Create LangChain tools for all supertools available to an agent.
    
    Args:
        board_root: Root directory of the board
        agent_id: ID of the agent
        
    Returns:
        List of LangChain tools for available supertools
    """
    executor = SupertoolExecutor(board_root, agent_id)
    available_tools = executor.list_available_tools()
    
    if not available_tools:
        logger.info(f"No supertools available for agent {agent_id}")
        return []
    
    tools = []
    
    # Create a generic supertool invocation tool
    async def invoke_supertool(
        tool_id: str,
        issue_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        additional_context: Optional[dict] = None,
    ) -> str:
        """
        Invoke a supertool.
        
        Args:
            tool_id: Supertool identifier
            issue_id: Optional issue ID being worked on
            execution_id: Optional execution ID for isolation
            additional_context: Optional additional context data
            
        Returns:
            JSON string with execution results
        """
        try:
            result = await executor.execute(
                tool_id=tool_id,
                issue_id=issue_id,
                execution_id=execution_id,
                additional_context=additional_context,
            )
            return result.to_dict()
        except Exception as e:
            logger.exception(f"Error invoking supertool {tool_id}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
            }
    
    # Create individual tools for each available supertool
    for tool_id, metadata in available_tools.items():
        tool_name = f"supertool_{tool_id}"
        tool_description = (
            f"{metadata.get('name', tool_id)}: {metadata.get('description', 'No description')}\n"
            f"Required credentials: {', '.join(metadata.get('required_credentials', []))}"
        )
        
        # Create a specialized tool function for this supertool (capture tool_id in closure)
        def make_tool_func(tid: str):
            async def tool_func(
                issue_id: Optional[str] = None,
                execution_id: Optional[str] = None,
                additional_context: Optional[dict] = None,
            ) -> str:
                return await invoke_supertool(
                    tool_id=tid,
                    issue_id=issue_id,
                    execution_id=execution_id,
                    additional_context=additional_context,
                )
            return tool_func
        
        tool_func = make_tool_func(tool_id)
        
        # Create input schema for this tool
        class ToolInput(BaseModel):
            issue_id: Optional[str] = Field(None, description="Optional issue ID being worked on")
            execution_id: Optional[str] = Field(None, description="Optional execution ID for isolation")
            additional_context: Optional[dict] = Field(None, description="Additional context data")
        
        tool = StructuredTool.from_function(
            name=tool_name,
            func=tool_func,
            args_schema=ToolInput,
            description=tool_description,
        )
        tools.append(tool)
    
    # Also add a generic supertool invocation tool
    generic_tool = StructuredTool.from_function(
        name="invoke_supertool",
        func=invoke_supertool,
        args_schema=SupertoolInvokeInput,
        description=(
            "Invoke any available supertool by ID. "
            "Use this when you need to use a specific supertool that isn't available as a dedicated tool."
        ),
    )
    tools.append(generic_tool)
    
    logger.info(f"Created {len(tools)} LangChain tools for agent {agent_id}")
    return tools


def get_supertool_descriptions(board_root: str, agent_id: str) -> str:
    """
    Get descriptions of all available supertools for an agent.
    
    This can be used in prompts to help the LLM select appropriate tools.
    
    Args:
        board_root: Root directory of the board
        agent_id: ID of the agent
        
    Returns:
        Formatted string describing available supertools
    """
    executor = SupertoolExecutor(board_root, agent_id)
    available_tools = executor.list_available_tools()
    
    if not available_tools:
        return "No supertools are available to this agent."
    
    descriptions = ["Available supertools:"]
    for tool_id, metadata in available_tools.items():
        desc = f"- {tool_id} ({metadata.get('name', 'Unknown')})"
        if metadata.get('description'):
            desc += f": {metadata['description']}"
        if metadata.get('required_credentials'):
            desc += f" [Requires: {', '.join(metadata['required_credentials'])}]"
        descriptions.append(desc)
    
    return "\n".join(descriptions)

