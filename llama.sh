#!/usr/bin/env bash

#
# llama.sh
#
# NOTE: The user is responsible for installing their own drivers if necessary.
#
# Fedora provides drivers out of the box.
# Debian based distros may require extra steps.
# Arch based distros require explicit installation.
#
# See your respective distribution documentation for more information.
#
# DISCLAIMER:
# This script simply installs the core development dependencies to enable building llama.cpp from source.
# In most cases, running this is harmless, but you are encouraged to do your own research before executing this script.
# In some rare cases, you may corrupt your current installation, so run this script with absolute caution.
# This script is simply a convenience script. I offer no guarentee that it will work or operate as expected.
#
# NOTE: You can modify this script to fit your requirements.
#
# See source for build instructions.
# https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md
#
# NOTE: llama.cpp is under review for official distribution support.
#
# This usually takes some time, so this is fine for now.
#
# SEE:
#   - Debian Unstable: https://packages.debian.org/search?keywords=llama.cpp
#   - Fedora Packages: https://packages.fedoraproject.org/pkgs/llama-cpp
#   - Arch User Repository: https://aur.archlinux.org/packages?O=0&K=llama.cpp
#
# Agent is developed on top of the lastest release which may be out of sync with distros like debian and fedora.
# You're free to install based on your preferences, but this is important to keep in mind.
# The development builds will conflict with the release builds. e.g. missing or broken features.
#
# ------------------------------------------------------------
#
#   llama.sh – Portable installer for ggml-org/llama.cpp.
#
#  * Detects the distribution and installs only what is needed:
#      * build tools (cmake, git …)
#      * installs llama.cpp into the system
#  * Clones / updates a local copy of `ggml‑org/llama.cpp`
#    into `${SRC_DIR}` – defaults to `<script-dir>/../src`.
#
#   Usage:
#     ./llama.sh [cpu|vulkan|cuda] [/usr/local]
#
# ------------------------------------------------------------
#

set -euo pipefail # fail fast

# ERROR
ERROR_ROOT=1          # script was run as root
ERROR_SUDO=2          # sudo is missing or not usable
ERROR_DISTRO=4        # unsupported distro / no known package manager
ERROR_DEPS=8

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
CMAKE_BUILD=('-DCMAKE_BUILD_TYPE=Release' '-DGGML_DEBUG=0' '-DBUILD_SHARED_LIBS=1' '-DLLAMA_BUILD_TESTS=0')
CMAKE_PREFIX="${2:-/usr/local}" # default to /usr/local

function ask_root() {
    if [ "$(id -u)" = 0 ]; then
      echo "Do NOT run this script as root."
      exit $ERROR_ROOT
    fi
}

function ask_permission() {
    echo 'DISCLAIMER:'
    echo 'This installer will pull packages, clone a Git repo, and build C++ code.'
    echo 'Drivers are NOT installed – they must be provided separately.'
    echo
    echo 'Drivers are NOT installed – you must have them already.'
    echo "You can press ctrl‑c to abort."
    read -p 'Proceed with installing these dependencies? (Y/n) ' -r response
    if [ "Y" != "$response" ]; then
        echo "Quit.";
        exit 0;
    fi
}

function ask_sudo() {
    if ! command -v sudo >/dev/null; then
        echo "sudo not available";
        exit $ERROR_SUDO;
    fi

    # A quick test that forces the password prompt now.
    sudo true || { echo "Unable to elevate privileges" >&2; exit $ERROR_SUDO; }
}

function ask_os_release() {
    # https://www.freedesktop.org/software/systemd/man/latest/os-release.html
    echo "$(grep -m1 '^ID=' /etc/os-release | cut -d'=' -f2)"
}

function ask_package_manager() {
    if command -v apt >/dev/null; then
        echo "apt"; # debian
    elif command -v dnf >/dev/null; then
        echo "dnf"; # fedora
    elif command -v pacman >/dev/null; then
        echo "pacman"; # arch
    else
        echo "$(ask_os_release)"; # unsupported os
    fi
}

function ask_llama_dependencies() {
    manager="$(ask_package_manager)"
    case $manager in
        apt)
            # https://packages.debian.org/search
            # https://packages.ubuntu.com/search
            echo "gcc g++ gdb make cmake pkg-config git"
            ;;
        dnf)
            # https://packages.fedoraproject.org/search?query=vulkan
            echo "gcc make cmake pkgconf-pkg-config git"
            ;;
        pacman)
            # https://archlinux.org/packages
            echo "gcc g++ gdb make cmake pkgconf"
            ;;
        *)
            echo "Unsupported os release: ${manager}"
            exit $ERROR_DIST
            ;;
    esac
}

function install_llama_dependencies() {
    manager="$(ask_package_manager)"
    packages="$(ask_llama_dependencies)"
    case $manager in
        apt|dnf)
            sudo $manager install $packages
            ;;
        pacman)
            sudo $manager -S $packages
            ;;
        *)
            echo "Unsupported package manager: ${cmd}"
            echo "Attempted to install: ${pkg}"
            exit $ERROR_PKGS
            ;;
    esac
}

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

