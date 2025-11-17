# Board Monitoring and Background Execution

## Overview

The board can run in the background with automatic monitoring that detects bottlenecks and takes remediation actions.

## Usage

### Start Board and Monitor

```bash
# Start board in background and begin monitoring
python scripts/board_manager.py
```

This will:
1. Start the board runner in the background
2. Begin monitoring status every 60 seconds
3. Detect bottlenecks if nothing moves for 2 minutes
4. Automatically take remediation actions

### Manual Control

```bash
# Start board in background
python scripts/run_board_background.py start

# Check if board is running
python scripts/run_board_background.py status

# Stop board (graceful shutdown with 60s grace period)
python scripts/run_board_background.py stop

# Monitor board status
python scripts/monitor_board.py
```

## Monitoring Features

### Status Checks (Every 60 seconds)

- Issues by column (backlog, todo, doing, done)
- Issues by agent
- Issues currently in progress
- Recent activity

### Bottleneck Detection (After 2 minutes of no movement)

1. **No Movement**: No issues have moved between columns
2. **Stuck Issues**: Issues stuck in "doing" column
3. **Idle Agents**: Agents with no assigned work
4. **Backlog Buildup**: Too many issues in backlog (>10)

### Automatic Remediation

When bottlenecks are detected, the monitor will:

1. **Stuck Issues**: Suggest reassignment or moving back to todo
2. **Idle Agents**: Automatically assign backlog issues to idle agents
3. **No Movement**: Report for investigation (check logs, verify agents running)

## Graceful Shutdown

The board supports graceful shutdown:

1. Shutdown signal is written to `.shutdown_requested` file
2. Agents check this file on each iteration
3. Agents finish current work but don't start new issues
4. After 60 seconds, agents exit cleanly

Manual shutdown:
```bash
python scripts/graceful_shutdown.py [grace_period_seconds]
```

## Logs

Board runner logs are written to:
- `boards/crewkanteam/.board_runner.log`

Monitor output goes to stdout (can be redirected).

## Troubleshooting

### Board Not Running

```bash
# Check status
python scripts/run_board_background.py status

# Check logs
tail -f boards/crewkanteam/.board_runner.log
```

### Agents Not Processing

1. Check if agents are active in `agents/agents.yaml`
2. Verify agents have supertools configured
3. Check for errors in logs
4. Verify board state is valid

### Stuck Issues

The monitor will automatically detect and suggest remediation. You can also manually:
- Reassign issues to different agents
- Move issues back to todo
- Check issue details for errors

