#!/usr/bin/env python3
"""
Check individual agent status and detect stuck agents.
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.board_core import BoardClient
from dateutil import parser


def check_agent_activity(board_root: str, agent_id: str, since_minutes: int = 5) -> dict:
    """Check activity for a specific agent."""
    activity_log = Path(board_root) / "board_activity.log"
    
    if not activity_log.exists():
        return {"has_activity": False, "last_activity_minutes_ago": None, "recent_actions": []}
    
    try:
        with open(activity_log, 'r') as f:
            lines = f.readlines()
        
        agent_actions = []
        cutoff_time = time.time() - (since_minutes * 60)
        
        for line in lines:
            if f"AGENT:{agent_id}" in line:
                try:
                    parts = line.split(" | ")
                    if len(parts) >= 2:
                        timestamp_str = parts[0]
                        log_time = parser.parse(timestamp_str).timestamp()
                        if log_time >= cutoff_time:
                            agent_actions.append({
                                "time": log_time,
                                "line": line.strip(),
                                "action": parts[2].split(":")[1] if len(parts) > 2 else "unknown"
                            })
                except Exception as e:
                    pass
        
        # Find most recent activity
        last_activity_minutes_ago = None
        if agent_actions:
            most_recent = max(a["time"] for a in agent_actions)
            last_activity_minutes_ago = (time.time() - most_recent) / 60
        
        return {
            "has_activity": len(agent_actions) > 0,
            "last_activity_minutes_ago": last_activity_minutes_ago,
            "recent_actions": sorted(agent_actions, key=lambda x: x["time"], reverse=True)[:5],
        }
    except Exception as e:
        return {"has_activity": False, "last_activity_minutes_ago": None, "recent_actions": [], "error": str(e)}


def check_agent_issues(board_root: str, agent_id: str) -> dict:
    """Check issues assigned to an agent."""
    client = BoardClient(board_root, "product-owner")
    
    agent_issues = {
        "doing": [],
        "todo": [],
        "backlog": [],
        "stuck_issues": [],
    }
    
    current_time = time.time()
    
    for path, issue in client.iter_issues():
        assignees = issue.get("assignees", [])
        if agent_id in assignees:
            col = issue.get("column", "unknown")
            if col in agent_issues:
                agent_issues[col].append({
                    "id": issue.get("id"),
                    "title": issue.get("title", "")[:60],
                    "updated_at": issue.get("updated_at"),
                    "age_minutes": None,
                })
                
                # Check if stuck (no update in last 10 minutes)
                updated = issue.get("updated_at", "")
                if updated and col == "doing":
                    try:
                        updated_time = parser.parse(updated).timestamp()
                        age_minutes = (current_time - updated_time) / 60
                        agent_issues[col][-1]["age_minutes"] = age_minutes
                        if age_minutes > 10:
                            agent_issues["stuck_issues"].append(agent_issues[col][-1])
                    except:
                        pass
    
    return agent_issues


def get_agent_status(board_root: str, agent_id: str) -> dict:
    """Get comprehensive status for an agent."""
    activity = check_agent_activity(board_root, agent_id, since_minutes=10)
    issues = check_agent_issues(board_root, agent_id)
    
    return {
        "agent_id": agent_id,
        "activity": activity,
        "issues": issues,
        "is_stuck": len(issues["stuck_issues"]) > 0 or (activity.get("last_activity_minutes_ago") and activity["last_activity_minutes_ago"] > 10),
    }


def main():
    """Check all agent statuses."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check agent status")
    parser.add_argument("--board-root", default="boards/crewkanteam", help="Board root directory")
    parser.add_argument("--agent", help="Check specific agent only")
    
    args = parser.parse_args()
    
    client = BoardClient(args.board_root, "product-owner")
    agents = client.list_agents()
    
    ai_agents = [a for a in agents if a.get("kind") == "ai" and a.get("status") == "active"]
    
    if args.agent:
        ai_agents = [a for a in ai_agents if a["id"] == args.agent]
        if not ai_agents:
            print(f"Agent '{args.agent}' not found")
            return 1
    
    print("=" * 60)
    print("Agent Status Check")
    print("=" * 60)
    print(f"Board: {args.board_root}\n")
    
    stuck_agents = []
    
    for agent in ai_agents:
        agent_id = agent["id"]
        status = get_agent_status(args.board_root, agent_id)
        
        print(f"Agent: {agent_id}")
        print(f"  Activity: ", end="")
        
        if status["activity"]["has_activity"]:
            age = status["activity"]["last_activity_minutes_ago"]
            print(f"✅ Active ({age:.1f} min ago)")
            if status["activity"]["recent_actions"]:
                print(f"  Recent actions:")
                for action in status["activity"]["recent_actions"][:3]:
                    action_type = action.get("action", "unknown")
                    print(f"    - {action_type}")
        else:
            age = status["activity"]["last_activity_minutes_ago"]
            if age:
                print(f"⚠️  Inactive ({age:.1f} min ago)")
            else:
                print("❌ No recent activity")
        
        print(f"  Issues:")
        print(f"    Doing: {len(status['issues']['doing'])}")
        print(f"    Todo: {len(status['issues']['todo'])}")
        print(f"    Backlog: {len(status['issues']['backlog'])}")
        
        if status["issues"]["stuck_issues"]:
            print(f"  ⚠️  Stuck issues: {len(status['issues']['stuck_issues'])}")
            for stuck in status["issues"]["stuck_issues"]:
                print(f"    - {stuck['id']}: {stuck['title']} (stuck {stuck['age_minutes']:.1f} min)")
        
        if status["is_stuck"]:
            stuck_agents.append(agent_id)
            print(f"  🔴 AGENT IS STUCK")
        
        print()
    
    if stuck_agents:
        print(f"⚠️  Stuck agents detected: {', '.join(stuck_agents)}")
        return 1
    else:
        print("✅ All agents are active")
        return 0


if __name__ == "__main__":
    sys.exit(main())

