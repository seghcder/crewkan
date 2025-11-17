#!/usr/bin/env python3
"""
Monitor the CrewKan team board status and detect bottlenecks.
"""

import sys
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.board_core import BoardClient

# Set up logging
logger = logging.getLogger(__name__)


def get_board_status(board_root: str) -> dict:
    """Get current board status."""
    client = BoardClient(board_root, "sean")
    
    status = {
        "timestamp": time.time(),
        "issues_by_column": defaultdict(int),
        "issues_by_agent": defaultdict(int),
        "issues_in_progress": [],
        "recent_activity": [],
    }
    
    # Count issues by column and agent
    for path, issue in client.iter_issues():
        col = issue.get("column", "unknown")
        status["issues_by_column"][col] += 1
        
        assignees = issue.get("assignees", [])
        for assignee in assignees:
            status["issues_by_agent"][assignee] += 1
        
        if col == "doing":
            status["issues_in_progress"].append({
                "id": issue.get("id"),
                "title": issue.get("title", "")[:60],
                "assignees": assignees,
                "updated_at": issue.get("updated_at"),
            })
    
    # Get recent activity from issue history
    for path, issue in client.iter_issues():
        history = issue.get("history", [])
        if history:
            last_event = history[-1]
            status["recent_activity"].append({
                "issue_id": issue.get("id"),
                "event": last_event.get("event"),
                "by": last_event.get("by"),
                "at": last_event.get("at"),
            })
    
    # Sort by timestamp
    status["recent_activity"].sort(key=lambda x: x.get("at", ""), reverse=True)
    
    return status


def detect_bottleneck(status: dict, previous_status: dict = None) -> dict:
    """Detect bottlenecks and issues."""
    issues = []
    
    # Check if nothing is moving
    if previous_status:
        prev_counts = previous_status.get("issues_by_column", {})
        curr_counts = status.get("issues_by_column", {})
        
        # Check if counts haven't changed
        if prev_counts == curr_counts:
            issues.append({
                "type": "no_movement",
                "severity": "high",
                "message": "No issues have moved between columns",
            })
        
        # Check if doing column is stuck
        prev_doing = set(i["id"] for i in previous_status.get("issues_in_progress", []))
        curr_doing = set(i["id"] for i in status.get("issues_in_progress", []))
        
        if prev_doing == curr_doing and len(curr_doing) > 0:
            stuck_issues = [i for i in status["issues_in_progress"] if i["id"] in prev_doing]
            issues.append({
                "type": "stuck_issues",
                "severity": "high",
                "message": f"{len(stuck_issues)} issues stuck in 'doing'",
                "stuck_issues": stuck_issues,
            })
    
    # Check for agents with no work
    issues_by_agent = status.get("issues_by_agent", {})
    all_agents = get_all_agents(status.get("board_root", "boards/crewkanteam"))
    agents_with_no_work = [a for a in all_agents if issues_by_agent.get(a, 0) == 0]
    
    if agents_with_no_work:
        issues.append({
            "type": "idle_agents",
            "severity": "medium",
            "message": f"Agents with no assigned work: {', '.join(agents_with_no_work)}",
            "agents": agents_with_no_work,
        })
    
    # Check for backlog buildup
    backlog_count = status.get("issues_by_column", {}).get("backlog", 0)
    if backlog_count > 10:
        issues.append({
            "type": "backlog_buildup",
            "severity": "medium",
            "message": f"Large backlog: {backlog_count} issues",
        })
    
    return {
        "detected_at": datetime.now().isoformat(),
        "issues": issues,
    }


def get_all_agents(board_root: str) -> list:
    """Get list of all active AI agents."""
    client = BoardClient(board_root, "sean")
    all_agents = client.list_agents()
    return [a["id"] for a in all_agents if a.get("status") == "active" and a.get("kind") == "ai"]


