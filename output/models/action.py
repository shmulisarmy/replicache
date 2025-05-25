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

