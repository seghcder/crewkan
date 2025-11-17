#!/usr/bin/env python3
"""
Run the CrewKan team board in the background.
"""

import sys
import subprocess
import signal
import os
from pathlib import Path

board_root = Path("boards/crewkanteam")
pid_file = board_root / ".board_runner.pid"
log_file = board_root / ".board_runner.log"

def start():
    """Start the board runner in background."""
    if pid_file.exists():
        pid = int(pid_file.read_text().strip())
        try:
            os.kill(pid, 0)  # Check if process exists
            print(f"Board runner already running (PID: {pid})")
            return
        except OSError:
            # Process doesn't exist, remove stale PID file
            pid_file.unlink()
    
    # Start in background
    script_path = Path(__file__).parent.parent / "examples" / "run_crewkanteam.py"
    with open(log_file, "w") as log:
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=Path(__file__).parent.parent,
        )
    
    pid_file.write_text(str(process.pid))
    print(f"Board runner started in background (PID: {process.pid})")
    print(f"Logs: {log_file}")

def stop():
    """Stop the board runner."""
    if not pid_file.exists():
        print("Board runner is not running")
        return
    
    pid = int(pid_file.read_text().strip())
    try:
        # Request graceful shutdown
        shutdown_file = board_root / ".shutdown_requested"
        import json
        import time
        shutdown_data = {
            "requested_at": time.time(),
            "deadline": time.time() + 60,
            "grace_period": 60,
        }
        shutdown_file.write_text(json.dumps(shutdown_data, indent=2))
        print("Graceful shutdown requested. Waiting 60 seconds...")
        
        # Wait for process to exit
        import time as time_module
        for _ in range(60):
            try:
                os.kill(pid, 0)
                time_module.sleep(1)
            except OSError:
                break
        
        # If still running, force kill
        try:
            os.kill(pid, 0)
            os.kill(pid, signal.SIGTERM)
            print("Process terminated")
        except OSError:
            pass
        
        pid_file.unlink()
        if shutdown_file.exists():
            shutdown_file.unlink()
        print("Board runner stopped")
    except Exception as e:
        print(f"Error stopping board runner: {e}")

def status():
    """Check if board runner is running."""
    if not pid_file.exists():
        print("Board runner is not running")
        return False
    
    pid = int(pid_file.read_text().strip())
    try:
        os.kill(pid, 0)
        print(f"Board runner is running (PID: {pid})")
        return True
    except OSError:
        print("Board runner is not running (stale PID file)")
        pid_file.unlink()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: run_board_background.py [start|stop|status]")
        sys.exit(1)
    
    command = sys.argv[1]
    if command == "start":
        start()
    elif command == "stop":
        stop()
    elif command == "status":
        status()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

