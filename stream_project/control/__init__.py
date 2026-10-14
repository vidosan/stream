"""Управление вводом: инъекция событий Win32 и пересылка между серверами."""

from .events import apply_input_event, handle_input_event
from .forward import forward_input
from .win32 import (
    get_cursor_pos,
    key_event,
    mouse_button,
    mouse_wheel,
    move_mouse,
    release_all_modifiers,
)

__all__ = [
    'apply_input_event',
    'handle_input_event',
    'forward_input',
    'get_cursor_pos',
    'key_event',
    'mouse_button',
    'mouse_wheel',
    'move_mouse',
    'release_all_modifiers',
]
