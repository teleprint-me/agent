"""
agent.editor.__main__
"""

from prompt_toolkit import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.key_binding.vi_state import InputMode
from prompt_toolkit.layout import HSplit
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.margins import ConditionalMargin, NumberedMargin
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style
from pygments.lexers import get_lexer_for_filename, guess_lexer
from pygments.util import ClassNotFound

from agent.config.style import style_dark

TAB_WIDTH = 4

kb = KeyBindings()

#
# Lexical Analysis
#


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


#
# on quit
#


@kb.add("c-q")
def on_quit(event: KeyPressEvent):
    event.app.exit()


#
# on enter
#


@kb.add("enter")
def on_enter(event: KeyPressEvent):
    input_mode = event.app.vi_state.input_mode
    if input_mode == InputMode.NAVIGATION:
        return  # Block on Normal Mode

    # current buffer and text
    buffer = event.current_buffer
    text = buffer.text

    # detect new lexer
    new_lexer = detect_lexer(text)
    event.app.layout.container.children[0].content.lexer = new_lexer

    # redraw ui
    event.app.invalidate()
    # reset to default behavior
    buffer.newline()


#
# on tab
#


def indent_line(text: str, width: int = TAB_WIDTH) -> str:
    return " " * width + text


def indent_selection(buf: Buffer, doc: Document, mod: callable):
    # get flat selection range (start, end indexes)
    start, end = doc.selection_range()

    # find start/end line numbers
    start_row, _ = doc.translate_index_to_position(start)
    end_row, _ = doc.translate_index_to_position(end)
    end_row += 1  # add one to include last line

    # split into lines
    lines = doc.text.splitlines(True)  # keep newlines
    line_count = len(lines)

    # clamp end_row to avoid indexing past the end
    end_row = min(end_row, line_count)

    # modify each line
    for i in range(start_row, end_row):
        if lines[i].strip() == "":
            continue
        lines[i] = mod(lines[i])

    # write new text
    buf.text = "".join(lines)


@kb.add("tab")
def on_tab(event: KeyPressEvent):
    buf = event.current_buffer
    doc = buf.document

    # if there's a selection, then indent whole selection
    if buf.selection_state:
        indent_selection(buf, doc, indent_line)
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
        indent_selection(buf, doc, dedent_line)
        return

    # Dedent current line
    dedent_current_line(buf, doc)


if __name__ == "__main__":
    # Buffer
    buffer = Buffer()
    lexer = detect_lexer()
    buffer_control = BufferControl(buffer=buffer, lexer=lexer)

    # Window
    window = Window(
        content=buffer_control,
        allow_scroll_beyond_bottom=True,
        left_margins=[
            ConditionalMargin(
                margin=NumberedMargin(
                    relative=Condition(lambda: False),
                    display_tildes=True,
                ),
                filter=Condition(lambda: True),
            )
        ],
    )

    # Status bar
    def status_bar_fn():
        app = get_app()
        buffer = app.current_buffer

        row = buffer.document.cursor_position_row + 1
        col = buffer.document.cursor_position_col + 1

        # real vi mode
        input_mode = app.vi_state.input_mode

        # visual mode override
        if buffer.selection_state:
            mode = "VISUAL"
        elif input_mode == InputMode.INSERT:
            mode = "INSERT"
        elif input_mode == InputMode.NAVIGATION:
            mode = "NORMAL"
        elif input_mode == InputMode.REPLACE:
            mode = "REPLACE"
        else:
            mode = "OTHER"

        return [
            ("class:status", f"  {mode}  "),
            ("", " | "),
            ("class:status.position", f"Ln {row}, Col {col}  "),
        ]

    status_bar = Window(FormattedTextControl(status_bar_fn), height=1)

    # Layout
    hsplit = HSplit(
        [
            window,
            status_bar,
        ]
    )
    layout = Layout(container=hsplit)

    # Style
    style = Style.from_dict(
        {
            **style_dark,
            "status": "#adb5bd",
            "status.position": "#adb5bd",
        }
    )

    # Application
    app = Application(
        layout=layout,
        key_bindings=kb,
        style=style,
        full_screen=True,
        editing_mode=EditingMode.VI,
    )
    app.run()