def suggest_remediation(bottleneck: dict, status: dict) -> list:
    """Suggest remediation actions."""
    suggestions = []
    
    for issue in bottleneck.get("issues", []):
        if issue["type"] == "stuck_issues":
            stuck = issue.get("stuck_issues", [])
            for stuck_issue in stuck:
                suggestions.append({
                    "action": "reassign",
                    "issue_id": stuck_issue["id"],
                    "reason": f"Issue {stuck_issue['id']} has been stuck in 'doing'",
                    "suggestion": f"Reassign {stuck_issue['id']} to another agent or move back to todo",
                })
        
        elif issue["type"] == "idle_agents":
            agents = issue.get("agents", [])
            # Find issues in backlog that could be assigned
            backlog_issues = []
            client = BoardClient(status.get("board_root", "boards/crewkanteam"), "sean")
            for path, issue_data in client.iter_issues():
                if issue_data.get("column") == "backlog":
                    backlog_issues.append(issue_data)
            
            if backlog_issues and agents:
                suggestions.append({
                    "action": "assign_work",
                    "reason": f"Agents {', '.join(agents)} have no work",
                    "suggestion": f"Assign backlog issues to idle agents",
                    "agents": agents,
                    "available_issues": [i.get("id") for i in backlog_issues[:len(agents)]],
                })
        
        elif issue["type"] == "no_movement":
            suggestions.append({
                "action": "investigate",
                "reason": "No activity detected",
                "suggestion": "Check if agents are running, check logs, verify board state",
            })
    
    return suggestions


def print_status(status: dict, bottleneck: dict = None, suggestions: list = None):
    """Print formatted status."""
    print("\n" + "=" * 60)
    print(f"Board Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Issues by column
    print("\n📊 Issues by Status:")
    for col, count in sorted(status.get("issues_by_column", {}).items()):
        print(f"  {col:12}: {count}")
    
    # Issues by agent
    print("\n👥 Issues by Agent:")
    for agent, count in sorted(status.get("issues_by_agent", {}).items()):
        print(f"  {agent:12}: {count}")
    
    # Issues in progress
    in_progress = status.get("issues_in_progress", [])
    if in_progress:
        print("\n🔄 Issues in Progress:")
        for issue in in_progress:
            assignees = ", ".join(issue.get("assignees", []))
            print(f"  {issue['id']}: {issue['title']} (assigned to: {assignees})")
    
    # Bottlenecks
    if bottleneck and bottleneck.get("issues"):
        print("\n⚠️  Detected Issues:")
        for issue in bottleneck["issues"]:
            severity_icon = "🔴" if issue["severity"] == "high" else "🟡"
            print(f"  {severity_icon} {issue['message']}")
    
    # Suggestions
    if suggestions:
        print("\n💡 Suggested Actions:")
        for suggestion in suggestions:
            print(f"  • {suggestion['suggestion']}")
            if "available_issues" in suggestion:
                print(f"    Issues to assign: {', '.join(suggestion['available_issues'])}")


def main():
    """Main monitoring loop."""
    board_root = "boards/crewkanteam"
    check_interval = 60  # Check every 60 seconds
    no_movement_threshold = 120  # 2 minutes
    
    print("Starting board monitor...")
    print(f"Check interval: {check_interval}s")
    print(f"No movement threshold: {no_movement_threshold}s")
    print("Press Ctrl+C to stop\n")
    
    previous_status = None
    last_change_time = time.time()
    
    try:
        while True:
            status = get_board_status(board_root)
            status["board_root"] = board_root
            
            # Check for changes
            has_changes = False
            if previous_status:
                prev_counts = previous_status.get("issues_by_column", {})
                curr_counts = status.get("issues_by_column", {})
                if prev_counts != curr_counts:
                    has_changes = True
                    last_change_time = time.time()
            
            # Detect bottlenecks
            bottleneck = None
            suggestions = []
            
            time_since_last_change = time.time() - last_change_time
            if time_since_last_change >= no_movement_threshold:
                bottleneck = detect_bottleneck(status, previous_status)
                if bottleneck.get("issues"):
                    suggestions = suggest_remediation(bottleneck, status)
            
    # Print status
    print_status(status, bottleneck, suggestions)
    
    # Append status to board_status.md
    try:
        subprocess.run([sys.executable, "scripts/check_board_status.py"],
                      cwd=Path(__file__).parent.parent,
                      capture_output=True)
    except Exception as e:
        logger.warning(f"Failed to write status summary: {e}")
    
    # Take action if needed
    if suggestions:
        print("\n🔧 Taking automatic remediation actions...")
        client = BoardClient(board_root, "sean")
        
        for suggestion in suggestions:
                    if suggestion["action"] == "assign_work":
                        agents = suggestion.get("agents", [])
                        issues = suggestion.get("available_issues", [])
                        for agent, issue_id in zip(agents, issues):
                            try:
                                client.reassign_issue(issue_id, agent, keep_existing=False)
                                print(f"  ✓ Assigned {issue_id} to {agent}")
                            except Exception as e:
                                print(f"  ✗ Failed to assign {issue_id} to {agent}: {e}")
            
            previous_status = status
            
            # Wait for next check
            print(f"\n⏳ Next check in {check_interval} seconds...\n")
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        print("\n\nMonitor stopped")


if __name__ == "__main__":
    main()

