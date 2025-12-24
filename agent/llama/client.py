# agent/llama/client.py

"""
Copyright © 2025 Austin Berrio
High-level client for performing language model inference.
"""

from typing import Optional

from agent.config import config
from agent.llama.requests import LlamaCppRequest
from agent.llama.router import LlamaCppRouter
from agent.llama.server import LlamaCppServer


class LlamaCppTokenizer:
    def __init__(self, request: Optional[LlamaCppRequest] = None):
        raise NotImplementedError()


class LlamaCppEmbedding:
    def __init__(self, request: Optional[LlamaCppRequest] = None):
        raise NotImplementedError()


class LlamaCppCompletion:
    def __init__(self, request: Optional[LlamaCppRequest] = None):
        raise NotImplementedError()


class LlamaCppClient:
    def __init__(self, request: Optional[LlamaCppRequest] = None):
        raise NotImplementedError()


# usage example
# model orchestration may be possible by employing a larger model
# to orientate and direct smaller models. this may require observation of
# memory which is not easy to do. i'm considering using a custom API hook
# into ggmls backend to enable getting memory related usage. for now, i just
# kind of have to guess. the backend observation must be hardware agnostic.
# one option that remains simple is to require vulkan which would enable probing
# just about any gpu without having to plugin to complex interface abstractions.
# these operations must occur synchronously. every operation depends upon on
# previous operation and we have to wait for the response before proceeding.
if __name__ == "__main__":
    from argparse import ArgumentParser
    from pathlib import Path

    parser = ArgumentParser()
    parser.add_argument("model", help="Path to the model file")
    args = parser.parse_args()

    # just reference the internal config for now
    request = LlamaCppRequest()  # this is the base object

    # every instance should probably share the core request object
    # maybe make the request object a singleton? unsure for now.
    server = LlamaCppServer(request)  # managers llama-server
    router = LlamaCppRouter(request)  # manages models

    # start the server
    if not server.start():  # optionally accepts args (overrides internal config)
        raise RuntimeError("Failed to start server")

    # the challenge here is deciding how to handle model routing
    # every endpoint will require a model id reference once a model is selected
    # for now, i just employ models/gpt-oss-20b-mxfp4.gguf
    model = str(Path(args.model).stem)
    if model not in router.ids:  # model ref does not exist
        print(f"[Model Identifiers]")
        for id in router.ids:
            print(f"  {id}")
        server.stop()
        raise ValueError(f"Invalid model selected: {model}")

    # once the model is selected, we can load it
    router.load(model)

    # it's good hygiene to clean up (unnecessary, but good habit)
    router.unload(model)

    # stop the server
    server.stop()
