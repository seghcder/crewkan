#!/usr/bin/env python3
"""
Check board status and append summary to board_status.md
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.board_core import BoardClient


def get_board_summary(board_root: str, previous_status: dict = None) -> dict:
    """Get current board status summary."""
    client = BoardClient(board_root, "sean")
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "issues_by_column": defaultdict(int),
        "issues_by_agent": defaultdict(int),
        "issues_in_progress": [],
        "recent_completions": [],
        "changes": {},
        "most_recent_update_age_minutes": None,
        "total_issues": 0,
    }
    
    # Count issues by column and agent
    last_updates = []
    for path, issue in client.iter_issues():
        col = issue.get("column", "unknown")
        summary["issues_by_column"][col] += 1
        summary["total_issues"] += 1
        
        assignees = issue.get("assignees", [])
        for assignee in assignees:
            summary["issues_by_agent"][assignee] += 1
        
        updated = issue.get("updated_at", "")
        if updated:
            try:
                from dateutil import parser
                updated_time = parser.parse(updated).timestamp()
                last_updates.append(updated_time)
            except:
                pass
        
        if col == "doing":
            summary["issues_in_progress"].append({
                "id": issue.get("id"),
                "title": issue.get("title", "")[:60],
                "assignees": assignees,
                "updated_at": issue.get("updated_at"),
            })
        
        if col == "done":
            summary["recent_completions"].append({
                "id": issue.get("id"),
                "title": issue.get("title", "")[:60],
                "updated_at": issue.get("updated_at"),
            })
    
    # Calculate most recent update age
    if last_updates:
        most_recent = max(last_updates)
        summary["most_recent_update_age_minutes"] = (time.time() - most_recent) / 60
    
    # Compare with previous status
    if previous_status:
        prev_counts = previous_status.get("issues_by_column", {})
        curr_counts = summary["issues_by_column"]
        
        changes = {}
        for col in set(list(prev_counts.keys()) + list(curr_counts.keys())):
            prev_count = prev_counts.get(col, 0)
            curr_count = curr_counts.get(col, 0)
            if prev_count != curr_count:
                changes[col] = curr_count - prev_count
        
        summary["changes"] = changes
    
    return summary


def format_summary_markdown(summary: dict) -> str:
    """Format summary as markdown."""
    lines = []
    lines.append(f"## {summary['timestamp']}")
    lines.append("")
    
    # Progress indicator
    age = summary.get("most_recent_update_age_minutes")
    if age is not None:
        if age > 4.5:
            lines.append(f"⚠️  **WARNING**: No progress detected in last {age:.1f} minutes")
        else:
            lines.append(f"✅ Most recent update: {age:.1f} minutes ago")
        lines.append("")
    
    # Status by column
    lines.append("### Issues by Status")
    total = summary.get("total_issues", sum(summary["issues_by_column"].values()))
    lines.append(f"**Total issues**: {total}")
    for col, count in sorted(summary["issues_by_column"].items()):
        change = summary.get("changes", {}).get(col, 0)
        change_str = f" ({change:+d})" if change != 0 else ""
        lines.append(f"- **{col}**: {count}{change_str}")
    lines.append("")
    
    # Issues by agent
    if summary["issues_by_agent"]:
        lines.append("### Issues by Agent")
        for agent, count in sorted(summary["issues_by_agent"].items()):
            lines.append(f"- **{agent}**: {count}")
        lines.append("")
    
    # Issues in progress
    if summary["issues_in_progress"]:
        lines.append("### Issues in Progress")
        for issue in summary["issues_in_progress"]:
            assignees = ", ".join(issue.get("assignees", []))
            lines.append(f"- `{issue['id']}`: {issue['title']} (assigned to: {assignees})")
        lines.append("")
    
    # Recent completions (if any)
    if summary.get("changes", {}).get("done", 0) > 0:
        lines.append("### Recent Completions")
        for comp in summary["recent_completions"][-5:]:
            lines.append(f"- `{comp['id']}`: {comp['title']}")
        lines.append("")
    
    # Changes summary
    if summary.get("changes"):
        lines.append("### Changes Since Last Check")
        for col, change in sorted(summary["changes"].items()):
            if change != 0:
                lines.append(f"- **{col}**: {change:+d}")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    return "\n".join(lines)


def main():
    """Check board status and append to board_status.md"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check board status")
    parser.add_argument("--board-root", default="boards/crewkanteam", help="Board root directory")
    parser.add_argument("--check-progress", action="store_true", help="Check if progress has been made")
    parser.add_argument("--no-append", action="store_true", help="Don't append to board_status.md, just print")
    
    args = parser.parse_args()
    
    board_root = args.board_root
    status_file = Path(board_root) / "board_status.md"
    
    # Load previous status if exists
    previous_status = None
    if status_file.exists():
        # Try to extract last status from markdown (simplified)
        # For now, we'll just track changes in memory
        pass
    
    # Get current status
    summary = get_board_summary(board_root, previous_status)
    
    # Format and append to file
    markdown = format_summary_markdown(summary)
    
    # Check progress if requested
    if args.check_progress:
        age = summary.get("most_recent_update_age_minutes")
        if age is not None and age > 4.5:
            print(f"⚠️  NO PROGRESS DETECTED - Last update was {age:.1f} minutes ago")
            return 1
        else:
            print(f"✅ Progress detected - Last update was {age:.1f} minutes ago")
            return 0
    
    # Append to file unless --no-append
    if not args.no_append:
        with open(status_file, "a") as f:
            f.write(markdown)
    
    # Also print to stdout
    print(markdown)
    
    return summary


if __name__ == "__main__":
    main()

