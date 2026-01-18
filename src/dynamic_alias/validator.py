"""
Config Validator Module

Implements rules 1.1.14, 1.1.15, 1.1.16, 1.1.17:
- Validate config file structure and keys
- Check that all referenced dicts/dynamic_dicts are defined
- Check priority order for dynamic_dict references
- User-friendly output with checklist, hints, and summary

Design Pattern: Strategy pattern for block type validation
"""
import os
import re
import yaml
from typing import Dict, List, Tuple, Any, Set, Optional, Protocol
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from .constants import REQUIRED_FIELDS, OPTIONAL_FIELDS, CONFIG_KEYS
from .utils import VariableResolver


@dataclass
class ValidationResult:
    """Represents the result of a single validation check."""
    passed: bool
    message: str
    hint: Optional[str] = None
    location: Optional[str] = None  # e.g., "block 3, line 45"


@dataclass
class ValidationReport:
    """Complete validation report."""
    config_path: str
    results: List[ValidationResult] = field(default_factory=list)
    
    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)
    
    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)
    
    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)
    
    def add(self, result: ValidationResult) -> None:
        self.results.append(result)


# =============================================================================
# Strategy Pattern: Block Validation Strategies
# =============================================================================

class BlockValidationStrategy(ABC):
    """Abstract strategy for validating different block types."""
    
    @abstractmethod
    def validate(self, block: Dict[str, Any], name: str, report: ValidationReport) -> None:
        """Validate a block and add results to report."""
        pass
    
    def _validate_required_fields(self, block: Dict, block_type: str, name: str, report: ValidationReport) -> None:
        """Check required fields exist for a block type."""
        required = REQUIRED_FIELDS.get(block_type, [])
        missing = [f for f in required if f not in block]
        
        if missing:
            report.add(ValidationResult(
                passed=False,
                message=f"{block_type} '{name}' missing required fields: {', '.join(missing)}",
                hint=f"Required fields for {block_type}: {', '.join(required)}",
                location=f"Block {block.get('_block_index', '?')}"
            ))
        else:
            report.add(ValidationResult(
                passed=True,
                message=f"{block_type} '{name}' has all required fields"
            ))


class DictBlockValidator(BlockValidationStrategy):
    """Strategy for validating dict blocks."""
    
    def validate(self, block: Dict[str, Any], name: str, report: ValidationReport) -> None:
        self._validate_required_fields(block, 'dict', name, report)
        self._validate_data(block, name, report)
    
    def _validate_data(self, d: Dict, name: str, report: ValidationReport) -> None:
        """Validate dict data structure."""
        data = d.get('data', [])
        if not isinstance(data, list):
            report.add(ValidationResult(
                passed=False,
                message=f"dict '{name}' data must be a list",
                hint="Use YAML list syntax: - key: value",
                location=f"Block {d.get('_block_index', '?')}"
            ))
        elif len(data) == 0:
            report.add(ValidationResult(
                passed=False,
                message=f"dict '{name}' has empty data list",
                hint="Add at least one item to the data list",
                location=f"Block {d.get('_block_index', '?')}"
            ))
        else:
            report.add(ValidationResult(
                passed=True,
                message=f"dict '{name}' has valid data structure ({len(data)} items)"
            ))


class DynamicDictBlockValidator(BlockValidationStrategy):
    """Strategy for validating dynamic_dict blocks."""
    
    def validate(self, block: Dict[str, Any], name: str, report: ValidationReport) -> None:
        self._validate_required_fields(block, 'dynamic_dict', name, report)
        self._validate_mapping(block, name, report)
    
    def _validate_mapping(self, dd: Dict, name: str, report: ValidationReport) -> None:
        """Validate dynamic_dict mapping structure."""
        mapping = dd.get('mapping', {})
        if not isinstance(mapping, dict):
            report.add(ValidationResult(
                passed=False,
                message=f"dynamic_dict '{name}' mapping must be a dict",
                hint="Use YAML dict syntax: internal_key: json_key",
                location=f"Block {dd.get('_block_index', '?')}"
            ))
        elif len(mapping) == 0:
            report.add(ValidationResult(
                passed=False,
                message=f"dynamic_dict '{name}' has empty mapping",
                hint="Add at least one key mapping",
                location=f"Block {dd.get('_block_index', '?')}"
            ))
        else:
            report.add(ValidationResult(
                passed=True,
                message=f"dynamic_dict '{name}' has valid mapping ({len(mapping)} keys)"
            ))


