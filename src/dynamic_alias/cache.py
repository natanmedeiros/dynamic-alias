import os
import json
from typing import Dict, List, Any, Optional

class CacheManager:
    def __init__(self, cache_file: str, enabled: bool):
        self.cache_file = cache_file
        self.enabled = enabled
        self.cache: Dict[str, List[Dict[str, Any]]] = {}

    def load(self):
        if not self.enabled:
            return
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load cache: {e}")

    def save(self):
        if not self.enabled:
            return
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")

    def get(self, key: str) -> Optional[List[Dict[str, Any]]]:
        if not self.enabled:
            return None
        return self.cache.get(key)

    def set(self, key: str, value: List[Dict[str, Any]]):
        if self.enabled:
            self.cache[key] = value
