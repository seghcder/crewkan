#!/usr/bin/env python3
"""
Test coverage framework using the simulator.

Uses coverage.py to track which code is executed during simulation runs.
"""

import sys
import subprocess
import tempfile
from pathlib import Path

# Try to import coverage, install if needed
try:
    import coverage
except ImportError:
    print("Installing coverage.py...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "coverage"])
    import coverage


def run_coverage_test():
    """Run the simulation with coverage tracking."""
    cov = coverage.Coverage(source=["crewkan"])
    cov.start()

    # Import and run simulation
    from tests.test_simulation import run_simulation

    # Run a smaller simulation for coverage
    run_simulation(
        num_agents=5,
        num_tasks=100,
        num_boards=2,
        work_cycles=20,
    )

    cov.stop()
    cov.save()

    # Generate report
    print("\n=== Coverage Report ===")
    cov.report(show_missing=True)

    # Get coverage percentage
    total = cov.report(show_missing=False)
    percentage = cov.html_report(directory="htmlcov")

    print(f"\nCoverage report saved to htmlcov/index.html")

    return cov


if __name__ == "__main__":
    run_coverage_test()

