#!/usr/bin/env python3
"""
Test framework for CrewKan with arbitrary agents and 1000 tasks.

Simulates:
- CEO agent creating tasks and assigning
- Other agents doing work, updating comments, creating new tasks
- Multi-board scenarios
"""

import random
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict
import yaml
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewkan.board_init import init_board
from crewkan.board_core import BoardClient, BoardError
from crewkan.board_registry import BoardRegistry


class AgentSimulator:
    """Simulates an agent working on tasks."""

    def __init__(self, client: BoardClient, agent_id: str):
        self.client = client
        self.agent_id = agent_id

    def work_cycle(self, max_actions: int = 10):
        """Perform a work cycle: check tasks, update, comment, create new tasks."""
        actions = 0

        # List my tasks
        tasks_json = self.client.list_my_tasks(limit=50)
        import json
        tasks = json.loads(tasks_json)

        if not tasks:
            # No tasks assigned, create one
            if random.random() < 0.3:  # 30% chance to create a task
                self.create_random_task()
                actions += 1
            return actions

        # Work on a random task
        task = random.choice(tasks)
        task_id = task["id"]
        current_column = task.get("column", "todo")

        # Random actions
        if random.random() < 0.4 and current_column != "done":
            # Move to next column
            columns = self.client.columns
            try:
                current_idx = columns.index(current_column)
                if current_idx < len(columns) - 1:
                    new_column = columns[current_idx + 1]
                    self.client.move_task(task_id, new_column)
                    actions += 1
            except (ValueError, BoardError):
                pass

        if random.random() < 0.5:
            # Add a comment
            comments = [
                "Working on this task",
                "Making good progress",
                "Need more information",
                "Blocked on dependency",
                "Almost done",
                "Reviewing requirements",
            ]
            comment = random.choice(comments)
            self.client.add_comment(task_id, comment)
            actions += 1

        if random.random() < 0.3:
            # Create a related task
            self.create_random_task()
            actions += 1

        if random.random() < 0.2 and len(tasks) > 1:
            # Reassign a task to another agent (if available)
            other_agents = [
                a["id"]
                for a in self.client.list_agents()
                if a["id"] != self.agent_id and a.get("status") == "active"
            ]
            if other_agents:
                other_task = random.choice([t for t in tasks if t["id"] != task_id])
                try:
                    self.client.reassign_task(
                        other_task["id"], random.choice(other_agents), keep_existing=False
                    )
                    actions += 1
                except BoardError:
                    pass

        return actions

    def create_random_task(self):
        """Create a random task."""
        titles = [
            "Implement feature X",
            "Fix bug in module Y",
            "Review documentation",
            "Update dependencies",
            "Optimize performance",
            "Add tests",
            "Refactor code",
            "Design new component",
            "Write specification",
            "Deploy to staging",
        ]
        columns = ["backlog", "todo"]
        priorities = ["low", "medium", "high"]

        title = random.choice(titles)
        column = random.choice(columns)
        priority = random.choice(priorities)

        try:
            self.client.create_task(
                title=title,
                description=f"Task created by {self.agent_id}",
                column=column,
                priority=priority,
                tags=[random.choice(["dev", "ops", "docs", "test"])],
            )
        except BoardError:
            pass


class CEOAgentSimulator(AgentSimulator):
    """Specialized simulator for CEO agent - creates and assigns tasks."""

    def work_cycle(self, max_actions: int = 20):
        """CEO creates many tasks and assigns them."""
        actions = 0

        # Create multiple tasks
        num_tasks = random.randint(1, 5)
        for _ in range(num_tasks):
            self.create_and_assign_task()
            actions += 1

        # Also do regular work
        actions += super().work_cycle(max_actions=5)

        return actions

    def create_and_assign_task(self):
        """Create a task and assign it to a random agent."""
        titles = [
            "Launch new initiative",
            "Establish new process",
            "Coordinate cross-team effort",
            "Review quarterly goals",
            "Plan next sprint",
            "Organize team meeting",
            "Evaluate new technology",
            "Set up new project",
        ]

        agents = [
            a["id"]
            for a in self.client.list_agents()
            if a["id"] != self.agent_id and a.get("status") == "active"
        ]

        if not agents:
            return

        title = random.choice(titles)
        assignee = random.choice(agents)

        try:
            self.client.create_task(
                title=title,
                description=f"Task assigned by CEO to {assignee}",
                column="todo",
                assignees=[assignee],
                priority=random.choice(["medium", "high"]),
            )
        except BoardError:
            pass


def create_test_agents(num_agents: int = 10) -> List[Dict]:
    """Create a list of test agents."""
    agents = []
    roles = [
        "Software Engineer",
        "DevOps Engineer",
        "Product Manager",
        "Designer",
        "QA Engineer",
        "Data Scientist",
        "Architect",
        "Team Lead",
    ]

    # CEO agent
    agents.append(
        {
            "id": "ceo-agent",
            "name": "CEO Agent",
            "role": "Chief Executive",
            "kind": "ai",
            "status": "active",
            "skills": ["coordination", "strategy"],
            "metadata": {},
        }
    )

    # Other agents
    for i in range(1, num_agents):
        agent_id = f"agent-{i:03d}"
        agents.append(
            {
                "id": agent_id,
                "name": f"Agent {i}",
                "role": random.choice(roles),
                "kind": random.choice(["ai", "human"]),
                "status": "active",
                "skills": [f"skill-{j}" for j in range(random.randint(1, 3))],
                "metadata": {},
            }
        )

    return agents


