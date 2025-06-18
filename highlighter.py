# coding: utf-8
"""Cross‑platform cursor‑highlighting bar using PyQt5.

The application displays a translucent bar that follows the mouse
pointer so readers can keep track of the current line. A small settings
window lets the user configure the bar's width, height, transparency and
colour. Pressing Escape stops the overlay. The overlay ignores mouse
events so windows below remain interactive.
"""
ABORT_KEY = 'esc'


import sys
import threading
from dataclasses import dataclass

try:
    from PyQt5 import QtGui, QtCore, QtWidgets
except Exception:  # pragma: no cover - PyQt5 might not be installed
    QtGui = QtCore = QtWidgets = None  # type: ignore

try:
    from pynput import keyboard  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    keyboard = None


@dataclass
class Settings:
    width: int = 800
    height: int = 30
    alpha: float = 0.3
    color: QtGui.QColor = QtGui.QColor(255, 255, 0, int(0.3 * 255))
    abort_key: str = 'esc'


class HotkeyListener(threading.Thread):
    """Background listener for a single key using pynput."""

    def __init__(self, key: str, callback):
        super().__init__(daemon=True)
        self._key = key.lower()
        self._callback = callback
        self._listener = keyboard.Listener(on_press=self._on_press)

    def _on_press(self, key):
        try:
            name = key.char.lower() if hasattr(key, 'char') and key.char else key.name.lower()
        except AttributeError:
            name = ''
        if name == self._key:
            self._callback()

    def run(self):
        with self._listener:
            self._listener.join()

    def stop(self):
        self._listener.stop()


class HighlightBar(QtWidgets.QWidget):
    def __init__(self, settings: Settings):
        super().__init__(flags=QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.settings = settings
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        screen_w = QtWidgets.QApplication.primaryScreen().size().width()
        self.resize(min(self.settings.width, screen_w), self.settings.height)
        self._timer = QtCore.QTimer(self, timeout=self.update_position)
        self._timer.start(10)
        self._color = self.settings.color

        self._click_through_applied = False

    def _make_click_through_win(self):
        try:
            import ctypes
            hwnd = int(self.winId())
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE) | WS_EX_LAYERED | WS_EX_TRANSPARENT)
            ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0,
                int(self.settings.alpha * 255), 0x02)
        except Exception:
            pass

    def _make_click_through_mac(self):
        try:
            import ctypes
            import ctypes.util
            objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library('objc'))
            objc.objc_getClass.restype = ctypes.c_void_p
            ns_window = ctypes.c_void_p(int(self.winId()))
            sel = objc.sel_registerName(b'setIgnoresMouseEvents:')
            objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool]
            objc.objc_msgSend(ns_window, sel, True)
        except Exception:
            pass

    def apply_click_through(self):
        if self._click_through_applied:
            return
        if sys.platform.startswith('win'):
            self._make_click_through_win()
        elif sys.platform == 'darwin':
            self._make_click_through_mac()
        # Linux typically works with WA_TransparentForMouseEvents only
        self._click_through_applied = True


    def update_settings(self, settings: Settings):
        self.settings = QtCore.QSettings('LineHighlighter', 'LineHighlighter')
        screen_w = QtWidgets.QApplication.primaryScreen().size().width()
        width = int(self.settings.value('width', screen_w))
        height = int(self.settings.value('height', 30))
        alpha = float(self.settings.value('alpha', 0.3))
        color_hex = self.settings.value('color', '#ffff00')

        self.width_spin = QtWidgets.QSpinBox(value=width, minimum=10, maximum=10000)
        self.height_spin = QtWidgets.QSpinBox(value=height, minimum=2, maximum=1000)
        self.alpha_spin = QtWidgets.QDoubleSpinBox(value=alpha, minimum=0.05, maximum=1.0, singleStep=0.05)
        self.color = QtGui.QColor(color_hex)
    def save_settings(self, s: Settings):
        self.settings.setValue('width', s.width)
        self.settings.setValue('height', s.height)
        self.settings.setValue('alpha', s.alpha)
        self.settings.setValue('color', s.color.name())

        self.dialog.save_settings(settings)
            self.hotkey = HotkeyListener(ABORT_KEY, self.stop)
            QtWidgets.QShortcut(QtGui.QKeySequence(ABORT_KEY), self.overlay, self.stop)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        colour = QtGui.QColor(self._color)
        colour.setAlphaF(self.settings.alpha)
        p.fillRect(self.rect(), colour)
        p.end()


