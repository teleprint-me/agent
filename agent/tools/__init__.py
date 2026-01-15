"""
Module: agent.tools.__init__
"""

_weather = [
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
]

_shell = [
    {
        "type": "function",
        "function": {
            "name": "access",
            "description": (
                "Return the status of shell access as a structured JSON object. "
                "The response includes whether execution is enabled, which commands are allowed, "
                "and any relevant hints for the agent."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shell",
            "description": (
                "Execute a virtual shell program that the agent supplies and return "
                "the result as structured JSON.  The output includes stdout, stderr, "
                "return code, or an error message if execution fails."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "program": {
                        "type": "string",
                        "description": (
                            "Agents may execute “virtual shell scripts” within the environment. "
                            "This function supports full shell capabilities unless disabled or restricted by Admin. "
                            "Use `access` to see which commands are actually permitted."
                        ),
                    },
                },
                "required": ["program"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
]

_file = [
    {
        "type": "function",
        "function": {
            "name": "read",
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
            "name": "write",
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

_memory = [
    {
        "type": "function",
        "function": {
            "name": "store",
            "description": "Store a memory. If a similar memory already exists, update it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {
                        "type": "string",
                        "description": "The memory to store or update.",
                    }
                },
                "required": ["fact"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall",
            "description": "Retrieve memories that match a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query used to search memory contents.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return.",
                        "default": 5,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget",
            "description": "Delete the memory that best matches the given query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A query describing the memory to delete. The top match will be removed.",
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
]

tools = _shell + _file + _memory
