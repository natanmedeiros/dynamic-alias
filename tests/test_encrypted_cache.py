"""
Encrypted Cache Tests

Tests for:
- Rule 1.2.28: Cache with "_crypt" key is encrypted
- Rule 1.2.29: Plain JSON migrates to encrypted on save
- All cache operations (history, locals, dynamic dicts) with encryption
"""
import os
import sys
import unittest
import tempfile
import json
import time
from unittest.mock import patch, MagicMock

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

from dynamic_alias.cache import CacheManager
from dynamic_alias.constants import CACHE_KEY_CRYPT, CACHE_KEY_HISTORY, CACHE_KEY_LOCALS
from dynamic_alias.crypto import encrypt_data, decrypt_data


class TestEncryptedCacheSaveLoad(unittest.TestCase):
    """Test basic save/load with encryption."""
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "cache.json")
        
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def test_save_creates_encrypted_file(self):
        """save() should create file with _crypt key."""
        cache = CacheManager(self.cache_path, enabled=True)
        cache.cache = {"test_key": "test_value"}
        cache.save()
        
        # Read raw file
        with open(self.cache_path, 'r') as f:
            raw = json.load(f)
        
        self.assertIn(CACHE_KEY_CRYPT, raw)
        self.assertEqual(len(raw), 1)  # Only _crypt key
    
    def test_load_decrypts_data(self):
        """load() should decrypt _crypt data correctly."""
        # Create encrypted file manually
        original_data = {"_history": ["cmd1", "cmd2"], "_locals": {"key": "value"}}
        encrypted = encrypt_data(original_data)
        with open(self.cache_path, 'w') as f:
            json.dump({CACHE_KEY_CRYPT: encrypted}, f)
        
        # Load and verify
        cache = CacheManager(self.cache_path, enabled=True)
        cache.load()
        
        self.assertEqual(cache.cache, original_data)
    
    def test_save_load_round_trip(self):
        """Data should survive save/load cycle."""
        cache1 = CacheManager(self.cache_path, enabled=True)
        cache1.cache = {
            "_history": ["cmd1", "cmd2"],
            "_locals": {"var": "value"},
            "dynamic_dict": {"timestamp": 12345, "data": [{"id": 1}]}
        }
        cache1.save()
        
        cache2 = CacheManager(self.cache_path, enabled=True)
        cache2.load()
        
        self.assertEqual(cache2.cache, cache1.cache)


class TestBackwardsCompatibility(unittest.TestCase):
    """Test Rule 1.2.29: Plain JSON migration to encrypted."""
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "cache.json")
        
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def test_load_plain_json(self):
        """load() should read plain JSON for backwards compatibility."""
        plain_data = {"_history": ["old_cmd"], "_locals": {"old_key": "old_value"}}
        with open(self.cache_path, 'w') as f:
            json.dump(plain_data, f)
        
        cache = CacheManager(self.cache_path, enabled=True)
        cache.load()
        
        self.assertEqual(cache.cache, plain_data)
    
    def test_plain_json_marked_for_encryption(self):
        """load() should mark plain JSON for encryption."""
        plain_data = {"_history": ["cmd"]}
        with open(self.cache_path, 'w') as f:
            json.dump(plain_data, f)
        
        cache = CacheManager(self.cache_path, enabled=True)
        cache.load()
        
        self.assertTrue(cache._needs_encryption)
    
    def test_plain_json_encrypted_on_save(self):
        """Plain JSON should be encrypted when saved."""
        plain_data = {"_history": ["cmd1"], "_locals": {"k": "v"}}
        with open(self.cache_path, 'w') as f:
            json.dump(plain_data, f)
        
        # Load (reads plain), then save (encrypts)
        cache = CacheManager(self.cache_path, enabled=True)
        cache.load()
        cache.save()
        
        # Verify file is now encrypted
        with open(self.cache_path, 'r') as f:
            raw = json.load(f)
        
        self.assertIn(CACHE_KEY_CRYPT, raw)
        self.assertNotIn("_history", raw)
        
        # Verify data is still correct
        decrypted = decrypt_data(raw[CACHE_KEY_CRYPT])
        self.assertEqual(decrypted, plain_data)
    
    def test_empty_plain_json_not_marked(self):
        """Empty plain JSON should not be marked for encryption."""
        with open(self.cache_path, 'w') as f:
            json.dump({}, f)
        
        cache = CacheManager(self.cache_path, enabled=True)
        cache.load()
        
        self.assertFalse(cache._needs_encryption)


