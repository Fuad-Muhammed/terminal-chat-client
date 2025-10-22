"""
Unit tests for client configuration management
"""

import pytest
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from client.config import ClientConfig, get_config


class TestClientConfig:
    """Tests for ClientConfig class"""

    def test_default_config_values(self, temp_config_dir):
        """Test that default configuration values are set correctly"""
        with patch.object(Path, 'home', return_value=Path(temp_config_dir)):
            config = ClientConfig()

            assert config.get("auto_reconnect") is True
            assert config.get("reconnect_delay") == 1
            assert config.get("max_reconnect_delay") == 60
            assert config.get("notification_sound") is True
            assert config.get("message_history_limit") == 50

    def test_config_file_creation(self, temp_config_dir):
        """Test that config file is created on first run"""
        with patch.object(Path, 'home', return_value=Path(temp_config_dir)):
            config = ClientConfig()

            assert config.config_file.exists()
            assert config.config_dir.exists()

    def test_load_existing_config(self, temp_config_dir):
        """Test loading existing configuration file"""
        with patch.object(Path, 'home', return_value=Path(temp_config_dir)):
            # Create config file manually
            config_dir = Path(temp_config_dir) / ".terminal-chat"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.json"

            custom_config = {
                "server_url": "http://custom-server.com",
                "auto_reconnect": False,
                "message_history_limit": 100
            }

            with open(config_file, 'w') as f:
                json.dump(custom_config, f)

            # Load config
            config = ClientConfig()

            assert config.get("server_url") == "http://custom-server.com"
            assert config.get("auto_reconnect") is False
            assert config.get("message_history_limit") == 100

    def test_config_merge_with_defaults(self, temp_config_dir):
        """Test that loaded config merges with defaults"""
        with patch.object(Path, 'home', return_value=Path(temp_config_dir)):
            # Create partial config file
            config_dir = Path(temp_config_dir) / ".terminal-chat"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.json"

            partial_config = {
                "server_url": "http://custom-server.com"
            }

            with open(config_file, 'w') as f:
                json.dump(partial_config, f)

            config = ClientConfig()

            # Custom value should be used
            assert config.get("server_url") == "http://custom-server.com"
            # Default values should still be available
            assert config.get("auto_reconnect") is True
            assert config.get("notification_sound") is True

    def test_get_config_value(self, temp_config_dir):
        """Test getting configuration values"""
        with patch.object(Path, 'home', return_value=Path(temp_config_dir)):
            config = ClientConfig()

            value = config.get("auto_reconnect")
            assert value is True

    def test_get_config_value_with_default(self, temp_config_dir):
        """Test getting non-existent config value with default"""
        with patch.object(Path, 'home', return_value=Path(temp_config_dir)):
            config = ClientConfig()

            value = config.get("nonexistent_key", "default_value")
            assert value == "default_value"

    def test_set_config_value(self, temp_config_dir):
        """Test setting configuration values"""
        with patch.object(Path, 'home', return_value=Path(temp_config_dir)):
            config = ClientConfig()

            config.set("custom_setting", "custom_value")

            assert config.get("custom_setting") == "custom_value"

            # Should be persisted
            config2 = ClientConfig()
            assert config2.get("custom_setting") == "custom_value"

    def test_server_url_property(self, temp_config_dir):
        """Test server_url property"""
        with patch.object(Path, 'home', return_value=Path(temp_config_dir)):
            config = ClientConfig()

            # Should return server URL from config
            server_url = config.server_url
            assert isinstance(server_url, str)
            assert len(server_url) > 0

    def test_server_url_env_override(self, temp_config_dir):
        """Test that environment variable overrides config file"""
        with patch.object(Path, 'home', return_value=Path(temp_config_dir)):
            os.environ["CHAT_SERVER_URL"] = "http://env-server.com"

            config = ClientConfig()
            assert config.server_url == "http://env-server.com"

            # Cleanup
            del os.environ["CHAT_SERVER_URL"]

    def test_server_url_trailing_slash_removed(self, temp_config_dir):
        """Test that trailing slash is removed from server URL"""
        with patch.object(Path, 'home', return_value=Path(temp_config_dir)):
            os.environ["CHAT_SERVER_URL"] = "http://server.com/"

            config = ClientConfig()
            assert config.server_url == "http://server.com"

            del os.environ["CHAT_SERVER_URL"]

    def test_ws_url_property(self, temp_config_dir):
        """Test WebSocket URL conversion"""
        with patch.object(Path, 'home', return_value=Path(temp_config_dir)):
            config_dir = Path(temp_config_dir) / ".terminal-chat"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.json"

            test_config = {"server_url": "http://localhost:8000"}
            with open(config_file, 'w') as f:
                json.dump(test_config, f)

            config = ClientConfig()
            assert config.ws_url == "ws://localhost:8000"

    def test_ws_url_https_to_wss(self, temp_config_dir):
        """Test that HTTPS converts to WSS"""
        with patch.object(Path, 'home', return_value=Path(temp_config_dir)):
            config_dir = Path(temp_config_dir) / ".terminal-chat"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.json"

            test_config = {"server_url": "https://secure-server.com"}
            with open(config_file, 'w') as f:
                json.dump(test_config, f)

            # Remove the environment variable that overrides config
            with patch.dict(os.environ, {}, clear=False):
                if "CHAT_SERVER_URL" in os.environ:
                    del os.environ["CHAT_SERVER_URL"]
                config = ClientConfig()
                assert config.ws_url == "wss://secure-server.com"

    def test_save_config(self, temp_config_dir):
        """Test saving configuration to file"""
        with patch.object(Path, 'home', return_value=Path(temp_config_dir)):
            config = ClientConfig()

            config.set("new_setting", "new_value")

            # Read file directly
            with open(config.config_file, 'r') as f:
                file_content = json.load(f)

            assert file_content["new_setting"] == "new_value"

    def test_load_config_invalid_json(self, temp_config_dir):
        """Test loading config with invalid JSON"""
        with patch.object(Path, 'home', return_value=Path(temp_config_dir)):
            # Create invalid JSON file
            config_dir = Path(temp_config_dir) / ".terminal-chat"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.json"

            with open(config_file, 'w') as f:
                f.write("invalid json {{{")

            # Should fall back to defaults
            config = ClientConfig()
            assert config.get("auto_reconnect") is True


class TestGetConfigFunction:
    """Tests for get_config() global function"""

    def test_get_config_singleton(self, temp_config_dir):
        """Test that get_config returns singleton instance"""
        with patch.object(Path, 'home', return_value=Path(temp_config_dir)):
            # Reset global instance
            import client.config
            client.config._config = None

            config1 = get_config()
            config2 = get_config()

            assert config1 is config2
