"""
Dict Chaining Tests
Test Rules:
    @system_rules.txt
    @global-test-rules.md

Tests for:
- Dict → Dict chaining (lazy loading)
- Validation that dicts cannot reference dynamic_dicts
- Complex chains: dict → dict → dynamic_dict → dynamic_dict
"""
import os
import sys
import unittest
import tempfile
from unittest.mock import patch, MagicMock
from io import StringIO

# Mock prompt_toolkit modules BEFORE any imports
sys.modules['prompt_toolkit'] = MagicMock()
sys.modules['prompt_toolkit.shortcuts'] = MagicMock()
sys.modules['prompt_toolkit.formatted_text'] = MagicMock()
sys.modules['prompt_toolkit.key_binding'] = MagicMock()
sys.modules['prompt_toolkit.history'] = MagicMock()
sys.modules['prompt_toolkit.patch_stdout'] = MagicMock()
sys.modules['prompt_toolkit.completion'] = MagicMock()
sys.modules['prompt_toolkit.styles'] = MagicMock()

# Add src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from dynamic_alias.config import ConfigLoader
from dynamic_alias.cache import CacheManager
from dynamic_alias.resolver import DataResolver
from dynamic_alias.validator import ConfigValidator


class TestDictToDictChaining(unittest.TestCase):
    """Test dict → dict chaining (lazy loading)."""
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "cache.json")
        
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def test_dict_can_reference_another_dict(self):
        """Dict with $${other_dict.key} should resolve correctly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write("""
---
type: dict
name: base_config
data:
  - env: production
    region: us-east-1

---
type: dict
name: derived_config  
data:
  - combined: $${base_config.env}-$${base_config.region}
""")
            f.flush()
            
            loader = ConfigLoader(f.name)
            loader.load()
            
            cache = CacheManager(self.cache_path, enabled=True)
            cache.load()
            
            resolver = DataResolver(loader, cache)
            
            # Resolve derived_config - should trigger lazy resolution of base_config
            data = resolver.resolve_one('derived_config')
            
            self.assertIsNotNone(data)
            self.assertEqual(len(data), 1)
            # The value should still contain the reference at dict level
            # Resolution happens at command execution time via VariableResolver
            self.assertIn('combined', data[0])
            
        os.unlink(f.name)
    
    def test_dict_chain_three_levels(self):
        """Dict1 → Dict2 → Dict3 chain should pass validation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write("""
---
type: dict
name: level1
data:
  - value: L1

---
type: dict
name: level2
data:
  - value: $${level1.value}-L2

---
type: dict
name: level3
data:
  - value: $${level2.value}-L3
""")
            f.flush()
            
            validator = ConfigValidator(f.name)
            report = validator.validate()
            
            # Should pass - dicts can reference dicts
            dict_ref_check = next(
                (r for r in report.results if 'dict→dynamic_dict' in r.message), 
                None
            )
            if dict_ref_check:
                self.assertTrue(dict_ref_check.passed)
            
        os.unlink(f.name)


class TestValidatorDictDynamicDictReference(unittest.TestCase):
    """Test validation prevents dicts from referencing dynamic_dicts."""
    
    def test_validator_fails_dict_referencing_dynamic_dict(self):
        """Validation should fail when dict references dynamic_dict."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write("""
---
type: dynamic_dict
name: dyn_source
command: echo '[]'
mapping:
  key: key

---
type: dict
name: static_dict
data:
  - value: $${dyn_source.key}
""")
            f.flush()
            
            validator = ConfigValidator(f.name)
            report = validator.validate()
            
            # Should fail - dict cannot reference dynamic_dict
            ref_errors = [r for r in report.results 
                         if 'cannot reference dynamic_dict' in r.message and not r.passed]
            self.assertGreater(len(ref_errors), 0, 
                             "Expected validation error for dict referencing dynamic_dict")
            
        os.unlink(f.name)
    
    def test_validator_allows_dict_referencing_dict(self):
        """Validation should pass when dict references another dict."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write("""
---
type: dict
name: base
data:
  - key: value

---
type: dict
name: derived
data:
  - ref: $${base.key}
