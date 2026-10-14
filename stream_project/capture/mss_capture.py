"""Захват экрана через mss (GDI, работает на всех версиях Windows)."""

import time

import cv2
import numpy as np

from ..config import MAX_FPS
from ..deps import mss
from ..frames import set_frame
from ..logs import log
from ..monitors import MONITOR_CONFIGS


def mss_capture():
    """mss: захват всех мониторов в одном цикле."""
    log.info("Метод: mss (все мониторы)")
    try:
        with mss.mss() as sct:
            while True:
                for mon in MONITOR_CONFIGS:
                    try:
                        frame = sct.grab(mon)
                        img = np.array(frame)
                        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                        set_frame(mon['id'], img.copy())
                    except Exception as e:
                        log.error(f"Монитор {mon['id']}: ошибка mss - {e}")
                time.sleep(1.0 / MAX_FPS)
    except Exception as e:
        log.error(f"Критическая ошибка mss: {e}")
