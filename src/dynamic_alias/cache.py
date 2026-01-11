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

    def get(self, key: str, ttl: int = 300) -> Optional[List[Dict[str, Any]]]:
        if not self.enabled:
            return None
        
        entry = self.cache.get(key)
        if not entry or not isinstance(entry, dict):
            # Backward compatibility or empty
            return None
            
        timestamp = entry.get('timestamp', 0)
        data = entry.get('data')
        
        if data is None:
            return None
            
        import time
        current_time = int(time.time())
        if current_time - timestamp > ttl:
            return None # Expired
            
        return data

    def set(self, key: str, value: List[Dict[str, Any]]):
        if self.enabled:
            import time
            self.cache[key] = {
                'timestamp': int(time.time()),
                'data': value
            }

    def add_history(self, command: str, limit: int = 20):
        if not self.enabled:
            return

        if '_history' not in self.cache:
            self.cache['_history'] = []
            
        history = self.cache['_history']
        
        # Rule 1.2.20: Append and shift
        # Only add if distinct from last command ?? Rules don't specify uniqueness, but standard shell usually does.
        # Rules say: "appended and shifted only if exceeds history-size"
        
        history.append(command)
        
        if len(history) > limit:
            history[:] = history[-limit:]
            
        self.cache['_history'] = history
        
    def get_history(self) -> List[str]:
        if not self.enabled:
            return []
        return self.cache.get('_history', [])
