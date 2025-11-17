#!/usr/bin/env python3
"""
Monitor board progress every 60 seconds, fix issues immediately if detected in logs,
but wait 5 minutes before investigating "busy" agents.
"""

import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.board_core import BoardClient
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_log_errors(board_root: str) -> list:
    """Check board runner log for errors."""
    log_file = Path(board_root) / ".board_runner.log"
    if not log_file.exists():
        return []
    
    errors = []
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            # Check last 50 lines for errors
            for line in lines[-50:]:
                if any(keyword in line.lower() for keyword in ['error', 'exception', 'traceback', 'failed']):
                    errors.append(line.strip())
    except Exception as e:
        logger.warning(f"Error reading log file: {e}")
    
    return errors


def check_activity_log(board_root: str, since_minutes: int = 5) -> dict:
    """Check board activity log for recent activity."""
    log_file = Path(board_root) / "board_activity.log"
    if not log_file.exists():
        return {"has_activity": False, "last_activity_minutes_ago": None, "recent_actions": []}
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        recent_actions = []
        cutoff_time = time.time() - (since_minutes * 60)
        
        for line in lines[-100:]:  # Check last 100 lines
            if "| ACTION:" in line:
                # Parse timestamp from log line
                try:
                    # Format: "2025-11-18 10:28:51 | ..."
                    parts = line.split(" | ")
                    if len(parts) >= 2:
                        timestamp_str = parts[0]
                        from dateutil import parser
                        log_time = parser.parse(timestamp_str).timestamp()
                        if log_time >= cutoff_time:
                            recent_actions.append(line.strip())
                except:
                    pass
        
        # Find most recent activity
        last_activity_minutes_ago = None
        if lines:
            try:
                last_line = lines[-1]
                parts = last_line.split(" | ")
                if len(parts) >= 2:
                    timestamp_str = parts[0]
                    from dateutil import parser
                    last_time = parser.parse(timestamp_str).timestamp()
                    last_activity_minutes_ago = (time.time() - last_time) / 60
            except:
                pass
        
        return {
            "has_activity": len(recent_actions) > 0,
            "last_activity_minutes_ago": last_activity_minutes_ago,
            "recent_actions": recent_actions[-10:],  # Last 10 actions
        }
    except Exception as e:
        logger.warning(f"Error reading activity log: {e}")
        return {"has_activity": False, "last_activity_minutes_ago": None, "recent_actions": []}


