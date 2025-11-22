"""
Copyright © 2023 Austin Berrio

Module: agent.backend.llama.api

Description: High-level Requests API for interacting with the LlamaCpp REST API.
"""

from pathlib import Path
from typing import Any, Dict, List, Union

import requests

from agent.config import config
from agent.llama.requests import LlamaCppRequest


# See agent.config.__init__ for details
class LlamaCppAPI:
    def __init__(self, llama_request: LlamaCppRequest = None, **kwargs: Any):
        """Initialize the API with default model parameters and request handler."""
        # Setup request object
        self.request = llama_request if llama_request else LlamaCppRequest()

        # Set model hyperparameters dict[str, any]
        self.data = config.get_value("model")
        # Sanity check hyperparameters
        assert self.data is not None
        # Update self.data with any additional parameters from kwargs
        self.data.update(kwargs)

        # Setup logger
        self.logger = config.get_logger("logger", self.__class__.__name__)
        self.logger.debug("Initialized LlamaCppAPI instance.")

    def error(self, code: int, message: str, type: str) -> dict[str, Any]:
        """Return a dictionary representing an error response."""
        return {"error": {"code": code, "message": message, "type": type}}

    @property
    def health(self) -> Dict[str, Any]:
        """Check the health status of the API."""
        try:
            self.logger.debug("Fetching health status")
            return self.request.get("/health")
        except requests.exceptions.ConnectionError as e:
            self.logger.debug(f"Connection error while fetching health status: {e}")
            return self.error(500, e, "unavailable_error")

    @property
    def slots(self) -> List[Dict[str, Any]]:
        """Get the current slots processing state."""
        try:
            self.logger.debug("Fetching slot states")
            return self.request.get("/slots")
        except requests.exceptions.HTTPError as e:
            self.logger.debug("Error fetching slot states")
            return self.error(501, e, "unavailable_error")

    @property
    def models(self) -> dict[str, Any]:
        """Get the language model's file path for the given slot."""
        self.logger.debug("Fetching models list")
        return self.request.get("/v1/models")

    def model_path(self, slot: int = 0) -> Path:
        return Path(self.models["data"][slot]["id"])

    def model_name(self, slot: int = 0) -> str:
        return self.model_path(slot).parent.name

    def vocab_size(self, slot: int = 0) -> int:
        """Get the language model's vocab size."""
        return self.models["data"][slot]["meta"]["n_vocab"]

    def max_seq_len(self, slot: int = 0) -> int:
        """Get the language model's max context length."""
        return self.models["data"][slot]["meta"]["n_ctx_train"]

    def max_embed_len(self, slot: int = 0) -> int:
        """Get the language model's max positional embeddings."""
        return self.models["data"][slot]["meta"]["n_embd"]

    def tokenize(
        self,
        content: str,
        add_special: bool = False,
        with_pieces: bool = False,
    ) -> List[int]:
        """Tokenizes a given text using the server's tokenize endpoint."""
        self.logger.debug(f"Tokenizing: {content}")
        data = {
            "content": content,
            "add_special": add_special,
            "with_pieces": with_pieces,
        }
        response = self.request.post("/tokenize", data=data)
        return response.get("tokens", [])

    def detokenize(
        self, pieces: Union[List[int], List[Dict[str, Union[int, str]]]]
    ) -> str:
        """Detokenizes a given sequence of token IDs using the server's detokenize endpoint."""
        self.logger.debug(f"Detokenizing: {pieces}")
        if isinstance(pieces, list) and isinstance(pieces[0], dict):
            self.logger.debug("Decoding pieces with 'id' and 'piece' keys")
            # If pieces is a list of dictionaries, extract the 'id' values
            pieces = [piece["id"] for piece in pieces]
        data = {"tokens": pieces}
        response = self.request.post("/detokenize", data=data)
        return response.get("content", "")

    def embeddings(self, content: str) -> Any:
        """Get the embedding for the given input."""
        self.logger.debug(f"Fetching embedding for input: {content}")
        endpoint = "/v1/embeddings"
        data = {
            "input": content,
            "model": "text-embedding-3-small",
            "encoding_format": "float",
        }
        return self.request.post(endpoint, data)

    def completion(self, prompt: str) -> Any:
        """Send a completion request to the API using the given prompt."""
        self.logger.debug(f"Sending completion request with prompt: {prompt}")
        self.data["prompt"] = prompt
        self.logger.debug(f"Completion request payload: {self.data}")

        endpoint = "/v1/completions"
        if self.data.get("stream"):
            self.logger.debug("Streaming completion request")
            return self.request.stream(endpoint=endpoint, data=self.data)
        else:
            self.logger.debug("Sending non-streaming completion request")
            return self.request.post(endpoint=endpoint, data=self.data)

    def chat_completion(self, messages: List[Dict[str, str]]) -> Any:
        """Send a ChatML-compatible chat completion request to the API."""
        self.logger.debug(f"Sending chat completion request with messages: {messages}")
        self.data["messages"] = messages

        endpoint = "/v1/chat/completions"
        if self.data.get("stream"):
            self.logger.debug("Streaming chat completion request")
            return self.request.stream(endpoint=endpoint, data=self.data)
        else:
            self.logger.debug("Sending non-streaming chat completion request")
            return self.request.post(endpoint=endpoint, data=self.data)


