# Features

## Strict Mode

By default, extra arguments are appended to the command. Enable `strict: true` to reject them.

### Default Behavior (strict: false)

```yaml
---
type: command
name: Echo
alias: echo
command: echo hello
strict: false  # Default
```

```bash
dya echo world
# Executes: echo hello world
```

### Strict Mode (strict: true)

```yaml
---
type: command
name: Exact Command
alias: exact
command: echo 'This is exact'
strict: true
```

```bash
dya exact extra args
# Error: Strict mode enabled. Unknown arguments: "extra args"
```

## Timeout

Set execution time limits to prevent hanging commands.

### Command Timeout

```yaml
---
type: command
name: Long Task
alias: task
command: ./long-running-script.sh
timeout: 60  # 60 seconds
```

If the command exceeds the timeout:
```
Error: Command timed out after 60s
```

### Dynamic Dict Timeout

```yaml
---
type: dynamic_dict
name: slow_api
timeout: 30
command: curl -s https://api.example.com/slow
mapping:
  id: id
```

## History

Command history is stored in the cache file and persists across sessions.

### Configuration

```yaml
config:
  history-size: 100  # Max 1000
```

### Storage

History is stored in the cache file:
```json
{
  "_history": [
    "pg production",
    "ssh web-server",
    "k get pods"
  ]
}
```

### Behavior

- **Create**: If `_history` doesn't exist, it's created
- **Append**: New commands are appended
- **Shift**: When exceeding `history-size`, oldest entries are removed

### Navigation

In interactive mode, use arrow keys:
- **↑ (Up)**: Previous command
- **↓ (Down)**: Next command

## Cache TTL

Dynamic dict results are cached with time-to-live:

```yaml
---
type: dynamic_dict
name: instances
cache-ttl: 600  # 10 minutes
command: aws ec2 describe-instances --output json
mapping:
  id: InstanceId
```

### Cache Behavior

1. **First call**: Executes command, caches result with timestamp
2. **Within TTL**: Returns cached data (no execution)
3. **After TTL**: Re-executes command, updates cache

### Cache File Structure

```json
{
  "instances": {
    "timestamp": 1704067200,
    "data": [
      {"id": "i-abc123", "name": "prod-web"}
    ]
  }
}
```

### Cache Management Flags

Manage your cache with these flags:

| Flag | Description |
|------|-------------|
| `--dya-clear-cache` | Remove cached dynamic dict data (keeps history) |
| `--dya-clear-history` | Clear command history |
| `--dya-clear-all` | Delete entire cache file |
| `--dya-dump` | Print decrypted cache as JSON |

**Examples:**

```bash
# Clear dynamic dict cache (useful after updating sources)
dya --dya-clear-cache
# Output: Cleared 5 cache entries (history preserved)

# Clear command history
dya --dya-clear-history
# Output: Command history cleared

# Delete entire cache file (fresh start)
dya --dya-clear-all
# Output: Cache file deleted: ~/.dya/dya.json
```

> [!NOTE]
> Expired cache entries are automatically purged when loading the cache, based on each dynamic dict's `cache-ttl` setting.

### Interactive Mode Support

Management flags also work in interactive mode:

```bash
dya> --dya-clear-cache
Cleared 5 cache entries (history preserved)

dya> --dya-set-locals mykey myvalue
Local variable set: mykey=myvalue

dya> --dya-dump
{
  "_history": ["cmd1", "cmd2"],
  "_locals": {"mykey": "myvalue"}
}
```

> [!WARNING]
> The `--dya-config` and `--dya-cache` flags are NOT supported in interactive mode. Use them when starting from command line.

## Locals Management

Store and manage local variables for use in your commands. Locals persist across sessions in the cache file.

For full details, see [Locals Management Coverage](locals.md).

- **Set local:** `dya --dya-set-locals <key> <value>`
- **Clear locals:** `dya --dya-clear-locals`
- **Use in command:** `echo $${locals.key}`

## Environment Variables

Access OS environment variables:

```yaml
---
type: command
name: Home Dir
alias: home
command: cd $${env.HOME} && ls
```

## Config Validator

Validate your configuration file for errors before use.

### Manual Validation

Run the validator with full output:

```bash
dya --dya-validate
# Or with custom config:
dya --dya-validate --dya-config ./path/to/config.yaml
```

**Example output:**
```
============================================================
  Configuration Validator (dya)
============================================================

  Config: ./dya.yaml

  VALIDATION CHECKLIST
  ----------------------------------------
  [✓] Config file exists: ./dya.yaml
  [✓] Valid YAML syntax
  [✓] Config block has valid keys
  [✓] All dict/dynamic_dict references are valid

  ----------------------------------------
  SUMMARY
  ----------------------------------------

  ✓ All 4 checks passed!

  Configuration is valid.
============================================================
```

