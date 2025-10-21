"""
Client configuration management
"""

import os
import json
from pathlib import Path
from typing import Dict, Any


class ClientConfig:
    """Manages client configuration"""

    DEFAULT_CONFIG = {
        "server_url": "https://terminal-chat.fuadmuhammed.com",
        "auto_reconnect": True,
        "reconnect_delay": 1,
        "max_reconnect_delay": 60,
        "notification_sound": True,
        "message_history_limit": 50,
    }

    def __init__(self):
        self.config_dir = Path.home() / ".terminal-chat"
        self.config_file = self.config_dir / "config.json"
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load existing config or create default
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults (in case new settings were added)
                    return {**self.DEFAULT_CONFIG, **config}
            except Exception as e:
                print(f"Warning: Failed to load config file: {e}")
                return self.DEFAULT_CONFIG.copy()
        else:
            # Create default config file
            self.save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()

    def save_config(self, config: Dict[str, Any] = None):
        """Save configuration to file"""
        if config is None:
            config = self.config

        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save config file: {e}")

    def get(self, key: str, default=None):
        """Get a configuration value"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Set a configuration value and save"""
        self.config[key] = value
        self.save_config()

    @property
    def server_url(self) -> str:
        """Get server URL from config or environment variable"""
        # Environment variable takes precedence
        return os.getenv("CHAT_SERVER_URL", self.config.get("server_url")).rstrip('/')

    @property
    def ws_url(self) -> str:
        """Get WebSocket URL"""
        url = self.server_url
        return url.replace('http://', 'ws://').replace('https://', 'wss://')


# Global config instance
_config = None


def get_config() -> ClientConfig:
    """Get the global config instance"""
    global _config
    if _config is None:
        _config = ClientConfig()
    return _config