class TestHistoryWithEncryption(unittest.TestCase):
    """Test history operations with encrypted cache."""
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "cache.json")
        
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def test_history_persists_encrypted(self):
        """History should persist across encrypted save/load."""
        cache1 = CacheManager(self.cache_path, enabled=True)
        cache1.add_history("command1")
        cache1.add_history("command2")
        cache1.save()
        
        cache2 = CacheManager(self.cache_path, enabled=True)
        cache2.load()
        
        self.assertEqual(cache2.get_history(), ["command1", "command2"])
    
    def test_history_limit_with_encryption(self):
        """History limit should work with encrypted cache."""
        cache = CacheManager(self.cache_path, enabled=True)
        for i in range(25):
            cache.add_history(f"cmd{i}", limit=20)
        cache.save()
        
        cache2 = CacheManager(self.cache_path, enabled=True)
        cache2.load()
        
        history = cache2.get_history()
        self.assertEqual(len(history), 20)
        self.assertEqual(history[0], "cmd5")  # First 5 should be dropped
        self.assertEqual(history[-1], "cmd24")
    
    def test_clear_history_with_encryption(self):
        """clear_history should work with encrypted cache."""
        cache = CacheManager(self.cache_path, enabled=True)
        cache.add_history("cmd1")
        cache.save()
        
        cache2 = CacheManager(self.cache_path, enabled=True)
        cache2.load()
        result = cache2.clear_history()
        
        self.assertTrue(result)
        
        # Verify persisted
        cache3 = CacheManager(self.cache_path, enabled=True)
        cache3.load()
        self.assertEqual(cache3.get_history(), [])


class TestLocalsWithEncryption(unittest.TestCase):
    """Test locals operations with encrypted cache."""
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "cache.json")
        
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def test_locals_persist_encrypted(self):
        """Locals should persist across encrypted save/load."""
        cache1 = CacheManager(self.cache_path, enabled=True)
        cache1.set_local("key1", "value1")
        cache1.set_local("key2", "value2")
        
        cache2 = CacheManager(self.cache_path, enabled=True)
        cache2.load()
        
        self.assertEqual(cache2.get_local("key1"), "value1")
        self.assertEqual(cache2.get_local("key2"), "value2")
    
    def test_set_local_with_encryption(self):
        """set_local should save encrypted."""
        cache = CacheManager(self.cache_path, enabled=True)
        cache.set_local("mykey", "myvalue")
        
        # Verify file is encrypted
        with open(self.cache_path, 'r') as f:
            raw = json.load(f)
        
        self.assertIn(CACHE_KEY_CRYPT, raw)
        decrypted = decrypt_data(raw[CACHE_KEY_CRYPT])
        self.assertEqual(decrypted[CACHE_KEY_LOCALS]["mykey"], "myvalue")
    
    def test_clear_locals_with_encryption(self):
        """clear_locals should work with encrypted cache."""
        cache = CacheManager(self.cache_path, enabled=True)
        cache.set_local("key", "value")
        
        cache2 = CacheManager(self.cache_path, enabled=True)
        cache2.load()
        result = cache2.clear_locals()
        
        self.assertTrue(result)
        
        cache3 = CacheManager(self.cache_path, enabled=True)
        cache3.load()
        self.assertEqual(cache3.get_locals(), {})


