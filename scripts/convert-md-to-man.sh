#!/usr/bin/env bash
# convert-md-to-man.sh
#
# Usage:
#   ./convert.sh  <markdown-file>  [<output-directory>]
#
# Example:
#   ./convert.sh docs/llama-server.md
#
# If <output-directory> is omitted the man page will be written to
# the same directory as the source file.
#
# Requires: pandoc, gzip, bash ≥ 4
# Author:  Austin Berrio (teleprint‑me)
# License: AGPL
# -------------------------------------------------------------

set -euo pipefail

# --------------------------- helper ---------------------------------
# Extract the first "# " line – the title – and the first
# non‑empty line that follows it – the description.
extract_metadata() {
    local md="$1"
    local title=""
    local description=""

    # Grab the title
    title="$(sed -n '1p' "$md" | sed 's/^# //')"

    # Grab the first non‑empty line after the title
    description="$(sed -n '2,$p' "$md" | grep -m1 -v '^$' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"

    printf '%s\n%s' "$title" "$description"
}

# --------------------------- arguments ---------------------------------
if [[ $# -lt 1 || $# -gt 2 ]]; then
    echo "Usage: $0 <markdown-file> [output-dir]" >&2
    exit 1
fi

MD_FILE="$(realpath "$1")"

if [[ ! -f "$MD_FILE" ]]; then
    echo "Error: file not found: $MD_FILE" >&2
    exit 1
fi

# Destination directory – default = source dir
DEST_DIR="${2:-$(dirname "$MD_FILE")}"
mkdir -p "$DEST_DIR"

# --------------------------- metadata ---------------------------------
read -r TITLE DESCRIPTION < <(extract_metadata "$MD_FILE")

# Some sanity checks – Pandoc will complain if we give empty values
if [[ -z "$TITLE" ]]; then
    echo "Error: could not find a title line (# ...)" >&2
    exit 1
fi
if [[ -z "$DESCRIPTION" ]]; then
    echo "Warning: no description found.  Leaving it blank." >&2
fi

# --------------------------- build the man page -----------------------
# Build the output filename: <basename>.3
BASE="$(basename "$MD_FILE" .md)"
MAN_FILE="$DEST_DIR/${BASE}.3"

# Construct the pandoc command
CMD=(
    pandoc
    "$MD_FILE"
    -s # standalone
    -t man # output format
    -o "$MAN_FILE"
    -M title="$TITLE"
    -M name="$TITLE"
    -M description="$DESCRIPTION"
    -M section=3
    -M date="$(date +%F)"
    -M source="llama-server wiki"
    -M manual="Llama User Manual"
)

echo "Converting $MD_FILE → $MAN_FILE"
if ! "${CMD[@]}"; then
    echo "Pandoc failed.  Exiting." >&2
    exit 1
fi

# --------------------------- compress -------------------------------
gzip -f "$MAN_FILE"

# Done
echo "Done: $(basename "$MAN_FILE").gz"

exit 0

