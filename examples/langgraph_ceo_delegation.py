#!/usr/bin/env python3
"""
LangGraph example: CEO delegating tasks to multiple agents working in parallel.

This demonstrates:
1. CEO agent creating and delegating tasks
2. Multiple worker agents processing tasks in parallel
3. Notification system for task completion
"""

import os
import sys
from pathlib import Path
from typing import Annotated, TypedDict
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from crewkan.board_langchain_tools import make_board_tools
from crewkan.board_core import BoardClient
from crewkan.board_init import init_board


# ============================================================================
# State Definition
# ============================================================================

class AgentState(TypedDict):
    """State shared between agents in the graph."""
    messages: Annotated[list, "Messages in the conversation"]
    agent_id: str  # Current agent processing
    task_id: str | None  # Current task being worked on
    board_root: str  # Board directory


# ============================================================================
# Agent Nodes
# ============================================================================

def create_ceo_node(board_root: str):
    """Create CEO agent node that delegates tasks."""
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    board_tools = make_board_tools(board_root, "ceo")
    event_tools = make_event_tools(board_root, "ceo")
    tools = board_tools + event_tools
    tool_node = ToolNode(tools)
    llm_with_tools = llm.bind_tools(tools)
    
    async def ceo_agent(state: AgentState):
        """CEO agent: Creates tasks and delegates to workers."""
        messages = state["messages"]
        
        # Get latest message
        if not messages:
            return {"messages": [{"role": "user", "content": "Create 3 tasks for the team: 1) Research market trends, 2) Design new feature, 3) Write documentation"}]}
        
        last_message = messages[-1]
        
        # If it's a user message, delegate tasks
        if last_message.get("role") == "user":
            response = await llm_with_tools.ainvoke(messages)
            return {"messages": [response]}
        
        # If tools were called, process them
        if last_message.get("tool_calls"):
            tool_responses = await tool_node.ainvoke({"messages": messages})
            return {"messages": tool_responses["messages"]}
        
        return {"messages": messages}
    
    return ceo_agent


def create_worker_node(board_root: str, worker_id: str):
    """Create a worker agent node."""
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    tools = make_board_tools(board_root, worker_id)
    tool_node = ToolNode(tools)
    llm_with_tools = llm.bind_tools(tools)
    
    async def worker_agent(state: AgentState):
        """Worker agent: Processes assigned tasks."""
        messages = state["messages"]
        
        # Get tasks assigned to this worker
        client = BoardClient(board_root, worker_id)
        tasks_json = client.list_my_tasks(column="todo", limit=5)
        import json
        tasks = json.loads(tasks_json)
        
        if not tasks:
            return {
                "messages": messages + [{
                    "role": "assistant",
                    "content": f"No tasks assigned to {worker_id}. Waiting..."
                }]
            }
        
        # Work on first task
        task = tasks[0]
        task_id = task["id"]
        
        # Add context about the task
        task_context = f"Task {task_id}: {task.get('title', '')} - {task.get('description', '')}"
        
        # Process the task
        worker_messages = [
            {"role": "system", "content": f"You are {worker_id}, a worker agent. Process your assigned tasks efficiently."},
            {"role": "user", "content": f"Work on this task: {task_context}. When done, move it to 'done' column."}
        ]
        
        response = await llm_with_tools.ainvoke(worker_messages)
        
        # If tools were called, execute them
        if response.tool_calls:
            tool_messages = [{"role": "assistant", "content": response.content, "tool_calls": response.tool_calls}]
            tool_responses = await tool_node.ainvoke({"messages": tool_messages})
            
            # Note: Completion events are automatically created by BoardClient.move_task()
            # when a task is moved to "done", so we don't need to manually create them here
            
            return {
                "messages": messages + [response] + tool_responses["messages"],
                "task_id": task_id
            }
        
        return {
            "messages": messages + [response],
            "task_id": task_id
        }
    
    return worker_agent


