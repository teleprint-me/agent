# agent/llama/router.py
"""
Client side interface for model routing.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Any

from agent.config import config
from agent.llama.requests import LlamaCppRequest


class LlamaCppRouter:
    """
    Thin wrapper around the router endpoints.

    The server keeps a *registry* of aliases → file paths.
    This client lets you query that registry and load/unload models at runtime.
    """

    def __init__(self, llama_request: Optional[LlamaCppRequest] = None):
        self.request = llama_request if llama_request else LlamaCppRequest()
        self.logger = config.get_logger("logger", self.__class__.__name__)
        self.logger.debug("Initialized LlamaCppRouter instance.")

    def models(self) -> List[Dict[str, Any]]:
        """
        Listing all models in cache.
        Metadata includes a field to indicate the status of the model.
        """
        self.logger.debug("Fetching models list")
        response = self.request.get("/models")
        if response.get("object") and response["object"] == "list":
            return response["data"]

    def aliases(self) -> List[str]:
        """Returns a list of cached model aliases."""
        self.logger.debug("Fetching model aliases")
        labels = []
        for model in self.models():
            labels.append(model["id"])
        return labels

    def load(self, alias: str) -> str:
        self.logger.debug(f"Loading {alias} from cache")
        response = self.request.get("/models", {"model": alias})
        if error



if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--n-predict", type=int, default=8080)
    args = parser.parse_args()

    llama_request = LlamaCppRequest(port=args.port)
    llama_router = LlamaCppRouter(llama_request)
    models = llama_router.models()
    print(json.dumps(models, indent=2))

