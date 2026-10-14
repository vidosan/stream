"""Хранилище последних кадров каждого монитора (потокобезопасное)."""

import threading

from .monitors import MONITOR_CONFIGS

_frame_stores = {}
_frame_locks = {}


def _init_slots():
    for mon in MONITOR_CONFIGS:
        _frame_stores[mon['id']] = None
        _frame_locks[mon['id']] = threading.Lock()


_init_slots()


def set_frame(monitor_id, frame):
    """Сохраняет кадр монитора (frame должен быть копией — буферы переиспользуются)."""
    lock = _frame_locks.get(monitor_id)
    if lock is None:
        return
    with lock:
        _frame_stores[monitor_id] = frame


def get_frame(monitor_id):
    """Возвращает последний кадр монитора или None."""
    lock = _frame_locks.get(monitor_id)
    if lock is None:
        return None
    with lock:
        return _frame_stores.get(monitor_id)
