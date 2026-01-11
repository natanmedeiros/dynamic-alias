---
trigger: always_on
---

Global System rules
These rules must be applied to every application file
1 - General Rules
1.1 - CLI Config
1.1.1 - Variables starting with two dollar signs are application variables
1.1.2 - Variables starting with one dollar sign are user input variables
1.1.3 - Application variable $${env} are imported from S.O. environment
1.1.4 - Three dashes means init of a new structure
1.1.5 - There is three types of structures: dict, dynamic_dict and command
1.1.6 - Command starting with | are multiline commands
1.1.7 - Every structure can use environment variables
1.1.8 - dya shortcut can be replace by customer defined shortcut defined in pyproject.toml custom-build shortcut
1.1.9 - every place "dya" term in code must be replaced by $(customer-defined-shortcut) to be possible change it
1.1.10 - shell style and placeholder must have default value, but if defined in config file inside type config must be used instead of default
1.1.11 - Must validate input and remove BOM issue from user created config file
1.2 - Application
1.2.1 - Code must be written in a way that is easy to read, understand, debug and test
1.2.2 - Create a new const to define if cache is enabled or not and ttl size in seconds
1.2.3 - If cache is enabled, import json with the list of dynamic_dict from the file defined in the const and use if ttl is not reached
1.2.4 - If cache is enabled, export cache to the file defined in the const after command execution with current time to future ttl validation
1.2.5 - If cache is disabled, do not import or export cache
1.2.6 - Create a new const to define the path of the cache file with default value of ~/.dya.json or ~/.$(customer-defined-shortcut).json
1.2.7 - Cache path can be replaced by flag originally as --dya-cache, but it is --$(customer-defined-shortcut)-cache
1.2.8 - Create a new const to define the path of the config file with default value of ~/.dya.yaml or ~/.$(customer-defined-shortcut).yaml
1.2.9 - Config file path can be replaced by flag originally as --dya-config, but can be evaluated as --$(customer-defined-shortcut)-cache
1.2.8 - Must be possible use complete static commands and must be possible to execute dya to enter interactive mode and use autocomplete to define commands
1.2.9 - When a command use a dynamic_dict or dict, it must be possible to use autocomplete from its values
1.2.10 - When an alias is defined with a user variable like ${filename}, it is possible to use it in command execution if calls it with same name, like ${filename}
1.2.11 - When an alias uses a dynamic_dict or dict option and its commands use another key from same dict or dynamic_dict, it must select the equivalent key from the same list position of dynamic_dict or dict
1.2.12 - example, take in consideration the dynamic_dict redis_servers with name and host, if use the name of dynamic_dict second item, when its commands calls another key like host, must be the host from the second item of dynamic_dict
1.2.13 - autocompletion must be evaluated for each command dynamicaly, and must be evaluated when backspace pressed and deleted entire word
1.2.14 - on every command end must evaluate autocompletion that come after command
1.2.15 - if delete character, must evaluate again autocompletion
1.2.16 - When showing autocompletion list, tab and enter must have same behavior, complete word, but if not showing any list, enter must execute command
1.2.17 - Every feature should work on both modes, interactive and non-interactive
1.2.18 - Shortcut and global name rules
1.2.18.1 - Must exist a constant named CUSTOM_SHORTCUT with default "dya"
1.2.18.2 - Must exist a constant named CUSTOM_NAME with default "DYNAMIC ALIAS"
1.2.18.3 - CUSTOM_SHORTCUT must be used as binary to trigger application when builded and as promt prefix in interactive mode
1.2.18.4 - CUSTOM_NAME must be used to build helper header
1.2.19 - cache file must contain _history with command execution history limited to default last 20 but can be replaced by used defined config history-size with max of 1000
1.2.20 - if _history exists, cache must be appended and shifted only if exceeds history-size
1.3 - Helper
1.3.1 - The helper can be displayed by using flag -h or --help
1.3.2 - Can't use -h or --help as command args, these flags are restricted
1.3.3 - The helper text displayed must gather helpers from matched commands and its parent's
1.3.4 - If user issue dya -h or dya --help without any alias/command, should display list of available dycts and commands
1.3.4 - helper should work on both modes, interactive and non-interactive
1.3.5 - helper must consider partial match commands when variables wasnt informed, e.g. for "pg $${database_servers.name}" the partial command helper "pg -h" or "pg --help" should work and display pg command helper
1.3.6 - helper header must display customer defined name placed in pyproject.toml custom-build name
2 - Dict Structure
2.1 - Static data accepted only
2.2 - Cannot use another dict or dynamic_dict
2.3 - It is required to have a name and data
2.4 - Data is a list of key-value pairs
3 - Dynamic Dict Structure
3.1 - It is required to have a name, command and mapping
3.2 - Mapping is a key-value pair and represents the link between commands and dict data
3.3 - Command return must be a valid json that contains the mapped keys
3.4 - Priority has default value of 1 and is used define dynamic_dict execution order
3.5 - Any integer value, negative or positive, is accepted
3.6 - Lower priority values are executed first
3.7 - If two dynamic_dict have the same priority, they are executed in the order they are defined
3.8 - Environment variables are (re)imported before every dynamic_dict execution
3.9 - Timeout is optional and has default value of 10 seconds. zero means no timeout
4 - Command Structure
4.1 - It is required to have a name, alias and command
4.2 - Alias is the shortcut that will be used to execute the command
4.3 - Command is what will be executed when the alias is used
4.4 - Helper is optional
4.5 - Helper is printed when the command is used with --help
4.6 - Sub is optional
4.7 - Sub is a list of commands that can be executed when the alias is used
4.8 - Sub is recursive and can have its own sub
4.9 - Timeout is optional and has default value of 0. zero means no timeout
4.10 - Args is optional
4.11 - Args is a list of arguments that can be used when the alias is used, like subs, but intented to be used with dash or double dash
4.12 - Args is not recursive
4.13 - Args are not executed, they are only used to build the command
4.14 - Sub and command can have args
4.15 - Args can occur multiple times
4.16 - Args can receive user input variables
4.17 - Args can be just flags without value
4.18 - Args can autocomplete only flags, not user variables like ${filename}
4.18.1 - e.g. "pg db1 -o " does not autocomplete ${filename}, but after use input ${filename}, autocomplete must continue to work
4.19 - autocompletion must continue to work for the commands and subs after args usage
4.20 - commands must be completed, but have to avoid user defined variables completion like ${sql_text} in sentence "pg db1 cmd ${sql_text}"