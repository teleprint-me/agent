import tkinter as tk

import ttkbootstrap as ttk

root = ttk.Window(themename="darkly")
root.title("Treeview")
root.geometry("480x320")
treeview = ttk.Treeview()
treeview.pack()
root.mainloop()
