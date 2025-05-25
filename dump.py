# models/user.py
"""User model for the real-time sync application."""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class User:
    """Represents a user with basic profile information."""
    
    name: str
    age: int
    email: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary representation."""
        return {
            'name': self.name,
            'age': self.age,
            'email': self.email
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create User instance from dictionary."""
        return cls(
            name=data['name'],
            age=data['age'],
            email=data['email']
        )
    
    def __repr__(self) -> str:
        return f"User(name={self.name!r}, age={self.age!r}, email={self.email!r})"


# models/action.py
"""Action models for representing data changes."""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict
from datetime import datetime


class ActionType(Enum):
    """Types of actions that can be performed on data."""
    APPEND = "append"
    DELETE = "delete"
    EDIT = "edit"


@dataclass
class BaseAction(ABC):
    """Base class for all data actions."""
    
    type: ActionType
    version: int
    client_id: uuid.UUID
    key: Any
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary representation."""
        return {
            'type': self.type.value,
            'version': self.version,
            'client_id': str(self.client_id),
            'key': self.key,
            'timestamp': self.timestamp.isoformat()
        }


class AppendAction(BaseAction):
    """Action for appending new data."""
    
    def __init__(self, data: Any, key: Any, version: int, client_id: uuid.UUID, timestamp: datetime):
        super().__init__(ActionType.APPEND, version, client_id, key, timestamp)
        self.data = data
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result['data'] = self.data
        return result
    
    def __repr__(self) -> str:
        return f"AppendAction(data={self.data!r}, key={self.key!r}, version={self.version!r})"


class DeleteAction(BaseAction):
    """Action for deleting data."""
    
    def __init__(self, key: Any, version: int, client_id: uuid.UUID, timestamp: datetime):
        super().__init__(ActionType.DELETE, version, client_id, key, timestamp)
    
    def __repr__(self) -> str:
        return f"DeleteAction(key={self.key!r}, version={self.version!r})"


class EditAction(BaseAction):
    """Action for editing existing data."""
    
    def __init__(self, value: Any, key: Any, field: str, version: int, client_id: uuid.UUID, timestamp: datetime):
        super().__init__(ActionType.EDIT, version, client_id, key, timestamp)
        self.field = field
        self.value = value
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            'field': self.field,
            'value': self.value
        })
        return result
    
    def __repr__(self) -> str:
        return f"EditAction(value={self.value!r}, key={self.key!r}, field={self.field!r}, version={self.version!r})"


# models/client.py
"""Client model for managing connected clients."""

import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class Client:
    """Represents a connected client with their current state."""
    
    id: uuid.UUID
    data_version: int
    messages: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_message(self, message: Dict[str, Any]) -> None:
        """Add a message to be sent to this client."""
        self.messages.append(message)
    
    def clear_messages(self) -> None:
        """Clear all pending messages."""
        self.messages.clear()
    
    def __repr__(self) -> str:
        return f"Client(id={self.id!r}, data_version={self.data_version!r})"


# core/database.py
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


# core/exceptions.py
"""Custom exceptions for the application."""


class SyncError(Exception):
    """Base exception for sync-related errors."""
    pass


class DatabaseError(SyncError):
    """Exception raised for database operation errors."""
    pass


class ConflictError(SyncError):
    """Exception raised when data conflicts occur."""
    pass


class ClientError(SyncError):
    """Exception raised for client-related errors."""
    pass


# core/websocket_manager.py
"""WebSocket connection manager for handling real-time communication."""

import json
import uuid
import asyncio
from typing import Dict, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

from models.client import Client
from models.action import AppendAction, DeleteAction, EditAction
from core.database import Database
from core.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and message routing."""
    
    def __init__(self, database: Database):
        self.database = database
        self.connections: Dict[str, WebSocket] = {}
        self.clients: Dict[str, Client] = {}
        self.pending_actions = []
    
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """
        Accept a new WebSocket connection and register the client.
        
        Args:
            websocket: WebSocket connection
            client_id: Unique identifier for the client
        """
        await websocket.accept()
        self.connections[client_id] = websocket
        self.clients[client_id] = Client(
            id=uuid.UUID(client_id) if self._is_valid_uuid(client_id) else uuid.uuid4(),
            data_version=self.database.get_data_version()
        )
        logger.info(f"Client {client_id} connected")
    
    def disconnect(self, client_id: str) -> None:
        """
        Remove a client connection.
        
        Args:
            client_id: ID of the client to disconnect
        """
        self.connections.pop(client_id, None)
        self.clients.pop(client_id, None)
        logger.info(f"Client {client_id} disconnected")
    
    async def handle_message(self, client_id: str, message: str) -> None:
        """
        Process an incoming message from a client.
        
        Args:
            client_id: ID of the sending client
            message: JSON message string
            
        Raises:
            ClientError: If message processing fails
        """
        try:
            data = json.loads(message)
            action = self._create_action_from_message(client_id, data)
            self.pending_actions.append(action)
            
            # Process actions with a small delay to batch them
            await asyncio.sleep(0.1)
            await self._process_pending_actions()
            
        except json.JSONDecodeError as e:
            raise ClientError(f"Invalid JSON message: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {str(e)}")
            raise ClientError(f"Failed to process message: {str(e)}") from e
    
    def _create_action_from_message(self, client_id: str, data: Dict) -> object:
        """Create an action object from a client message."""
        client = self.clients[client_id]
        timestamp = datetime.fromisoformat(data.get('time', datetime.now().isoformat()).replace('Z', '+00:00'))
        
        action_type = data.get('type')
        if action_type == 'add':
            return AppendAction(
                data=data['data'],
                key=data['key'],
                version=self.database.get_data_version(),
                client_id=client.id,
                timestamp=timestamp
            )
        elif action_type == 'edit':
            return EditAction(
                value=data['value'],
                key=data['key'],
                field=data['field'],
                version=self.database.get_data_version(),
                client_id=client.id,
                timestamp=timestamp
            )
        elif action_type == 'delete':
            return DeleteAction(
                key=data['key'],
                version=self.database.get_data_version(),
                client_id=client.id,
                timestamp=timestamp
            )
        else:
            raise ClientError(f"Unknown action type: {action_type}")
    
    async def _process_pending_actions(self) -> None:
        """Process all pending actions and send responses to clients."""
        if not self.pending_actions:
            return
        
        try:
            client_ids = [client.id for client in self.clients.values()]
            messages = await self.database.apply_mutations(self.pending_actions, client_ids)
            
            # Send messages to clients
            for client_id_str, websocket in self.connections.items():
                client = self.clients[client_id_str]
                client_messages = messages.get(client.id, [])
                
                for message in client_messages:
                    try:
                        await websocket.send_text(json.dumps(message))
                    except Exception as e:
                        logger.error(f"Failed to send message to {client_id_str}: {str(e)}")
            
            self.pending_actions.clear()
            
        except Exception as e:
            logger.error(f"Error processing actions: {str(e)}")
            self.pending_actions.clear()
    
    @staticmethod
    def _is_valid_uuid(uuid_string: str) -> bool:
        """Check if a string is a valid UUID."""
        try:
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            return False


