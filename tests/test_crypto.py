"""
Crypto Module Tests

Tests for:
- Rule 1.2.28: Machine ID retrieval and encryption
- Cross-platform machine ID functions
- AES-256-GCM encryption/decryption
"""
import os
import sys
import unittest
import platform
from unittest.mock import patch, MagicMock, mock_open

# Mock prompt_toolkit modules BEFORE any imports
sys.modules['prompt_toolkit'] = MagicMock()
sys.modules['prompt_toolkit.shortcuts'] = MagicMock()
sys.modules['prompt_toolkit.formatted_text'] = MagicMock()
sys.modules['prompt_toolkit.key_binding'] = MagicMock()
sys.modules['prompt_toolkit.history'] = MagicMock()
sys.modules['prompt_toolkit.patch_stdout'] = MagicMock()
sys.modules['prompt_toolkit.completion'] = MagicMock()
sys.modules['prompt_toolkit.styles'] = MagicMock()

# Add src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from dynamic_alias.crypto import (
    get_machine_id, derive_key, encrypt_data, decrypt_data,
    _get_windows_machine_guid, _get_linux_machine_id, _get_macos_machine_id,
    _get_fallback_machine_id
)


class TestMachineId(unittest.TestCase):
    """Test machine ID retrieval."""
    
    def test_get_machine_id_returns_string(self):
        """get_machine_id should return a non-empty string."""
        machine_id = get_machine_id()
        self.assertIsInstance(machine_id, str)
        self.assertTrue(len(machine_id) > 0)
    
    def test_machine_id_is_consistent(self):
        """Multiple calls should return the same machine ID."""
        id1 = get_machine_id()
        id2 = get_machine_id()
        self.assertEqual(id1, id2)
    
    @unittest.skipUnless(platform.system() == "Windows", "Windows only")
    def test_windows_machine_guid_format(self):
        """Windows MachineGuid should have GUID format."""
        guid = _get_windows_machine_guid()
        # GUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        self.assertEqual(len(guid), 36)
        self.assertEqual(guid.count('-'), 4)
    
    @unittest.skipUnless(platform.system() == "Linux", "Linux only")
    def test_linux_machine_id_format(self):
        """Linux machine-id should be a hex string."""
        machine_id = _get_linux_machine_id()
        # machine-id is typically 32 hex characters
        self.assertTrue(len(machine_id) >= 32)
        self.assertTrue(all(c in '0123456789abcdef' for c in machine_id))
    
    @unittest.skipUnless(platform.system() == "Darwin", "macOS only")
    def test_macos_machine_id_format(self):
        """macOS IOPlatformUUID should have UUID format."""
        uuid = _get_macos_machine_id()
        # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        self.assertEqual(len(uuid), 36)
        self.assertEqual(uuid.count('-'), 4)


class TestDeriveKey(unittest.TestCase):
    """Test key derivation."""
    
    def test_derive_key_returns_32_bytes(self):
        """derive_key should return 256-bit (32-byte) key for AES-256."""
        key = derive_key("test-machine-id")
        self.assertEqual(len(key), 32)
        self.assertIsInstance(key, bytes)
    
    def test_derive_key_is_deterministic(self):
        """Same input should produce same key."""
        key1 = derive_key("test-id-123")
        key2 = derive_key("test-id-123")
        self.assertEqual(key1, key2)
    
    def test_derive_key_different_for_different_input(self):
        """Different inputs should produce different keys."""
        key1 = derive_key("machine-id-1")
        key2 = derive_key("machine-id-2")
        self.assertNotEqual(key1, key2)


