# Commands

Commands define the aliases you type and the shell commands they execute.

## Basic Structure

```yaml
---
type: command
name: Greeting
alias: hello
command: echo 'Hello, World!'
```

Usage:
```bash
dya hello
# Executes: echo 'Hello, World!'
```

## Required Fields

| Field | Description |
|-------|-------------|
| `type` | Must be `command` |
| `name` | Human-readable name (shown in help) |
| `alias` | What you type to trigger the command |
| `command` | Shell command to execute |

## Optional Fields

| Field | Default | Description |
|-------|---------|-------------|
| `helper` | - | Help text for `-h/--help` |
| `strict` | `false` | Reject extra arguments |
| `timeout` | `0` | Execution timeout (0 = no limit) |
| `set-locals` | `false` | Capture output as local variables |
| `sub` | - | Subcommands |
| `args` | - | Optional arguments/flags |

## User Variables

Capture user input with `${variable}`:

```yaml
---
type: command
name: Ping Host
alias: ping ${hostname}
command: ping -c 4 ${hostname}
```

Usage:
```bash
dya ping google.com
# Executes: ping -c 4 google.com
```

## Application Variables

Reference dicts/dynamic_dicts with `$${source.key}`:

```yaml
---
type: command
name: Connect Database
alias: db $${databases.name}
command: psql -h $${databases.host} -U $${databases.user} -d $${databases.dbname}
```

Usage:
```bash
dya db production
# Executes: psql -h db.prod.internal -U app -d main
```

