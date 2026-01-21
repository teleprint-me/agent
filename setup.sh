#!/usr/bin/env bash
# ---
# setup.sh
# ---
# Purpose:  Create a fresh virtualenv and install everything the agent
#           requires, in the exact order needed.
# ---

set -euo pipefail

# ---
# Clean pip cache
# ---
python -m pip cache purge

# ---
# Create a fresh virtualenv
# ---
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools

# ---
# Install PyTorch (must be first)
# ---
pip install "torch>=2.6.0" --index-url "https://download.pytorch.org/whl/cpu"

# ---
# Install the rest of the agent’s dependencies
# ---
pip install -r requirements.txt

# ---
# Install the GGUF helpers (must come after the normal requirements)
# ---
pip install "git+https://github.com/ggml-org/llama.cpp@master#subdirectory=gguf-py"

# ---
# Finalise
# ---
deactivate

echo "All done!  Activate the venv with:  source .venv/bin/activate"
