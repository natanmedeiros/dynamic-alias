# Interactive Mode

Launch the interactive shell for autocomplete and history navigation.

## Starting the Shell

```bash
dya
```

You'll see:
```
dya> (tab for menu)
```

## Autocomplete

Press **Tab** to see available completions:

```
dya> <TAB>
      hello
      ssh
      pg
      k
```

### Smart Completion

Autocomplete works at every level:

```
dya> ssh <TAB>
          prod
          staging
          dev

dya> k get <TAB>
            pods
            services
            deployments
```

### Dynamic Data

Dynamic dict values are autocompleted:

```
dya> pg <TAB>
          production
          staging
          analytics
```

## History Navigation

Use arrow keys to navigate command history:

| Key | Action |
|-----|--------|
| ↑ (Up) | Previous command |
| ↓ (Down) | Next command |

History persists across sessions in the cache file.

## Styling

Customize the appearance:

```yaml
config:
  style-completion: "bg:#008888 #ffffff"
  style-completion-current: "bg:#00aaaa #000000"
  style-scrollbar-background: "bg:#88aaaa"
  style-scrollbar-button: "bg:#222222"
  style-placeholder-color: "gray"
  style-placeholder-text: "(type command)"
```

## Help

Get help at any point:

```
dya> -h
# Shows global help with all dicts and commands

dya> ssh -h
# Shows help for 'ssh' command
```

## Shell Mode

Enable shell mode to execute unrecognized commands directly in the system shell:

```yaml
config:
  shell: true
```

### Behavior

With shell mode **enabled**:
- Recognized commands → execute as defined in config
- Unrecognized commands → execute directly in shell

```
dya> simple           # Recognized: executes defined command
Running: echo simple

dya> date             # Unrecognized: executes in shell
Mon Jan 13 22:00:00 -03 2026

dya> ls -la           # Any shell command works
total 48
drwxr-xr-x  5 user user 4096 Jan 13 22:00 .
...
```

### Use Cases

- Quick one-off shell commands without leaving dya
- Hybrid workflow: aliases + direct shell access
- Testing and debugging

> [!NOTE]
> Shell mode is disabled by default. When disabled, unrecognized commands show "Invalid command."

### Path Completion

Enable system command completion for shell mode:

```yaml
config:
  shell: true
  path-completion: true
```

With path completion enabled:
- Press Tab on unrecognized text to complete to system commands
- Completes to the first matching command from PATH (inline, not dropdown)
- Only works at the first word of the command line

```
dya> ech<TAB>
dya> echo           # Completed inline

dya> git<TAB>
dya> git            # Completed inline
```

> [!TIP]
> Path completion is useful when you frequently use shell mode to run system commands.
> It provides quick completion without showing a dropdown menu.

## Exiting

Exit the shell:

```
dya> exit
# or press Ctrl+C / Ctrl+D
```

## Non-Interactive Execution

Run commands directly without entering the shell:

```bash
dya ssh prod
dya pg production
dya k get pods
```

The command executes and returns to your normal shell.

---

| ← Previous | Next → |
|:-----------|-------:|
| [Features](features.md) | [Examples](examples/) |
