import tkinter as tk
from tkinter import colorchooser
import sys
import ctypes

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

    def make_click_through(self, window):
        """Attempt to make the overlay ignore mouse events."""
        if sys.platform.startswith('win'):
            hwnd = window.winfo_id()
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, -20, style | 0x80000 | 0x20
            )
        elif sys.platform == 'darwin':
            try:
                appkit = ctypes.cdll.LoadLibrary(
                    '/System/Library/Frameworks/AppKit.framework/AppKit'
                )
                objc = ctypes.cdll.LoadLibrary('/usr/lib/libobjc.A.dylib')
                objc.objc_getClass.restype = ctypes.c_void_p
                objc.sel_registerName.restype = ctypes.c_void_p
                objc.objc_msgSend.restype = ctypes.c_void_p
                ns_window = ctypes.c_void_p(int(window.frame(), 16))
                sel = objc.sel_registerName(b'setIgnoresMouseEvents:')
                objc.objc_msgSend(ns_window, sel, True)
            except Exception:
                pass
        elif sys.platform.startswith('linux'):
            try:
                window.attributes('-type', 'dock')
                window.attributes('-alpha', float(self.alpha_var.get()))
            except Exception:
                pass

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
            self.make_click_through(self.overlay)
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
