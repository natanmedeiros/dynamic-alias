# Dynamic Alias (`dya`)

![Wheel Build](https://img.shields.io/badge/Wheel-passing-brightgreen)
![MacOS Build](https://img.shields.io/badge/MacOS-pending-yellow)
![Deb Build](https://img.shields.io/badge/Deb-pending-yellow)
![RPM Build](https://img.shields.io/badge/RPM-pending-yellow)


> [!CAUTION]
> **UNDER DEVELOPMENT**
>
> This project is currently in **active development** and is **not ready for production use**.
> Although many features are functional, breaking changes may occur at any time.

Dynamic Alias is a powerful CLI application that allows users to create "aliases with superpowers". It transforms complex command-line interactions into simple, autocompletable shortcuts, leveraging dynamic data sources and structured configurations.

## Features

-   **Superpowered Aliases**: Define aliases that map to complex commands.
-   **Dynamic Data**: Use output from external commands (e.g., AWS, Redis) as data sources for your aliases.
-   **Smart Autocomplete**: Context-aware autocompletion for commands, subcommands, arguments, and dynamic data values.
-   **Variable Support**:
    -   **User Input Variables** (`${var}`): Placeholders that you fill in during execution.
    -   **Application Variables** (`$${source.key}`): Values automatically populated from your dynamic data sources.
    -   **Environment Variables** (`$${env.VAR}`): Integration with system environment variables.
-   **Interactive Shell**: A robust shell environment (`dya >`) with menu-based completion.

## System Requirements

-   Python 3.8+
-   Configuration file: `dya.yaml` (default at `~/.dya.yaml` or current directory)

## Configuration (`dya.yaml`)

The application is driven by a YAML configuration file that defines three main structures: **Dict**, **Dynamic Dict**, and **Command**.

### 1. Variables Syntax
-   `$${variable}`: Application variable (from Dynamic Dicts or Environment).
-   `${variable}`: User input variable (you type the value).

### 2. Dict (Static Data)
Defines static key-value lists.
```yaml
---
type: dict
name: application_servers
data:
  - name: app1
    host: 192.168.1.10
    port: 8080
```

### 3. Dynamic Dict (Dynamic Data)
Fetches data by executing a shell command. The output must be JSON.
```yaml
---
type: dynamic_dict
name: redis_servers
priority: 1
command: |
  aws elasticache describe-cache-clusters --output json ...
mapping:
  name: CacheClusterId
  host: Endpoint.Address
```

### 4. Command (The Alias)
Defines the executable command, its structure, and arguments.

```yaml
---
type: command
name: PostgreSQL Client
alias: pg $${database_servers.name} # Uses dynamic variable
command: psql -h $${database_servers.host} ...
helper: |
    Connects to a database.
args:
  - alias: -o ${filename} # Argument with user variable
    command: -o ${filename}
    helper: Output to file
sub:
  - alias: file ${filename} # Subcommand
    command: -f ${filename}
```

## Installation and Building

### Python Wheel
To build and install the package via pip:

```bash
# Build
python -m build

# Install (Local)
pip install .
```

### Debian/Ubuntu (APT)
To build a `.deb` package:

```bash
# Requires stdeb
pip install stdeb fakeroot

# Build
python3 setup.py --command-packages=stdeb.command bdist_deb

# Install
sudo dpkg -i deb_dist/python3-dynamic-alias_*.deb
# or
sudo apt install ./deb_dist/python3-dynamic-alias_*.deb
```

### Fedora/RHEL (DNF/RPM)
To build an `.rpm` package:

```bash
# Copy source to rpmbuild SOURCES
python setup.py sdist
cp dist/dynamic-alias-0.1.0.tar.gz ~/rpmbuild/SOURCES/

# Build
rpmbuild -ba packaging/rpm/dynamic-alias.spec

# Install
sudo dnf install ~/rpmbuild/RPMS/noarch/dynamic-alias-*.noarch.rpm
```

### MacOS
#### Homebrew
```bash
brew install packaging/macos/homebrew/dynamic-alias.rb
```

#### PKG Installer
To generate a `.pkg` installer (requires macOS):
```bash
./packaging/macos/scripts/build_pkg.sh
```

## Usage

1.  **Start the shell**:
    ```bash
    dya
    ```
2.  **Type a command**:
    ```text
    dya > pg db1 -o my_output.txt
    ```
