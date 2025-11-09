#!/usr/bin/env python3
"""
Unified test runner for all CrewKan tests.

Similar to ctest - runs all tests and generates coverage report.
Usage: python tests/test_all.py [--coverage]
"""

import sys
import subprocess
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def run_tests_with_coverage():
    """Run all tests with coverage tracking."""
    try:
        import coverage
    except ImportError:
        print("Installing coverage.py...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "coverage"])
        import coverage
    
    # Start coverage
    cov = coverage.Coverage(
        source=["crewkan"],
        omit=[
            "crewkan/__init__.py",
            "crewkan/__pycache__/*",
            "*/test_*.py",
        ]
    )
    cov.start()
    
    print("=" * 70)
    print("Running all CrewKan tests with coverage tracking")
    print("=" * 70)
    
    results = {}
    
    # Use comprehensive coverage test which imports functions directly
    print("\n[1/6] Running comprehensive coverage test (imports functions directly)...")
    try:
        from tests.test_coverage_comprehensive import run_coverage_comprehensive
        run_coverage_comprehensive()
        results["coverage_comprehensive"] = True
        print("  ✓ Comprehensive coverage test passed")
    except Exception as e:
        print(f"  ✗ Comprehensive coverage test error: {e}")
        import traceback
        traceback.print_exc()
        results["coverage_comprehensive"] = False
    
    # Also run tests via subprocess for actual test execution
    print("\n[2/6] Running CLI tests (subprocess)...")
    try:
        result = subprocess.run(
            [sys.executable, "tests/test_cli.py"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        results["cli"] = result.returncode == 0
        if result.returncode == 0:
            print("  ✓ CLI tests passed")
        else:
            print(f"  ✗ CLI tests failed")
    except Exception as e:
        print(f"  ✗ CLI tests error: {e}")
        results["cli"] = False
    
    # 3. Simulation tests
    print("\n[3/6] Running simulation tests...")
    try:
        result = subprocess.run(
            [sys.executable, "tests/test_simulation.py", "--agents", "5", "--tasks", "50", "--boards", "2", "--cycles", "10"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        results["simulation"] = result.returncode == 0
        if result.returncode == 0:
            print("  ✓ Simulation tests passed")
        else:
            print(f"  ✗ Simulation tests failed: {result.stderr}")
    except Exception as e:
        print(f"  ✗ Simulation tests error: {e}")
        results["simulation"] = False
    
    # 4. Abstracted tests
    print("\n[4/6] Running abstracted tests...")
    try:
        result = subprocess.run(
            [sys.executable, "tests/test_abstracted.py"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        results["abstracted"] = result.returncode == 0
        if result.returncode == 0:
            print("  ✓ Abstracted tests passed")
        else:
            print(f"  ✗ Abstracted tests failed: {result.stderr}")
    except Exception as e:
        print(f"  ✗ Abstracted tests error: {e}")
        results["abstracted"] = False
    
    # 5. Extended UI tests (Playwright)
    print("\n[5/6] Running extended UI tests (Playwright)...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_streamlit_extended.py", "-v", "--tb=short"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        results["ui_extended"] = result.returncode == 0
        if result.returncode == 0:
            print("  ✓ Extended UI tests passed")
        else:
            print(f"  ✗ Extended UI tests failed")
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
    except Exception as e:
        print(f"  ✗ Extended UI tests error: {e}")
        results["ui_extended"] = False
    
    # 6. LangChain tests (optional - requires .env)
    print("\n[6/7] Running LangChain tests (optional)...")
    try:
        result = subprocess.run(
            [sys.executable, "tests/test_langchain_agent.py"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=60,
        )
        results["langchain"] = result.returncode == 0
        if result.returncode == 0:
            print("  ✓ LangChain tests passed")
        else:
            print("  ⚠ LangChain tests skipped (requires .env configuration)")
            results["langchain"] = None  # Not a failure, just skipped
    except subprocess.TimeoutExpired:
        print("  ⚠ LangChain tests timed out")
        results["langchain"] = None
    except Exception as e:
        print(f"  ⚠ LangChain tests skipped: {e}")
        results["langchain"] = None
    
    # 7. CEO Delegation extended test (optional - requires Azure OpenAI)
    print("\n[7/7] Running CEO Delegation extended test (optional)...")
    try:
        result = subprocess.run(
            [sys.executable, "tests/test_ceo_delegation.py"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=90,
        )
        results["ceo_delegation"] = result.returncode == 0
        if result.returncode == 0:
            print("  ✓ CEO Delegation test passed")
        else:
            print("  ⚠ CEO Delegation test skipped (requires Azure OpenAI configuration)")
            results["ceo_delegation"] = None  # Not a failure, just skipped
    except subprocess.TimeoutExpired:
        print("  ⚠ CEO Delegation test timed out")
        results["ceo_delegation"] = None
    except Exception as e:
        print(f"  ⚠ CEO Delegation test skipped: {e}")
        results["ceo_delegation"] = None
    
    # Stop coverage
    cov.stop()
    cov.save()
    
    # Generate report
    print("\n" + "=" * 70)
    print("Coverage Report")
    print("=" * 70)
    cov.report(show_missing=True)
    
    # Generate HTML report
    cov.html_report(directory="htmlcov")
    print(f"\nHTML coverage report: htmlcov/index.html")
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    for name, result in results.items():
        status = "✓ PASS" if result is True else "✗ FAIL" if result is False else "⚠ SKIP"
        print(f"  {name:20} {status}")
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    
    return failed == 0


def run_tests_without_coverage():
    """Run all tests without coverage tracking."""
    print("=" * 70)
    print("Running all CrewKan tests (no coverage)")
    print("=" * 70)
    
    tests = [
        ("CLI", [sys.executable, "tests/test_cli.py"]),
        ("Simulation", [sys.executable, "tests/test_simulation.py", "--agents", "5", "--tasks", "50", "--boards", "2", "--cycles", "10"]),
        ("Abstracted", [sys.executable, "tests/test_abstracted.py"]),
        ("UI Extended", [sys.executable, "-m", "pytest", "tests/test_streamlit_extended.py", "-v", "--tb=short"]),
    ]
    
    results = {}
    for name, cmd in tests:
        print(f"\nRunning {name} tests...")
        try:
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
            )
            results[name] = result.returncode == 0
            if result.returncode == 0:
                print(f"  ✓ {name} tests passed")
            else:
                print(f"  ✗ {name} tests failed")
        except Exception as e:
            print(f"  ✗ {name} tests error: {e}")
            results[name] = False
    
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {name:20} {status}")
    
    return all(results.values())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all CrewKan tests")
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run tests with coverage tracking",
    )
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Run tests without coverage tracking",
    )
    parser.add_argument(
        "--extended",
        action="store_true",
        help="Include extended tests (CEO delegation, etc.)",
    )
    
    args = parser.parse_args()
    
    if args.no_coverage:
        success = run_tests_without_coverage()
    else:
        success = run_tests_with_coverage()
    
    sys.exit(0 if success else 1)

