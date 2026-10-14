"""Захват экрана через dxcam (Desktop Duplication API, Windows 8+)."""

import threading
import time

from ..config import MAX_FPS
from ..deps import dxcam
from ..frames import set_frame
from ..logs import log
from ..monitors import MONITOR_CONFIGS


def _dxcam_monitor_worker(mon):
    """Захват одного монитора через dxcam в отдельном потоке.

    Почему отдельный поток: get_latest_frame() в dxcam БЛОКИРУЕТСЯ, пока
    на мониторе не появится новый кадр. Если опрашивать несколько камер
    в одном цикле, он застревает на первом же статичном мониторе, и все
    остальные перестают обновляться. Своим потоком каждый монитор
    обновляется независимо.

    Если камера умирает (DXGI access lost: смена разрешения, UAC,
    блокировка экрана) — поток пересоздаёт её автоматически.
    """
    idx = mon['id'] - 1
    restart_delay = 2.0

    while True:
        camera = None
        try:
            camera = dxcam.create(output_idx=idx, output_color="BGR")
            if camera is None:
                log.warning(f"Монитор {mon['id']}: dxcam не создал камеру (output_idx={idx}), "
                            f"повтор через {restart_delay:.0f}с")
                time.sleep(restart_delay)
                continue

            camera.start(target_fps=MAX_FPS, video_mode=True)
            log.info(f"Монитор {mon['id']}: захват dxcam запущен")

            while True:
                frame = camera.get_latest_frame()  # блокируется до нового кадра
                if frame is None:
                    # камера остановлена/потеряла доступ — пересоздаём
                    log.warning(f"Монитор {mon['id']}: dxcam перестал отдавать кадры, "
                                f"пересоздание...")
                    break
                # буфер dxcam переиспользуется — нужна копия
                set_frame(mon['id'], frame.copy())
        except Exception as e:
            log.error(f"Монитор {mon['id']}: камера dxcam упала ({e}), пересоздание...")
        finally:
            if camera is not None:
                try:
                    camera.stop()
                except Exception:
                    pass
        time.sleep(restart_delay)


def dxcam_capture():
    """dxcam: захват ВСЕХ мониторов — по отдельному потоку на каждый."""
    log.info(f"Метод: dxcam ({len(MONITOR_CONFIGS)} мониторов, поток на каждый)")
    for mon in MONITOR_CONFIGS:
        threading.Thread(target=_dxcam_monitor_worker, args=(mon,), daemon=True).start()
        time.sleep(0.3)  # разводим создание камер во времени


def dxcam_capture_monitor1():
    """dxcam: захват ТОЛЬКО монитора 1 (одна камера, output_idx=0).

    Старый проверенный вариант — используйте, если захват нескольких
    мониторов работает нестабильно.
    """
    log.info("Метод: dxcam (только монитор 1)")
    camera = None
    try:
        camera = dxcam.create(output_idx=0, output_color="BGR")
        if camera is None:
            log.error("dxcam: камера для монитора 1 не создана")
            return
        camera.start(target_fps=MAX_FPS, video_mode=True)
        log.info("Камера dxcam запущена")

        while True:
            frame = camera.get_latest_frame()
            if frame is not None:
                set_frame(1, frame.copy())
            time.sleep(1.0 / MAX_FPS)
    except Exception as e:
        log.error(f"Ошибка захвата dxcam: {e}")
    finally:
        if camera:
            try:
                camera.stop()
            except Exception:
                pass
