#!/usr/bin/env bash

#
# File:          packages.sh
# Author(s):     Austin Berrio 
# Project:       agent / llama.cpp Vulkan dependency installer
# License:       AGPL-3.0-or-later  (see LICENSE file in repo)
#
# Version:       v0.1 # <-- bump when you make a breaking change
# Last‑Updated:  2025‑12‑18
#
# Description:
#     A collection of shell functions that install the minimal set of Vulkan 
#     development packages required to build llama.cpp with its vulkan backend.
#     
#     The script is *intended* for end users who already have their GPU drivers
#     installed.  It will **never** touch driver installation – this responsibility
#     remains on the user or a higher‑level installer (e.g., your RAG pipeline).
#
# Usage:
#   source packages.sh          # Import functions into current shell.
#
# Functions exported by default:
#   ask_root            - abort if script is run as root
#   ask_permission      - display disclaimer & confirm continuation
#   ask_sudo            - cache sudo privileges for the session
#   install_vulkan_packages  – installs distro‑specific Vulkan dev packages
#   install_llama_dependencies – generic build tools (gcc, cmake …)
#
# Notes:
# * The script automatically detects your package manager via `apt`, `dnf`,
#   or `pacman`. If none of these are found it falls back to `/etc/os-release`.
# * Duplicate definitions for any function will cause the last one defined
#   (in this file) to be used.  Remove duplicates before committing.
#

set -euo pipefail # fail fast

# Error Codes (by power of 2):
ERROR_SRCS=1 # failed to import source file
ERROR_ROOT=2 # script executed as root
ERROR_SUDO=4 # failed to escalate privileges
ERROR_DIST=8 # failed to identify supported os release
ERROR_PKGS=16 # failed to install packages

# --- Utilities ---

# Do not allow users to run the script as root!
# Ask for permission on an as needed basis.
# This means user space commands remain in user space.
# Root commands use sudo to execute as a super user.
function ask_root() {
    # note: id -u returns the EUID (effective user identifier)
    # https://stackoverflow.com/a/27670422/15147156
    if [ 0 -eq "$(id -u)" ]; then
        echo "Do not run this script as root!";
        exit $ERROR_ROOT;
    fi
}

# Print a disclaimer and ask end user for permission before proceeding.
# NOTE: Using echo is cleaner than cat << EOF
function ask_permission() {
    local response

    echo 'DISCLAIMER:'
    # General note – what this installer does:
    echo 'This installer will pull packages, clone a Git repository,'
    echo 'and build C++ code for the llama.cpp Vulkan backend.'
    # Explicit driver notice (kept from second duplicate):
    echo 'Drivers are NOT installed – they must be provided separately.'
    echo
    echo "Enter 'n' or ctrl‑c to abort, 'Y' to continue."

    read -p 'Proceed with installing these dependencies? (Y/n) ' -r response
    if [ "Y" != "$response" ]; then
        echo "Quit.";
        exit 0;
    fi
}

# Escalate user privileges.
# Ask once per script run (cached for ~15 min by sudo)
function ask_sudo() {
    if ! command -v sudo >/dev/null; then
        echo "sudo not available";
        exit $ERROR_SUDO;
    fi

    # A quick test that forces the password prompt now.
    sudo true || { echo "Unable to elevate privileges" >&2; exit $ERROR_SUDO; }
}

# This is useful for discovering the distro family if the above fails for some reason.
function ask_os_release() {
    # https://www.freedesktop.org/software/systemd/man/latest/os-release.html
    echo "$(grep -m1 '^ID=' /etc/os-release | cut -d'=' -f2)"
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

# --- Vulkan Dependencies ---

function ask_vulkan_packages() {
    manager=$(ask_package_manager)
    case "${manager}" in
        apt)
            # note: ubuntu uses mesa-vulkan-drivers instead of vulkan-headers?
            # https://packages.debian.org/search?keywords=vulkan
            # https://packages.ubuntu.com/search?keywords=vulkan
            echo "vulkan-headers libvulkan-dev vulkan-tools"
            ;;
        dnf)
            # note: drivers are installed out of the box by default.
            # we only need the development packages.
            # https://packages.fedoraproject.org/search?query=vulkan
            echo "vulkan-headers vulkan-loader vulkan-tools"
            ;;
        pacman)
            # note: drivers must be explicitly installed by user.
            # https://wiki.archlinux.org/title/Vulkan
            # https://archlinux.org/packages/?q=vulkan
            echo "vulkan-headers vulkan-icd-loader vulkan-tools"
            ;;
        *)
            echo "Unsupported os release: ${manager}"
            exit $ERROR_DIST
            ;;
    esac
}

# llama.cpp depends upon the vulkan headers and icd loader.
# this varies from distro to distro, but are generally the same.
# user must attend the install and confirm packages manually.
# note: package managers may have unique commands and or options for installation.
function install_vulkan_packages() {
    manager="$(ask_package_manager)"
    packages="$(ask_vulkan_packages)"
    case $cmd in
        apt|dnf)
            sudo $manager install $packages
            ;;
        pacman)
            sudo $manager -S $packages
            ;;
        *)
            echo "Unsupported package manager: ${manager}"
            echo "Attempted to install: ${packages}"
            exit $ERROR_PKGS
            ;;
    esac
}

# --- Compiler Dependencies ---

function ask_llama_dependencies() {
    manager="$(ask_package_manager)"
    case $manager in
        apt)
            # https://packages.debian.org/search
            # https://packages.ubuntu.com/search
            echo "gcc g++ gdb make cmake pkg-config git"
            ;;
        dnf)
            # https://packages.fedoraproject.org/search
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

