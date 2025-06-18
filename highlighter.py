# coding: utf-8
"""Cross‑platform cursor‑highlighting bar using PyQt5.

The application displays a translucent bar that follows the mouse
pointer so readers can keep track of the current line. A small settings
window lets the user configure the bar's width, height, transparency and
colour. The settings window stays visible, and the highlighter can be toggled
on/off directly from the settings dialog.
"""
from __future__ import annotations

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

        # Force the width explicitly
        self._desired_width = min(self.settings.width, screen_w)
        self._desired_height = self.settings.height

        # Set the fixed size to prevent any automatic resizing
        self.setFixedSize(self._desired_width, self._desired_height)

        # Debug
        print(f"HighlightBar created with fixed size: {self._desired_width}x{self._desired_height}")

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
                                                ctypes.windll.user32.GetWindowLongW(hwnd,
                                                                                    GWL_EXSTYLE) | WS_EX_LAYERED | WS_EX_TRANSPARENT)
            ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0,
                                                            int(self.settings.alpha * 255), 0x02)
        except Exception as e:
            print(f"Error applying Windows click-through: {e}")
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
        except Exception as e:
            print(f"Error applying Mac click-through: {e}")
            pass

    def apply_click_through(self):
        if self._click_through_applied:
            return
        if sys.platform.startswith('win'):
            self._make_click_through_win()
            # Reapply the fixed size after changing window style
            self.setFixedSize(self._desired_width, self._desired_height)
        elif sys.platform == 'darwin':
            self._make_click_through_mac()
        # Linux typically works with WA_TransparentForMouseEvents only
        self._click_through_applied = True

        # Debug
        size = self.size()
        print(f"Size after applying click-through: {size.width()}x{size.height()}")

    def update_settings(self, settings: Settings):
        self.settings = settings
        screen_w = QtWidgets.QApplication.primaryScreen().size().width()

        # Update desired dimensions
        self._desired_width = min(settings.width, screen_w)
        self._desired_height = settings.height

        # Apply as fixed size
        self.setFixedSize(self._desired_width, self._desired_height)

        # Debug
        print(f"HighlightBar updated with fixed size: {self._desired_width}x{self._desired_height}")

        self._color = settings.color

    def update_position(self):
        pos = QtGui.QCursor.pos()
        y = pos.y() - self._desired_height // 2
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
        layout = QtWidgets.QVBoxLayout(self)

        # Create a form layout for the settings
        form_layout = QtWidgets.QFormLayout()

        # Initialize QSettings
        self.settings = QtCore.QSettings('LineHighlighter', 'LineHighlighter')

        # Clear any stored window geometry that might interfere
        self.clearWindowSettings()

        screen_w = QtWidgets.QApplication.primaryScreen().size().width()

        # Safely retrieve values with better type handling
        width_value = self.settings.value('width', str(screen_w))
        height_value = self.settings.value('height', '30')
        alpha_value = self.settings.value('alpha', '0.3')
        color_hex = self.settings.value('color', '#ffff00')

        # Convert with proper error handling
        try:
            width = int(width_value)
            height = int(height_value)
            alpha = float(alpha_value)
        except (ValueError, TypeError):
            # Use defaults if conversion fails
            width = screen_w
            height = 30
            alpha = 0.3

        # Debug - you can remove this after confirming it works
        print(f"Loading settings - width: {width_value}->{width}, height: {height_value}->{height}")

        self.width_spin = QtWidgets.QSpinBox(value=width, minimum=10, maximum=10000)
        self.width_spin.setMaximumWidth(80)
        self.height_spin = QtWidgets.QSpinBox(value=height, minimum=2, maximum=1000)
        self.height_spin.setMaximumWidth(80)
        self.alpha_spin = QtWidgets.QDoubleSpinBox(value=alpha, minimum=0.05, maximum=1.0, singleStep=0.05)
        self.alpha_spin.setMaximumWidth(80)
        self.color_btn = QtWidgets.QPushButton('Choose…')

        # Add fields to form layout
        form_layout.addRow('Width:', self.width_spin)
        form_layout.addRow('Height:', self.height_spin)
        form_layout.addRow('Transparency:', self.alpha_spin)
        form_layout.addRow('Color:', self.color_btn)

        # Add form layout to main layout
        layout.addLayout(form_layout)

        # Create button layout with Apply and Toggle buttons
        button_layout = QtWidgets.QHBoxLayout()

        # Apply button
        self.apply_btn = QtWidgets.QPushButton('Apply Settings')

        # Toggle button with initial text "Start"
        self.toggle_btn = QtWidgets.QPushButton('Start Highlighter')

        # Add buttons to layout
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.toggle_btn)

        # Add button layout to main layout
        layout.addLayout(button_layout)

        # Set a reasonable fixed width for the dialog
        self.setFixedWidth(300)

        # Connect signals
        self.color_btn.clicked.connect(self.choose_color)
        self.color = QtGui.QColor(color_hex)

        # Keep track of highlighter state
        self.highlighter_active = False

    def clearWindowSettings(self):
        """Clear any stored window geometry/state from QSettings"""
        self.settings.remove("geometry")
        self.settings.remove("windowState")
        self.settings.remove("size")
        self.settings.remove("pos")
        # These keys might not exist, but it's safe to try removing them
        self.settings.sync()
        print("Cleared potential stored window geometry")

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
        )

    def save_settings(self, s: Settings):
        # Store values as strings to avoid type conversion issues
        self.settings.setValue('width', str(s.width))
        self.settings.setValue('height', str(s.height))
        self.settings.setValue('alpha', str(s.alpha))
        self.settings.setValue('color', s.color.name())

        # Force sync to ensure settings are written
        self.settings.sync()

        # Debug - you can remove this after confirming it works
        print(f"Saving settings - width: {s.width}, height: {s.height}")


