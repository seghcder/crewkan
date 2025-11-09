# board_registry.py

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from crewkan.utils import load_yaml, save_yaml

# Set up logging
logger = logging.getLogger(__name__)


class BoardRegistry:
    """
    Manages a registry of boards, typically stored at boards/registry.yaml
    """

    def __init__(self, registry_path: str | Path):
        self.registry_path = Path(registry_path).resolve()
        self.registry = load_yaml(self.registry_path, default={"boards": []})
        if "boards" not in self.registry:
            self.registry["boards"] = []

    def _save(self):
        """Save the registry to disk."""
        save_yaml(self.registry_path, self.registry)

    def list_boards(self, status: Optional[str] = None) -> list[dict]:
        """
        List all boards, optionally filtered by status.
        """
        boards = self.registry.get("boards", [])
        if status:
            return [b for b in boards if b.get("status") == status]
        return boards

    def get_board(self, board_id: str) -> Optional[dict]:
        """
        Get a board by id.
        """
        for board in self.registry.get("boards", []):
            if board.get("id") == board_id:
                return board
        return None

    def register_board(
        self,
        board_id: str,
        path: str,
        owner_agent: str,
        purpose: Optional[str] = None,
        parent_board_id: Optional[str] = None,
        status: str = "active",
    ):
        """
        Register a new board in the registry.
        """
        # Check if board already exists
        existing = self.get_board(board_id)
        if existing:
            # Update existing
            existing["path"] = path
            existing["owner_agent"] = owner_agent
            if purpose is not None:
                existing["purpose"] = purpose
            if parent_board_id is not None:
                existing["parent_board_id"] = parent_board_id
            existing["status"] = status
        else:
            # Add new
            board_entry = {
                "id": board_id,
                "path": path,
                "owner_agent": owner_agent,
                "status": status,
            }
            if purpose:
                board_entry["purpose"] = purpose
            if parent_board_id:
                board_entry["parent_board_id"] = parent_board_id

            self.registry["boards"].append(board_entry)

        self._save()

    def archive_board(self, board_id: str):
        """
        Archive a board by setting its status to 'archived'.
        """
        board = self.get_board(board_id)
        if board:
            board["status"] = "archived"
            self._save()

    def delete_board(self, board_id: str):
        """
        Remove a board from the registry.
        """
        self.registry["boards"] = [
            b for b in self.registry.get("boards", []) if b.get("id") != board_id
        ]
        self._save()