class SettingsDialog(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Line Highlighter Settings')
        layout = QtWidgets.QFormLayout(self)
        self.setFixedWidth(250)

        self.width_spin = QtWidgets.QSpinBox(value=800, minimum=10, maximum=10000)
        self.width_spin.setMaximumWidth(80)
        self.height_spin = QtWidgets.QSpinBox(value=30, minimum=2, maximum=1000)
        self.height_spin.setMaximumWidth(80)
        self.alpha_spin = QtWidgets.QDoubleSpinBox(value=0.3, minimum=0.05, maximum=1.0, singleStep=0.05)
        self.alpha_spin.setMaximumWidth(80)
        self.color_btn = QtWidgets.QPushButton('Choose…')
        self.key_edit = QtWidgets.QLineEdit('esc')
        self.key_edit.setMaximumWidth(80)
        self.start_btn = QtWidgets.QPushButton('Start')

        layout.addRow('Width:', self.width_spin)
        layout.addRow('Height:', self.height_spin)
        layout.addRow('Transparency:', self.alpha_spin)
        layout.addRow('Color:', self.color_btn)
        layout.addRow('Abort key:', self.key_edit)
        layout.addRow(self.start_btn)

        self.color = QtGui.QColor(255, 255, 0)
        self.color_btn.clicked.connect(self.choose_color)

    def choose_color(self):
        col = QtWidgets.QColorDialog.getColor(self.color, self)
        if col.isValid():
            self.color = col

    def get_settings(self) -> Settings:
        colour = QtGui.QColor(self.color)
        alpha = self.alpha_spin.value()
        colour.setAlphaF(alpha)
        return Settings(
            width=self.width_spin.value(),
            height=self.height_spin.value(),
            alpha=alpha,
            color=colour,
            abort_key=self.key_edit.text() or 'esc',
        )


class Controller:
    def __init__(self):
        if QtWidgets is None:
            raise SystemExit('PyQt5 is required to run this program.')
        self.app = QtWidgets.QApplication(sys.argv)
        self.dialog = SettingsDialog()
        self.overlay: HighlightBar | None = None
        self.hotkey: HotkeyListener | None = None
        self.dialog.start_btn.clicked.connect(self.start)
        self.dialog.show()
        sys.exit(self.app.exec_())

    def start(self):
        settings = self.dialog.get_settings()
        # Ensure the settings window appears in front again
        self.dialog.raise_()
        self.dialog.activateWindow()
        if self.overlay is None:
            self.overlay = HighlightBar(settings)
        else:
            self.overlay.update_settings(settings)
        self.overlay.show()
        self.overlay.raise_()
        QtWidgets.QApplication.processEvents()
        self.overlay.apply_click_through()
        self.dialog.hide()
        if keyboard:
            if self.hotkey:
                self.hotkey.stop()
            self.hotkey = HotkeyListener(settings.abort_key, self.stop)
            self.hotkey.start()
        else:
            # fallback to QShortcut requiring focus
            QtWidgets.QShortcut(QtGui.QKeySequence(settings.abort_key), self.overlay, self.stop)

    def stop(self):
        if self.hotkey:
            self.hotkey.stop()
            self.hotkey = None
        if self.overlay:
            self.overlay.close()
            self.overlay = None
        self.dialog.show()


if __name__ == '__main__':
    Controller()
