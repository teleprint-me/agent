"""
Module: agent.tools.__init__
"""

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
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
            "name": "read_file",
            "description": "Reads a portion of a file between two line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "The path of the file to read.",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "The line number to start reading from (0-based).",
                        "minimum": 0,
                    },
                    "end_line": {
                        "type": ["integer", "null"],
                        "description": "The line number to stop reading at (exclusive). If null, reads to the end of the file.",
                        "minimum": 0,
                    },
                },
                "required": ["filepath", "start_line"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
]