if __name__ == "__main__":
    import argparse
    import json
    import sys  # Allow streaming to stdout

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n",
        "--predict",
        type=int,
        default=128,
        help="Tokens generated.",
    )
    parser.add_argument(
        "-s",
        "--slots",
        action="store_true",
        help="Enable debugging",
    )
    args = parser.parse_args()

    # Create an instance of LlamaCppAPI
    llama_api = LlamaCppAPI(n_predict=args.predict)

    if args.slots:
        print("Health:", json.dumps(llama_api.health, indent=2))
        print("Models:", json.dumps(llama_api.models, indent=2))
        print("Slots:", json.dumps(llama_api.slots, indent=2))

    # Example: Get model file path for a specific slot
    slot_index = 0
    print(f"Using slot {slot_index}")
    print(f"Model Name {str(llama_api.model_name(slot_index))}")
    print(f"Model Path {str(llama_api.model_path(slot_index))}")
    print(f"Vocab Size {str(llama_api.vocab_size(slot_index))}")
    print(f"Max Seq Len {str(llama_api.max_seq_len(slot_index))}")
    print(f"Max Embed Len {str(llama_api.max_embed_len(slot_index))}")
    print(f"Set to n token predictions {llama_api.data['n_predict']}")

    # ---
    print("Running completion...")
    # ---

    # Example: Generate prediction given a prompt
    prompt = "Once upon a time"
    print(prompt, end="")

    completions = llama_api.completion(prompt)
    # Handle the model's generated response
    content = ""
    for completed in completions:
        token = completed["choices"][0]["text"]
        if token:
            content += token
            # Print each token to the user
            print(token, end="")
            sys.stdout.flush()
    print()  # Add padding to the model's output

    # ---
    print("\nRunning chat completion...")
    # ---

    # Example: Generate chat completion given a sequence of messages
    messages = [
        {"role": "user", "content": "Hello! How are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you for asking."},
        {"role": "user", "content": "Can you tell me a joke?"},
    ]
    for message in messages:
        print(f'{message["role"]}:', message["content"])

    chat_completions = llama_api.chat_completion(messages)
    # Handle the models generated response
    content = ""

    reasoning_active = False
    print("assistant:")
    for completed in chat_completions:
        delta = completed["choices"][0]["delta"]

        reasoning = delta.get("reasoning_content", None)
        if reasoning and reasoning_active:
            # model is reasoning
            print(reasoning, end="")
            content += reasoning
        elif reasoning and not reasoning_active:
            # reasoning open
            reasoning_active = True
            print("Thinking")
            print(reasoning, end="")
            content += reasoning
        elif not reasoning and reasoning_active:
            # reasoning close
            print("\n\nCompletion")
            reasoning_active = False

        if delta.get("content", None):
            # extract the token from the completed
            token = delta["content"]
            # append each chunk to the completed
            content += token
            print(token, end="")  # print the chunk out to the user

        sys.stdout.flush()

    print()  # add padding to models output
