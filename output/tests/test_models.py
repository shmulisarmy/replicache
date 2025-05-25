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
