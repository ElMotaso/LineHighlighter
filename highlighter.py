import tkinter as tk
from tkinter import colorchooser
import sys
import ctypes
try:
    import keyboard  # type: ignore
except Exception:
    keyboard = None

class LineHighlighter:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Line Highlighter Settings')
        # slightly larger settings window so all widgets are visible
        self.root.geometry('300x250')

        self.width_var = tk.IntVar(value=self.root.winfo_screenwidth())
        self.height_var = tk.IntVar(value=20)
        self.alpha_var = tk.DoubleVar(value=0.3)
        self.color_var = tk.StringVar(value='#ffff00')
        self.abort_key_var = tk.StringVar(value='esc')

        tk.Label(self.root, text='Width:').pack()
        tk.Entry(self.root, textvariable=self.width_var).pack()
        tk.Label(self.root, text='Height:').pack()
        tk.Entry(self.root, textvariable=self.height_var).pack()
        tk.Label(self.root, text='Transparency (0-1):').pack()
        tk.Entry(self.root, textvariable=self.alpha_var).pack()
        tk.Button(self.root, text='Choose Color',
                  command=self.choose_color).pack(pady=5)
        tk.Label(self.root, text='Abort key:').pack()
        tk.Entry(self.root, textvariable=self.abort_key_var).pack()
        tk.Button(self.root, text='Start',
                  command=self.start).pack(pady=5)

        self.overlay = None
        self.running = False
        self.hotkey = None
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)

    def make_click_through(self, window):
        """Attempt to make the overlay ignore mouse events."""
        if sys.platform.startswith('win'):
            hwnd = window.winfo_id()
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT
            )
            # Ensure layering style uses the alpha set on the window
            ctypes.windll.user32.SetLayeredWindowAttributes(
                hwnd, 0, int(float(self.alpha_var.get()) * 255), 0x02
            )
        elif sys.platform == 'darwin':
            try:
                from ctypes import util
                appkit = ctypes.cdll.LoadLibrary(util.find_library('AppKit'))
                objc = ctypes.cdll.LoadLibrary(util.find_library('objc'))
                objc.objc_getClass.restype = ctypes.c_void_p
                objc.sel_registerName.restype = ctypes.c_void_p
                objc.objc_msgSend.restype = ctypes.c_void_p
                ns_window = ctypes.c_void_p(int(window.frame(), 16))
                sel = objc.sel_registerName(b'setIgnoresMouseEvents:')
                objc.objc_msgSend(ns_window, sel, True)
            except Exception:
                pass
        else:
            try:
                window.attributes('-disabled', True)
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
            self.overlay.attributes('-alpha', self.alpha_var.get())
            self.overlay.configure(bg=self.color_var.get())
            self.overlay.update_idletasks()
            self.make_click_through(self.overlay)
            self.overlay.protocol('WM_DELETE_WINDOW', self.stop)
        else:
            # reuse existing overlay with updated settings
            self.overlay.configure(bg=self.color_var.get())
            self.overlay.attributes('-alpha', self.alpha_var.get())
        self.running = True
        self.root.withdraw()
        self.register_abort_key()
        self.follow_mouse()

    def register_abort_key(self):
        key = self.abort_key_var.get()
        if keyboard:
            if self.hotkey is not None:
                try:
                    keyboard.remove_hotkey(self.hotkey)
                except Exception:
                    pass
            try:
                self.hotkey = keyboard.add_hotkey(key, self.stop)
                return
            except Exception:
                self.hotkey = None
        # fall back to Tk event binding if global hotkey failed
        self.overlay.bind_all(f'<{key}>', self.stop)

    def stop(self, event=None):
        self.running = False
        if keyboard and self.hotkey is not None:
            try:
                keyboard.remove_hotkey(self.hotkey)
            except Exception:
                pass
            self.hotkey = None
        if self.overlay is not None:
            try:
                self.overlay.destroy()
            finally:
                self.overlay = None
        self.root.deiconify()

    def on_close(self):
        self.stop()
        self.root.destroy()

    def follow_mouse(self):
        if not self.overlay or not self.running:
            return
        # use the root pointer position so it works even when the overlay
        # ignores mouse events
        y = self.root.winfo_pointery() - int(self.height_var.get()) // 2
        geom = f"{int(self.width_var.get())}x{int(self.height_var.get())}+0+{y}"
        self.overlay.geometry(geom)
        self.overlay.configure(bg=self.color_var.get())
        self.overlay.attributes('-alpha', float(self.alpha_var.get()))
        self.overlay.lift()
        if self.running:
            self.overlay.after(10, self.follow_mouse)

if __name__ == '__main__':
    LineHighlighter()
    tk.mainloop()
