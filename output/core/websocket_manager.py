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

