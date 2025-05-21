"""
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

from agent.api.openai import Model
from agent.tools import tools
from agent.tools.weather import get_weather

ESCAPE = "\x1b"
RESET = ESCAPE + "[0m"
BOLD = ESCAPE + "[1m"
ITALIC = ESCAPE + "[3m"
UNDERLINE = ESCAPE + "[4m"


def run_tool(tool_name: str, **kwargs) -> any:
    if tool_name == "get_weather":
        return get_weather(kwargs["location"], kwargs["units"])
    return ""


def run_agent(model: Model, **kwargs: dict[str, any]):
    thoughts = ""
    content = ""
    tool_call_happened = False
    messages = kwargs.get("messages", {})

    stream = model.completion(
        model="gpt-3.5-turbo",
        messages=messages,
        stream=kwargs.get("stream", True),
        temperature=kwargs.get("temperature", 0.8),
        tools=kwargs.get("tools", tools),
    )

    for event in stream:
        event_type = event[0]
        if event_type == model.THINK_OPEN:
            print(f"{UNDERLINE}{BOLD}Thinking:{RESET}")
        elif event_type == "reasoning":
            token = event[1]
            thoughts += token
            print(f"{ITALIC}{token}{RESET}", end="")
        elif event_type == model.THINK_CLOSE:
            print(f"\n{UNDERLINE}{BOLD}Completion:{RESET}")
        elif event_type == "content":
            output = event[1]
            content += output
            print(output, end="")
        elif event_type == "tool_call":
            tool_name, args = event[1], event[2]
            result = run_tool(tool_name, **args)
            messages.append(
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(args),  # MUST be a string
                            },
                        }
                    ],
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "name": tool_name,
                    "content": result,
                }
            )
            tool_call_happened = True
            print(f"{UNDERLINE}{BOLD}Tool Call:{RESET}")
            print(f"{UNDERLINE}{BOLD}{tool_name}({args}){RESET}: {result}")
        sys.stdout.flush()  # Flushing print() is affecting values?

    # Append assistant content message if any
    if content and not tool_call_happened:
        messages.append(
            {
                "role": "assistant",
                "content": content,
            }
        )


def main():
    # Sample chat sequence
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather like in Paris today?"},
    ]

    model = Model()
    try:
        run_agent(
            model,
            messages=messages,
            stream=True,
            temperature=0.8,
            tools=tools,
        )
        run_agent(
            model,
            messages=messages,
            stream=True,
            temperature=0.8,
            tools=tools,
        )
    except Exception as e:
        print(f"Error: {e}")

    print(f"\n{UNDERLINE}{BOLD}Messages:{RESET}")
    for message in messages:
        for k, v in message.items():
            print(f"{k}: {v}")


if __name__ == "__main__":
    main()
