#!/usr/bin/env python3
"""
Standalone agent runner for CrewKan agents.

Each agent runs independently, reading from the board directory and using
LangChain agents with board tools and supertools.
"""

import os
import sys
import asyncio
import argparse
import json
import logging
import time
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load environment variables from .env if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

from langchain_openai import AzureChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import SystemMessage, HumanMessage

from crewkan.board_core import BoardClient
from crewkan.board_langchain_tools import make_board_tools
from crewkan.agent_framework.langchain_tools import make_supertool_tools, get_supertool_descriptions
from crewkan.agent_framework.workspace import AgentWorkspace

# Import supertools to register them
from crewkan.agent_framework.supertools import *  # noqa: F403, F401

# Set up logging - will be configured per agent in main()
logger = logging.getLogger(__name__)


# Import logging setup from separate module to avoid LangChain dependency in tests
from crewkan.agent_framework.logging_utils import setup_agent_logging


def get_default_system_prompt(agent_id: str, board_root: str, agent_info: dict) -> str:
    """
    Generate a default system prompt for an agent based on their role and skills.
    
    Args:
        agent_id: Agent ID
        board_root: Board root directory
        agent_info: Agent information dict from board
        
    Returns:
        System prompt string
    """
    workspace = AgentWorkspace(Path(board_root), agent_id)
    workspace_path = workspace.get_workspace_path()
    shared_workspace_path = Path(board_root) / "workspaces" / "shared"
    
    role = agent_info.get("role", "agent")
    name = agent_info.get("name", agent_id)
    skills = agent_info.get("skills", [])
    
    skills_text = f"Skills: {', '.join(skills)}" if skills else ""
    
    prompt = f"""You are {name}, a {role} agent working on a CrewKan task board.

WORKSPACE:
- Your workspace: {workspace_path}
- Shared workspace: {shared_workspace_path}
- All files you create should be placed in your workspace directory unless the task specifies otherwise.
- Use the shared workspace for files that need to be accessed by multiple agents.

WORKFLOW:
1. Check your assigned tasks: Use list_my_issues() to see tasks assigned to you
2. Prioritize work:
   - First, complete any tasks already in "doing" column
   - Then, start working on tasks in "todo" column (move to "doing" first)
   - Finally, move tasks from "backlog" to "todo" if you have capacity
3. Start work: When beginning a task, move it to "doing" with move_issue()
4. Do the work: Use appropriate supertools (cline, deep-research, etc.) or standard processes
5. Track progress: Add comments with add_comment_to_issue() to document your work
6. Complete: When finished, move task to "done" with move_issue()
7. Follow-ups: If task description mentions reassignment or creating new tasks:
   - Use reassign_issue() to assign to another agent
   - Use create_issue() to create follow-up tasks
8. Workspace management: Create and modify files in your workspace as needed

{skills_text}

TOOLS:
You have access to board management tools (list_my_issues, move_issue, add_comment_to_issue, etc.)
and supertools for specialized tasks. Use supertools when appropriate for the task type.

Be proactive, efficient, and thorough. Always check for assigned tasks and work on them systematically."""
    
    return prompt


def create_agent_executor(
    board_root: str,
    agent_id: str,
    system_prompt: Optional[str] = None
):
    """
    Create a LangChain agent for an agent (LangChain 1.0 API).
    
    Args:
        board_root: Board root directory
        agent_id: Agent ID
        system_prompt: Optional system prompt (if None, will be generated)
        
    Returns:
        Compiled agent graph (LangChain 1.0)
    """
    # Get LLM
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    
    if not (api_key and endpoint and deployment):
        raise ValueError(
            "Missing Azure OpenAI configuration. Set AZURE_OPENAI_API_KEY, "
            "AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_DEPLOYMENT_NAME environment variables."
        )
    
    llm = AzureChatOpenAI(
        azure_endpoint=endpoint,
        azure_deployment=deployment,
        api_key=api_key,
        api_version=api_version,
        temperature=0.7,
    )
    
    # Get tools
    board_tools = make_board_tools(board_root, agent_id)
    supertools = make_supertool_tools(board_root, agent_id)
    all_tools = board_tools + supertools
    
    logger.info(f"Created {len(board_tools)} board tools and {len(supertools)} supertools for {agent_id}")
    
    # Get system prompt
    client = BoardClient(board_root, agent_id)
    agent_info = client.get_agent(agent_id)
    
    if not system_prompt:
        # Try to load from agent config
        system_prompt = client.get_agent_system_prompt(agent_id)
        if not system_prompt:
            # Generate default prompt
            system_prompt = get_default_system_prompt(agent_id, board_root, agent_info or {})
    
    # Add supertool descriptions to prompt
    supertool_descriptions = get_supertool_descriptions(board_root, agent_id)
    if supertool_descriptions:
        system_prompt += f"\n\n{supertool_descriptions}"
    
    # Create agent using LangChain 1.0 API
    agent = create_agent(
        model=llm,
        tools=all_tools,
        system_prompt=system_prompt,
        debug=True,
    )
    
    return agent


def check_shutdown_requested(board_root: str) -> tuple[bool, float]:
    """
    Check if shutdown has been requested via file.
    
    Returns:
        Tuple of (shutdown_requested, deadline_timestamp)
    """
    shutdown_file = Path(board_root) / ".shutdown_requested"
    if not shutdown_file.exists():
        return False, 0.0
    
    try:
        shutdown_data = json.loads(shutdown_file.read_text())
        deadline = shutdown_data.get("deadline", 0)
        return True, deadline
    except Exception:
        return True, 0.0


