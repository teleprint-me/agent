#!/usr/bin/env bash

#
## llama.sh – Portable installer / build helper for ggml‑org/llama.cpp.
#
# NOTE: You can modify this script to fit your requirements.
#
## Purpose ---------------------------------------------------------------
# Automates the process of building and installing `llama.cpp` from source:
#   * Installs only minimal development tools
#     (gcc, g++, make, cmake, pkgconf) when they are missing.
#   * Clones or updates a local copy in `${SRC_DIR}` – defaults to
#     `<script‑dir>/../src`.
#
## Usage ---------------------------------------------------------------
#  ./llama.sh [cpu|vulkan|cuda] [/usr/local]
#    cpu      * (default) build for CPU only (no GPU driver required).
#    vulkan   * builds the Vulkan backend. Requires a working graphics stack.
#    cuda     * attempt an CUDA build if `nvcc`/drivers are present.
#
## Distribution notes -----------------------------------------------------
# * Fedora ships all needed tools out of the box – no action required.
# * Debian / Ubuntu: you may need to run e.g.:
#       apt install gcc g++ make cmake pkgconf libvulkan-dev
# * Arch users must explicitly pacman‑install those packages and any GPU
#   drivers they intend to use.
#
## Dependencies -----------------------------------------------------------
# The script does **not** pull in runtime libraries.
# You are responsible for installing your own graphics driver stack if Vulkan or CUDA is chosen;
# only build‑time tools are auto-installed when missing on the target system.
#
# See source for build instructions:
#   https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md
#
## WARNING / DISCLAIMER ----------------------------------------------- 
# * No uninstaller – running this will overwrite an existing
#   `${PREFIX}/bin/llama` and leave any manually installed binaries in place.
# * The script runs with elevated privileges if needed; proceed at your own risk.
#   It is a convenience wrapper, not guaranteed to work on every system.
#
## Targets ----------------------------------------------------------
# * This helper targets Vulkan as the primary backend (used by our agent
#   project), but CPU and CUDA builds are also supported via flags above.
# * The Agent uses the latest GitHub commit; distro‑packaged releases may be older,
#   so mixing system binaries with a git build can cause feature mismatches.
#
## References ------------------------------------------------------------
# NOTE: llama.cpp is under review for official distribution support.
#
# SEE:
#   * Debian Unstable: https://packages.debian.org/search?keywords=llama.cpp
#   * Fedora Packages: https://packages.fedoraproject.org/pkgs/llama-cpp
#   * Arch User Repository: https://aur.archlinux.org/packages?O=0&K=llama.cpp
#

set -euo pipefail # fail fast

# Dependency import
# Includes error codes - see packages.sh for more information.
# This script should not install any packages aside from llama.cpp.
# The goal is to separate concerns and reduce repeated code.
if [[ ! -f "./packages.sh" ]]; then
    echo "❌ Could not locate ./packages.sh – aborting." >&2
    exit $ERROR_SRCS   # the helper file defines its own error codes.
fi

# Save current working directory
CWD="$PWD"

# GIT
GIT_BASE='https://github.com'
GIT_REPO='ggml-org/llama.cpp'
GIT_BRANCH='master' # latest version
GIT_URL="${GIT_BASE}/${GIT_REPO}.git@${GIT_BRANCH}"

# GGML
# backend can be specified if installed drivers are supported and dependencies are met.
# CPU, Vulkan, and CUDA are the easiest to build for.
# GGML supports ROCm, ARM, Andriod, and more. See build.md (above) for more information.
GGML_BACKEND="${1:-cpu}"

# CMAKE
CMAKE_PREFIX="${2:-/usr/local}" # default to /usr/local
CMAKE_BUILD=(
    '-DCMAKE_BUILD_TYPE=Release'
    '-DBUILD_SHARED_LIBS=1'
    '-DGGML_DEBUG=0'
    '-DLLAMA_BUILD_TESTS=0'
)

# if there is no existing repo, clone from src path to dst path.
function git_clone() {
    if [ ! -d "$GIT_REPO" ]; then
        git clone "$GIT_URL" "$GIT_REPO"
    fi
}

function git_update() {
    # enter the build path
    cd "$CWD/$GIT_REPO"
    # update the repo if it already existed
    git pull origin "$GIT_BRANCH"
}

function cmake_build() {
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
}

function cmake_install() {
    # needs sudo to install system level
    DESTDIR="$CMAKE_PREFIX" cmake --install build
}

function main() {
    ask_root # ensure script is not executed as root
    ask_permission # ask user for explicit permission
    ask_sudo # enable sudo at runtime, e.g. sudo true || exit $ERROR
    return # todo
}

main

