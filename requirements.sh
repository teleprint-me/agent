#!/usr/bin/env bash

# catch errors and exit
set -eu

#
# requirements.sh - install pip dependencies for agent
#

# NOTE: Installation must happen in consecutive order.
# The setup is procedural and will fail if dependencies are isntalled out of order.
# Torch must be installed before requirements
# GGUF must be installed after requirements
# Poppler is independent of order, but depends upon a 3rd party patch to compile the wheel and install the package.

# Clear the cache to resolve conflicts
python -m pip cache purge

# Virtual Environment
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# 1. Install PyTorch
pip install 'torch>=2.6.0' --index-url https://download.pytorch.org/whl/cpu
# 2. Install Agent dependencies
pip install -r requirements.txt
# 3. Install GGUF
# NOTE: This is required to get convert_hf_to_gguf.py to work
pip install git+https://github.com/ggml-org/llama.cpp@master#subdirectory=gguf-py

#
# python-poppler fork 
# NOTE: Wrapper unmaintained – upstream poppler maintained
#

# Temporary fix for python-poppler issue #93
# https://github.com/cbrunet/python-poppler/issues/93
pip install 'git+https://github.com/opale-ai/python-poppler.git@ca6678d'

# Exit venv
deactivate

echo "source .venv/bin/activate"

