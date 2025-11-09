#!/usr/bin/env python3
"""
LangGraph example: CEO delegating tasks to multiple agents working in parallel.

This demonstrates:
1. CEO agent generating tasks dynamically using GenAI
2. Multiple worker agents processing tasks continuously in parallel
3. Long-running workflow where agents process tasks: backlog→todo→doing→done
4. Priority-based task selection (AI-generated priorities)
5. Work resumption support - can restart and continue from where it left off
6. All agents run independently in parallel
"""

import os
import sys
import argparse
import random
from pathlib import Path
from typing import Annotated, TypedDict
import asyncio
import json
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load environment variables from .env if it exists
from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from operator import add
from langchain_openai import AzureChatOpenAI

from crewkan.board_core import BoardClient
from crewkan.board_init import init_board
from crewkan.board_langchain_tools import make_board_tools


# ============================================================================
# State Definition
# ============================================================================

class AgentState(TypedDict):
    """State shared between agents in the graph."""
    messages: Annotated[list, add]  # Messages with reducer to handle concurrent updates
    agent_id: str  # Current agent processing
    task_id: str | None  # Current task being worked on
    board_root: str  # Board directory
    last_task_gen_time: float  # Timestamp of last task generation
    should_exit: bool  # Flag to signal all work is done


# ============================================================================
# Helper Functions
# ============================================================================

def get_priority_value(priority: str | None) -> int:
    """Convert priority string to numeric value for sorting (higher = more important)."""
    priority_map = {"high": 3, "medium": 2, "low": 1}
    return priority_map.get(priority or "medium", 0)


def count_tasks_by_status(board_root: str) -> dict[str, int]:
    """Count tasks in each column."""
    client = BoardClient(board_root, "ceo")  # Use CEO to count all tasks
    counts = {}
    for path, task in client.iter_tasks():
        column = task.get("column", "unknown")
        counts[column] = counts.get(column, 0) + 1
    return counts


def get_recent_task_history(board_root: str, limit: int = 10) -> str:
    """Get recent task history for context in task generation."""
    client = BoardClient(board_root, "ceo")
    history = []
    
    # Get recent completed tasks
    for path, task in client.iter_tasks():
        if task.get("column") == "done":
            history.append({
                "title": task.get("title", ""),
                "assignee": task.get("assignees", [""])[0] if task.get("assignees") else "",
                "priority": task.get("priority", "medium"),
            })
        if len(history) >= limit:
            break
    
    return json.dumps(history, indent=2)


def all_tasks_done(board_root: str, expected_total: int = 30) -> bool:
    """Check if all tasks are in the 'done' column."""
    counts = count_tasks_by_status(board_root)
    done_count = counts.get("done", 0)
    return done_count >= expected_total


# ============================================================================
# Agent Nodes
# ============================================================================

def create_ceo_node(board_root: str):
    """Create CEO agent node that generates tasks dynamically using GenAI."""
    
    # Check for Azure OpenAI API key
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    
    if not api_key or not endpoint or not deployment:
        raise ValueError(
            "Azure OpenAI credentials not set. Required: "
            "AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME"
        )
    
    llm = AzureChatOpenAI(
        azure_endpoint=endpoint,
        azure_deployment=deployment,
        api_key=api_key,
        api_version=api_version,
        temperature=0.7,
    )
    client = BoardClient(board_root, "ceo")
    agents = ["coo", "cfo", "cto"]
    max_backlog_per_agent = 5
    
    async def ceo_agent(state: AgentState):
        """CEO agent: Generates tasks dynamically using GenAI and monitors completion."""
        last_gen_time = state.get("last_task_gen_time", 0.0)
        current_time = time.time()
        
        # Check if we should generate a new task (every ~1 second)
        if current_time - last_gen_time < 1.0:
            # Too soon, just monitor
            return {}
        
        # Check backlog size - only generate if backlog < agents X max_backlog_per_agent
        counts = count_tasks_by_status(board_root)
        backlog_count = counts.get("backlog", 0)
        max_backlog = len(agents) * max_backlog_per_agent
        
        if backlog_count >= max_backlog:
            # Backlog is full, don't generate more
            return {"last_task_gen_time": current_time}
        
        # Get recent task history for context
        recent_history = get_recent_task_history(board_root, limit=5)
        
        # Generate a new task using GenAI
        prompt = f"""You are a CEO managing a team of executives: COO (Operations), CFO (Finance), and CTO (Technology).

Recent completed tasks:
{recent_history}

Current backlog size: {backlog_count}/{max_backlog}

Generate ONE new task for one of the executives. Consider:
1. What work would be most valuable based on recent completions?
2. Which executive (coo, cfo, or cto) should handle this?
3. What priority (high, medium, low) is appropriate?

Respond in JSON format:
{{
    "title": "Task title",
    "description": "Brief task description",
    "assignee": "coo|cfo|cto",
    "priority": "high|medium|low"
}}"""

        try:
            response = llm.invoke(prompt)
            content = response.content.strip()
            
            # Parse JSON from response (may have markdown code blocks)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            task_data = json.loads(content)
            
            # Validate and create task
            assignee = task_data.get("assignee", random.choice(agents))
            if assignee not in agents:
                assignee = random.choice(agents)
            
            priority = task_data.get("priority", "medium")
            if priority not in ["high", "medium", "low"]:
                priority = "medium"
            
            task_id = client.create_task(
                title=task_data.get("title", "Generated task"),
                description=task_data.get("description", ""),
                column="backlog",
                assignees=[assignee],
                priority=priority,
                requested_by="ceo",
            )
            
            return {
                "last_task_gen_time": current_time,
                "messages": [{
                    "role": "assistant",
                    "content": f"CEO: Generated task {task_id} for {assignee.upper()} - {task_data.get('title', '')} (priority: {priority})"
                }]
            }
        except Exception as e:
            # If generation fails, just update timestamp and continue
            return {"last_task_gen_time": current_time}
    
    return ceo_agent


