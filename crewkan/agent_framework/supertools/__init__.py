"""
Example supertool implementations.
"""

# Import supertools to register them
try:
    from crewkan.agent_framework.supertools.coding import (
        ClineSupertool,
        ContinueSupertool,
    )
except ImportError:
    pass

try:
    from crewkan.agent_framework.supertools.research import (
        DeepResearchSupertool,
        WebSearchSupertool,
    )
except ImportError:
    pass

try:
    from crewkan.agent_framework.supertools.automation import (
        BrowserAutomationSupertool,
        TaskLineSupertool,
    )
except ImportError:
    pass

try:
    from crewkan.agent_framework.supertools.mcp import (
        MCPServerSupertool,
        MCPServerRegistry,
    )
except ImportError:
    pass

__all__ = [
    "ClineSupertool",
    "ContinueSupertool",
    "DeepResearchSupertool",
    "WebSearchSupertool",
    "BrowserAutomationSupertool",
    "TaskLineSupertool",
    "MCPServerSupertool",
    "MCPServerRegistry",
]

