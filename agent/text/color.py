# agent/text/color.py
"""
Color is the spice of life.

Convenience helpers for 256-color ANSI output.

References:
- **Rendering:** https://en.wikipedia.org/wiki/ANSI_escape_code#Select_Graphic_Rendition_parameters
- **8-Bit Coloring:** https://en.wikipedia.org/wiki/ANSI_escape_code#8-bit
- **Block Elements:** https://en.wikipedia.org/wiki/Block_Elements
"""


class Renderer:
    @property
    def escape() -> str:
        return "\x1b"

    @property
    def reset() -> str:
        return f"{ESCAPE}[0m"

    @staticmethod
    def paint():
        pass


class Background:
    @staticmethod
    def t256(n: int) -> str:
        """Return a background escape sequence for the given 0-255 code."""
        return f"{ESCAPE}[48;5;{n}m"

    def matte() -> str:
        return Background.t256(233)


class Foreground:
    @staticmethod
    def t256(n: int) -> str:
        """Return a foreground escape sequence for the given 0-255 code."""
        return f"{ESCAPE}[38;5;{n}m"

    # RGB
    @property
    def red() -> str:
        return Foreground.t256(9)

    @property
    def green() -> str:
        return Foreground.t256(10)

    @property
    def blue() -> str:
        return Foreground.t256(32)

    # CMYK
    @property
    def cyan() -> str:
        return Foreground.t256(14)

    @property
    def magenta() -> str:
        return Foreground.t256(13)

    @property
    def yellow() -> str:
        return Foreground.t256(226)

    @property
    def black() -> str:
        return Foreground.t256(0)

    # Other
    @property
    def pink() -> str:
        return Foreground.t256(198)

    @property
    def gold() -> str:
        return Foreground.t256(214)

    # Convenience helpers
    @staticmethod
    def key(color: str, n: object) -> str:
        return f"{color}[{n}]{RESET}"

    @staticmethod
    def value(color: str, n: object) -> str:
        return f"{color}{n}{RESET}"


# usage example
if __name__ == "__main__":
    # print a gride of colors from 0 - 255
    swatch = "█"
    pad = " "

    for i in enumerate(range(0, 256)):
        color = Foreground.t256(i)
        print()