class TestDynamicDictCacheWithEncryption(unittest.TestCase):
    """Test dynamic dict caching with encryption."""
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "cache.json")
        
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def test_dynamic_dict_cache_encrypted(self):
        """Dynamic dict cache should persist encrypted."""
        cache1 = CacheManager(self.cache_path, enabled=True)
        cache1.set("my_dict", [{"id": 1, "name": "test"}])
        cache1.save()
        
        cache2 = CacheManager(self.cache_path, enabled=True)
        cache2.load()
        
        result = cache2.get("my_dict", ttl=3600)
        self.assertEqual(result, [{"id": 1, "name": "test"}])
    
    def test_cache_ttl_with_encryption(self):
        """TTL expiration should work with encrypted cache."""
        cache = CacheManager(self.cache_path, enabled=True)
        cache.cache = {
            "expired": {"timestamp": int(time.time()) - 1000, "data": []},
            "fresh": {"timestamp": int(time.time()), "data": [{"x": 1}]}
        }
        cache.save()
        
        cache2 = CacheManager(self.cache_path, enabled=True)
        cache2.load()
        
        self.assertIsNone(cache2.get("expired", ttl=300))
        self.assertEqual(cache2.get("fresh", ttl=300), [{"x": 1}])
    
    def test_purge_expired_with_encryption(self):
        """purge_expired should work with encrypted cache."""
        cache = CacheManager(self.cache_path, enabled=True)
        cache.cache = {
            "old_dict": {"timestamp": int(time.time()) - 1000, "data": []},
            "_history": ["cmd"]
        }
        cache.save()
        
        cache2 = CacheManager(self.cache_path, enabled=True)
        cache2.load()
        count = cache2.purge_expired({"old_dict": 300})
        
        self.assertEqual(count, 1)
        
        cache3 = CacheManager(self.cache_path, enabled=True)
        cache3.load()
        self.assertNotIn("old_dict", cache3.cache)
        self.assertIn("_history", cache3.cache)


class TestClearOperationsWithEncryption(unittest.TestCase):
    """Test clear operations with encrypted cache."""
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "cache.json")
        
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def test_clear_cache_with_encryption(self):
        """clear_cache should preserve underscore keys in encrypted cache."""
        cache = CacheManager(self.cache_path, enabled=True)
        cache.cache = {
            "dynamic_dict": {"timestamp": 123, "data": []},
            "_history": ["cmd"],
            "_locals": {"k": "v"}
        }
        cache.save()
        
        cache2 = CacheManager(self.cache_path, enabled=True)
        cache2.load()
        count = cache2.clear_cache()
        
        self.assertEqual(count, 1)
        
        cache3 = CacheManager(self.cache_path, enabled=True)
        cache3.load()
        self.assertNotIn("dynamic_dict", cache3.cache)
        self.assertIn("_history", cache3.cache)
        self.assertIn("_locals", cache3.cache)
    
    def test_clear_all_removes_encrypted_file(self):
        """delete_all should remove encrypted cache file."""
        cache = CacheManager(self.cache_path, enabled=True)
        cache.set_local("key", "value")
        
        self.assertTrue(os.path.exists(self.cache_path))
        
        cache2 = CacheManager(self.cache_path, enabled=True)
        cache2.load()
        result = cache2.delete_all()
        
        self.assertTrue(result)
        self.assertFalse(os.path.exists(self.cache_path))


class TestDirectoryCreation(unittest.TestCase):
    """Test that save() creates directory if needed."""
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def test_save_creates_parent_directory(self):
        """save() should create parent directory if it doesn't exist."""
        nested_path = os.path.join(self.temp_dir.name, "subdir", "cache.json")
        
        cache = CacheManager(nested_path, enabled=True)
        cache.set_local("key", "value")
        
        self.assertTrue(os.path.exists(nested_path))
        self.assertTrue(os.path.isdir(os.path.dirname(nested_path)))


class TestDecryptionFailure(unittest.TestCase):
    """Test handling of decryption failures."""
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "cache.json")
        
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def test_corrupted_encrypted_cache_handled(self):
        """Corrupted encrypted cache should result in empty cache."""
        # Write invalid encrypted data
        with open(self.cache_path, 'w') as f:
            json.dump({CACHE_KEY_CRYPT: "invalid-base64-data"}, f)
        
        cache = CacheManager(self.cache_path, enabled=True)
        cache.load()  # Should not raise, just warn and set empty cache
        
        self.assertEqual(cache.cache, {})


if __name__ == '__main__':
    unittest.main()
