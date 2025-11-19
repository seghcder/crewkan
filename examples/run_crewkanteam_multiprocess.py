#!/usr/bin/env python3
"""
Multiprocessing coordinator for running multiple CrewKan agents in parallel.

This script launches multiple agent processes and coordinates them.
Each agent can also be run independently using agent_runner.py.
"""

import os
import sys
import asyncio
import multiprocessing
import signal
import json
import time
import logging
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load environment variables from .env if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

from crewkan.board_core import BoardClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_agent_process(agent_id: str, board_root: str, max_iterations: int = None, poll_interval: float = 5.0):
    """
    Run an agent in a separate process.
    
    This function is called by multiprocessing.Process.
    """
    import asyncio
    from crewkan.agent_runner import main as agent_main
    
    try:
        asyncio.run(agent_main(
            agent_id=agent_id,
            board_root=board_root,
            max_iterations=max_iterations,
            poll_interval=poll_interval
        ))
    except Exception as e:
        logger.error(f"Agent {agent_id} process failed: {e}", exc_info=True)


def count_issues_by_status(board_root: str) -> Dict[str, int]:
    """Count issues in each column."""
    client = BoardClient(board_root, "system")
    counts = {}
    for path, issue in client.iter_issues():
        column = issue.get("column", "unknown")
        counts[column] = counts.get(column, 0) + 1
    return counts


def main(
    board_root: str,
    max_duration_seconds: int = None,
    max_iterations: int = None,
    poll_interval: float = 5.0
):
    """
    Main coordinator function.
    
    Args:
        board_root: Board root directory
        max_duration_seconds: Maximum duration to run (None for unlimited)
        max_iterations: Maximum iterations per agent (None for unlimited)
        poll_interval: Seconds between agent cycles
    """
    board_root = Path(board_root).resolve()
    
    print("=" * 60)
    print("Starting CrewKan Team Board (Multiprocessing)")
    print(f"Board: {board_root}")
    if max_duration_seconds:
        print(f"Running for up to {max_duration_seconds} seconds")
    else:
        print("Running until stopped")
    print("=" * 60)
    
    # Get all active AI agents (use 'sean' to access board)
    temp_client = BoardClient(str(board_root), "sean")
    all_agents = temp_client.list_agents()
    agent_ids = [
        a["id"] for a in all_agents
        if a.get("status") == "active" and a.get("kind") == "ai"
    ]
    
    if not agent_ids:
        print("No active AI agents found on board")
        return
    
    print(f"Found {len(agent_ids)} active AI agents: {', '.join(agent_ids)}")
    
    # Create shutdown file if needed
    shutdown_file = board_root / ".shutdown_requested"
    if shutdown_file.exists():
        shutdown_file.unlink()  # Clear any existing shutdown request
    
    # Start agent processes
    processes: List[multiprocessing.Process] = []
    
    try:
        for agent_id in agent_ids:
            logger.info(f"Starting process for agent {agent_id}")
            process = multiprocessing.Process(
                target=run_agent_process,
                args=(agent_id, str(board_root), max_iterations, poll_interval),
                name=f"agent-{agent_id}"
            )
            process.start()
            processes.append(process)
            logger.info(f"Started process {process.pid} for agent {agent_id}")
        
        print(f"\nStarted {len(processes)} agent processes")
        print("Press Ctrl+C to stop all agents gracefully\n")
        
        # Monitor processes
        start_time = time.time()
        status_interval = 30  # Print status every 30 seconds
        last_status_time = start_time
        
        while True:
            # Check if any process has died
            dead_processes = [p for p in processes if not p.is_alive()]
            if dead_processes:
                for p in dead_processes:
                    logger.warning(f"Process {p.name} (PID {p.pid}) has died")
                    processes.remove(p)
            
            if not processes:
                logger.error("All agent processes have died")
                break
            
            # Check time limit
            elapsed = time.time() - start_time
            if max_duration_seconds and elapsed >= max_duration_seconds - 60:
                # Request graceful shutdown 60 seconds before time limit
                if not shutdown_file.exists():
                    logger.info("Requesting graceful shutdown (60s grace period)")
                    shutdown_data = {
                        "requested_at": time.time(),
                        "deadline": time.time() + 60,
                        "grace_period": 60,
                    }
                    shutdown_file.write_text(json.dumps(shutdown_data, indent=2))
            
            if max_duration_seconds and elapsed >= max_duration_seconds:
                logger.info(f"Time limit reached ({max_duration_seconds}s)")
                break
            
            # Print status periodically
            if time.time() - last_status_time >= status_interval:
                counts = count_issues_by_status(str(board_root))
                print(f"\n📊 Elapsed: {elapsed:.1f}s, Active processes: {len(processes)}, Status: {counts}")
                last_status_time = time.time()
            
            # Sleep briefly
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nInterrupted by user, requesting graceful shutdown...")
        shutdown_data = {
            "requested_at": time.time(),
            "deadline": time.time() + 30,  # 30 second grace period
            "grace_period": 30,
        }
        shutdown_file.write_text(json.dumps(shutdown_data, indent=2))
        
        # Wait for processes to finish
        logger.info("Waiting for agents to finish gracefully...")
        for process in processes:
            process.join(timeout=35)  # Wait up to 35 seconds
            if process.is_alive():
                logger.warning(f"Process {process.name} did not finish gracefully, terminating")
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    logger.error(f"Process {process.name} did not terminate, killing")
                    process.kill()
    
    finally:
        # Cleanup
        if shutdown_file.exists():
            shutdown_file.unlink()
        
        # Final status
        print("\n" + "=" * 60)
        print("Workflow completed!")
        final_counts = count_issues_by_status(str(board_root))
        print(f"Final status: {final_counts}")
        print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run multiple CrewKan agents in parallel using multiprocessing"
    )
    parser.add_argument(
        "--board-root",
        type=str,
        default="boards/crewkanteam",
        help="Board root directory (default: boards/crewkanteam)"
    )
    parser.add_argument(
        "--max-duration",
        type=int,
        default=None,
        help="Maximum duration in seconds (default: unlimited)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum iterations per agent (default: unlimited)"
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
        help="Seconds between agent cycles (default: 5.0)"
    )
    
    args = parser.parse_args()
    
    main(
        board_root=args.board_root,
        max_duration_seconds=args.max_duration,
        max_iterations=args.max_iterations,
        poll_interval=args.poll_interval
    )

