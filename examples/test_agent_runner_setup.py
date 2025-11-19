#!/usr/bin/env python3
"""
Test script to validate agent_runner setup without requiring LLM execution.

This validates that:
1. Board structure is correct
2. Agents can be loaded
3. Tools can be created
4. System prompts can be loaded
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.board_core import BoardClient
from crewkan.board_langchain_tools import make_board_tools
from crewkan.agent_framework.langchain_tools import make_supertool_tools
from crewkan.agent_framework.test_supertools_startup import validate_supertools_startup


def test_setup(board_root: str, agent_id: str):
    """Test agent runner setup for an agent."""
    print(f"\n{'='*60}")
    print(f"Testing setup for agent: {agent_id}")
    print(f"{'='*60}\n")
    
    # 1. Test BoardClient
    print("1. Testing BoardClient...")
    try:
        client = BoardClient(board_root, agent_id)
        agent_info = client.get_agent(agent_id)
        if agent_info:
            print(f"   ✓ Agent found: {agent_info.get('name')} ({agent_info.get('role')})")
        else:
            print(f"   ✗ Agent {agent_id} not found")
            return False
    except Exception as e:
        print(f"   ✗ Error loading agent: {e}")
        return False
    
    # 2. Test system prompt loading
    print("\n2. Testing system prompt loading...")
    try:
        system_prompt = client.get_agent_system_prompt(agent_id)
        if system_prompt:
            print(f"   ✓ System prompt loaded ({len(system_prompt)} chars)")
            print(f"   Preview: {system_prompt[:100]}...")
        else:
            print(f"   ⚠ No system prompt configured (will use default)")
    except Exception as e:
        print(f"   ✗ Error loading system prompt: {e}")
    
    # 3. Test board tools
    print("\n3. Testing board tools...")
    try:
        board_tools = make_board_tools(board_root, agent_id)
        print(f"   ✓ Created {len(board_tools)} board tools")
        for tool in board_tools[:3]:  # Show first 3
            print(f"     - {tool.name}")
        if len(board_tools) > 3:
            print(f"     ... and {len(board_tools) - 3} more")
    except Exception as e:
        print(f"   ✗ Error creating board tools: {e}")
        return False
    
    # 4. Test supertools
    print("\n4. Testing supertools...")
    try:
        supertools = make_supertool_tools(board_root, agent_id)
        print(f"   ✓ Created {len(supertools)} supertool tools")
        if supertools:
            for tool in supertools[:3]:  # Show first 3
                print(f"     - {tool.name}")
            if len(supertools) > 3:
                print(f"     ... and {len(supertools) - 3} more")
        else:
            print("   ⚠ No supertools available for this agent")
    except Exception as e:
        print(f"   ✗ Error creating supertools: {e}")
        # Not fatal, continue
    
    # 5. Test supertool validation
    print("\n5. Testing supertool validation...")
    try:
        all_passed, results = validate_supertools_startup(board_root, agent_id)
        print(f"   ✓ Validation completed: {'PASSED' if all_passed else 'FAILED'}")
        print(f"   Tested {len(results)} supertools")
    except Exception as e:
        print(f"   ⚠ Error validating supertools: {e}")
    
    # 6. Test workspace
    print("\n6. Testing workspace...")
    try:
        from crewkan.agent_framework.workspace import AgentWorkspace
        workspace = AgentWorkspace(Path(board_root), agent_id)
        workspace_path = workspace.get_workspace_path()
        print(f"   ✓ Workspace path: {workspace_path}")
        if workspace_path.exists():
            print(f"   ✓ Workspace directory exists")
        else:
            print(f"   ⚠ Workspace directory does not exist (will be created on first use)")
    except Exception as e:
        print(f"   ✗ Error checking workspace: {e}")
    
    # 7. Test tasks
    print("\n7. Testing task access...")
    try:
        import json
        tasks = json.loads(client.list_my_issues(column="todo", limit=5))
        print(f"   ✓ Found {len(tasks)} tasks in 'todo' column")
        for task in tasks[:3]:
            print(f"     - {task['id']}: {task['title'][:50]}")
        if len(tasks) > 3:
            print(f"     ... and {len(tasks) - 3} more")
    except Exception as e:
        print(f"   ⚠ Error listing tasks: {e}")
    
    print(f"\n{'='*60}")
    print("Setup validation complete!")
    print(f"{'='*60}\n")
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test agent runner setup")
    parser.add_argument(
        "--board-root",
        type=str,
        default="boards/crewkanteam",
        help="Board root directory"
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        default=None,
        help="Agent ID to test (default: test all active AI agents)"
    )
    
    args = parser.parse_args()
    
    board_root = Path(args.board_root).resolve()
    
    if args.agent_id:
        # Test single agent
        test_setup(str(board_root), args.agent_id)
    else:
        # Test all active AI agents
        client = BoardClient(str(board_root), "system")
        agents = client.list_agents()
        ai_agents = [a for a in agents if a.get("kind") == "ai" and a.get("status") == "active"]
        
        print(f"Testing {len(ai_agents)} active AI agents...\n")
        
        for agent in ai_agents:
            test_setup(str(board_root), agent["id"])

