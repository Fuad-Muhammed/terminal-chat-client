"""
Encryption utilities for end-to-end encrypted messaging
"""

from cryptography.fernet import Fernet
import os
from pathlib import Path
from typing import Optional


class MessageEncryption:
    """Handles message encryption and decryption using Fernet symmetric encryption"""

    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize encryption with a key.
        If no key is provided, generates a new one.
        """
        if key:
            self.key = key
        else:
            self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt(self, message: str) -> str:
        """Encrypt a message"""
        encrypted = self.cipher.encrypt(message.encode())
        return encrypted.decode()

    def decrypt(self, encrypted_message: str) -> str:
        """Decrypt a message"""
        decrypted = self.cipher.decrypt(encrypted_message.encode())
        return decrypted.decode()

    def get_key(self) -> bytes:
        """Get the encryption key"""
        return self.key

    @staticmethod
    def save_key(key: bytes, filepath: str = None):
        """Save encryption key to a file"""
        if filepath is None:
            # Default location: ~/.terminal-chat/keys
            config_dir = Path.home() / ".terminal-chat"
            config_dir.mkdir(exist_ok=True)
            filepath = config_dir / "encryption.key"

        with open(filepath, "wb") as key_file:
            key_file.write(key)

    @staticmethod
    def load_key(filepath: str = None) -> bytes:
        """Load encryption key from a file"""
        if filepath is None:
            # Default location: ~/.terminal-chat/keys
            filepath = Path.home() / ".terminal-chat" / "encryption.key"

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Encryption key not found at {filepath}")

        with open(filepath, "rb") as key_file:
            return key_file.read()

    @staticmethod
    def generate_and_save_key(filepath: str = None) -> bytes:
        """Generate a new key and save it"""
        key = Fernet.generate_key()
        MessageEncryption.save_key(key, filepath)
        return key


def get_or_create_encryption() -> MessageEncryption:
    """
    Get encryption instance with existing key or create new one.
    This is the recommended way to initialize encryption for clients.
    """
    try:
        key = MessageEncryption.load_key()
        return MessageEncryption(key)
    except FileNotFoundError:
        # Generate new key on first run
        key = MessageEncryption.generate_and_save_key()
        return MessageEncryption(key)
