# agent/llama/server.py
"""Automate llama-server management"""

import shutil
import time
from logging import Logger
from subprocess import DEVNULL, Popen
from typing import List, Optional

from requests.exceptions import HTTPError

from agent.config import config
from agent.llama.requests import LlamaCppRequest


class LlamaCppServer:
    """Thin wrapper around llama-server binary."""

    def __init__(self, request: Optional[LlamaCppRequest] = None):
        self.request = request or LlamaCppRequest()
        self.process: Optional[Popen] = None
        self.logger: Logger = config.get_logger("logger", self.__class__.__name__)
        self.logger.debug("Initialized LlamaCppServer instance.")

    def _bin(self) -> str:
        """Absolute path to llama-server, raising if not found."""
        path = shutil.which("llama-server")
        if path is None:
            raise FileNotFoundError("'llama-server' binary missing from $PATH")
        return path

    def _options(self) -> List[str]:
        options = []
        pairs = config.get_value("server", {})
        for key, value in pairs.items():
            if isinstance(value, bool) and value:
                options.append(f"--{key}")
            else:
                options.extend((f"--{key}", f"{value}"))
        return options

    def _command(self, path: Optional[str] = None) -> List[str]:
        command = [path or self._bin()]
        command.extend(self._options())
        return command

    def _execute(self, command: List[str]) -> Popen:
        """Start a background process."""
        try:
            # Non-blocking, background process
            return Popen(
                command,
                stdout=DEVNULL,
                stderr=DEVNULL,
                stdin=DEVNULL,
                start_new_session=True,  # important
            )
        except OSError as e:
            raise RuntimeError(f"Could not spawn llama-server: {e}") from e

    def _wait(self) -> bool:
        """Poll the health endpoint until it reports ok or time-outs."""
        start = time.time()
        while (time.time() - start) < self.request.timeout:
            try:
                health = self.request.health()
                if health.get("status") == "ok":
                    return True
            except HTTPError:
                pass  # polling server
            time.sleep(0.5)
        return False

    @property
    def path(self) -> str:
        return self._bin()

    @property
    def pid(self) -> Optional[int]:
        return self.process.pid if self.process else None

    def start(self, command: Optional[List[str]] = None) -> bool:
        """Launch the server and wait until it reports healthy."""
        self.logger.info("Starting llama-server")

        if self.process:
            self.logger.warning(f"Using pid={self.process.pid} (running)")
            return False

        if command:
            self.process = self._execute(command)
        else:
            self.process = self._execute(self._command())

        if not self._wait():
            error_info = "(unknown)"
            health = self.request.health()
            if health.get("error"):
                error_info = f"({health["error"]["code"]}) {health["error"]["message"]}"

            self.stop()
            self.logger.error(f"Server failed to become ready: {error_info}")
            return False

        self.logger.info(f"Launched pid={self.process.pid} (ready)")
        return True

    def stop(self) -> bool:
        """Kill the process if it exists."""

        # no running process
        if not self.process:
            self.logger.warning("No active llama-server process.")
            return False

        pid = self.process.pid
        self.process.terminate()
        self.process.wait(timeout=self.request.timeout)
        code = self.process.poll()  # returns None or exit status
        self.logger.info(f"Stopped {pid} (exit {code})")
        self.process = None

        return True

    def restart(self, command: Optional[List[str]] = None) -> bool:
        """Convenience helper to stop and start again."""
        self.stop()
        time.sleep(0.25)
        return self.start(command)


# usage example
# note: Model presets allow advanced users to define custom configurations using an .ini file
# llama-server --models-preset ./my-models.ini
if __name__ == "__main__":
    import sys
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument(
        "--port",
        default="8080",
        help="Port the server listens from (default: 8080)",
    )
    parser.add_argument(
        "--n-gpu-layers",
        type=int,
        default=-1,
        help="Number of layers stored in VRAM (default: -1)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Path to GGUF model file (default: None)",
    )
    parser.add_argument(
        "--models-dir",
        default=None,
        help="Model directory used by the router (default: None)",
    )
    parser.add_argument(
        "--models-preset",
        default=None,
        help="File used to configure the router (default: None)",
    )
    args = parser.parse_args()

    llama_request = LlamaCppRequest(port=args.port)
    llama_server = LlamaCppServer(llama_request)

    # /usr/local/bin/llama-server
    command = [llama_server.path]

    if args.model:
        # model path to load
        command.extend(["--model", str(args.model)])
    elif args.models_dir:
        # directory containing models for the router server (default: disabled)
        command.extend(["--models-dir", str(args.models_dir)])

    # path to INI file containing model presets for the router server (default: disabled)
    if args.models_preset:
        command.extend(["--models-preset", str(args.models_preset)])
    else:
        # I'm not sure how to handle dynamic context size at runtime
        # --ctx-size: size of the prompt context (default: 0, 0 = loaded from model)
        command.extend(
            [
                # whether to use jinja template engine for chat (default: enabled)
                "--jinja",  # note that the default jinja template injects a system prompt
                # enable prometheus compatible metrics endpoint (default: disabled)
                "--metrics",
                # enable changing global properties via POST /props (default: disabled)
                "--props",
                # expose slots monitoring endpoint (default: enabled)
                "--slots",
                # use single unified KV buffer shared across all sequences (default: enabled if number of slots is auto)
                "--kv-unified",
                # port to listen (default: 8080)
                "--port",
                str(args.port),
                # number of layers to store in VRAM (default: -1)
                "--n-gpu-layers",
                str(args.n_gpu_layers),
            ]
        )

    for token in command:
        print(token, end=" ")
        sys.stdout.flush()
    print()

    assert llama_server.start(command), "Failed to start server."
    print(f"Launched server with pid: {llama_server.pid}")

    assert llama_server.restart(command), "Failed to restart server"
    print(f"Restarted server with pid: {llama_server.pid}")

    assert llama_server.request.health().get("status") == "ok", "Server is unhealthy"

    # the alias for the model to load
    model = "gpt-oss-20b-mxfp4"

    # the model has to be loaded first
    response = llama_request.post("/models/load", {"model": model})
    assert response.get("success") is True, f"Failed to load {model}"

    # Define the prompt for the model
    prompt = "Once upon a time,"
    print(prompt, end="")

    # Prepare data for streaming request
    data = {
        "prompt": prompt,
        "n_predict": 128,
        "stream": True,
        "model": model,
    }

    # Generate the model's response
    generator = llama_request.stream("/completion", data=data)

    # Handle the model's generated response
    content = ""
    for response in generator:
        if "content" in response:
            token = response["content"]
            content += token
            # Print each token to the user
            print(token, end="")
            sys.stdout.flush()

    # Add padding to the model's output
    print()

    # release occupied vram
    response = llama_request.post("/models/unload", {"model": model})
    assert response.get("success") is True, f"Failed to unload {model}"

    assert llama_server.stop(), "Failed to stop server"
    print("Terminated server.")
