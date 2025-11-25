"""
https://python-prompt-toolkit.readthedocs.io/en/master/pages/full_screen_apps.html
"""

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers import guess_lexer, guess_lexer_for_filename
from pygments.lexers.special import TextLexer
from pygments.util import ClassNotFound

buffer = Buffer()
kb = KeyBindings()

root_container = Window(content=BufferControl(buffer=buffer))


@kb.add("c-q")
def quit(event):
    event.app.exit()


def detect_lexer(text: str, path: str = None) -> PygmentsLexer:
    lexer = None
    if path:
        try:
            lexer = guess_lexer_for_filename(path, text)
        except ClassNotFound:
            pass

    try:
        lexer = guess_lexer(text)
    except ClassNotFound:
        lexer = TextLexer()

    return PygmentsLexer(lexer)


def line_number_control(buffer: Buffer) -> FormattedTextControl:
    def get_line_format() -> ANSI:
        total = buffer.document.line_count
        width = len(str(total))  # right-pad alignment
        text = ""
        for i in range(1, total + 1):
            text += f"{str(i).rjust(width)}\n"
        return ANSI(text)

    return FormattedTextControl(get_line_format)


layout = Layout(root_container)
app = Application(layout=layout, key_bindings=kb, full_screen=True)
app.run()