""")
            f.flush()
            
            validator = ConfigValidator(f.name)
            report = validator.validate()
            
            # Should pass - dicts can reference other dicts
            dict_dyn_check = next(
                (r for r in report.results if 'dict→dynamic_dict' in r.message),
                None
            )
            if dict_dyn_check:
                self.assertTrue(dict_dyn_check.passed)
            
        os.unlink(f.name)
    
    def test_validator_allows_dynamic_dict_referencing_dynamic_dict(self):
        """Validation should pass when dynamic_dict references another dynamic_dict."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write("""
---
type: dynamic_dict
name: dyn1
priority: 1
command: echo '[]'
mapping:
  key: key

---
type: dynamic_dict
name: dyn2
priority: 2
command: echo '$${dyn1.key}'
mapping:
  key: key
""")
            f.flush()
            
            validator = ConfigValidator(f.name)
            report = validator.validate()
            
            # Should pass - dynamic_dicts can reference other dynamic_dicts
            # Just check there's no dict→dynamic_dict error
            ref_errors = [r for r in report.results 
                         if 'cannot reference dynamic_dict' in r.message and not r.passed]
            self.assertEqual(len(ref_errors), 0)
            
        os.unlink(f.name)


class TestComplexChainValidation(unittest.TestCase):
    """Test complex chain validation: dict → dict → dynamic_dict → dynamic_dict."""
    
    def test_complex_chain_dict_dict_dynamicdict_dynamicdict(self):
        """Complex chain: dict1→dict2, dynamic_dict1→dict2, dynamic_dict2→dynamic_dict1."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write("""
---
type: dict
name: config_base
data:
  - prefix: PROD

---
type: dict
name: config_derived
data:
  - full_prefix: $${config_base.prefix}-APP

---
type: dynamic_dict
name: level1_dyn
priority: 1
command: echo '[{"val": "DYN-$${config_derived.full_prefix}"}]'
mapping:
  result: val

---
type: dynamic_dict
name: level2_dyn
priority: 2
command: echo '[{"val": "$${level1_dyn.result}-L2"}]'
mapping:
  result: val

---
type: command
name: Complex Chain Test
alias: complex-chain
command: echo $${level2_dyn.result}
""")
            f.flush()
            
            validator = ConfigValidator(f.name)
            report = validator.validate()
            
            # All validations should pass for this complex chain
            failed = [r for r in report.results if not r.passed]
            
            # Filter out expected non-blocking issues
            critical_failures = [r for r in failed 
                                if 'cannot reference dynamic_dict' in r.message]
            
            self.assertEqual(len(critical_failures), 0,
                           f"Complex chain should be valid, but got: {[r.message for r in critical_failures]}")
            
        os.unlink(f.name)
    
    def test_invalid_chain_dict_refs_dynamic_dict_in_complex_chain(self):
        """Complex chain with invalid dict→dynamic_dict reference should fail."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write("""
config:
  verbosity: default

---
type: dynamic_dict
name: dyn_source
priority: 1
command: |
  echo '[]'
mapping:
  key: key

---
type: dict
name: bad_dict
data:
  - invalid_ref: $${dyn_source.key}

---
type: dict
name: derived_dict
data:
  - value: $${bad_dict.invalid_ref}
""")
            f.flush()
            
            validator = ConfigValidator(f.name)
            report = validator.validate()
            
            # Should fail because bad_dict references dyn_source
            ref_errors = [r for r in report.results 
                         if 'cannot reference dynamic_dict' in r.message and not r.passed]
            self.assertGreater(len(ref_errors), 0)
            
        os.unlink(f.name)


class TestDictChainWithTestConfig(unittest.TestCase):
    """Test dict chaining with the main test config file."""
    
    @classmethod
    def setUpClass(cls):
        cls.config_file = os.path.join(os.path.dirname(__file__), "dya.yaml")
        
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "dya.json")
        
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def test_existing_config_passes_dict_dynamic_dict_validation(self):
        """Existing dya.yaml should pass the new dict→dynamic_dict validation."""
        validator = ConfigValidator(self.config_file)
        report = validator.validate()
        
        # Check for our new validation
        dict_dyn_check = next(
            (r for r in report.results if 'dict→dynamic_dict' in r.message),
            None
        )
        
        # Should exist and pass (no dict in dya.yaml references dynamic_dicts)
        self.assertIsNotNone(dict_dyn_check, "Dict→dynamic_dict validation should run")
        self.assertTrue(dict_dyn_check.passed, 
                       f"Existing config should pass: {dict_dyn_check.message}")


if __name__ == '__main__':
    unittest.main()
