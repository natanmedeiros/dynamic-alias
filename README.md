<p align="center">
  <img src="docs/dynamic-alias.png" alt="Dynamic Alias" width="40%">
</p>

# Dynamic Alias (dya)

A declarative CLI builder that transforms complex command-line workflows into simple, memorable aliases with smart autocompletion.

## Why Dynamic Alias?

Modern infrastructure professionals juggle dozens of CLI tools daily—AWS, GCP, Azure, Kubernetes, databases, and more. Each tool has its own syntax, flags, and resource identifiers. **Dynamic Alias** lets you define once, use everywhere:

```bash
# Instead of remembering:
aws ssm start-session --target i-0abc123def456 --region us-east-1

# Just type:
dya ssm prod-web-server
```

## Quick Start

```bash
# Install
pip install dynamic-alias

# Create ~/.dya.yaml
echo "
config:
  history-size: 100

---
type: command
name: Hello World
alias: hello
command: echo 'Hello from Dynamic Alias!'
" > ~/.dya.yaml

# Run
dya hello
```

## Documentation

| Topic | Description |
|-------|-------------|
| [Getting Started](docs/getting-started.md) | Installation, first config, running |
| [Configuration](docs/configuration.md) | YAML structure, config block, styles |
| [Static Dicts](docs/dicts.md) | Defining static data sources |
| [Dynamic Dicts](docs/dynamic-dicts.md) | Fetching data from external commands, caching, TTL |
| [Commands](docs/commands.md) | Aliases, subcommands, arguments |
| [Features](docs/features.md) | Strict mode, timeout, history |
| [Interactive Mode](docs/interactive-mode.md) | Shell, autocomplete, history navigation |

## Examples

Real-world configurations for cloud providers:

| Example | Description |
|---------|-------------|
| [AWS](docs/examples/aws/) | SSO login, SSM sessions, RDS PostgreSQL, ElastiCache |
| [GCP](docs/examples/gcp/) | gcloud auth, Compute SSH, Cloud SQL, Memorystore |
| [Azure](docs/examples/azure/) | az login, VM SSH, PostgreSQL, Redis Cache |
| [OCI](docs/examples/oci/) | oci session, Compute SSH, Autonomous DB, Redis |
| [Custom CLI](docs/examples/custom-cli/) | Building your own branded CLI |

## Use Cases

### Infrastructure Professionals
DBAs, SREs, DBREs, and DevOps engineers who work with multiple tools and dozens of resources daily. Stop memorizing instance IDs—let Dynamic Alias remember them for you.

### Companies Building Internal CLIs
Create a declarative, customizable CLI for your organization. Define your company's resources in YAML and distribute a branded tool to your teams.

## Roadmap

- [ ] **OS Package Publishing** - Debian (.deb), RPM, Windows installer
- [ ] **Python Package Publication** - PyPI release
- [ ] **Homebrew Publication** - macOS/Linux via Homebrew

## License

MIT License - See [LICENSE](LICENSE) for details.
