"""
Copyright © 2023 Austin Berrio

Module: agent.backend.llama.requests

Description: Module for handling low-level requests to the LlamaCpp REST API.
"""

import json
import sys
import traceback
from json import JSONDecodeError
from typing import Any, Dict, Generator, Optional, Union

import requests
from requests.exceptions import ConnectionError

from agent.config import ConfigurationManager, config


class StreamNotAllowedError(Exception):
    def __init__(
        self,
        message="Streaming not allowed for this request. Set 'stream' to False.",
    ):
        super().__init__(message)


class LlamaCppRequest:
    def __init__(
        self,
        *,
        scheme: Optional[str] = None,
        domain: Optional[str] = None,
        port: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Create a request helper that talks to the local Llama-CPP REST endpoint.

        :param scheme: str, optional
            URL scheme (`http` or `https`). Defaults to `"http"`.
        :param domain: str, optional
            Hostname/IP of the server. Default is `"127.0.0.1"` for a local instance.
        :param port: int | str, optional
            TCP port on which the endpoint listens; can be passed as an integer or string.
            The default value is `8080` (matching Llama-CPP's built-in choice).
        :param headers: dict[str, str] | None, optional
            Extra HTTP headers to include with every request. If omitted a minimal header set
            containing only `"Content-Type": "application/json"` is used.

        See agent/config/__init__.py for details.
        The instance builds the base URL lazily from *scheme*, *domain* and *port*.
        It also configures an internal logger via :pyfunc:`config.get_logger(key, name)`.
        """

        if scheme and isinstance(scheme, str):
            self.scheme = scheme
        if domain and isinstance(domain, str):
            self.domain = domain
        if port and isinstance(port, str):
            self.port = str(port)
        if headers and isinstance(headers, dict):
            self.headers = headers

        # … logger …
        self.logger = config.get_logger("logger", self.__class__.__name__)
        self.logger.debug("Initialized LlamaCppRequest instance.")

    def _handle_response(self, response: requests.Response) -> Any:
        """
        Handle the HTTP response.

        :param response: The HTTP response object.
        :return: The parsed JSON response.
        """
        self.logger.debug(f"Received response with status {response.status_code}")
        if not response.ok:
            response.raise_for_status()

        try:
            return response.json()
        except JSONDecodeError:  # json decode failed
            return response.text

    @property
    def scheme(self) -> str:
        return config.get_value("requests.scheme", "http")

    @scheme.setter
    def scheme(self, value: str):
        config.set_value("requests.scheme", value)

    @property
    def domain(self) -> str:
        return config.get_value("requests.domain", "127.0.0.1")

    @domain.setter
    def domain(self, value: str):
        config.set_value("requests.domain", value)

    @property
    def port(self) -> str:
        return config.get_value("requests.port", "8080")

    @port.setter
    def port(self, value: str) -> str:
        config.set_value("requests.port", value)

    @property
    def headers(self) -> Dict[str, str]:
        return config.get_value(
            "requests.headers",
            {
                "Content-Type": "application/json",
            },
        )

    @headers.setter
    def headers(self, value: Dict[str, str]):
        config.set_value("requests.headers", value)

    @property
    def timeout(self) -> int:
        return config.get_value("requests.timeout", 30.0)

    @timeout.setter
    def timeout(self, value: int):
        config.set_value("requests.timeout", value)

    @property
    def base_url(self) -> str:
        return f"{self.scheme}://{self.domain}:{self.port}"

    def error(
        self, code: int, message: Union[str, Exception], type: str
    ) -> Dict[str, Any]:
        """Return a dictionary representing an error response."""
        return {"error": {"code": code, "message": message, "type": type}}

    def health(self) -> Dict[str, Any]:
        """Check the health status of the API."""
        try:
            self.logger.debug("Fetching health status")
            return self.get("/health")  # {"status": "ok"}
        except ConnectionError as e:
            self.logger.debug(f"Connection error while fetching health status: {e}")
            return self.error(500, str(e), "unavailable_error")

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Perform an HTTP GET request.

        :param endpoint: The API endpoint to send the GET request to.
        :param params: Optional query parameters to include in the request.
        :return: The parsed JSON response.
        """
        if params and params.get("stream", False):
            raise StreamNotAllowedError()

        url = f"{self.base_url}{endpoint}"
        self.logger.debug(f"GET request to {url} with params: {params}")
        response = requests.get(
            url,
            params=params,
            headers=self.headers,
            timeout=self.timeout,
        )
        return self._handle_response(response)

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Any:
        """
        Perform an HTTP POST request.

        :param endpoint: The API endpoint to send the POST request to.
        :param data: The data to include in the request body.
        :return: The parsed JSON response.
        """
        if data and data.get("stream", False):
            raise StreamNotAllowedError()

        url = f"{self.base_url}{endpoint}"
        self.logger.debug(f"POST request to {url} with data: {data}")
        response = requests.post(
            url,
            json=data,
            headers=self.headers,
            timeout=self.timeout,
        )
        return self._handle_response(response)

    def stream(
        self, endpoint: str, data: Dict[str, Any]
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream an HTTP request.

        :param endpoint: The API endpoint to stream to.
        :param data: Data to be sent with the request (must include 'stream': True).
        :return: A generator of response data.
        """
        if not isinstance(data, dict):
            raise TypeError("Data must be a dictionary containing 'stream': True.")
        if not data.get("stream", True):
            raise ValueError("Stream must be set to True for streaming requests.")

        url = f"{self.base_url}{endpoint}"
        self.logger.debug(f"Streaming request to {url} with data: {data}")

        response = requests.post(url, json=data, headers=self.headers, stream=True)
        response.raise_for_status()

        for line in response.iter_lines():
            if not line:
                continue

            chunk = line[len("data: ") :]
            if chunk == b"[DONE]":
                self.logger.debug("Streaming complete: [DONE] signal received.")
                break

            try:
                decoded_chunk = json.loads(chunk)
                self.logger.debug(f"Stream chunk received: {decoded_chunk}")
                yield decoded_chunk
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to decode JSON chunk: {chunk}")
                raise e


if __name__ == "__main__":
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--prompt",
        help="Model input.",
        default="Once upon a time",
    )
    parser.add_argument(
        "-n",
        "--n-predict",
        help="Tokens generated.",
        default=256,
        type=int,
    )
    args = parser.parse_args()

    # Initialize the LlamaCppRequest instance
    llama_request = LlamaCppRequest(scheme="http", domain="127.0.0.1", port="8080")

    llama_health = llama_request.health()
    if llama_health.get("error"):
        print("Server is unavailable.")
        exit(1)

    # Define the prompt for the model
    print(args.prompt, end="")

    # Prepare data for streaming request
    data = {"prompt": args.prompt, "n_predict": args.n_predict, "stream": True}

    # Generate the model's response
    generator = llama_request.stream("/completion", data=data)

    # Handle the model's generated response
    content = ""
    for response in generator:
        if "content" in response:
            token = response["content"]
            content += token
            # Print each token to the user
            print(token, end="")
            sys.stdout.flush()

    # Add padding to the model's output
    print()
