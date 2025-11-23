"""
https://python-prompt-toolkit.readthedocs.io/en/master/pages/asking_for_input.html
"""

from prompt_toolkit import PromptSession
from prompt_toolkit import print_formatted_text as print
from prompt_toolkit.formatted_text import PygmentsTokens
from prompt_toolkit.styles import Style
from pygments import lex
from pygments.lexer import Lexer
from pygments.lexers import guess_lexer
from pygments.lexers.special import TextLexer
from pygments.util import ClassNotFound

valerie_dark = {
    # ------------------------------
    # BASE
    # ------------------------------
    "": "#d0d0d0",
    "pygments.background": "#1e1e1e",
    "pygments.text": "#d0d0d0",
    # ------------------------------
    # COMMENTS
    # ------------------------------
    "pygments.comment": "italic #6a8e5a",
    "pygments.comment.preproc": "#5aa4b2",
    "pygments.comment.preprocfile": "#5afadf underline",
    "pygments.comment.special": "italic #66baff",
    # ------------------------------
    # STRINGS & NUMBERS
    # ------------------------------
    "pygments.literal.string": "#ce9178",
    "pygments.literal.string.doc": "#ce9178",
    "pygments.literal.string.interpol": "#ce9178",
    "pygments.literal.string.escape": "#ffd27f bold",
    "pygments.literal.number": "#9ad5ff",
    # ------------------------------
    # KEYWORDS
    # ------------------------------
    "pygments.keyword": "#c586c0",
    "pygments.keyword.namespace": "#71c4ff",
    "pygments.keyword.type": "#ff4d88",
    "pygments.keyword.constant": "#4ec9b0",
    "pygments.keyword.declaration": "#c586c0",
    "pygments.keyword.reserved": "#c586c0",
    "pygments.keyword.other": "#c586c0",
    # ------------------------------
    # OPERATORS & PUNCTUATION
    # ------------------------------
    "pygments.operator": "#e0e0e0",
    "pygments.operator.word": "#ffc500",
    "pygments.punctuation": "#f8c555",
    # ------------------------------
    # NAMES / IDENTIFIERS
    # ------------------------------
    "pygments.name": "#d0d0d0",
    "pygments.name.attribute": "#d0d0d0",
    "pygments.name.variable": "#ceb18a",
    "pygments.name.variable.global": "#dcdcaa",
    "pygments.name.variable.class": "#dcdcaa",
    "pygments.name.variable.instance": "#ceb18a",
    "pygments.name.function": "#dcdcaa",
    "pygments.name.function.magic": "#ffc500",
    "pygments.name.class": "#4ec9b0",
    "pygments.name.class.magic": "#4ec9b0",
    "pygments.name.builtin": "#4ec9b0",
    "pygments.name.builtin.pseudo": "#71c4ff",
    "pygments.name.constant": "#dcdcaa",
    "pygments.name.decorator": "#c586c0",
    "pygments.name.label": "#c586c0",
    "pygments.name.namespace": "#4ec9b0",
    "pygments.name.exception": "#ff7070",
    "pygments.name.tag": "#4ec9b0",
    # ------------------------------
    # GENERICS (Markdown, reST, etc.)
    # ------------------------------
    "pygments.generic.heading": "bold #f0d080",
    "pygments.generic.subheading": "#e5c07b",
    "pygments.generic.emphasis": "italic #ce9178",
    "pygments.generic.strong": "bold #ffffff",
    "pygments.generic.deleted": "#ff7070",
    "pygments.generic.inserted": "#84ff84",
    "pygments.generic.traceback": "#ff7070 bold",
    "pygments.generic.output": "#9ad5ff",
    "pygments.generic.prompt": "#71c4ff bold",
    # ------------------------------
    # ERRORS / HIGHLIGHTS
    # ------------------------------
    "pygments.error": "bg:#ff0033 #ffffff bold",
}


def lex_source(text: str) -> list[Lexer]:
    try:
        lexer = guess_lexer(text)
        print(lexer)
    except ClassNotFound:
        lexer = TextLexer()

    return PygmentsTokens(list(lex(text, lexer=lexer)))


session = PromptSession()

text = session.prompt("> ")
print(lex_source(text), style=Style.from_dict(valerie_dark))
