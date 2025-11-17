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
  --pooling mean \
  --slots \
  --jinja \
  --embeddings \
  -m /mnt/valerie/models/Qwen/Qwen3-Embedding-0.6B/ggml-model-q8_0.gguf
```

Notes
-----
- **Embedding model** - A dedicated embedding model must be used.
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
curl http://localhost:8080/v1/embeddings \
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
curl http://localhost:8080/v1/embeddings \
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

# --------------------------------------------------------------------
# The module can expose the helper or any additional utilities.
# --------------------------------------------------------------------
"""

import os

from openai import OpenAI


def connect(base_url: str = None, api_key: str = None) -> OpenAI:
    if not base_url or not api_key:
        # Load .env if we need it
        from dotenv import load_dotenv

        load_dotenv(".env")

    if not base_url:
        base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:8080/v1")

    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY", "sk-no-key-required")

    return OpenAI(api_key=api_key, base_url=base_url)


if __name__ == "__main__":
    client = connect()
    embeddings = client.embeddings.create(model="gpt-4o-mini", input="hello")
    print(embeddings.data[0].embedding)
