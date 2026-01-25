# agent/text/color.py
"""
Color is the spice of life.

Convenience helpers for 256-color ANSI output.

References:
- **Rendering:** https://en.wikipedia.org/wiki/ANSI_escape_code#Select_Graphic_Rendition_parameters
- **8-Bit Coloring:** https://en.wikipedia.org/wiki/ANSI_escape_code#8-bit
- **Block Elements:** https://en.wikipedia.org/wiki/Block_Elements
"""

ESCAPE = "\x1b"
RESET = f"{ESCAPE}[0m"


class Code:
    # Standard 8‑color codes (0–7) + bright (8–15)
    BLACK = 0
    RED = 1
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    MAGENTA = 5
    CYAN = 6
    WHITE = 7
    # Bright variants
    BBLACK = 8
    BRED = 9
    BGREEN = 10
    BYELLOW = 11
    BBLUE = 12
    BMAGENTA = 13
    BCYAN = 14
    BWHITE = 15


def in_range(n: int) -> bool:
    return 0 <= n <= 255


def bg256(n: int) -> str:
    """Return a background escape sequence for the given 0-255 code."""
    if not in_range(n):
        raise ValueError("color number must be 0-255")
    return f"{ESCAPE}[48;5;{n}m"


def fg256(n: int) -> str:
    """Return a foreground escape sequence for the given 0-255 code."""
    if not in_range(n):
        raise ValueError("color number must be 0-255")
    return f"{ESCAPE}[38;5;{n}m"


def t256(n: int, bg: bool = False) -> str:
    """Return the 256-color escape for *n* (0-255). Pass `bg=True` for bg."""
    if not in_range(n):
        raise ValueError("color number must be 0-255")
    return bg256(n) if bg else fg256(n)


def paint(text: str, fg: int | Code | None = None, bg: int | Code | None = None) -> str:
    """Wrap *text* with optional foreground/background 256-color codes."""
    parts = []
    if fg is not None:
        parts.append(t256(int(fg), bg=False))
    if bg is not None:
        parts.append(t256(int(bg), bg=True))
    parts.append(text)
    parts.append(RESET)
    return "".join(parts)


def key(n: int | Code, *values: Iterable[str]) -> str:
    """Format a key/value pair with the supplied foreground color."""
    color = t256(int(n))
    vals = " ".join(map(str, values))
    return f"{color}[{n}]{vals}{RESET}"


# usage example
if __name__ == "__main__":
    """Print a full 256-color swatch."""

    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument(
        "-c",
        "--columns",
        type=int,
        default=12,
        help="Add a new row after n columns (default: 12).",
    )
    parser.add_argument(
        "-d",
        "--codes",
        action="store_true",
        help="Print the code to the left of each swatch (default: False).",
    )
    parser.add_argument(
        "-s",
        "--swatch",
        default="█",
        help="Character used for each sampled block (default: █).",
    )
    args = parser.parse_args()

    for i in range(256):
        samples = []
        if args.codes:
            samples.append(f"{i:03} ")
        samples.append(f"{t256(i)}{args.swatch}{RESET}")
        if args.codes:
            samples.append(" ")
        print("".join(samples), end="")
        if (i + 1) % args.columns == 0:
            print()  # new row after n columns
    if args.columns % 8:
        print()  # add missing newline
