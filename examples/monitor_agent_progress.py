#!/usr/bin/env python3
"""
Monitor agent progress by checking board state and agent logs.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.board_core import BoardClient


def count_issues_by_status(board_root: str) -> dict:
    """Count issues in each column."""
    # Use first available agent or 'sean' as fallback
    try:
        client = BoardClient(board_root, "sean")
    except Exception:
        # Try to get any agent
        temp_client = BoardClient(board_root, "sean")
        agents = temp_client.list_agents()
        if agents:
            client = BoardClient(board_root, agents[0]["id"])
        else:
            raise ValueError("No agents found on board")
    
    counts = {}
    for path, issue in client.iter_issues():
        column = issue.get("column", "unknown")
        counts[column] = counts.get(column, 0) + 1
    return counts


def get_agent_tasks(board_root: str, agent_id: str) -> dict:
    """Get tasks for an agent by column."""
    client = BoardClient(board_root, agent_id)
    tasks_by_column = {}
    for column in ["backlog", "todo", "doing", "done"]:
        tasks_json = client.list_my_issues(column=column, limit=100)
        tasks = json.loads(tasks_json)
        tasks_by_column[column] = tasks
    return tasks_by_column


def check_agent_log(board_root: str, agent_id: str) -> list:
    """Get recent log entries from agent log file."""
    workspace_path = Path(board_root) / "workspaces" / agent_id
    log_file = workspace_path / f"{agent_id}.log"
    
    if not log_file.exists():
        return []
    
    try:
        lines = log_file.read_text().strip().split('\n')
        return lines[-10:] if len(lines) > 10 else lines  # Last 10 lines
    except Exception:
        return []


def monitor_agents(board_root: str, agent_ids: list, interval: int = 5):
    """Monitor multiple agents."""
    print("=" * 80)
    print(f"Monitoring agents: {', '.join(agent_ids)}")
    print(f"Board: {board_root}")
    print(f"Update interval: {interval} seconds")
    print("=" * 80)
    print()
    
    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{timestamp}] Status Update")
            print("-" * 80)
            
            # Overall board status
            counts = count_issues_by_status(board_root)
            print(f"Board Status: {counts}")
            print()
            
            # Per-agent status
            for agent_id in agent_ids:
                print(f"Agent: {agent_id}")
                tasks = get_agent_tasks(board_root, agent_id)
                
                for column in ["backlog", "todo", "doing", "done"]:
                    task_list = tasks.get(column, [])
                    if task_list:
                        print(f"  {column:8s}: {len(task_list)} tasks")
                        for task in task_list[:2]:  # Show first 2
                            print(f"    - {task['id']}: {task['title'][:50]}")
                        if len(task_list) > 2:
                            print(f"    ... and {len(task_list) - 2} more")
                
                # Check log
                log_lines = check_agent_log(board_root, agent_id)
                if log_lines:
                    print(f"  Recent log entries:")
                    for line in log_lines[-3:]:  # Last 3 lines
                        print(f"    {line}")
                else:
                    print(f"  No log file yet")
                
                print()
            
            print("-" * 80)
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor agent progress")
    parser.add_argument(
        "--board-root",
        type=str,
        default="boards/crewkanteam",
        help="Board root directory"
    )
    parser.add_argument(
        "--agents",
        nargs="+",
        default=["docs", "developer", "tester"],
        help="Agent IDs to monitor"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Update interval in seconds"
    )
    
    args = parser.parse_args()
    
    monitor_agents(args.board_root, args.agents, args.interval)

