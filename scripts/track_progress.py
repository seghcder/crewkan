#!/usr/bin/env python3
"""
Enhanced progress tracking for board owner.
Tracks multiple metrics to understand board health and agent productivity.
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.board_core import BoardClient, get_board_activity_logger


def get_comprehensive_status(board_root: str) -> dict:
    """Get comprehensive board status with multiple metrics."""
    client = BoardClient(board_root, "product-owner")
    
    status = {
        "timestamp": datetime.now().isoformat(),
        "issues_by_column": defaultdict(int),
        "issues_by_agent": defaultdict(int),
        "issues_by_priority": defaultdict(int),
        "issues_by_type": defaultdict(int),
        "issues_in_progress": [],
        "recently_completed": [],
        "stuck_issues": [],
        "agent_productivity": {},
        "completion_rate": {},
        "average_time_in_doing": {},
    }
    
    # Collect all issues
    all_issues = []
    for path, issue in client.iter_issues():
        all_issues.append(issue)
        col = issue.get("column", "unknown")
        status["issues_by_column"][col] += 1
        
        # By agent
        for assignee in issue.get("assignees", []):
            status["issues_by_agent"][assignee] += 1
        
        # By priority
        priority = issue.get("priority", "unknown")
        status["issues_by_priority"][priority] += 1
        
        # By type
        issue_type = issue.get("issue_type", "unknown")
        status["issues_by_type"][issue_type] += 1
        
        # In progress
        if col == "doing":
            status["issues_in_progress"].append({
                "id": issue.get("id"),
                "title": issue.get("title", "")[:60],
                "assignees": issue.get("assignees", []),
                "updated_at": issue.get("updated_at", ""),
                "age_minutes": None,
            })
            
            # Calculate age
            updated = issue.get("updated_at", "")
            if updated:
                try:
                    from dateutil import parser
                    updated_time = parser.parse(updated).timestamp()
                    age_minutes = (time.time() - updated_time) / 60
                    status["issues_in_progress"][-1]["age_minutes"] = age_minutes
                    
                    # Mark as stuck if > 10 minutes
                    if age_minutes > 10:
                        status["stuck_issues"].append({
                            "id": issue.get("id"),
                            "title": issue.get("title", "")[:60],
                            "assignee": issue.get("assignees", [""])[0] if issue.get("assignees") else "unassigned",
                            "age_minutes": age_minutes,
                        })
                except:
                    pass
        
        # Recently completed (last hour)
        if col == "done":
            updated = issue.get("updated_at", "")
            if updated:
                try:
                    from dateutil import parser
                    updated_time = parser.parse(updated).timestamp()
                    age_minutes = (time.time() - updated_time) / 60
                    if age_minutes < 60:  # Completed in last hour
                        status["recently_completed"].append({
                            "id": issue.get("id"),
                            "title": issue.get("title", "")[:60],
                            "assignees": issue.get("assignees", []),
                            "completed_minutes_ago": age_minutes,
                        })
                except:
                    pass
    
    # Calculate agent productivity (issues completed in last hour)
    for issue in status["recently_completed"]:
        for assignee in issue.get("assignees", []):
            if assignee not in status["agent_productivity"]:
                status["agent_productivity"][assignee] = 0
            status["agent_productivity"][assignee] += 1
    
    # Calculate average time in doing (for completed issues)
    doing_times = defaultdict(list)
    for issue in all_issues:
        if issue.get("column") == "done":
            history = issue.get("history", [])
            # Find when moved to doing and when moved to done
            moved_to_doing = None
            moved_to_done = None
            for entry in history:
                if entry.get("event") == "moved":
                    details = entry.get("details", "")
                    if "-> doing" in details or "todo -> doing" in details or "backlog -> doing" in details:
                        moved_to_doing = entry.get("at")
                    if "-> done" in details or "doing -> done" in details:
                        moved_to_done = entry.get("at")
            
            if moved_to_doing and moved_to_done:
                try:
                    from dateutil import parser
                    doing_start = parser.parse(moved_to_doing).timestamp()
                    done_time = parser.parse(moved_to_done).timestamp()
                    duration_minutes = (done_time - doing_start) / 60
                    
                    for assignee in issue.get("assignees", []):
                        doing_times[assignee].append(duration_minutes)
                except:
                    pass
    
    # Calculate averages
    for agent, times in doing_times.items():
        if times:
            status["average_time_in_doing"][agent] = sum(times) / len(times)
    
    # Calculate completion rate (completed / total)
    total = sum(status["issues_by_column"].values())
    done = status["issues_by_column"].get("done", 0)
    if total > 0:
        status["completion_rate"]["overall"] = (done / total) * 100
    else:
        status["completion_rate"]["overall"] = 0
    
    return status


def print_comprehensive_status(status: dict):
    """Print comprehensive status in a readable format."""
    print("=" * 80)
    print("COMPREHENSIVE BOARD STATUS")
    print("=" * 80)
    print(f"Timestamp: {status['timestamp']}\n")
    
    # Overall stats
    print("📊 OVERALL STATS")
    print(f"  Total issues: {sum(status['issues_by_column'].values())}")
    print(f"  Completion rate: {status['completion_rate']['overall']:.1f}%")
    print(f"  Issues by column: {dict(status['issues_by_column'])}")
    print()
    
    # Issues by agent
    print("👥 ISSUES BY AGENT")
    for agent, count in sorted(status['issues_by_agent'].items()):
        productivity = status['agent_productivity'].get(agent, 0)
        avg_time = status['average_time_in_doing'].get(agent, 0)
        print(f"  {agent}: {count} issues | {productivity} completed (last hour) | Avg time: {avg_time:.1f} min")
    print()
    
    # In progress
    print("🔄 ISSUES IN PROGRESS")
    if status['issues_in_progress']:
        for issue in status['issues_in_progress']:
            age = issue.get('age_minutes', 0)
            age_str = f"{age:.1f} min" if age else "unknown"
            print(f"  {issue['id']}: {issue['title']} (assigned to: {', '.join(issue['assignees'])}, age: {age_str})")
    else:
        print("  None")
    print()
    
    # Stuck issues
    if status['stuck_issues']:
        print("⚠️  STUCK ISSUES (>10 min in doing)")
        for issue in status['stuck_issues']:
            print(f"  {issue['id']}: {issue['title']} (assigned to: {issue['assignee']}, stuck for {issue['age_minutes']:.1f} min)")
        print()
    
    # Recently completed
    if status['recently_completed']:
        print("✅ RECENTLY COMPLETED (last hour)")
        for issue in status['recently_completed']:
            print(f"  {issue['id']}: {issue['title']} (completed {issue['completed_minutes_ago']:.1f} min ago)")
        print()
    
    # By priority
    print("🎯 ISSUES BY PRIORITY")
    for priority, count in sorted(status['issues_by_priority'].items()):
        print(f"  {priority}: {count}")
    print()
    
    # By type
    print("📋 ISSUES BY TYPE")
    for issue_type, count in sorted(status['issues_by_type'].items()):
        print(f"  {issue_type}: {count}")
    print()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Track comprehensive board progress")
    parser.add_argument("--board-root", default="boards/crewkanteam", help="Board root directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    status = get_comprehensive_status(args.board_root)
    
    if args.json:
        print(json.dumps(status, indent=2))
    else:
        print_comprehensive_status(status)


if __name__ == "__main__":
    main()

