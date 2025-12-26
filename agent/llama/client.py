# agent/llama/client.py

"""
Copyright © 2025 Austin Berrio
High-level client for performing language model inference.
"""

from typing import Any, Dict, List, Optional, Union, cast

from agent.config import config
from agent.llama.requests import LlamaCppRequest
from agent.llama.router import LlamaCppRouter
from agent.llama.server import LlamaCppServer


class LlamaCppBase:
    def __init__(self, request: Optional[LlamaCppRequest], **kwargs):
        # Get the name of the current class
        cls_name = self.__class__.__name__
        # Set the base component for server communication
        self.request = request
        # Instance for managing llama-server processes
        self.server = LlamaCppServer(request)  # e.g. start(), stop(), restart()
        # Instance for managing model (de)allocation
        self.router = LlamaCppRouter(request)  # e.g. load() and unload()
        # Set the models hyperparameters (mutable dict[str, any])
        self.data = config.get_value("parameters")
        # Sanity check hyperparameters
        if self.data is None:
            raise RuntimeError(f"Set {cls_name} with empty hyperparameters!")
        # Update self.data with any additional parameters from kwargs
        self.data.update(kwargs)
        # Create a custom logging.Logger for the current instance
        self.logger = config.get_logger(key="logger", logger_name=cls_name)
        # Report instance status to logger
        self.logger.debug(f"Initialized {cls_name} instance.")
        # NOTE: Each request must be updated with the current model in mind

    @property
    def model(self) -> Optional[str]:
        """Get the current model"""
        return self.data.get("model")

    @model.setter
    def model(self, value: str):
        """Set the current model"""
        self.data["model"] = value


class LlamaCppTokenizer(LlamaCppBase):
    def __init__(self, request: Optional[LlamaCppRequest], **kwargs):
        super().__init__(request, kwargs)

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


class LlamaCppEmbedding:
    def __init__(self, request: Optional[LlamaCppRequest], **kwargs):
        super().__init__(request, kwargs)


# The primary issue is that we have to pass in the model id for every request
# Using the original base API simplifies a lot of issues.
#   - data: we need to pass in the payload configuring the request
#   - model: we need to specify the model the request will be routed to
#   - router: if the model is not loaded, we must unload a model, then load the selected model
class LlamaCppCompletion:
    def __init__(self, request: Optional[LlamaCppRequest], **kwargs):
        super().__init__(request, kwargs)

    @property
    def prompt(self) -> Optional[Union[str, List[str]]]:
        return self.data.get("prompt", "")

    @prompt.setter
    def prompt(self, value: Union[str, List[str]]):
        self.data["prompt"] = value

    @property
    def messages(self) -> Optional[List[Dict[str, Any]]]:
        return self.data.get("messages", [])

    @messages.setter
    def messages(self, value: List[Dict[str, Any]]):
        self.data["messages"] = value

    # TODO infill(model, prompt)
    def infill(self, model: str, prompt: str):
        pass  # this is complicated, see llama-server doc for info

    # maybe allow overriding n-predict?
    def complete(self, model: str, prompt: Union[str, List[str]]) -> Any:
        """Send a completion request to the API using the given prompt."""
        # probably should verify the model is available in the router
        # TODO
        self.data["model"] = model
        self.data["prompt"] = prompt

        self.logger.debug(f"Completion request payload: {self.data}")

        endpoint = "/v1/completions"
        if self.data.get("stream"):
            self.logger.debug("Streaming completion request")
            return self.request.stream(endpoint=endpoint, data=self.data)
        else:
            self.logger.debug("Sending non-streaming completion request")
            return self.request.post(endpoint=endpoint, data=self.data)

    # TODO chat_completion(model, messages)
    def chat(self, model: str, messages: list[dict[str, str]]):
        pass


# Not sure if this should be a convenience wrapper
# or possibly a dataclass that groups instances for semi-convience?
class LlamaCppClient:
    def __init__(self, request: Optional[LlamaCppRequest] = None):
        # something like this?
        # self.request = request or LlamaCppRequest() # maybe this should be ephemeral?
        # self.server = LlamaCppServer(self.request)
        # self.router = LlamaCppRouter(self.request)
        # self.tokenizer = LlamaCppCompletion(self.request)
        # self.embedding = LlamaCppEmbedding(self.request)
        # self.completion = LlamaCppCompletion(self.request)
        # this feels kinda crowded? maybe expose via read-only properties?
        raise NotImplementedError()  # TODO


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

    parser = ArgumentParser()
    parser.add_argument("model", help="Path to the model file")
    args = parser.parse_args()

    # just reference the internal config for now
    request = LlamaCppRequest()  # this is the base object

    # every instance should probably share the core request object
    # maybe make the request object a singleton? unsure for now.
    server = LlamaCppServer(request)  # managers llama-server
    router = LlamaCppRouter(request)  # manages models
    completion = LlamaCppCompletion(request, n_predict=128)

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
    print("loading", end="")
    router.load(model)  # note: this can be slow. *sigh*

    # this feels super weird. i don't like it.
    # nested refs are gross - completion.completion? like, why? eww.
    # maybe rename the method? but that might be confusing? shit.
    # oooo. maybe completion.generator? hm - maybe a bit too on the nose?
    # nah, i don't like that either. double shit.
    prompt = "Once upon a time,"
    print(prompt, end="")
    generator = completion.completion(model, prompt)
    # hang in there

    # Handle the model's generated response
    content = ""
    for completed in generator:
        token = completed["choices"][0]["text"]
        if token:
            content += token
            # Print each token to the user
            print(token, end="")
            sys.stdout.flush()
    print()  # Add padding to the model's output

    # it's good hygiene to clean up (unnecessary, but good habit)
    print("unloading", end="")
    router.unload(model)

    # stop the server
    server.stop()
