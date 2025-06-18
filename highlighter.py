# coding: utf-8
"""Cross-platform cursor-highlighting bar using PyQt5.

This script shows a translucent bar following the mouse cursor to help
read long texts. A small settings dialog lets the user adjust width,
height, transparency, colour and the abort shortcut. The bar ignores
mouse events so windows underneath remain interactive.
"""

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
        self.resize(self.settings.width, self.settings.height)
        self._timer = QtCore.QTimer(self, timeout=self.update_position)
        self._timer.start(10)
        self._color = self.settings.color

        if sys.platform.startswith('win'):
            self._make_click_through_win()

    def _make_click_through_win(self):
        try:
            import ctypes
            from ctypes import wintypes
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

    def update_settings(self, settings: Settings):
        self.settings = settings
        self.resize(settings.width, settings.height)
        self._color = settings.color

    def update_position(self):
        pos = QtGui.QCursor.pos()
        y = pos.y() - self.settings.height // 2
        self.move(0, y)
        self.repaint()

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

        self.width_spin = QtWidgets.QSpinBox(value=800, minimum=10, maximum=10000)
        self.height_spin = QtWidgets.QSpinBox(value=30, minimum=2, maximum=1000)
        self.alpha_spin = QtWidgets.QDoubleSpinBox(value=0.3, minimum=0.05, maximum=1.0, singleStep=0.05)
        self.color_btn = QtWidgets.QPushButton('Choose…')
        self.key_edit = QtWidgets.QLineEdit('esc')
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
        if self.overlay is None:
            self.overlay = HighlightBar(settings)
        else:
            self.overlay.update_settings(settings)
        self.overlay.show()
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
            self.overlay.hide()
        self.dialog.show()


if __name__ == '__main__':
    Controller()