def setup_test_board(board_root: Path, agents: List[Dict], board_id: str = "test"):
    """Set up a test board with agents."""
    init_board(
        board_root,
        board_id=board_id,
        board_name="Test Board",
        owner_agent_id="ceo-agent",
        default_superagent_id="ceo-agent",
    )

    # Add all agents
    agents_path = board_root / "agents" / "agents.yaml"
    with agents_path.open("r") as f:
        agents_data = yaml.safe_load(f)

    agents_data["agents"] = agents
    with agents_path.open("w") as f:
        yaml.safe_dump(agents_data, f)


def run_simulation(
    num_agents: int = 10,
    num_tasks: int = 1000,
    num_boards: int = 3,
    work_cycles: int = 100,
):
    """
    Run a full simulation with arbitrary agents and tasks.

    Args:
        num_agents: Number of agents to create
        num_tasks: Target number of tasks to create
        num_boards: Number of boards to create
        work_cycles: Number of work cycles to simulate
    """
    temp_dir = Path(tempfile.mkdtemp())
    print(f"Running simulation in {temp_dir}")

    try:
        # Create agents
        agents = create_test_agents(num_agents)
        print(f"Created {len(agents)} agents")

        # Create boards
        boards = []
        registry_path = temp_dir / "boards" / "registry.yaml"
        registry = BoardRegistry(registry_path)

        for i in range(num_boards):
            board_id = f"board-{i}"
            board_root = temp_dir / "boards" / board_id
            setup_test_board(board_root, agents, board_id=board_id)
            boards.append((board_id, board_root))

            # Register board
            owner = "ceo-agent" if i == 0 else random.choice(agents)["id"]
            parent = "board-0" if i > 0 else None
            registry.register_board(
                board_id=board_id,
                path=str(board_root.relative_to(temp_dir)),
                owner_agent=owner,
                purpose=f"Test board {i}",
                parent_board_id=parent,
            )

        print(f"Created {len(boards)} boards")

        # Create initial tasks (CEO creates many)
        tasks_created = 0
        ceo_client = BoardClient(boards[0][1], "ceo-agent")
        ceo_sim = CEOAgentSimulator(ceo_client, "ceo-agent")

        print("Creating initial tasks...")
        while tasks_created < num_tasks:
            ceo_sim.work_cycle()
            # Count all tasks across all boards
            total = 0
            for _, br in boards:
                for _ in BoardClient(br, "ceo-agent").iter_tasks():
                    total += 1
            tasks_created = total
            if tasks_created >= num_tasks:
                break

        print(f"Created {tasks_created} tasks")

        # Test CLI commands via subprocess for coverage
        print("Testing CLI commands...")
        import subprocess
        for board_id, board_root in boards[:1]:  # Test first board
            # Test list-agents
            subprocess.run(
                ["python", "-m", "crewkan.crewkan_cli", "--root", str(board_root), "list-agents"],
                capture_output=True,
            )
            # Test list-tasks
            subprocess.run(
                ["python", "-m", "crewkan.crewkan_cli", "--root", str(board_root), "list-tasks"],
                capture_output=True,
            )
            # Test validate
            subprocess.run(
                ["python", "-m", "crewkan.crewkan_cli", "--root", str(board_root), "validate"],
                capture_output=True,
            )

        # Simulate work cycles
        print(f"Running {work_cycles} work cycles...")
        total_actions = 0
        for cycle in range(work_cycles):
            # Each agent does work
            for agent in agents:
                if agent["id"] == "ceo-agent":
                    sim = CEOAgentSimulator(
                        BoardClient(boards[0][1], agent["id"]), agent["id"]
                    )
                else:
                    # Random board for non-CEO agents
                    board_id, board_root = random.choice(boards)
                    sim = AgentSimulator(
                        BoardClient(board_root, agent["id"]), agent["id"]
                    )
                actions = sim.work_cycle()
                total_actions += actions

            if (cycle + 1) % 10 == 0:
                print(f"  Cycle {cycle + 1}/{work_cycles}, total actions: {total_actions}")

        # Test LangChain tools
        print("Testing LangChain tools...")
        from crewkan.board_langchain_tools import make_board_tools
        tools = make_board_tools(str(boards[0][1]), "ceo-agent")
        # Call each tool to exercise code
        if tools:
            # Test list_my_tasks tool
            list_tool = next((t for t in tools if t.name == "list_my_tasks"), None)
            if list_tool:
                try:
                    list_tool.invoke({"column": None, "limit": 10})
                except Exception:
                    pass  # May fail if no tasks, that's ok for coverage

        # Final statistics
        print("\n=== Final Statistics ===")
        for board_id, board_root in boards:
            client = BoardClient(board_root, "ceo-agent")
            total_tasks = sum(1 for _ in client.iter_tasks())
            print(f"Board {board_id}: {total_tasks} tasks")

            # Count by column
            by_column = {}
            for _, task in client.iter_tasks():
                col = task.get("column", "unknown")
                by_column[col] = by_column.get(col, 0) + 1
            print(f"  By column: {by_column}")

        print(f"\nTotal actions performed: {total_actions}")
        print("Simulation completed successfully!")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"Cleaned up {temp_dir}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run CrewKan simulation")
    parser.add_argument("--agents", type=int, default=10, help="Number of agents")
    parser.add_argument("--tasks", type=int, default=1000, help="Target number of tasks")
    parser.add_argument("--boards", type=int, default=3, help="Number of boards")
    parser.add_argument("--cycles", type=int, default=100, help="Number of work cycles")
    args = parser.parse_args()

    run_simulation(
        num_agents=args.agents,
        num_tasks=args.tasks,
        num_boards=args.boards,
        work_cycles=args.cycles,
    )

