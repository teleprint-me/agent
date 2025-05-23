import customtkinter as ctk

ctk.set_appearance_mode("dark")  # "light", "dark", or "system"
ctk.set_default_color_theme("blue")  # or "green", "dark-blue", etc.


class AgentApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Agent Editor")
        self.geometry("800x600")

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(expand=True, fill="both")

        self.new_tab("untitled")

    def new_tab(self, name):
        tab = self.tabview.add(name)
        textbox = ctk.CTkTextbox(tab, wrap="none")
        textbox.pack(expand=True, fill="both")


if __name__ == "__main__":
    app = AgentApp()
    app.mainloop()
