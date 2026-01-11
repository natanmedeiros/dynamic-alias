---
trigger: always_on
---

# Config File Rules

This file defines the rules for creating a new `dya.yaml` or user-defined config file. These rules are derived from `global-system-rules.md` and implicit patterns in `dya.yaml`.

## 1. File Structure
1.  **Format**: The file must be valid YAML.
2.  **Separators**: Use `---` to separate each block definition.
3.  **Indentation**: Use 2 spaces.

## 2. Variable Syntax
1.  **User Input**: Use ` ${variable_name} ` for values the user must provide via CLI (e.g., ` ${filename} `).
    - Used in `alias` to define expected input.
    - Used in `command` to insert the input.
2.  **Internal/Config Variables**: Use ` $ ` for values referenced from the configuration itself.
    - **Dict Reference**: ` $ ` (e.g., ` $ `).
    - **Environment**: ` $ ` to access OS environment variables.

## 3. Reference Logic
1.  **Dict/DynamicDict References**:
    - Dicts and Dynamic Dicts can reference other Dicts/Dynamic Dicts.
    - **Condition**: The referencing block must have a **higher priority** number than the referenced block.
      - `Referencing.Priority > Referenced.Priority`
2.  **Command References**:
    - Commands can reference any Dict or Dynamic Dict regardless of priority.

## 4. Block Definitions

### 4.1 Dict (`type: dict`)
Used for static lists of resources.
*   **Required Fields**: `type: dict`, `name`, `data`.
*   **Data**: A list of key-value pairs (static data).

### 4.2 Dynamic Dict (`type: dynamic_dict`)
Used for fetching resources dynamically from external tools (AWS, Azure, etc.).
*   **Required Fields**: `type: dynamic_dict`, `name`, `command`, `mapping`.
*   **Optional Fields**: `priority` (default 1), `timeout` (default 10s).
*   **Command**: A shell command that outputs JSON.
*   **Mapping**: Maps the JSON output keys (values) to internal keys (keys).
    - Format: `internal_key: json_key`

### 4.3 Command (`type: command`)
Defines a CLI command.
*   **Required Fields**: `type: command`, `name`, `alias`, `command`.
*   **Optional Fields**: `helper`, `sub`, `args`, `timeout`.
*   **Alias**: Defines the command signature.
    - Can contain static words and user variables (e.g., `sync ${source} ${dest} `).
    - Can use dict variables to create dynamic commands (e.g., `pg $ `).
*   **Command**: The actual shell execution string. Uses the variables defined in `alias`.
*   **Helper**: A multiline string (`|`) describing the command.
    - **Standard Format**:
        `yaml
        helper: |
          Description:
            <Text>
          Usage:
            <cli_name> <alias_signature>
          Options:
            <option_description>
        `

## 5. Subcommands and Arguments

### 5.1 Subcommands (`sub`)
*   **Structure**: A list of objects with the same structure as a top-level Command (alias, command, helper, sub, args).
*   **Recursion**: Supports infinite nesting.
*   **Scope**: Inherits variables from parent commands.

### 5.2 Arguments (`args`)
*   **Purpose**: For flags or optional modifiers (e.g., `-v`, `--output ${file} `).
*   **Structure**: List of objects with `alias`, `command`, `helper`.
*   **Constraint**: Non-recursive (cannot have `sub` or `args`).

## Declarative Metadata
config:
    style-completion: "bg:#008888 #ffffff"
    style-completion-current: "bg:#00aaaa #000000"
    style-scrollbar-background: "bg:#88aaaa"
    style-scrollbar-button: "bg:#222222"
    style-placeholder-color: "gray"
    style-placeholder-text: "(tab for menu)"

--- # New config block
type: dict
name: # "Dict name"
data: # Items list
  - name: # First custom item key 'name'
    host: # First custom item key 'host'
    port: # First custom item key 'port'
    user: # First custom item key 'user'
    dbname: # First custom item key 'dbname'
  - name: # Second custom item key 'name'
    host: # Second custom item key 'host'
    port: # Second custom item key 'port'
    user: # Second  custom item key 'user'
    dbname: # Second custom item key 'dbname'

---
type: dynamic_dict
name: # "Dict name"
priority: [0-1000] # Dict execution priority for nested usage
cache-ttl: # Time to live in seconds, default 300s
command: # Multi-line command when init with "|" or single line command when missing "|"
mapping: # Mapping from command result keys to internal keys
  custom_internal_key1: command_output_key1
  custom_internal_key2: command_output_key2

---
type: command
name: # Command name
strict: # Default false. If false, user can input text to be concat at the end of matched generated command, e.g. alias is only "pg server" and produces "psql server", but user inputs "pg server --output teste", strict false accepts and concats at the and of command as "psql server --output teste", but when strict true, it will be rejected returning as invalid command with not recognized text between double quotes like "--output teste".
alias: # Alias to trigger command, e.g. pg $
command: # Multi-line command when init with "|" or single line command when missing "|" that will be executed when calls alias, e.g. psql -h $ -p $ -U $ -d $
timeout: # Command execution timeout, default 0
helper: # Multi-line helper message when init with "|" or single line helper message when missing "|"
args: # Command args list
  - alias: # Alias to trigger command args, e.g. -o ${output_filename}
    command: # Multi-line command when init with "|" or single line command when missing "|" that will be executed when calls alias, e.g. -o ${output_filename}
    helper: # Multi-line helper message when init with "|" or single line helper message when missing "|"
  - alias: # Alias to trigger command args, e.g. -v
    command: # Multi-line command when init with "|" or single line command when missing "|" that will be executed when calls alias, e.g. -v
    helper:  # Multi-line helper message when init with "|" or single line helper message when missing "|"
sub: # Subcommand list
  - alias: # Alias to trigger subcommand, e.g. file ${filename}
    command: # Multi-line command when init with "|" or single line command when missing "|" that will be executed when calls alias subcommand, e.g. -f ${filename}
    helper: # Multi-line helper message when init with "|" or single line helper message when missing "|"
  - alias: # Alias to trigger subcommand, e.g. cmd ${sql_text}
    command:  # Multi-line command when init with "|" or single line command when missing "|" that will be executed when calls alias subcommand, e.g. -c "${sql_text}"
    helper: # Multi-line helper message when init with "|" or single line helper message when missing "|"
    args: # Subcommand can have args with same structure as commands
    sub: # Subcommand are recursive with same structure
      - alias: # Alias to trigger subcommand, e.g. export_log ${s3_bucket}
        command:  # Multi-line command when init with "|" or single line command when missing "|" that will be executed when calls alias subcommand, e.g. | aws s3 cp ${filename} s3://${s3_bucket}/
        helper: # Multi-line helper message when init with "|" or single line helper message when missing "|"