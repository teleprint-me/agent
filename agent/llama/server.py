# agent/llama/server.py
"""Automate llama-server management"""

import os
import shutil
import time
from logging import Logger
from pathlib import Path
from subprocess import Popen
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

    @property
    def config(self) -> ConfigurationManager:
        return config

    def _wait(self, timeout: float = 30.0) -> bool:
        """Poll the health endpoint until it reports ok or time-outs."""
        start = time.time()
        while (time.time() - start) < timeout:
            try:
                health = self.request.health()
                if health.get("status") == "ok":
                    return True
            except HTTPError:
                pass  # polling server
            time.sleep(0.25)
        return False

    def _execute(self, cmd: List[str]) -> Popen:
        """Start a background process."""
        try:
            # Non-blocking, background process
            return Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,  # important
            )
        except OSError as e:
            raise RuntimeError(f"Could not spawn llama-server: {e}") from e

    def path(self) -> str:
        """Absolute path to llama-server, raising if not found."""
        bin_path = shutil.which("llama-server") or str()
        if not bin_path:
            raise FileNotFoundError("'llama-server' binary missing from $PATH")
        return bin_path

    def start(self, cmd: List[str], timeout: float = 30.0) -> None:
        """Launch the server and wait until it reports healthy."""
        self.logger.info("Starting llama-server")

        if self.process:
            self.logger.info(f"Using pid={self.process.pid} (running)")
            return False

        self.process = self._execute(cmd)
        self.logger.debug(self.process.stdout.read())

        if not self._wait(timeout):
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
        """Kill the process group if it exists."""
        if self.process:
            self.process.terminate()
            self.process.wait(30.0)
            self.logger.debug(
                f"Stopped {self.process.pid} with exit code {self.process.poll()}"
            )
            self.process = None
            return True
        self.logger.debug("No process currently exists. Ignoring service request.")
        return False

    def restart(self, cmd: List[str], timeout: float = 30.0) -> None:
        """Convenience helper to stop and start again."""
        self.stop()
        time.sleep(1)
        self.start(cmd, timeout)


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
        help="Port the server listens from",
    )
    parser.add_argument(
        "--n-gpu-layers",
        type=int,
        default=-1,
        help="Number of layers stored in VRAM",
    )
    parser.add_argument(
        "--models-dir",
        default=None,
        help="Model directory used by the router",
    )
    parser.add_argument(
        "--models-preset",
        default=None,
        help="File used to configure the router",
    )
    args = parser.parse_args()

    llama_server = LlamaCppServer()
    if not llama_server.exists():
        print("llama-server is not available in the system PATH variable")
        exit(1)

    # I'm not sure how to handle dynamic context size at runtime
    # --ctx-size: size of the prompt context (default: 0, 0 = loaded from model)
    cmd = [
        # /usr/local/bin/llama-server
        llama_server.path(),
        # whether to use jinja template engine for chat (default: enabled)
        "--jinja",
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

    # directory containing models for the router server (default: disabled)
    if args.models_dir:
        cmd.extend(["--models-dir", str(args.models_dir)])

    # path to INI file containing model presets for the router server (default: disabled)
    if args.models_preset:
        cmd.extend(["--models-preset", str(args.models_preset)])

    for token in cmd:
        print(token, end=" ")
        sys.stdout.flush()
    print()
