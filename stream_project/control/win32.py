"""Инъекция ввода (мышь + клавиатура) через Win32 SendInput.

Работает без сторонних библиотек (только ctypes). События приходят из
браузера и "проигрываются" как реальные действия мыши и клавиатуры.
На не-Windows все функции становятся пустышками.
"""

import os
import ctypes

from ..logs import log

if os.name == 'nt':
    import ctypes.wintypes as _wt

    _user32 = ctypes.windll.user32

    _INPUT_MOUSE = 0
    _INPUT_KEYBOARD = 1

    _MOUSEEVENTF_MOVE = 0x0001
    _MOUSEEVENTF_LEFTDOWN = 0x0002
    _MOUSEEVENTF_LEFTUP = 0x0004
    _MOUSEEVENTF_RIGHTDOWN = 0x0008
    _MOUSEEVENTF_RIGHTUP = 0x0010
    _MOUSEEVENTF_MIDDLEDOWN = 0x0020
    _MOUSEEVENTF_MIDDLEUP = 0x0040
    _MOUSEEVENTF_WHEEL = 0x0800
    _MOUSEEVENTF_ABSOLUTE = 0x8000
    # Без этого флага Windows мапит координаты только на основной монитор
    _MOUSEEVENTF_VIRTUALDESK = 0x4000

    _KEYEVENTF_KEYUP = 0x0002
    _KEYEVENTF_UNICODE = 0x0004

    # Метрики виртуального рабочего стола (объединение всех мониторов)
    _SM_XVIRTUALSCREEN = 76
    _SM_YVIRTUALSCREEN = 77
    _SM_CXVIRTUALSCREEN = 78
    _SM_CYVIRTUALSCREEN = 79

    _ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

    class _MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", _wt.LONG), ("dy", _wt.LONG), ("mouseData", _wt.DWORD),
                    ("dwFlags", _wt.DWORD), ("time", _wt.DWORD),
                    ("dwExtraInfo", _ULONG_PTR)]

    class _KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", _wt.WORD), ("wScan", _wt.WORD), ("dwFlags", _wt.DWORD),
                    ("time", _wt.DWORD), ("dwExtraInfo", _ULONG_PTR)]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT)]

    class _INPUT(ctypes.Structure):
        _fields_ = [("type", _wt.DWORD), ("u", _INPUTUNION)]

    _user32.SendInput.restype = _wt.UINT
    _user32.SendInput.argtypes = [_wt.UINT, ctypes.POINTER(_INPUT), ctypes.c_int]
    _user32.GetSystemMetrics.restype = ctypes.c_int
    _user32.GetSystemMetrics.argtypes = [ctypes.c_int]

    # --- Соответствие event.code (браузер) -> виртуальный код клавиши (Win32) ---
    _VK_CODES = {
        'Backspace': 0x08, 'Tab': 0x09, 'Enter': 0x0D, 'NumpadEnter': 0x0D,
        'ShiftLeft': 0x10, 'ShiftRight': 0x10, 'ControlLeft': 0x11, 'ControlRight': 0x11,
        'AltLeft': 0x12, 'AltRight': 0x12, 'Pause': 0x13, 'CapsLock': 0x14,
        'Escape': 0x1B, 'Space': 0x20, 'PageUp': 0x21, 'PageDown': 0x22,
        'End': 0x23, 'Home': 0x24, 'ArrowLeft': 0x25, 'ArrowUp': 0x26,
        'ArrowRight': 0x27, 'ArrowDown': 0x28, 'PrintScreen': 0x2C, 'Insert': 0x2D,
        'Delete': 0x2E, 'MetaLeft': 0x5B, 'MetaRight': 0x5C,
        'ContextMenu': 0x5D, 'NumLock': 0x90, 'ScrollLock': 0x91,
        'Semicolon': 0xBA, 'Equal': 0xBB, 'Comma': 0xBC, 'Minus': 0xBD,
        'Period': 0xBE, 'Slash': 0xBF, 'Backquote': 0xC0,
        'BracketLeft': 0xDB, 'Backslash': 0xDC, 'BracketRight': 0xDD, 'Quote': 0xDE,
        'Numpad0': 0x60, 'Numpad1': 0x61, 'Numpad2': 0x62, 'Numpad3': 0x63,
        'Numpad4': 0x64, 'Numpad5': 0x65, 'Numpad6': 0x66, 'Numpad7': 0x67,
        'Numpad8': 0x68, 'Numpad9': 0x69, 'NumpadMultiply': 0x6A,
        'NumpadAdd': 0x6B, 'NumpadSubtract': 0x6D, 'NumpadDecimal': 0x6E,
        'NumpadDivide': 0x6F,
    }
    for _i in range(10):
        _VK_CODES[f'Digit{_i}'] = 0x30 + _i
    for _c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        _VK_CODES[f'Key{_c}'] = ord(_c)
    for _i in range(1, 25):
        _VK_CODES[f'F{_i}'] = 0x6F + _i

    def _send_inputs(inputs):
        n = len(inputs)
        arr = (_INPUT * n)(*inputs)
        sent = _user32.SendInput(n, arr, ctypes.sizeof(_INPUT))
        if sent != n:
            log.debug(f"SendInput: отправлено {sent} из {n}")

    def _mouse_input(flags, dx=0, dy=0, data=0):
        return _INPUT(type=_INPUT_MOUSE,
                      u=_INPUTUNION(mi=_MOUSEINPUT(dx, dy, data, flags, 0, 0)))

    def _key_input(vk=0, scan=0, flags=0):
        return _INPUT(type=_INPUT_KEYBOARD,
                      u=_INPUTUNION(ki=_KEYBDINPUT(vk, scan, flags, 0, 0)))

    def _normalize_absolute(x, y):
        """Переводит координаты виртуального экрана в 0..65535 (как ждёт SendInput)."""
        vleft = _user32.GetSystemMetrics(_SM_XVIRTUALSCREEN)
        vtop = _user32.GetSystemMetrics(_SM_YVIRTUALSCREEN)
        vwidth = max(1, _user32.GetSystemMetrics(_SM_CXVIRTUALSCREEN))
        vheight = max(1, _user32.GetSystemMetrics(_SM_CYVIRTUALSCREEN))
        nx = int((x - vleft) * 65535 / max(1, vwidth - 1))
        ny = int((y - vtop) * 65535 / max(1, vheight - 1))
        return max(0, min(65535, nx)), max(0, min(65535, ny))

    _BUTTON_FLAGS = {
        'left': (_MOUSEEVENTF_LEFTDOWN, _MOUSEEVENTF_LEFTUP),
        'right': (_MOUSEEVENTF_RIGHTDOWN, _MOUSEEVENTF_RIGHTUP),
        'middle': (_MOUSEEVENTF_MIDDLEDOWN, _MOUSEEVENTF_MIDDLEUP),
    }

    def move_mouse(x, y):
        """Двигает курсор в абсолютные координаты виртуального экрана."""
        nx, ny = _normalize_absolute(int(x), int(y))
        _send_inputs([_mouse_input(
            _MOUSEEVENTF_MOVE | _MOUSEEVENTF_ABSOLUTE | _MOUSEEVENTF_VIRTUALDESK, nx, ny)])

    def mouse_button(button, down):
        """Нажатие/отпускание кнопки мыши: left / right / middle."""
        pair = _BUTTON_FLAGS.get(button)
        if not pair:
            return
        _send_inputs([_mouse_input(pair[0] if down else pair[1])])

    def mouse_wheel(delta):
        """delta: положительное — вверх, отрицательное — вниз (шаг 120)."""
        _send_inputs([_mouse_input(_MOUSEEVENTF_WHEEL, data=int(delta) & 0xFFFFFFFF)])

    def key_event(code, key, down, unicode_mode=False):
        """Нажатие/отпускание клавиши.

        unicode_mode=True — ввод символа по его коду (не зависит от раскладки).
        Иначе используется виртуальный код клавиши (нужен для сочетаний и
        служебных клавиш).
        """
        flags = 0 if down else _KEYEVENTF_KEYUP
        if unicode_mode:
            if not key or len(key) != 1:
                return
            _send_inputs([_key_input(scan=ord(key), flags=flags | _KEYEVENTF_UNICODE)])
            return
        vk = _VK_CODES.get(code)
        if vk is None:
            return
        _send_inputs([_key_input(vk=vk, flags=flags)])

    def release_all_modifiers():
        """Аварийно отпускает модификаторы (защита от 'залипания' клавиш)."""
        inputs = []
        for vk in (0x10, 0x11, 0x12, 0x5B, 0x5C):  # Shift, Ctrl, Alt, Win
            inputs.append(_key_input(vk=vk, flags=_KEYEVENTF_KEYUP))
        _send_inputs(inputs)

    def get_cursor_pos():
        """Текущая позиция курсора на рабочем столе."""
        pt = _wt.POINT()
        _user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

else:
    def move_mouse(x, y):
        pass

    def mouse_button(button, down):
        pass

    def mouse_wheel(delta):
        pass

    def key_event(code, key, down, unicode_mode=False):
        pass

    def release_all_modifiers():
        pass

    def get_cursor_pos():
        return (0, 0)
