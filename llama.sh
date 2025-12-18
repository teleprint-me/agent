#!/usr/bin/env bash

#
# llama.sh
#
# This script is an attempt to provide a portable llama.cpp installer compatible with common distributions.
#

set -euo pipefail # fail fast

REPO_URL='https://github.com/ggml-org/llama.cpp'
REPO_BRANCH='master'

