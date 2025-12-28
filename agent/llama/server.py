# agent/llama/server.py
"""
Copyright © 2025 Austin Berrio
Automate llama-server management
"""

import shutil
import time
from logging import Logger
from subprocess import DEVNULL, Popen
from typing import Any, Dict, List, Optional, Set

from jsonpycraft.core import Singleton
from requests.exceptions import HTTPError

from agent.config import config
from agent.llama.requests import LlamaCppRequest


class LlamaCppServerOptions:
    @property
    def config(self) -> Dict[str, Any]:
        return config.get_value("server", {})

    @property
    def path(self) -> str:
        """Absolute path to llama-server, raising if not found."""
        which = shutil.which("llama-server")
        if which is None:
            raise FileNotFoundError("'llama-server' binary missing from $PATH")
        return which

    @property
    def args(self) -> List[str]:
        options = [self.path]
        for k, v in self.config.items():
            if isinstance(v, bool):
                if v:
                    options.append(f"--{k}")
            else:
                options.extend((f"--{k}", str(v)))
        return options

    def execute(self, args: Optional[List[str]] = None) -> Popen:
        """Start a background process."""
        try:
            # Non-blocking, background process
            return Popen(
                self.args if args is None else args,
                stdout=DEVNULL,
                stderr=DEVNULL,
                stdin=DEVNULL,
                start_new_session=True,  # important
            )
        except OSError as e:
            raise RuntimeError(f"Could not spawn llama-server: {e}") from e


class LlamaCppServer(Singleton):
    """Thin wrapper around llama-server binary."""

    def __init__(self, request: Optional[LlamaCppRequest] = None):
        self.request = request or LlamaCppRequest()
        self.options = LlamaCppServerOptions()
        self.process: Optional[Popen] = None
        self.logger: Logger = config.get_logger("logger", self.__class__.__name__)
        self.logger.debug("Initialized LlamaCppServer instance.")

    @property
    def timeout(self) -> int:
        return self.request.timeout

    @property
    def health(self) -> Dict[str, Any]:
        return self.request.health()

    @property
    def pid(self) -> Optional[int]:
        return self.process.pid if self.process else None

    @property
    def path(self) -> str:
        return self.options.path

    def _wait(self) -> bool:
        """Poll the health endpoint until it reports ok or time-outs."""
        start = time.time()
        while (time.time() - start) < self.timeout:
            try:
                if self.health.get("status") == "ok":
                    return True
            except HTTPError:
                pass  # polling server
            time.sleep(0.25)
        return False

    def start(self, args: Optional[List[str]] = None) -> bool:
        """Launch the server and wait until it reports healthy."""
        self.logger.info("Starting llama-server")

        if self.process:
            self.logger.warning(f"Using pid={self.pid} (running)")
            return False

        self.process = self.options.execute(args)
        if not self._wait():
            error_info = "(unknown)"
            if self.health.get("error"):
                error_code = self.health["error"]["code"]
                error_message = self.health["error"]["message"]
                error_info = f"({error_code}) {error_message}"

            self.stop()
            self.logger.error(f"Server failed to become ready: {error_info}")
            return False

        self.logger.info(f"Launched pid={self.pid} (ready)")
        return True

    def stop(self) -> bool:
        """Kill the process if it exists."""

        # no running process
        if not self.process:
            self.logger.warning("No active llama-server process.")
            return False

        pid = self.process.pid
        self.process.terminate()
        self.process.wait(timeout=self.timeout)
        code = self.process.poll()  # returns exit status or None
        self.logger.info(f"Stopped {pid} (exit {code})")
        self.process = None

        return True

    def restart(self, args: Optional[List[str]] = None) -> bool:
        """Convenience helper to stop and start again."""
        self.stop()
        time.sleep(0.25)
        return self.start(args)


# usage example
# note: Model presets allow advanced users to define custom configurations using an .ini file
# llama-server --models-preset ./my-models.ini
if __name__ == "__main__":
    import sys
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("model", help="The model id (e.g. gpt-oss-20b-mxfp4)")
    args = parser.parse_args()

    request = LlamaCppRequest()
    server = LlamaCppServer(request)

    # /usr/local/bin/llama-server
    for token in server.options.args:
        print(token, end=" ")
        sys.stdout.flush()
    print()

    # smoke test starting the server
    assert server.start(), "Failed to start server."
    assert server.health.get("status") == "ok", "Server is unhealthy"
    print(f"Launched server with pid: {server.pid}")

    response = request.get("/models")
    models = response.get("data")
    if models is None:
        print("Error retrieving models")
        print(f"Error: {response.get('error', {}).get('message')}")
        server.stop()
        exit(1)

    model_ids = [model["id"] for model in models]
    for id in model_ids:
        print(f"model id: {id}")

    if args.model not in model_ids:
        print(f"Error: '{args.model}' is not a valid id!")
        server.stop()
        exit(1)

    # smoke test restarting the server
    assert server.restart(), "Failed to restart server"
    assert server.health.get("status") == "ok", "Server is unhealthy"
    print(f"Restarted server with pid: {server.pid}")

    # the model has to be loaded first
    response = request.post("/models/load", {"model": args.model})
    assert response.get("success") is True, f"Failed to load {args.model}"

    # Define the prompt for the model
    prompt = "Once upon a time,"
    print(prompt, end="")

    # Prepare data for streaming request
    data = {
        "model": args.model,
        "prompt": prompt,
        "n_predict": 64,
        "stream": True,
    }

    # Generate the model's response
    generator = request.stream("/completion", data=data)

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
    response = request.post("/models/unload", {"model": args.model})
    assert response.get("success") is True, f"Failed to unload {args.model}"

    assert server.stop(), "Failed to stop server"
    print("Terminated server.")
