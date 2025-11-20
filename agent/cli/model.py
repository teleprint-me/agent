import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from jsonpycraft import JSONListTemplate
from prompt_toolkit import PromptSession

from agent.config import config
from agent.llama.api import LlamaCppAPI
from agent.tools.memory import memory_initialize
from agent.tools.registry import ToolRegistry

ESCAPE = "\x1b"
RESET = ESCAPE + "[0m"
BOLD = ESCAPE + "[1m"
UNDERLINE = ESCAPE + "[4m"


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
    if content and not active:
        return {"reasoning.open": content}, True

    elif content and active:
        return {"reasoning": content}, True

    elif not content and active:
        return {"reasoning.close": content if content else "\n"}, False

    return None, active


def classify_event(chat_completions):
    tool_buffer = {}
    args_fragments = []
    reasoning_active = False

    for completed in chat_completions:
        delta = completed["choices"][0]["delta"]

        reasoning, reasoning_active = classify_reasoning(
            delta.get("reasoning_content"),
            reasoning_active,
        )
        if reasoning:
            yield reasoning

        # Note: Only yield content **after** reasoning
        if delta.get("content"):
            yield {"content": delta["content"]}

        if delta.get("tool_calls"):
            for tool_call in delta["tool_calls"]:
                result = classify_tool(tool_call, tool_buffer, args_fragments)
                if result:
                    yield result


def run_agent(
    model: LlamaCppAPI,
    messages: JSONListTemplate,
    registry: ToolRegistry,
) -> None:
    tool_call_pending = False
    message = {"role": "assistant", "content": ""}
    chat_completions = model.chat_completion(messages.data)

    for event in classify_event(chat_completions):
        if event.get("reasoning"):
            message["content"] += event["reasoning"]
            print(event["reasoning"], end="")
        elif event.get("reasoning.open"):
            message["content"] += event["reasoning.open"]
            print("thinking")
            print(event["reasoning.open"], end="")
        elif event.get("reasoning.close"):
            message["content"] += event["reasoning.close"]
            print("\ncompletion")
        elif event.get("content"):
            message["content"] += event["content"]
            print(event["content"], end="")
        elif event.get("tool_call"):
            if message["content"]:
                messages.append(message)

            tool_req = registry.request(event)
            messages.append(tool_req)

            tool_res = registry.dispatch(event)
            messages.append(tool_res)

            tool_call_pending = True

            # Temp: Debug tool calling
            print(f"{UNDERLINE}{BOLD}{event['tool_call']}{RESET}")
            print(tool_res["content"])

        sys.stdout.flush()

    if message["content"] and not tool_call_pending:
        messages.append(message)


if __name__ == "__main__":
    path = config.get_value("templates.messages.path")
    if path is None:
        raise RuntimeError(
            "Missing config: templates.messages.path is required. Please check your config."
        )

    messages = JSONListTemplate(
        path,
        initial_data=[
            {
                "role": "system",
                "content": config.get_value("templates.system.content"),
            },
        ],
    )
    messages.mkdir()

    session = PromptSession()
    registry = ToolRegistry()
    memory_initialize()

    model = LlamaCppAPI()

    for message in messages.data:
        print(f'{message["role"]}\n{message["content"]}')
    print()

    while True:
        try:
            if messages.data[-1]["role"] != "tool":
                if messages.data[-1]["role"] != "system":
                    print()
                user_input = session.prompt("> ", multiline=True)
                if user_input.lower() in ("exit", "quit"):
                    print("Exiting.")
                    break
                messages.append({"role": "user", "content": user_input})
                messages.save_json()

            run_agent(model, messages, registry)
            print()
            messages.save_json()

        except EOFError:  # Pop the last message
            print(f"\n{UNDERLINE}{BOLD}Popped:{RESET}")
            last = messages.pop(messages.length - 1)
            print(last)
            messages.save_json()

        except KeyboardInterrupt:  # Exit the program
            print("\nInterrupted.")
            break
