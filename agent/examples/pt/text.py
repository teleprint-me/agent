"""
https://python-prompt-toolkit.readthedocs.io/en/master/pages/printing_text.html
"""

import argparse

import pygments
from prompt_toolkit import print_formatted_text as print
from prompt_toolkit.formatted_text import PygmentsTokens
from prompt_toolkit.styles import Style
from pygments.lexers import guess_lexer, guess_lexer_for_filename
from pygments.lexers.special import TextLexer
from pygments.util import ClassNotFound

from agent.config.style import style_dark


def detect_lexer(path, source):
    try:
        return guess_lexer_for_filename(path, source)
    except ClassNotFound:
        pass

    try:
        return guess_lexer(source)
    except ClassNotFound:
        pass

    # last resort: plain text
    return TextLexer()


parser = argparse.ArgumentParser()
parser.add_argument("path", help="Python source file")
parser.add_argument("--debug", action="store_true", help="Print tokens to stdout")
args = parser.parse_args()


with open(args.path) as file:
    source = file.read()
    lexer = detect_lexer(args.path, source)
    tokens_list = list(pygments.lex(source, lexer=lexer))

if args.debug:
    for tok in tokens_list:
        print(tok)
else:
    print(PygmentsTokens(token_list=tokens_list), style=Style.from_dict(style_dark))

