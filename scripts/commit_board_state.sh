#!/bin/bash
# Commit the current state of the CrewKan team board

cd /home/seanwy/dev/src/crewkan/boards/crewkanteam

# Add all changes
git add -A

# Get current status summary
ISSUES=$(find issues -name "*.yaml" 2>/dev/null | wc -l)
AGENTS=$(find agents -name "*.yaml" 2>/dev/null | wc -l)

# Create commit message
git commit -m "Board state update: $ISSUES issues, $AGENTS agent configs

Auto-committed board state after workflow execution.
$(date '+%Y-%m-%d %H:%M:%S')"

echo "Committed board state: $ISSUES issues"




