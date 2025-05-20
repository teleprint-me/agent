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
    }
]