> [!TIP]
> **Indexed Access**: Use `$${source[N].key}` to access a specific position. Positions are **0-indexed**.
> - `$${dict.key}` = position 0 (default)
> - `$${dict[1].key}` = position 1 (second item)
> 
> See [Static Dicts](dicts.md#indexed-access) for detailed examples.

## Local Variables

Reference stored local variables with `$${locals.key}`:

```yaml
---
type: command
name: Show Environment
alias: show-env
command: echo "Current environment is: $${locals.env}"
```

### Setting Locals from Command Output

Use `set-locals: true` to capture JSON output and store it as local variables:

```yaml
---
type: command
name: Load Config
alias: load-config
set-locals: true
command: python get_config.py
helper: Loads configuration into locals
```

If `get_config.py` outputs:
```json
{"env": "production", "region": "us-east-1"}
```

Then `dya load-config` will store `env` and `region` in the locals cache, making them available for future commands.

> [!NOTE]
> **Persistence**: Local variables are stored in the application cache file (e.g., `~/.dya.json`) and **persist between sessions**. They do not expire and are only removed if explicitly cleared via `dya --dya-clear-locals` or `dya --dya-clear-all`.

## Subcommands

Nest commands with `sub`:

```yaml
---
type: command
name: Docker
alias: d
command: docker
helper: |
  Docker shortcuts
sub:
  - alias: ps
    command: ps -a
    helper: List all containers
  - alias: logs ${container}
    command: logs -f ${container}
    helper: Follow container logs
  - alias: exec ${container}
    command: exec -it ${container} /bin/bash
    helper: Shell into container
```

Usage:
```bash
dya d ps              # docker ps -a
dya d logs web        # docker logs -f web
dya d exec web        # docker exec -it web /bin/bash
```

## Arguments (Flags)

Define optional flags with `args`:

```yaml
---
type: command
name: List Files
alias: ls
command: ls
args:
  - alias: -l
    command: -l
    helper: Long format
  - alias: -a
    command: -a
    helper: Show hidden files
  - alias: -h
    command: -h
    helper: Human-readable sizes
```

Usage:
```bash
dya ls -l -a          # ls -l -a
```

### Array Aliases

Arguments can define multiple aliases using an array:

```yaml
args:
  - alias: ["-o ${file}", "--output ${file}"]
    command: -o ${file}
    helper: Specify output file
  - alias: ["-v", "--verbose"]
    command: --verbose
    helper: Enable verbose mode
```

Both `-o` and `--output` will trigger the same arg. See [Helper System](helper.md) for display format.

> [!IMPORTANT]
> Arguments are **scoped to their parent** command or subcommand. An `arg` defined on a parent command cannot be used after a subcommand. Args must always be at the same level as their parent.
>
> ```bash
> # ✓ Correct: -v is an arg of root command
> dya deploy -v prod
>
> # ✗ Invalid: -v cannot come after subcommand 'prod'
> dya deploy prod -v    # -v won't be recognized as root arg
> ```

## Recursive Subcommands

Subcommands can have their own subcommands:

```yaml
---
type: command
name: Kubernetes
alias: k
command: kubectl
sub:
  - alias: get
    command: get
    sub:
      - alias: pods
        command: pods
      - alias: svc
        command: services
      - alias: deploy
        command: deployments
  - alias: describe
    command: describe
    sub:
      - alias: pod ${name}
        command: pod ${name}
```

Usage:
```bash
dya k get pods        # kubectl get pods
dya k describe pod web # kubectl describe pod web
```

## Helper Text

Helper text can be used at **any level**: root commands, subcommands, and arguments.

```yaml
---
type: command
name: Deploy
alias: deploy
command: ./deploy.sh
helper: Deploy application to environment  # Root helper
sub:
  - alias: $${environments.name}
    command: --env $${environments.name}
    helper: Deploy to specific environment  # Subcommand helper
    args:
      - alias: --force
        command: --force
        helper: Skip confirmation prompts  # Argument helper
```

View help at any level:
```bash
dya deploy -h           # Shows root helper
dya deploy prod -h      # Shows subcommand helper
```

> [!NOTE]
> The `-h` or `--help` flag shows the helper text for the **entire matched command chain**. If you type `dya deploy prod --force -h`, it will show helpers from the root command, through the subcommand, down to the argument level, based on what was matched.

## Arguments in Subcommands

Subcommands can have their own `args`:

```yaml
---
type: command
name: Git Shortcuts
alias: g
command: git
sub:
  - alias: commit
    command: commit
    helper: Create a commit
    args:
      - alias: -m ${message}
        command: -m "${message}"
        helper: Commit message
      - alias: --amend
        command: --amend
        helper: Amend previous commit
  - alias: push
    command: push
    args:
      - alias: --force
        command: --force
        helper: Force push
      - alias: -u ${remote}
        command: -u ${remote}
        helper: Set upstream
```

Usage:
```bash
dya g commit -m "fix bug"      # git commit -m "fix bug"
dya g commit --amend           # git commit --amend
dya g push --force             # git push --force
dya g push -u origin           # git push -u origin
```

## Multiline vs Single Line

Both `command` and `helper` support single line and multiline syntax.

### Single Line

```yaml
alias: hello
command: echo 'Hello World'
helper: Simple greeting command
```

### Multiline (using `|`)

Use YAML's `|` for multiline content:

```yaml
alias: setup
command: |
  echo "Starting setup..."
  ./install-deps.sh
  ./configure.sh
  echo "Setup complete!"
helper: |
  Description:
    Run full environment setup
  
  Steps:
    1. Install dependencies
    2. Configure application
    3. Verify installation
```

> [!TIP]
> Use multiline `command` for complex shell scripts. Use multiline `helper` for detailed documentation with sections.

> [!WARNING]
> **Colon (`:`) in Commands**: If your command contains a colon followed by a space (`: `) (e.g., in JSON arguments or scripts), standard YAML parsers will misinterpret it as a key-value pair.
>
> **Solution**: Use **multi-line syntax (`|`)** for commands containing colons.
>
> **Incorrect:** `command: echo '{"k": "v"}'`
> **Correct:**
> ```yaml
> command: |
>   echo '{"k": "v"}'
> ```

---

| ← Previous | Next → |
|:-----------|-------:|
| [Dynamic Dicts](dynamic-dicts.md) | [Helper System](helper.md) |
