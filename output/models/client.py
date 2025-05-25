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

