# Getting Started

## Requirements

| Requirement | Minimum Version |
|-------------|----------------|
| Python | 3.8+ |
| pip | 22.0+ |
| setuptools | 61.0+ (for building from source) |

## Installation

### From PyPI
```bash
pip install dynamic-alias
```

### From Source
```bash
git clone https://github.com/natanmedeiros/dynamic-alias.git
cd dynamic-alias
pip install -e .
```

### Build Packages

> **Note:** Building from source requires `setuptools>=61.0` and `pip>=22.0`.

**Python Wheel:**
```bash
python -m build
pip install dist/dynamic_alias-*.whl
```

**Debian Package:**
```bash
python setup.py --command-packages=stdeb.command bdist_deb
sudo dpkg -i deb_dist/python3-dynamic-alias_*.deb
```

## First Configuration

Create `~/.dya/dya.yaml` (the directory will be created automatically on first run):

```yaml
config:
  history-size: 50

---
type: command
name: Hello World
alias: hello
command: echo 'Hello, Dynamic Alias!'
```

## Running

### Non-Interactive Mode
```bash
dya hello
# Output: Hello, Dynamic Alias!
```

### Interactive Mode
```bash
dya
# Starts interactive shell with autocomplete
# Type 'hello' and press Tab for suggestions
```

## Config and Cache Paths

By default:
- **Config:** `~/.dya/dya.yaml`
- **Cache:** `~/.dya/dya.json` (automatically encrypted)

Override with flags:
```bash
dya --dya-config /path/to/config.yaml --dya-cache /path/to/cache.json
```

## Next Steps

- [Configuration Reference](configuration.md)
- [Defining Commands](commands.md)
- [Dynamic Data Sources](dynamic-dicts.md)

---

| ← Previous | Next → |
|:-----------|-------:|
| [Back to README](../README.md) | [Configuration](configuration.md) |
