"""
Module: agent.tools.__init__
"""

tools = [
    {
        "type": "function",
        "function": {
            "name": "weather",
            "description": "Retrieves current weather for the given location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "units": {
                        "type": "string",
                        "enum": ["metric", "uscs"],
                        "description": "The unit system. Default is 'metric'.",
                    },
                },
                "required": ["location", "units"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_read",
            "description": "Reads one or more lines from a file, using 1-based (inclusive) line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "The path of the file to read.",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "The line number to start reading from (1-based, inclusive).",
                        "minimum": 1,
                    },
                    "end_line": {
                        "type": ["integer", "null"],
                        "description": "The line number to stop reading at (1-based, inclusive). If null, reads to the end of the file.",
                        "minimum": 1,
                    },
                },
                "required": ["filepath", "start_line"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_write",
            "description": "Writes text to a file. Optionally replaces a specific line range (1-based, inclusive). If no lines are specified, replaces the entire file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "The path of the file to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file.",
                    },
                    "start_line": {
                        "type": ["integer", "null"],
                        "description": "The first line number to replace (1-based, inclusive). If not set, overwrites the entire file.",
                        "minimum": 1,
                    },
                    "end_line": {
                        "type": ["integer", "null"],
                        "description": "The last line number to replace (1-based, inclusive). If not set, overwrites or appends after start_line.",
                        "minimum": 1,
                    },
                },
                "required": ["filepath", "content"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
]
