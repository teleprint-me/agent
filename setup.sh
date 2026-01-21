#!/usr/bin/env bash
# ---
# setup.sh
# ---
# Purpose:  Create a fresh virtualenv and install everything the agent
#           requires, in the exact order needed.
# ---

set -euo pipefail

# ---
# 1. Environment variables (edit if you want a GPU PyTorch wheel)
# ---
PYTORCH_INDEX_URL="https://download.pytorch.org/whl/cpu"

# ---
# 2. Clean pip cache
# ---
python -m pip cache purge

# ---
# 3. Create a fresh virtualenv
# ---
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools

# ---
# 4. Install PyTorch (must be first)
# ---
pip install "torch>=2.6.0" --index-url "$PYTORCH_INDEX_URL"

# ---
# 5. Install the rest of the agent’s dependencies
# ---
pip install -r requirements.txt

# ---
# 6. Install the GGUF helpers (must come after the normal requirements)
# ---
pip install "git+https://github.com/ggml-org/llama.cpp@master#subdirectory=gguf-py"

# ---
# 7. Install the patched python‑poppler fork
# Temporary fix for python-poppler issue #93
# https://github.com/cbrunet/python-poppler/issues/93
# ---
pip install "git+https://github.com/opale-ai/python-poppler.git@ca6678d"

# ---
# 8. Finalise
# ---
deactivate

echo "All done!  Activate the venv with:  source .venv/bin/activate"
