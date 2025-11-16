import os

from openai import OpenAI


def get_client(base_url: str = None, api_key: str = None) -> OpenAI:
    if not base_url or not api_key:
        # Load .env if we need it
        from dotenv import load_dotenv

        load_dotenv(".env")

    if not base_url:
        base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:8080/v1")
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY", "sk-no-key-required")

    return OpenAI(api_key=api_key, base_url=base_url)


def chat_stream(messages, model="gpt-4o-mini"):
    client = get_client()

    # The request – `stream=True` tells the client to yield each token
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        reasoning_effort="low",  # literal str: "none", "minimal", "low", "medium", "high"
        temperature=0.1,  # low entropy for testing
        stream=True,  # enable streaming
    )

    # Consume the stream token‑by‑token
    for chunk in response:
        # The `chunk` is a `ChatCompletionChunk`; the delta may be empty
        delta = chunk.choices[0].delta
        print(delta, flush=True)
        # if delta.content is not None:
        # Optional: strip stray newlines that some llama.cpp builds add
        # print(delta.content, end="", flush=True)

        # Detect end‑of‑response
        if chunk.choices[0].finish_reason is not None:
            print()  # newline after the stream ends
            break


if __name__ == "__main__":
    user_msg = [{"role": "user", "content": "Tell me a joke about cats."}]
    chat_stream(user_msg)
