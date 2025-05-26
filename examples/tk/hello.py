# zipper/__main__.py
import tkinter as tk
from tkinter import filedialog, messagebox

class ZipperEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Zipper Editor (Alpha)")
        self.text = tk.Text(root, undo=True, wrap="none", font=("Noto Sans Mono", 12))
        self.text.pack(fill="both", expand=True)
        self.filename = None
        self._make_menu()

    def _make_menu(self):
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open", command=self.open_file)
        filemenu.add_command(label="Save", command=self.save_file)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

    def open_file(self):
        fname = filedialog.askopenfilename()
        if fname:
            with open(fname, "r") as f:
                self.text.delete("1.0", tk.END)
                self.text.insert("1.0", f.read())
            self.filename = fname

    def save_file(self):
        if not self.filename:
            fname = filedialog.asksaveasfilename()
            if not fname:
                return
            self.filename = fname
        with open(self.filename, "w") as f:
            f.write(self.text.get("1.0", tk.END))

def main():
    root = tk.Tk()
    app = ZipperEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
