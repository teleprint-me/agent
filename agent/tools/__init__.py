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
    {
        "type": "function",
        "function": {
            "name": "memory_create",
            "description": "Create a new memory with optional tags.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The memory or information to store.",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of tags for searching or filtering.",
                    },
                },
                "required": ["content"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_read",
            "description": "Retrieve memories by ID or by tags. If neither is given, returns the latest memories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": ["integer", "null"],
                        "description": "Optional memory ID. If given, retrieves only that memory.",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of tags to filter by.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of memories to retrieve.",
                        "default": 10,
                        "minimum": 1,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of memories to skip (for pagination).",
                        "default": 0,
                        "minimum": 0,
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_update",
            "description": "Update the content and/or tags of an existing memory by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "description": "ID of the memory to update.",
                    },
                    "content": {
                        "type": "string",
                        "description": "New content for the memory (optional if just updating tags).",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New list of tags for the memory (optional).",
                    },
                },
                "required": ["id"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_delete",
            "description": "Delete a memory by ID, or multiple memories by tags.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": ["integer", "null"],
                        "description": "Optional ID of the memory to delete.",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of tags. If set, deletes all matching memories.",
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
]
