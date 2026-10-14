"""Конфигурация сервера: параметры захвата, раздачи видео и управления."""

import os
import socket
import sys
from pathlib import Path

# =====================================================================
# Раздача видео
# =====================================================================
JPEG_QUALITY = 85
MAX_FPS = 15
FRAME_TIMEOUT = 15

#: Имя файла со списком серверов
CONFIG_NAME = 'servers.json'


def _find_config_file():
    """Ищет servers.json.

    Порядок поиска:
      1. рядом с .exe — чтобы список серверов можно было править без пересборки;
      2. рядом с этим модулем — при запуске из исходников.
    """
    candidates = []
    if getattr(sys, 'frozen', False):
        candidates.append(Path(sys.executable).resolve().parent / CONFIG_NAME)
    candidates.append(Path(__file__).resolve().parent / CONFIG_NAME)
    for path in candidates:
        if path.exists():
            return str(path)
    return str(candidates[-1])


CONFIG_FILE = _find_config_file()

# =====================================================================
# Пароль (пусто = авторизация выключена)
# =====================================================================
PASSWORD = os.environ.get('STREAM_PASSWORD', '')

# =====================================================================
# Управление мышью и клавиатурой с другого ПК (по умолчанию ВЫКЛЮЧЕНО).
# Включить: переменная окружения STREAM_CONTROL=1
# =====================================================================
CONTROL_ENABLED = os.environ.get('STREAM_CONTROL', '0') == '1'

# Таймаут запроса при пересылке ввода на удалённый сервер (сек)
INPUT_FORWARD_TIMEOUT = 2


def _collect_local_ips():
    """Собирает адреса, по которым сервер может обращаться сам к себе."""
    ips = {'127.0.0.1', 'localhost', '::1'}
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            ips.add(ip)
    except Exception:
        pass
    return ips


LOCAL_IPS = _collect_local_ips()


def is_local_host(host):
    """True, если host — это та же машина, где запущен сервер."""
    return str(host) in LOCAL_IPS
