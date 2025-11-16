"""
Example supertool implementations.
"""

# Import supertools to register them
from crewkan.agent_framework.supertools.coding import (
    ClineSupertool,
    ContinueSupertool,
)
from crewkan.agent_framework.supertools.research import (
    DeepResearchSupertool,
    WebSearchSupertool,
)
from crewkan.agent_framework.supertools.automation import (
    BrowserAutomationSupertool,
    TaskLineSupertool,
)

__all__ = [
    "ClineSupertool",
    "ContinueSupertool",
    "DeepResearchSupertool",
    "WebSearchSupertool",
    "BrowserAutomationSupertool",
    "TaskLineSupertool",
]

