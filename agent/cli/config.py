"""
Module: agent.cli.config
"""

from jsonpycraft.manager.configuration import ConfigurationManager

from agent.tools import tools

# Define defaults here
DEFAULTS = {
    "openai": {
        "model": "gpt-3.5-turbo",
        "stream": True,
        "temperature": 0.7,
        "max_tokens": -1,
        "seed": 1337,
        "system": "You are a helpful assistant.",
        "tools": tools,
    },
}

config = ConfigurationManager(".agent/cli/settings.json", initial_data=DEFAULTS)

try:
    config.mkdir()  # Create if not present
    config.load()  # Read if present
except Exception:
    config.save()  # Create if not present
