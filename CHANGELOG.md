# Changelog

All notable changes to Dynamic Alias will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.5] - 2026-01-22

### Fixed
- **Dict Chain Resolution (again 😅)**: Ok, I admit it... 1.1.4 said it was fixed but it wasn't *really* fixed. Now dict→dict chaining actually works in list mode when you select an item from autocomplete. Third time's the charm, right? 🙈

### Added
- Dict chain list mode examples in `tests/dya.yaml` for manual testing

---

## [1.1.4] - 2026-01-22

### Added
- **Dict Chaining**: Static dicts can now reference other static dicts using `$${other_dict.key}` syntax (lazy loading)
- **Validation**: New validation rule prevents dicts from referencing dynamic_dicts

### Changed
- Documentation updated to clarify dict/dynamic_dict reference rules

---

## [1.1.3] - 2026-01-19

### Fixed
- **Interactive Subprocess Signal Handling**: Fixed Ctrl+C behavior when running interactive programs (like `psql`, `python`, etc.) from dya interactive mode.
  - Ctrl+C is now properly forwarded to the subprocess (e.g., clearing the current line in psql) instead of killing it
  - Ctrl+D correctly exits the subprocess gracefully
  - Terminal state is properly restored after subprocess exit, fixing "broken terminal" issues
  - Works correctly on both Unix/macOS (using SIGINT handling) and Windows (using `CREATE_NEW_PROCESS_GROUP`)

---

## [1.1.2] - 2026-01-17

### Added
- Fix: Support for local variables (`$${locals.key}`) in `dynamic_dict` commands.
- Documentation: Added warnings about using colons (`:`) in YAML commands and recommended multi-line syntax.
- Logging: Enhanced trace logs to show full JSON content of inputs and outputs for easier debugging.
- Error Handling: Added explicit error messages when variable resolution fails (e.g. missing locals or dictionary keys).

### Security
- Workflow: Updated GitHub Actions to use Trusted Publishing (OIDC) for PyPI releases.

## [1.1.1] - 2026-01-17

### Added
- **Path Completion**: New config option `path-completion: true` (requires `shell: true`).
  - Enables inline completion of system commands (from PATH) when no alias matches.
  - Supports Windows built-ins (e.g., `dir`, `echo`, `cls`) and Unix commands.

### Fixed
- **Nested Subcommand Execution**: Resolved an issue where pressing Enter on a nested subcommand (e.g., `cmd sub1`) would incorrectly auto-select the next child (`sub2`) instead of executing `sub1`.
  - Enter behavior logic improved: if no menu item is explicitly selected, Enter now executes the command.
- **CI/CD Reliability**: Updated `cryptography` dependency to version 46.0.3 and adjusted pip compatibility matrix to fix CI failures on older pip environments.

---

## [1.1.0] - 2026-01-17

### ⚠️ Breaking Changes

#### Default File Paths Changed
Config and cache files now use a directory structure:

**Config path:**
- **Old**: `~/.dya.yaml`
- **New**: `~/.dya/dya.yaml`

**Cache path:**
- **Old**: `~/.dya.json`
- **New**: `~/.dya/dya.json`

> If you have existing files, move them manually to the new directory or they will be recreated.

#### Verbosity Configuration Changed
The `verbose` boolean config has been replaced with `verbosity` string:
- **Old**: `verbose: true` or `verbose: false`
- **New**: `verbosity: silent|default|verbose|trace`

```yaml
# Before
config:
  verbose: true

# After
config:
  verbosity: verbose
```

> Backward compatibility: `verbose: true` → `verbosity: verbose`, but the validator will warn about deprecation.

### ✨ New Features

#### Cache Encryption
Cache files are now encrypted using AES-256-GCM with a machine-specific key:
- Data is tied to the machine where cache was created
- Automatic migration: plain JSON is encrypted on first save
- Export with `--dya-dump` for backup or migration

#### Verbosity Levels
Four verbosity levels for different use cases:

| Level | Description |
|-------|-------------|
| `silent` | No "Running:" hint, no dividers — minimal output |
| `default` | Standard output with "Running:" and dividers |
| `verbose` | All default + variable resolution logs, cache modifications |
| `trace` | All verbose + method timing with input/output (buffered in interactive mode) |

