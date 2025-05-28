"""
Module: agent.tools.registry
"""

import json
from typing import Any, Dict

from agent.tools.file import file_read, file_write
from agent.tools.memory import memory_create, memory_delete, memory_read, memory_update
from agent.tools.shell import shell
from agent.tools.weather import weather


class ToolRegistry:
    def __init__(self):
        self._tools = {
            "weather": weather,
            "file_read": file_read,
            "file_write": file_write,
            "memory_create": memory_create,
            "memory_read": memory_read,
            "memory_update": memory_update,
            "memory_delete": memory_delete,
            "shell": shell,  # Optional, gated/whitelisted
        }

    def register(self, name, function):
        self._tools[name] = function

    def call(self, name, **kwargs):
        if name not in self._tools:
            return {"error": f"Tool '{name}' not found."}
        try:
            return self._tools[name](**kwargs)
        except Exception as e:
            return {"error": str(e)}

    def request(self, event: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = event["value"]["name"]
        tool_args = event["value"]["arguments"]
        return {
            "role": "assistant",
            "tool_calls": [
                {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(tool_args),
                    },
                }
            ],
        }

    def dispatch(self, event: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = event["value"]["name"]
        tool_args = event["value"].get("arguments", {})
        result = self.call(tool_name, **tool_args)
        return {
            "role": "tool",
            "name": tool_name,
            "content": result,
        }
