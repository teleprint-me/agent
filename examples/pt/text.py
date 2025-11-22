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
parser.add_argument("--debug", action="store_true", help="Print tokens to stdout")
args = parser.parse_args()

terminal_dark = {
    # base
    "": "#d0d0d0",
    "pygments.background": "#1e1e1e",
    "pygments.text": "#d0d0d0",
    # comments
    "pygments.comment": "#5a8e52 italic",
    "pygments.comment.preproc": "#5aa4b2",
    "pygments.comment.preprocfile": "#5afadf underline",
    # strings / numbers
    "pygments.literal.string": "#ce9178",
    "pygments.literal.string.doc": "#ce9178",
    "pygments.literal.number": "#9ad5ff",
    # keywords
    "pygments.keyword": "#cf8dd3",
    "pygments.keyword.namespace": "#71c4ff",
    "pygments.keyword.type": "#4ec9b0",  # C types (int, char, void)
    # operators
    "pygments.operator": "#d4d4d4",
    "pygments.operator.word": "#cf8dd3",
    # names
    "pygments.name": "#d0d0d0",
    "pygments.name.function": "#dcdcaa",
    "pygments.name.class": "#4ec9b0",
    "pygments.name.namespace": "#d0d0d0",
    "pygments.name.builtin": "#4ec9b0",
    "pygments.name.constant": "#dcdcaa",  # uppercase constants / macros
    "pygments.name.label": "#cf8dd3",  # goto labels
    "pygments.name.decorator": "#cf8dd3",  # __attribute__
}

with open(args.path) as file:
    source = file.read()
    lexer = detect_lexer(args.path, source)
    tokens_list = list(pygments.lex(source, lexer=lexer))

if args.debug:
    for tok in tokens_list:
        print(tok)

style = Style.from_dict(terminal_dark)
print(PygmentsTokens(token_list=tokens_list), style=style)
