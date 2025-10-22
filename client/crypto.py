"""
Encryption utilities for end-to-end encrypted messaging with RSA key exchange
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
import os
from pathlib import Path
from typing import Optional
import base64


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

    def update_key(self, new_key: bytes):
        """Update the encryption key (for key rotation)"""
        self.key = new_key
        self.cipher = Fernet(new_key)

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


class RSAKeyManager:
    """Manages RSA key pairs for public key encryption"""

    @staticmethod
    def generate_key_pair() -> tuple[bytes, bytes]:
        """
        Generate RSA key pair (2048-bit)

        Returns:
            tuple: (private_key_pem, public_key_pem)
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Serialize public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return private_pem, public_pem

    @staticmethod
    def decrypt_with_private_key(private_key_pem: bytes, encrypted_data: bytes) -> bytes:
        """
        Decrypt data with RSA private key

        Args:
            private_key_pem: Private key in PEM format
            encrypted_data: Encrypted data

        Returns:
            Decrypted data
        """
        private_key = serialization.load_pem_private_key(
            private_key_pem,
            password=None,
            backend=default_backend()
        )

        decrypted = private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        return decrypted

    @staticmethod
    def save_private_key(private_key_pem: bytes, filepath: str = None):
        """
        Save RSA private key to a file

        Args:
            private_key_pem: Private key in PEM format
            filepath: Optional custom filepath
        """
        if filepath is None:
            config_dir = Path.home() / ".terminal-chat"
            config_dir.mkdir(exist_ok=True, mode=0o700)
            filepath = config_dir / "private.key"

        # Write with restrictive permissions
        with open(filepath, "wb") as key_file:
            key_file.write(private_key_pem)

        # Set file permissions to 600 (read/write for owner only)
        os.chmod(filepath, 0o600)

    @staticmethod
    def load_private_key(filepath: str = None) -> bytes:
        """
        Load RSA private key from a file

        Args:
            filepath: Optional custom filepath

        Returns:
            Private key in PEM format
        """
        if filepath is None:
            filepath = Path.home() / ".terminal-chat" / "private.key"

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Private key not found at {filepath}")

        with open(filepath, "rb") as key_file:
            return key_file.read()

    @staticmethod
    def get_or_create_key_pair() -> tuple[bytes, bytes]:
        """
        Get existing key pair or generate new one

        Returns:
            tuple: (private_key_pem, public_key_pem)
        """
        try:
            private_key_pem = RSAKeyManager.load_private_key()

            # Load private key and extract public key
            private_key = serialization.load_pem_private_key(
                private_key_pem,
                password=None,
                backend=default_backend()
            )

            public_key = private_key.public_key()
            public_key_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            return private_key_pem, public_key_pem

        except FileNotFoundError:
            # Generate new key pair
            private_key_pem, public_key_pem = RSAKeyManager.generate_key_pair()
            RSAKeyManager.save_private_key(private_key_pem)
            return private_key_pem, public_key_pem


class ClientEncryption:
    """
    Client-side encryption manager handling both RSA and session keys

    This class manages:
    - RSA key pair for receiving encrypted session keys
    - Session key for encrypting/decrypting messages
    """

    def __init__(self):
        """Initialize client encryption"""
        # Get or create RSA key pair
        self.private_key, self.public_key = RSAKeyManager.get_or_create_key_pair()

        # Session key will be set after key exchange
        self.session_key: Optional[bytes] = None
        self.encryption: Optional[MessageEncryption] = None

    def get_public_key(self) -> bytes:
        """Get client's RSA public key"""
        return self.public_key

    def get_public_key_b64(self) -> str:
        """Get client's RSA public key as base64 string for transmission"""
        return base64.b64encode(self.public_key).decode('utf-8')

    def set_session_key_encrypted(self, encrypted_session_key: bytes):
        """
        Decrypt and set session key from server

        Args:
            encrypted_session_key: Session key encrypted with client's public key
        """
        # Decrypt session key with private key
        self.session_key = RSAKeyManager.decrypt_with_private_key(
            self.private_key,
            encrypted_session_key
        )

        # Initialize message encryption with session key
        self.encryption = MessageEncryption(self.session_key)

    def encrypt_message(self, message: str) -> str:
        """
        Encrypt a message with session key

        Args:
            message: Plaintext message

        Returns:
            Encrypted message

        Raises:
            RuntimeError: If session key not set
        """
        if self.encryption is None:
            raise RuntimeError("Session key not set. Complete key exchange first.")

        return self.encryption.encrypt(message)

    def decrypt_message(self, encrypted_message: str) -> str:
        """
        Decrypt a message with session key

        Args:
            encrypted_message: Encrypted message

        Returns:
            Decrypted plaintext message

        Raises:
            RuntimeError: If session key not set
        """
        if self.encryption is None:
            raise RuntimeError("Session key not set. Complete key exchange first.")

        return self.encryption.decrypt(encrypted_message)

    def has_session_key(self) -> bool:
        """Check if session key has been set"""
        return self.encryption is not None


def get_or_create_encryption() -> MessageEncryption:
    """
    Get encryption instance with existing key or create new one.
    This is the legacy method for backward compatibility.

    NOTE: New clients should use ClientEncryption class instead.
    """
    try:
        key = MessageEncryption.load_key()
        return MessageEncryption(key)
    except FileNotFoundError:
        # Generate new key on first run
        key = MessageEncryption.generate_and_save_key()
        return MessageEncryption(key)
