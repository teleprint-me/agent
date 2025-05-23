import tkinter as tk
from tkinter import ttk

def main():
    root = tk.Tk()
    root.title("Zipper Editor - Split View Example")

    # Create a horizontal PanedWindow (side-by-side)
    paned = ttk.Panedwindow(root, orient="horizontal")
    paned.pack(fill="both", expand=True)

    # Left editor
    text_left = tk.Text(paned, wrap="none", font=("Consolas", 12))
    paned.add(text_left, weight=1)

    # Right editor
    text_right = tk.Text(paned, wrap="none", font=("Consolas", 12))
    paned.add(text_right, weight=1)

    root.mainloop()

if __name__ == "__main__":
    main()
