import argparse

import pygments
from prompt_toolkit import print_formatted_text as print
from prompt_toolkit.formatted_text import PygmentsTokens
from prompt_toolkit.styles import Style
from pygments.lexers import guess_lexer, guess_lexer_for_filename
from pygments.lexers.special import TextLexer
from pygments.util import ClassNotFound


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
args = parser.parse_args()

with open(args.path) as file:
    source = file.read()

terminal_dark = {
    # base
    "": "#d0d0d0",
    "pygments.background": "#1e1e1e",
    "pygments.text": "#d0d0d0",
    # comments
    "pygments.comment": "italic #5a8e52",
    # strings / numbers
    "pygments.literal.string": "#ce9178",
    "pygments.literal.string.doc": "#ce9178",
    "pygments.literal.number": "#9ad5ff",
    # keywords
    "pygments.keyword": "#cf8dd3",
    "pygments.keyword.namespace": "#71c4ff",
    # operators
    "pygments.operator": "#d4d4d4",
    "pygments.operator.word": "#cf8dd3",
    # names
    "pygments.name": "#d0d0d0",
    "pygments.name.function": "#dcdcaa",
    "pygments.name.class": "#4ec9b0",
    "pygments.name.namespace": "#d0d0d0",
    "pygments.name.builtin": "#4ec9b0",
}

lexer = detect_lexer(args.path, source)
tokens = list(pygments.lex(source, lexer=lexer))
# for tok in tokens:
#     print(tok)

style = Style.from_dict(terminal_dark)
print(PygmentsTokens(token_list=tokens), style=style)
