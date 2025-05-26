import json
import os
import re
import sys
from typing import Any, Dict, Generator, List, Tuple

import dotenv
from openai import OpenAI

from agent.tools import tools
from agent.tools.weather import get_weather  # get_weather(location, units)
from agent.utils.json import save_json

ESCAPE = "\x1b"
RESET = ESCAPE + "[0m"
BOLD = ESCAPE + "[1m"


def connect(base_url: str = None, api_key: str = None) -> OpenAI:
    if not base_url or not api_key:
        dotenv.load_dotenv(".env")

    if not base_url:
        base_url = os.getenv("OPENAI_BASE_URL", "")

    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY", "")

    if not api_key:
        raise ValueError("EnvironmentError: OPENAI_API_KEY not set in .env")

    # Setup default base URL if using local mode
    if api_key == "sk-no-key-required" and not base_url:
        base_url = "http://localhost:8080/v1"

    return OpenAI(api_key=api_key, base_url=base_url)


def call_tool(client, messages):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=-1,
        stream=False,
        temperature=0.8,
        tools=tools,
    )

    # After getting initial completion
    tool_call = completion.choices[0].message.tool_calls[0]
    func_name = tool_call.function.name
    func_args = json.loads(tool_call.function.arguments)

    # Actually call your tool
    result = get_weather(**func_args)

    # Add tool call and output to messages for follow-up
    messages.append(
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": func_name,
                        "arguments": tool_call.function.arguments,
                    },
                }
            ],
        }
    )
    messages.append(
        {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": func_name,
            "content": str(result),
        }
    )

    # Final model call to get answer in natural language
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=-1,
        stream=False,
        temperature=0.8,
    )
    final_role = response.choices[0].message.role
    final_content = response.choices[0].message.content

    messages.append(
        {
            "role": final_role,
            "content": final_content,
        }
    )


if __name__ == "__main__":
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather like in Paris today?"},
    ]

    client = connect()
    call_tool(client, messages)

    messages.append(
        {
            "role": "user",
            "content": "What kind of apparel should I wear for this kind of weather?",
        }
    )

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=-1,
        stream=False,
        temperature=0.8,
    )
    messages.append(
        {
            "role": completion.choices[0].message.role,
            "content": completion.choices[0].message.content,
        }
    )

    save_json(messages, "temp.json")
