import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class TabData:
    def __init__(self, text_widget, filename=None):
        self.text_widget = text_widget
        self.filename = filename

class ZipperEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Zipper Editor (Alpha)")
        self.font_size = 12
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)
        self.tabs = []
        self._make_menu()
        self.new_tab()  # Start with one blank tab

    def _make_menu(self):
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New Tab", command=self.new_tab)
        filemenu.add_command(label="Open...", command=self.open_file)
        filemenu.add_command(label="Save", command=self.save_file)
        filemenu.add_command(label="Save As...", command=self.save_file_as)
        filemenu.add_separator()
        filemenu.add_command(label="Close Tab", command=self.close_tab)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        # View menu for font size
        viewmenu = tk.Menu(menubar, tearoff=0)
        viewmenu.add_command(label="Increase Font Size", command=self.increase_font)
        viewmenu.add_command(label="Decrease Font Size", command=self.decrease_font)
        menubar.add_cascade(label="View", menu=viewmenu)
        self.root.config(menu=menubar)

    def new_tab(self):
        text = tk.Text(self.notebook, undo=True, wrap="none", font=("Consolas", self.font_size))
        tab = TabData(text)
        self.tabs.append(tab)
        tab_idx = len(self.tabs) - 1
        self.notebook.add(text, text=f"Untitled {tab_idx+1}")
        self.notebook.select(tab_idx)

    def close_tab(self):
        idx = self.notebook.index(self.notebook.select())
        self.notebook.forget(idx)
        del self.tabs[idx]

    def get_current_tab(self):
        idx = self.notebook.index(self.notebook.select())
        return self.tabs[idx] if self.tabs else None

    def open_file(self):
        fname = filedialog.askopenfilename()
        if fname:
            with open(fname, "r") as f:
                text = tk.Text(self.notebook, undo=True, wrap="none", font=("Consolas", self.font_size))
                text.insert("1.0", f.read())
                tab = TabData(text, fname)
                self.tabs.append(tab)
                self.notebook.add(text, text=fname.split("/")[-1])
                self.notebook.select(len(self.tabs) - 1)

    def save_file(self):
        tab = self.get_current_tab()
        if tab and tab.filename:
            with open(tab.filename, "w") as f:
                f.write(tab.text_widget.get("1.0", tk.END))
        else:
            self.save_file_as()

    def save_file_as(self):
        tab = self.get_current_tab()
        fname = filedialog.asksaveasfilename()
        if fname:
            with open(fname, "w") as f:
                f.write(tab.text_widget.get("1.0", tk.END))
            tab.filename = fname
            self.notebook.tab(self.notebook.select(), text=fname.split("/")[-1])

    # --- Font size controls ---
    def set_font_size(self, size):
        self.font_size = size
        for tab in self.tabs:
            tab.text_widget.configure(font=("Consolas", self.font_size))

    def increase_font(self):
        self.set_font_size(self.font_size + 1)

    def decrease_font(self):
        if self.font_size > 6:
            self.set_font_size(self.font_size - 1)

def main():
    root = tk.Tk()
    app = ZipperEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
