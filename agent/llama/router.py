# agent/llama/router.py
"""
Client side interface for model routing.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from agent.config import config
from agent.llama.requests import LlamaCppRequest
from agent.llama.server import LlamaCppServer


class LlamaCppRouter:
    """
    Thin wrapper around the router endpoints.

    The server keeps a *registry* of aliases → file paths.
    This client lets you query that registry and load/unload models at runtime.
    """

    def __init__(self, llama_request: Optional[LlamaCppRequest] = None):
        self.request = llama_request or LlamaCppRequest()
        self.logger = config.get_logger("logger", self.__class__.__name__)
        self.logger.debug("Initialized LlamaCppRouter instance.")

    @lru_cache
    def models(self) -> List[Dict[str, Any]]:
        """
        Listing all models in cache.
        Metadata includes a field to indicate the status of the model.
        """
        self.logger.debug("Fetching models list")
        return self.request.get("/models")["data"]

    @lru_cache
    def ids(self) -> List[str]:
        """Returns a list of cached model aliases."""
        self.logger.debug("Fetching model aliases")
        return [model["id"] for model in self.models()]

    def load(self, model: str) -> str:
        self.logger.debug(f"Loading {model} from cache")
        return self.request.post("/models/load", {"model": model})

    def unload(self, model: str) -> str:
        self.logger.debug(f"Unloading {model} to cache")
        return self.request.post("/models/unload", {"model", model})


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--n-predict", type=int, default=-1)  # model chooses
    parser.add_argument("--ctx-size", type=int, default=0)  # uses full context
    args = parser.parse_args()

    request = LlamaCppRequest(port=args.port)
    server = LlamaCppServer(request)
    router = LlamaCppRouter(request)

    server.start()
    models = router.models()
    print(json.dumps(models, indent=2))
    server.stop()
