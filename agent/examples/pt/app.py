"""
https://python-prompt-toolkit.readthedocs.io/en/master/pages/full_screen_apps.html
"""

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout

buffer = Buffer()
kb = KeyBindings()

root_container = Window(content=BufferControl(buffer=buffer))


@kb.add("c-q")
def quit(event):
    event.app.exit()


layout = Layout(root_container)
app = Application(layout=layout, key_bindings=kb, full_screen=True)
app.run()
