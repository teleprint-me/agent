"""
Module: agent.config
"""

import argparse

from jsonpycraft import (
    ConfigurationManager,
    JSONDecodeErrorHandler,
    JSONFileErrorHandler,
    JSONMap,
)

from agent.tools import tools

DEFAULT_PATH = ".agent/settings.json"

DEFAULT_CONF = {
    "openai": {
        "model": "gpt-3.5-turbo",
        "stream": True,
        "seed": 1337,
        "max_tokens": -1,
        "temperature": 0.7,
        "n": 1,
        "top_p": 0.95,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "stop": [],
        "logit_bias": {},
    },
    "templates": {
        "system": {
            "content": "My name is ChatGPT. I am a helpful assistant.",
            "type": "str",
        },
        "messages": {
            "path": ".agent/messages.json",
            "type": "file",
        },
        "schemas": {
            "tools": tools,
            "type": "list",
        },
    },
    "cli": {},
    "gui": {
        "font": {
            "size": 12,
            "name": "Noto Sans Mono",
        },
        "theme": "darkly",
    },
    # Add other sections as needed
}


def load_or_init_config(path: str, defaults: JSONMap):
    config = ConfigurationManager(path, initial_data=defaults)
    config.mkdir()
    try:
        config.load()
    except (JSONFileErrorHandler, JSONDecodeErrorHandler):
        config.save()
    return config


# NOTE: Do not assign to `config` in any function; it is a top-level singleton.
config = load_or_init_config(DEFAULT_PATH, DEFAULT_CONF)


def main():
    parser = argparse.ArgumentParser(description="Agent Configuration Utility")
    subparsers = parser.add_subparsers(dest="command")

    # View value(s)
    view = subparsers.add_parser(
        "view", help="View a config value or the entire config"
    )
    view.add_argument("key", nargs="?", default=None, help="Config key (dot notation)")

    # Set value
    set_ = subparsers.add_parser("set", help="Set a config value")
    set_.add_argument("key", help="Config key (dot notation)")
    set_.add_argument("value", help="New value (JSON or string)")

    # List keys
    list_ = subparsers.add_parser("list", help="List all config keys")

    # Reset config
    reset = subparsers.add_parser("reset", help="Reset config to defaults")

    args = parser.parse_args()

    if args.command == "view":
        if args.key:
            print(config.get_value(args.key))
        else:
            import json

            print(json.dumps(config.data, indent=2))
    elif args.command == "set":
        import json

        try:
            # Try to parse as JSON for richer types
            value = json.loads(args.value)
        except Exception:
            value = args.value
        config.set_value(args.key, value)
        config.save()
        print(f"Set {args.key} to {value}")
    elif args.command == "list":

        def walk(d, prefix=""):
            for k, v in d.items():
                full = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    walk(v, full)
                else:
                    print(full)

        walk(config.data)
    elif args.command == "reset":
        # Overwrite the config file directly with defaults
        config.reset(initial_data=DEFAULT_CONF)
        print("Config reset to defaults. Please restart your agent to reload settings.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
