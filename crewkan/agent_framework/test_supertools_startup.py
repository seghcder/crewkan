"""
Startup test utility for supertools.

Validates that supertools are available and working before agent execution.
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple
from crewkan.agent_framework.executor import SupertoolExecutor
from crewkan.board_core import BoardClient

logger = logging.getLogger(__name__)


class SupertoolTestResult:
    """Result of a supertool test."""
    
    def __init__(self, tool_id: str, success: bool, message: str = ""):
        self.tool_id = tool_id
        self.success = success
        self.message = message
    
    def __repr__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.tool_id}: {self.message}"


def test_supertool_availability(
    board_root: str,
    agent_id: str,
    tool_id: str
) -> SupertoolTestResult:
    """
    Test if a supertool is available for an agent.
    
    Args:
        board_root: Board root directory
        agent_id: Agent ID
        tool_id: Supertool ID to test
        
    Returns:
        SupertoolTestResult
    """
    try:
        executor = SupertoolExecutor(board_root, agent_id)
        available_tools = executor.list_available_tools()
        
        # Check if tool is available
        if isinstance(available_tools, dict):
            if tool_id not in available_tools:
                return SupertoolTestResult(
                    tool_id,
                    False,
                    f"Tool not in available tools list"
                )
        elif isinstance(available_tools, list):
            if tool_id not in available_tools:
                return SupertoolTestResult(
                    tool_id,
                    False,
                    f"Tool not in available tools list"
                )
        
        # Check permissions
        if not executor.can_use_tool(tool_id):
            return SupertoolTestResult(
                tool_id,
                False,
                f"Agent does not have permission to use this tool"
            )
        
        return SupertoolTestResult(
            tool_id,
            True,
            "Available and permitted"
        )
        
    except Exception as e:
        return SupertoolTestResult(
            tool_id,
            False,
            f"Error checking availability: {str(e)}"
        )


def test_all_supertools(
    board_root: str,
    agent_id: str
) -> List[SupertoolTestResult]:
    """
    Test all supertools available to an agent.
    
    Args:
        board_root: Board root directory
        agent_id: Agent ID
        
    Returns:
        List of SupertoolTestResult objects
    """
    results = []
    
    try:
        executor = SupertoolExecutor(board_root, agent_id)
        available_tools = executor.list_available_tools()
        
        if isinstance(available_tools, dict):
            tool_ids = list(available_tools.keys())
        elif isinstance(available_tools, list):
            tool_ids = available_tools
        else:
            logger.warning(f"Unexpected available_tools type: {type(available_tools)}")
            return results
        
        for tool_id in tool_ids:
            result = test_supertool_availability(board_root, agent_id, tool_id)
            results.append(result)
        
    except Exception as e:
        logger.error(f"Error testing supertools: {e}", exc_info=True)
        results.append(SupertoolTestResult(
            "unknown",
            False,
            f"Failed to list supertools: {str(e)}"
        ))
    
    return results


def validate_supertools_startup(
    board_root: str,
    agent_id: str,
    required_tools: List[str] = None
) -> Tuple[bool, List[SupertoolTestResult]]:
    """
    Validate that supertools are working before agent startup.
    
    Args:
        board_root: Board root directory
        agent_id: Agent ID
        required_tools: Optional list of tool IDs that must be available
        
    Returns:
        Tuple of (all_passed, results)
    """
    logger.info(f"Validating supertools for agent {agent_id}")
    
    results = test_all_supertools(board_root, agent_id)
    
    # Check required tools
    if required_tools:
        available_tool_ids = {r.tool_id for r in results if r.success}
        missing_required = set(required_tools) - available_tool_ids
        if missing_required:
            for tool_id in missing_required:
                results.append(SupertoolTestResult(
                    tool_id,
                    False,
                    "Required tool not available"
                ))
    
    # Check if all passed
    all_passed = all(r.success for r in results)
    
    # Log results
    logger.info(f"Supertool validation results for {agent_id}:")
    for result in results:
        logger.info(f"  {result}")
    
    if all_passed:
        logger.info(f"✓ All supertools validated successfully for {agent_id}")
    else:
        failed = [r for r in results if not r.success]
        logger.warning(f"✗ {len(failed)} supertool(s) failed validation for {agent_id}")
        for result in failed:
            logger.warning(f"  {result}")
    
    return all_passed, results


def main():
    """CLI entry point for supertool testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test supertools for an agent")
    parser.add_argument(
        "--board-root",
        required=True,
        help="Board root directory"
    )
    parser.add_argument(
        "--agent-id",
        required=True,
        help="Agent ID to test"
    )
    parser.add_argument(
        "--required-tools",
        nargs="*",
        help="Required tool IDs (must be available)"
    )
    
    args = parser.parse_args()
    
    all_passed, results = validate_supertools_startup(
        args.board_root,
        args.agent_id,
        required_tools=args.required_tools
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("Supertool Validation Results")
    print("=" * 60)
    for result in results:
        print(result)
    print("=" * 60)
    
    if all_passed:
        print("✓ All tests passed")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

