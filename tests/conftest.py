"""
Pytest configuration and fixtures for terminal-chat-client tests
"""

import pytest
import os
import tempfile
import json
from unittest.mock import Mock, AsyncMock, patch

from client.crypto import MessageEncryption
from client.config import ClientConfig


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config files"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    import shutil
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def encryption_key(temp_config_dir):
    """Create a temporary encryption key for testing"""
    key_path = os.path.join(temp_config_dir, "test_encryption.key")
    encryption = MessageEncryption(key_path=key_path)
    return encryption


@pytest.fixture
def test_config(temp_config_dir):
    """Create a test client configuration"""
    config_path = os.path.join(temp_config_dir, "config.json")
    config = ClientConfig(config_path=config_path)
    return config


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection"""
    ws = Mock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock()
    ws.close = AsyncMock()
    ws.closed = False
    return ws


@pytest.fixture
def mock_aiohttp_session():
    """Create a mock aiohttp ClientSession"""
    session = Mock()
    session.post = AsyncMock()
    session.get = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "username": "testuser",
        "password": "testpass123"
    }


@pytest.fixture
def sample_token_response():
    """Sample JWT token response from server"""
    return {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token",
        "token_type": "bearer",
        "user_id": 1,
        "username": "testuser"
    }


@pytest.fixture
def sample_message():
    """Sample message data"""
    return {
        "type": "message",
        "content": "Hello, this is a test message!",
        "username": "testuser",
        "user_id": 1,
        "timestamp": "2024-01-01T12:00:00Z"
    }


@pytest.fixture
def sample_encrypted_message(encryption_key):
    """Sample encrypted message"""
    plaintext = "Secret message content"
    encrypted = encryption_key.encrypt(plaintext)
    return {
        "plaintext": plaintext,
        "encrypted": encrypted
    }


@pytest.fixture
def sample_message_history():
    """Sample message history from server"""
    return [
        {
            "id": 1,
            "user_id": 1,
            "username": "user1",
            "content": "Message 1",
            "timestamp": "2024-01-01T12:00:00Z",
            "room_id": "general"
        },
        {
            "id": 2,
            "user_id": 2,
            "username": "user2",
            "content": "Message 2",
            "timestamp": "2024-01-01T12:01:00Z",
            "room_id": "general"
        },
        {
            "id": 3,
            "user_id": 1,
            "username": "user1",
            "content": "Message 3",
            "timestamp": "2024-01-01T12:02:00Z",
            "room_id": "general"
        }
    ]


@pytest.fixture
def mock_textual_app():
    """Create a mock Textual application"""
    app = Mock()
    app.post_message = Mock()
    app.call_from_thread = Mock()
    return app


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables"""
    original_env = {}

    # Save original env vars
    env_vars = ["CHAT_SERVER_URL"]
    for var in env_vars:
        original_env[var] = os.environ.get(var)

    # Set test env vars
    os.environ["CHAT_SERVER_URL"] = "http://localhost:8000"

    yield

    # Restore original env vars
    for var, value in original_env.items():
        if value is None:
            os.environ.pop(var, None)
        else:
            os.environ[var] = value


@pytest.fixture
def mock_connection_callbacks():
    """Create mock callbacks for connection events"""
    return {
        "on_message": Mock(),
        "on_status_change": Mock(),
        "on_error": Mock(),
        "on_user_joined": Mock(),
        "on_user_left": Mock()
    }
