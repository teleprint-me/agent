"""
Module: agent.tools.registry
"""

import json
from typing import Any, Dict

from agent.tools.file import file_read, file_write
from agent.tools.memory import memory_forget, memory_recall, memory_store
from agent.tools.shell import Shell
from agent.tools.weather import weather


class ToolRegistry:
    def __init__(self):
        self._tools = {
            "weather": weather,
            "access": Shell.access,
            "shell": Shell.run,
            "read": file_read,
            "write": file_write,
            "store": memory_store,
            "recall": memory_recall,
            "forget": memory_forget,
        }

    def register(self, name: str, function: callable):
        self._tools[name] = function

    def call(self, name: str, **kwargs: Dict[str, Any]) -> str:
        if name not in self._tools:
            return f"Error: Tool '{name}' not found."
        try:
            return self._tools[name](**kwargs)
        except Exception as e:
            return f"Error: Tool raised exception: {e}"

    def request(self, event: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = event["tool_call"]["name"]
        tool_args = event["tool_call"].get("arguments", {})
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

    def dispatch(self, event: Dict[str, Any]) -> Dict[str, str]:
        tool_name = event["tool_call"]["name"]
        tool_args = event["tool_call"].get("arguments", {})
        result = self.call(tool_name, **tool_args)
        return {
            "role": "tool",
            "name": tool_name,
            "content": result,
        }
