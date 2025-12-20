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
# IMPORTANT: Installing an agent on a non-sandboxed system is a security risk.
# Users may prefer a container to isolate enabled capabilities.
# Agents are able to reason and act which may be capable of escape.
#
# NOTE: I personally don't see how a container resolves this issue.
# It's probably better to give the agent user permissions and treat them as you
# would any other user.
#
# SEE:
#   * Debian Unstable: https://packages.debian.org/search?keywords=llama.cpp
#       # note that this requires enabling unstable repos
#       # not available in ubuntu packages.
#       sudo apt install llama.cpp
#   * Fedora Packages: https://packages.fedoraproject.org/pkgs/llama-cpp
#       # note that silverblue may require special setups due to immutability.
#       # users may prefer to use the supported package.
#       sudo dnf install llama.cpp
#   * Arch User Repository: https://aur.archlinux.org/packages?O=0&K=llama.cpp
#       # note that this installs an optional service and config.
#       # an automated service may be undesirable for some setups.
#       yay -S llama.cpp-vulkan
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

# GIT
# Base URL
GIT_BASE='https://github.com'
# <org>/<dir>
GIT_REPO='ggml-org/llama.cpp'
# Uses master (does not use main)
GIT_BRANCH='master' # latest version
# Absolute URL reference
GIT_URL="${GIT_BASE}/${GIT_REPO}.git@${GIT_BRANCH}"
# Add absolute path to track root path
GIT_PATH="${PWD}/${GIT_REPO}"

# GGML
# backend can be specified if installed drivers are supported and dependencies are met.
# CPU, Vulkan, and CUDA are the easiest to build for.
# GGML supports ROCm, ARM, Andriod, and more. See build.md (above) for more information.
GGML_BACKEND="${1:-cpu}"

# CMAKE
CMAKE_PREFIX="${2:-/usr/local}" # default to /usr/local
# NOTE: Some flags are backend specific. e.g. DGGML_VULKAN_DEBUG
# Not all backends support debug flags, e.g. no CUDA debug flag is available.
CMAKE_BUILD=(
    '-DCMAKE_BUILD_TYPE=Release' # Debug mode degrades performance
    '-DGGML_DEBUG=OFF' # disable symbols (enabling this degrades performance)
    '-DLLAMA_BUILD_TESTS=OFF' # disable tests (only useful for dev builds)
    '-DLLAMA_BUILD_EXAMPLES=OFF' # disable example bins (extra, not required)
    '-DLLAMA_BUILD_COMMON=ON' # tools depends on common (enables curl)
    '-DLLAMA_BUILD_TOOLS=ON' # enable tools (llama-server, llama-quantize, etc)
    '-DBUILD_SHARED_LIBS=ON' # required prereq (static builds are optional)
    "-DCMAKE_INSTALL_PREFIX=${CMAKE_PREFIX}" # defaults to /usr/local
)

# if there is no existing repo, clone from src path to dst path.
function clone() {
    if [ ! -d "$GIT_PATH" ]; then
        git clone "$GIT_URL" "$GIT_PATH"
    fi
}

function update() {
    cd "$GIT_PATH"
    git pull origin "$GIT_BRANCH"
}

function build() {
    cd "$GIT_PATH"

    if [ "cpu" == "$GGML_BACKEND" ]; then
        cmake -B build ${CMAKE_BUILD[@]} # cpu has no argument
    elif [ "cuda" == "$GGML_BACKEND" ]; then
        cmake -B build ${CMAKE_BUILD[@]} -DGGML_CUDA=1
    elif [ "vulkan" == "$GGML_BACKEND" ]; then
        cmake -B build ${CMAKE_BUILD[@]} -DGGML_VULKAN=1
    fi
    
    cmake --build build -j $(nproc)
}

# if installed, do not remove build path!
# removal requires build/install_manifest.txt
function package() {
    DESTDIR="$CMAKE_PREFIX" cmake --install build
}

# https://askubuntu.com/a/942740
# can be manually removed using xargs:
#   xargs rm < build/install_manifest.txt
function uninstall() {
    # prefer using cmake over manual intervention
    cd "$GIT_PATH"
    # cmake automatically generates this at build time
    make uninstall
}

function main() {
    ask_root # ensure script is not executed as root
    ask_permission # ask user for explicit permission
    ask_sudo # enable sudo at runtime, e.g. sudo true || exit $ERROR
    clone
    update
    build
    # todo: install
    # note: install is disabled for now
}

main

