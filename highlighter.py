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
        cursor_screen = QtWidgets.QApplication.screenAt(QtGui.QCursor.pos())
        screen_w = (cursor_screen.geometry().width()
                    if cursor_screen is not None
                    else QtWidgets.QApplication.primaryScreen().size().width())

        # Force the width explicitly, but respect the user's setting if possible
        self._desired_width = min(self.settings.width, screen_w)
        self._desired_height = self.settings.height

        # Set the fixed size to prevent any automatic resizing
        self.setFixedSize(self._desired_width, self._desired_height)

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

    def _update_alpha_win(self):
        """Update transparency on Windows when settings change."""
        try:
            import ctypes
            hwnd = int(self.winId())
            ctypes.windll.user32.SetLayeredWindowAttributes(
                hwnd, 0, int(self.settings.alpha * 255), 0x02
            )
        except Exception as e:  # pragma: no cover - platform specific
            print(f"Error updating Windows alpha: {e}")
            pass

    # This method needs to be un-indented to become a class method
    def update_settings(self, settings: Settings):
        old_color = self._color
        self.settings = settings
        screen = QtWidgets.QApplication.screenAt(QtGui.QCursor.pos())
        screen_w = (screen.geometry().width()
                     if screen is not None
                     else QtWidgets.QApplication.primaryScreen().size().width())

        # Update desired dimensions; width will be clamped in update_position
        self._desired_width = min(settings.width, screen_w)
        self._desired_height = settings.height

        # Apply as fixed size immediately
        self.setFixedSize(self._desired_width, self._desired_height)

        # Create a completely new QColor to avoid reference issues
        self._color = QtGui.QColor(
            settings.color.red(),
            settings.color.green(),
            settings.color.blue()
        )

        if sys.platform.startswith('win') and self._click_through_applied:
            self._update_alpha_win()

        # Force a complete repaint
        self.update()
        # Process any pending events immediately
        QtWidgets.QApplication.processEvents()

    def update_position(self):
        pos = QtGui.QCursor.pos()
        screen = QtWidgets.QApplication.screenAt(pos)
        if screen is not None:
            geo = screen.geometry()
            # Adjust width for the current screen
            screen_w = geo.width()
            new_width = min(self.settings.width, screen_w)
            if new_width != self._desired_width:
                self._desired_width = new_width
                self.setFixedSize(self._desired_width, self._desired_height)
            x = geo.x()
        else:
            # Fallback to primary screen origin
            x = 0
        y = pos.y() - self._desired_height // 2
        self.move(x, y)
        self.repaint()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        # Create a new color object directly from RGBA values to avoid any reference issues
        r, g, b = self._color.red(), self._color.green(), self._color.blue()
        colour = QtGui.QColor(r, g, b)
        colour.setAlphaF(self.settings.alpha)
        p.fillRect(self.rect(), colour)
        p.end()


