"""Опциональные и обязательные внешние зависимости."""

import sys

# --- dxcam: необязателен (быстрый GPU-захват, Windows 8+) ---
try:
    import dxcam

    DXCAM_AVAILABLE = True
except Exception:
    dxcam = None
    DXCAM_AVAILABLE = False

# --- mss: обязателен (используется и для определения мониторов) ---
try:
    import mss

    MSS_AVAILABLE = True
except ImportError:
    mss = None
    MSS_AVAILABLE = False
    print("Ошибка: установите библиотеку mss командой: pip install mss")
    sys.exit(1)
