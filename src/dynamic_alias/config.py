import os
import sys
import yaml
import re
from typing import Dict, List, Any
from .models import DictConfig, DynamicDictConfig, CommandConfig, SubCommand, ArgConfig, DEFAULT_TIMEOUT

class ConfigLoader:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.dicts: Dict[str, DictConfig] = {}
        self.dynamic_dicts: Dict[str, DynamicDictConfig] = {}
        self.commands: List[CommandConfig] = []

    def _substitute_env_vars(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        pattern = r'\$\$\{env\.(\w+)\}'
        def replace(match):
            var_name = match.group(1)
            return os.environ.get(var_name, '')
        return re.sub(pattern, replace, text)

    def _process_data_structure(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        processed = []
        for item in data:
            new_item = {}
            for k, v in item.items():
                if isinstance(v, str):
                    new_item[k] = self._substitute_env_vars(v)
                else:
                    new_item[k] = v
            processed.append(new_item)
        return processed

    def load(self):
        if not os.path.exists(self.config_file):
            print(f"Error: Config file not found at {self.config_file}")
            sys.exit(1)

        with open(self.config_file, 'r') as f:
            content = f.read()
            docs = [doc for doc in content.split('---') if doc.strip()]

        for doc_str in docs:
            try:
                doc = yaml.safe_load(doc_str)
                if not doc or 'type' not in doc:
                    continue

                if doc['type'] == 'dict':
                    name = doc['name']
                    data = self._process_data_structure(doc.get('data', []))
                    self.dicts[name] = DictConfig(name=name, data=data)

                elif doc['type'] == 'dynamic_dict':
                    self.dynamic_dicts[doc['name']] = DynamicDictConfig(
                        name=doc['name'],
                        command=doc['command'],
                        mapping=doc['mapping'],
                        priority=doc.get('priority', 1),
                        timeout=doc.get('timeout', DEFAULT_TIMEOUT)
                    )

                elif doc['type'] == 'command':
                    self.commands.append(self._parse_command(doc))

            except yaml.YAMLError as e:
                print(f"Error parsing YAML: {e}")

        self.dynamic_dicts = dict(sorted(self.dynamic_dicts.items(), key=lambda x: x[1].priority))

    def _parse_command(self, doc: Dict) -> CommandConfig:
        subs = []
        if 'sub' in doc:
            subs = [self._parse_subcommand(s) for s in doc['sub']]
        
        return CommandConfig(
            name=doc['name'],
            alias=doc['alias'],
            command=doc['command'],
            helper=doc.get('helper'),
            sub=subs,
            args=[self._parse_arg(a) for a in doc.get('args', [])],
            timeout=doc.get('timeout', DEFAULT_TIMEOUT)
        )

    def _parse_subcommand(self, doc: Dict) -> SubCommand:
        subs = []
        if 'sub' in doc:
            subs = [self._parse_subcommand(s) for s in doc['sub']]
        
        return SubCommand(
            alias=doc['alias'],
            command=doc['command'],
            helper=doc.get('helper'),
            sub=subs,
            args=[self._parse_arg(a) for a in doc.get('args', [])]
        )
    
    def _parse_arg(self, doc: Dict) -> ArgConfig:
        return ArgConfig(
            alias=doc['alias'],
            command=doc['command'],
            helper=doc.get('helper')
        )
