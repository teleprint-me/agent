"""
Adapted client for OpenAI and local llama.cpp server.
Supports streaming completions and environment-based switching.
"""

import os
import sys

import dotenv
from openai import OpenAI
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

# Load environment
dotenv.load_dotenv(".env")

api_key = os.getenv("OPENAI_API_KEY", "")
base_url = os.getenv("OPENAI_BASE_URL", "")

if not api_key:
    raise ValueError("EnvironmentError: OPENAI_API_KEY not set in .env")

# Setup default base URL if using local mode
if api_key == "sk-no-key-required" and not base_url:
    base_url = "http://localhost:8080/v1"

# Initialize client
client = OpenAI(api_key=api_key, base_url=base_url)

# Sample chat sequence
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"},
]

try:
    response = client.chat.completions.create(
        model="qwen3",  # Use "gpt-4" for OpenAI, "qwen3" for local
        messages=messages,
        stream=True,
        temperature=0.7,
        max_tokens=512,
    )

    for chunk in response:
        if isinstance(chunk, ChatCompletionChunk):
            content = chunk.choices[0].delta.content
            if content:
                print(content, end="")
                sys.stdout.flush()
    print()
except Exception as e:
    print(f"Error: {e}")