# api/main.py
"""Main FastAPI application with WebSocket endpoints."""

import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from models.user import User
from core.database import Database
from core.websocket_manager import WebSocketManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Real-time Sync API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database with sample data
initial_users = [
    User("John", 20, "john@example.com"),
    User("Jane", 21, "jane@example.com"),
    User("Alice", 22, "alice@example.com"),
    User("Bob", 23, "bob@example.com"),
]

database = Database(initial_users, key_extractor=lambda user: user.name)
websocket_manager = WebSocketManager(database)


@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "message": "Real-time Sync API",
        "version": "1.0.0",
        "endpoints": {
            "websocket": "/ws/{client_id}",
            "database": "/db"
        }
    }


@app.get("/db")
async def get_database():
    """Get current database state."""
    return {
        "data": database.get_all_data(),
        "version": database.get_data_version(),
        "connected_clients": len(websocket_manager.clients)
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database_version": database.get_data_version(),
        "connected_clients": len(websocket_manager.clients)
    }


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time communication with clients.
    
    Args:
        websocket: WebSocket connection
        client_id: Unique identifier for the client
    """
    try:
        await websocket_manager.connect(websocket, client_id)
        
        while True:
            message = await websocket.receive_text()
            await websocket_manager.handle_message(client_id, message)
            
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {str(e)}")
    finally:
        websocket_manager.disconnect(client_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


# tests/test_database.py
"""Unit tests for the Database class."""

import pytest
import uuid
from datetime import datetime
from models.user import User
from models.action import AppendAction, EditAction, DeleteAction
from core.database import Database


@pytest.fixture
def sample_users():
    """Sample users for testing."""
    return [
        User("Alice", 25, "alice@example.com"),
        User("Bob", 30, "bob@example.com")
    ]


@pytest.fixture
def database(sample_users):
    """Database instance for testing."""
    return Database(sample_users, key_extractor=lambda user: user.name)


@pytest.mark.asyncio
async def test_database_initialization(database):
    """Test database initialization."""
    data = database.get_all_data()
    assert len(data) == 2
    assert "Alice" in data
    assert "Bob" in data
    assert database.get_data_version() == 1


@pytest.mark.asyncio
async def test_append_action(database):
    """Test adding new data."""
    client_id = uuid.uuid4()
    action = AppendAction(
        data=User("Charlie", 35, "charlie@example.com"),
        key="Charlie",
        version=1,
        client_id=client_id,
        timestamp=datetime.now()
    )
    
    messages = await database.apply_mutations([action], [client_id])
    
    assert "Charlie" in database.get_all_data()
    assert len(messages[client_id]) == 1
    assert messages[client_id][0]["type"] == "add"


@pytest.mark.asyncio
async def test_edit_action(database):
    """Test editing existing data."""
    client_id = uuid.uuid4()
    action = EditAction(
        value=26,
        key="Alice",
        field="age",
        version=1,
        client_id=client_id,
        timestamp=datetime.now()
    )
    
    messages = await database.apply_mutations([action], [client_id])
    
    alice_data = database.get_all_data()["Alice"]["data"]
    assert alice_data.age == 26
    assert len(messages[client_id]) == 1
    assert messages[client_id][0]["type"] == "edit"


@pytest.mark.asyncio
async def test_delete_action(database):
    """Test deleting data."""
    client_id = uuid.uuid4()
    action = DeleteAction(
        key="Alice",
        version=1,
        client_id=client_id,
        timestamp=datetime.now()
    )
    
    messages = await database.apply_mutations([action], [client_id])
    
    assert "Alice" not in database.get_all_data()
    assert len(messages[client_id]) == 1
    assert messages[client_id][0]["type"] == "delete"


@pytest.mark.asyncio
async def test_conflict_detection(database):
    """Test conflict detection between delete and edit actions."""
    client_id1 = uuid.uuid4()
    client_id2 = uuid.uuid4()
    
    edit_action = EditAction(
        value=26,
        key="Alice",
        field="age",
        version=1,
        client_id=client_id1,
        timestamp=datetime.now()
    )
    
    delete_action = DeleteAction(
        key="Alice",
        version=1,
        client_id=client_id2,
        timestamp=datetime.now()
    )
    
    messages = await database.apply_mutations([edit_action, delete_action], [client_id1, client_id2])
    
    # Should detect conflict and notify the deleting client
    assert any(msg["type"] == "conflict" for msg in messages[client_id2])
    assert "Alice" in database.get_all_data()  # Alice should still exist


# tests/test_models.py
"""Unit tests for model classes."""

import pytest
import uuid
from datetime import datetime
from models.user import User
from models.action import AppendAction, EditAction, DeleteAction
from models.client import Client


def test_user_creation():
    """Test User model creation and methods."""
    user = User("John", 30, "john@example.com")
    assert user.name == "John"
    assert user.age == 30
    assert user.email == "john@example.com"
    
    user_dict = user.to_dict()
    assert user_dict == {"name": "John", "age": 30, "email": "john@example.com"}
    
    user_from_dict = User.from_dict(user_dict)
    assert user_from_dict == user


def test_append_action():
    """Test AppendAction creation."""
    client_id = uuid.uuid4()
    timestamp = datetime.now()
    user_data = {"name": "John", "age": 30, "email": "john@example.com"}
    
    action = AppendAction(user_data, "John", 1, client_id, timestamp)
    
    assert action.data == user_data
    assert action.key == "John"
    assert action.version == 1
    assert action.client_id == client_id
    assert action.timestamp == timestamp


def test_client_model():
    """Test Client model functionality."""
    client_id = uuid.uuid4()
    client = Client(client_id, 1)
    
    assert client.id == client_id
    assert client.data_version == 1
    assert len(client.messages) == 0
    
    message = {"type": "test", "data": "test_data"}
    client.add_message(message)
    assert len(client.messages) == 1
    assert client.messages[0] == message
    
    client.clear_messages()
    assert len(client.messages) == 0

