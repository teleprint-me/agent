"""
Module: agent.gui.config
"""

from jsonpycraft.manager.configuration import ConfigurationManager

# Define defaults here
DEFAULTS = {
    "editor": {"font": {"size": 12, "name": "Noto Sans Mono"}, "theme": "darkly"}
}

config = ConfigurationManager(".agent/gui/settings.json", initial_data=DEFAULTS)

try:
    config.mkdir()  # Create if not present
    config.load()  # Read if present
except Exception:
    config.save()  # Create if not present