def create_worker_node(board_root: str, worker_id: str):
    """Create a worker agent node that continuously processes tasks.
    
    All workers use the same template - they process tasks independently.
    """
    
    client = BoardClient(board_root, worker_id)
    
    async def worker_agent(state: AgentState):
        """Worker agent: Continuously processes tasks from backlog→todo→doing→done."""
        messages = state.get("messages", [])
        
        # Priority order: 1) Complete tasks in "doing", 2) Start tasks from "todo", 3) Move from "backlog" to "todo"
        
        # Step 1: Check if there's a task in "doing" - if so, complete it (highest priority)
        doing_tasks_json = client.list_my_tasks(column="doing", limit=1)
        doing_tasks = json.loads(doing_tasks_json)
        
        if doing_tasks:
            task = doing_tasks[0]
            task_id = task["id"]
            # Simulate work (random 2-5 seconds)
            work_time = random.uniform(2.0, 5.0)
            await asyncio.sleep(work_time)
            # Move to done
            client.move_task(task_id, "done", notify_on_completion=True)
            return {
                "messages": [{
                    "role": "assistant",
                    "content": f"{worker_id.upper()}: Completed task {task_id} ({task.get('title', '')}) and moved to done"
                }]
            }
        
        # Step 2: Pick highest priority task from todo and move to doing
        todo_tasks_json = client.list_my_tasks(column="todo", limit=10)
        todo_tasks = json.loads(todo_tasks_json)
        
        if todo_tasks:
            # Sort by priority (high > medium > low)
            todo_tasks.sort(key=lambda t: get_priority_value(t.get("priority")), reverse=True)
            task = todo_tasks[0]
            task_id = task["id"]
            client.move_task(task_id, "doing", notify_on_completion=False)
            return {
                "messages": [{
                    "role": "assistant",
                    "content": f"{worker_id.upper()}: Started working on task {task_id} ({task.get('title', '')}) - priority: {task.get('priority', 'medium')}"
                }]
            }
        
        # Step 3: Move tasks from backlog to todo (if any)
        backlog_tasks_json = client.list_my_tasks(column="backlog", limit=10)
        backlog_tasks = json.loads(backlog_tasks_json)
        
        if backlog_tasks:
            # Move first task from backlog to todo
            task = backlog_tasks[0]
            task_id = task["id"]
            client.move_task(task_id, "todo", notify_on_completion=False)
            return {
                "messages": [{
                    "role": "assistant",
                    "content": f"{worker_id.upper()}: Moved task {task_id} from backlog to todo"
                }]
            }
        
        # No tasks to process
        return {
            "messages": [{
                "role": "assistant",
                "content": f"{worker_id.upper()}: No tasks to process. Waiting..."
            }]
        }
    
    return worker_agent




def should_continue_worker(state: AgentState) -> str:
    """Worker nodes continue processing unless explicitly told to stop."""
    should_exit = state.get("should_exit", False)
    if should_exit:
        return "end"
    return "continue"  # Continue processing

def should_continue_ceo(state: AgentState) -> str:
    """CEO node continues generating tasks and monitoring."""
    should_exit = state.get("should_exit", False)
    if should_exit:
        return "end"
    return "continue"  # Continue generating tasks


# ============================================================================
# Graph Construction
# ============================================================================

def create_coordinator_node():
    """Create a coordinator node that routes to all agents in parallel."""
    async def coordinator(state: AgentState):
        """Coordinator that passes through state - just routes to all agents."""
        return state
    return coordinator

