import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path
from typing import Optional

from jsonpycraft import JSONFileErrorHandler, JSONListTemplate
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from requests.exceptions import HTTPError

from agent.config import DEFAULT_PATH_MSGS, config
from agent.llama.client import (
    LlamaCppCompletion,
    LlamaCppProperties,
    LlamaCppRequest,
    LlamaCppRouter,
    LlamaCppServer,
)
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


def classify_event(generator):
    tool_buffer = {}
    args_fragments = []
    reasoning_active = False

    for chunk in generator:
        delta = chunk["choices"][0]["delta"]

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
    model: str,
    completion: LlamaCppCompletion,
    messages: JSONListTemplate,
    registry: ToolRegistry,
) -> None:
    tool_call_pending = False
    message = {"role": "assistant", "content": ""}
    generator = completion.chat(model, messages.data)

    for event in classify_event(generator):
        if event.get("reasoning"):
            message["content"] += event["reasoning"]
            print(event["reasoning"], end="")
        elif event.get("reasoning.open"):
            message["content"] += event["reasoning.open"]
            print(f"\n{BOLD}thinking{RESET}")
            print(event["reasoning.open"], end="")
        elif event.get("reasoning.close"):
            message["content"] += event["reasoning.close"]
            print(f"\n\n{BOLD}completion{RESET}")
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


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Run a selected agent by its router id.")
    parser.add_argument("model", help="Path to the model file")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        default="8080",
        help="Port number (default: 8080)",
    )
    parser.add_argument(
        "--session",
        default=None,
        help="Selected chat context (default: timestamped)",
    )
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Output token-usage (default: False)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # exit early if server is not in users path
    if shutil.which("llama-server") is None:
        print("llama-server is not in $PATH")
        exit(1)

    # get(), post(), or stream() (configures host and port)
    request = LlamaCppRequest(host=args.host, port=args.port)  # This is a singleton
    # start(), stop(), or restart() (inherits host and port from request)
    server = LlamaCppServer(request)  # This is a singleton
    # load() or unload() a model
    router = LlamaCppRouter(request)
    # convenience wrapper for getting model related metadata
    properties = LlamaCppProperties(request)
    # complete() and chat() return generators
    # infill() is a work a progress (not currently implemented)
    completion = LlamaCppCompletion(request)

    # start the server
    if not server.start():  # optionally accepts args (overrides internal config)
        raise RuntimeError("Failed to start server")

    # make sure the model id is registered with the server!
    model = str(Path(args.model).stem)
    if model not in router.ids:  # model ref does not exist
        print(f"[Model Identifiers]")
        for name in router.ids:
            print(f"  {name}")
        server.stop()
        raise ValueError(f"Invalid model selected: {model}")

    # output status
    print("Loading", end="")
    router.load(model)

    # output related server and model metadata
    max_seq_len = properties.max_seq_len(model)
    print(f"pid         -> {server.pid}")
    print(f"alias       -> {properties.alias(model)}")
    print(f"path        -> {properties.path(model)}")
    print(f"max seq len -> {max_seq_len}")
    print(f"ctx size    -> {config.get_value('server.ctx-size', max_seq_len)}")

    # set up the path to the current chat session
    messages_path = config.get_value("messages.path", DEFAULT_PATH_MSGS)
    if args.session:
        messages_path = f"{messages_path}/{args.session}.json"
        print(f"session     -> {args.session}")
    else:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        messages_path = f"{messages_path}/{timestamp}.json"
        print(f"session     -> {timestamp}")

    # create the chat context
    messages = JSONListTemplate(
        messages_path,
        initial_data=[
            {
                "role": "system",
                "content": config.get_value("system.content"),
            },
        ],
    )
    messages.mkdir()

    # if chat context exists, load it, else create a new one
    try:
        messages.load_json()
        print(f"loaded      -> {messages.file_path}\n")
    except JSONFileErrorHandler:
        messages.save_json()
        print(f"created     -> {messages.file_path}\n")

    # create i/o context for user and model
    session = PromptSession(history=FileHistory(config.get_value("history.path")))
    registry = ToolRegistry()
    memory_initialize()

    # output the chat context if it previously existed
    for message in messages.data:
        role = message.get("role")
        content = message.get("content")
        tool_calls = message.get("tool_calls")
        if role:
            print(f"{BOLD}{role}{RESET}")
        if content:
            print(f"{content.strip()}\n")
        if tool_calls:
            for call in tool_calls:
                name = call["function"]["name"]
                arguments = call["function"]["arguments"]
                print(f"{BOLD}{name}({arguments}){RESET}\n")

    previous_prompt = 0
    previous_gen = 0

    while True:
        try:
            if messages.data[-1]["role"] != "tool":
                user_input = session.prompt(
                    "> ",
                    multiline=True,
                    auto_suggest=AutoSuggestFromHistory(),
                )
                messages.append({"role": "user", "content": user_input})
                messages.save_json()

            run_agent(model, completion, messages, registry)
            print()
            messages.save_json()

            if args.metrics:
                prompt = completion.metrics(model)["prompt_tokens_total"]
                generated = completion.metrics(model)["tokens_predicted_total"]

                # track deltas
                dp = prompt - previous_prompt
                dg = generated - previous_gen

                previous_prompt = prompt
                previous_gen = generated

                print(f"\n{BOLD}metrics{RESET}:")
                print(f"  prompt tokens    +{dp}")
                print(f"  generated tokens +{dg}")
                print(f"  total: {prompt + generated}/{max_seq_len}")
                print()  # add padding
        except EOFError:  # Pop the last message
            print(f"\n{BOLD}Popped:{RESET}")
            last = messages.pop(messages.length - 1)
            print(last)
            messages.save_json()

        except KeyboardInterrupt:  # Exit the program
            print("\nQuit", end="")
            router.unload(model)
            server.stop()
            exit(0)

        # Trap unhandled exceptions and output the traceback
        except Exception as e:
            router.unload(model)
            server.stop()
            traceback.print_exception(e)
            exit(1)
