"""Пересылка событий ввода на удалённые серверы.

Ввод идёт тем же путём, что и видео: клиент отправляет событие серверу,
к которому подключён, а тот пересылает его дальше на нужный ПК.
"""

import requests

from ..config import INPUT_FORWARD_TIMEOUT
from ..logs import log


def forward_input(target, ev, pwd=''):
    """Пересылает событие ввода на удалённый сервер (host:port)."""
    url = f"http://{target}/input"
    params = {'pwd': pwd} if pwd else None
    try:
        requests.post(url, json=ev, params=params, timeout=INPUT_FORWARD_TIMEOUT)
    except requests.RequestException as e:
        log.debug(f"Пересылка ввода на {target} не удалась: {e}")
