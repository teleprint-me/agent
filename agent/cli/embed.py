# agent/cli/embed.py
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

Model & Memory Usage Notes
-----

- General Rules
  - **Embedding model** – Must support the same context window (32 768 tokens).
  - **Embedding flag** – Required for the embedding server.
  - **Port** – Keep the chat and embedding servers on different ports.
  - **Sequence length** – Qwen3‑Embedding supports up to 32 768 tokens.

- VRAM Consumption

| Model                | Approx. VRAM (q8 / bf16) | Notes |
|----------------------|--------------------------|-------|
| **GPT‑OSS‑20B‑A3B**  | q8: 12.5 GB | 35 layers |
| **Qwen3‑Embedding‑0.6B** | bf16: 3.5 GB | 36 layers |

Total available: ~16 GB

- Offloading Strategies
  - Offloading reduces VRAM load but can hurt throughput.
  - For GPT‑OSS the **best** performance comes from **all** layers on the GPU (71 tokens/s).
  - Offloading 5 layers to the CPU drops throughput dramatically (≈73 % drop).
  - For Qwen‑Embedding the hit is smaller (≈36 % drop) but still noticeable.

| Model | Offload Target | Layers | Tokens/s (GPU‑only) | Tokens/s (CPU‑offload) | Δ% |
|-------|----------------|--------|---------------------|------------------------|----|
| **GPT‑OSS** | CPU (`--n-cpu-moe`) | 5 layers | **71** | 19 | -73 % |
| **Qwen‑Embedding** | GPU (`--n-gpu-layers`) | 5 layers | ~70 tokens/s (baseline) | ~45 tokens/s | -36 % |

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
* Only the non-compatible llama.cpp REST API supports the `rank` pooling
  strategy.
* The embeddings endpoint is normally disabled; enable it with
  `--embedding` or the corresponding environment variable.

--------------------------------------------------------------------
The module can expose the helper or any additional utilities.
--------------------------------------------------------------------
"""

import argparse
import os
import sqlite3
from typing import Generator

import numpy as np

from agent.config import DEFAULT_PATH_STOR, config
from agent.llama.api import LlamaCppAPI
from agent.llama.requests import LlamaCppRequest

#
# Embedding model
#


def embeddings(llama_api: LlamaCppAPI, text: str) -> np.ndarray:
    response = llama_api.embeddings(text=text)
    embedding = response["data"][0]["embedding"]
    return np.asarray(embedding, dtype=np.float32)


#
# Tokenizer model
#


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

DB_PATH = config.get_value("database.path", default=DEFAULT_PATH_STOR)


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


def rag_create(doc_id: str, chunk_id: int, content: str, vector: np.ndarray) -> None:
    with rag_connect() as conn:
        conn.execute(
            """
            INSERT INTO embeddings (doc_id, chunk_id, content, vector)
            VALUES (?, ?, ?, ?)
            """,
            (doc_id, chunk_id, content, vector.tobytes()),
        )
        conn.commit()


def rag_ingest(llama_api: LlamaCppAPI, path: str) -> None:
    """Chunk, embed, then store."""

    with open(path) as file:
        text = file.read()
        token_ids = llama_api.tokenize(text, add_special=False)

        for i, chunk in enumerate(token_chunk(token_ids)):
            chunk_text = llama_api.detokenize(chunk)
            vector = embeddings(llama_api, chunk_text)
            rag_create(path, i, chunk_text, vector)


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


def search(llama_api: LlamaCppAPI, query: str, top_k: int = 5) -> list[tuple]:
    scores = []
    q_vec = embeddings(llama_api, query)

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
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    llama_api = LlamaCppAPI(
        llama_request=LlamaCppRequest(port=args.port),
        stream=False,
        cache_prompt=False,
    )

    rag_initialize()

    if args.file:
        rag_ingest(llama_api, args.file)

    results = search(llama_api, args.query, args.top_k)

    for score, doc_id, idx, content in results:
        print(f"{score:.3f} | {doc_id} [{idx}]:\n{content}\n")
