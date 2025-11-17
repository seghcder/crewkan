#!/usr/bin/env python3
"""
Run the CrewKan team board for a specified number of steps.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load environment variables from .env if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from operator import add

def max_reducer(left: int, right: int) -> int:
    """Reducer that takes the maximum of two values."""
    return max(left, right)
from langchain_openai import AzureChatOpenAI
from typing import Annotated, TypedDict
import json
import time
import random
import logging

from crewkan.board_core import BoardClient
from crewkan.agent_framework import SupertoolExecutor
from crewkan.agent_framework.supertools import *  # Import all supertools to register them

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# State Definition
# ============================================================================

class AgentState(TypedDict):
    """State shared between agents in the graph."""
    messages: Annotated[list, add]
    agent_id: str
    issue_id: str | None
    board_root: str
    last_issue_gen_time: float
    should_exit: bool
    shutdown_requested: bool  # Flag for graceful shutdown
    shutdown_deadline: float  # Timestamp when shutdown must complete
    step_count: Annotated[int, max_reducer]  # Use max reducer to track highest step


# ============================================================================
# Helper Functions
# ============================================================================

def get_priority_value(priority: str | None) -> int:
    """Convert priority string to numeric value for sorting."""
    priority_map = {"high": 3, "medium": 2, "low": 1}
    return priority_map.get(priority or "medium", 0)


def count_issues_by_status(board_root: str) -> dict[str, int]:
    """Count issues in each column."""
    client = BoardClient(board_root, "sean")
    counts = {}
    for path, issue in client.iter_issues():
        column = issue.get("column", "unknown")
        counts[column] = counts.get(column, 0) + 1
    return counts


# ============================================================================
# Agent Nodes
# ============================================================================

def create_agent_node(board_root: str, agent_id: str):
    """Create an agent node that processes issues."""
    
    # Check for Azure OpenAI API key
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    
    llm = None
    if api_key and endpoint and deployment:
        try:
            llm = AzureChatOpenAI(
                azure_endpoint=endpoint,
                azure_deployment=deployment,
                api_key=api_key,
                api_version=api_version,
                temperature=0.7,
            )
        except Exception:
            llm = None
    
    client = BoardClient(board_root, agent_id)
    supertool_executor = SupertoolExecutor(board_root, agent_id)
    available_supertools = supertool_executor.list_available_tools()
    
    async def agent_worker(state: AgentState):
        """Agent worker: Processes issues from backlog→todo→doing→done."""
        step_count = state.get("step_count", 0)
        
        # Check for graceful shutdown request (from file or state)
        shutdown_file = Path(board_root) / ".shutdown_requested"
        shutdown_requested = state.get("shutdown_requested", False)
        shutdown_deadline = state.get("shutdown_deadline", 0)
        
        # Check file-based shutdown signal
        if shutdown_file.exists():
            try:
                shutdown_data = json.loads(shutdown_file.read_text())
                shutdown_requested = True
                shutdown_deadline = shutdown_data.get("deadline", 0)
            except Exception:
                pass
        
        if shutdown_requested:
            time_remaining = shutdown_deadline - time.time() if shutdown_deadline > 0 else 0
            if time_remaining <= 0:
                return {
                    "step_count": step_count + 1,
                    "should_exit": True,
                    "messages": [{
                        "role": "assistant",
                        "content": f"{agent_id.upper()}: Graceful shutdown completed"
                    }]
                }
            # Continue but finish current work quickly - don't start new issues
            logger.info(f"{agent_id}: Shutdown requested, {time_remaining:.1f}s remaining")
        
        # Priority order: 1) Complete issues in "doing", 2) Start issues from "todo", 3) Move from "backlog" to "todo"
        
        # Step 1: Check if there's an issue in "doing"
        doing_issues_json = client.list_my_issues(column="doing", limit=1)
        doing_issues = json.loads(doing_issues_json)
        
        if doing_issues:
            issue = doing_issues[0]
            issue_id = issue["id"]
            issue_details = client.get_issue_details(issue_id)
            
            # Log that we're starting work on this issue (important for restarts)
            logger.info(f"{agent_id}: Starting work on issue {issue_id}: {issue_details.get('title', '')[:50]}")
            client.activity_logger.info(f"AGENT:{agent_id} | ACTION:start_work | ISSUE:{issue_id} | TITLE:{issue_details.get('title', '')[:50]}")
            
            # Read task history and comments to understand where we left off
            history = issue_details.get("history", [])
            comments = [h for h in history if h.get("event") == "comment"]
            
            # Check if this is a restart (issue was already in doing, might have been interrupted)
            was_in_doing = issue_details.get("column") == "doing"
            last_agent = None
            if history:
                # Find last agent who worked on this
                for entry in reversed(history):
                    if entry.get("by") and entry.get("by") != agent_id:
                        last_agent = entry.get("by")
                        break
            
            # Add restart comment if this is a resume after restart
            # (issue is already in "doing", which suggests we're resuming after a restart)
            if was_in_doing:
                # This might be a restart - add a comment
                restart_comment = f"🔄 Resuming work on this issue."
                if comments:
                    restart_comment += f" Reviewing {len(comments)} previous comment(s) to understand context."
                if last_agent and last_agent != agent_id:
                    restart_comment += f" Last worked on by {last_agent}."
                client.add_comment(issue_id, restart_comment)
                logger.info(f"{agent_id}: Added restart comment to issue {issue_id}")
            
            if comments:
                logger.info(f"{agent_id}: Found {len(comments)} comments on issue {issue_id}, reviewing context...")
                # Log recent comments for context
                recent_comments = comments[-3:]  # Last 3 comments
                for comment in recent_comments:
                    logger.debug(f"{agent_id}: Previous comment by {comment.get('by', 'unknown')}: {comment.get('details', '')[:100]}")
            
            # Check if we should use a supertool
            issue_type = issue_details.get("issue_type", "task")
            issue_title = issue_details.get("title", "")
            issue_desc = issue_details.get("description", "")
            
            used_supertool = False
            supertool_result = None
            
            # Use appropriate supertool based on agent and issue
            if agent_id == "community" and ("research" in issue_title.lower() or "community" in issue_title.lower()):
                if "deep-research" in available_supertools:
                    try:
                        supertool_result = await supertool_executor.execute(
                            tool_id="deep-research",
                            issue_id=issue_id,
                            additional_context={
                                "query": issue_desc or issue_title,
                                "depth": 3,
                            }
                        )
                        used_supertool = True
                    except Exception as e:
                        logger.warning(f"Error using deep-research supertool: {e}")
            
            elif agent_id in ["architect", "developer", "tester", "docs"]:
                if "cline" in available_supertools and any(kw in issue_title.lower() or kw in issue_desc.lower() 
                                                           for kw in ["code", "implement", "fix", "refactor", "debug", "test"]):
                    try:
                        supertool_result = await supertool_executor.execute(
                            tool_id="cline",
                            issue_id=issue_id,
                            additional_context={
                                "prompt": f"Work on this: {issue_title}\n\n{issue_desc}",
                            }
                        )
                        used_supertool = True
                    except Exception as e:
                        logger.warning(f"Error using Cline supertool: {e}")
            
            # For long-running tasks, add periodic progress updates
            work_start_time = time.time()
            progress_update_interval = 180  # Update every 3 minutes
            
            # Simulate work with periodic progress updates
            if used_supertool and supertool_result and supertool_result.execution_time:
                work_time = min(supertool_result.execution_time, 2.0)
            else:
                work_time = random.uniform(0.5, 1.5)
            
            # If work will take longer than progress interval, add periodic updates
            # For real long tasks, we'd check elapsed time, but for simulated work we just sleep
            # In production, this would be checking actual work progress
            if work_time > progress_update_interval / 60:  # If work > 3 minutes
                # For simulated work, we'll add a progress comment at the start
                # In real implementation, this would be a loop checking actual progress
                progress_comment = f"⏳ Working on this task (estimated {int(work_time * 60)} seconds)..."
                if used_supertool:
                    progress_comment += f" Using supertool: {supertool_result.tool_id if supertool_result else 'unknown'}"
                client.add_comment(issue_id, progress_comment)
                logger.info(f"{agent_id}: Added progress comment to issue {issue_id}")
                client.activity_logger.info(f"AGENT:{agent_id} | ACTION:progress_update | ISSUE:{issue_id} | ESTIMATED:{int(work_time * 60)}s")
            
            await asyncio.sleep(work_time)
            
            # Generate completion comment
            comments_text = "\n".join([
                f"- {h.get('by', 'unknown')}: {h.get('details', '')}"
                for h in issue_details.get("history", [])
                if h.get("event") == "comment"
            ])
            
            completion_comment = None
            if llm:
                try:
                    completion_prompt = f"""You are {agent_id} completing an issue. Generate a brief completion comment.