class TestEncryption(unittest.TestCase):
    """Test AES-256-GCM encryption/decryption."""
    
    def test_encrypt_decrypt_round_trip(self):
        """Encrypt then decrypt should return original data."""
        original = {"key": "value", "number": 42, "nested": {"a": 1}}
        encrypted = encrypt_data(original)
        decrypted = decrypt_data(encrypted)
        self.assertEqual(decrypted, original)
    
    def test_encrypt_with_empty_dict(self):
        """Should handle empty dictionary."""
        original = {}
        encrypted = encrypt_data(original)
        decrypted = decrypt_data(encrypted)
        self.assertEqual(decrypted, original)
    
    def test_encrypt_with_nested_data(self):
        """Should handle deeply nested data."""
        original = {
            "_history": ["cmd1", "cmd2"],
            "_locals": {"var1": "value1"},
            "dynamic_dict": {
                "timestamp": 12345,
                "data": [{"id": 1, "name": "test"}]
            }
        }
        encrypted = encrypt_data(original)
        decrypted = decrypt_data(encrypted)
        self.assertEqual(decrypted, original)
    
    def test_encrypt_with_unicode(self):
        """Should handle unicode characters."""
        original = {"name": "テスト", "emoji": "🚀", "special": "café"}
        encrypted = encrypt_data(original)
        decrypted = decrypt_data(encrypted)
        self.assertEqual(decrypted, original)
    
    def test_encrypted_output_is_base64(self):
        """Encrypted output should be valid base64 string."""
        import base64
        encrypted = encrypt_data({"test": "data"})
        # Should not raise exception
        decoded = base64.b64decode(encrypted)
        # IV (12) + tag (16) + at least some ciphertext
        self.assertGreater(len(decoded), 28)
    
    def test_decrypt_with_corrupted_data_fails(self):
        """Decryption should fail with corrupted data."""
        import base64
        # Create corrupted base64 data
        corrupted = base64.b64encode(b"corrupted-random-data-here").decode()
        with self.assertRaises(ValueError):
            decrypt_data(corrupted)
    
    def test_decrypt_with_tampered_ciphertext_fails(self):
        """Decryption should fail if ciphertext is tampered."""
        import base64
        encrypted = encrypt_data({"secret": "data"})
        # Decode, modify a byte, re-encode
        data = bytearray(base64.b64decode(encrypted))
        data[-1] ^= 0xFF  # Flip bits in last byte
        tampered = base64.b64encode(bytes(data)).decode()
        with self.assertRaises(ValueError):
            decrypt_data(tampered)
    
    def test_each_encryption_produces_different_output(self):
        """Same data encrypted twice should produce different ciphertext (due to random IV)."""
        data = {"test": "value"}
        enc1 = encrypt_data(data)
        enc2 = encrypt_data(data)
        # Ciphertext should differ due to random IV
        self.assertNotEqual(enc1, enc2)
        # But both should decrypt to same value
        self.assertEqual(decrypt_data(enc1), data)
        self.assertEqual(decrypt_data(enc2), data)


class TestMachineIdMocking(unittest.TestCase):
    """Test machine ID with mocked platform functions."""
    
    @patch('dynamic_alias.crypto.platform.system', return_value='Windows')
    @patch('dynamic_alias.crypto._get_windows_machine_guid', return_value='test-guid-123')
    def test_windows_path(self, mock_guid, mock_system):
        """Should use Windows function when on Windows."""
        result = get_machine_id()
        self.assertEqual(result, 'test-guid-123')
    
    @patch('dynamic_alias.crypto.platform.system', return_value='Linux')
    @patch('dynamic_alias.crypto._get_linux_machine_id', return_value='test-linux-id')
    def test_linux_path(self, mock_id, mock_system):
        """Should use Linux function when on Linux."""
        result = get_machine_id()
        self.assertEqual(result, 'test-linux-id')
    
    @patch('dynamic_alias.crypto.platform.system', return_value='Darwin')
    @patch('dynamic_alias.crypto._get_macos_machine_id', return_value='test-macos-uuid')
    def test_macos_path(self, mock_uuid, mock_system):
        """Should use macOS function when on Darwin."""
        result = get_machine_id()
        self.assertEqual(result, 'test-macos-uuid')
    
    @patch('dynamic_alias.crypto.platform.system', return_value='FreeBSD')
    @patch('dynamic_alias.crypto._get_fallback_machine_id', return_value='fallback:test-host:test-user')
    def test_unsupported_platform_uses_fallback(self, mock_fallback, mock_system):
        """Should use fallback on unsupported platform."""
        result = get_machine_id()
        self.assertEqual(result, 'fallback:test-host:test-user')
        mock_fallback.assert_called_once()
    
    @patch('dynamic_alias.crypto.platform.system', return_value='Linux')
    @patch('dynamic_alias.crypto._get_linux_machine_id', side_effect=RuntimeError("No machine-id"))
    @patch('dynamic_alias.crypto._get_fallback_machine_id', return_value='fallback:ci-host:runner')
    def test_platform_failure_uses_fallback(self, mock_fallback, mock_linux, mock_system):
        """Should use fallback when platform-specific method fails."""
        result = get_machine_id()
        self.assertEqual(result, 'fallback:ci-host:runner')
        mock_fallback.assert_called_once()


if __name__ == '__main__':
    unittest.main()
