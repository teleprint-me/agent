"""
Script: gui.__main__
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from agent.gui.config import config


class TabData:
    def __init__(self, name, text_widget, filename=None):
        self.name = name
        self.text_widget = text_widget
        self.filename = filename


class AgentApp(ttk.Window):
    def __init__(self):
        theme = config.get_value("editor.theme", "darkly")
        super().__init__(themename=theme)

        self.title("Agent Editor")
        self.geometry("800x600")

        self.font_size = config.get_value("editor.font.size", 12)
        self.font_name = config.get_value("editor.font.name", "Noto Sans Mono")
        self.font = (self.font_name, self.font_size)
        self.tabs = []

        self._make_menu()
        self._make_tabs()

        self.new_tab()

    def _make_menu(self):
        menubar = tk.Menu(self)

        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New Tab", command=self.new_tab)
        filemenu.add_command(label="Open...", command=self.open_file)
        filemenu.add_command(label="Save", command=self.save_file)
        filemenu.add_command(label="Save As...", command=self.save_file_as)
        filemenu.add_separator()
        filemenu.add_command(label="Close Tab", command=self.close_tab)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=filemenu)

        viewmenu = tk.Menu(menubar, tearoff=0)
        viewmenu.add_command(label="Increase Font Size", command=self.increase_font)
        viewmenu.add_command(label="Decrease Font Size", command=self.decrease_font)
        menubar.add_cascade(label="View", menu=viewmenu)

        self.config(menu=menubar)

    def _make_tabs(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=2, pady=2)

    def get_current_tab(self):
        tab_name = self.notebook.tab(self.notebook.select(), "text")
        for tab in self.tabs:
            if tab.name == tab_name:
                return tab
        return None

    def new_tab(self):
        idx = len(self.tabs) + 1
        name = f"Untitled-{idx}"

        frame = ttk.Frame(self.notebook)
        text = tk.Text(frame, wrap="none", font=self.font, undo=True)
        text.pack(fill="both", expand=True)

        self.notebook.add(frame, text=name)
        self.notebook.select(len(self.tabs))

        self.tabs.append(TabData(name, text))

    def close_tab(self):
        current = self.get_current_tab()
        if not current:
            return

        index = self.notebook.index(self.notebook.select())
        self.notebook.forget(index)
        self.tabs = [tab for tab in self.tabs if tab != current]

    def open_file(self):
        path = filedialog.askopenfilename()
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Open Error", str(e))
            return

        name = os.path.basename(path)
        frame = ttk.Frame(self.notebook)
        text = tk.Text(frame, wrap="none", font=self.font, undo=True)
        text.insert("1.0", content)
        text.pack(fill="both", expand=True)

        self.notebook.add(frame, text=name)
        self.notebook.select(len(self.tabs))

        self.tabs.append(TabData(name, text, filename=path))

    def save_file(self):
        tab = self.get_current_tab()
        if not tab:
            return
        if tab.filename:
            try:
                with open(tab.filename, "w", encoding="utf-8") as f:
                    f.write(tab.text_widget.get("1.0", "end-1c"))
            except Exception as e:
                messagebox.showerror("Save Error", str(e))
        else:
            self.save_file_as()

    def save_file_as(self):
        tab = self.get_current_tab()
        if not tab:
            return

        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(tab.text_widget.get("1.0", "end-1c"))
        except Exception as e:
            messagebox.showerror("Save As Error", str(e))
            return

        tab.filename = path
        tab.name = os.path.basename(path)
        index = self.notebook.index("current")
        self.notebook.tab(index, text=tab.name)

    def set_font_size(self, size):
        self.font_size = size
        self.font = (self.font_name, self.font_size)
        for tab in self.tabs:
            tab.text_widget.configure(font=self.font)

    def increase_font(self):
        self.set_font_size(self.font_size + 1)
        config.set_value("editor.font.size", self.font_size)
        config.save()

    def decrease_font(self):
        if self.font_size > 6:
            self.set_font_size(self.font_size - 1)
            config.set_value("editor.font.size", self.font_size)
            config.save()


if __name__ == "__main__":
    app = AgentApp()
    app.mainloop()
