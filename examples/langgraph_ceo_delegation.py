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
import argparse
import random
from pathlib import Path
from typing import Annotated, TypedDict
import asyncio
import json
import time

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
    last_fanout_time: float  # Timestamp of last fanout routing to prevent rapid re-routing
    total_tasks: int  # Total number of tasks to create


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

def create_ceo_node(board_root: str, tasks_per_worker: int = 10):
    """Create CEO agent node that creates tasks and monitors completion."""
    
    async def ceo_agent(state: AgentState):
        """CEO agent: Creates tasks (tasks_per_worker each for COO, CFO, CTO) and monitors."""
        tasks_created = state.get("tasks_created", False)
        total_tasks = state.get("total_tasks", tasks_per_worker * 3)
        
        # If tasks haven't been created yet, create them
        if not tasks_created:
            client = BoardClient(board_root, "ceo")
            
            # Check if tasks already exist (work resumption - don't recreate)
            existing_counts = count_tasks_by_status(board_root)
            existing_total = sum(existing_counts.values())
            if existing_total >= total_tasks:
                # Tasks already exist, just mark as created (work resumption)
                return {"tasks_created": True}
            
            # Create tasks_per_worker tasks for each agent (COO, CFO, CTO)
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
                    "Develop operational metrics",
                    "Create process documentation",
                    "Train operations team",
                    "Review compliance standards",
                    "Optimize inventory management",
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
                    "Review accounts receivable",
                    "Analyze cost structure",
                    "Prepare board presentation",
                    "Review financial controls",
                    "Optimize capital allocation",
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
                    "Review API design",
                    "Optimize application performance",
                    "Implement backup strategy",
                    "Review security policies",
                    "Plan capacity scaling",
                ],
            }
            
            created_tasks = []
            priorities = ["high", "medium", "low"]
            
            for agent_id in agents:
                titles = task_titles[agent_id]
                # Create tasks_per_worker tasks with random priorities
                for i in range(tasks_per_worker):
                    title = titles[i % len(titles)]  # Cycle through titles if needed
                    priority = random.choice(priorities)  # Random priority
                    task_id = client.create_task(
                        title=f"{title} ({i+1})",
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
        # Don't update state to avoid conflicts when called multiple times
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


def create_fanout_node():
    """Create a fan-out node that routes to all workers."""
    async def fanout(state: AgentState):
        """Pass through node that allows routing to multiple workers."""
        # Update last_fanout_time to prevent rapid re-routing
        return {"last_fanout_time": time.time()}
    
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
    total_tasks = state.get("total_tasks", 30)
    last_fanout_time = state.get("last_fanout_time", 0.0)
    current_time = time.time()
    
    if not tasks_created:
        return "fanout"  # Go to fanout which routes to all workers
    
    if all_tasks_done(board_root, expected_total=total_tasks):
        return "end"  # All done, exit
    
    # Only route to fanout if enough time has passed since last routing
    # This prevents exponential growth when CEO is called multiple times concurrently
    # 0.1 seconds should be enough to let one call through while blocking rapid re-routing
    if current_time - last_fanout_time > 0.1:
        return "fanout"
    else:
        return "end"  # End this execution path to prevent recursion


# ============================================================================
# Graph Construction
# ============================================================================

def create_delegation_graph(board_root: str, tasks_per_worker: int = 10):
    """Create the LangGraph for CEO delegation with continuous task processing."""
    
    graph = StateGraph(AgentState)
    
    # Add nodes
    ceo_node = create_ceo_node(board_root, tasks_per_worker)
    fanout_node = create_fanout_node()
    coo_node = create_worker_node(board_root, "coo")
    cfo_node = create_worker_node(board_root, "cfo")
    cto_node = create_worker_node(board_root, "cto")
    
    graph.add_node("ceo", ceo_node)
    graph.add_node("fanout", fanout_node)
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
    
    # Workers process tasks and route directly to CEO
    # CEO is idempotent, so multiple calls are safe
    graph.add_edge("coo", "ceo")
    graph.add_edge("cfo", "ceo")
    graph.add_edge("cto", "ceo")
    
    return graph.compile(checkpointer=MemorySaver(), interrupt_before=[], interrupt_after=[])


# ============================================================================
# Main Execution
# ============================================================================

async def main():
    """Run the CEO delegation example with continuous task processing."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="CEO delegation workflow with continuous task processing")
    parser.add_argument(
        "--tasks-per-worker",
        type=int,
        default=10,
        help="Number of tasks to create per worker (default: 10)"
    )
    args = parser.parse_args()
    tasks_per_worker = args.tasks_per_worker
    total_tasks = tasks_per_worker * 3
    
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
    
    # Create and run graph
    graph = create_delegation_graph(str(board_root), tasks_per_worker)
    
    initial_state = {
        "messages": [{"role": "user", "content": f"Create {total_tasks} tasks ({tasks_per_worker} each for COO, CFO, CTO) and monitor their completion"}],
        "agent_id": "ceo",
        "task_id": None,
        "board_root": str(board_root),
        "tasks_created": False,
        "last_fanout_time": 0.0,
        "total_tasks": total_tasks,
    }
    
    config = {
        "configurable": {
            "thread_id": "1",
        },
        "recursion_limit": 1000
    }
    
    print("=" * 60)
    print("Starting CEO delegation workflow...")
    print(f"CEO will create {total_tasks} tasks ({tasks_per_worker} each for COO, CFO, CTO)")
    print("Agents will process tasks: backlog → todo → doing → done")
    print("Each task takes 2-5 seconds to complete (random)")
    print("Task priorities are assigned randomly")
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

