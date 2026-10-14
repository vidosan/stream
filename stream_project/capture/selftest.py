"""Самопроверка методов захвата (запуск: python -m stream_project.main --test)."""

import time

from ..deps import DXCAM_AVAILABLE, MSS_AVAILABLE, dxcam, mss
from ..logs import log
from ..monitors import MONITOR_CONFIGS


def test_dxcam():
    """Проверяет захват КАЖДОГО монитора через dxcam отдельно."""
    log.info("Тестирование dxcam...")
    if not DXCAM_AVAILABLE:
        log.error("dxcam: НЕДОСТУПЕН (библиотека не установлена).")
        return False
    ok_any = False
    for mon in MONITOR_CONFIGS:
        idx = mon['id'] - 1
        try:
            camera = dxcam.create(output_idx=idx, output_color="BGR")
            if camera is None:
                log.error(f"dxcam: монитор {mon['id']} (output_idx={idx}): камера НЕ создана.")
                continue
            camera.start(target_fps=1, video_mode=True)
            time.sleep(0.5)
            frame = camera.get_latest_frame()
            camera.stop()
            if frame is not None:
                log.info(f"dxcam: монитор {mon['id']} (output_idx={idx}): УСПЕШНО "
                         f"({frame.shape[1]}x{frame.shape[0]}).")
                ok_any = True
            else:
                log.error(f"dxcam: монитор {mon['id']} (output_idx={idx}): кадр пуст.")
        except Exception as e:
            log.error(f"dxcam: монитор {mon['id']} (output_idx={idx}): ОШИБКА - {e}")
    return ok_any


def test_mss():
    """Проверяет захват первого монитора через mss."""
    log.info("Тестирование mss...")
    if not MSS_AVAILABLE:
        log.error("mss: НЕДОСТУПЕН.")
        return False
    try:
        with mss.mss() as sct:
            mon = sct.monitors[1]
            frame = sct.grab(mon)
            if frame is not None:
                log.info("mss: УСПЕШНО (кадр получен).")
                return True
            log.error("mss: ОШИБКА (кадр пуст).")
            return False
    except Exception as e:
        log.error(f"mss: ОШИБКА - {e}")
        return False


def run_all():
    """Запускает все проверки и возвращает True, если хотя бы одна прошла."""
    print("\n--- ЗАПУСК ТЕСТИРОВАНИЯ МЕТОДОВ ЗАХВАТА ---")
    results = [test_dxcam(), test_mss()]
    print("--- ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ---\n")
    return any(results)
