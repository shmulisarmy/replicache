from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any
import time
import uuid

class ActionType(Enum):
    APPEND = "append"
    DELETE = "delete"
    EDIT = "edit"

@dataclass
class Action:
    type: ActionType
    version: int
    client_id: uuid.UUID
    key: Any
    time: any


    
class AppendAction(Action):
    def __init__(self, data: Any, key: Any, version: int, client_id: uuid.UUID, time):
        super().__init__(ActionType.APPEND, version, client_id, key, time)
        self.data = data

    @abstractmethod
    def _(self):
        pass
    def __repr__(self):
        return f"AppendAction(data={self.data!r}, version={self.version!r})"


    
class DeleteAction(Action):
    def __init__(self, key: Any, version: int, client_id: uuid.UUID, time):
        super().__init__(ActionType.DELETE, version, client_id, key, time)

    def __repr__(self):
        return f"DeleteAction(key={self.key!r}, version={self.version!r})"




class EditAction(Action):
    def __init__(self, value: Any, key: Any, field: Any, version: int, client_id: uuid.UUID, time):
        super().__init__(ActionType.EDIT, version, client_id, key, time)
        self.field = field
        self.value = value

    def __repr__(self):
        return f"EditAction(value={self.value!r}, key={self.key!r}, field={self.field!r}, version={self.version!r})"

