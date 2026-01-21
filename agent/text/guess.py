# agent/text/guess.py
"""
Try to guess the language from the source text.
Pretty-printing is for fun and improves readability.
"""

from prompt_toolkit.lexers import PygmentsLexer
from pygments import highlight
from pygments.formatters.terminal256 import Terminal256Formatter
from pygments.lexer import Lexer
from pygments.lexers import get_lexer_for_filename, guess_lexer
from pygments.util import ClassNotFound


def class_name(cls: object) -> str:
    return cls.__class__.__name__


def module_name(lexer: Lexer) -> str:
    name = class_name(lexer)
    index = name.find("Lexer")
    return name[:index]


def detect_lexer(text: str = None) -> Lexer:
    if text is None:
        text = ""  # default to TextLexer
    try:
        lexer = get_lexer_for_filename(text)
    except ClassNotFound:
        lexer = guess_lexer(text)
    return lexer


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("path", help="File path to a plain text source file.")
    args = parser.parse_args()

    with open(args.path, "r") as file:
        text = file.read()

    lexer = detect_lexer(text)
    print(highlight(text, lexer, Terminal256Formatter(style="github-dark")))
    print(module_name(lexer))
