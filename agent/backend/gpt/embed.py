# agent/backend/gpt/embed.py
"""
Llama-Server Embeddings Wrapper
================================

Llama-Server is an OpenAI-API compatible server that exposes chat completions
and embeddings.  The embeddings endpoint requires a model that uses a pooling
strategy other than ``none``; the returned vectors are L2-normalised.

--------------------------------------------------------------------
Configuration
--------------------------------------------------------------------
The server can be configured through command-line flags or environment
variables:

```
--pooling {none,mean,cls,last,rank}   # pooling strategy (default: model default)
                                      # (env: LLAMA_ARG_POOLING)

--embedding, --embeddings             # enable the embeddings endpoint only
                                      # (default: disabled)
                                      # (env: LLAMA_ARG_EMBEDDINGS)
```

Typical launch command:

```bash
llama-server \
  --port 8081 \
  --ctx-size 32768 \
  --n-gpu-layers 99 \
  --slots \
  --pooling mean \
  --embeddings \
  -m /mnt/valerie/models/Qwen/Qwen3-Embedding-0.6B/ggml-model-q8_0.gguf
```

Notes
-----
- **Embedding model** - A dedicated embedding model must be used.
- **Embedding flag** - This flag is required.
- **Port** - Ensure the port does not conflict with the chat model.
- **Sequence length** - Qwen3-Embedding supports a maximum of 32768 tokens.
- **VRAM usage**
  - GPT-OSS ≈ 12.1 GB
  - Embedding model ≈ 3.5 GB
  - Total available ≈ 16 GB

--------------------------------------------------------------------
API Usage
--------------------------------------------------------------------
The endpoint follows the OpenAI embeddings API specification.

*Single string*

```bash
curl http://localhost:8081/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer no-key" \
  -d '{
        "input": "hello",
        "model": "GPT-4",
        "encoding_format": "float"
      }'
```

*Array of strings*

```bash
curl http://localhost:8081/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer no-key" \
  -d '{
        "input": ["hello", "world"],
        "model": "GPT-4",
        "encoding_format": "float"
      }'
```

--------------------------------------------------------------------
Notes
--------------------------------------------------------------------
* Only the non-compatible llama.cpp REST API supports the ``rank`` pooling
  strategy.
* The embeddings endpoint is normally disabled; enable it with
  ``--embedding`` or the corresponding environment variable.

--------------------------------------------------------------------
The module can expose the helper or any additional utilities.
--------------------------------------------------------------------
"""

import os
import sqlite3

import numpy as np
from openai import OpenAI

from agent.backend.llama.api import LlamaCppAPI
from agent.backend.llama.requests import LlamaCppRequest
from agent.config import DEFAULT_PATH_MEM, config

DB_PATH = config.get_value("memory.db.path", default=DEFAULT_PATH_MEM)


def rag_connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def rag_initialize():
    with rag_connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                chunk_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding BLOB NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def llama_client(base_url: str = None, port: int = None):
    llama_request = LlamaCppRequest(base_url=base_url, port=port)
    return LlamaCppAPI(llama_request=llama_request, stream=False, cache_prompt=False)


def openai_client(base_url: str = None, api_key: str = None) -> OpenAI:
    if not base_url or not api_key:
        # Load .env if we need it
        from dotenv import load_dotenv

        load_dotenv(".env")

    if not base_url:
        base_url = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8081/v1")

    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY", "sk-no-key-required")

    return OpenAI(api_key=api_key, base_url=base_url)


def tokenize(llama_api: LlamaCppAPI, text: str) -> list[int]:
    return llama_api.tokenize(text, add_special=False)


def detokenize(llama_api: LlamaCppAPI, token_ids: list[int]) -> str:
    return llama_api.detokenize(token_ids=token_ids)


def chunk_tokens(token_ids: list[int], max_len: int = 512, overlap: int = 64):
    start = 0
    while start < len(token_ids):
        yield token_ids[start : start + max_len]
        start += max_len - overlap


if __name__ == "__main__":
    text_sample = "hello, world!"
    llama_model = llama_client("http://127.0.0.1", 8081)
    t = llama_model.tokenize("hello, world!")
    t2 = llama_model.tokenize("hello, world!", add_special=True)
    print(len(t), len(t2))

    detok = llama_model.detokenize(t2)
    print(detok)

    openai_model = openai_client(
        base_url="http://localhost:8081/v1", api_key="sk-no-key-required"
    )
    response = openai_model.embeddings.create(
        model="text-embedding-3-small", input=text_sample
    )

    # print(response.data[0].embedding)
    print(f"prompt tokens: {response.usage.prompt_tokens}")
    print(f"total tokens: {response.usage.total_tokens}")
