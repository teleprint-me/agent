import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from typing import Optional

from jsonpycraft import JSONFileErrorHandler, JSONListTemplate
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from requests.exceptions import HTTPError

from agent.config import config
from agent.llama.api import LlamaCppAPI
from agent.tools.memory import memory_initialize
from agent.tools.registry import ToolRegistry

ESCAPE = "\x1b"
RESET = ESCAPE + "[0m"
BOLD = ESCAPE + "[1m"
UNDERLINE = ESCAPE + "[4m"


def wait_for_server(model: LlamaCppAPI, port: int, timeout: float = 30.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            if model.health.get("status") == "ok":
                return True
        except HTTPError:
            pass  # polling server

        time.sleep(0.25)

    return False


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


def build_parser():
    parser = argparse.ArgumentParser(
        description="Start a llama.cpp server with optional features."
    )

    # Required: model path
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Path to the GGUF model file.",
    )

    # Basic server settings
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Server port (default: 8080).",
    )

    parser.add_argument(
        "--ctx-size",
        type=int,
        default=8192,
        help="Context size to allocate (default: 8192).",
    )

    parser.add_argument(
        "--n-gpu-layers",
        type=int,
        default=99,
        help="Number of layers to offload to GPU (default: 99).",
    )

    parser.add_argument(
        "--n-cpu-moe",
        type=int,
        default=0,
        help="Number of MoE layers to offload to CPU (default: 0)",
    )

    # Feature toggles (boolean flags)
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Enable server metrics (required for some API features).",
    )

    parser.add_argument(
        "--props",
        action="store_true",
        help="Enable global server properties (required for some API features).",
    )

    parser.add_argument(
        "--slots",
        action="store_true",
        help="Enable server statistics (required for some API features).",
    )

    parser.add_argument(
        "--jinja",
        action="store_true",
        help="Enable Jinja prompt templating (required for chat/instruct models).",
    )

    parser.add_argument(
        "--embeddings",
        action="store_true",
        help="Enable embedding mode.",
    )

    # Pooling
    parser.add_argument(
        "--pooling",
        type=str,
        default="none",
        choices=["none", "mean", "cls", "last", "rank"],
        help="Enable embedding pooling. Default: none.",
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Time to wait for the server to spawn.",
    )

    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()

    llama_server = shutil.which("llama-server")
    if not llama_server:
        print("llama-server is not PATH")
        exit(1)

    cmd = [
        llama_server,
        "--port",
        str(args.port),
        "--ctx-size",
        str(args.ctx_size),
        "--n-gpu-layers",
        str(args.n_gpu_layers),
        "-m",
        args.model,
    ]

    if args.metrics:
        cmd.append("--metrics")

    if args.props:
        cmd.append("--props")

    if args.slots:
        cmd.append("--slots")

    if args.jinja:
        cmd.append("--jinja")

    if args.n_cpu_moe > 0:
        cmd.extend(["--n-cpu-moe", args.n_cpu_moe])

    if args.embeddings:
        cmd.append("--embeddings")

    if args.pooling != "none":
        cmd.extend(["--pooling", args.pooling])

    for token in cmd:
        print(token, end=" ")
        sys.stdout.flush()
    print()

    # Non-blocking, background process
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,  # important
    )

    model = LlamaCppAPI()

    print("waiting for server")
    if not wait_for_server(model, args.port, args.timeout):
        if model.health.get("error"):
            error_code = model.health["error"]["code"]
            error_msg = model.health["error"]["message"]
            print(f"Error ({error_code}): {error_msg}")
        print("Server failed to become ready.")
        proc.kill()
        exit(1)

    print(f"Process id {proc.pid}")
    print(f"Model Name {str(model.model_name())}")
    print(f"Model Path {str(model.model_path())}")
    print(f"Vocab Size {str(model.vocab_size())}")
    print(f"Seq Len {args.ctx_size}/{str(model.max_seq_len())}")
    print(f"Max Embed Len {str(model.max_embed_len())}")
    print(f"Prediction limit {model.data['n_predict']}")

    path = config.get_value("messages.path")
    if path is None:
        raise RuntimeError(
            "Missing config: messages.path is required. Please check your config."
        )

    messages = JSONListTemplate(
        path,
        initial_data=[
            {
                "role": "system",
                "content": config.get_value("system.content"),
            },
        ],
    )
    messages.mkdir()

    try:
        messages.load_json()
        print(f"Loaded cache: {messages.file_path}\n")
    except JSONFileErrorHandler:
        messages.save_json()
        print(f"Created cache: {messages.file_path}\n")

    session = PromptSession(history=FileHistory(config.get_value("history.path")))
    registry = ToolRegistry()
    memory_initialize()

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

    while True:
        try:
            if messages.data[-1]["role"] != "tool":
                user_input = session.prompt(
                    "> ",
                    multiline=True,
                    auto_suggest=AutoSuggestFromHistory(),
                )
                if user_input.lower() in ("exit", "quit"):
                    print("Exiting.")
                    break
                messages.append({"role": "user", "content": user_input})
                messages.save_json()

            run_agent(model, messages, registry)
            print()
            messages.save_json()

            # This is a really crappy way to go about this.
            # llama-server has an endpoint for getting this information.
            # should request token count from there instead.
            token_count = 0
            for message in messages.data:
                content = message.get("content")
                tool_calls = message.get("tool_calls")
                if content:
                    token_count += len(model.tokenize(content))
                if tool_calls:
                    for call in tool_calls:
                        name = call["function"]["name"]
                        arguments = call["function"]["arguments"]
                        token_count += len(model.tokenize(name + arguments))
            print(f"\nTokens consumed -> {token_count}/{args.ctx_size}")
        except EOFError:  # Pop the last message
            print(f"\n{BOLD}Popped:{RESET}")
            last = messages.pop(messages.length - 1)
            print(last)
            messages.save_json()

        except KeyboardInterrupt:  # Exit the program
            print("\nQuit.")
            proc.kill()
            exit(0)

        # Trap unhandled exceptions and output the traceback
        except Exception as e:
            proc.kill()
            traceback.print_exception(e)
            exit(1)
