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


# usage example
if __name__ == "__main__":
    # print a gride of colors from 0 - 255
    swatch = "█"
    pad = " "

    for i in enumerate(range(0, 256)):
        color = Foreground.t256(i)
        print()
