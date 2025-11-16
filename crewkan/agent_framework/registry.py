"""
Supertool registry for registration and discovery of supertools.
"""

import logging
from typing import Dict, Optional, Type
from crewkan.agent_framework.base import Supertool

logger = logging.getLogger(__name__)


class SupertoolRegistry:
    """
    Central registry for all supertools.
    
    Supports decorator-based registration and auto-discovery.
    """
    
    def __init__(self):
        self._tools: Dict[str, Type[Supertool]] = {}
        self._instances: Dict[str, Supertool] = {}
    
    def register(self, tool_class: Type[Supertool], tool_id: Optional[str] = None) -> Type[Supertool]:
        """
        Register a supertool class.
        
        Args:
            tool_class: Supertool class to register
            tool_id: Optional tool ID (defaults to class name)
            
        Returns:
            The tool class (for use as decorator)
        """
        # Create instance to get tool_id
        instance = tool_class()
        actual_id = tool_id or instance.tool_id
        
        if actual_id in self._tools:
            logger.warning(f"Supertool {actual_id} already registered, overwriting")
        
        self._tools[actual_id] = tool_class
        logger.info(f"Registered supertool: {actual_id} ({instance.name})")
        return tool_class
    
    def get(self, tool_id: str) -> Optional[Supertool]:
        """
        Get an instance of a supertool by ID.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            Supertool instance or None if not found
        """
        if tool_id not in self._tools:
            return None
        
        # Cache instances
        if tool_id not in self._instances:
            self._instances[tool_id] = self._tools[tool_id]()
        
        return self._instances[tool_id]
    
    def list_all(self) -> Dict[str, Dict]:
        """
        List all registered supertools with metadata.
        
        Returns:
            Dictionary mapping tool_id to tool metadata
        """
        result = {}
        for tool_id, tool_class in self._tools.items():
            instance = self.get(tool_id)
            if instance:
                result[tool_id] = instance.get_metadata()
        return result
    
    def is_registered(self, tool_id: str) -> bool:
        """Check if a tool is registered."""
        return tool_id in self._tools
    
    def get_allowed_tools(self, allowed_ids: list[str]) -> Dict[str, Supertool]:
        """
        Get instances of tools that are in the allowed list.
        
        Args:
            allowed_ids: List of allowed tool IDs
            
        Returns:
            Dictionary mapping tool_id to Supertool instance
        """
        result = {}
        for tool_id in allowed_ids:
            tool = self.get(tool_id)
            if tool:
                result[tool_id] = tool
            else:
                logger.warning(f"Requested supertool {tool_id} not found in registry")
        return result


# Global registry instance
_registry: Optional[SupertoolRegistry] = None


def get_registry() -> SupertoolRegistry:
    """Get the global supertool registry."""
    global _registry
    if _registry is None:
        _registry = SupertoolRegistry()
    return _registry


def register_supertool(tool_id: Optional[str] = None):
    """
    Decorator to register a supertool.
    
    Usage:
        @register_supertool("my-tool")
        class MySupertool(Supertool):
            ...
    
    Args:
        tool_id: Optional tool ID (defaults to class name)
    """
    def decorator(tool_class: Type[Supertool]) -> Type[Supertool]:
        registry = get_registry()
        return registry.register(tool_class, tool_id)
    return decorator