async def run_agent_cycle(
    executor,
    board_root: str,
    agent_id: str,
    iteration: int
) -> bool:
    """
    Run one cycle of agent work.
    
    Args:
        executor: Agent executor
        board_root: Board root directory
        agent_id: Agent ID
        iteration: Current iteration number
        
    Returns:
        True if should continue, False if should stop
    """
    # Check shutdown
    shutdown_requested, deadline = check_shutdown_requested(board_root)
    if shutdown_requested:
        if deadline > 0 and time.time() >= deadline:
            agent_logger = logging.getLogger(f"crewkan.agent.{agent_id}")
            agent_logger.info(f"Shutdown deadline reached")
            return False
        time_remaining = deadline - time.time() if deadline > 0 else 0
        agent_logger = logging.getLogger(f"crewkan.agent.{agent_id}")
        agent_logger.info(f"Shutdown requested, {time_remaining:.1f}s remaining")
    
    # Agent decides what to do
    try:
        # Create a prompt that encourages the agent to check and work on tasks
        input_prompt = (
            f"Review your assigned tasks and work on the highest priority item. "
            f"Check tasks in 'doing' first, then 'todo', then move items from 'backlog' to 'todo' if needed. "
            f"Be efficient and thorough."
        )
        
        # LangChain 1.0 agent expects messages format
        result = await executor.ainvoke({
            "messages": [HumanMessage(content=input_prompt)]
        })
        
        agent_logger = logging.getLogger(f"crewkan.agent.{agent_id}")
        # LangChain 1.0 returns messages, extract last message content
        if isinstance(result, dict) and "messages" in result:
            messages = result["messages"]
            if messages:
                last_msg = messages[-1]
                output_preview = getattr(last_msg, 'content', str(last_msg))[:200]
            else:
                output_preview = "No output"
        else:
            output_preview = str(result)[:200]
        agent_logger.info(f"Cycle {iteration} completed: {output_preview}")
        return True
        
    except Exception as e:
        agent_logger = logging.getLogger(f"crewkan.agent.{agent_id}")
        agent_logger.error(f"Error in agent cycle: {e}", exc_info=True)
        return True  # Continue despite errors


async def main(
    agent_id: str,
    board_root: str,
    max_iterations: Optional[int] = None,
    poll_interval: float = 5.0
):
    """
    Main agent runner loop.
    
    Args:
        agent_id: Agent ID to run
        board_root: Board root directory
        max_iterations: Maximum number of iterations (None for unlimited)
        poll_interval: Seconds to wait between cycles
    """
    # Set up agent-specific logging
    agent_logger = setup_agent_logging(agent_id, board_root)
    agent_logger.info(f"Starting agent runner for {agent_id} on board {board_root}")
    
    # Validate agent exists
    client = BoardClient(board_root, agent_id)
    agent_info = client.get_agent(agent_id)
    if not agent_info:
        agent_logger.error(f"Agent {agent_id} not found on board {board_root}")
        raise ValueError(f"Agent {agent_id} not found on board {board_root}")
    
    if agent_info.get("status") != "active":
        agent_logger.warning(f"Agent {agent_id} is not active (status: {agent_info.get('status')})")
    
    # Create agent executor
    try:
        executor = create_agent_executor(board_root, agent_id)
        agent_logger.info(f"Agent executor created successfully")
    except Exception as e:
        agent_logger.error(f"Failed to create agent executor: {e}", exc_info=True)
        raise
    
    # Get workspace info
    workspace = AgentWorkspace(Path(board_root), agent_id)
    workspace_path = workspace.get_workspace_path()
    agent_logger.info(f"Workspace at {workspace_path}")
    
    # Main loop
    iteration = 0
    try:
        while True:
            iteration += 1
            
            if max_iterations and iteration > max_iterations:
                logger.info(f"{agent_id}: Reached max iterations ({max_iterations})")
                break
            
            # Check shutdown
            shutdown_requested, deadline = check_shutdown_requested(board_root)
            if shutdown_requested:
                if deadline > 0 and time.time() >= deadline:
                    agent_logger.info(f"Shutdown deadline reached")
                    break
            
            # Run agent cycle
            should_continue = await run_agent_cycle(executor, board_root, agent_id, iteration)
            if not should_continue:
                break
            
            # Wait before next cycle
            await asyncio.sleep(poll_interval)
            
    except KeyboardInterrupt:
        agent_logger.info(f"Interrupted by user")
    except Exception as e:
        agent_logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        agent_logger.info(f"Agent runner stopped after {iteration} iterations")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a CrewKan agent independently")
    parser.add_argument(
        "--agent-id",
        required=True,
        help="Agent ID to run"
    )
    parser.add_argument(
        "--board-root",
        required=True,
        help="Board root directory"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum number of iterations (default: unlimited)"
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
        help="Seconds to wait between cycles (default: 5.0)"
    )
    
    args = parser.parse_args()
    
    asyncio.run(main(
        agent_id=args.agent_id,
        board_root=args.board_root,
        max_iterations=args.max_iterations,
        poll_interval=args.poll_interval
    ))

