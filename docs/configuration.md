# Configuration Reference

## File Structure

Dynamic Alias uses YAML with document separators (`---`) to define blocks:

```yaml
config:
  # Global settings

---
type: dict
# Static data

---
type: dynamic_dict
# Dynamic data from commands

---
type: command
# Aliases and commands
```

## Config Block

The config block defines global settings. It can be defined two ways:

### Implicit (Recommended)
```yaml
config:
  style-completion: "bg:#008888 #ffffff"
  history-size: 100
```

### Explicit
```yaml
---
type: config
style-completion: "bg:#008888 #ffffff"
history-size: 100
```

## Config Options

| Option | Default | Description |
|--------|---------|-------------|
| `style-completion` | `bg:#008888 #ffffff` | Completion menu colors |
| `style-completion-current` | `bg:#00aaaa #000000` | Selected item colors |
| `style-scrollbar-background` | `bg:#88aaaa` | Scrollbar background |
| `style-scrollbar-button` | `bg:#222222` | Scrollbar button |
| `style-placeholder-color` | `gray` | Placeholder text color |
| `style-placeholder-text` | `(tab for menu)` | Placeholder hint |
| `history-size` | `20` | Max commands in history (max: 1000) |
| `verbose` | `false` | Enable verbose logging |

### Verbose Mode

When `verbose: true` is set, the application outputs diagnostic information:

```yaml
config:
  verbose: true
```

**Output includes:**
- Configuration file path loaded
- Cache file path (loaded or created)
- Number of history entries loaded
- Dynamic dict execution times
- Dynamic dict cache hits

**Example output:**
```
[VERBOSE] Loaded configuration from: ~/.dya.yaml
[VERBOSE] Loaded cache from: ~/.dya.json
[VERBOSE] Loaded 5 history entries
dya > dyn node-1
[VERBOSE] Executed dynamic_dict 'mock_nodes' in 0.13s
Running: echo dyn 10.0.0.1
```

> [!NOTE]
> Style parameters follow the [prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/en/master/pages/advanced_topics/styling.html) styling format. Use CSS-like syntax with `bg:` for background colors and color names or hex values for foreground.

## Variable Syntax

### User Input Variables
Variables the user provides via CLI:
```yaml
alias: connect ${hostname}
command: ssh ${hostname}
```

### Application Variables  
References to dicts/dynamic_dicts:
```yaml
alias: pg $${databases.name}
command: psql -h $${databases.host} -U $${databases.user}
```

### Environment Variables
Access OS environment:
```yaml
command: echo $${env.HOME}
---

| ← Previous | Next → |
|:-----------|-------:|
| [Getting Started](getting-started.md) | [Static Dicts](dicts.md) |
