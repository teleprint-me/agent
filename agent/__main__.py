import tkinter as tk

import customtkinter as ctk

ctk.set_appearance_mode("dark")  # "light", "dark", or "system"
ctk.set_default_color_theme("blue")  # or "green", "dark-blue", etc.


class TabData:
    def __init__(self, name, textbox, filename=None):
        self.name = name
        self.textbox = textbox
        self.filename = filename


class AgentApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Agent Editor")
        self.geometry("800x600")

        self.font_size = 12
        self.font_name = "Noto Sans Mono"
        self.font = (self.font_name, self.font_size)
        self._make_menu()

        self.tabs = []
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(expand=True, fill="both")

        self.new_tab()

    def _make_menu(self):
        menubar = tk.Menu(self)

        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New Tab", command=lambda: self.new_tab())
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

    def open_file(self):
        pass

    def save_file(self):
        pass

    def save_file_as(self):
        pass

    # --- Font size controls ---
    def set_font_size(self, size):
        self.font_size = size
        for tab in self.tabs:
            tab.text_widget.configure(font=self.font)

    def increase_font(self):
        self.set_font_size(self.font_size + 1)

    def decrease_font(self):
        if self.font_size > 6:
            self.set_font_size(self.font_size - 1)

    def new_tab(self, name=None):
        if not name:
            name = f"Untitled-{len(self.tabs) + 1}"
        tab = self.tabview.add(name)
        textbox = ctk.CTkTextbox(tab, wrap="none", font=self.font)
        textbox.pack(expand=True, fill="both")
        self.tabs.append(TabData(name, textbox))
        self.tabview.set(name)

    def close_tab(self):
        pass


if __name__ == "__main__":
    app = AgentApp()
    app.mainloop()
