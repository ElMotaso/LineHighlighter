import importlib
import os
import sys

import pytest

module_name = 'highlighter'
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def reload_highlighter():
    if module_name in sys.modules:
        del sys.modules[module_name]
    return importlib.import_module(module_name)


def test_settings_defaults():
    mod = reload_highlighter()
    s = mod.Settings()
    assert s.width == 800
    assert s.height == 30
    assert s.alpha == 0.3
    assert s.abort_key == 'esc'


def test_hotkey_listener_triggers_callback():
    mod = reload_highlighter()
    triggered = []
    listener = mod.HotkeyListener('a', lambda: triggered.append(True))

    class Key:
        def __init__(self, name, char=None):
            self.name = name
            self.char = char

    listener._on_press(Key('a'))
    assert triggered


def test_update_settings_changes_properties():
    mod = reload_highlighter()
    hb = mod.HighlightBar(mod.Settings())
    new_settings = mod.Settings(width=123, height=45, color=mod.QtGui.QColor())
    hb.update_settings(new_settings)
    assert hb.settings.width == 123
    assert hb._color == new_settings.color
