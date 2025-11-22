import argparse

import pygments
from prompt_toolkit import print_formatted_text as print
from prompt_toolkit.formatted_text import PygmentsTokens
from prompt_toolkit.styles import Style
from pygments.lexers.python import PythonLexer

parser = argparse.ArgumentParser()
parser.add_argument("path", help="Python source file")
args = parser.parse_args()

with open(args.path) as file:
    source = file.read()

style = Style.from_dict(
    {
        # base text / background
        "": "#d0d0d0",  # default foreground
        "pygments.background": "#1e1e1e",  # dark warm base
        "pygments.text": "#d0d0d0",
        # comments
        "pygments.comment": "italic #6a9955",  # soft green comment
        # strings / numbers
        "pygments.literal.string": "#ce9178",  # warm/desaturated orange
        "pygments.literal.string.doc": "#ce9178",
        "pygments.literal.number": "#b5cea8",  # greenish numeric
        # keywords
        "pygments.keyword": "#c586c0",  # purple keywords
        "pygments.keyword.namespace": "#569cd6",  # blue imports/namespace
        # operators
        "pygments.operator": "#d4d4d4",
        "pygments.operator.word": "#c586c0",
        # names
        "pygments.name": "#d0d0d0",
        "pygments.name.function": "#dcdcaa",  # yellowish for defs
        "pygments.name.class": "#4ec9b0",  # teal class names
        "pygments.name.namespace": "#d0d0d0",
        "pygments.name.builtin": "#4ec9b0",  # builtin functions
    }
)

tokens = list(pygments.lex(source, lexer=PythonLexer()))
# for tok in tokens:
#     print(tok)
print(PygmentsTokens(token_list=tokens), style=style)
