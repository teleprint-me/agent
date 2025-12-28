# agent/llama/client.py

"""
Copyright © 2025 Austin Berrio
High-level client for performing language model inference.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union, cast

import regex as re
from requests.exceptions import HTTPError

from agent.config import config
from agent.llama.requests import LlamaCppRequest
from agent.llama.router import LlamaCppRouter
from agent.llama.server import LlamaCppServer


class LlamaCppBase:
    def __init__(self, request: Optional[LlamaCppRequest] = None, **kwargs):
        # Get the name of the current class
        cls_name = self.__class__.__name__
        # Set the base component for server communication
        self.request = request or LlamaCppRequest()
        # Set the models hyperparameters (mutable dict[str, any])
        self.params = config.get_value("parameters")
        # Sanity check hyperparameters
        if self.params is None:
            self.server.stop()  # stop the server if a process exists
            raise RuntimeError(f"Set {cls_name} with empty hyperparameters!")
        # Update with any additional parameters from kwargs
        self.params.update(kwargs)
        # Create a custom logging.Logger for the current instance
        self.logger = config.get_logger(key="logger", logger_name=cls_name)
        # Report instance status to logger
        self.logger.debug(f"Initialized {cls_name} instance.")
        # NOTE: Each request must be updated with the current model in mind

    @property
    def model(self) -> Optional[str]:
        """Get the current model"""
        return self.params.get("model")

    @model.setter
    def model(self, value: str):
        """Set the current model"""
        self.params["model"] = value


# Not sure if this should be in the router?
# the server must have been started with `--props` flag enabled.
# otherwise, the server returns an error.
class LlamaCppProperties(LlamaCppBase):
    def __init__(self, request: Optional[LlamaCppRequest], **kwargs):
        super().__init__(request, **kwargs)

    def props(self, model: str) -> Dict[str, Any]:
        return self.request.get("/props", params=dict(model=model))

    def model_path(self, model: str) -> Optional[str]:
        props = self.props(model)
        return props.get("model_path")

    def max_seq_len(self, model: str) -> Optional[int]:
        props = self.props(model)
        settings = props.get("default_generation_settings", {})
        return settings.get("n_ctx")

    def chat_template(self, model: str) -> Optional[str]:
        """Get the models jinja template."""
        # not sure if should return a jinja.Template or let the caller handle it.
        # it's easier to just return it as a raw string for now.
        props = self.props(model)
        return props.get("chat_template")

    def is_sleeping(self, model: str) -> Optional[bool]:
        props = self.props(model)
        return props.get("is_sleeping")


class LlamaCppTokenizer(LlamaCppBase):
    def __init__(self, request: Optional[LlamaCppRequest], **kwargs):
        super().__init__(request, **kwargs)

    def encode(
        self,
        model: str,
        content: Union[str, List[str]],
        add_special: bool = False,
        with_pieces: bool = False,
    ) -> List[int]:
        """Tokenizes a given text using the server's tokenize endpoint."""
        self.logger.debug(f"Tokenizing: {content}")

        prompts: List[str] = []
        if isinstance(content, str):
            self.logger.debug("Encoding str to int")
            prompts = cast(List[str], [content])
        elif all(isinstance(prompt, str) for prompt in content):
            self.logger.debug("Encoding prompts to sequence")
            prompts = cast(List[str], content)
        else:
            self.logger.error("Content is not a list with str")
            raise TypeError("Content must contain str or list[str]")

        data = {
            "model": model,
            "content": content,
            "add_special": add_special,
            "with_pieces": with_pieces,
        }

        response = self.request.post("/tokenize", data=data)
        return response.get("tokens", [])

    def decode(
        self,
        model: str,
        pieces: List[Union[int, Dict[str, Union[int, str]]]],
    ) -> str:
        """Detokenizes a given sequence of token IDs using the server's detokenize endpoint."""
        self.logger.debug(f"Decoding: {pieces}")
        if not isinstance(pieces, list):
            raise TypeError("Pieces must be a list")

        tokens: List[int] = []
        if all(isinstance(piece, int) for piece in pieces):
            self.logger.debug("Decoding pieces as 'list' with 'int'")
            tokens = cast(List[int], pieces)
        elif all(isinstance(piece, dict) for piece in pieces):
            self.logger.debug("Decoding pieces as 'dict' with 'id' and 'piece' keys")
            tokens = cast(List[int], [piece["id"] for piece in pieces])
        else:
            self.logger.debug("Pieces is not a list with int or dict[str, int|str]")
            raise TypeError("Pieces must contain int or dict[str, int|str]")
        data: Dict[str, List[int]] = {"tokens": tokens}

        # Pieces must resolve to a list of integers
        response = self.request.post("/detokenize", data=data)
        return response.get("content", "")


