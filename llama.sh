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

GIT_BASE='https://github.com'
GIT_REPO='ggml-org/llama.cpp'
GIT_BRANCH='master' # latest version
GIT_URL="${GIT_BASE}/${GIT_REPO}.git@${GIT_BRANCH}"

# backend can be specified if installed drivers are supported and dependencies are met.
# CPU, Vulkan, and CUDA are the easiest to build for.
# GGML supports ROCm, ARM, Andriod, and more. See build.md (above) for more information.
GGML_BACKEND="${1:-cpu}"

CMAKE_BUILD=('-DCMAKE_BUILD_TYPE=Release' '-DGGML_DEBUG=0' '-DBUILD_SHARED_LIBS=1' '-DLLAMA_BUILD_TESTS=0')
CMAKE_PREFIX="${2:-/usr/local}" # default to /usr/local

# if there is no existing repo, clone from src path to dst path.
if [ ! -d "$GIT_REPO" ]; then
    git clone "$GIT_URL" "$GIT_REPO"
fi

# enter the build path
cd "$GIT_REPO"

# update the repo if it already existed
git pull origin "$GIT_BRANCH"

# generate build files
if [ "cpu" == "$GGML_BACKEND" ]; then
    cmake -B build ${CMAKE_BUILD[@]} # cpu has no argument
elif [ "cuda" == "$GGML_BACKEND" ]; then
    cmake -B build ${CMAKE_BUILD[@]} -DGGML_CUDA=1
elif [ "vulkan" == "GGML_BACKEND" ]; then
    cmake -B build ${CMAKE_BUILD[@]} -DGGML_VULKAN=1
fi

# compile from source (use all available cores)
cmake --build build -j $(nproc)

