from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

DEFAULT_TIMEOUT = 10

@dataclass
class DictConfig:
    name: str
    data: List[Dict[str, Any]]

@dataclass
class DynamicDictConfig:
    name: str
    command: str
    mapping: Dict[str, str]
    priority: int = 1
    timeout: int = 10  # Rule 3.9: Default 10s
    cache_ttl: int = 300  # Rule 1.2.2: Default 300s

@dataclass
class ArgConfig:
    alias: str
    command: str
    helper: Optional[str] = None

@dataclass
class SubCommand:
    alias: str
    command: str
    helper: Optional[str] = None
    sub: List['SubCommand'] = field(default_factory=list)
    args: List[ArgConfig] = field(default_factory=list)

def default_styles():
    return {
        'completion-menu.completion': 'bg:#008888 #ffffff',
        'completion-menu.completion.current': 'bg:#00aaaa #000000',
        'scrollbar.background': 'bg:#88aaaa',
        'scrollbar.button': 'bg:#222222',
    }

@dataclass
class GlobalConfig:
    styles: Dict[str, str] = field(default_factory=default_styles)
    placeholder_color: str = "gray"
    placeholder_text: str = "(tab for menu)"
    history_size: int = 20  # Rule 1.2.19: Default 20

@dataclass
class CommandConfig:
    name: str
    alias: str
    command: str
    helper: Optional[str] = None
    sub: List[SubCommand] = field(default_factory=list)
    args: List[ArgConfig] = field(default_factory=list)
    timeout: int = 0  # Rule 4.9: Default 0
    strict: bool = False  # Strict mode logic
