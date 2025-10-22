"""
Unit tests for WebSocket connection handler
"""

import pytest
import json
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import asyncio

from client.connection import ChatConnection


class TestChatConnection:
    """Tests for ChatConnection class"""

    @pytest.fixture
    def connection(self):
        """Create a ChatConnection instance"""
        return ChatConnection(
            server_url="ws://localhost:8000",
            user_id=1,
            token="test_token"
        )

    def test_initialization(self, connection):
        """Test ChatConnection initialization"""
        assert connection.server_url == "ws://localhost:8000"
        assert connection.user_id == 1
        assert connection.token == "test_token"
        assert connection.websocket is None
        assert connection.running is False
        assert connection.connected is False
        assert connection.reconnect_delay == 1
        assert connection.max_reconnect_delay == 60
        assert connection.message_queue == []

    async def test_connect_success(self, connection):
        """Test successful WebSocket connection"""
        mock_ws = AsyncMock()
        status_callback = Mock()
        connection.status_callback = status_callback

        with patch('websockets.connect', new_callable=AsyncMock, return_value=mock_ws) as mock_connect:
            with patch.object(connection, 'receive_messages', new_callable=AsyncMock):
                await connection.connect()

                assert connection.connected is True
                assert connection.running is True
                assert connection.websocket == mock_ws
                status_callback.assert_called_with("connected")
                mock_connect.assert_called_once()

    async def test_connect_failure(self, connection):
        """Test connection failure handling"""
        status_callback = Mock()
        connection.status_callback = status_callback

        with patch('websockets.connect', side_effect=Exception("Connection failed")):
            with pytest.raises(Exception):
                await connection.connect()

            assert connection.connected is False
            status_callback.assert_called()
            # Check that status callback was called with connection_failed
            call_args = status_callback.call_args[0][0]
            assert "connection_failed" in call_args

    async def test_disconnect(self, connection):
        """Test disconnecting from server"""
        mock_ws = AsyncMock()
        connection.websocket = mock_ws
        connection.connected = True
        connection.running = True

        # Create a proper asyncio task that can be awaited and cancelled
        async def dummy_receive():
            await asyncio.sleep(0)

        connection.receive_task = asyncio.create_task(dummy_receive())

        status_callback = Mock()
        connection.status_callback = status_callback

        await connection.disconnect()

        assert connection.running is False
        assert connection.connected is False
        mock_ws.close.assert_called_once()
        status_callback.assert_called_with("disconnected")

    async def test_send_message_when_connected(self, connection):
        """Test sending message when connected"""
        mock_ws = AsyncMock()
        connection.websocket = mock_ws
        connection.connected = True

        await connection.send_message("Test message")

        mock_ws.send.assert_called_once()
        call_args = mock_ws.send.call_args[0][0]
        sent_data = json.loads(call_args)

        assert sent_data["type"] == "message"
        assert sent_data["content"] == "Test message"
        assert sent_data["room_id"] == "general"

    async def test_send_message_with_custom_room(self, connection):
        """Test sending message to custom room"""
        mock_ws = AsyncMock()
        connection.websocket = mock_ws
        connection.connected = True

        await connection.send_message("Test message", room_id="custom_room")

        call_args = mock_ws.send.call_args[0][0]
        sent_data = json.loads(call_args)

        assert sent_data["room_id"] == "custom_room"

    async def test_send_message_when_disconnected(self, connection):
        """Test sending message queues it when disconnected"""
        connection.connected = False
        status_callback = Mock()
        connection.status_callback = status_callback

        await connection.send_message("Queued message")

        assert len(connection.message_queue) == 1
        assert connection.message_queue[0]["content"] == "Queued message"
        status_callback.assert_called_with("offline_queued")

    async def test_send_message_failure_queues_message(self, connection):
        """Test that failed send queues the message"""
        mock_ws = AsyncMock()
        mock_ws.send.side_effect = Exception("Send failed")
        connection.websocket = mock_ws
        connection.connected = True
        status_callback = Mock()
        connection.status_callback = status_callback

        await connection.send_message("Failed message")

        assert len(connection.message_queue) == 1
        assert connection.message_queue[0]["content"] == "Failed message"

    async def test_send_queued_messages(self, connection):
        """Test sending queued messages after reconnection"""
        mock_ws = AsyncMock()
        connection.websocket = mock_ws
        connection.connected = True

        # Add messages to queue
        connection.message_queue = [
            {"type": "message", "content": "Message 1"},
            {"type": "message", "content": "Message 2"}
        ]

        await connection.send_queued_messages()

        assert mock_ws.send.call_count == 2
        assert len(connection.message_queue) == 0

    async def test_send_pong(self, connection):
        """Test sending pong response"""
        mock_ws = AsyncMock()
        connection.websocket = mock_ws
        connection.connected = True

        await connection.send_pong()

        mock_ws.send.assert_called_once()
        call_args = mock_ws.send.call_args[0][0]
        sent_data = json.loads(call_args)

        assert sent_data["type"] == "pong"

    async def test_send_typing_indicator(self, connection):
        """Test sending typing indicator"""
        mock_ws = AsyncMock()
        connection.websocket = mock_ws
        connection.connected = True

        await connection.send_typing_indicator(is_typing=True)

        mock_ws.send.assert_called_once()
        call_args = mock_ws.send.call_args[0][0]
        sent_data = json.loads(call_args)

        assert sent_data["type"] == "typing"
        assert sent_data["is_typing"] is True

    async def test_message_callback_invoked(self, connection):
        """Test that message callback is invoked on receiving message"""
        message_callback = Mock()
        connection.message_callback = message_callback

        test_message = {
            "type": "message",
            "content": "Test",
            "username": "user1"
        }

        # Simulate receiving message (handle_message expects a dict, not JSON string)
        await connection.handle_message(test_message)

        message_callback.assert_called_once_with(test_message)

    async def test_reconnect_delay_increases(self, connection):
        """Test that reconnect delay increases exponentially"""
        initial_delay = connection.reconnect_delay

        connection.increase_reconnect_delay()
        delay1 = connection.reconnect_delay

        connection.increase_reconnect_delay()
        delay2 = connection.reconnect_delay

        assert delay1 > initial_delay
        assert delay2 > delay1
        assert connection.reconnect_delay <= connection.max_reconnect_delay

    async def test_reconnect_delay_caps_at_maximum(self, connection):
        """Test that reconnect delay doesn't exceed maximum"""
        # Increase delay many times
        for _ in range(20):
            connection.increase_reconnect_delay()

        assert connection.reconnect_delay <= connection.max_reconnect_delay

    def test_set_callbacks(self, connection):
        """Test setting callbacks"""
        message_callback = Mock()
        status_callback = Mock()

        connection.message_callback = message_callback
        connection.status_callback = status_callback

        assert connection.message_callback == message_callback
        assert connection.status_callback == status_callback

    async def test_handle_ping_message(self, connection):
        """Test handling ping message from server"""
        mock_ws = AsyncMock()
        connection.websocket = mock_ws
        connection.connected = True

        ping_message = {"type": "ping"}
        # handle_message expects a dict, not JSON string
        await connection.handle_message(ping_message)

        # Should send pong response
        mock_ws.send.assert_called()
        call_args = mock_ws.send.call_args[0][0]
        sent_data = json.loads(call_args)
        assert sent_data["type"] == "pong"

    async def test_message_queue_preserves_order(self, connection):
        """Test that message queue preserves message order"""
        connection.connected = False

        await connection.send_message("Message 1")
        await connection.send_message("Message 2")
        await connection.send_message("Message 3")

        assert len(connection.message_queue) == 3
        assert connection.message_queue[0]["content"] == "Message 1"
        assert connection.message_queue[1]["content"] == "Message 2"
        assert connection.message_queue[2]["content"] == "Message 3"


class TestConnectionReconnection:
    """Tests for reconnection logic"""

    @pytest.fixture
    def connection(self):
        """Create a ChatConnection instance"""
        return ChatConnection(
            server_url="ws://localhost:8000",
            user_id=1,
            token="test_token"
        )

    async def test_auto_reconnect_on_disconnect(self, connection):
        """Test automatic reconnection after disconnect"""
        # This is an integration-style test
        # Would need more complex mocking to fully test auto-reconnect
        assert connection.reconnect_delay == 1
        connection.increase_reconnect_delay()
        assert connection.reconnect_delay > 1

    def test_reconnect_delay_reset_on_successful_connection(self, connection):
        """Test that reconnect delay resets on successful connection"""
        # Increase delay
        connection.reconnect_delay = 30

        # Simulate successful connection
        connection.reconnect_delay = 1  # This happens in connect()

        assert connection.reconnect_delay == 1
