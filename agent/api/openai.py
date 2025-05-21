"""
agent.api.openai
"""

import os
import re
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

    def _think_token_heal(self, token: Tuple[str, str]) -> List[Tuple[str, str]]:
        kind, text = token
        if kind != "content" or (THINK_OPEN not in text and THINK_CLOSE not in text):
            return [token]
        pattern = f"({re.escape(THINK_OPEN)}|{re.escape(THINK_CLOSE)})"
        parts = re.split(pattern, text)
        return [(kind, part) for part in parts if part]

    @staticmethod
    def classify(stream):
        is_reasoning = False
        for token in stream:
            kind, *rest = token
            if kind == "content":
                text = rest[0]
                if text == THINK_OPEN:
                    is_reasoning = True
                    continue  # Optional: skip the tag token itself
                elif text == THINK_CLOSE:
                    is_reasoning = False
                    continue  # Optional: skip the tag token itself
                yield ("reasoning" if is_reasoning else "content", text)
            else:
                yield token  # Pass through other tuple types

    def stream(
        self, **kwargs: Dict[str, Any]
    ) -> Generator[Tuple[str, str], None, None]:
        response = self.client.chat.completions.create(**kwargs)
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta:
                if delta.role:
                    yield ("role", delta.role)
                if delta.content:
                    token = ("content", delta.content)
                    for healed_token in self._think_token_heal(token):
                        yield healed_token
                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        yield (
                            "tool_call",
                            tool_call.function.name,
                            tool_call.function.arguments,
                        )
                if delta.refusal:
                    yield ("refusal", delta.refusal)
                if delta.function_call:
                    yield (
                        "function_call",
                        delta.function_call.name,
                        delta.function_call.arguments,
                    )


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
        stream = model.stream(
            model="gpt-3.5-turbo",
            messages=messages,
            stream=True,
            temperature=0.8,
            tools=tools,  # Leave this blank for now
        )
        for token in model.classify(stream):
            print(token)
            sys.stdout.flush()
        print()
    except Exception as e:
        print(f"Error: {e}")
