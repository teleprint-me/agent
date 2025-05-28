"""
Script: cli.__main__

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

from jsonpycraft import JSONListTemplate
from prompt_toolkit import PromptSession

from agent.backend.gpt.requests import GPTRequest
from agent.cli.config import config
from agent.tools.read_file import read_file
from agent.tools.weather import get_weather

ESCAPE = "\x1b"
RESET = ESCAPE + "[0m"
BOLD = ESCAPE + "[1m"
UNDERLINE = ESCAPE + "[4m"


def run_tool(tool_name: str, **kwargs) -> str:
    if tool_name == "get_weather":
        return get_weather(kwargs["location"], kwargs.get("units", "metric"))
    if tool_name == "read_file":
        return read_file(
            kwargs["filepath"], kwargs["start_line"], kwargs.get("end_line", None)
        )
    return ""


def run_agent(model: GPTRequest, messages: JSONListTemplate) -> None:
    stream = model.stream(
        messages=messages.data,
        model=config.get_value("openai.model"),
        stream=config.get_value("openai.stream"),
        seed=config.get_value("openai.seed"),
        max_tokens=config.get_value("openai.max_tokens"),
        temperature=config.get_value("openai.temperature"),
        n=config.get_value("openai.n"),
        top_p=config.get_value("openai.top_p"),
        presence_penalty=config.get_value("openai.presence_penalty"),
        frequency_penalty=config.get_value("openai.frequency_penalty"),
        stop=config.get_value("openai.stop"),
        logit_bias=config.get_value("openai.logit_bias"),
        tools=config.get_value("templates.schemas.tools"),
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
            print()
            print(f"{UNDERLINE}{BOLD}Thinking:{RESET}")
            message["content"] += value

        elif event_type == "reasoning.close":
            print()
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

            print()
            print(f"\n{UNDERLINE}{BOLD}Tool Call:{RESET}")
            print(f"{UNDERLINE}{BOLD}{tool_name}({tool_args}){RESET}:\n{result}")

        sys.stdout.flush()

    if message["content"] and not tool_call_pending:
        messages.append(message)


def run_chat():
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
    session = PromptSession()  # Initialize prompt-toolkit session

    gpt = GPTRequest()
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

            run_agent(gpt, messages)
            print()
            messages.save_json()

        except KeyboardInterrupt:
            print("\nInterrupted.")
            break


def main():
    run_chat()


if __name__ == "__main__":
    main()
