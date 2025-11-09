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
    from langchain.agents import AgentExecutor, create_openai_tools_agent
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
except ImportError:
    print("Installing langchain dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "langchain-openai", "langchain", "python-dotenv"])
    from langchain_openai import AzureChatOpenAI
    from langchain.agents import AgentExecutor, create_openai_tools_agent
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

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

        # Create agent
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a CrewKan task management agent. "
                    "Use the available tools to manage tasks on your board. "
                    "Be concise and efficient.",
                ),
                MessagesPlaceholder("chat_history"),
                ("user", "{input}"),
                MessagesPlaceholder("agent_scratchpad"),
            ]
        )

        agent = create_openai_tools_agent(llm, tools, prompt)
        executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        # Test: Create a task
        print("\n=== Test: Create Task ===")
        result = executor.invoke(
            {"input": "Create a task titled 'Test LangChain Integration' in the todo column with high priority."}
        )
        print(f"Result: {result['output']}")

        # Test: List tasks
        print("\n=== Test: List My Tasks ===")
        result = executor.invoke({"input": "List all my tasks in the todo column."})
        print(f"Result: {result['output']}")

        # Test: Add comment
        print("\n=== Test: Add Comment ===")
        # First get a task ID from the list
        from crewkan.board_core import BoardClient
        client = BoardClient(board_dir, "test-agent")
        tasks_json = client.list_my_tasks()
        import json
        tasks = json.loads(tasks_json)
        if tasks:
            task_id = tasks[0]["id"]
            result = executor.invoke(
                {"input": f"Add a comment to task {task_id} saying 'Working on LangChain integration test'."}
            )
            print(f"Result: {result['output']}")

        print("\n✓ LangChain agent test completed successfully!")

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_langchain_agent()

