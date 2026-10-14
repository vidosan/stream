"""Методы захвата экрана."""

import threading

from ..deps import DXCAM_AVAILABLE
from ..logs import log
from .dxcam_capture import dxcam_capture, dxcam_capture_monitor1
from .mss_capture import mss_capture
from .selftest import test_dxcam, test_mss

__all__ = [
    'dxcam_capture',
    'dxcam_capture_monitor1',
    'mss_capture',
    'test_dxcam',
    'test_mss',
    'available_methods',
    'start_capture',
]


def available_methods():
    """Список доступных методов захвата: [(код, описание), ...]."""
    methods = []
    if DXCAM_AVAILABLE:
        methods.append(('dxcam', 'dxcam (все мониторы, быстрый)'))
        methods.append(('dxcam1', 'dxcam (только монитор 1, старый проверенный)'))
    methods.append(('mss', 'mss (все мониторы, стандартный)'))
    return methods


def start_capture(method):
    """Запускает поток захвата для выбранного метода.

    Если метод недоступен — откатывается на mss.
    """
    if method == 'dxcam' and DXCAM_AVAILABLE:
        target = dxcam_capture
    elif method == 'dxcam1' and DXCAM_AVAILABLE:
        target = dxcam_capture_monitor1
    else:
        if method not in (None, 'mss'):
            log.warning("Выбранный метод недоступен, используется mss.")
        target = mss_capture

    threading.Thread(target=target, daemon=True).start()
    return target.__name__
