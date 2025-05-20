"""
Adapted client for OpenAI and local llama.cpp servers.
Supports streaming completions and environment-based endpoint switching.

Qwen3 models support internal "thinking" behavior, which is wrapped in <think>...</think> blocks.
This behavior is controlled via special user prompt suffixes, as interpreted by the model's chat template.

Usage notes for Qwen3 (when chat templates support reasoning):

- Default behavior: reflection is enabled, and the model emits <think>...</think> with internal reasoning.
- To explicitly disable reflection, append `/no_think` to the user prompt.
- To explicitly enable reflection (optional), append `/think`.

Example:
    {"role": "user", "content": "What is the capital of France? /no_think"}

Important:
- `/no_think` disables reflection content but not the presence of <think> tags.
- To suppress <think> tags entirely, the chat template must be modified.
"""

import os
import sys

import dotenv
from openai import OpenAI
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

from agent.tools.weather import get_weather

ESCAPE = "\x1b"
BOLD = ESCAPE + "[1m"
UNDERLINE = ESCAPE + "[4m"
RESET = ESCAPE + "[0m"


def create_client():
    # Load environment
    dotenv.load_dotenv(".env")

    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "")

    if not api_key:
        raise ValueError("EnvironmentError: OPENAI_API_KEY not set in .env")

    # Setup default base URL if using local mode
    if api_key == "sk-no-key-required" and not base_url:
        base_url = "http://localhost:8080/v1"

    # Initialize client
    return OpenAI(api_key=api_key, base_url=base_url)


def stream_response(response):
    for chunk in response:
        if isinstance(chunk, ChatCompletionChunk):
            content = chunk.choices[0].delta.content
            if content:
                if content == "<think>":
                    print(f"{UNDERLINE}{BOLD}Thinking{RESET}", end="\n")
                elif content == "</think>":
                    print(f"\n{UNDERLINE}{BOLD}Completion{RESET}", end="")
                else:
                    print(content, end="")
                sys.stdout.flush()
    print()


def main():
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

    # Sample chat sequence
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather like in Paris today?"},
    ]

    try:
        client = create_client()
        response = client.chat.completions.create(
            model="qwen3",  # Use "gpt-4" for OpenAI, "qwen3" for local
            messages=messages,
            stream=True,
            temperature=0.8,
            tools=tools,
        )
        stream_response(response)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
