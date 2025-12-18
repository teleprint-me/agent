#!/usr/bin/env bash

#
# dependencies.sh
#
# NOTE: The user is responsible for installing their own drivers if necessary.
#
# Fedora provides the drivers out of the box.
# Debian based distros may require extra steps.
# Arch based distros require explicit installation.
#
# See your respective distribution documentation for more information.
#
# DISCLAIMER:
# This script simply installs the core vulkan dependencies to enable building the llama.cpp vulkan backend.
# In most cases, running this is harmless, but you are encouraged to do your own research before executing this script.
# In some rare cases, you may corrupt your current installation, so run this script with absolute caution.
# This script is simply a convenience script. I offer no guarentee that it will work or operate as expected.
#

set -euo pipefail # fail fast

if [ -e packages.sh ]; then
    source packages.sh
else
    echo "Failed to import source files."
    exit $ERROR_SRCS
fi

function main() {
    ask_root
    ask_permission
    ask_sudo
    install_llama_dependencies
    install_vulkan_packages
}

main