class LlamaCppEmbedding(LlamaCppBase):
    def __init__(self, request: Optional[LlamaCppRequest], **kwargs):
        super().__init__(request, **kwargs)

    def embeddings(self, model: str, input: Union[str, List[str]]) -> Any:
        """Get the embedding for the given input."""
        self.logger.debug(f"Fetching embedding for input: {input}")
        endpoint = "/v1/embeddings"
        data = {
            "model": model,
            "input": input,
            "encoding_format": "float",
        }
        return self.request.post(endpoint, data)


# The primary issue is that we have to pass in the model id for every request
# Using the original base API simplifies a lot of issues.
#   - data: we need to pass in the payload configuring the request
#   - model: we need to specify the model the request will be routed to
#   - router: if the model is not loaded, we must unload a model, then load the selected model
class LlamaCppCompletion(LlamaCppBase):
    def __init__(self, request: Optional[LlamaCppRequest], **kwargs):
        super().__init__(request, **kwargs)

    @property
    def prompt(self) -> Optional[Union[str, List[str]]]:
        return self.params.get("prompt", "")

    @prompt.setter
    def prompt(self, value: Union[str, List[str]]):
        self.params["prompt"] = value

    @property
    def messages(self) -> Optional[List[Dict[str, Any]]]:
        return self.params.get("messages", [])

    @messages.setter
    def messages(self, value: List[Dict[str, Any]]):
        self.params["messages"] = value

    @property
    @lru_cache
    def _metrics_re(self) -> re.Regex:
        return re.compile(r"^([^ {]+)(?:\{([^}]*)\})?\s+([+-]?\d+(?:\.\d+)?)$")

    # maybe abstract this into its own private helper function?
    def _metrics_parse(self, content: str) -> Dict[str, Any]:
        # @note this format is terrible as a response object.
        # @see https://prometheus.io/docs/instrumenting/exposition_formats/
        data = {}

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            m = self._metrics_re.match(line)
            if not m:
                self.logger.debug(f"Malformed expression: {m}")
                continue

            namespace, label_text, value_text = m.groups()

            # strip namespace prefix (i.e. llamacpp:)
            name = namespace.split(":")[-1]
            value = float(value_text) if "." in value_text else int(value_text)

            if label_text:
                labels = {}
                for item in label_text.split(","):
                    k, v = item.split("=", 1)
                    labels[k] = v.strip('"')
                data[name] = {"value": value, "labels": labels}
            else:
                data[name] = value

        return data

    def metrics(self, model: str) -> Dict[str, Any]:
        """Prometheus compatible metrics exporter."""
        self.model = model

        try:
            self.logger.debug("Fetching server metrics")
            content: str = self.request.get("/metrics", params=dict(model=self.model))
            return self._metrics_parse(content)
        except HTTPError as e:
            self.logger.debug("Error fetching server metrics")
            return self.request.error(501, e, "unavailable_error")

    # TODO
    def infill(self, model: str, context: Dict[str, Any]) -> Any:
        """Accept a prefix and a suffix and return the predicted completion as stream."""
        # @see Qwen2.5-Coder TR: https://arxiv.org/pdf/2409.12186
        pass  # @see llama-server doc for additional info

    # maybe allow overriding n-predict?
    def complete(self, model: str, prompt: Union[str, List[str]]) -> Any:
        """Send a completion request to the API using the given prompt."""
        self.model = model
        self.prompt = prompt

        self.logger.debug(f"Completion request payload: {self.params}")

        endpoint = "/v1/completions"
        if self.params.get("stream"):
            self.logger.debug("Streaming completion request")
            return self.request.stream(endpoint=endpoint, data=self.params)
        else:
            self.logger.debug("Sending non-streaming completion request")
            return self.request.post(endpoint=endpoint, data=self.params)

    def chat(self, model: str, messages: list[dict[str, str]]) -> Any:
        """Send a ChatML-compatible chat completion request to the API."""
        self.model = model
        self.messages = messages

        self.logger.debug(f"Sending chat completion request with messages: {messages}")

        endpoint = "/v1/chat/completions"
        if self.params.get("stream"):
            self.logger.debug("Streaming chat completion request")
            return self.request.stream(endpoint=endpoint, data=self.params)
        else:
            self.logger.debug("Sending non-streaming chat completion request")
            return self.request.post(endpoint=endpoint, data=self.params)


