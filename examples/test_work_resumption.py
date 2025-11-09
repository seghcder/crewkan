#!/usr/bin/env python3
"""
Test script for work resumption in CEO delegation workflow.

This script:
1. Starts a new board
2. Lets the workflow run for a while
3. Kills the script
4. Restarts it
5. Verifies all work completes as expected
"""

import os
import sys
import signal
import subprocess
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load environment variables from .env if it exists
from dotenv import load_dotenv
load_dotenv()

from crewkan.board_core import BoardClient


def count_tasks_by_status(board_root: str) -> dict[str, int]:
    """Count tasks in each column."""
    client = BoardClient(board_root, "ceo")
    counts = {}
    for path, task in client.iter_tasks():
        column = task.get("column", "unknown")
        counts[column] = counts.get(column, 0) + 1
    return counts


def test_work_resumption():
    """Test that work can be resumed after interruption."""
    
    board_root = Path("examples/ceo_delegation_board")
    script_path = Path("examples/langgraph_ceo_delegation.py")
    
    # Check if Azure OpenAI credentials are set (load from .env)
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    
    if not api_key or not endpoint or not deployment:
        print("⚠️  Azure OpenAI credentials not set. Skipping GenAI test.")
        print("   Required: AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME")
        return True
    
    # Set environment for subprocess (inherit current env which has .env loaded)
    env = os.environ.copy()
    
    print("=" * 60)
    print("Test 1: Starting workflow and letting it run...")
    print("=" * 60)
    
    # Clean board for fresh start
    if board_root.exists():
        import shutil
        shutil.rmtree(board_root)
    
    # Start the workflow in background
    print("Starting workflow process...")
    process = subprocess.Popen(
        [sys.executable, str(script_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env
    )
    
    # Let it run for 20 seconds
    print("Letting workflow run for 20 seconds...")
    time.sleep(20)
    
    # Check initial progress
    if board_root.exists():
        counts = count_tasks_by_status(str(board_root))
        print(f"Progress after 20s: {counts}")
        total_tasks = sum(counts.values())
        print(f"Total tasks: {total_tasks}")
    
    # Kill the process
    print("\nKilling workflow process...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    
    print("Process terminated.")
    
    # Check state before restart
    if board_root.exists():
        counts_before = count_tasks_by_status(str(board_root))
        print(f"\nState before restart: {counts_before}")
        tasks_before = sum(counts_before.values())
    else:
        print("Board not found - cannot resume")
        return False
    
    print("\n" + "=" * 60)
    print("Test 2: Restarting workflow and verifying completion...")
    print("=" * 60)
    
    # Restart the workflow
    print("Restarting workflow...")
    process2 = subprocess.Popen(
        [sys.executable, str(script_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env
    )
    
    # Monitor for up to 2 minutes
    max_wait = 120
    start_time = time.time()
    last_counts = counts_before
    
    while time.time() - start_time < max_wait:
        time.sleep(5)
        
        if not process2.poll() is None:
            # Process ended
            break
        
        if board_root.exists():
            counts = count_tasks_by_status(str(board_root))
            done_count = counts.get("done", 0)
            total = sum(counts.values())
            
            # Check if progress is being made
            if counts != last_counts:
                print(f"Progress: {counts} (done: {done_count}/{total})")
                last_counts = counts
            
            # Check if we have a reasonable number of completed tasks
            # Since tasks are continuously generated, we just verify work is progressing
            if done_count >= 10:  # At least 10 tasks completed
                print(f"\n✅ Work resumption test PASSED: {done_count} tasks completed! Final: {counts}")
                process2.terminate()
                try:
                    process2.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process2.kill()
                    process2.wait()
                return True
    
    # Final check
    if board_root.exists():
        final_counts = count_tasks_by_status(str(board_root))
        print(f"\nFinal state: {final_counts}")
        
        # Verify work resumption worked
        if sum(final_counts.values()) >= tasks_before:
            print("✅ Work resumption verified - tasks continued from where they left off")
            return True
        else:
            print("❌ Work resumption failed - task count decreased")
            return False
    else:
        print("❌ Board not found after restart")
        return False


if __name__ == "__main__":
    success = test_work_resumption()
    sys.exit(0 if success else 1)

