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
    timeout: int = DEFAULT_TIMEOUT

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

@dataclass
class CommandConfig:
    name: str
    alias: str
    command: str
    helper: Optional[str] = None
    sub: List[SubCommand] = field(default_factory=list)
    args: List[ArgConfig] = field(default_factory=list)
    timeout: int = DEFAULT_TIMEOUT
