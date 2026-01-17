# Helper System

The helper system provides contextual documentation for commands. Dynamic Alias supports two helper types: **auto** and **custom**.

## Helper Types

### Auto (Default)

The auto helper generates a structured format with Description, Args, and Options/Subcommands sections:

```yaml
---
type: command
name: Database Connect
alias: db $${databases.name}
command: psql -h $${databases.host} -U $${databases.user}
helper_type: auto  # Default, can be omitted
helper: Connect to a PostgreSQL database
args:
  - alias: ["-o ${file}", "--output ${file}"]
    command: -o ${file}
    helper: Output log file path
sub:
  - alias: query ${sql}
    command: -c "${sql}"
    helper: Run a SQL query
```

**Output** (`dya db production -h`):
```
db production

    Description:
        Connect to a PostgreSQL database

    Usage:
        db production [-o | --output] [query ${sql}]

    Args:
        -o, --output ${file}    Output log file path

    Options/Subcommands:
        query ${sql}

            Description:
                Run a SQL query

            Usage:
                db production query ${sql}
```

The **Usage** section shows:
- **Matched path**: `db production` - what you typed to get here
- **Optional args**: `[-o | --output]` - available argument flags
- **Optional subs**: `[query ${sql}]` - available subcommands with their args recursively

### Custom

Custom helper displays the raw helper text exactly as defined, concatenated from the matched command chain:

```yaml
---
type: command
name: Deploy
alias: deploy
command: ./deploy.sh
helper_type: custom
helper: |
  DEPLOY TOOL
  ===========
  Deploys the application to the specified environment.
  
  Usage:
    dya deploy <environment>
```

**Output** (`dya deploy -h`):
```
DEPLOY TOOL
===========
Deploys the application to the specified environment.

Usage:
  dya deploy <environment>
```

## Args with Multiple Aliases

Arguments can define multiple aliases using an array. All aliases must have the **same variable structure**:

```yaml
args:
  - alias: ["-o ${filename}", "--output ${filename}"]
    command: -o ${filename}
    helper: Specify output file

  - alias: ["-v", "--verbose"]
    command: --verbose
    helper: Enable verbose output
```

In helper output, array aliases are combined with commas:
```
Args:
    -o, --output ${filename}    Specify output file
    -v, --verbose               Enable verbose output
```

> [!IMPORTANT]
> **Validation**: All aliases in an array must have identical variables in the same order.
> - ✅ Valid: `["-o ${file}", "--output ${file}"]`
> - ❌ Invalid: `["-o ${file}", "--output"]`

## Global Help

Running `dya -h` or `dya --help` displays the global help, which lists all dicts, dynamic_dicts, and commands. This is unaffected by `helper_type`.

---

| ← Previous | Next → |
|:-----------|-------:|
| [Commands](commands.md) | [Features](features.md) |
