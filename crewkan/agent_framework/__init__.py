"""
Agent Framework for CrewKan - Supertool integration system.

This module provides the infrastructure for agents to use powerful tools
(supertools) while maintaining separation of concerns - supertools execute,
agents coordinate and update the board.
"""

from crewkan.agent_framework.base import (
    Supertool,
    SupertoolContext,
    SupertoolResult,
    SupertoolError,
)
from crewkan.agent_framework.registry import (
    SupertoolRegistry,
    register_supertool,
    get_registry,
)
from crewkan.agent_framework.executor import SupertoolExecutor
from crewkan.agent_framework.workspace import AgentWorkspace
from crewkan.agent_framework.credentials import CredentialManager
from crewkan.agent_framework.langchain_tools import (
    make_supertool_tools,
    get_supertool_descriptions,
)

__all__ = [
    "Supertool",
    "SupertoolContext",
    "SupertoolResult",
    "SupertoolError",
    "SupertoolRegistry",
    "register_supertool",
    "get_registry",
    "SupertoolExecutor",
    "AgentWorkspace",
    "CredentialManager",
    "make_supertool_tools",
    "get_supertool_descriptions",
]

