"""
agent.openai.inference

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

import json
import sys

from agent.openai.stream import GPTRequest
from agent.tools import tools
from agent.tools.weather import get_weather
from agent.utils.json import save_json

ESCAPE = "\x1b"
RESET = ESCAPE + "[0m"
BOLD = ESCAPE + "[1m"
UNDERLINE = ESCAPE + "[4m"


def run_tool(tool_name: str, **kwargs) -> str:
    if tool_name == "get_weather":
        return get_weather(kwargs["location"], kwargs["units"])
    return ""


def run_agent(model: GPTRequest, messages: list[dict], **kwargs):
    stream = model.stream(
        model="gpt-3.5-turbo",
        messages=messages,
        stream=kwargs.get("stream", True),
        temperature=kwargs.get("temperature", 0.8),
        tools=kwargs.get("tools", tools),
    )

    message = {"role": "assistant", "content": ""}
    tool_call_pending = False
    tool_name, tool_args = None, {}

    for event in stream:
        event_type = event["type"]
        value = event["value"]

        if event_type == "role":
            continue  # Already handled by message["role"]

        elif event_type == "reasoning.open":
            print(f"{UNDERLINE}{BOLD}Thinking:{RESET}")
            message["content"] += value

        elif event_type == "reasoning.close":
            print(f"\n{UNDERLINE}{BOLD}Completion:{RESET}")
            message["content"] += value

        elif event_type == "content":
            message["content"] += value
            print(value, end="")

        elif event_type == "tool_call":
            tool_name = value["name"]
            tool_args = value["arguments"]

            if message["content"]:
                messages.append(message)

            messages.append(
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(tool_args),
                            },
                        }
                    ],
                }
            )

            result = run_tool(tool_name, **tool_args)
            messages.append(
                {
                    "role": "tool",
                    "name": tool_name,
                    "content": result,
                }
            )

            tool_call_pending = True

            print(f"\n{UNDERLINE}{BOLD}Tool Call:{RESET}")
            print(f"{UNDERLINE}{BOLD}{tool_name}({tool_args}){RESET}: {result}")

        sys.stdout.flush()

    if message["content"] and not tool_call_pending:
        messages.append(message)


def run_chat(model: GPTRequest, tools: list):
    messages = [
        {"role": "system", "content": "My name is Qwen. I am a helpful assistant."}
    ]

    while True:
        try:
            if messages[-1]["role"] != "tool":
                if messages[-1]["role"] != "system":
                    print()
                user_input = input("<user> ").strip()
                if user_input.lower() in ("exit", "quit"):
                    print("Exiting.")
                    break
                messages.append({"role": "user", "content": user_input})

            print()
            save_json(messages, "test.json")
            run_agent(model, messages, temperature=0.8, stream=True, tools=tools)
            print()
            save_json(messages, "test.json")

        except KeyboardInterrupt:
            print("\nInterrupted.")
            break


def main():
    gpt = GPTRequest()
    run_chat(gpt, tools)


if __name__ == "__main__":
    main()
