#!/usr/bin/env bash

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

# Do not allow users to run the script as root!
# Ask for permission on an as needed basis.
# This means user space commands remain in user space.
# Root commands use sudo to execute as a super user.
function root() {
    if 0 -eq $UID; then
        echo "Do not run this script as root!"
        exit 1
    fi
}

# discover the distribution family
# there aren't that many.
# this covers the basics:
#   - Debian
#   - Arch
#   - Red Hat
# a more accurate way to handle this would be cat /etc/os-release
# but then we have to filter out the id and match it.
# checking for the package manager keeps things simple, but is error prone.
function distro() {
    if command -v apt >/dev/null; then
        echo "debian"
    elif command -v dnf >/dev/null; then
        echo "fedora"
    elif command -v pacman >/dev/null; then
        echo "arch"
    else
        echo "unknown"
    fi
}

# llama.cpp depends upon the vulkan headers and icd loader.
# this varies from distro to distro, but are generally the same.
# user must attend the install and confirm packages manually.
function vulkan() {
    family=$(distro)
    case $family in
        debian)
            # https://wiki.archlinux.org/title/Vulkan
            sudo apt install vulkan-headers libvulkan-dev vulkan-tools
        fedora)
            # https://packages.fedoraproject.org/search?query=vulkan
            sudo dnf install vulkan-headers vulkan-loader vulkan-tools
        arch)
            # https://packages.debian.org/search?keywords=vulkan
            sudo pacman -S vulkan-headers vulkan-icd-loader vulkan-tools
        *)
            echo "Unknown distribution family"
            exit 1
    esac
}

function main() {
    root
    vulkan
}

main

