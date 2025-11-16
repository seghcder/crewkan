"""
Credential management for supertools.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional
import json
import yaml
from crewkan.utils import load_yaml, save_yaml

logger = logging.getLogger(__name__)


class CredentialManager:
    """
    Manages credential storage and retrieval for supertools.
    
    Supports:
    - Per-agent credential storage
    - User-provided credentials (via tasks)
    - Secure credential injection into supertool context
    """
    
    def __init__(self, board_root: Path):
        """
        Initialize credential manager.
        
        Args:
            board_root: Root directory of the board
        """
        self.board_root = Path(board_root).resolve()
        self.credentials_root = self.board_root / "credentials"
        self.credentials_root.mkdir(parents=True, exist_ok=True)
    
    def get_agent_credentials(self, agent_id: str) -> Dict[str, Any]:
        """
        Get credentials for a specific agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Dictionary of credentials
        """
        creds_path = self.credentials_root / f"{agent_id}.yaml"
        if not creds_path.exists():
            return {}
        
        try:
            return load_yaml(creds_path, default={})
        except Exception as e:
            logger.error(f"Error loading credentials for {agent_id}: {e}")
            return {}
    
    def set_agent_credentials(self, agent_id: str, credentials: Dict[str, Any]) -> None:
        """
        Set credentials for a specific agent.
        
        Args:
            agent_id: Agent identifier
            credentials: Dictionary of credentials to store
        """
        creds_path = self.credentials_root / f"{agent_id}.yaml"
        save_yaml(creds_path, credentials)
        logger.info(f"Saved credentials for agent {agent_id}")
    
    def update_agent_credentials(self, agent_id: str, updates: Dict[str, Any]) -> None:
        """
        Update credentials for an agent (merge with existing).
        
        Args:
            agent_id: Agent identifier
            updates: Dictionary of credential updates
        """
        current = self.get_agent_credentials(agent_id)
        current.update(updates)
        self.set_agent_credentials(agent_id, current)
    
    def get_credential(self, agent_id: str, key: str, default: Any = None) -> Any:
        """
        Get a specific credential value.
        
        Args:
            agent_id: Agent identifier
            key: Credential key
            default: Default value if not found
            
        Returns:
            Credential value or default
        """
        creds = self.get_agent_credentials(agent_id)
        return creds.get(key, default)
    
    def set_credential(self, agent_id: str, key: str, value: Any) -> None:
        """
        Set a specific credential value.
        
        Args:
            agent_id: Agent identifier
            key: Credential key
            value: Credential value
        """
        self.update_agent_credentials(agent_id, {key: value})
    
    def get_supertool_credentials(self, agent_id: str, tool_id: str) -> Dict[str, Any]:
        """
        Get credentials specific to a supertool for an agent.
        
        Args:
            agent_id: Agent identifier
            tool_id: Supertool identifier
            
        Returns:
            Dictionary of tool-specific credentials
        """
        all_creds = self.get_agent_credentials(agent_id)
        tool_creds = all_creds.get("supertools", {}).get(tool_id, {})
        return tool_creds
    
    def set_supertool_credentials(self, agent_id: str, tool_id: str, credentials: Dict[str, Any]) -> None:
        """
        Set credentials for a specific supertool.
        
        Args:
            agent_id: Agent identifier
            tool_id: Supertool identifier
            credentials: Dictionary of tool-specific credentials
        """
        all_creds = self.get_agent_credentials(agent_id)
        if "supertools" not in all_creds:
            all_creds["supertools"] = {}
        all_creds["supertools"][tool_id] = credentials
        self.set_agent_credentials(agent_id, all_creds)
    
    def merge_credentials(self, agent_id: str, tool_id: str, required_keys: list[str]) -> Dict[str, Any]:
        """
        Merge agent credentials and tool-specific credentials.
        
        Args:
            agent_id: Agent identifier
            tool_id: Supertool identifier
            required_keys: List of required credential keys
            
        Returns:
            Merged credentials dictionary
        """
        # Start with agent-level credentials
        merged = self.get_agent_credentials(agent_id).copy()
        
        # Override with tool-specific credentials
        tool_creds = self.get_supertool_credentials(agent_id, tool_id)
        merged.update(tool_creds)
        
        # Filter to only required keys if specified
        if required_keys:
            merged = {k: v for k, v in merged.items() if k in required_keys}
        
        return merged
    
    def has_credentials(self, agent_id: str, tool_id: str, required_keys: list[str]) -> bool:
        """
        Check if agent has all required credentials for a tool.
        
        Args:
            agent_id: Agent identifier
            tool_id: Supertool identifier
            required_keys: List of required credential keys
            
        Returns:
            True if all required credentials are present
        """
        creds = self.merge_credentials(agent_id, tool_id, required_keys)
        return all(key in creds and creds[key] is not None for key in required_keys)

