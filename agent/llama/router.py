# agent/llama/router.py
"""
Client side interface for model routing.
"""

from functools import lru_cache
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

    def __init__(self, llama_request: Optional[LlamaCppRequest] = None):
        self.request = llama_request or LlamaCppRequest()
        self.logger = config.get_logger("logger", self.__class__.__name__)
        self.logger.debug("Initialized LlamaCppRouter instance.")

    def _invalidate_cache(self):
        """Clear all cached values after a state change."""
        try:  # the lru_cache decorator exposes `cache_clear`
            type(self).data.cache_clear()
        except AttributeError:  # if you ever remove @lru_cache
            self.logger.debug("Missing LlamaCppRouter cache")

    @lru_cache
    def data(self) -> List[Dict[str, Any]]:
        """
        Listing all models in cache.
        Metadata includes a field to indicate the status of the model.
        """
        self.logger.debug("Fetching models list")
        return self.request.get("/models")["data"]

    @property
    def ids(self) -> List[str]:
        """Returns a list of cached model ids."""
        self.logger.debug("Fetching model ids")
        return [model["id"] for model in self.data()]

    @property
    def args(self) -> List[str]:
        """Returns a list of parameters used to configure the model."""
        self.logger.debug("Fetching model args")
        return [model["status"]["args"] for model in self.data()]

    @property
    def presets(self) -> List[str]:
        """Returns a list of configurable model presets."""
        # note that this is read from and or written to a ini file.
        self.logger.debug("Fetching model presets")
        return [model["status"]["preset"] for model in self.data()]

    @property
    def args_by_id(self) -> Dict[str, List[str]]:
        """Map: id to launch-args list."""
        self.logger.debug("Fetching model args")
        return {m["id"]: m["status"]["args"] for m in self.data()}

    @property
    def presets_by_id(self) -> Dict[str, str]:
        """Map: id to preset string (inherits from args if not defined)."""
        # note that this is read from and or written to a ini file.
        self.logger.debug("Fetching model presets")
        return {m["id"]: m["status"]["preset"] for m in self.data()}

    def load(self, model: str) -> Dict[str, Any]:
        self.logger.debug(f"Loading {model} from cache")
        resp = self.request.post("/models/load", data=dict(model=model))
        self._invalidate_cache()
        return resp

    def unload(self, model: str) -> Dict[str, Any]:
        self.logger.debug(f"Unloading {model} to cache")
        resp = self.request.post("/models/unload", data=dict(model=model))
        self._invalidate_cache()
        return resp


# usage example
# note that each model may be configured individually.
# this allows tuning each model according to its abilities.
if __name__ == "__main__":
    import json
    from argparse import ArgumentParser
    from pathlib import Path

    # stub for now (maybe accept a model id?)
    parser = ArgumentParser()
    parser.add_argument(
        "model",
        help="Path to the model file (e.g. models/gpt-oss-20b-mxfp4.gguf)",
    )
    args = parser.parse_args()

    # original: args.model could be "gpt-oss-20b-mxfp4.gguf" or just "gpt-oss-20b-mxfp4"
    model_id = str(Path(args.model).stem)  # removes ".gguf"

    request = LlamaCppRequest()
    server = LlamaCppServer(request)
    router = LlamaCppRouter(request)

    # server.start()
    # data = router.data()
    # print(json.dumps(data, indent=2))
    # server.stop()

    server.start()

    if model_id not in router.ids:
        print(f"Error: Invalid model id '{model_id}'")
        server.stop()
        exit(1)

    print("Available model ids:")
    for id in router.ids:
        print(id)

    print(f"Selected: {model_id}")
    # -> ['--model', 'models/gpt‑...']
    print(f"Arguments: {router.args_by_id[model_id]}")
    # -> preset text block
    print(f"Presets:\n{router.presets_by_id[model_id]}")

    server.stop()
