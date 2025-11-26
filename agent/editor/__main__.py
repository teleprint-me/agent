"""
https://python-prompt-toolkit.readthedocs.io/en/master/pages/full_screen_apps.html
"""

import sys

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style
from pygments.lexers import get_lexer_for_filename, guess_lexer
from pygments.util import ClassNotFound

from agent.config.style import style_dark

TAB_WIDTH = 4

kb = KeyBindings()

#
# on tab
#


def indent_line(text: str, width: int = TAB_WIDTH) -> str:
    return " " * width + text


def indent_selection(buf: Buffer, doc: Document):
    # get flat selection range (start, end indexes)
    start, end = doc.selection_range()

    # find start/end line numbers
    start_row, _ = doc.translate_index_to_position(start)
    end_row, _ = doc.translate_index_to_position(end)

    # split into lines
    lines = doc.text.splitlines(True)  # keep newlines

    # modify each line
    for i in range(start_row, end_row + 1):
        try:
            lines[i] = indent_line(lines[i])
        except IndexError:
            pass  # end row is out of range

    # write new text
    buf.text = "".join(lines)


@kb.add("tab")
def on_tab(event: KeyPressEvent):
    buf = event.current_buffer
    doc = buf.document

    # if there's a selection, then indent whole selection
    if buf.selection_state:
        indent_selection(buf, doc)
        return

    # otherwise, simple indent on current line at cursor
    buf.insert_text(" " * TAB_WIDTH)


#
# on shift tab
#


def dedent_line(text: str, width: int = TAB_WIDTH) -> str:
    stripped = text.lstrip(" ")
    removed = len(text) - len(stripped)
    return text[min(width, removed) :]


def dedent_selection(buf: Buffer, doc: Document):
    start, end = doc.selection_range()
    lines = doc.text.splitlines(True)

    start_row, _ = doc.translate_index_to_position(start)
    end_row, _ = doc.translate_index_to_position(end)

    for i in range(start_row, end_row + 1):
        try:
            lines[i] = dedent_line(lines[i])
        except IndexError:
            pass  # end row is out of range

    buf.text = "".join(lines)


def dedent_current_line(buf: Buffer, doc: Document):
    line = doc.current_line
    indent = len(line) - len(line.lstrip(" "))
    remove = min(indent, TAB_WIDTH)

    if remove > 0:
        # move cursor to beginning of line
        buf.cursor_position -= doc.cursor_position_col
        buf.delete(count=remove)
        # restore cursor horizontally
        buf.cursor_position += max(doc.cursor_position_col - remove, 0)


@kb.add("s-tab")
def on_shift_tab(event: KeyPressEvent):
    buf = event.current_buffer
    doc = buf.document

    if buf.selection_state:
        dedent_selection(buf, doc)
        return

    # Dedent current line
    dedent_current_line(buf, doc)


#
# on enter
#


@kb.add("enter")
def on_enter(event: KeyPressEvent):
    # current buffer and text
    buffer = event.current_buffer
    text = buffer.text

    # detect new lexer
    new_lexer = detect_lexer(text)
    event.app.layout.container.content.lexer = new_lexer

    # redraw ui
    event.app.invalidate()
    # reset to default behavior
    buffer.newline()


#
# on quit
#


@kb.add("c-q")
def on_quit(event: KeyPressEvent):
    event.app.exit()


# this is so hacky - i hate it.
def detect_lexer(text: str = None) -> PygmentsLexer:
    if text is None:
        text = ""  # default to TextLexer

    try:
        # raises ClassNotFound if not a file-like object
        cls = get_lexer_for_filename(text).__class__
    except ClassNotFound:
        # defaults to TextLexer
        cls = guess_lexer(text).__class__

    # expects a class, not an instance
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
    lexer = detect_lexer()
    buffer_control = BufferControl(buffer=buffer, lexer=lexer)
    window = Window(content=buffer_control, allow_scroll_beyond_bottom=True)
    layout = Layout(container=window)
    style = Style.from_dict(style_dark)
    app = Application(
        layout=layout,
        key_bindings=kb,
        style=style,
        full_screen=True,
        editing_mode=EditingMode.VI,
    )
    app.run()
