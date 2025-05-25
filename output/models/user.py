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