**Trace Mode** logs method timing and input/output for:
- **Startup**: `ConfigLoader.load`, `ConfigValidator.validate`, `CacheManager.load`
- **Execution**: `DataResolver.resolve_one`, `DataResolver._execute_dynamic_source`, `VariableResolver.resolve_app_vars`

```yaml
config:
  verbosity: trace  # For debugging
```

#### Interactive Mode Cache Management
Management flags now work in interactive mode:
```bash
dya> --dya-clear-cache
dya> --dya-set-locals key value
dya> --dya-dump
```

> Note: `--dya-config` and `--dya-cache` are NOT supported in interactive mode.

#### Indexed Access for Dicts and Dynamic Dicts
Direct position selection in data sources using bracket syntax:
```yaml
# Default (position 0)
command: echo $${db_servers.host}

# Explicit index access
command: echo $${db_servers[0].host} $${db_servers[1].host} $${db_servers[2].host}
```
Access any position in your dict/dynamic_dict data directly without list mode selection.

#### New Helper System
Completely redesigned help output with two modes:

- **Auto Helper** (`helper_type: auto`): Structured format with Description, Usage, Args, and Options/Subcommands sections
- **Custom Helper** (`helper_type: custom`): Raw concatenated helper text for custom formatting

**Dynamic Usage Display**: Usage section now shows the full matched command path with optional args and subcommands in bracket notation:
```
deep-cmd [-v | --verbose | -c | --config] [level1 [-f | --force] | status [-a | --all]]
```

#### Array Aliases for Arguments
Define multiple aliases for the same argument:
```yaml
args:
  - alias: ["-o ${file}", "--output ${file}"]
    command: -o ${file}
    helper: Output file path
  - alias: ["-v", "--verbose"]
    command: --verbose
    helper: Verbose mode
```
Both `-o` and `--output` trigger the same argument. Displayed as `-o, --output ${file}` in help.

### 🔧 Improvements

#### Enhanced Validator
- **Deprecated Config Detection**: Warns about old `verbose: true/false` usage
- **Variable Reference Validation**: Checks all dict/dynamic_dict variables are defined
- **Position Validation**: Validates indexed access syntax `$${source[N].key}`
- **Key Validation**: Ensures referenced keys exist in data sources
- **Array Alias Validation**: Verifies consistent variable structure across alias arrays

### 📚 Documentation
- New dedicated [Helper System documentation](docs/helper.md)
- Updated [Commands documentation](docs/commands.md) with array aliases
- Updated [Features documentation](docs/features.md) with verbosity levels
- Added Helper System to README documentation index

---

## [1.0.0] - 2026-01-15

🚀 **Dynamic Alias to the world!**

We're thrilled to announce the first public release of Dynamic Alias — a declarative CLI builder that transforms complex command-line workflows into simple, memorable aliases with smart autocompletion.

### What is Dynamic Alias?
Modern infrastructure professionals juggle dozens of CLI tools daily—AWS, GCP, Azure, Kubernetes, databases, and more. Dynamic Alias lets you define your workflows once in YAML and use them everywhere:

```bash
# Instead of remembering:
aws ssm start-session --target i-0abc123def456 --region us-east-1

# Just type:
dya ssm prod-web-server
```

### ✨ Key Features

- **Declarative Configuration** — Define commands, aliases, and data sources in YAML
- **Smart Autocompletion** — Tab-complete through your resources, databases, and servers
- **Dynamic Data Sources** — Fetch live data from AWS, GCP, Azure, or any CLI tool
- **Interactive Shell** — Run `dya` for a full shell experience with history navigation
- **Caching & TTL** — Reduce API calls with configurable cache expiration
- **Subcommands & Arguments** — Build complex CLI trees with nested commands
- **Custom Branding** — Create your own branded CLI tool for your organization

### 🎯 Who is this for?

- **DBAs, SREs, DBREs, DevOps engineers, and sysadmins** who work with multiple tools daily
- **Companies building internal CLIs** for their teams
- Anyone tired of memorizing instance IDs, hostnames, and complex flags

### 📦 Installation

```bash
pip install dynamic-alias
```

### 📚 Documentation

Full documentation with examples for AWS, GCP, Azure, and OCI is available on [GitHub](https://github.com/natanmedeiros/dynamic-alias).

---

**Thank you for using Dynamic Alias!** We'd love to hear your feedback and see how you're using it.

[1.1.0]: https://github.com/natanmedeiros/dynamic-alias/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/natanmedeiros/dynamic-alias/releases/tag/v1.0.0
