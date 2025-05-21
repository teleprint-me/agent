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

import sys

from agent.api.openai import Model
from agent.tools import tools
from agent.tools.weather import get_weather

ESCAPE = "\x1b"
RESET = ESCAPE + "[0m"
BOLD = ESCAPE + "[1m"
ITALIC = ESCAPE + "[3m"
UNDERLINE = ESCAPE + "[4m"


def main():
    # Sample chat sequence
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

        for event in completion:
            if event[0] == model.THINK_OPEN:
                print(f"{UNDERLINE}{BOLD}Thinking:{RESET}")

            elif event[0] == "reasoning":
                print(f"{ITALIC}{event[1]}{RESET}", end="")

            elif event[0] == model.THINK_CLOSE:
                print()  # End reasoning block (newline)

            elif event[0] == "content":
                print(event[1], end="")

            elif event[0] == "tool_call":
                tool_name, args = event[1], event[2]
                print(f"\n{UNDERLINE}{BOLD}Tool Call:{RESET} ", end="")
                print(f"{ITALIC}{tool_name}({args}){RESET}")

            sys.stdout.flush()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