class SettingsDialog(QtWidgets.QWidget):
    settings_changed = QtCore.pyqtSignal()

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


        # Create width spinner with screen width as maximum
        self.width_spin = QtWidgets.QSpinBox()
        self.width_spin.setRange(10, 99999)  # Much larger maximum
        self.width_spin.setValue(width)
        self.width_spin.setMaximumWidth(80)

        self.height_spin = QtWidgets.QSpinBox(value=height, minimum=2, maximum=1000)
        self.height_spin.setMaximumWidth(80)
        self.alpha_spin = QtWidgets.QDoubleSpinBox(value=alpha, minimum=0.05, maximum=1.0, singleStep=0.05)
        self.alpha_spin.setMaximumWidth(80)
        self.color_btn = QtWidgets.QPushButton('Choose…')

        # Emit signal when any setting changes
        self.width_spin.valueChanged.connect(
            lambda _=None: self.settings_changed.emit()
        )
        self.height_spin.valueChanged.connect(
            lambda _=None: self.settings_changed.emit()
        )
        self.alpha_spin.valueChanged.connect(
            lambda _=None: self.settings_changed.emit()
        )

        # Add fields to form layout
        form_layout.addRow('Width:', self.width_spin)
        form_layout.addRow('Height:', self.height_spin)
        form_layout.addRow('Transparency:', self.alpha_spin)
        form_layout.addRow('Color:', self.color_btn)

        # Add form layout to main layout
        layout.addLayout(form_layout)

        # Create button layout with just the toggle button
        button_layout = QtWidgets.QHBoxLayout()

        # Toggle button with initial text "Start"
        self.toggle_btn = QtWidgets.QPushButton('Start Highlighter')

        # Add button to layout
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

    def choose_color(self):
        dialog = QtWidgets.QColorDialog(self.color, self)
        # For live preview while using the color picker
        dialog.currentColorChanged.connect(self._preview_color_live)
        # For final selection when OK is clicked
        dialog.colorSelected.connect(self._update_color)

        # Store original color in case user cancels
        self._original_color = QtGui.QColor(self.color)

        # Execute dialog
        result = dialog.exec_()

        # If canceled, restore original color
        if not result:
            self.color = self._original_color
            self.settings_changed.emit()  # Restore the original color in the overlay

    def _preview_color(self, col: QtGui.QColor):
        """No longer needed as we're using _preview_color_live instead"""
        pass

    def _preview_color_live(self, col: QtGui.QColor):
        """Update color in real-time while in color picker"""
        if col.isValid():
            # Temporarily update the color
            self.color = QtGui.QColor(col.red(), col.green(), col.blue())

            # Signal that settings changed to update the highlighter immediately
            self.settings_changed.emit()
    
    def _update_color(self, col: QtGui.QColor):
        if col.isValid():
            # Create a new color object to avoid reference issues
            self.color = QtGui.QColor(col.red(), col.green(), col.blue())

            # Signal that settings changed
            self.settings_changed.emit()

            # Optionally, inform user if highlighter isn't running
            from_controller = hasattr(self, 'parent') and isinstance(self.parent(), Controller)



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


class Controller:
    def __init__(self):
        if QtWidgets is None:
            raise SystemExit('PyQt5 is required to run this program.')
        self.app = QtWidgets.QApplication(sys.argv)
        self.dialog = SettingsDialog()
        self.overlay: HighlightBar | None = None

        # Connect the toggle button
        self.dialog.toggle_btn.clicked.connect(self.toggle_highlighter)
        self.dialog.settings_changed.connect(self.live_update_settings)

        # Show the dialog
        self.dialog.show()
        sys.exit(self.app.exec_())

    def live_update_settings(self):
        """Update overlay immediately when settings change"""
        if self.overlay is not None:
            settings = self.dialog.get_settings()
            
            # Get current color of the overlay for comparison
            current_color = self.overlay._color.name()
            new_color = settings.color.name()
            
            # If color changed, recreate the highlighter
            if current_color != new_color:
                # Remember position
                old_pos = self.overlay.pos()
                
                # Close the existing overlay
                self.overlay.close()
                
                # Create a new one with the new settings
                self.overlay = HighlightBar(settings)
                
                # Restore position and show it
                self.overlay.move(old_pos)
                self.overlay.show()
                self.overlay.raise_()
                QtWidgets.QApplication.processEvents()
                self.overlay.apply_click_through()
            else:
                # For non-color changes, just update settings
                self.overlay.update_settings(settings)
        
        # Save the settings
        self.dialog.save_settings(settings)

        # Add this method to the Controller class
    def update_highlighter_color(self, color):
        """Safely update just the highlighter color"""
        if self.overlay is not None:
            try:
                # Create a new settings object with the new color
                current_settings = self.dialog.get_settings()
                new_settings = Settings(
                    width=current_settings.width,
                    height=current_settings.height,
                    alpha=current_settings.alpha,
                    color=color
                )
                # Update the overlay with the new settings
                self.overlay.update_settings(new_settings)
                # Save the settings
                self.dialog.save_settings(new_settings)
            except Exception as e:
                print(f"Error updating color: {e}")

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


    def stop_highlighter(self):
        """Stop the highlighter"""
        if self.overlay:
            self.overlay.close()
            self.overlay = None


if __name__ == '__main__':
    Controller()