"""Определение мониторов и поиск монитора по номеру.

Список MONITOR_CONFIGS заполняется один раз при импорте модуля и далее
меняется ТОЛЬКО на месте (slice-assignment), чтобы ссылки в других
модулях оставались актуальными.
"""

from .deps import mss
from .logs import log

#: Список мониторов: [{'id': 1, 'left': 0, 'top': 0, 'width': ..., 'height': ...}, ...]
MONITOR_CONFIGS = []


def detect_monitors():
    """Заполняет MONITOR_CONFIGS через mss; при ошибке — резервный профиль."""
    try:
        with mss.mss() as sct:
            all_monitors = sct.monitors[1:]
            if not all_monitors:
                raise ValueError("Мониторы не найдены")
            detected = [
                {
                    'id': i,
                    'left': mon['left'],
                    'top': mon['top'],
                    'width': mon['width'],
                    'height': mon['height'],
                }
                for i, mon in enumerate(all_monitors, 1)
            ]
            # Мутируем на месте, чтобы не портить ссылки в других модулях
            MONITOR_CONFIGS[:] = detected
            log.info(f"Найдено {len(MONITOR_CONFIGS)} мониторов через mss.")
    except Exception as e:
        log.warning(f"Не удалось определить мониторы через mss ({e}). "
                    f"Используется резервный профиль.")
        MONITOR_CONFIGS[:] = [{
            'id': 1,
            'left': 0,
            'top': 0,
            'width': 1920,
            'height': 1080,
        }]


def find_monitor(monitor_id):
    """Возвращает конфигурацию монитора по его номеру (1..N) или None."""
    for mon in MONITOR_CONFIGS:
        if mon['id'] == monitor_id:
            return mon
    return None


def monitor_count():
    """Количество обнаруженных мониторов."""
    return len(MONITOR_CONFIGS)


detect_monitors()
