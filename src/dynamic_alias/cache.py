"""
Cache Manager Module

Manages cache persistence for dynamic dicts, history, and locals.
Includes encryption support using machine-specific identifiers.

Rules:
    1.2.28: If cache contains "_crypt", data was encrypted with machine GUID/ID
    1.2.29: If "_crypt" does not exist and data exists, encrypt on save
"""
import os
import json
import time
from typing import Dict, List, Any, Optional

from .constants import (
    CACHE_KEY_HISTORY, CACHE_KEY_LOCALS, 
    CACHE_KEY_TIMESTAMP, CACHE_KEY_DATA, CACHE_KEY_CRYPT
)


class CacheManager:
    """Manages cache persistence for dynamic dicts, history, and locals."""
    
    def __init__(self, cache_file: str, enabled: bool):
        self.cache_file = cache_file
        self.enabled = enabled
        self.cache: Dict[str, Any] = {}
        self._needs_encryption = False  # Rule 1.2.29: Track if migration needed

    def load(self) -> None:
        """
        Load cache from disk.
        
        Rule 1.2.28: If "_crypt" key exists, decrypt the data.
        Rule 1.2.29: If plain data exists, mark for encryption on save.
        """
        if not self.enabled:
            return
        if not os.path.exists(self.cache_file):
            return
            
        try:
            with open(self.cache_file, 'r') as f:
                raw = json.load(f)
            
            # Rule 1.2.28: Check for encrypted data
            if CACHE_KEY_CRYPT in raw:
                from .crypto import decrypt_data
                try:
                    self.cache = decrypt_data(raw[CACHE_KEY_CRYPT])
                except ValueError as e:
                    print(f"Warning: Failed to decrypt cache: {e}")
                    print("  Cache may have been created on a different machine.")
                    self.cache = {}
            else:
                # Rule 1.2.29: Plain data exists, load it and mark for encryption
                self.cache = raw
                if raw:  # Only mark if there's actual data
                    self._needs_encryption = True
                    
        except Exception as e:
            print(f"Warning: Failed to load cache: {e}")

    def save(self) -> None:
        """
        Save cache to disk with encryption.
        
        Rule 1.2.28/1.2.29: Always save encrypted with "_crypt" key.
        """
        if not self.enabled:
            return
        try:
            # Ensure directory exists
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir:
                os.makedirs(cache_dir, exist_ok=True)
            
            # Always encrypt on save
            from .crypto import encrypt_data
            encrypted = encrypt_data(self.cache)
            
            with open(self.cache_file, 'w') as f:
                json.dump({CACHE_KEY_CRYPT: encrypted}, f)
            
            # Reset migration flag after successful save
            self._needs_encryption = False
            
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")

    def get(self, key: str, ttl: int = 300) -> Optional[List[Dict[str, Any]]]:
        """Get cached data if not expired."""
        if not self.enabled:
            return None
        
        entry = self.cache.get(key)
        if not entry or not isinstance(entry, dict):
            return None
            
        timestamp = entry.get(CACHE_KEY_TIMESTAMP, 0)
        data = entry.get(CACHE_KEY_DATA)
        
        if data is None:
            return None
            
        current_time = int(time.time())
        if current_time - timestamp > ttl:
            return None  # Expired
            
        return data

    def set(self, key: str, value: List[Dict[str, Any]]) -> None:
        """Set cache entry with timestamp."""
        if self.enabled:
            self.cache[key] = {
                CACHE_KEY_TIMESTAMP: int(time.time()),
                CACHE_KEY_DATA: value
            }

    def add_history(self, command: str, limit: int = 20) -> None:
        """Add command to history with limit enforcement."""
        if not self.enabled:
            return

        if CACHE_KEY_HISTORY not in self.cache:
            self.cache[CACHE_KEY_HISTORY] = []
            
        history = self.cache[CACHE_KEY_HISTORY]
        
        # Rule 1.2.20: Append and shift
        history.append(command)
        
        if len(history) > limit:
            history[:] = history[-limit:]
            
        self.cache[CACHE_KEY_HISTORY] = history
        
    def get_history(self) -> List[str]:
        """Get command history."""
        if not self.enabled:
            return []
        return self.cache.get(CACHE_KEY_HISTORY, [])
    
    def clear_cache(self) -> int:
        """
        Rule 1.2.21: Purge cache entries that do not start with underscore "_".
        Returns number of entries purged.
        """
        if not self.enabled:
            return 0
        
        keys_to_remove = [k for k in self.cache.keys() if not k.startswith('_')]
        count = len(keys_to_remove)
        
        for key in keys_to_remove:
            del self.cache[key]
        
        self.save()
        return count
    
    def clear_history(self) -> bool:
        """
        Rule 1.2.23: Purge cache _history entry.
        Returns True if history was removed.
        """
        if not self.enabled:
            return False
        
        if CACHE_KEY_HISTORY in self.cache:
            del self.cache[CACHE_KEY_HISTORY]
            self.save()
            return True
        return False
    
    def delete_all(self) -> bool:
        """
        Rule 1.2.24: Delete the entire cache file.
        Returns True if file was deleted.
        """
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
            self.cache = {}
            return True
        return False
    
    def purge_expired(self, ttl_map: Dict[str, int] = None) -> int:
        """
        Rule 1.2.22: Purge expired cache entries.
        ttl_map is a dict mapping cache key names to their TTL.
        Returns number of entries purged.
        """
        if not self.enabled or ttl_map is None:
            return 0
        
        current_time = int(time.time())
        keys_to_remove = []
        
        for key, entry in self.cache.items():
            if key.startswith('_'):
                continue  # Skip internal entries like _history
            
            if not isinstance(entry, dict):
                continue
            
            timestamp = entry.get(CACHE_KEY_TIMESTAMP, 0)
            ttl = ttl_map.get(key, 300)  # Default 5 min TTL
            
            if current_time - timestamp > ttl:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
        
        if keys_to_remove:
            self.save()
        
        return len(keys_to_remove)
    
    # =========================================================================
    # Locals Management (Rules 1.2.25, 1.2.26, 1.2.27)
    # =========================================================================
    
    def set_local(self, key: str, value: str) -> None:
        """
        Rule 1.2.26: Set or replace a local variable.
        Locals are stored in _locals key as key/value pairs.
        """
        if not self.enabled:
            return
        
        if CACHE_KEY_LOCALS not in self.cache:
            self.cache[CACHE_KEY_LOCALS] = {}
        
        self.cache[CACHE_KEY_LOCALS][key] = value
        self.save()
    
    def get_local(self, key: str) -> Optional[str]:
        """
        Rule 1.2.25: Get a local variable value.
        Returns None if not found.
        """
        if not self.enabled:
            return None
        
        locals_dict = self.cache.get(CACHE_KEY_LOCALS, {})
        return locals_dict.get(key)
    
    def get_locals(self) -> Dict[str, str]:
        """Rule 1.2.25: Get all local variables."""
        if not self.enabled:
            return {}
        return self.cache.get(CACHE_KEY_LOCALS, {})
    
    def clear_locals(self) -> bool:
        """
        Rule 1.2.27: Purge all local variables.
        Returns True if locals were removed.
        """
        if not self.enabled:
            return False
        
        if CACHE_KEY_LOCALS in self.cache:
            del self.cache[CACHE_KEY_LOCALS]
            self.save()
            return True
        return False