### Automatic Silent Validation

At startup (interactive and non-interactive modes), the config is automatically validated. If errors are found, they are displayed and execution stops:

```
[DYA] Configuration errors found in: ./config.yaml
--------------------------------------------------
  ✗ command 'my_command' references undefined source: 'undefined_dict'
    Location: Block 3
    Hint: Define a dict or dynamic_dict named 'undefined_dict'
--------------------------------------------------
Fix the 1 error(s) above or run 'dya --dya-validate' for full report.
```

### What is Validated

| Check | Description |
|-------|-------------|
| **File exists** | Config file must exist |
| **Valid YAML** | Syntax must be correct |
| **Required fields** | Each block type must have required fields |
| **Config keys** | Only valid keys in config block |
| **References** | All `$${source.key}` must reference defined sources |

## Cache Encryption

Cache data is automatically encrypted.

### How It Works

The cache file is encrypted using AES-256-GCM with a machine-specific key.

### Automatic Migration

Existing plain JSON cache files are automatically encrypted on the first save after upgrading.

### Encrypted Cache Structure

```json
{
  "_crypt": "base64-encoded-encrypted-data..."
}
```

> [!WARNING]
> **Data is tied to this machine.** If you reinstall your operating system or copy the cache file to another machine, encrypted data will become inaccessible. This only affects cached dynamic dict data, history, and locals — not your configuration file.

### Viewing Cache Contents

To view the decrypted cache contents:

```bash
dya --dya-dump
```

This outputs the cache as plain JSON, useful for debugging or backup purposes.

### Migrating Cache to Another Machine

To transfer cache data to another machine:

1. **Export** the cache as plain JSON:
   ```bash
   dya --dya-dump > cache-backup.json
   ```

2. **Copy** `cache-backup.json` to the new machine.

3. **Place** the file at the default cache location:
   - `~/.dya/dya.json` (or your custom shortcut directory)

4. **Run any command** — the application will automatically detect the plain JSON and re-encrypt it with the new machine's key on first save.

## Verbosity Levels

Control the amount of output with the `verbosity` configuration option.

### Configuration

```yaml
config:
  verbosity: verbose  # silent | default | verbose | trace
```

### Available Levels

| Level | Description |
|-------|-------------|
| `silent` | No "Running:" hint, no dividers — minimal output |
| `default` | Standard output with "Running:" and dividers |
| `verbose` | All default + variable resolution logs, cache modifications |
| `trace` | All verbose + method timing with input/output |

### Examples

**Silent Mode** — Ideal for scripting:
```yaml
config:
  verbosity: silent
```
```bash
dya simple
# Output: simple (no "Running: echo simple" prefix)
```

**Verbose Mode** — Shows what's happening:
```yaml
config:
  verbosity: verbose
```
```
[VERBOSE] Loaded configuration from: ~/.dya/dya.yaml
[VERBOSE] Loaded cache from: ~/.dya/dya.json
[VERBOSE] Resolved $${servers.host} = '192.168.1.1' (from context)
Running: ping 192.168.1.1
------------------------------
```

**Trace Mode** — Full debugging with method timing:
```yaml
config:
  verbosity: trace
```

**Startup traces:**
```
[TRACE] ConfigLoader.load (0.0123s)
  Input: {"path": "./tests/dya.yaml"}
  Output: "15 commands, 3 dicts, 2 dynamic_dicts"
[TRACE] ConfigValidator.validate (0.0045s)
  Input: {"path": "./tests/dya.yaml"}
  Output: "passed"
[TRACE] CacheManager.load (0.0089s)
  Input: {"path": "~/.dya/dya.json", "existed": true}
  Output: "5 history entries"
```

**Execution traces:**
```
[TRACE] DataResolver._execute_dynamic_source (0.4023s)
  Input: {"name": "dynamic_nodes", "command": "powershell -NoProfile -Comma..."}
  Output: "2 items"
[TRACE] VariableResolver.resolve_app_vars (0.5512s)
  Input: {"template": "echo $${dynamic_nodes.ip}", "variables": {...}}
  Output: "echo 10.0.0.1"
```

> **Note**: In interactive mode, trace logs are buffered and printed after command execution to avoid breaking the prompt.

### Migration from `verbose`

The old `verbose: true/false` is deprecated. Use `verbosity` instead:

| Old | New |
|-----|-----|
| `verbose: true` | `verbosity: verbose` |
| `verbose: false` | `verbosity: default` |

> The validator will warn if you're using the deprecated `verbose` key.

## BOM Handling

Config files with UTF-8 BOM (Byte Order Mark) are automatically handled. This ensures compatibility with files created by Windows editors.

---

| ← Previous | Next → |
|:-----------|-------:|
| [Helper System](helper.md) | [Interactive Mode](interactive-mode.md) |


