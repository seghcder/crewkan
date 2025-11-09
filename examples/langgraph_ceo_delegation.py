#!/usr/bin/env python3
"""
LangGraph example: CEO delegating tasks to multiple agents working in parallel.

This demonstrates:
1. CEO agent creating 30 tasks (10 each for COO, CFO, CTO)
2. Multiple worker agents processing tasks continuously in parallel
3. Long-running workflow where agents process tasks: backlog→todo→doing→done
4. Priority-based task selection
5. CEO monitors completion and exits when all tasks are done
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Annotated, TypedDict
import asyncio
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from operator import add

from crewkan.board_core import BoardClient
from crewkan.board_init import init_board


# ============================================================================
# State Definition
# ============================================================================

class AgentState(TypedDict):
    """State shared between agents in the graph."""
    messages: Annotated[list, add]  # Messages with reducer to handle concurrent updates
    agent_id: str  # Current agent processing
    task_id: str | None  # Current task being worked on
    board_root: str  # Board directory
    tasks_created: bool  # Whether CEO has created all tasks


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


def all_tasks_done(board_root: str, expected_total: int = 30) -> bool:
    """Check if all tasks are in the 'done' column."""
    counts = count_tasks_by_status(board_root)
    done_count = counts.get("done", 0)
    return done_count >= expected_total


# ============================================================================
# Agent Nodes
# ============================================================================

def create_ceo_node(board_root: str):
    """Create CEO agent node that creates tasks and monitors completion."""
    
    async def ceo_agent(state: AgentState):
        """CEO agent: Creates 30 tasks (10 each for COO, CFO, CTO) and monitors."""
        tasks_created = state.get("tasks_created", False)
        
        # If tasks haven't been created yet, create them
        if not tasks_created:
            client = BoardClient(board_root, "ceo")
            
            # Check if tasks already exist (in case of concurrent calls)
            existing_counts = count_tasks_by_status(board_root)
            if existing_counts.get("backlog", 0) >= 30:
                # Tasks already created, just mark as created
                return {"tasks_created": True}
            
            # Create 10 tasks for each agent (COO, CFO, CTO)
            agents = ["coo", "cfo", "cto"]
            task_titles = {
                "coo": [
                    "Optimize operations workflow",
                    "Review supply chain efficiency",
                    "Implement process improvements",
                    "Analyze operational costs",
                    "Streamline production pipeline",
                    "Evaluate vendor relationships",
                    "Improve quality control",
                    "Enhance customer service",
                    "Optimize resource allocation",
                    "Review safety protocols",
                ],
                "cfo": [
                    "Prepare quarterly financial report",
                    "Analyze budget variance",
                    "Review investment portfolio",
                    "Optimize cash flow",
                    "Audit expense reports",
                    "Evaluate financial risks",
                    "Prepare tax documentation",
                    "Review pricing strategy",
                    "Analyze profitability",
                    "Update financial forecasts",
                ],
                "cto": [
                    "Design new system architecture",
                    "Review code quality standards",
                    "Implement security improvements",
                    "Optimize database performance",
                    "Upgrade infrastructure",
                    "Review technical debt",
                    "Implement CI/CD pipeline",
                    "Evaluate new technologies",
                    "Improve system monitoring",
                    "Plan technical roadmap",
                ],
            }
            
            created_tasks = []
            for agent_id in agents:
                titles = task_titles[agent_id]
                # Assign priorities: first 3 high, next 4 medium, last 3 low
                priorities = ["high"] * 3 + ["medium"] * 4 + ["low"] * 3
                
                for i, title in enumerate(titles):
                    priority = priorities[i]
                    task_id = client.create_task(
                        title=title,
                        description=f"Task {i+1} for {agent_id.upper()}",
                        column="backlog",
                        assignees=[agent_id],
                        priority=priority,
                        requested_by="ceo",
                    )
                    created_tasks.append(task_id)
            
            return {
                "tasks_created": True,
            }
        
        # After tasks are created, monitor completion (idempotent - just check status)
        # Don't update messages to avoid state conflicts
        return {}
    
    return ceo_agent


def create_worker_node(board_root: str, worker_id: str):
    """Create a worker agent node that continuously processes tasks."""
    
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
            # Simulate work (10 seconds)
            await asyncio.sleep(10)
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


def create_fanout_node():
    """Create a fan-out node that routes to all workers."""
    async def fanout(state: AgentState):
        """Pass through node that allows routing to multiple workers."""
        return state
    
    return fanout


def create_collector_node():
    """Create a collector node that aggregates worker results before routing to CEO."""
    async def collector(state: AgentState):
        """Collector node that passes through state."""
        # This node just passes through - it's used to ensure all workers complete
        # before routing to CEO
        return state
    
    return collector


def should_continue(state: AgentState) -> str:
    """Conditional routing: check if all tasks are done."""
    board_root = state["board_root"]
    tasks_created = state.get("tasks_created", False)
    
    if not tasks_created:
        return "fanout"  # Go to fanout which routes to all workers
    
    if all_tasks_done(board_root, expected_total=30):
        return "end"  # All done, exit
    else:
        return "fanout"  # Continue processing via fanout


# ============================================================================
# Graph Construction
# ============================================================================

def create_delegation_graph(board_root: str):
    """Create the LangGraph for CEO delegation with continuous task processing."""
    
    graph = StateGraph(AgentState)
    
    # Add nodes
    ceo_node = create_ceo_node(board_root)
    fanout_node = create_fanout_node()
    collector_node = create_collector_node()
    coo_node = create_worker_node(board_root, "coo")
    cfo_node = create_worker_node(board_root, "cfo")
    cto_node = create_worker_node(board_root, "cto")
    
    graph.add_node("ceo", ceo_node)
    graph.add_node("fanout", fanout_node)
    graph.add_node("collector", collector_node)
    graph.add_node("coo", coo_node)
    graph.add_node("cfo", cfo_node)
    graph.add_node("cto", cto_node)
    
    # Set entry point
    graph.set_entry_point("ceo")
    
    # CEO routes conditionally: after creating tasks, route to fanout
    # After monitoring, route back to fanout or exit
    graph.add_conditional_edges(
        "ceo",
        should_continue,
        {
            "fanout": "fanout",
            "end": END
        }
    )
    
    # Fanout routes to all workers in parallel
    graph.add_edge("fanout", "coo")
    graph.add_edge("fanout", "cfo")
    graph.add_edge("fanout", "cto")
    
    # Workers process tasks and route to collector
    graph.add_edge("coo", "collector")
    graph.add_edge("cfo", "collector")
    graph.add_edge("cto", "collector")
    
    # Collector routes to CEO (only after all workers complete)
    graph.add_edge("collector", "ceo")
    
    return graph.compile(checkpointer=MemorySaver(), interrupt_before=[], interrupt_after=[])


# ============================================================================
# Main Execution
# ============================================================================

async def main():
    """Run the CEO delegation example with continuous task processing."""
    
    # Setup board - clean existing board first
    board_root = Path("examples/ceo_delegation_board")
    if board_root.exists():
        shutil.rmtree(board_root)
    board_root.mkdir(parents=True, exist_ok=True)
    
    # Initialize board
    init_board(
        board_root,
        board_id="ceo-delegation",
        board_name="CEO Delegation Example",
        owner_agent_id="ceo",
        default_superagent_id="ceo",
    )
    
    # Add executive agents (COO, CFO, CTO)
    from crewkan.crewkan_cli import cmd_add_agent
    import argparse
    
    class Args:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    executives = [
        ("coo", "Chief Operating Officer", "Operations"),
        ("cfo", "Chief Financial Officer", "Finance"),
        ("cto", "Chief Technology Officer", "Technology"),
    ]
    
    for agent_id, name, role in executives:
        args = Args(root=str(board_root), id=agent_id, name=name, role=role, kind="ai")
        cmd_add_agent(args)
    
    # Create and run graph
    graph = create_delegation_graph(str(board_root))
    
    initial_state = {
        "messages": [{"role": "user", "content": "Create 30 tasks (10 each for COO, CFO, CTO) and monitor their completion"}],
        "agent_id": "ceo",
        "task_id": None,
        "board_root": str(board_root),
        "tasks_created": False,
    }
    
    config = {
        "configurable": {
            "thread_id": "1",
            "recursion_limit": 1000
        }
    }
    
    print("=" * 60)
    print("Starting CEO delegation workflow...")
    print("CEO will create 30 tasks (10 each for COO, CFO, CTO)")
    print("Agents will process tasks: backlog → todo → doing → done")
    print("Each task takes 10 seconds to complete")
    print("=" * 60)
    
    iteration = 0
    async for event in graph.astream(initial_state, config):
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

