"""
agent.api.openai
"""

import os
import sys
from typing import Any, Dict, Generator, List, Tuple

import dotenv
from openai import OpenAI

from agent.tools import tools

THINK_OPEN = "<think>"
THINK_CLOSE = "</think>"


class Model:
    def __init__(self, base_url: str = None, api_key: str = None):
        self.client = self.connect(base_url, api_key)

    def connect(self, base_url: str = None, api_key: str = None) -> OpenAI:
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

    def stream(
        self, **kwargs: Dict[str, Any]
    ) -> Generator[Tuple[str, str], None, None]:
        response = self.client.chat.completions.create(**kwargs)
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield ("content", delta.content)
            if delta and delta.tool_calls:
                for tool_call in delta.tool_calls:
                    yield ("argument", tool_call.function.arguments)


if __name__ == "__main__":
    # Sample chat sequence
    # messages = [
    #     {"role": "system", "content": "You are a helpful assistant."},
    #     {"role": "user", "content": "What is the capital of France?"},
    # ]
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather like in Paris today?"},
    ]

    try:
        model = Model()
        generator = model.stream(
            model="gpt-3.5-turbo",
            messages=messages,
            stream=True,
            temperature=0.8,
            tools=tools,  # Leave this blank for now
        )
        for token in generator:
            print(token, end="")
            sys.stdout.flush()
        print()
    except Exception as e:
        print(f"Error: {e}")
