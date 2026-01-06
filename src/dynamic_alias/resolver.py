import subprocess
import json
from typing import Dict, List, Any
from .models import DynamicDictConfig
from .config import ConfigLoader
from .cache import CacheManager

class DataResolver:
    def __init__(self, config: ConfigLoader, cache: CacheManager):
        self.config = config
        self.cache = cache
        self.resolved_data: Dict[str, List[Dict[str, Any]]] = {}

    def resolve_all(self):
        for name, d in self.config.dicts.items():
            self.resolved_data[name] = d.data
        
        for name, dd in self.config.dynamic_dicts.items():
            data = self.cache.get(name)
            if data is None:
                data = self._execute_dynamic_source(dd)
                self.cache.set(name, data)
            self.resolved_data[name] = data

    def _execute_dynamic_source(self, dd: DynamicDictConfig) -> List[Dict[str, Any]]:
        try:
            cmd = dd.command
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=dd.timeout)
            if result.returncode != 0:
                print(f"Error executing dynamic dict '{dd.name}': {result.stderr}")
                return []

            raw_json = json.loads(result.stdout)
            mapped_data = []
            target_list = raw_json
            if isinstance(raw_json, dict):
                 pass # Heuristic handling
            
            if not isinstance(target_list, list):
                target_list = [target_list]

            for item in target_list:
                new_item = {}
                for internal_key, json_key in dd.mapping.items():
                    if json_key in item:
                        new_item[internal_key] = item[json_key]
                if new_item:
                    mapped_data.append(new_item)
            return mapped_data

        except Exception as e:
            print(f"Error in dynamic dict '{dd.name}': {e}")
            return []
