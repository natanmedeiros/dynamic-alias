import os
import sys
import yaml
import re
from typing import Dict, List, Any
from .models import DictConfig, DynamicDictConfig, CommandConfig, SubCommand, ArgConfig,  GlobalConfig, DEFAULT_TIMEOUT

class ConfigLoader:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.dicts: Dict[str, DictConfig] = {}
        self.dynamic_dicts: Dict[str, DynamicDictConfig] = {}
        self.commands: List[CommandConfig] = []
        self.global_config: GlobalConfig = GlobalConfig()

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

        # Use utf-8-sig to handle BOM if present (e.g. VS Code on Windows)
        with open(self.config_file, 'r', encoding='utf-8-sig') as f:
            content = f.read()
            docs = [doc for doc in content.split('---') if doc.strip()]

        for doc_str in docs:
            try:
                doc = yaml.safe_load(doc_str)
                if not doc:
                    continue
                
                if not isinstance(doc, dict):
                    # Skip documents that aren't dictionaries (e.g. simple strings)
                    continue
                
                # Check for explicit 'type'
                doc_type = doc.get('type')
                
                # Check for 'config' root key (Declarative Metadata style)
                if 'config' in doc:
                    if isinstance(doc['config'], dict):
                        # It's a config block
                        cfg = doc['config']
                        styles = self.global_config.styles.copy()
                        
                        if 'style-completion' in cfg:
                            styles['completion-menu.completion'] = cfg['style-completion']
                        if 'style-completion-current' in cfg:
                             styles['completion-menu.completion.current'] = cfg['style-completion-current']
                        if 'style-scrollbar-background' in cfg:
                             styles['scrollbar.background'] = cfg['style-scrollbar-background']
                        if 'style-scrollbar-button' in cfg:
                             styles['scrollbar.button'] = cfg['style-scrollbar-button']
                        
                        self.global_config.styles = styles
                        
                        if 'style-placeholder-color' in cfg:
                            self.global_config.placeholder_color = cfg['style-placeholder-color']
                        if 'style-placeholder-text' in cfg:
                            self.global_config.placeholder_text = cfg['style-placeholder-text']
                            
                        if 'history-size' in cfg:
                             # Rule 1.2.19: Max 1000
                             val = int(cfg['history-size'])
                             self.global_config.history_size = min(val, 1000)
                    else:
                        pass # Valid key, but not a config dict (ignoring)
                
                # Rule 1.1.10: "inside type config"
                elif doc_type == 'config':
                    styles = self.global_config.styles.copy()
                    
                    if 'style-completion' in doc:
                        styles['completion-menu.completion'] = doc['style-completion']
                    if 'style-completion-current' in doc:
                         styles['completion-menu.completion.current'] = doc['style-completion-current']
                    if 'style-scrollbar-background' in doc:
                         styles['scrollbar.background'] = doc['style-scrollbar-background']
                    if 'style-scrollbar-button' in doc:
                         styles['scrollbar.button'] = doc['style-scrollbar-button']
                    
                    self.global_config.styles = styles
                    
                    if 'style-placeholder-color' in doc:
                        self.global_config.placeholder_color = doc['style-placeholder-color']
                    if 'style-placeholder-text' in doc:
                        self.global_config.placeholder_text = doc['style-placeholder-text']
                        
                    if 'history-size' in doc:
                         # Rule 1.2.19: Max 1000
                         val = int(doc['history-size'])
                         self.global_config.history_size = min(val, 1000)
                        
                elif doc_type == 'dict':
                    name = doc['name']
                    data = self._process_data_structure(doc.get('data', []))
                    self.dicts[name] = DictConfig(name=name, data=data)

                elif doc_type == 'dynamic_dict':
                    self.dynamic_dicts[doc['name']] = DynamicDictConfig(
                        name=doc['name'],
                        command=doc['command'],
                        mapping=doc['mapping'],
                        priority=doc.get('priority', 1),
                        timeout=doc.get('timeout', 10), # Rule 3.9
                        cache_ttl=doc.get('cache-ttl', 300) # Rule 1.2.2
                    )

                elif doc_type == 'command':
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
            timeout=doc.get('timeout', 0), # Rule 4.9
            strict=doc.get('strict', False)
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
