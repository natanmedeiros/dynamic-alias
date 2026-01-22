# Static Dicts

Static dicts define fixed data that doesn't change at runtime. Use them for configuration values, server lists, or any static reference data.

## Basic Structure

```yaml
---
type: dict
name: servers
data:
  - name: web-prod
    host: 10.0.1.10
    port: 22
  - name: web-staging
    host: 10.0.2.10
    port: 22
  - name: db-prod
    host: 10.0.1.20
    port: 5432
```

## Required Fields

| Field | Description |
|-------|-------------|
| `type` | Must be `dict` |
| `name` | Unique identifier for the dict |
| `data` | List of key-value objects |

## Access Modes

There are **two ways** to use dicts in commands:

### List Mode (Dict in Alias)

When you reference the dict in the **alias**, the user selects an item interactively, and all keys in the command resolve from that **same item**:

```yaml
---
type: dict
name: servers
data:
  - name: prod
    host: 192.168.1.10
    user: admin
  - name: staging
    host: 192.168.1.20
    user: deploy

---
type: command
name: SSH Connect
alias: ssh $${servers.name}        # ← Dict in ALIAS (list mode)
command: ssh $${servers.user}@$${servers.host}
```

**Usage:**
```
dya> ssh <TAB>
         prod
         staging

dya> ssh prod
Running: ssh admin@192.168.1.10
```

The user selects `prod`, so `$${servers.user}` resolves to `admin` and `$${servers.host}` resolves to `192.168.1.10` from the **same item**.

### Direct Mode (Dict NOT in Alias)

When you reference the dict **only in the command** (not in alias), it accesses a specific position. By default, position 0 (first item):

```yaml
---
type: dict
name: api_config
data:
  - key: MY_API_KEY
    endpoint: https://api.example.com
    timeout: 30

---
type: command
name: API Call
alias: api-call                    # ← No dict in alias (direct mode)
command: curl -H "Authorization: $${api_config.key}" $${api_config.endpoint}
```

**Usage:**
```
dya> api-call
Running: curl -H "Authorization: MY_API_KEY" https://api.example.com
```

#### Indexed Access

You can specify which position to access using `[N]` syntax:

| Syntax | Position Accessed |
|--------|-------------------|
| `$${dict.key}` | Position 0 (default) |
| `$${dict[0].key}` | Position 0 (explicit) |
| `$${dict[1].key}` | Position 1 (second item) |
| `$${dict[2].key}` | Position 2 (third item) |

> [!IMPORTANT]
> Positions are **0-indexed**: first item = `[0]`, second = `[1]`, third = `[2]`, etc.

**Example accessing different positions:**

```yaml
---
type: dict
name: regions
data:
  - name: us-east-1       # Position [0]
    endpoint: https://us-east-1.api.com
  - name: eu-west-1       # Position [1]
    endpoint: https://eu-west-1.api.com
  - name: ap-southeast-1  # Position [2]
    endpoint: https://ap-southeast-1.api.com

---
type: command
name: Multi Region
alias: multi-region
command: |
  echo "Primary: $${regions[0].name}"
  echo "Secondary: $${regions[1].name}"
  echo "Tertiary: $${regions[2].name}"
```

**Usage:**
```
dya> multi-region
Running: echo "Primary: us-east-1" && echo "Secondary: eu-west-1" && echo "Tertiary: ap-southeast-1"
```

## Mode Comparison

| Mode | Dict in Alias | Behavior |
|------|---------------|----------|
| **List** | ✓ Yes | User selects item; all keys from same item |
| **Direct** | ✗ No | Uses position 0 by default, or `[N]` for specific position |

## Multiple Keys

Each data item can have any number of keys:

```yaml
---
type: dict
name: databases
data:
  - name: analytics
    host: db-analytics.internal
    port: 5432
    user: analyst
    dbname: analytics_prod
  - name: orders
    host: db-orders.internal
    port: 5432
    user: app
    dbname: orders_prod
```

## Dict Chaining

Static dicts can reference values from other static dicts using `$${other_dict.key}` syntax. References are resolved lazily when the data is accessed.

```yaml
---
type: dict
name: base_config
data:
  - env: production
    region: us-east-1

---
type: dict
name: derived_config
data:
  - prefix: $${base_config.env}-$${base_config.region}
    endpoint: https://api.$${base_config.region}.example.com

---
type: command
name: Show Config
alias: show-config
command: echo $${derived_config.prefix}
```

**Usage:**
```
dya> show-config
Running: echo production-us-east-1
```

> [!WARNING]
> Dicts **cannot** reference dynamic_dicts. This will cause a validation error. Only dynamic_dicts can reference other dynamic_dicts.

## Autocomplete

In interactive mode (list mode), typing the alias prefix shows all available options:

```
dya> ssh <TAB>
         prod
         staging
```

---

| ← Previous | Next → |
|:-----------|-------:|
| [Configuration](configuration.md) | [Dynamic Dicts](dynamic-dicts.md) |
