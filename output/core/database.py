"""Database manager for handling data operations and synchronization."""

import asyncio
import uuid
from collections import defaultdict
from copy import deepcopy
from typing import Dict, List, Any, Generic, TypeVar, Optional
from datetime import datetime

from models.action import BaseAction, ActionType, AppendAction, DeleteAction, EditAction
from core.exceptions import DatabaseError, ConflictError

T = TypeVar('T')


class ConflictResolutionStrategy:
    """Strategies for resolving conflicts between concurrent edits."""
    
    APPLY_LATEST = "apply_latest"
    APPLY_BY_COLUMN = "apply_by_column"
    APPLY_BY_ROW = "apply_by_row"


class Database(Generic[T]):
    """
    Thread-safe database for managing real-time synchronized data.
    
    Handles CRUD operations with conflict resolution and version management.
    """
    
    def __init__(self, initial_data: List[T], key_extractor: callable):
        """
        Initialize database with initial data.
        
        Args:
            initial_data: List of initial data objects
            key_extractor: Function to extract key from data object
        """
        self.data_version = 1
        self.data: Dict[str, Dict[str, Any]] = {}
        self.id_counter = 0
        self.conflict_resolution = ConflictResolutionStrategy.APPLY_LATEST
        self.key_extractor = key_extractor
        self._mutex = asyncio.Lock()
        
        # Initialize with provided data
        for item in initial_data:
            self.id_counter += 1
            key = self.key_extractor(item)
            self.data[key] = {
                "id": self.id_counter,
                "data": item
            }
    
    def get_all_data(self) -> Dict[str, Any]:
        """Get all data in the database."""
        return self.data.copy()
    
    def get_data_version(self) -> int:
        """Get current data version."""
        return self.data_version
    
    @staticmethod
    def group_actions_by_key(actions: List[BaseAction]) -> Dict[str, List[BaseAction]]:
        """
        Group actions by their target key.
        
        Args:
            actions: List of actions to group
            
        Returns:
            Dictionary mapping keys to lists of actions
        """
        grouped = defaultdict(list)
        for action in actions:
            grouped[action.key].append(action)
        return dict(grouped)
    
    async def apply_mutations(self, actions: List[BaseAction], client_ids: List[uuid.UUID]) -> Dict[uuid.UUID, List[Dict[str, Any]]]:
        """
        Apply a batch of mutations to the database.
        
        Args:
            actions: List of actions to apply
            client_ids: List of connected client IDs
            
        Returns:
            Dictionary mapping client IDs to lists of messages to send
            
        Raises:
            DatabaseError: If mutation application fails
        """
        if not actions:
            return {client_id: [] for client_id in client_ids}
        
        async with self._mutex:
            try:
                messages = defaultdict(list)
                grouped_actions = self.group_actions_by_key(actions)
                
                for key, key_actions in grouped_actions.items():
                    await self._process_key_actions(key, key_actions, client_ids, messages)
                
                # Increment version after all changes
                self.data_version += 1
                
                # Update version in all messages
                for client_messages in messages.values():
                    for message in client_messages:
                        message["version"] = self.data_version
                
                return dict(messages)
                
            except Exception as e:
                raise DatabaseError(f"Failed to apply mutations: {str(e)}") from e
    
    async def _process_key_actions(self, key: str, actions: List[BaseAction], 
                                 client_ids: List[uuid.UUID], 
                                 messages: Dict[uuid.UUID, List[Dict[str, Any]]]) -> None:
        """Process all actions for a specific key."""
        # Sort actions by priority: APPEND > DELETE > EDIT
        append_actions = [a for a in actions if a.type == ActionType.APPEND]
        delete_actions = [a for a in actions if a.type == ActionType.DELETE]
        edit_actions = [a for a in actions if a.type == ActionType.EDIT]
        
        # Process append actions
        if append_actions:
            await self._process_append_actions(key, append_actions, client_ids, messages)
        
        # Process delete actions (check for conflicts with edits)
        if delete_actions:
            await self._process_delete_actions(key, delete_actions, edit_actions, client_ids, messages)
        
        # Process edit actions (only if no deletes)
        elif edit_actions:
            await self._process_edit_actions(key, edit_actions, client_ids, messages)
    
    async def _process_append_actions(self, key: str, actions: List[AppendAction], 
                                    client_ids: List[uuid.UUID], 
                                    messages: Dict[uuid.UUID, List[Dict[str, Any]]]) -> None:
        """Process append actions for a key."""
        # Use the latest append action based on version and timestamp
        latest_action = max(actions, key=lambda a: (a.version, a.timestamp))
        
        self.id_counter += 1
        self.data[key] = {
            "id": self.id_counter,
            "data": deepcopy(latest_action.data)
        }
        
        # Notify all clients
        for client_id in client_ids:
            messages[client_id].append({
                "type": "add",
                "key": key,
                "data": latest_action.data,
                "version": self.data_version
            })
    
    async def _process_delete_actions(self, key: str, delete_actions: List[DeleteAction], 
                                    edit_actions: List[EditAction], client_ids: List[uuid.UUID], 
                                    messages: Dict[uuid.UUID, List[Dict[str, Any]]]) -> None:
        """Process delete actions, handling conflicts with edits."""
        if edit_actions:
            # Conflict detected - notify the deleting client
            delete_action = delete_actions[0]  # Take first delete action
            messages[delete_action.client_id].append({
                "type": "conflict",
                "message": "Another user has recently made changes. Do you still want to delete?",
                "key": key
            })
        else:
            # No conflicts, proceed with delete
            if key in self.data:
                del self.data[key]
                
                # Notify all clients
                for client_id in client_ids:
                    messages[client_id].append({
                        "type": "delete",
                        "key": key,
                        "version": self.data_version
                    })
    
    async def _process_edit_actions(self, key: str, actions: List[EditAction], 
                                  client_ids: List[uuid.UUID], 
                                  messages: Dict[uuid.UUID, List[Dict[str, Any]]]) -> None:
        """Process edit actions for a key."""
        if key not in self.data:
            raise DatabaseError(f"Cannot edit non-existent key: {key}")
        
        if self.conflict_resolution == ConflictResolutionStrategy.APPLY_LATEST:
            # Apply changes in version order
            changes = {}
            for action in sorted(actions, key=lambda a: a.version):
                changes[action.field] = action.value
            
            # Apply changes to the data
            current_data = self.data[key]['data']
            if hasattr(current_data, '__dict__'):
                for field, value in changes.items():
                    setattr(current_data, field, value)
            else:
                # Handle dictionary-like data
                for field, value in changes.items():
                    current_data[field] = value
            
            # Notify all clients
            for client_id in client_ids:
                messages[client_id].append({
                    "type": "edit",
                    "key": key,
                    "row_changes": changes,
                    "version": self.data_version
                })

