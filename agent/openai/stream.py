# agent.openai.stream
import json
import os
import re
from pprint import pprint
from typing import Any, Dict, Generator, List, Optional

import dotenv
from openai import OpenAI

from agent.tools import tools


class GPTRequest:
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

    def _think_token_heal(self, token: str) -> List[str]:
        think_open = "<think>"
        think_close = "</think>"
        if think_open not in token and think_close not in token:
            return [token]
        pattern = f"({re.escape(think_open)}|{re.escape(think_close)})"
        parts = re.split(pattern, token)
        return [part for part in parts if part]

    def _classify_reasoning(self, text: str) -> Optional[str]:
        if "<think>" in text:
            return "reasoning.open"
        if "</think>" in text:
            return "reasoning.close"
        return None

    def _classify_tool(self, tool_call, buffer, args_fragments):
        fn = tool_call.function
        if fn.name:
            buffer["name"] = fn.name
        if fn.arguments:
            args_fragments.append(fn.arguments)
        if fn.arguments and fn.arguments.strip().endswith("}"):
            try:
                args = "".join(args_fragments)
                buffer["arguments"] = json.loads(args)
                args_fragments.clear()
                return {"type": "tool_call", "value": buffer.copy()}
            except json.JSONDecodeError as e:
                if os.getenv("DEBUG_TOOL_JSON"):
                    print(
                        f"[warn] tool_call args error: {e} :: {''.join(args_fragments)}"
                    )
        return None

    def stream(self, **kwargs) -> Generator[Dict[str, Any], None, None]:
        response = self.client.chat.completions.create(**kwargs)
        tool_buffer = {}
        args_fragments = []

        for chunk in response:
            delta = chunk.choices[0].delta

            if delta.role:
                yield {"type": "role", "value": delta.role}

            if delta.content:
                for token in self._think_token_heal(delta.content):
                    reasoning_type = self._classify_reasoning(token)
                    yield {"type": reasoning_type or "content", "value": token}

            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    result = self._classify_tool(tool_call, tool_buffer, args_fragments)
                    if result:
                        yield result

            if delta.refusal:
                yield {"type": "refusal", "value": delta.refusal.model_dump()}

            # Future compatibility with OpenAI's or llama.cpp's structured reasoning output
            if hasattr(delta, "reasoning") and delta.reasoning:
                yield {"type": "reasoning", "value": delta.reasoning.model_dump()}


def main():
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather like in Paris, France?"},
    ]

    request = GPTRequest()
    generator = request.stream(
        model="gpt-3.5-turbo",  # Llama.Cpp expects this model definition
        messages=messages,
        max_tokens=-1,  # Allow the to model to naturally stop on its own
        stream=True,
        temperature=0.8,
        tools=tools,
    )
    for obj in generator:
        pprint(obj)


if __name__ == "__main__":
    main()
