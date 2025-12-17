#!/usr/bin/env bash

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

#
# Error Codes (by power of 2):
#
# 1 - user ran script with escalated privileges.
# 2 - user is unable to escalate privileges with sudo.
# 4 - user is on a unsupported distribution.
# 8 - failed to install required packages.
#
ERROR_ROOT=1
ERROR_SUDO=2
ERROR_DIST=4
ERROR_PKGS=8

# Do not allow users to run the script as root!
# Ask for permission on an as needed basis.
# This means user space commands remain in user space.
# Root commands use sudo to execute as a super user.
function ask_root() {
    if [ 0 -eq "$(id -u)" ]; then
        echo "Do not run this script as root!";
        exit $ERROR_ROOT;
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
    sudo true || { echo "Unable to elevate privileges" >&2; return 2; }
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

function ask_vulkan_packages() {
    case "$(ask_package_manager)" in
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
            echo "Unsupported os release: $(ask_os_release)";
            exit $ERROR_DIST;
            ;;
    esac
}

# llama.cpp depends upon the vulkan headers and icd loader.
# this varies from distro to distro, but are generally the same.
# user must attend the install and confirm packages manually.
function install_vulkan_packages() {
    cmd="$(ask_package_manager)"
    pkg="$(ask_vulkan_packages)"
    sudo $cmd $pkg

    if [ 0 -neq $? ]; then
        echo "Failed to install $pkg";
        exit $ERROR_PKGS;
    fi
}

function main() {
    ask_root
    ask_sudo
    install_vulkan_packages
}

main

