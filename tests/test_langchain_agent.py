#!/usr/bin/env python3
"""
Test LangChain agent integration with CrewKan.

Requires .env file with Azure OpenAI credentials.
"""

import os
import tempfile
import shutil
from pathlib import Path
import sys

# Check for .env file
if not os.path.exists(".env"):
    print("ERROR: .env file not found.")
    print("Please create .env with:")
    print("  AZURE_OPENAI_API_KEY=your_key")
    print("  AZURE_OPENAI_ENDPOINT=your_endpoint")
    print("  AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment")
    print("  AZURE_OPENAI_API_VERSION=2024-02-15-preview")
    sys.exit(1)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Check required vars
required_vars = [
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT_NAME",
]
missing = [v for v in required_vars if not os.getenv(v)]
if missing:
    print(f"ERROR: Missing environment variables: {', '.join(missing)}")
    sys.exit(1)

try:
    from langchain_openai import AzureChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain.agents import create_agent
    from langchain_core.runnables import RunnableLambda
except ImportError as e:
    print(f"Import error: {e}")
    print("Installing langchain dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "langchain-openai", "langchain", "python-dotenv"])
    from langchain_openai import AzureChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain.agents import create_agent
    from langchain_core.runnables import RunnableLambda

from crewkan.board_init import init_board
from crewkan.board_langchain_tools import make_board_tools


def test_langchain_agent():
    """Test LangChain agent with CrewKan tools."""
    temp_dir = Path(tempfile.mkdtemp())
    board_dir = temp_dir / "test_board"

    try:
        # Set up board
        init_board(
            board_dir,
            board_id="test",
            board_name="Test Board",
            owner_agent_id="test-agent",
            default_superagent_id="test-agent",
        )

        # Add test agent
        import yaml
        agents_path = board_dir / "agents" / "agents.yaml"
        with agents_path.open("r") as f:
            agents_data = yaml.safe_load(f)
        agents_data["agents"].append({
            "id": "test-agent",
            "name": "Test Agent",
            "role": "Test Role",
            "kind": "ai",
            "status": "active",
            "skills": [],
            "metadata": {},
        })
        with agents_path.open("w") as f:
            yaml.safe_dump(agents_data, f)

        # Create tools
        tools = make_board_tools(str(board_dir), "test-agent")
        print(f"Created {len(tools)} tools")

        # Create LLM
        llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            temperature=0,
        )

        # Create agent using LangChain 1.0 API
        # For LangChain 1.0, we'll use a simpler approach with tool calling
        # The LLM can directly call tools when bound to them
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
        
        llm_with_tools = llm.bind_tools(tools)
        
        # Create a simple agent function
        def agent_runner(user_input: str) -> str:
            """Simple agent that uses LLM with tools."""
            messages = [
                SystemMessage(content="You are a CrewKan task management agent. Use the available tools to manage tasks on your board. Be concise and efficient."),
                HumanMessage(content=user_input)
            ]
            
            response = llm_with_tools.invoke(messages)
            
            # Check if LLM wants to call tools
            if hasattr(response, 'tool_calls') and response.tool_calls:
                results = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("args", {})
                    
                    # Find and call the tool
                    for tool in tools:
                        if tool.name == tool_name:
                            try:
                                result = tool.invoke(tool_args)
                                results.append(f"{tool_name}: {result}")
                            except Exception as e:
                                results.append(f"{tool_name} error: {e}")
                
                return "\n".join(results)
            else:
                return response.content if hasattr(response, 'content') else str(response)
        
        # Test: Create a task
        print("\n=== Test: Create Task ===")
        result = agent_runner("Create a task titled 'Test LangChain Integration' in the todo column with high priority.")
        print(f"Result: {result}")

        # Test: List tasks
        print("\n=== Test: List My Tasks ===")
        result = agent_runner("List all my tasks in the todo column.")
        print(f"Result: {result}")

        # Test: Add comment
        print("\n=== Test: Add Comment ===")
        # First get a task ID from the list
        from crewkan.board_core import BoardClient
        client = BoardClient(board_dir, "test-agent")
        tasks_json = client.list_my_issues()
        import json
        tasks = json.loads(tasks_json)
        if tasks:
            task_id = tasks[0]["id"]
            result = agent_runner(f"Add a comment to task {task_id} saying 'Working on LangChain integration test'.")
            print(f"Result: {result}")

        print("\n✓ LangChain agent test completed successfully!")

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_langchain_agent()