def create_ceo_notification_node(board_root: str):
    """CEO node that checks for completion notifications."""
    
    async def check_notifications(state: AgentState):
        """Check for task completion notifications."""
        from crewkan.board_events import list_pending_events
        
        events = list_pending_events(board_root, "ceo", event_type="task_completed")
        
        if events:
            notifications = []
            for event in events:
                data = event.get("data", {})
                task_id = data.get("task_id", "unknown")
                completed_by = data.get("completed_by", "unknown")
                task_title = data.get("task_title", "")
                notifications.append(f"Task {task_id} ({task_title}) completed by {completed_by}")
            
            return {
                "messages": state["messages"] + [{
                    "role": "assistant",
                    "content": f"Task completion notifications:\n" + "\n".join(f"  - {n}" for n in notifications)
                }]
            }
        
        return {"messages": state["messages"]}
    
    return check_notifications


# ============================================================================
# Graph Construction
# ============================================================================

def create_delegation_graph(board_root: str):
    """Create the LangGraph for CEO delegation."""
    
    graph = StateGraph(AgentState)
    
    # Add nodes
    ceo_node = create_ceo_node(board_root)
    worker1_node = create_worker_node(board_root, "worker1")
    worker2_node = create_worker_node(board_root, "worker2")
    worker3_node = create_worker_node(board_root, "worker3")
    notification_node = create_ceo_notification_node(board_root)
    
    graph.add_node("ceo", ceo_node)
    graph.add_node("worker1", worker1_node)
    graph.add_node("worker2", worker2_node)
    graph.add_node("worker3", worker3_node)
    graph.add_node("notifications", notification_node)
    
    # Set entry point
    graph.set_entry_point("ceo")
    
    # CEO delegates to workers
    graph.add_edge("ceo", "worker1")
    graph.add_edge("ceo", "worker2")
    graph.add_edge("ceo", "worker3")
    
    # Workers can complete and notify
    graph.add_edge("worker1", "notifications")
    graph.add_edge("worker2", "notifications")
    graph.add_edge("worker3", "notifications")
    
    # Notifications back to CEO
    graph.add_edge("notifications", "ceo")
    
    # CEO can end
    graph.add_edge("ceo", END)
    
    return graph.compile(checkpointer=MemorySaver())


# ============================================================================
# Main Execution
# ============================================================================

async def main():
    """Run the CEO delegation example."""
    
    # Setup board
    board_root = Path("examples/ceo_delegation_board")
    board_root.mkdir(parents=True, exist_ok=True)
    
    if not (board_root / "board.yaml").exists():
        init_board(
            board_root,
            board_id="ceo-delegation",
            board_name="CEO Delegation Example",
            owner_agent_id="ceo",
            default_superagent_id="ceo",
        )
        
        # Add worker agents
        from crewkan.crewkan_cli import cmd_add_agent
        import argparse
        
        class Args:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        for worker_id in ["worker1", "worker2", "worker3"]:
            args = Args(root=str(board_root), id=worker_id, name=worker_id.title(), role="Worker", kind="ai")
            cmd_add_agent(args)
    
    # Create and run graph
    graph = create_delegation_graph(str(board_root))
    
    initial_state = {
        "messages": [{"role": "user", "content": "Create 3 tasks and delegate them to workers"}],
        "agent_id": "ceo",
        "task_id": None,
        "board_root": str(board_root),
    }
    
    config = {"configurable": {"thread_id": "1"}}
    
    print("Starting CEO delegation workflow...")
    async for event in graph.astream(initial_state, config):
        print(f"\n=== Event: {list(event.keys())[0]} ===")
        print(event)
    
    print("\n=== Checking for notifications ===")
    from crewkan.board_events import list_pending_events
    events = list_pending_events(str(board_root), "ceo")
    for event in events:
        print(f"  - {event}")


if __name__ == "__main__":
    asyncio.run(main())

