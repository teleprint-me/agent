#!/usr/bin/env bash

#
# requirements.sh - install pip dependencies for agent
#

# Virtual Environment
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

#
# Dependencies
# 

pip install -r requirements/development.txt
pip install -r requirements/core.txt
pip install -r requirements/tree-sitter.txt
pip install -r requirements/web.txt # optional: only available for cli tool

#
# python-poppler fork 
# NOTE: Wrapper unmaintained – upstream poppler maintained
#

# Temporary fix for python-poppler issue #93
# https://github.com/cbrunet/python-poppler/issues/93
pip install git+https://github.com/opale-ai/python-poppler.git@ca6678d

#
# GGUF dependencies: Execute each package in consecutive order
#

# NOTE: This is required to get convert_hf_to_gguf.py to work
pip install torch~=2.6.0 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements/gguf.txt
pip install git+https://github.com/ggml-org/llama.cpp@master#subdirectory=gguf-py

# Exit venv
deactivate

echo "source .venv/bin/activate"

