"""
Textual UI components for the terminal chat client
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Header, Footer, Input, Static, Button, Label, RichLog
from textual.binding import Binding
from textual.screen import Screen
from datetime import datetime
from typing import Optional, Callable
from rich.text import Text
import hashlib


class LoginScreen(Screen):
    """Login and registration screen"""

    CSS = """
    LoginScreen {
        align: center middle;
        background: $surface;
    }

    #login-container {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $panel;
        padding: 2;
    }

    #login-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: $accent;
        padding: 1;
    }

    .login-label {
        width: 100%;
        padding: 1 0;
    }

    .login-input {
        width: 100%;
        margin-bottom: 1;
    }

    #button-container {
        width: 100%;
        height: auto;
        layout: horizontal;
        padding: 1 0;
    }

    Button {
        width: 1fr;
        margin: 0 1;
    }

    #status-label {
        width: 100%;
        text-align: center;
        color: $warning;
        padding: 1 0;
        height: 3;
    }
    """

    def __init__(self, on_login: Callable):
        super().__init__()
        self.on_login = on_login

    def compose(self) -> ComposeResult:
        """Compose the login screen"""
        with Container(id="login-container"):
            yield Label("Terminal Chat", id="login-title")
            yield Label("Username:", classes="login-label")
            yield Input(
                placeholder="Enter username (min 3 chars)",
                id="username-input",
                classes="login-input"
            )
            yield Label("Password:", classes="login-label")
            yield Input(
                placeholder="Enter password (min 6 chars)",
                password=True,
                id="password-input",
                classes="login-input"
            )
            with Horizontal(id="button-container"):
                yield Button("Login", variant="primary", id="login-btn")
                yield Button("Register", variant="success", id="register-btn")
            yield Label("", id="status-label")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        username_input = self.query_one("#username-input", Input)
        password_input = self.query_one("#password-input", Input)
        status_label = self.query_one("#status-label", Label)

        username = username_input.value.strip()
        password = password_input.value.strip()

        # Validation
        if len(username) < 3:
            status_label.update("Username must be at least 3 characters")
            return

        if len(username) > 30:
            status_label.update("Username must be less than 30 characters")
            return

        # Check for valid characters
        if not username.replace('_', '').replace('-', '').isalnum():
            status_label.update("Username: letters, numbers, _, - only")
            return

        if len(password) < 6:
            status_label.update("Password must be at least 6 characters")
            return

        # Determine action
        if event.button.id == "login-btn":
            action = "login"
        elif event.button.id == "register-btn":
            action = "register"
        else:
            return

        status_label.update(f"{action.capitalize()}ing...")

        # Call the login callback
        self.on_login(username, password, action)

    def show_error(self, message: str):
        """Show error message"""
        status_label = self.query_one("#status-label", Label)
        status_label.update(f"Error: {message}")


class ChatScreen(Screen):
    """Main chat interface"""

    CSS = """
    ChatScreen {
        background: $surface;
    }

    #chat-header {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
        padding: 1 2;
    }

    #header-content {
        layout: horizontal;
        width: 100%;
        height: 100%;
    }

    #app-title {
        width: auto;
        text-style: bold;
    }

    #online-users {
        width: auto;
        dock: right;
        text-align: right;
        margin-right: 2;
    }

    #encryption-indicator {
        width: auto;
        dock: right;
        text-align: right;
        color: $success;
        text-style: bold;
    }

    #status-bar {
        dock: top;
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 2;
    }

    #typing-indicator {
        dock: top;
        height: 0;
        background: $surface;
        color: $text-muted;
        padding: 0 2;
        text-style: italic;
        display: none;
    }

    #typing-indicator.visible {
        height: 1;
        display: block;
    }

    #message-display {
        height: 1fr;
        border: solid $primary;
        background: $surface;
        margin: 1;
        padding: 1;
    }

    #input-container {
        dock: bottom;
        height: 3;
        background: $panel;
        padding: 0 2;
    }

    Input {
        width: 100%;
    }

    .message-line {
        padding: 0 0 0 1;
    }

    .message-timestamp {
        color: $text-muted;
    }

    .message-username {
        color: $accent;
        text-style: bold;
    }

    .message-content {
        color: $text;
    }

    .system-message {
        color: $warning;
        text-style: italic;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, username: str, on_send_message: Callable):
        super().__init__()
        self.username = username
        self.on_send_message = on_send_message
        self.online_users_count = 0
        self.online_usernames = []
        # User colors for consistent color assignment
        self.user_colors = {}
        self.available_colors = [
            "cyan", "magenta", "yellow", "blue",
            "green", "bright_cyan", "bright_magenta", "bright_yellow"
        ]
        # Typing indicator tracking
        self.typing_users = set()  # Set of usernames currently typing
        self.typing_indicator_callback = None  # Callback to send typing events
        self.typing_timer = None  # Timer to debounce typing indicator
        self.is_currently_typing = False  # Track if user is currently indicated as typing

    def get_user_color(self, username: str) -> str:
        """Get a consistent color for a username"""
        if username not in self.user_colors:
            # Use hash to get consistent color for username
            hash_value = int(hashlib.md5(username.encode()).hexdigest(), 16)
            color_index = hash_value % len(self.available_colors)
            self.user_colors[username] = self.available_colors[color_index]
        return self.user_colors[username]

    def compose(self) -> ComposeResult:
        """Compose the chat screen"""
        # Header
        with Container(id="chat-header"):
            with Horizontal(id="header-content"):
                yield Label(f"Terminal Chat - {self.username}", id="app-title")
                yield Label("🔒 E2EE", id="encryption-indicator")
                yield Label("Online: 0", id="online-users")

        # Status bar
        yield Label("Connecting...", id="status-bar")

        # Typing indicator
        yield Label("", id="typing-indicator")

        # Message display area
        yield RichLog(id="message-display", highlight=True, markup=True, wrap=True)

        # Input area
        with Container(id="input-container"):
            yield Input(placeholder="Type a message and press Enter...", id="message-input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle message submission"""
        message = event.value.strip()
        if message:
            # Send stop typing indicator before sending message
            if self.typing_indicator_callback:
                self.typing_indicator_callback(False)

            # Check for commands
            if message.startswith('/'):
                self.handle_command(message)
                event.input.value = ""
            else:
                # Send message via callback
                self.on_send_message(message)
                event.input.value = ""

    def add_message(self, username: str, content: str, timestamp: str = None, play_sound: bool = True):
        """Add a chat message to the display"""
        message_display = self.query_one("#message-display", RichLog)

        # Format timestamp
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime("%H:%M:%S")
            except Exception:
                time_str = timestamp[:8] if len(timestamp) >= 8 else ""
        else:
            time_str = datetime.now().strftime("%H:%M:%S")

        # Get user color
        user_color = self.get_user_color(username)

        # Use different color for own messages
        if username == self.username:
            new_message = f"[dim]{time_str}[/dim] [bold white]{username}:[/bold white] {content}"
        else:
            new_message = f"[dim]{time_str}[/dim] [bold {user_color}]{username}:[/bold {user_color}] {content}"

        # Write the message to RichLog
        message_display.write(new_message)

        # Play notification sound for messages from other users
        if play_sound and username != self.username:
            self.app.bell()

    def add_system_message(self, message: str):
        """Add a system message (user joined, left, etc.)"""
        message_display = self.query_one("#message-display", RichLog)

        time_str = datetime.now().strftime("%H:%M:%S")
        # Use Rich markup for system messages
        new_message = f"[dim]{time_str}[/dim] [italic yellow]* {message}[/italic yellow]"

        # Write the system message to RichLog
        message_display.write(new_message)

    def update_status(self, status: str):
        """Update the status bar"""
        status_bar = self.query_one("#status-bar", Label)
        status_bar.update(status)

    def update_online_users(self, count: int, usernames: list = None):
        """Update online users count and list"""
        self.online_users_count = count
        self.online_usernames = usernames or []
        online_label = self.query_one("#online-users", Label)

        # Display count and usernames if available
        if usernames:
            # Limit the display to show just a few names, then "..."
            if len(usernames) <= 3:
                names_str = ", ".join(usernames)
                online_label.update(f"Online ({count}): {names_str}")
            else:
                # Show first 3 names and indicate there are more
                names_str = ", ".join(usernames[:3])
                online_label.update(f"Online ({count}): {names_str}...")
        else:
            online_label.update(f"Online: {count}")

    def handle_command(self, command: str):
        """Handle slash commands"""
        parts = command.split()
        cmd = parts[0].lower()

        if cmd == "/help":
            self.show_help()
        elif cmd == "/quit" or cmd == "/exit":
            self.app.exit()
        elif cmd == "/clear":
            self.clear_messages()
        elif cmd == "/who":
            self.show_online_users()
        else:
            self.add_system_message(f"Unknown command: {cmd}. Type /help for available commands.")

    def show_help(self):
        """Show help message with available commands"""
        help_text = [
            "Available Commands:",
            "  /help       - Show this help message",
            "  /who        - Show list of online users",
            "  /quit       - Exit the application",
            "  /clear      - Clear message history",
            "",
            "Keyboard Shortcuts:",
            "  Ctrl+C/Q    - Quit application"
        ]
        for line in help_text:
            self.add_system_message(line)

    def show_online_users(self):
        """Show the list of all online users"""
        if not self.online_usernames:
            self.add_system_message(f"Online users ({self.online_users_count}): No user list available")
        else:
            self.add_system_message(f"Online users ({self.online_users_count}):")
            for username in sorted(self.online_usernames):
                marker = " (you)" if username == self.username else ""
                self.add_system_message(f"  • {username}{marker}")

    def clear_messages(self):
        """Clear the message display"""
        message_display = self.query_one("#message-display", RichLog)
        message_display.clear()
        self.add_system_message("Message history cleared")

    def action_quit(self) -> None:
        """Quit the application"""
        self.app.exit()

    def update_typing_indicator(self, username: str, is_typing: bool):
        """Update typing indicator when users start/stop typing"""
        if is_typing:
            self.typing_users.add(username)
        else:
            self.typing_users.discard(username)

        # Update the typing indicator label
        typing_label = self.query_one("#typing-indicator", Label)

        if not self.typing_users:
            # Hide the typing indicator when no one is typing
            typing_label.update("")
            typing_label.remove_class("visible")
        elif len(self.typing_users) == 1:
            username = list(self.typing_users)[0]
            typing_label.update(f"{username} is typing...")
            typing_label.add_class("visible")
        elif len(self.typing_users) == 2:
            users = sorted(self.typing_users)
            typing_label.update(f"{users[0]} and {users[1]} are typing...")
            typing_label.add_class("visible")
        else:
            typing_label.update(f"{len(self.typing_users)} people are typing...")
            typing_label.add_class("visible")

    def set_typing_indicator_callback(self, callback: Callable):
        """Set callback for sending typing indicator events"""
        self.typing_indicator_callback = callback

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes to send typing indicator"""
        if event.input.id != "message-input":
            return

        # Remove existing timer
        if self.typing_timer:
            try:
                self.remove_timer(self.typing_timer)
            except:
                pass  # Timer may have already expired

        if event.value:
            # Send typing indicator when user starts typing (if not already sent)
            if not self.is_currently_typing and self.typing_indicator_callback:
                self.typing_indicator_callback(True)
                self.is_currently_typing = True

            # Set timer to stop typing indicator after 3 seconds of inactivity
            self.typing_timer = self.set_timer(3.0, self.stop_typing_indicator)
        else:
            # Send stop typing when input is cleared
            if self.is_currently_typing and self.typing_indicator_callback:
                self.typing_indicator_callback(False)
                self.is_currently_typing = False

    def stop_typing_indicator(self) -> None:
        """Stop typing indicator after timeout"""
        if self.is_currently_typing and self.typing_indicator_callback:
            self.typing_indicator_callback(False)
            self.is_currently_typing = False


class ChatApp(App):
    """Main chat application"""

    def __init__(self):
        super().__init__()
        self.username: Optional[str] = None
        self.user_id: Optional[int] = None
        self.token: Optional[str] = None
        self.send_message_callback: Optional[Callable] = None
        self.login_callback: Optional[Callable] = None

    def on_mount(self) -> None:
        """Show login screen on startup"""
        self.push_screen(LoginScreen(self.handle_login))

    def handle_login(self, username: str, password: str, action: str):
        """Handle login/register action"""
        if self.login_callback:
            self.login_callback(username, password, action)

    def show_chat(self, username: str, user_id: int, token: str):
        """Switch to chat screen after successful login"""
        self.username = username
        self.user_id = user_id
        self.token = token

        # Remove login screen and show chat
        self.pop_screen()
        self.push_screen(ChatScreen(username, self.handle_send_message))

    def handle_send_message(self, message: str):
        """Handle message sending"""
        if self.send_message_callback:
            self.send_message_callback(message)

    def set_login_callback(self, callback: Callable):
        """Set callback for login/register"""
        self.login_callback = callback

    def set_send_message_callback(self, callback: Callable):
        """Set callback for sending messages"""
        self.send_message_callback = callback

    def get_chat_screen(self) -> Optional[ChatScreen]:
        """Get the chat screen if it exists"""
        for screen in self.screen_stack:
            if isinstance(screen, ChatScreen):
                return screen
        return None

    def show_login_error(self, message: str):
        """Show error on login screen"""
        for screen in self.screen_stack:
            if isinstance(screen, LoginScreen):
                screen.show_error(message)
                break
