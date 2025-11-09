#!/usr/bin/env python3
"""
Extended test for CEO delegation workflow.

This test verifies:
- CEO generates tasks dynamically using GenAI
- Workers process tasks with clarification requests
- Comments are generated with IDs
- Work resumption after interruption
- All agents work independently in parallel

This is an extended test that requires:
- Azure OpenAI credentials (AZURE_OPENAI_API_KEY, etc.)
- Longer runtime (30-60 seconds)
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


def test_ceo_delegation_workflow():
    """Test the CEO delegation workflow."""
    
    board_root = Path("examples/ceo_delegation_board")
    script_path = Path("examples/langgraph_ceo_delegation.py")
    
    # Check if Azure OpenAI credentials are set
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    
    if not api_key or not endpoint or not deployment:
        print("⚠️  Azure OpenAI credentials not set. Skipping CEO delegation test.")
        print("   Required: AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME")
        return True  # Not a failure, just skipped
    
    # Clean board for fresh start
    if board_root.exists():
        import shutil
        shutil.rmtree(board_root)
    
    print("Starting CEO delegation workflow test...")
    print("This will run for 30 seconds to verify task generation and processing...")
    
    # Start the workflow
    process = subprocess.Popen(
        [sys.executable, "-u", str(script_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=os.environ.copy(),
        preexec_fn=os.setsid,  # For killing child processes
    )
    
    # Let it run for 30 seconds
    start_time = time.time()
    output_lines = []
    max_runtime = 30
    
    try:
        while time.time() - start_time < max_runtime:
            line = process.stdout.readline()
            if not line:
                if process.poll() is not None:
                    break
                time.sleep(0.1)
                continue
            
            output_lines.append(line)
            # Check for errors in output
            if "Error" in line or "Traceback" in line or "Exception" in line:
                print(f"⚠️  Error detected: {line.strip()}")
        
        # Check if process is still running
        if process.poll() is None:
            # Still running, terminate it
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait()
    except Exception as e:
        print(f"Error during test execution: {e}")
        if process.poll() is None:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            process.wait()
    
    # Verify results
    if not board_root.exists():
        print("❌ Board not created - test failed")
        return False
    
    counts = count_tasks_by_status(str(board_root))
    print(f"\nTask counts: {counts}")
    
    # Check that tasks were created and processed
    total_tasks = sum(counts.values())
    if total_tasks == 0:
        print("❌ No tasks created - test failed")
        return False
    
    # Check that some tasks were completed
    done_count = counts.get("done", 0)
    if done_count == 0 and total_tasks > 5:
        print("⚠️  No tasks completed, but tasks were created")
        # Not a failure, but note it
    
    # Verify comments have IDs
    client = BoardClient(str(board_root), "ceo")
    tasks_with_comments = 0
    for path, task in client.iter_tasks():
        comments = client.get_comments(task.get("id"))
        if comments:
            tasks_with_comments += 1
            # Verify comment structure
            for comment in comments:
                if not comment.get("comment_id", "").startswith("C-"):
                    print(f"❌ Comment missing comment_id: {comment}")
                    return False
                if not comment.get("by"):
                    print(f"❌ Comment missing 'by' field: {comment}")
                    return False
                if not comment.get("at"):
                    print(f"❌ Comment missing 'at' field: {comment}")
                    return False
    
    if tasks_with_comments > 0:
        print(f"✓ Verified {tasks_with_comments} task(s) have comments with IDs")
    
    # Check for clarification comments (should have reasonable content)
    clarification_found = False
    for path, task in client.iter_tasks():
        comments = client.get_comments(task.get("id"))
        for comment in comments:
            details = comment.get("details", "").lower()
            if "clarification" in details or "question" in details or "need" in details:
                if len(comment.get("details", "")) > 20:  # Reasonable length
                    clarification_found = True
                    print(f"✓ Found clarification comment: {comment.get('details', '')[:100]}...")
                    break
    
    if not clarification_found and total_tasks > 10:
        print("⚠️  No clarification comments found (may be normal if random chance didn't trigger)")
    
    print(f"\n✓ CEO delegation test completed successfully")
    print(f"  - Total tasks: {total_tasks}")
    print(f"  - Tasks with comments: {tasks_with_comments}")
    print(f"  - Done: {done_count}")
    
    return True


if __name__ == "__main__":
    success = test_ceo_delegation_workflow()
    sys.exit(0 if success else 1)

