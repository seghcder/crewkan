#!/usr/bin/env python3
"""
Board manager: Start board in background and monitor it.
"""

import sys
import subprocess
import time
from pathlib import Path

def main():
    """Start board and monitor."""
    board_root = Path("boards/crewkanteam")
    
    # Start board in background
    print("Starting board in background...")
    subprocess.run([sys.executable, "scripts/run_board_background.py", "start"], 
                   cwd=Path(__file__).parent.parent)
    
    time.sleep(2)  # Give it a moment to start
    
    # Start monitor
    print("Starting monitor...")
    print("Monitor will check status every 60 seconds")
    print("If no movement after 2 minutes, it will detect bottlenecks and take action")
    print("Press Ctrl+C to stop both board and monitor\n")
    
    try:
        subprocess.run([sys.executable, "scripts/monitor_board.py"],
                      cwd=Path(__file__).parent.parent)
    except KeyboardInterrupt:
        print("\n\nStopping board and monitor...")
        subprocess.run([sys.executable, "scripts/run_board_background.py", "stop"],
                      cwd=Path(__file__).parent.parent)

if __name__ == "__main__":
    main()

