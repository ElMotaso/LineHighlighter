import tkinter as tk
from tkinter import colorchooser

class LineHighlighter:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Line Highlighter Settings')
        self.root.geometry('250x200')

        self.width_var = tk.IntVar(value=self.root.winfo_screenwidth())
        self.height_var = tk.IntVar(value=20)
        self.alpha_var = tk.DoubleVar(value=0.3)
        self.color_var = tk.StringVar(value='#ffff00')

        tk.Label(self.root, text='Width:').pack()
        tk.Entry(self.root, textvariable=self.width_var).pack()
        tk.Label(self.root, text='Height:').pack()
        tk.Entry(self.root, textvariable=self.height_var).pack()
        tk.Label(self.root, text='Transparency (0-1):').pack()
        tk.Entry(self.root, textvariable=self.alpha_var).pack()
        tk.Button(self.root, text='Choose Color',
                  command=self.choose_color).pack(pady=5)
        tk.Button(self.root, text='Start',
                  command=self.start).pack(pady=5)

        self.overlay = None

    def choose_color(self):
        color = colorchooser.askcolor(initialcolor=self.color_var.get())
        if color[1]:
            self.color_var.set(color[1])

    def start(self):
        if self.overlay is None:
            self.overlay = tk.Toplevel(self.root)
            self.overlay.overrideredirect(True)
            self.overlay.attributes('-topmost', True)
            self.overlay.configure(bg=self.color_var.get())
            self.overlay.attributes('-alpha', self.alpha_var.get())
            self.root.withdraw()
            self.follow_mouse()

    def follow_mouse(self):
        if not self.overlay:
            return
        y = self.overlay.winfo_pointery() - int(self.height_var.get()) // 2
        geom = f"{int(self.width_var.get())}x{int(self.height_var.get())}+0+{y}"
        self.overlay.geometry(geom)
        self.overlay.configure(bg=self.color_var.get())
        self.overlay.attributes('-alpha', float(self.alpha_var.get()))
        self.overlay.after(10, self.follow_mouse)

if __name__ == '__main__':
    LineHighlighter()
    tk.mainloop()