class Controller:
    def __init__(self):
        if QtWidgets is None:
            raise SystemExit('PyQt5 is required to run this program.')
        self.app = QtWidgets.QApplication(sys.argv)
        self.dialog = SettingsDialog()
        self.overlay: HighlightBar | None = None

        # Connect the buttons
        self.dialog.apply_btn.clicked.connect(self.apply_settings)
        self.dialog.toggle_btn.clicked.connect(self.toggle_highlighter)

        # Show the dialog
        self.dialog.show()
        sys.exit(self.app.exec_())

    def apply_settings(self):
        """Apply current settings to the highlighter without toggling it"""
        settings = self.dialog.get_settings()
        self.dialog.save_settings(settings)

        # If highlighter is active, update its settings
        if self.overlay is not None:
            self.overlay.update_settings(settings)
            print(f"Applied new settings to active highlighter")

    def toggle_highlighter(self):
        """Toggle the highlighter on/off"""
        if self.overlay is None:
            # Start the highlighter
            self.start_highlighter()
            self.dialog.toggle_btn.setText('Stop Highlighter')
            self.dialog.highlighter_active = True
        else:
            # Stop the highlighter
            self.stop_highlighter()
            self.dialog.toggle_btn.setText('Start Highlighter')
            self.dialog.highlighter_active = False

    def start_highlighter(self):
        """Start the highlighter"""
        settings = self.dialog.get_settings()
        self.dialog.save_settings(settings)

        # Create new highlighter
        self.overlay = HighlightBar(settings)

        # Show and configure it
        self.overlay.show()
        self.overlay.raise_()
        QtWidgets.QApplication.processEvents()
        self.overlay.apply_click_through()

        print("Highlighter started")

    def stop_highlighter(self):
        """Stop the highlighter"""
        if self.overlay:
            self.overlay.close()
            self.overlay = None
            print("Highlighter stopped")


if __name__ == '__main__':
    Controller()