"""
https://python-prompt-toolkit.readthedocs.io/en/master/pages/asking_for_input.html
"""

from prompt_toolkit import PromptSession
from prompt_toolkit import print_formatted_text as print
from prompt_toolkit.formatted_text import PygmentsTokens
from prompt_toolkit.lexers import PygmentsLexer
from pygments import lex
from pygments.lexers import guess_lexer
from pygments.lexers.python import PythonLexer
from pygments.lexers.special import TextLexer
from pygments.util import ClassNotFound

from agent.config.style import style_dark


def lex_source(text: str) -> PygmentsTokens:
    try:
        lexer = guess_lexer(text)
    except ClassNotFound:
        lexer = TextLexer()

    return PygmentsTokens(list(lex(text, lexer=lexer)))


session = PromptSession(multiline=True)

text = session.prompt(
    "> ",
    lexer=PygmentsLexer(PythonLexer),
    style=style_dark,
    include_default_pygments_style=False,
)

print("\ncaptured input:")
print(lex_source(text), style=style_dark)
