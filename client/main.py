"""
Terminal Chat Client - Entry point
"""

import asyncio
import aiohttp
import os
from typing import Dict, Any
from .ui import ChatApp, ChatScreen
from .connection import ChatConnection
from .config import get_config
from .crypto import get_or_create_encryption


class ChatClient:
    """Main chat client controller integrated with Textual"""

    def __init__(self, server_url: str = None):
        # Load configuration
        self.config = get_config()

        # Use provided server_url or config value
        self.server_url = server_url or self.config.server_url
        self.ws_url = self.server_url.replace('http://', 'ws://').replace('https://', 'wss://')

        self.app = ChatApp()
        self.connection: ChatConnection = None
        self.user_id: int = None
        self.username: str = None
        self.token: str = None

        # Initialize encryption
        self.encryption = get_or_create_encryption()

        # Set up callbacks
        self.app.set_login_callback(self.handle_login_sync)
        self.app.set_send_message_callback(self.handle_send_message_sync)

    def handle_login_sync(self, username: str, password: str, action: str):
        """Synchronous wrapper for login callback"""
        self.app.run_worker(self.handle_login(username, password, action), exclusive=True)

    def handle_send_message_sync(self, message: str):
        """Synchronous wrapper for send message callback"""
        self.app.run_worker(self.send_message(message))

    def handle_typing_indicator_sync(self, is_typing: bool):
        """Synchronous wrapper for typing indicator callback"""
        self.app.run_worker(self.send_typing_indicator(is_typing))

    async def handle_login(self, username: str, password: str, action: str):
        """Handle login or registration"""
        try:
            async with aiohttp.ClientSession() as session:
                endpoint = f"{self.server_url}/api/{action}"
                data = {"username": username, "password": password}

                try:
                    async with session.post(endpoint, json=data, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status in [200, 201]:
                            result = await response.json()
                            self.token = result.get("access_token")
                            self.user_id = result.get("user_id")
                            self.username = result.get("username")

                            # Switch to chat screen
                            self.app.show_chat(self.username, self.user_id, self.token)

                            # Connect to WebSocket
                            await self.connect_websocket()

                            # Load message history
                            await self.load_history()

                        else:
                            try:
                                error_data = await response.json()
                                error_msg = error_data.get("detail", f"Server error ({response.status})")
                            except:
                                error_msg = f"Server returned status {response.status}"
                            self.app.show_login_error(error_msg)

                except aiohttp.ClientConnectorError:
                    self.app.show_login_error(f"Cannot connect to server at {self.server_url}. Is it running?")
                except aiohttp.ClientResponseError as e:
                    self.app.show_login_error(f"Server error: {e.status}")
                except asyncio.TimeoutError:
                    self.app.show_login_error("Connection timeout. Server is not responding.")

        except aiohttp.ClientError as e:
            self.app.show_login_error(f"Network error: {type(e).__name__}")
        except Exception as e:
            self.app.show_login_error(f"Unexpected error: {type(e).__name__}: {str(e)}")

    async def connect_websocket(self):
        """Connect to WebSocket server"""
        try:
            self.connection = ChatConnection(self.ws_url, self.user_id, self.token)

            # Set up message and status callbacks
            self.connection.on_message(self.handle_incoming_message)
            self.connection.on_status_change(self.handle_status_change)

            # Connect
            await self.connection.connect()

            # Show encryption info
            chat_screen = self.app.get_chat_screen()
            if chat_screen:
                from pathlib import Path
                key_path = Path.home() / ".terminal-chat" / "encryption.key"
                chat_screen.add_system_message("End-to-end encryption enabled")
                chat_screen.add_system_message(f"Key location: {key_path}")

                # Set up typing indicator callback
                chat_screen.set_typing_indicator_callback(self.handle_typing_indicator_sync)

        except ConnectionRefusedError:
            chat_screen = self.app.get_chat_screen()
            if chat_screen:
                chat_screen.update_status("Connection refused - is the server running?")
                chat_screen.add_system_message("Cannot connect to server. Please check if the server is running.")
        except TimeoutError:
            chat_screen = self.app.get_chat_screen()
            if chat_screen:
                chat_screen.update_status("Connection timeout")
                chat_screen.add_system_message("Connection timed out. Will retry automatically...")
        except Exception as e:
            chat_screen = self.app.get_chat_screen()
            if chat_screen:
                chat_screen.update_status(f"Connection error")
                chat_screen.add_system_message(f"Failed to connect: {str(e)}")

    async def load_history(self):
        """Load message history from server"""
        chat_screen = self.app.get_chat_screen()

        try:
            # Show loading indicator
            if chat_screen:
                chat_screen.update_status("Loading message history...")

            async with aiohttp.ClientSession() as session:
                history_limit = self.config.get('message_history_limit', 50)
                endpoint = f"{self.server_url}/api/history?limit={history_limit}"

                async with session.get(endpoint) as response:
                    if response.status == 200:
                        messages = await response.json()

                        if chat_screen:
                            if messages:
                                chat_screen.add_system_message(f"Loading {len(messages)} messages...")

                            for msg in messages:
                                # Decrypt message content
                                encrypted_content = msg.get("content")
                                try:
                                    content = self.encryption.decrypt(encrypted_content)
                                except Exception as e:
                                    content = f"[Decryption failed]"

                                # Don't play sound for history messages
                                chat_screen.add_message(
                                    msg.get("username"),
                                    content,
                                    msg.get("timestamp"),
                                    play_sound=False
                                )

                            if messages:
                                chat_screen.add_system_message("Message history loaded")
                            chat_screen.update_status("Connected")

        except Exception as e:
            if chat_screen:
                chat_screen.add_system_message(f"Failed to load history: {str(e)}")
                chat_screen.update_status("Connected (history load failed)")

    def handle_incoming_message(self, message_data: Dict[str, Any]):
        """Handle incoming WebSocket messages"""
        message_type = message_data.get("type")
        chat_screen = self.app.get_chat_screen()

        if not chat_screen:
            return

        if message_type == "message":
            # Regular chat message - decrypt content
            username = message_data.get("username", "Unknown")
            encrypted_content = message_data.get("content", "")
            timestamp = message_data.get("timestamp")

            # Decrypt the message
            try:
                content = self.encryption.decrypt(encrypted_content)
            except Exception as e:
                content = f"[Decryption failed: {str(e)}]"

            chat_screen.add_message(username, content, timestamp)

        elif message_type == "user_joined":
            # User joined notification
            username = message_data.get("username", "Someone")
            chat_screen.add_system_message(f"{username} joined the chat")

        elif message_type == "user_left":
            # User left notification
            username = message_data.get("username", "Someone")
            chat_screen.add_system_message(f"{username} left the chat")

        elif message_type == "active_users":
            # Active users count and list update
            count = message_data.get("count", 0)
            user_info = message_data.get("user_info", [])

            # Extract usernames from user_info
            usernames = [info.get("username") for info in user_info if info.get("username")]

            chat_screen.update_online_users(count, usernames)

        elif message_type == "error":
            # Error message from server
            error_message = message_data.get("message", "Unknown error")
            chat_screen.add_system_message(f"Error: {error_message}")

        elif message_type == "typing":
            # Typing indicator from another user
            username = message_data.get("username", "Someone")
            is_typing = message_data.get("is_typing", False)
            chat_screen.update_typing_indicator(username, is_typing)

    def handle_status_change(self, status: str):
        """Handle connection status changes"""
        chat_screen = self.app.get_chat_screen()
        if not chat_screen:
            return

        status_message = status
        if status == "connected":
            status_message = "Connected"
        elif status == "disconnected":
            status_message = "Disconnected"
        elif status == "connection_lost":
            status_message = "Connection lost..."
        elif status.startswith("reconnecting"):
            status_message = "Reconnecting..."
        elif status == "reconnected":
            status_message = "Reconnected!"
        elif status == "offline_queued":
            status_message = "Offline - message queued"

        chat_screen.update_status(status_message)

    async def send_typing_indicator(self, is_typing: bool):
        """Send typing indicator to server"""
        if self.connection and self.connection.connected:
            try:
                await self.connection.send_typing_indicator(is_typing)
            except Exception:
                # Silently fail for typing indicators
                pass

    async def send_message(self, message: str):
        """Handle sending a message"""
        try:
            # Validate message length
            if len(message) > 5000:
                chat_screen = self.app.get_chat_screen()
                if chat_screen:
                    chat_screen.add_system_message("Message too long (max 5000 characters)")
                return

            if self.connection and self.connection.connected:
                try:
                    # Encrypt message before sending
                    encrypted_message = self.encryption.encrypt(message)
                    await self.connection.send_message(encrypted_message)
                except Exception as e:
                    chat_screen = self.app.get_chat_screen()
                    if chat_screen:
                        chat_screen.add_system_message(f"Failed to send message - will retry when reconnected")
                        # Queue the message for retry
                        if self.connection:
                            encrypted_message = self.encryption.encrypt(message)
                            await self.connection.send_message(encrypted_message)
            else:
                chat_screen = self.app.get_chat_screen()
                if chat_screen:
                    chat_screen.add_system_message("Offline - message queued for sending")
                    # Still try to queue the message (encrypt it first)
                    if self.connection:
                        try:
                            encrypted_message = self.encryption.encrypt(message)
                            await self.connection.send_message(encrypted_message)
                        except Exception as e:
                            chat_screen.add_system_message(f"Failed to queue message: {str(e)}")
        except Exception as e:
            chat_screen = self.app.get_chat_screen()
            if chat_screen:
                chat_screen.add_system_message(f"Error: {str(e)}")

    async def shutdown(self):
        """Clean shutdown"""
        if self.connection:
            await self.connection.disconnect()

    def run(self):
        """Run the chat client"""
        try:
            self.app.run()
        finally:
            # Cleanup
            if self.connection:
                asyncio.run(self.shutdown())


def main():
    """Entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Terminal Chat Client - A secure end-to-end encrypted chat application"
    )
    parser.add_argument(
        "--server",
        "-s",
        type=str,
        help="Server URL (e.g., http://localhost:8000)",
        default=None
    )
    parser.add_argument(
        "--config",
        "-c",
        action="store_true",
        help="Show current configuration and exit"
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="Terminal Chat Client v1.0.0"
    )

    args = parser.parse_args()

    # Show config and exit if requested
    if args.config:
        from .config import get_config
        config = get_config()
        print("Current Configuration:")
        print(f"  Config file: {config.config_file}")
        print(f"  Server URL: {config.server_url}")
        print(f"  Auto-reconnect: {config.get('auto_reconnect')}")
        print(f"  Notification sound: {config.get('notification_sound')}")
        print(f"  Message history limit: {config.get('message_history_limit')}")
        return

    # Create and run client
    client = ChatClient(server_url=args.server)
    client.run()


if __name__ == "__main__":
    main()