Issue: {issue_title}
Description: {issue_desc}
{f"Supertool result: {supertool_result.output if supertool_result and supertool_result.success else 'None'}" if used_supertool else ""}

Generate a brief completion comment (1-2 sentences):"""
                    response = llm.invoke(completion_prompt)
                    completion_comment = response.content.strip()
                except Exception:
                    completion_comment = "Issue completed successfully."
            else:
                completion_comment = f"Completed using {'supertool' if used_supertool else 'standard process'}."
            
            client.add_comment(issue_id, completion_comment)
            
            # Move to done
            client.move_issue(issue_id, "done", notify_on_completion=True)
            return {
                "step_count": step_count + 1,
                "messages": [{
                    "role": "assistant",
                    "content": f"{agent_id.upper()}: Completed {issue_id} ({issue_title})" + 
                              (f" using supertool" if used_supertool else "")
                }]
            }
        
        # Step 2: Pick highest priority issue from todo and move to doing
        # Skip if shutdown requested (finish current work only)
        if not shutdown_requested:
            todo_issues_json = client.list_my_issues(column="todo", limit=10)
            todo_issues = json.loads(todo_issues_json)
            
            if todo_issues:
                todo_issues.sort(key=lambda t: get_priority_value(t.get("priority")), reverse=True)
                issue = todo_issues[0]
                issue_id = issue["id"]
                
                # Get issue details before moving to understand context
                issue_details = client.get_issue_details(issue_id)
                
                # Log that we're starting work on this issue
                logger.info(f"{agent_id}: Starting new issue {issue_id}: {issue_details.get('title', '')[:50]}")
                client.activity_logger.info(f"AGENT:{agent_id} | ACTION:start_new_issue | ISSUE:{issue_id} | TITLE:{issue_details.get('title', '')[:50]}")
                
                # Read task history and comments to understand context
                history = issue_details.get("history", [])
                comments = [h for h in history if h.get("event") == "comment"]
                
                # Add start comment
                start_comment = f"🚀 Starting work on this issue."
                if comments:
                    start_comment += f" Reviewing {len(comments)} previous comment(s) for context."
                client.add_comment(issue_id, start_comment)
                logger.info(f"{agent_id}: Added start comment to issue {issue_id}")
                
                if comments:
                    logger.info(f"{agent_id}: Found {len(comments)} comments on new issue {issue_id}, reviewing context...")
                    recent_comments = comments[-3:]
                    for comment in recent_comments:
                        logger.debug(f"{agent_id}: Previous comment by {comment.get('by', 'unknown')}: {comment.get('details', '')[:100]}")
                
                client.move_issue(issue_id, "doing", notify_on_completion=False)
                return {
                    "step_count": step_count + 1,
                    "messages": [{
                        "role": "assistant",
                        "content": f"{agent_id.upper()}: Started working on {issue_id} ({issue.get('title', '')})"
                    }]
                }
        
        # Step 3: Move issues from backlog to todo (skip if shutdown requested)
        if not shutdown_requested:
            backlog_issues_json = client.list_my_issues(column="backlog", limit=10)
            backlog_issues = json.loads(backlog_issues_json)
            
            if backlog_issues:
                issue = backlog_issues[0]
                issue_id = issue["id"]
                client.move_issue(issue_id, "todo", notify_on_completion=False)
                return {
                    "step_count": step_count + 1,
                    "messages": [{
                        "role": "assistant",
                        "content": f"{agent_id.upper()}: Moved {issue_id} from backlog to todo"
                    }]
                }
        
        # No issues to process
        return {
            "step_count": step_count + 1,
            "messages": [{
                "role": "assistant",
                "content": f"{agent_id.upper()}: No issues to process"
            }]
        }
    
    return agent_worker


def should_continue(state: AgentState) -> str:
    """Continue processing unless explicitly told to stop or max steps reached."""
    should_exit = state.get("should_exit", False)
    shutdown_requested = state.get("shutdown_requested", False)
    shutdown_deadline = state.get("shutdown_deadline", 0)
    step_count = state.get("step_count", 0)
    max_steps = state.get("max_steps", 1000)
    
    # Check graceful shutdown deadline
    if shutdown_requested and shutdown_deadline > 0:
        if time.time() >= shutdown_deadline:
            return "end"
        # Continue processing but agents should finish current work
    
    if should_exit or step_count >= max_steps:
        return "end"
    return "continue"


# ============================================================================
# Graph Construction
# ============================================================================

def create_team_graph(board_root: str):
    """Create the LangGraph with all team agents running in parallel."""
    
    from langgraph.graph import StateGraph
    
    graph = StateGraph(AgentState)
    
    # Get all agents
    client = BoardClient(board_root, "sean")
    all_agents = client.list_agents()
    agent_ids = [a["id"] for a in all_agents if a.get("status") == "active" and a.get("kind") == "ai"]
    
    # Add nodes for each AI agent
    for agent_id in agent_ids:
        graph.add_node(agent_id, create_agent_node(board_root, agent_id))
        graph.add_conditional_edges(agent_id, should_continue, {"continue": agent_id, "end": END})
    
    # Create a coordinator node that starts all agents in parallel
    def coordinator_node(state: AgentState):
        """Coordinator that starts all agents in parallel."""
        return state
    
    graph.add_node("coordinator", coordinator_node)
    graph.set_entry_point("coordinator")
    
    # Route from coordinator to all agents in parallel
    for agent_id in agent_ids:
        graph.add_edge("coordinator", agent_id)
    
    return graph.compile(checkpointer=MemorySaver(), interrupt_before=[], interrupt_after=[])


# ============================================================================
# Main Execution
# ============================================================================

async def main(max_duration_seconds: int = None):
    """Run the CrewKan team board.
    
    Args:
        max_duration_seconds: Maximum duration to run in seconds (None for unlimited)
    """
    
    board_root = Path("boards/crewkanteam")
    
    print("=" * 60)
    print("Starting CrewKan Team Board")
    print(f"Board: {board_root}")
    if max_duration_seconds:
        print(f"Running for up to {max_duration_seconds} seconds")
    else:
        print("Running for up to 1000 steps")
    print("=" * 60)
    
    graph = create_team_graph(str(board_root))
    
    initial_state = {
        "messages": [{"role": "user", "content": "Start team workflow"}],
        "agent_id": "system",
        "issue_id": None,
        "board_root": str(board_root),
        "last_issue_gen_time": 0.0,
        "should_exit": False,
        "shutdown_requested": False,
        "shutdown_deadline": 0.0,
        "step_count": 0,
        "max_steps": 1000,
    }
    
    config = {
        "configurable": {
            "thread_id": "crewkanteam-1",
        },
        "recursion_limit": 10000
    }
    
    start_time = time.time()
    iteration = 0
    async for event in graph.astream(initial_state, config, recursion_limit=1000):
        iteration += 1
        node_name = list(event.keys())[0]
        state = event[node_name]
        
        if state and "messages" in state and state["messages"]:
            last_msg = state["messages"][-1] if isinstance(state["messages"], list) else {}
            content = last_msg.get("content", "") if isinstance(last_msg, dict) else ""
            if content:
                print(f"\n[{node_name.upper()}] {content}")
        
        step_count = state.get("step_count", 0) if state else 0
        elapsed = time.time() - start_time
        
        if iteration % 10 == 0:
            counts = count_issues_by_status(str(board_root))
            print(f"\n📊 Step {step_count}, Elapsed: {elapsed:.1f}s: {counts}")
        
        # Check time limit - request graceful shutdown
        if max_duration_seconds and elapsed >= max_duration_seconds - 60:
            # Request graceful shutdown 60 seconds before time limit
            shutdown_file = board_root / ".shutdown_requested"
            if not shutdown_file.exists():
                print(f"\n🛑 Requesting graceful shutdown (60s grace period)")
                shutdown_data = {
                    "requested_at": time.time(),
                    "deadline": time.time() + 60,
                    "grace_period": 60,
                }
                shutdown_file.write_text(json.dumps(shutdown_data, indent=2))
        
        if max_duration_seconds and elapsed >= max_duration_seconds:
            print(f"\n⏱️  Time limit reached ({max_duration_seconds}s)")
            break
        
        if step_count >= 1000:
            break
    
    # Final status
    print("\n" + "=" * 60)
    print("Workflow completed!")
    final_counts = count_issues_by_status(str(board_root))
    print(f"Final status: {final_counts}")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    max_duration = None
    if len(sys.argv) > 1:
        try:
            max_duration = int(sys.argv[1])
        except ValueError:
            print(f"Usage: {sys.argv[0]} [max_duration_seconds]")
            sys.exit(1)
    asyncio.run(main(max_duration_seconds=max_duration))

