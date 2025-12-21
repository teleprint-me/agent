# agent/llama/server.py
"""Automate llama-server management"""

import shutil
import time
from subprocess import Popen
from typing import Optional

from agent.config import config
from agent.llama.requests import LlamaCppRequest


class LlamaCppServer:
    def __init__(self, request: Optional[LlamaCppRequest] = None):
        self.request = request if request else LlamaCppRequest()
        self.binary = shutil.which("llama-server")
        self.process = None

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

    def has_binary(self) -> bool:
        return True if self.binary else False

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
        print("waiting for server")
        if not self._wait(timeout):
            health = self.request.health()
            if health.get("error"):
                error_code = model.health["error"]["code"]
                error_msg = model.health["error"]["message"]
                print(f"Error ({error_code}): {error_msg}")
            print("Server failed to become ready.")
            self.kill()
            exit(1)
        print(f"llama-server (pid): {self.process.pid}")


# usage example
# note: Model presets allow advanced users to define custom configurations using an .ini file
# llama-server --models-preset ./my-models.ini
if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--n-gpu-layers", type=int, default=-1)
    parser.add_argument("--models-dir", default=None)
    parser.add_argument("--models-preset", default=None)
    args = parser.parse_args()

    cmd = [
        llama_server,
        # port to listen (default: 8080)
        "--port",
        str(args.port),
        # number of layers to store in VRAM (default: -1)
        "--n-gpu-layers",
        str(args.n_gpu_layers),
    ]

    # directory containing models for the router server (default: disabled)
    if args.model_dir:
        cmd.extend(["--models-dir", str(args.models_dir)])

    # path to INI file containing model presets for the router server (default: disabled)
    if args.model_preset:
        cmd.extend(["--models-preset", str(args.models_preset)])

    for token in cmd:
        print(token, end=" ")
        sys.stdout.flush()
    print()

    llama_server = LlamaCppServer()
    if llama_server.has_binary():
        print("llama-server is not available in the system PATH variable")
        exit(1)
