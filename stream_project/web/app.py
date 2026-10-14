"""Flask-приложение: раздача видео, прокси, приём событий ввода."""

import json
import os
import time

import cv2
import numpy as np
import requests
from flask import Flask, Response, abort, request
from flask_sock import Sock

from ..config import (
    CONFIG_FILE,
    CONTROL_ENABLED,
    FRAME_TIMEOUT,
    JPEG_QUALITY,
    MAX_FPS,
    PASSWORD,
    is_local_host,
)
from ..control import apply_input_event, forward_input, release_all_modifiers
from ..frames import get_frame
from ..logs import log
from ..monitors import MONITOR_CONFIGS
from .pages import render_index, render_view

app = Flask(__name__)
sock = Sock(app)


# =====================================================================
# Авторизация
# =====================================================================
@app.before_request
def check_auth():
    if PASSWORD and not request.path.startswith('/static'):
        auth = request.args.get('pwd', '') or request.headers.get('X-Stream-Password', '')
        if auth != PASSWORD:
            abort(401, "Неверный пароль. Укажите ?pwd=ВАШ_ПАРОЛЬ")


# =====================================================================
# Видео
# =====================================================================
def generate_stream(monitor_id):
    """MJPEG-поток монитора; при отсутствии сигнала — заглушка."""
    while True:
        frame = get_frame(monitor_id)
        if frame is not None:
            ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            if ok:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
        else:
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(img, f"No signal (Monitor {monitor_id})", (100, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 50])
            if ok:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
        time.sleep(1.0 / MAX_FPS)


@app.route('/screen/<int:monitor_id>')
def screen_stream(monitor_id):
    """Поток монитора локальной машины."""
    if 1 <= monitor_id <= len(MONITOR_CONFIGS):
        return Response(
            generate_stream(monitor_id),
            mimetype='multipart/x-mixed-replace; boundary=frame',
        )
    return "Монитор не найден", 404


@app.route('/proxy/<path:url>')
def proxy(url):
    """Прокси для потока удалённого сервера (чтобы не было проблем с CORS)."""
    try:
        resp = requests.get(f"http://{url}", stream=True, timeout=(3, FRAME_TIMEOUT))
        return Response(
            resp.iter_content(chunk_size=8192),
            mimetype=resp.headers.get('content-type', 'multipart/x-mixed-replace; boundary=frame'),
        )
    except requests.ConnectionError:
        return "Сервер недоступен", 502
    except requests.Timeout:
        return "Таймаут соединения", 504
    except Exception as e:
        log.error(f"Прокси {url}: {e}")
        return "Ошибка прокси", 502


# =====================================================================
# Страницы
# =====================================================================
def _load_remote_servers():
    """Читает список серверов из servers.json (ошибки не фатальны)."""
    if not os.path.exists(CONFIG_FILE):
        return []
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            servers = json.load(f)
        return servers if isinstance(servers, list) else []
    except Exception:
        return []


@app.route('/')
def index():
    """Сетка карточек всех мониторов (локальных и удалённых)."""
    return render_index(
        remote_servers=_load_remote_servers(),
        password=PASSWORD,
        control_enabled=CONTROL_ENABLED,
        is_local_host=is_local_host,
    )


@app.route('/view')
def view_page():
    """Полноэкранный просмотр одного монитора с управлением."""
    return render_view(
        mon=request.args.get('mon', '1'),
        target=request.args.get('target', ''),
        pwd=request.args.get('pwd', ''),
        control_enabled=CONTROL_ENABLED,
    )


# =====================================================================
# Управление вводом
# =====================================================================
@app.route('/input', methods=['POST'])
def input_endpoint():
    """Приём одного события ввода (используется в т.ч. для пересылки между серверами)."""
    if not CONTROL_ENABLED:
        return {"ok": False, "error": "control_disabled"}, 403
    ev = request.get_json(silent=True)
    if not isinstance(ev, dict):
        return {"ok": False, "error": "bad_json"}, 400
    apply_input_event(ev)
    return {"ok": True}


@sock.route('/ws')
def ws_input(ws):
    """WebSocket-канал для событий ввода из браузера (низкая задержка)."""
    if not CONTROL_ENABLED:
        ws.send(json.dumps({"ok": False, "error": "control_disabled"}))
        return

    log.info("Управление: подключился клиент по WebSocket")
    try:
        while True:
            raw = ws.receive()
            if raw is None:
                break
            try:
                msg = json.loads(raw)
            except (ValueError, TypeError):
                continue

            # Батч событий: {"events": [...]} либо одно событие
            events = msg.get('events') if isinstance(msg, dict) else None
            if events is None:
                events = [msg] if isinstance(msg, dict) else []

            target = msg.get('target') or '' if isinstance(msg, dict) else ''
            pwd = msg.get('pwd', '') if isinstance(msg, dict) else ''

            for ev in events:
                if not isinstance(ev, dict):
                    continue
                if target:
                    forward_input(target, ev, pwd)
                else:
                    apply_input_event(ev)
    except Exception as e:
        log.info(f"Управление: клиент отключился ({e})")
    finally:
        # Не оставляем зажатые клавиши после обрыва связи
        release_all_modifiers()
