# agent/llama/server.py
"""
Copyright © 2025 Austin Berrio
Automate llama-server management
"""

import shutil
import time
from logging import Logger
from subprocess import DEVNULL, Popen
from typing import Any, Dict, List, Optional

from jsonpycraft.core import Singleton
from requests.exceptions import HTTPError

from agent.config import config
from agent.llama.requests import LlamaCppRequest


class LlamaCppServerCommand(Singleton):
    def __init__(self, request: Optional[LlamaCppRequest] = None):
        self.request = request if request else LlamaCppRequest()

    @property
    def host(self) -> str:
        return str(self.request.host)

    @property
    def port(self) -> str:
        return str(self.request.port)

    @property
    def timeout(self) -> int:
        return int(self.request.timeout)

    @property
    def health(self) -> Dict[str, Any]:
        return self.request.health()

    @property
    def path(self) -> str:
        """Absolute path to llama-server, raising if not found."""
        which = shutil.which("llama-server")
        if which is None:
            raise FileNotFoundError("'llama-server' binary missing from $PATH")
        return which

    @property
    def args(self) -> List[str]:
        """Returns a pre-built set of command arguments to execute"""
        command = [self.path, "--host", self.host, "--port", self.port]
        for k, v in config.get_value("server", {}).items():
            if k == "host" or k == "port":
                continue  # skip duplicates
            if isinstance(v, bool) and v is False:
                continue  # skip unset flags
            if isinstance(v, bool) and v is True:
                command.append(f"--{k}")  # add set flags
            else:  # option accepts an argument
                command.extend((f"--{k}", str(v)))
        return command

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


class LlamaCppServer(LlamaCppServerCommand):
    """Thin wrapper around llama-server binary."""

    def __init__(self, request: Optional[LlamaCppRequest] = None):
        super().__init__(request)

        self.process: Optional[Popen] = None
        self.logger: Logger = config.get_logger("logger", self.__class__.__name__)
        self.logger.debug("Initialized LlamaCppServer instance.")

    @property
    def pid(self) -> Optional[int]:
        """Returns the process identifier, otherwise None"""
        return self.process.pid if self.process else None

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

        if self.process and self.process.pid:
            self.logger.warning(f"Using pid={self.pid} (running)")
            return False

        self.process = self.execute(args)
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
    from pathlib import Path

    parser = ArgumentParser()
    parser.add_argument("model", help="The model path or id")
    parser.add_argument("--port", default="8080", help="Port to listen (default: 8080)")
    args = parser.parse_args()

    # Get the models base name
    model = str(Path(args.model).stem)

    # Create a custom request and server
    request = LlamaCppRequest(port=args.port)
    server = LlamaCppServer(request)

    # Flush out the default command
    for token in server.args:
        print(token, end=" ")
        sys.stdout.flush()
    print()

    # smoke test starting the server
    if not server.start():
        raise RuntimeError("Failed to start server.")

    # smoke test the servers health
    if server.health.get("status") != "ok":
        server.stop()
        raise RuntimeError("Server is unhealthy")

    print(f"Launched server with pid: {server.pid}")

    # get metadata for models registered with the server
    response = request.get("/models")
    # extract the metadata for the registered models
    data = response.get("data")
    # ensure the response data is valid
    if data is None:
        print("Error retrieving model data")
        print(f"Error: {response.get('error', {}).get('message')}")
        server.stop()
        exit(1)

    # extract the model identifiers from the response
    model_ids = [m["id"] for m in data]
    for name in model_ids:
        print(f"model id: {name}")

    # assert the input model id matches the servers model registration
    if model not in model_ids:
        print(f"Error: '{model}' is not a valid id!")
        server.stop()
        exit(1)

    # smoke test restarting the server
    if not server.restart():
        server.stop()  # something went wrong, kill the process
        raise RuntimeError("Failed to restart server")

    # smoke test the servers health
    if server.health.get("status") != "ok":
        server.stop()
        raise RuntimeError("Server is unhealthy")

    print(f"Restarted server with pid: {server.pid}")

    # load the model using the input identifier
    response = request.post("/models/load", {"model": model})
    # assert the model is in memory
    if not response.get("success"):
        server.stop()
        raise RuntimeError(f"Failed to load {model}")

    # Define the prompt for the model
    prompt = "Once upon a time,"
    print(prompt, end="")

    # Prepare data for streaming request
    load = {
        "model": model,
        "prompt": prompt,
        "n_predict": 64,
        "stream": True,
    }

    # Generate the model's response
    generator = request.stream("/completion", data=load)

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

    # unload the model using the input identifier
    response = request.post("/models/unload", {"model": model})
    # assert the model was freed from memory
    if not response.get("success"):
        server.stop()
        raise RuntimeError(f"Failed to unload {model}")

    # assert the servers process is terminated
    if not server.stop():
        raise RuntimeError("Failed to stop server")

    # successfully started, restarted, and stopped the server
    print("Terminated server.")