class CommandBlockValidator(BlockValidationStrategy):
    """Strategy for validating command blocks."""
    
    def validate(self, block: Dict[str, Any], name: str, report: ValidationReport) -> None:
        self._validate_required_fields(block, 'command', name, report)
        self._validate_subcommands(block.get('sub', []), name, report)
        self._validate_args(block.get('args', []), name, report)
    
    def _validate_subcommands(self, subs: List, parent_name: str, report: ValidationReport) -> None:
        """Validate subcommand structure recursively."""
        for i, sub in enumerate(subs):
            if not isinstance(sub, dict):
                continue
            
            sub_name = sub.get('alias', f'sub_{i}')
            
            # Check required fields for sub
            required = ['alias', 'command']
            missing = [f for f in required if f not in sub]
            if missing:
                report.add(ValidationResult(
                    passed=False,
                    message=f"Subcommand '{sub_name}' in '{parent_name}' missing: {', '.join(missing)}",
                    hint="Subcommands require 'alias' and 'command' fields"
                ))
            
            # Recurse
            self._validate_subcommands(sub.get('sub', []), f"{parent_name}.{sub_name}", report)
            self._validate_args(sub.get('args', []), f"{parent_name}.{sub_name}", report)
    
    def _validate_args(self, args: List, parent_name: str, report: ValidationReport) -> None:
        """Validate args structure."""
        for i, arg in enumerate(args):
            if not isinstance(arg, dict):
                continue
            
            arg_alias = arg.get('alias', f'arg_{i}')
            arg_name = arg_alias if isinstance(arg_alias, str) else str(arg_alias)
            
            # Check required fields
            required = ['alias', 'command']
            missing = [f for f in required if f not in arg]
            if missing:
                report.add(ValidationResult(
                    passed=False,
                    message=f"Arg '{arg_name}' in '{parent_name}' missing: {', '.join(missing)}",
                    hint="Args require 'alias' and 'command' fields"
                ))
            
            # Validate alias array structure if alias is a list
            if 'alias' in arg:
                self._validate_alias_array(arg['alias'], parent_name, report)
            
            # Args cannot have sub or args (rule 5.2)
            if 'sub' in arg:
                report.add(ValidationResult(
                    passed=False,
                    message=f"Arg '{arg_name}' in '{parent_name}' cannot have 'sub'",
                    hint="Args are non-recursive - use subcommands instead"
                ))
            if 'args' in arg:
                report.add(ValidationResult(
                    passed=False,
                    message=f"Arg '{arg_name}' in '{parent_name}' cannot have nested 'args'",
                    hint="Args are non-recursive"
                ))
    
    def _validate_alias_array(self, alias, parent_name: str, report: ValidationReport) -> None:
        """Validate that all aliases in an array have the same variable structure."""
        if not isinstance(alias, list):
            return  # Single string alias, nothing to validate
        
        if len(alias) < 2:
            return  # Single item list, nothing to compare
        
        import re
        var_pattern = r'\$\{(\w+)\}|\$\$\{(\w+)(?:\[\d+\])?\.(\w+)\}'
        
        def extract_var_structure(text: str) -> str:
            """Extract variable structure from alias (order and names preserved)."""
            matches = re.findall(var_pattern, text)
            # Return a normalized structure string
            vars_list = []
            for match in matches:
                if match[0]:  # User variable ${var}
                    vars_list.append(f"${{{match[0]}}}")
                elif match[1]:  # App variable $${source.key}
                    vars_list.append(f"$${{{match[1]}.{match[2]}}}")
            return '|'.join(vars_list)
        
        # Get structure from first alias
        first_structure = extract_var_structure(alias[0])
        
        for idx, alt_alias in enumerate(alias[1:], start=1):
            alt_structure = extract_var_structure(alt_alias)
            if alt_structure != first_structure:
                report.add(ValidationResult(
                    passed=False,
                    message=f"Arg alias array in '{parent_name}' has inconsistent variable structure",
                    hint=f"All aliases must have same variables. '{alias[0]}' has '{first_structure or '(none)'}' but '{alt_alias}' has '{alt_structure or '(none)'}'"
                ))


# Strategy registry for block types
BLOCK_VALIDATORS: Dict[str, BlockValidationStrategy] = {
    'dict': DictBlockValidator(),
    'dynamic_dict': DynamicDictBlockValidator(),
    'command': CommandBlockValidator(),
}


