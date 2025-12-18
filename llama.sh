#!/usr/bin/env bash

#
# llama.sh
#
# This script is an attempt to provide a portable llama.cpp installer compatible with common distributions.
# you can modify this script to fit your requirements.
#
# see source for build instructions.
# https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md
#

set -euo pipefail # fail fast

GIT_URL='https://github.com'
GIT_REPO='ggml-org/llama.cpp'
GIT_BRANCH='master' # latest version
GIT_CLONE="${GIT_URL}/${GIT_REPO}.git@${GIT_BRANCH}"

    
CMAKE_BUILD=('-DCMAKE_BUILD_TYPE=Release' '-DGGML_DEBUG=0' '-DBUILD_SHARED_LIBS=1' '-DLLAMA_BUILD_TESTS=0')
CMAKE_PREFIX="${1:-/usr/local}" # default to /usr/local

# clone from src path to dst path
git clone "$GIT_CLONE" "$GIT_REPO"
# enter build path
cd "$GIT_REPO"

# generate build files
# cpu build has no arguments
# cmake -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=1 -DGGML_DEBUG=0 -DGGML_BUILD_TESTS=0

# backend can be specified if installed drivers are supported and dependencies are met.
# vulkan build requires a vulkan flag, ggml is the backend, llama is the frontend. no llama flags are utilized here.
# e.g. CUDA is -DGGML_CUDA=ON
# CPU, Vulkan, and CUDA are the easiest to build for.
# GGML supports ROCm, ARM, Andriod, and more. See build.md (above) for more information.
cmake -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=1 -DGGML_DEBUG=0 -DGGML_BUILD_TESTS=0 -DGGML_VULKAN=1

# compile from source (use all available cores)
cmake --build build -j $(nproc)

