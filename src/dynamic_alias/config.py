import os
import sys
import yaml
import re
from typing import Dict, List, Any, Optional, Callable
from abc import ABC, abstractmethod
from .models import DictConfig, DynamicDictConfig, CommandConfig, SubCommand, ArgConfig, GlobalConfig


# =============================================================================
# Factory Pattern: Block Parsers
# =============================================================================

class BlockParser(ABC):
    """Abstract factory for parsing block types."""
    
    @abstractmethod
    def parse(self, doc: Dict[str, Any], loader: 'ConfigLoader') -> None:
        """Parse a block and add it to the loader's data structures."""
        pass


class ConfigBlockParser(BlockParser):
    """Factory for parsing config blocks."""
    
    def parse(self, doc: Dict[str, Any], loader: 'ConfigLoader') -> None:
        from .constants import VERBOSITY_LEVELS, VERBOSITY_VERBOSE, VERBOSITY_DEFAULT
        
        cfg = doc.get('config', {})
        if not isinstance(cfg, dict):
            return
        
        styles = loader.global_config.styles.copy()
        
        if 'style-completion' in cfg:
            styles['completion-menu.completion'] = cfg['style-completion']
        if 'style-completion-current' in cfg:
            styles['completion-menu.completion.current'] = cfg['style-completion-current']
        if 'style-scrollbar-background' in cfg:
            styles['scrollbar.background'] = cfg['style-scrollbar-background']
        if 'style-scrollbar-button' in cfg:
            styles['scrollbar.button'] = cfg['style-scrollbar-button']
        
        loader.global_config.styles = styles
        
        if 'style-placeholder-color' in cfg:
            loader.global_config.placeholder_color = cfg['style-placeholder-color']
        if 'style-placeholder-text' in cfg:
            loader.global_config.placeholder_text = cfg['style-placeholder-text']
            
        if 'history-size' in cfg:
            # Rule 1.2.19: Max 1000
            val = int(cfg['history-size'])
            loader.global_config.history_size = min(val, 1000)
        
        # Handle verbosity (with backward compatibility for verbose: true/false)
        if 'verbosity' in cfg:
            val = str(cfg['verbosity']).lower()
            if val in VERBOSITY_LEVELS:
                loader.global_config.verbosity = val
            else:
                print(f"Warning: Invalid verbosity '{val}', using 'default'")
                loader.global_config.verbosity = VERBOSITY_DEFAULT
        elif 'verbose' in cfg:
            # Backward compatibility: verbose: true -> verbosity: verbose
            loader.global_config.verbosity = VERBOSITY_VERBOSE if bool(cfg['verbose']) else VERBOSITY_DEFAULT
        
        if 'shell' in cfg:
            loader.global_config.shell = bool(cfg['shell'])


class DictBlockParser(BlockParser):
    """Factory for parsing dict blocks."""
    
    def parse(self, doc: Dict[str, Any], loader: 'ConfigLoader') -> None:
        name = doc['name']
        data = loader._process_data_structure(doc.get('data', []))
        loader.dicts[name] = DictConfig(name=name, data=data)


class DynamicDictBlockParser(BlockParser):
    """Factory for parsing dynamic_dict blocks."""
    
    def parse(self, doc: Dict[str, Any], loader: 'ConfigLoader') -> None:
        loader.dynamic_dicts[doc['name']] = DynamicDictConfig(
            name=doc['name'],
            command=doc['command'],
            mapping=doc['mapping'],
            priority=doc.get('priority', 1),
            timeout=doc.get('timeout', 10),  # Rule 3.9
            cache_ttl=doc.get('cache-ttl', 300)  # Rule 1.2.2
        )


class CommandBlockParser(BlockParser):
    """Factory for parsing command blocks."""
    
    def parse(self, doc: Dict[str, Any], loader: 'ConfigLoader') -> None:
        loader.commands.append(loader._parse_command(doc))


# Block Parser Factory Registry
BLOCK_PARSERS: Dict[str, BlockParser] = {
    'dict': DictBlockParser(),
    'dynamic_dict': DynamicDictBlockParser(),
    'command': CommandBlockParser(),
}

# Special parser for config blocks (detected by 'config' key presence)
CONFIG_PARSER = ConfigBlockParser()


class ConfigLoader:
    """Loads and parses dya.yaml configuration files using Factory pattern."""
    
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.dicts: Dict[str, DictConfig] = {}
        self.dynamic_dicts: Dict[str, DynamicDictConfig] = {}
        self.commands: List[CommandConfig] = []
        self.global_config: GlobalConfig = GlobalConfig()

    def _substitute_env_vars(self, text: str) -> str:
        """Substitute environment variables in text."""
        if not isinstance(text, str):
            return text
        pattern = r'\$\$\{env\.(\w+)\}'
        def replace(match):
            var_name = match.group(1)
            return os.environ.get(var_name, '')
        return re.sub(pattern, replace, text)

    def _process_data_structure(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process data structure with environment variable substitution."""
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

    def load(self) -> None:
        """Load and parse configuration file using Factory pattern."""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Config file not found at {self.config_file}")

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
                    # Skip documents that aren't dictionaries
                    continue
                
                # Use Factory pattern for block parsing
                if 'config' in doc:
                    CONFIG_PARSER.parse(doc, self)
                else:
                    doc_type = doc.get('type')
                    if doc_type in BLOCK_PARSERS:
                        BLOCK_PARSERS[doc_type].parse(doc, self)
                    # Unknown types are silently ignored

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
            helper_type=doc.get('helper_type', 'auto'),  # Default to 'auto'
            sub=subs,
            args=[self._parse_arg(a) for a in doc.get('args', [])],
            timeout=doc.get('timeout', 0), # Rule 4.9
            strict=doc.get('strict', False),
            set_locals=doc.get('set-locals', False) # Rule 4.21
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
            args=[self._parse_arg(a) for a in doc.get('args', [])],
            set_locals=doc.get('set-locals', False) # Rule 4.21
        )
    
    def _parse_arg(self, doc: Dict) -> ArgConfig:
        return ArgConfig(
            alias=doc['alias'],
            command=doc['command'],
            helper=doc.get('helper')
        )
