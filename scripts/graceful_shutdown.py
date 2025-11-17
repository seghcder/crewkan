#!/usr/bin/env python3
"""
Signal graceful shutdown to running board.
Creates a shutdown flag file that agents can check.
"""

import sys
from pathlib import Path
import time
import json

board_root = Path("boards/crewkanteam")
shutdown_file = board_root / ".shutdown_requested"

if len(sys.argv) > 1:
    grace_period = int(sys.argv[1])
else:
    grace_period = 60  # Default 60 seconds

shutdown_data = {
    "requested_at": time.time(),
    "deadline": time.time() + grace_period,
    "grace_period": grace_period,
}

shutdown_file.write_text(json.dumps(shutdown_data, indent=2))
print(f"Shutdown requested. Agents have {grace_period} seconds to finish current work.")

