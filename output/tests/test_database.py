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