# Not sure if this should be a convenience wrapper
# or possibly a dataclass that groups instances for semi-convience?
class LlamaCppClient:
    def __init__(self, request: LlamaCppRequest, **kwargs):
        # Singleton for managing llama-server processes
        self.server = LlamaCppServer(request)  # e.g. start(), stop(), restart()
        # Instance for managing model (de)allocation
        self.router = LlamaCppRouter(request)  # e.g. load() and unload()
        # Get model specific properties based on server configuration
        self.properties = LlamaCppProperties(request, **kwargs)
        # Convenience wrappers for managing models
        self.tokenizer = LlamaCppCompletion(request, **kwargs)
        self.embedding = LlamaCppEmbedding(request, **kwargs)
        self.completion = LlamaCppCompletion(request, **kwargs)


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
    import sys
    from argparse import ArgumentParser
    from pathlib import Path

    # from requests.exceptions import HTTPError

    parser = ArgumentParser()
    parser.add_argument("model", help="Path to the model file")
    args = parser.parse_args()

    # just reference the internal config for now
    client = LlamaCppClient(request=LlamaCppRequest(), n_predict=128)

    # start the server
    if not client.server.start():  # optionally accepts args (overrides internal config)
        raise RuntimeError("Failed to start server")

    # the challenge here is deciding how to handle model routing
    # every endpoint will require a model id reference once a model is selected
    # for now, i just employ the models file path
    model = str(Path(args.model).stem)
    if model not in client.router.ids:  # model ref does not exist
        print(f"[Model Identifiers]")
        for id in client.router.ids:
            print(f"  {id}")
        client.server.stop()
        raise ValueError(f"Invalid model selected: {model}")

    # once the model is selected, we can load it
    print("loading", end="")
    client.router.load(model)  # note: this can be slow. *sigh*

    # output model properties
    print("model properties:")
    print(f"  ID: {model}")
    print(f"  Path: {client.properties.model_path(model)}")
    print(f"  Max Seq Len: {client.properties.max_seq_len(model)}")
    print(f"  Sleeping: {client.properties.is_sleeping(model)}")
    print()  # add padding

    # set up the model prompt and generator
    prompt = "Once upon a time,"
    print(prompt, end="")
    generator = client.completion.complete(model, prompt)

    # Handle the model's generated response
    content = ""
    for completed in generator:
        token = completed["choices"][0]["text"]
        if token:
            content += token
            # Print each token to the user
            print(token, end="")
            sys.stdout.flush()
    print()  # add padding

    # output model completion stats
    current_prompt = client.completion.metrics(model)["prompt_tokens_total"]
    generated = client.completion.metrics(model)["tokens_predicted_total"]

    previous_prompt = 0
    previous_gen = 0

    # track deltas
    dp = current_prompt - previous_prompt
    dg = generated - previous_gen

    previous_prompt = current_prompt
    previous_gen = generated

    print()
    print(f"metrics:")
    print(f"  prompt tokens    +{dp}")
    print(f"  generated tokens +{dg}")
    print(f"  total: {current_prompt + generated}")
    print()  # add padding

    # it's good hygiene to clean up (unnecessary, but good habit)
    print("unloading", end="")
    client.router.unload(model)

    # stop the server
    client.server.stop()
