#!/usr/bin/env python3
"""
Check board status and append summary to board_status.md
"""

import sys
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
    }
    
    # Count issues by column and agent
    for path, issue in client.iter_issues():
        col = issue.get("column", "unknown")
        summary["issues_by_column"][col] += 1
        
        assignees = issue.get("assignees", [])
        for assignee in assignees:
            summary["issues_by_agent"][assignee] += 1
        
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
    
    # Status by column
    lines.append("### Issues by Status")
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
    board_root = "boards/crewkanteam"
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
    
    # Append to file
    with open(status_file, "a") as f:
        f.write(markdown)
    
    # Also print to stdout
    print(markdown)
    
    return summary


if __name__ == "__main__":
    main()