class ConfigValidator:
    """Validates dya.yaml configuration files using Strategy pattern."""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.report = ValidationReport(config_path=config_path)
        self.raw_content = ""
        self.blocks: List[Dict[str, Any]] = []
        self.dicts: Dict[str, Dict] = {}
        self.dynamic_dicts: Dict[str, Dict] = {}
        self.commands: List[Dict] = []
        self.global_config: Optional[Dict] = None
    
    def validate(self) -> ValidationReport:
        """Run all validations and return report."""
        
        # 1. Check file exists
        if not self._check_file_exists():
            return self.report
        
        # 2. Check valid YAML
        if not self._check_valid_yaml():
            return self.report
        
        # 3. Parse blocks
        self._parse_blocks()
        
        # 4. Validate each block structure using Strategy pattern
        self._validate_block_structures()
        
        # 5. Validate references (rule 1.1.15)
        self._validate_references()
        
        # 6. Validate priority order for dynamic_dict references
        self._validate_priority_order()
        
        # 7. Validate dict index bounds and key existence (static dicts only)
        self._validate_dict_index_and_keys()
        
        return self.report
    
    def _check_file_exists(self) -> bool:
        """Check if config file exists."""
        if os.path.exists(self.config_path):
            self.report.add(ValidationResult(
                passed=True,
                message=f"Config file exists: {self.config_path}"
            ))
            return True
        else:
            self.report.add(ValidationResult(
                passed=False,
                message=f"Config file not found: {self.config_path}",
                hint="Create the config file or specify correct path with --dya-config"
            ))
            return False
    
    def _check_valid_yaml(self) -> bool:
        """Check if file is valid YAML."""
        try:
            # Read with BOM handling
            with open(self.config_path, 'r', encoding='utf-8-sig') as f:
                self.raw_content = f.read()
            
            # Try to parse each document
            docs = [doc for doc in self.raw_content.split('---') if doc.strip()]
            
            for i, doc_str in enumerate(docs, 1):
                try:
                    yaml.safe_load(doc_str)
                except yaml.YAMLError as e:
                    self.report.add(ValidationResult(
                        passed=False,
                        message=f"Invalid YAML syntax in block {i}",
                        hint=str(e),
                        location=f"Block {i}"
                    ))
                    return False
            
            self.report.add(ValidationResult(
                passed=True,
                message="Valid YAML syntax"
            ))
            return True
            
        except Exception as e:
            self.report.add(ValidationResult(
                passed=False,
                message=f"Failed to read config file: {e}",
                hint="Check file permissions and encoding (UTF-8)"
            ))
            return False
    
    def _parse_blocks(self) -> None:
        """Parse config into blocks and categorize them."""
        docs = [doc for doc in self.raw_content.split('---') if doc.strip()]
        
        for i, doc_str in enumerate(docs, 1):
            try:
                doc = yaml.safe_load(doc_str)
                if not doc or not isinstance(doc, dict):
                    continue
                
                doc['_block_index'] = i
                self.blocks.append(doc)
                
                # Categorize
                if 'config' in doc:
                    self.global_config = doc.get('config', {})
                elif doc.get('type') == 'dict':
                    name = doc.get('name', f'unnamed_dict_{i}')
                    self.dicts[name] = doc
                elif doc.get('type') == 'dynamic_dict':
                    name = doc.get('name', f'unnamed_dynamic_dict_{i}')
                    self.dynamic_dicts[name] = doc
                elif doc.get('type') == 'command':
                    self.commands.append(doc)
                    
            except Exception:
                pass
    
    def _validate_block_structures(self) -> None:
        """Validate block structures using Strategy pattern."""
        
        # Validate config block (special case, not a typed block)
        if self.global_config is not None:
            # Check for deprecated 'verbose' key
            if 'verbose' in self.global_config:
                self.report.add(ValidationResult(
                    passed=False,
                    message="Config uses deprecated 'verbose' key",
                    hint="Replace 'verbose: true/false' with 'verbosity: silent|default|verbose|trace'",
                    location="config block"
                ))
            
            # Check path-completion requires shell mode
            if self.global_config.get('path-completion') and not self.global_config.get('shell'):
                self.report.add(ValidationResult(
                    passed=False,
                    message="'path-completion' requires 'shell: true'",
                    hint="Enable shell mode with 'shell: true' or disable path-completion",
                    location="config block"
                ))
            
            invalid_keys = [k for k in self.global_config.keys() 
                          if k not in CONFIG_KEYS]
            if invalid_keys:
                self.report.add(ValidationResult(
                    passed=False,
                    message=f"Unknown config keys: {', '.join(invalid_keys)}",
                    hint=f"Valid keys: {', '.join(CONFIG_KEYS)}",
                    location="config block"
                ))
            else:
                self.report.add(ValidationResult(
                    passed=True,
                    message="Config block has valid keys"
                ))
        
        # Use Strategy pattern for typed blocks
        for name, d in self.dicts.items():
            BLOCK_VALIDATORS['dict'].validate(d, name, self.report)
        
        for name, dd in self.dynamic_dicts.items():
            BLOCK_VALIDATORS['dynamic_dict'].validate(dd, name, self.report)
        
        for cmd in self.commands:
            name = cmd.get('name', 'unnamed')
            BLOCK_VALIDATORS['command'].validate(cmd, name, self.report)
    
    def _extract_references(self, text: str) -> Set[Tuple[str, str]]:
        """Extract all $${source.key} references from text."""
        return VariableResolver.extract_app_vars(text)
    
    def _validate_references(self):
        """Rule 1.1.15: Check all referenced dicts/dynamic_dicts are defined."""
        # Rule 1.2.25: 'locals' is a reserved built-in source for local variables
        all_sources = set(self.dicts.keys()) | set(self.dynamic_dicts.keys()) | {'locals'}
        
        # Check dynamic_dict commands
        for name, dd in self.dynamic_dicts.items():
            cmd = dd.get('command', '')
            refs = self._extract_references(cmd)
            for source, _index, key in refs:
                if source not in all_sources:
                    self.report.add(ValidationResult(
                        passed=False,
                        message=f"dynamic_dict '{name}' references undefined source: '{source}'",
                        hint=f"Define a dict or dynamic_dict named '{source}'",
                        location=f"Block {dd.get('_block_index', '?')}"
                    ))
        
        # Check commands
        for cmd in self.commands:
            name = cmd.get('name', 'unnamed')
            alias = cmd.get('alias', '')
            command_str = cmd.get('command', '')
            
            # Check alias and command
            for text in [alias, command_str]:
                refs = self._extract_references(text)
                for source, _index, key in refs:
                    if source not in all_sources:
                        self.report.add(ValidationResult(
                            passed=False,
                            message=f"command '{name}' references undefined source: '{source}'",
                            hint=f"Define a dict or dynamic_dict named '{source}'",
                            location=f"Block {cmd.get('_block_index', '?')}"
                        ))
            
            # Check subcommands and args
            self._check_sub_references(cmd.get('sub', []), name, all_sources)
            self._check_arg_references(cmd.get('args', []), name, all_sources)
        
        # If we got here without adding failures, add success
        ref_failures = [r for r in self.report.results 
                       if not r.passed and 'references undefined' in r.message]
        if not ref_failures:
            self.report.add(ValidationResult(
                passed=True,
                message="All dict/dynamic_dict references are valid"
            ))
    
    def _check_sub_references(self, subs: List, parent: str, all_sources: Set[str]):
        """Recursively check references in subcommands."""
        for sub in subs:
            if not isinstance(sub, dict):
                continue
            for text in [sub.get('alias', ''), sub.get('command', '')]:
                refs = self._extract_references(text)
                for source, _index, key in refs:
                    if source not in all_sources:
                        self.report.add(ValidationResult(
                            passed=False,
                            message=f"Subcommand in '{parent}' references undefined source: '{source}'",
                            hint=f"Define a dict or dynamic_dict named '{source}'"
                        ))
            self._check_sub_references(sub.get('sub', []), parent, all_sources)
            self._check_arg_references(sub.get('args', []), parent, all_sources)
    
    def _check_arg_references(self, args: List, parent: str, all_sources: Set[str]):
        """Check references in args."""
        for arg in args:
            if not isinstance(arg, dict):
                continue
            for text in [arg.get('alias', ''), arg.get('command', '')]:
                refs = self._extract_references(text)
                for source, _index, key in refs:
                    if source not in all_sources:
                        self.report.add(ValidationResult(
                            passed=False,
                            message=f"Arg in '{parent}' references undefined source: '{source}'",
                            hint=f"Define a dict or dynamic_dict named '{source}'"
                        ))
    
    def _validate_priority_order(self):
        """Check that dynamic_dict references respect priority order."""
        # Get priorities
        priorities = {}
        for name, dd in self.dynamic_dicts.items():
            priorities[name] = dd.get('priority', 1)
        
        # Static dicts have implicit priority 0 (always available)
        for name in self.dicts.keys():
            priorities[name] = 0
        
        # Check each dynamic_dict
        for name, dd in self.dynamic_dicts.items():
            my_priority = priorities[name]
            cmd = dd.get('command', '')
            refs = self._extract_references(cmd)
            
            for source, _index, key in refs:
                if source in priorities:
                    ref_priority = priorities[source]
                    # With lazy loading, priority order is not essential for correctness
                    # The resolver handles dependencies on-demand
                    # Only circular references should block - priority is just for optimization
                    if source in self.dynamic_dicts and ref_priority >= my_priority:
                        self.report.add(ValidationResult(
                            passed=True,  # Warning only, not blocking
                            message=f"[WARNING] dynamic_dict '{name}' (priority {my_priority}) references '{source}' (priority {ref_priority}) - lazy loading will handle this"
                        ))
        
        # Priority order is always "OK" now (just warnings)
        self.report.add(ValidationResult(
            passed=True,
            message="Priority order checked (lazy loading handles dependencies)"
        ))
        
        # Check for circular references
        self._validate_circular_references()
    
    def _validate_circular_references(self):
        """Detect circular references in dynamic_dict dependencies."""
        # Build dependency graph: name -> set of dependencies
        graph: Dict[str, Set[str]] = {}
        
        for name, dd in self.dynamic_dicts.items():
            cmd = dd.get('command', '')
            refs = self._extract_references(cmd)
            # Only track references to other dynamic_dicts (not static dicts)
            deps = {source for source, _index, key in refs if source in self.dynamic_dicts}
            graph[name] = deps
        
        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        cycles_found = []
        
        def find_cycle(node: str, path: List[str]) -> Optional[List[str]]:
            if node in rec_stack:
                # Found cycle - return the cycle path
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]
            if node in visited:
                return None
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for dep in graph.get(node, []):
                cycle = find_cycle(dep, path)
                if cycle:
                    return cycle
            
            path.pop()
            rec_stack.remove(node)
            return None
        
        for name in self.dynamic_dicts:
            if name not in visited:
                cycle = find_cycle(name, [])
                if cycle:
                    cycles_found.append(cycle)
        
        if cycles_found:
            for cycle in cycles_found:
                cycle_str = ' -> '.join(cycle)
                self.report.add(ValidationResult(
                    passed=False,
                    message=f"Circular reference detected: {cycle_str}",
                    hint="Break the cycle by using a static dict or restructuring dependencies"
                ))
        else:
            self.report.add(ValidationResult(
                passed=True,
                message="No circular references in dynamic_dict dependencies"
            ))
    
    def _validate_dict_index_and_keys(self):
        """
        Validate that indexed references to static dicts have valid bounds and keys.
        
        For $${dict[N].key}:
        - Check that index N is within bounds of dict.data
        - Check that key exists in dict.data[N]
        
        Dynamic dicts are skipped (data unknown at validation time).
        """
        errors_found = False
        
        def validate_reference(source: str, index_str: str, key: str, 
                               context: str, location: str):
            """Validate a single reference against static dict."""
            nonlocal errors_found
            
            # Skip if not a static dict
            if source not in self.dicts:
                return
            
            # Skip 'locals' (built-in)
            if source == 'locals':
                return
            
            dict_data = self.dicts[source].get('data', [])
            dict_size = len(dict_data)
            
            # Parse index (default 0)
            index = int(index_str) if index_str else 0
            
            # Check index bounds
            if index >= dict_size:
                errors_found = True
                self.report.add(ValidationResult(
                    passed=False,
                    message=f"{context} uses index [{index}] but '{source}' only has {dict_size} items",
                    hint=f"Valid indices for '{source}': 0 to {dict_size - 1}" if dict_size > 0 else f"Dict '{source}' is empty",
                    location=location
                ))
                return
            
            # Check key exists at that index
            item = dict_data[index]
            if isinstance(item, dict) and key not in item:
                errors_found = True
                available_keys = list(item.keys())
                self.report.add(ValidationResult(
                    passed=False,
                    message=f"{context} references key '{key}' not found at '{source}[{index}]'",
                    hint=f"Available keys at position {index}: {', '.join(available_keys)}" if available_keys else "Item has no keys",
                    location=location
                ))
        
        # Check all commands
        for cmd in self.commands:
            name = cmd.get('name', 'unnamed')
            block_idx = cmd.get('_block_index', '?')
            
            for text in [cmd.get('alias', ''), cmd.get('command', '')]:
                refs = self._extract_references(text)
                for source, index_str, key in refs:
                    validate_reference(source, index_str, key, 
                                       f"command '{name}'", f"Block {block_idx}")
            
            # Check subcommands and args
            self._check_sub_dict_refs(cmd.get('sub', []), name, validate_reference)
            self._check_arg_dict_refs(cmd.get('args', []), name, validate_reference)
        
        # Check dynamic_dict commands (they might reference static dicts)
        for name, dd in self.dynamic_dicts.items():
            block_idx = dd.get('_block_index', '?')
            refs = self._extract_references(dd.get('command', ''))
            for source, index_str, key in refs:
                validate_reference(source, index_str, key,
                                   f"dynamic_dict '{name}'", f"Block {block_idx}")
        
        if not errors_found:
            self.report.add(ValidationResult(
                passed=True,
                message="All dict index and key references are valid"
            ))
    
    def _check_sub_dict_refs(self, subs: List, parent: str, validate_fn):
        """Recursively check dict references in subcommands."""
        for sub in subs:
            if not isinstance(sub, dict):
                continue
            for text in [sub.get('alias', ''), sub.get('command', '')]:
                refs = self._extract_references(text)
                for source, index_str, key in refs:
                    validate_fn(source, index_str, key, f"subcommand in '{parent}'", parent)
            self._check_sub_dict_refs(sub.get('sub', []), parent, validate_fn)
            self._check_arg_dict_refs(sub.get('args', []), parent, validate_fn)
    
    def _check_arg_dict_refs(self, args: List, parent: str, validate_fn):
        """Check dict references in args."""
        for arg in args:
            if not isinstance(arg, dict):
                continue
            for text in [arg.get('alias', ''), arg.get('command', '')]:
                refs = self._extract_references(text)
                for source, index_str, key in refs:
                    validate_fn(source, index_str, key, f"arg in '{parent}'", parent)

