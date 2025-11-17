"""
Copyright © 2023 Austin Berrio

Module: agent.backend.gpt.requests

"Embrace the journey of discovery and evolution in the world of software development, and remember that adaptability is key to staying resilient in the face of change."
    - OpenAI's GPT-3.5
"""

import json
import os
from pprint import pprint
from typing import Any, Dict, Generator, List, Optional

from openai import OpenAI
from openai.types.chat.chat_completion_chunk import (
    ChoiceDelta,
    ChoiceDeltaFunctionCall,
    ChoiceDeltaToolCall,
)

from agent.tools import tools


class GPTRequest:
    def __init__(self, base_url: str = None, api_key: str = None):
        if not base_url or not api_key:
            # Load .env if we need it
            from dotenv import load_dotenv

            load_dotenv(".env")

        if not base_url:
            base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:8080/v1")

        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY", "sk-no-key-required")

        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def _classify_tool(
        self,
        tool_call: ChoiceDeltaToolCall,
        buffer: Dict[str, Any],
        args_fragments: List[str],
    ) -> Optional[Dict[str, Any]]:
        fn: ChoiceDeltaFunctionCall = tool_call.function
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

    def _dump_value(self, val):
        return val.model_dump() if hasattr(val, "model_dump") else val

    def _emit_event(self, key, value) -> dict[str, any]:
        return {"type": key, "value": value}

    def stream(self, **kwargs) -> Generator[Dict[str, Any], None, None]:
        kwargs["stream"] = True  # Coerce streaming
        response = self.client.chat.completions.create(**kwargs)
        reasoning_active = False
        tool_buffer = {}
        args_fragments = []

        for chunk in response:
            delta: ChoiceDelta = chunk.choices[0].delta
            reasoning = getattr(delta, "reasoning_content", None)

            # emit event role
            if delta.role:
                yield self._emit_event("role", delta.role)

            # emit event reason
            if reasoning and reasoning_active:
                yield self._emit_event("reasoning", delta.reasoning_content)
            elif reasoning and not reasoning_active:
                reasoning_active = True
                yield self._emit_event("reasoning.open", reasoning)
            elif not reasoning and reasoning_active:
                reasoning_active = False
                yield self._emit_event("reasoning.close", "")

            # emit event content
            if delta.content:
                yield self._emit_event("content", delta.content)

            # emit event tool call
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    result = self._classify_tool(tool_call, tool_buffer, args_fragments)
                    if result:
                        yield result

            # emit event refusal
            if delta.refusal:
                yield {"type": "refusal", "value": self._dump_value(delta.refusal)}


def main():
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather like in Paris, France?"},
    ]

    request = GPTRequest()
    generator = request.stream(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=-1,
        stream=True,
        temperature=0.8,
        tools=tools,
    )
    for obj in generator:
        pprint(obj)


if __name__ == "__main__":
    main()