def check_board_runner_status() -> dict:
    """Check if board runner is running."""
    try:
        result = subprocess.run(
            [sys.executable, "scripts/run_board_background.py", "status"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=5
        )
        is_running = "running" in result.stdout.lower() and "not" not in result.stdout.lower()
        return {"is_running": is_running, "output": result.stdout}
    except Exception as e:
        logger.warning(f"Error checking board runner status: {e}")
        return {"is_running": False, "output": str(e)}


def fix_immediate_issues(board_root: str, errors: list, runner_status: dict) -> bool:
    """Fix immediate issues detected in logs or runner status."""
    fixed = False
    
    # Check if runner is not running
    if not runner_status.get("is_running", False):
        logger.warning("⚠️  Board runner is not running! Restarting...")
        try:
            subprocess.run(
                [sys.executable, "scripts/run_board_background.py", "start"],
                cwd=Path(__file__).parent.parent,
                timeout=10
            )
            logger.info("✅ Board runner restarted")
            fixed = True
        except Exception as e:
            logger.error(f"❌ Failed to restart board runner: {e}")
    
    # Check for critical errors in logs
    if errors:
        critical_errors = [e for e in errors if any(kw in e.lower() for kw in ['unboundlocalerror', 'syntaxerror', 'importerror', 'attributeerror'])]
        if critical_errors:
            logger.error(f"⚠️  Critical errors detected in logs:")
            for err in critical_errors[-3:]:  # Show last 3
                logger.error(f"  {err[:200]}")
            # Could add auto-fix logic here for known issues
            fixed = True
    
    return fixed


def investigate_agent_status(board_root: str) -> dict:
    """Investigate why agents might not be making progress."""
    client = BoardClient(board_root, "product-owner")
    
    # Get all issues in "doing"
    doing_issues = []
    for path, issue in client.iter_issues():
        if issue.get("column") == "doing":
            doing_issues.append(issue)
    
    # Check for stuck issues (no update in last 10 minutes)
    stuck_issues = []
    current_time = time.time()
    
    for issue in doing_issues:
        updated = issue.get("updated_at", "")
        if updated:
            try:
                from dateutil import parser
                updated_time = parser.parse(updated).timestamp()
                age_minutes = (current_time - updated_time) / 60
                if age_minutes > 10:
                    stuck_issues.append({
                        "id": issue.get("id"),
                        "title": issue.get("title", "")[:50],
                        "age_minutes": age_minutes,
                        "assignees": issue.get("assignees", []),
                    })
            except:
                pass
    
    return {
        "doing_count": len(doing_issues),
        "stuck_issues": stuck_issues,
    }


def main():
    """Main monitoring loop."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor board and auto-fix issues")
    parser.add_argument("--max-duration", type=int, default=1800, help="Maximum duration to run in seconds (default: 1800 = 30 min)")
    parser.add_argument("--check-interval", type=int, default=60, help="Check interval in seconds (default: 60)")
    parser.add_argument("--busy-threshold", type=int, default=5, help="Wait time before investigating busy agents in minutes (default: 5)")
    
    args = parser.parse_args()
    
    board_root = "boards/crewkanteam"
    check_interval = args.check_interval
    busy_agent_threshold = args.busy_threshold
    max_duration = args.max_duration
    start_time = time.time()
    
    print("=" * 60)
    print("Board Monitor & Auto-Fix")
    print("=" * 60)
    print(f"Board: {board_root}")
    print(f"Check interval: {check_interval}s")
    print(f"Busy agent investigation threshold: {busy_agent_threshold} minutes")
    print(f"Max duration: {max_duration}s ({max_duration/60:.1f} minutes)")
    print("Press Ctrl+C to stop\n")
    
    last_investigation_time = time.time()
    consecutive_no_progress = 0
    
    try:
        while True:
            # Check if we've exceeded max duration
            elapsed = time.time() - start_time
            if elapsed >= max_duration:
                print(f"\n⏱️  Maximum duration reached ({max_duration}s)")
                break
            check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{check_time}] Checking board status...")
            
            # 1. Check for immediate issues (logs, runner status)
            runner_status = check_board_runner_status()
            log_errors = check_log_errors(board_root)
            
            immediate_fix_needed = not runner_status.get("is_running", False) or bool(log_errors)
            
            if immediate_fix_needed:
                print("🔧 Immediate issues detected - fixing now...")
                fixed = fix_immediate_issues(board_root, log_errors, runner_status)
                if fixed:
                    print("✅ Immediate issues fixed")
                    consecutive_no_progress = 0  # Reset counter
                else:
                    print("⚠️  Could not fix all immediate issues")
            
            # 2. Check activity log for recent progress
            activity = check_activity_log(board_root, since_minutes=busy_agent_threshold)
            
            if activity.get("has_activity"):
                print(f"✅ Recent activity detected (last {activity.get('last_activity_minutes_ago', 0):.1f} min ago)")
                consecutive_no_progress = 0
                last_investigation_time = time.time()
            else:
                consecutive_no_progress += 1
                age = activity.get("last_activity_minutes_ago")
                if age:
                    print(f"⚠️  No activity in last {age:.1f} minutes")
                else:
                    print("⚠️  No activity log found")
            
            # 3. Check board status using check script
            try:
                result = subprocess.run(
                    [sys.executable, "scripts/check_board_status.py", "--no-append"],
                    cwd=Path(__file__).parent.parent,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    # Print summary (last few lines)
                    lines = result.stdout.strip().split('\n')
                    for line in lines[-5:]:
                        if line.strip():
                            print(line)
            except Exception as e:
                logger.warning(f"Error running status check: {e}")
            
            # 4. If no progress for threshold time, investigate agents
            time_since_investigation = time.time() - last_investigation_time
            if time_since_investigation >= (busy_agent_threshold * 60) and not activity.get("has_activity"):
                print(f"\n🔍 Investigating agent status (no progress for {busy_agent_threshold} minutes)...")
                agent_status = investigate_agent_status(board_root)
                
                print(f"  Issues in 'doing': {agent_status['doing_count']}")
                if agent_status['stuck_issues']:
                    print(f"  ⚠️  Found {len(agent_status['stuck_issues'])} stuck issues:")
                    for stuck in agent_status['stuck_issues']:
                        assignees = ", ".join(stuck['assignees'])
                        print(f"    - {stuck['id']}: {stuck['title']} (stuck {stuck['age_minutes']:.1f} min, assigned to: {assignees})")
                    
                    # Try to reassign stuck issues
                    print("  🔧 Attempting to reassign stuck issues...")
                    client = BoardClient(board_root, "product-owner")
                    agents = client.list_agents()
                    available_agents = [a['id'] for a in agents if a.get('status') == 'active' and a.get('kind') == 'ai']
                    
                    for stuck in agent_status['stuck_issues'][:3]:  # Max 3 reassignments
                        current_assignees = set(stuck['assignees'])
                        new_agent = None
                        for agent_id in available_agents:
                            if agent_id not in current_assignees:
                                new_agent = agent_id
                                break
                        
                        if new_agent:
                            try:
                                client.reassign_issue(stuck['id'], new_agent, keep_existing=False)
                                print(f"    ✓ Reassigned {stuck['id']} to {new_agent}")
                            except Exception as e:
                                print(f"    ✗ Failed to reassign {stuck['id']}: {e}")
                
                last_investigation_time = time.time()
            
            # Wait for next check
            elapsed = time.time() - start_time
            remaining = max_duration - elapsed
            if remaining <= check_interval:
                print(f"\n⏱️  Approaching time limit, finishing...")
                break
            print(f"\n⏳ Next check in {check_interval} seconds... (elapsed: {elapsed/60:.1f} min, remaining: {remaining/60:.1f} min)")
            time.sleep(check_interval)
    
    except KeyboardInterrupt:
        print("\n\nMonitor stopped by user")
    
    finally:
        elapsed = time.time() - start_time
        print(f"\n✅ Monitor completed (ran for {elapsed/60:.1f} minutes)")
        print("Final status check:")
        try:
            subprocess.run(
                [sys.executable, "scripts/check_board_status.py", "--no-append"],
                cwd=Path(__file__).parent.parent,
                timeout=10
            )
        except Exception as e:
            logger.warning(f"Error running final status check: {e}")


if __name__ == "__main__":
    main()

