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

import argparse
import os
import sqlite3
from typing import Generator

import numpy as np
from openai import OpenAI

from agent.backend.llama.api import LlamaCppAPI
from agent.backend.llama.requests import LlamaCppRequest
from agent.config import DEFAULT_PATH_MEM, config

#
# Embedding model
#


def embeddings(client: OpenAI, text: str) -> np.ndarray:
    response = client.embeddings.create(model="text-embedding-3-small", input=text)
    return np.asarray(response.data[0].embedding, dtype=np.float32)


#
# Tokenizer model
#


def tokenize(client: LlamaCppAPI, text: str) -> list[int]:
    return client.tokenize(text, add_special=False)


def detokenize(client: LlamaCppAPI, token_ids: list[int]) -> str:
    return client.detokenize(token_ids=token_ids)


def token_chunk(
    token_ids: list[int], max_len: int = 32, overlap: int = 16
) -> Generator:
    start = 0
    while start < len(token_ids):
        yield token_ids[start : start + max_len]
        start += max_len - overlap


#
# Database operations
#

DB_PATH = config.get_value("memory.db.path", default=DEFAULT_PATH_MEM)


def rag_connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def rag_initialize() -> None:
    with rag_connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                chunk_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                vector BLOB NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def rag_entry(doc_id: str, chunk_id: int, content: str, vector: np.ndarray) -> None:
    with rag_connect() as conn:
        conn.execute(
            """
            INSERT INTO embeddings (doc_id, chunk_id, content, vector)
            VALUES (?, ?, ?, ?)
            """,
            (doc_id, chunk_id, content, vector.tobytes()),
        )
        conn.commit()


def rag_ingest(openai_client: OpenAI, llama_client: LlamaCppAPI, path: str) -> None:
    """Chunk, embed, then store."""

    with open(path) as file:
        text = file.read()
        token_ids = tokenize(llama_client, text)

        for i, chunk in enumerate(token_chunk(token_ids)):
            chunk_text = detokenize(llama_client, chunk)
            vector = embeddings(openai_client, chunk_text)
            rag_entry(path, i, chunk_text, vector)


def rag_load() -> Generator:
    with rag_connect() as conn:
        rows = conn.execute(
            "SELECT doc_id, chunk_id, content, vector FROM embeddings"
        ).fetchall()
        for doc_id, chunk_id, content, blob in rows:
            vector = np.frombuffer(blob, dtype=np.float32)
            yield (doc_id, chunk_id, content, vector)


#
# Search
#


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """cosine similarity"""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def search(client: OpenAI, query: str, top_k: int = 5) -> list[tuple]:
    scores = []
    q_vec = embeddings(client, query)

    for doc_id, chunk_id, content, vector in rag_load():
        score = cosine(q_vec, vector)
        scores.append((score, doc_id, chunk_id, content))

    scores.sort(reverse=True, key=lambda x: x[0])
    return scores[:top_k]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query", type=str)
    parser.add_argument("--file", type=str, required=False)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    port = 8081
    llama_client = LlamaCppAPI(
        llama_request=LlamaCppRequest(port=port),
        stream=False,
        cache_prompt=False,
    )
    openai_client = OpenAI(
        api_key="sk-no-key-required",
        base_url=f"http://127.0.0.1:{port}/v1",
    )

    rag_initialize()

    if args.file:
        rag_ingest(openai_client, llama_client, args.file)

    results = search(openai_client, args.query, args.top_k)

    for score, doc_id, idx, content in results:
        print(f"{score:.3f} | {doc_id} [{idx}]:\n{content}\n")
