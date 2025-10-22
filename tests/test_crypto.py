"""
Unit tests for client-side encryption (same as server, but testing client implementation)
"""

import pytest
import os
from cryptography.fernet import InvalidToken

from client.crypto import MessageEncryption


class TestClientEncryption:
    """Tests for client-side message encryption"""

    def test_encrypt_decrypt_roundtrip(self, encryption_key):
        """Test encryption and decryption roundtrip"""
        plaintext = "Secret client message"
        encrypted = encryption_key.encrypt(plaintext)
        decrypted = encryption_key.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_produces_different_output(self, encryption_key):
        """Test that same message encrypts differently each time"""
        plaintext = "Same message"
        encrypted1 = encryption_key.encrypt(plaintext)
        encrypted2 = encryption_key.encrypt(plaintext)

        assert encrypted1 != encrypted2

    def test_decrypt_invalid_data(self, encryption_key):
        """Test decrypting invalid data raises error"""
        with pytest.raises(InvalidToken):
            encryption_key.decrypt("invalid_encrypted_data")

    def test_encrypt_unicode(self, encryption_key):
        """Test encrypting Unicode characters"""
        plaintext = "🎉 Unicode test 世界 مرحبا"
        encrypted = encryption_key.encrypt(plaintext)
        decrypted = encryption_key.decrypt(encrypted)

        assert decrypted == plaintext

    def test_key_persistence_across_instances(self, temp_config_dir):
        """Test that encryption key persists across instances"""
        key_path = os.path.join(temp_config_dir, "persistent.key")

        # First instance - generate and save key
        key = MessageEncryption.generate_and_save_key(key_path)
        enc1 = MessageEncryption(key=key)
        plaintext = "Test message"
        encrypted = enc1.encrypt(plaintext)

        # Second instance with same key loaded from file
        loaded_key = MessageEncryption.load_key(key_path)
        enc2 = MessageEncryption(key=loaded_key)
        decrypted = enc2.decrypt(encrypted)

        assert decrypted == plaintext

    def test_different_keys_cannot_decrypt(self, temp_config_dir):
        """Test that different keys cannot decrypt each other's messages"""
        key_path1 = os.path.join(temp_config_dir, "key1.key")
        key_path2 = os.path.join(temp_config_dir, "key2.key")

        # Generate two different keys
        key1 = MessageEncryption.generate_and_save_key(key_path1)
        key2 = MessageEncryption.generate_and_save_key(key_path2)

        enc1 = MessageEncryption(key=key1)
        enc2 = MessageEncryption(key=key2)

        plaintext = "Secret"
        encrypted = enc1.encrypt(plaintext)

        with pytest.raises(InvalidToken):
            enc2.decrypt(encrypted)

    def test_get_key_format(self, encryption_key):
        """Test that encryption key has correct format"""
        key = encryption_key.get_key()

        assert isinstance(key, bytes)
        assert len(key) == 44  # Fernet key base64 encoded
