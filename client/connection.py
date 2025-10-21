"""
WebSocket client connection handler with auto-reconnection
"""

import asyncio
import websockets
from typing import Callable, Optional, Dict, Any
import json
from datetime import datetime


class ChatConnection:
    """Manages WebSocket connection to the chat server with auto-reconnection"""

    def __init__(self, server_url: str, user_id: int, token: str):
        self.server_url = server_url
        self.user_id = user_id
        self.token = token
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.connected = False
        self.message_callback: Optional[Callable] = None
        self.status_callback: Optional[Callable] = None
        self.reconnect_delay = 1  # Initial reconnect delay in seconds
        self.max_reconnect_delay = 60
        self.message_queue = []  # Queue messages when offline
        self.receive_task: Optional[asyncio.Task] = None

    async def connect(self):
        """Connect to the WebSocket server"""
        try:
            url = f"{self.server_url}/ws/{self.user_id}"
            self.websocket = await websockets.connect(url)
            self.connected = True
            self.running = True
            self.reconnect_delay = 1  # Reset delay on successful connection

            if self.status_callback:
                self.status_callback("connected")

            # Send queued messages
            await self.send_queued_messages()

            # Start receive loop
            self.receive_task = asyncio.create_task(self.receive_messages())

        except Exception as e:
            self.connected = False
            if self.status_callback:
                self.status_callback(f"connection_failed: {e}")
            raise

    async def disconnect(self):
        """Disconnect from the server"""
        self.running = False
        self.connected = False

        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass

        if self.websocket:
            await self.websocket.close()

        if self.status_callback:
            self.status_callback("disconnected")

    async def send_message(self, content: str, room_id: str = "general"):
        """Send a message to the server"""
        message_data = {
            "type": "message",
            "content": content,
            "room_id": room_id
        }

        if self.connected and self.websocket:
            try:
                await self.websocket.send(json.dumps(message_data))
            except Exception as e:
                # Queue message if send fails
                self.message_queue.append(message_data)
                if self.status_callback:
                    self.status_callback(f"send_failed: {e}")
        else:
            # Queue message when offline
            self.message_queue.append(message_data)
            if self.status_callback:
                self.status_callback("offline_queued")

    async def send_pong(self):
        """Respond to server ping with pong"""
        if self.connected and self.websocket:
            try:
                await self.websocket.send(json.dumps({"type": "pong"}))
            except Exception:
                pass

    async def send_typing_indicator(self, is_typing: bool):
        """Send typing indicator to server"""
        if self.connected and self.websocket:
            try:
                typing_data = {
                    "type": "typing",
                    "is_typing": is_typing
                }
                await self.websocket.send(json.dumps(typing_data))
            except Exception:
                pass

    async def send_queued_messages(self):
        """Send all queued messages after reconnection"""
        if not self.message_queue:
            return

        for message_data in self.message_queue:
            try:
                if self.websocket:
                    await self.websocket.send(json.dumps(message_data))
            except Exception as e:
                if self.status_callback:
                    self.status_callback(f"queue_send_failed: {e}")
                break

        # Clear successfully sent messages
        self.message_queue.clear()

    async def receive_messages(self):
        """Receive messages from the server"""
        while self.running and self.websocket:
            try:
                raw_message = await self.websocket.recv()
                message_data = json.loads(raw_message)

                # Handle different message types
                await self.handle_message(message_data)

            except websockets.exceptions.ConnectionClosed:
                self.connected = False
                if self.status_callback:
                    self.status_callback("connection_lost")

                if self.running:
                    await self.handle_reconnect()
                break

            except json.JSONDecodeError as e:
                if self.status_callback:
                    self.status_callback(f"json_error: {e}")

            except Exception as e:
                if self.status_callback:
                    self.status_callback(f"receive_error: {e}")

    async def handle_message(self, message_data: Dict[str, Any]):
        """Handle different types of messages from server"""
        message_type = message_data.get("type")

        if message_type == "ping":
            # Respond to heartbeat
            await self.send_pong()

        elif message_type == "message":
            # Chat message - pass to callback
            if self.message_callback:
                self.message_callback(message_data)

        elif message_type == "user_joined":
            # User joined notification
            if self.message_callback:
                self.message_callback(message_data)

        elif message_type == "user_left":
            # User left notification
            if self.message_callback:
                self.message_callback(message_data)

        elif message_type == "active_users":
            # Active users list
            if self.message_callback:
                self.message_callback(message_data)

        elif message_type == "error":
            # Error message from server
            if self.message_callback:
                self.message_callback(message_data)

        elif message_type == "typing":
            # Typing indicator from another user
            if self.message_callback:
                self.message_callback(message_data)

    async def handle_reconnect(self):
        """Handle reconnection with exponential backoff"""
        if not self.running:
            return

        if self.status_callback:
            self.status_callback(f"reconnecting in {self.reconnect_delay}s")

        await asyncio.sleep(self.reconnect_delay)

        try:
            await self.connect()
            if self.status_callback:
                self.status_callback("reconnected")
        except Exception as e:
            # Exponential backoff
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)

            if self.status_callback:
                self.status_callback(f"reconnect_failed: {e}")

            # Try again
            await self.handle_reconnect()

    def on_message(self, callback: Callable):
        """Register a callback for incoming messages"""
        self.message_callback = callback

    def on_status_change(self, callback: Callable):
        """Register a callback for connection status changes"""
        self.status_callback = callback
