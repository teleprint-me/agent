# agent/llama/router.py
"""
Copyright © 2025 Austin Berrio
Client side interface for model routing.
"""

import sys
import time
from logging import Logger
from typing import Any, Dict, List, Optional

from agent.config import config
from agent.llama.requests import LlamaCppRequest
from agent.llama.server import LlamaCppServer


class LlamaCppRouter:
    """
    Thin wrapper around the router endpoints.

    The server keeps a *registry* of aliases → file paths.
    This client lets you query that registry and load/unload models at runtime.
    """

    def __init__(self, request: Optional[LlamaCppRequest] = None):
        self.request = request if request else LlamaCppRequest()

        cls_name = self.__class__.__name__
        self.logger: Logger = config.get_logger("logger", cls_name)
        self.logger.debug(f"Initialized {cls_name} instance.")

    @property
    def data(self) -> List[Dict[str, Any]]:
        """List all registered models and their associated metadata."""
        self.logger.debug("Fetching models list")
        resp = self.request.get("/models")
        return resp.get("data", [])

    @property
    def ids(self) -> List[str]:
        """Returns a list of cached model ids."""
        self.logger.debug("Fetching model ids")
        return [model["id"] for model in self.data]

    @property
    def args_by_id(self) -> Dict[str, List[str]]:
        """Map: id to args list."""
        self.logger.debug("Fetching model args")
        return {m["id"]: m["status"]["args"] for m in self.data}

    @property
    def presets_by_id(self) -> Dict[str, str]:
        """Map: id to preset string (inherits from args if not defined)."""
        # note that this is read from and or written to a ini file.
        self.logger.debug("Fetching model presets")
        return {m["id"]: m["status"]["preset"] for m in self.data}

    @property
    def loaded_by_id(self) -> Dict[str, str]:
        """Map: id to status value string ("loaded" or "unloaded")"""
        return {m["id"]: m["status"]["value"] for m in self.data}

    def _wait(self, model: str, stop: str):
        """Poll the cached model loading status"""
        while self.loaded_by_id[model] != stop:
            print(".", end="")
            sys.stdout.flush()
            time.sleep(0.25)  # sleep ~250ms while (de)allocating
        print()

    def load(self, model: str) -> Dict[str, Any]:
        """Load a cached model into memory"""
        self.logger.debug(f"Loading {model} from cache")
        resp = self.request.post("/models/load", data=dict(model=model))

        if resp.get("success", False):
            self._wait(model, "loaded")

        return resp

    def unload(self, model: str) -> Dict[str, Any]:
        """Unload a cached model from memory"""
        self.logger.debug(f"Unloading {model} to cache")
        resp = self.request.post("/models/unload", data=dict(model=model))

        if resp.get("success", False):  # returns True if successful
            self._wait(model, "unloaded")

        return resp


# usage example
# note that each model may be configured individually.
# this allows tuning each model according to its abilities.
if __name__ == "__main__":
    import json
    from argparse import ArgumentParser
    from pathlib import Path

    from requests.exceptions import HTTPError

    # stub for now (maybe accept a model id?)
    parser = ArgumentParser()
    parser.add_argument("model", help="The model path or id")
    parser.add_argument("--port", default="8080", help="Port to listen (default: 8080)")
    args = parser.parse_args()

    # original: args.model could be "gpt-oss-20b-mxfp4.gguf" or just "gpt-oss-20b-mxfp4"
    model = str(Path(args.model).stem)  # removes ".gguf"

    request = LlamaCppRequest(port=args.port)
    server = LlamaCppServer(request)
    router = LlamaCppRouter(request)

    server.start()

    # Ensure input is a registered model id
    if model not in router.ids:
        print(f"Error: Invalid model id '{model}'")
        server.stop()
        exit(1)

    # Input model id is validated
    print(f"Selected ID: {model}\n")

    # Output model ids
    print("Model IDs:")
    for id in router.ids:
        print(f"  {id}")
    print()

    # Output model preset text block
    print(f"Model Preset:")
    for line in router.presets_by_id[model].strip().splitlines(keepends=True):
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            print(line)
        else:
            print(f"  {line}")
    print()

    try:
        # first load the model and report status
        print(f"Status: Loading {model}.")
        status = router.load(model)
        print(f"{model} -> {router.loaded_by_id[model]}")
        print(f"success? {status['success']}")
        print()  # pad output
    except KeyboardInterrupt:  # If the program hangs, enable clean exit
        server.stop()  # clean up
        exit(1)  # no traceback needed

    # then unload the model and report status
    try:
        print(f"Status: Unloading {model}.")
        router.unload(model)
        print(f"{model} -> {router.loaded_by_id[model]}")
        print(f"success? {status['success']}")
    except (KeyboardInterrupt, HTTPError) as e:  # server reporting "loading"?
        server.stop()  # clean up
        raise Exception(e) from e  # output traceback

    server.stop()
