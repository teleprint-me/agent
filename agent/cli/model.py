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


def classify_reasoning(content: str, active: bool) -> tuple[Optional[dict], bool]:
    if content and active:
        return {"reasoning": content}, True

    elif content and not active:
        return {"reasoning.open": content}, True

    elif not content and active:
        return {"reasoning.close": "\n"}, False

    return None, active


def classify_event(chat_completions):
    tool_buffer = {}
    args_fragments = []
    reasoning_active = False

    for completed in chat_completions:
        delta = completed["choices"][0]["delta"]

        if delta.get("content"):
            yield {"content": delta["content"]}

        reasoning, reasoning_active = classify_reasoning(
            delta.get("reasoning_content"),
            reasoning_active,
        )
        if reasoning:
            yield reasoning

        if delta.get("tool_calls"):
            for tool_call in delta["tool_calls"]:
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
    print()

    chat_completions = llama_api.chat_completion(messages)

    # Handle the models generated response
    content = ""
    for event in classify_event(chat_completions):
        if event.get("reasoning"):
            content += event["reasoning"]
            print(event["reasoning"], end="")
        elif event.get("reasoning.open"):
            print("thinking")
            content += event["reasoning.open"]
            print(event["reasoning.open"], end="")
        elif event.get("reasoning.close"):
            content += event["reasoning.close"]
            print("\n\ncompletion")

        if event.get("content"):
            token = event["content"]
            content += token
            print(token, end="")

        if event.get("tool_call"):
            print(event["tool_call"])

        sys.stdout.flush()
    print()  # add padding to models output
