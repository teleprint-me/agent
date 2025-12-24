# agent/llama/client.py

"""
Copyright © 2025 Austin Berrio
High-level client for performing language model inference.
"""

from typing import Any, Optional

from agent.config import config
from agent.llama.requests import LlamaCppRequest
from agent.llama.router import LlamaCppRouter
from agent.llama.server import LlamaCppServer


class LlamaCppTokenizer:
    def __init__(self, request: Optional[LlamaCppRequest] = None):
        raise NotImplementedError()  # TODO


class LlamaCppEmbedding:
    def __init__(self, request: Optional[LlamaCppRequest] = None):
        raise NotImplementedError()  # TODO


# The primary issue is that we have to pass in the model id for every request
# Using the original base API simplifies a lot of issues.
#   - data: we need to pass in the payload configuring the request
#   - model: we need to specify the model the request will be routed to
#   - router: if the model is not loaded, we must unload a model, then load the selected model
class LlamaCppCompletion:
    def __init__(self, request: Optional[LlamaCppRequest] = None, **kwargs):
        self.request = request

        # Set model hyperparameters dict[str, any]
        self.data = config.get_value("model")
        # Sanity check hyperparameters
        assert self.data is not None
        # Update self.data with any additional parameters from kwargs
        self.data.update(kwargs)

        # Setup logger
        self.logger = config.get_logger("logger", self.__class__.__name__)
        self.logger.debug("Initialized LlamaCppAPI instance.")

    # i have no idea what i'm doing here :p
    def select(self, model: str):
        # we can't mutate the internal payload, so make a copy
        data = self.data.copy()
        # probably should verify the model is available in the router
        # TODO
        # we need to add the model to the payload
        data["model"] = model
        return data  # profit ???

    # maybe allow overriding n-predict?
    def completion(self, model: str, prompt: str) -> Any:
        """Send a completion request to the API using the given prompt."""
        self.logger.debug(f"Sending completion request with prompt: {prompt}")
        self.data["prompt"] = prompt
        self.logger.debug(f"Completion request payload: {self.data}")

        # don't mutate internal data!
        data = self.select(model)  # this feels weird and dishonest :|

        endpoint = "/v1/completions"
        if self.data.get("stream"):
            self.logger.debug("Streaming completion request")
            return self.request.stream(endpoint=endpoint, data=data)
        else:
            self.logger.debug("Sending non-streaming completion request")
            return self.request.post(endpoint=endpoint, data=data)

    # TODO chat_completion(model, messages)


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
    router.unload(model)

    # stop the server
    server.stop()