def print_validation_report(report: ValidationReport, shortcut: str = "dya"):
    """Print user-friendly validation report with checklist format."""
    
    print(f"\n{'='*60}")
    print(f"  Configuration Validator ({shortcut})")
    print(f"{'='*60}")
    print(f"\n  Config: {report.config_path}\n")
    
    # Print checklist
    print("  VALIDATION CHECKLIST")
    print("  " + "-"*40)
    
    for result in report.results:
        status = "OK" if result.passed else "FAIL"
        color_start = "" 
        color_end = ""
        
        print(f"  [{status}] {result.message}")
        
        if not result.passed:
            if result.location:
                print(f"      Location: {result.location}")
            if result.hint:
                print(f"      Hint: {result.hint}")
    
    # Print summary
    print(f"\n  " + "-"*40)
    print(f"  SUMMARY")
    print(f"  " + "-"*40)
    
    total = len(report.results)
    passed = report.passed_count
    failed = report.failed_count
    
    if report.passed:
        print(f"\n  [OK] All {total} checks passed!")
        print(f"\n  Configuration is valid.\n")
    else:
        print(f"\n  Results: {passed}/{total} passed, {failed} failed")
        print(f"\n  [FAIL] Configuration has {failed} error(s).")
        print(f"  Please fix the issues above and run validation again.\n")
    
    print(f"{'='*60}\n")
    
    return 0 if report.passed else 1


def print_validation_errors(report: ValidationReport, shortcut: str = "dya"):
    """Print only errors from validation report (silent mode - only outputs on errors)."""
    if report.passed:
        return 0
    
    print(f"\n[{shortcut.upper()}] Configuration errors found in: {report.config_path}")
    print("-" * 50)
    
    for result in report.results:
        if not result.passed:
            print(f"  [FAIL] {result.message}")
            if result.location:
                print(f"    Location: {result.location}")
            if result.hint:
                print(f"    Hint: {result.hint}")
    
    print("-" * 50)
    print(f"Fix the {report.failed_count} error(s) above or run '{shortcut} --{shortcut}-validate' for full report.\n")
    
    return 1


def validate_config_silent(config_path: str, shortcut: str = "dya") -> bool:
    """
    Validate config file in silent mode (only outputs on errors).
    
    Used at startup for both interactive and non-interactive modes.
    Returns True if validation passed, False if there are errors.
    """
    validator = ConfigValidator(config_path)
    report = validator.validate()
    
    if not report.passed:
        print_validation_errors(report, shortcut)
        return False
    
    return True

