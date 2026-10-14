"""Разбор событий ввода, пришедших из браузера."""

from ..logs import log
from ..monitors import find_monitor
from . import win32

# Модификаторы, удерживаемые в данный момент (чтобы понимать, слать ли
# символ как unicode или как виртуальный код — для сочетаний вроде Ctrl+C)
_HELD_MODIFIERS = set()
_MODIFIER_CODES = {
    'ControlLeft', 'ControlRight', 'AltLeft', 'AltRight',
    'ShiftLeft', 'ShiftRight', 'MetaLeft', 'MetaRight',
}


def handle_input_event(ev):
    """Выполняет одно событие ввода, пришедшее из браузера.

    Поддерживаемые типы:
      mousemove {x, y}              — абсолютные координаты монитора
      mousedown/mouseup {button}    — left / right / middle
      wheel {delta}                 — прокрутка
      keydown/keyup {code, key}     — клавиши
      release                       — аварийно отпустить всё
    """
    etype = ev.get('type')

    if etype == 'mousemove':
        win32.move_mouse(ev.get('x', 0), ev.get('y', 0))
    elif etype in ('mousedown', 'mouseup'):
        win32.mouse_button(ev.get('button', 'left'), etype == 'mousedown')
    elif etype == 'wheel':
        win32.mouse_wheel(ev.get('delta', 0))
    elif etype in ('keydown', 'keyup'):
        code = ev.get('code', '')
        key = ev.get('key', '')
        down = etype == 'keydown'
        if code in _MODIFIER_CODES:
            if down:
                _HELD_MODIFIERS.add(code)
            else:
                _HELD_MODIFIERS.discard(code)
        # Сочетания (Ctrl+C и т.п.) требуют виртуального кода клавиши,
        # обычный текст удобнее слать как unicode — не зависит от раскладки.
        combo = any(m.startswith(('Control', 'Alt', 'Meta')) for m in _HELD_MODIFIERS)
        unicode_mode = (not combo) and len(key) == 1
        win32.key_event(code, key, down, unicode_mode=unicode_mode)
    elif etype == 'release':
        win32.release_all_modifiers()
    else:
        log.debug(f"Неизвестное событие ввода: {etype}")


def apply_input_event(ev):
    """Применяет событие ввода локально.

    Координаты из браузера — в пикселях конкретного монитора, поэтому
    добавляем смещение монитора, чтобы получить координаты рабочего стола.
    """
    if ev.get('type') == 'mousemove':
        mon = find_monitor(int(ev.get('mon', 1)))
        if mon:
            ev = dict(ev)
            ev['x'] = mon['left'] + int(ev.get('x', 0))
            ev['y'] = mon['top'] + int(ev.get('y', 0))
    handle_input_event(ev)
