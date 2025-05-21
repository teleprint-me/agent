"""
agent.api.openai

"Embrace the journey of discovery and evolution in the world of software development, and remember that adaptability is key to staying resilient in the face of change."
    - OpenAI's GPT-3.5
"""

import json
import os
import re
import sys
from typing import Any, Dict, Generator, List, Tuple

import dotenv
from openai import OpenAI


class Model:
    THINK_OPEN = "<think>"
    THINK_CLOSE = "</think>"

    def __init__(self, base_url: str = None, api_key: str = None):
        self.client = self._connect(base_url, api_key)

    def _connect(self, base_url: str = None, api_key: str = None) -> OpenAI:
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
        thinking = self.THINK_OPEN not in text and self.THINK_CLOSE not in text
        if kind != "content" or thinking:
            return [token]
        pattern = f"({re.escape(self.THINK_OPEN)}|{re.escape(self.THINK_CLOSE)})"
        parts = re.split(pattern, text)
        return [(kind, part) for part in parts if part]

    def _stream(
        self, response: Generator[Dict[str, any], None, None]
    ) -> Generator[Tuple[str, str], None, None]:
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

    def _classify(
        self, stream: Generator[Tuple[str, str], None, None]
    ) -> Generator[Tuple[str, str], None, None]:
        is_reasoning = False
        for token in stream:
            kind, *rest = token
            if kind == "content":
                text = rest[0]
                if text == self.THINK_OPEN:
                    is_reasoning = True
                    yield (self.THINK_OPEN, None)
                    continue
                elif text == self.THINK_CLOSE:
                    is_reasoning = False
                    yield (self.THINK_CLOSE, None)
                    continue
                yield ("reasoning" if is_reasoning else "content", text)
            else:
                yield token  # Pass through other tuple types

    def _tool_call(
        self, stream: Generator[Tuple[str, str], None, None]
    ) -> Generator[Tuple[str, Any], None, None]:
        buffer = ""
        current_name = None
        in_tool_call = False

        for token in stream:
            if token[0] == "tool_call":
                _, name, arg = token
                # Start of a new tool call
                if arg is None:
                    # flush previous if any (should not be, but for safety)
                    if in_tool_call and buffer and current_name:
                        try:
                            args = json.loads(buffer)
                            yield ("tool_call", current_name, args)
                        except Exception:
                            yield ("tool_call", current_name, buffer)
                    buffer = ""
                    current_name = name
                    in_tool_call = True
                else:
                    buffer += arg
            else:
                # If you reach a non-tool_call, finish the buffer if in progress
                if in_tool_call and buffer and current_name:
                    try:
                        args = json.loads(buffer)
                        yield ("tool_call", current_name, args)
                    except Exception:
                        yield ("tool_call", current_name, buffer)
                    buffer = ""
                    in_tool_call = False
                    current_name = None
                yield token  # Pass through non-tool_call events

        # flush at end of stream if needed
        if in_tool_call and buffer and current_name:
            try:
                args = json.loads(buffer)
                yield ("tool_call", current_name, args)
            except Exception:
                yield ("tool_call", current_name, buffer)

    def completion(
        self, **kwargs: Dict[str, Any]
    ) -> Generator[Tuple[str, str], None, None]:
        response = self.client.chat.completions.create(**kwargs)
        stream = self._stream(response)
        classified = self._classify(stream)
        tool_call = self._tool_call(classified)
        return tool_call


if __name__ == "__main__":
    from agent.tools import tools

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
        completion = model.completion(
            model="gpt-3.5-turbo",
            messages=messages,
            stream=True,
            temperature=0.8,
            tools=tools,  # Leave this blank for now
        )
        for token in completion:
            print(token)
            sys.stdout.flush()
    except Exception as e:
        print(f"Error: {e}")
