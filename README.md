# Terminal Chat Client

A secure, end-to-end encrypted terminal-based chat application with a beautiful UI.

## Features

- End-to-end encryption (E2EE) using Fernet symmetric encryption
- Real-time messaging via WebSockets
- Beautiful terminal UI powered by Textual
- Auto-reconnection with exponential backoff
- Message history with scroll-back support
- Cross-platform (Windows, macOS, Linux)
- System notifications for new messages

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Quick Install

```bash
pip install terminal-chat-client
```

### Alternative: Install from Wheel File

If you received a `.whl` file:

```bash
pip install terminal_chat_client-1.0.0-py3-none-any.whl
```

### Alternative: Install from GitHub

```bash
pip install git+https://github.com/yourusername/terminal-chat.git
```

## Usage

### Starting the Client

Simply run:

```bash
terminal-chat
```

### First Time Setup

1. When you first launch the client, you'll see a login screen
2. Choose "Register" to create a new account
3. Enter a unique username and password
4. After registration, you'll be automatically logged in

### Chatting

- Type your message in the input field at the bottom
- Press Enter to send
- Messages are automatically encrypted before sending
- You'll see messages from other users in real-time

### Commands

The client supports the following slash commands:

- `/help` - Show available commands
- `/quit` or `/exit` - Exit the application
- `/clear` - Clear the message history from screen
- `/config` - Show current configuration

### Configuration

The client stores configuration in `~/.terminal-chat/config.json`. You can customize:

```json
{
  "server_url": "https://terminal-chat.fuadmuhammed.com",
  "auto_reconnect": true,
  "reconnect_delay": 1,
  "max_reconnect_delay": 60,
  "notification_sound": true,
  "message_history_limit": 50
}
```

You can also override the server URL using environment variable:

```bash
export CHAT_SERVER_URL=https://terminal-chat.fuadmuhammed.com
terminal-chat
```

Or using command-line argument:

```bash
terminal-chat --server https://terminal-chat.fuadmuhammed.com
```

### Encryption Keys

Your encryption key is automatically generated on first run and stored at:

```
~/.terminal-chat/encryption.key
```

**IMPORTANT:** Keep this file safe! If you lose it, you won't be able to decrypt old messages.

## Platform-Specific Notes

### Windows

On Windows, install Python from [python.org](https://www.python.org/downloads/), then:

```cmd
pip install terminal-chat-client
terminal-chat
```

### Linux

Most Linux distributions come with Python pre-installed:

```bash
pip install terminal-chat-client
terminal-chat
```

If `pip` is not found, install it first:

```bash
# Ubuntu/Debian
sudo apt install python3-pip

# Fedora
sudo dnf install python3-pip

# Arch
sudo pacman -S python-pip
```

### macOS

Python 3 should be pre-installed. If not, install via Homebrew:

```bash
brew install python3
pip3 install terminal-chat-client
terminal-chat
```

## Troubleshooting

### Cannot connect to server

Check that:
1. You have internet connectivity
2. The server URL in config is correct
3. Firewall is not blocking the connection

### Command not found: terminal-chat

If you get "command not found" after installation:

```bash
# Add Python scripts to PATH (Linux/Mac)
export PATH="$HOME/.local/bin:$PATH"

# Or use python -m instead
python -m client.main
```

On Windows, make sure Python Scripts folder is in your PATH.

### Python version issues

Check your Python version:

```bash
python --version
# or
python3 --version
```

Make sure it's 3.8 or higher. If you have multiple Python versions, use:

```bash
python3.8 -m pip install terminal-chat-client
python3.8 -m client.main
```

## Uninstallation

```bash
pip uninstall terminal-chat-client
```

To remove all data:

```bash
rm -rf ~/.terminal-chat
```

## Support

For issues or questions:
- Check the main README
- Contact the server administrator
- Report bugs at: https://github.com/yourusername/terminal-chat/issues

## Security

- All messages are encrypted end-to-end
- The server cannot read your messages
- Your password is hashed with bcrypt
- Always use HTTPS/WSS in production

## License

MIT License
