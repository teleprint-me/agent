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
from pygments.util import ClassNotFound

kb = KeyBindings()


@kb.add("c-q")
def quit(event):
    event.app.exit()


# this is so hacky - i hate it.
def detect_lexer(text: str, path: str = None) -> PygmentsLexer:
    cls = None
    try:
        cls = guess_lexer_for_filename(path, text).__class__
    except (TypeError, ClassNotFound):
        # guess_lexer() defaults to TextLexer
        cls = guess_lexer(text).__class__
    return PygmentsLexer(cls)


def line_number_control(buffer: Buffer) -> FormattedTextControl:
    def get_line_format() -> ANSI:
        total = buffer.document.line_count
        width = len(str(total))  # right-pad alignment
        text = ""
        for i in range(1, total + 1):
            text += f"{str(i).rjust(width)}\n"
        return ANSI(text)

    return FormattedTextControl(get_line_format)


if __name__ == "__main__":
    buffer = Buffer()
    lexer = detect_lexer("plain text")
    buffer_control = BufferControl(buffer=buffer, lexer=lexer)
    window = Window(content=buffer_control)
    layout = Layout(container=window)
    app = Application(layout=layout, key_bindings=kb, full_screen=True)

    print(buffer)
    print(lexer)
    print(buffer_control)
    print(window)
    print(layout)
    print(app)

    app.run()
