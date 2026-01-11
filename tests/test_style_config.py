"""
Style Config Tests
Test Rules:
    @system_rules.txt
    @global-test-rules.md
"""
import unittest
import os
import tempfile
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from dynamic_alias.config import ConfigLoader
from dynamic_alias.models import default_styles

class TestStyleConfig(unittest.TestCase):
    def test_dya_yaml_config_loading(self):
        # Verify loading from the standardized tests/dya.yaml
        config_file = os.path.join(os.path.dirname(__file__), "dya.yaml")
        assert os.path.exists(config_file)
        
        loader = ConfigLoader(config_file)
        loader.load()
        
        # dya.yaml has:
        # style-completion: "bg:#002222 #ffffff"
        # history-size: 5
        
        styles = loader.global_config.styles
        self.assertEqual(styles['completion-menu.completion'], "bg:#002222 #ffffff")
        self.assertEqual(loader.global_config.history_size, 5)

    def test_default_styles(self):
        # Unit test for default fallback (files without config block)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as tmp:
            tmp.write("""---
type: command
name: TestCmd
alias: test
command: echo test
""")
            tmp_path = tmp.name

        try:
            loader = ConfigLoader(tmp_path)
            loader.load()
            
            # Verify defaults
            defaults = default_styles()
            self.assertEqual(loader.global_config.styles, defaults)
            self.assertEqual(loader.global_config.placeholder_color, "gray")
        finally:
            os.remove(tmp_path)

    def test_explicit_type_config(self):
        # Unit test for 'type: config' block pattern
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as tmp:
            tmp.write("""---
type: config
style-completion: "bg:custom_bg custom_fg"
history-size: 10

---
type: command
name: TestCmd
alias: test
command: echo test
""")
            tmp_path = tmp.name

        try:
            loader = ConfigLoader(tmp_path)
            loader.load()
            
            styles = loader.global_config.styles
            self.assertEqual(styles['completion-menu.completion'], "bg:custom_bg custom_fg")
            self.assertEqual(loader.global_config.history_size, 10)
        finally:
            os.remove(tmp_path)

    def test_bom_config(self):
        # Unit test for BOM handling
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml', encoding='utf-8-sig') as tmp:
            tmp.write("""config:
    style-completion: "bg:bom_bg bom_fg"
""")
            tmp_path = tmp.name

        try:
            loader = ConfigLoader(tmp_path)
            loader.load()
            
            styles = loader.global_config.styles
            self.assertEqual(styles['completion-menu.completion'], "bg:bom_bg bom_fg")
        finally:
            os.remove(tmp_path)

if __name__ == '__main__':
    unittest.main()
