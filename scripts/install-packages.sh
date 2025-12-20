#!/usr/bin/env bash

#
# File:          install-packages.sh
# Author(s):     Austin Berrio 
# Project:       agent / llama.cpp Vulkan dependency installer
# License:       AGPL-3.0-or-later  (see LICENSE file in repo)
#
# Version:       v0.2   # bump when you change the API or add new commands.
# Last‑Updated:  2025‑12‑18
#
# Description:
#     This script pulls **only** the build prerequisites for llama.cpp’s Vulkan backend –
#     i.e., a C/C++ toolchain and the Vulkan development headers/ICD loader.  
#     
#     Driver installation is *explicitly* left out; users must have their GPU drivers
#     installed beforehand (the package manager already ships them on Fedora, but not
#     Arch or Debian‑based distros).
#
# Usage:
#   source packages.sh          # make the helper functions available.
#   ./dependencies.sh           # run to install all required deps in one go.
#

set -euo pipefail  # fail fast on unset vars, errors and pipelines.

# Dependency import
if [[ ! -f "./packages.sh" ]]; then
    echo "❌ Could not locate ./packages.sh – aborting." >&2
    exit 1 # the helper file defines its own error codes.
fi

# Import all utility / install helpers.  
source "./packages.sh"

# Main entry point
main() {
    ask_root            # fail if run as root (we want to stay in user space).
    ask_permission      # display unified disclaimer & confirm intent.
    ask_sudo            # cache sudo credentials for the duration of this script.

    echo "🚀 Installing build‑toolchain dependencies..."
    install_build_packages

    echo "🔧 Installing Vulkan development packages..."
    install_vulkan_packages
}

# Execute
main

