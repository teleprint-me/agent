import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from agent.config import config
from agent.llama.api import LlamaCppAPI


def classify_tool(
    tool_call: dict[str, any],
    buffer: dict[str, any],
    args_fragments: list[str],
) -> Optional[dict[str, any]]:
    fn = tool_call["function"]
    if fn.get("name"):
        buffer["name"] = fn["name"]
    if fn.get("arguments"):
        args_fragments.append(fn["arguments"])
    if fn.get("arguments") and fn["arguments"].strip().endswith("}"):
        try:
            args = "".join(args_fragments)
            buffer["arguments"] = json.loads(args)
            args_fragments.clear()
            return {"tool_call": buffer.copy()}
        except json.JSONDecodeError as e:
            if os.getenv("DEBUG_TOOL_JSON"):
                print(f"[warn] tool_call args error: {e} :: {''.join(args_fragments)}")
    return None


def classify_reasoning(
    content: str,
    active: bool,
) -> Optional[dict[str, any]]:
    if content and active:
        return {"reasoning": delta["reasoning_content"]}
    elif content and not active:
        reasoning_active = True
        return {"reasoning.open": delta["reasoning_content"]}
    elif not content and active:
        reasoning_active = False
        return {"reasoning.close": "\n"}
    return None


def stream(chat_completions):
    tool_buffer = {}
    args_fragments = []
    reasoning_active = False
    for completed in chat_completions:
        delta = completed["choices"][0]["delta"]

        if delta.get("content", None):
            yield {"content": delta["content"]}

        reasoning = delta.get("reasoning_content", None)
        if reasoning and reasoning_active:
            yield {"reasoning": delta["reasoning_content"]}
        elif reasoning and not reasoning_active:
            reasoning_active = True
            yield {"reasoning.open": delta["reasoning_content"]}
        elif not reasoning and reasoning_active:
            reasoning_active = False
            yield {"reasoning.close": "\n"}

        if delta.get("tool_calls", None):
            for tool_call in delta["tool_calls"]:
                # print(tool_call)
                result = classify_tool(tool_call, tool_buffer, args_fragments)
                if result:
                    yield result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n",
        "--predict",
        type=int,
        default=128,
        help="Tokens generated.",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debugging",
    )
    args = parser.parse_args()

    # NOTE: Reasoning models require a larger context size and may fail to emit a closing
    # token (if any) if provided with insufficient space within a given window.
    # Create an instance of LlamaCppAPI
    llama_api = LlamaCppAPI(n_predict=args.predict, log_level=args.debug)

    # Example: Generate chat completion given a sequence of messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather like in Paris today?"},
    ]

    for message in messages:
        print(f'{message["role"]}\n{message["content"]}')

    chat_completions = llama_api.chat_completion(messages)

    # Handle the models generated response
    content = ""
    for delta in stream(chat_completions):
        if delta.get("reasoning"):
            content += delta["reasoning"]
            print(delta["reasoning"], end="")
        elif delta.get("reasoning.open"):
            reasoning_active = True
            content += delta["reasoning.open"]
            print(delta["reasoning.open"], end="")
        elif delta.get("reasoning.close"):
            reasoning_active = False
            content += delta["reasoning.close"]
            print("\n")

        if delta.get("content"):
            token = delta["content"]
            content += token
            print(token, end="")

        if delta.get("tool_call"):
            print(delta["tool_call"])

        sys.stdout.flush()
    print()  # add padding to models output

    # sanity check
    print(content)
