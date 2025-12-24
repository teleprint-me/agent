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
if __name__ == "__main__":
    raise NotImplementedError()