def create_delegation_graph(board_root: str):
    """Create the LangGraph with all agents running independently in parallel.
    
    All agents (CEO + workers) run continuously and independently.
    CEO generates tasks, workers process them.
    """
    
    graph = StateGraph(AgentState)
    
    # Add nodes - all agents run independently
    coordinator_node = create_coordinator_node()
    ceo_node = create_ceo_node(board_root)
    coo_node = create_worker_node(board_root, "coo")
    cfo_node = create_worker_node(board_root, "cfo")
    cto_node = create_worker_node(board_root, "cto")
    
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("ceo", ceo_node)
    graph.add_node("coo", coo_node)
    graph.add_node("cfo", cfo_node)
    graph.add_node("cto", cto_node)
    
    # Start with coordinator that routes to all agents in parallel
    graph.set_entry_point("coordinator")
    graph.add_edge("coordinator", "ceo")
    graph.add_edge("coordinator", "coo")
    graph.add_edge("coordinator", "cfo")
    graph.add_edge("coordinator", "cto")
    
    # Each agent loops back to itself to continue processing
    # They all run independently in parallel
    graph.add_conditional_edges("ceo", should_continue_ceo, {"continue": "ceo", "end": END})
    graph.add_conditional_edges("coo", should_continue_worker, {"continue": "coo", "end": END})
    graph.add_conditional_edges("cfo", should_continue_worker, {"continue": "cfo", "end": END})
    graph.add_conditional_edges("cto", should_continue_worker, {"continue": "cto", "end": END})
    
    return graph.compile(checkpointer=MemorySaver(), interrupt_before=[], interrupt_after=[])


# ============================================================================
# Main Execution
# ============================================================================

async def main():
    """Run the CEO delegation example with continuous task processing."""
    
    # Setup board - don't reset, support work resumption
    board_root = Path("examples/ceo_delegation_board")
    board_root.mkdir(parents=True, exist_ok=True)
    
    # Initialize board only if it doesn't exist (work resumption)
    if not (board_root / "board.yaml").exists():
        init_board(
            board_root,
            board_id="ceo-delegation",
            board_name="CEO Delegation Example",
            owner_agent_id="ceo",
            default_superagent_id="ceo",
        )
        
        # Add executive agents (COO, CFO, CTO) only if they don't exist
        from crewkan.crewkan_cli import cmd_add_agent
        
        class Args:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        executives = [
            ("coo", "Chief Operating Officer", "Operations"),
            ("cfo", "Chief Financial Officer", "Finance"),
            ("cto", "Chief Technology Officer", "Technology"),
        ]
        
        # Check existing agents to avoid duplicates
        from crewkan.utils import load_yaml
        agents_path = board_root / "agents" / "agents.yaml"
        if agents_path.exists():
            agents_data = load_yaml(agents_path, default={"agents": []})
            existing_ids = {a.get("id") for a in agents_data.get("agents", [])}
        else:
            existing_ids = set()
        
        for agent_id, name, role in executives:
            if agent_id not in existing_ids:
                args = Args(root=str(board_root), id=agent_id, name=name, role=role, kind="ai")
                cmd_add_agent(args)
    
    # Create and run graph - all agents run independently
    graph = create_delegation_graph(str(board_root))
    
    initial_state = {
        "messages": [{"role": "user", "content": "Start continuous task processing workflow"}],
        "agent_id": "system",
        "task_id": None,
        "board_root": str(board_root),
        "last_task_gen_time": 0.0,
        "should_exit": False,
    }
    
    config = {
        "configurable": {
            "thread_id": "1",
        },
        "recursion_limit": 10000  # Higher limit for long-running workflow
    }
    
    print("=" * 60)
    print("Starting CEO delegation workflow...")
    print("CEO will generate tasks dynamically using GenAI")
    print("Agents will process tasks: backlog → todo → doing → done")
    print("Each task takes 2-5 seconds to complete (random)")
    print("CEO generates new tasks every second if backlog < 15")
    print("All agents run independently in parallel")
    print("=" * 60)
    
    iteration = 0
    async for event in graph.astream(initial_state, config, recursion_limit=1000):
        iteration += 1
        node_name = list(event.keys())[0]
        state = event[node_name]
        
        # Print relevant messages
        if state and "messages" in state and state["messages"]:
            last_msg = state["messages"][-1] if isinstance(state["messages"], list) else {}
            content = last_msg.get("content", "") if isinstance(last_msg, dict) else ""
            if content:
                print(f"\n[{node_name.upper()}] {content}")
        
        # Show progress periodically
        if iteration % 5 == 0:
            counts = count_tasks_by_status(str(board_root))
            print(f"\n📊 Progress: {counts}")
    
    # Final status
    print("\n" + "=" * 60)
    print("Workflow completed!")
    final_counts = count_tasks_by_status(str(board_root))
    print(f"Final status: {final_counts}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

