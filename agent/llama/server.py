# agent/llama/server.py
"""Automate llama-server management"""

import shutil
import time
from pathlib import Path
from subprocess import Popen
from typing import Optional

from requests.exceptions import HTTPError

from agent.config import config
from agent.llama.requests import LlamaCppRequest


class LlamaCppServer:
    def __init__(self, request: Optional[LlamaCppRequest] = None):
        self.request = request if request else LlamaCppRequest()
        self.process = None
        self.logger = config.get_logger("logger", self.__class__.__name__)
        self.logger.debug("Initialized LlamaCppServer instance.")

    def _wait(self, timeout: float = 30.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            try:
                health = self.request.health()
                if health.get("status") == "ok":
                    return True
            except HTTPError:
                pass  # polling server
            time.sleep(0.25)
        return False

    def path(self) -> Path:
        return Path(shutil.which("llama-server"))

    def exists(self) -> bool:
        return self.path().exists()

    def build(cmd: list[str]) -> None:
        # Non-blocking, background process
        self.process = Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,  # important
        )

    def kill(self) -> bool:
        if self.process:
            self.process.kill()
            return True
        return False

    def poll(self, timeout: float = 30.0) -> None:
        self.logger.info("waiting for llama-server")
        if not self._wait(timeout):
            health = self.request.health()
            if health.get("error"):
                error_code = health["error"]["code"]
                error_msg = health["error"]["message"]
                self.logger.error(f"Error ({error_code}): {error_msg}")
            self.logger.error("Server failed to become ready.")
            self.kill()
            exit(1)
        self.logger.info(f"llama-server (pid): {self.process.pid}")


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
