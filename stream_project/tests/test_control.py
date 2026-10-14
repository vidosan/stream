"""Tests for remote control: /input, /ws, /view and MJPEG regression.

Starts the Flask app in a subprocess twice:
  1) control disabled (STREAM_CONTROL unset) -> input must be rejected
  2) control enabled  (STREAM_CONTROL=1)     -> input must be applied

Run: python -m stream_project.tests.test_control
Note: this really moves the mouse and presses keys, so do not touch the
mouse while it runs.
"""
import ctypes
import json
import os
import subprocess
import sys
import time

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import requests

PORT = 8123
BASE = f"http://127.0.0.1:{PORT}"

user32 = ctypes.windll.user32

results = []


def check(name, ok, extra=''):
    results.append((name, ok))
    print(f"[{'OK  ' if ok else 'FAIL'}] {name} {extra}")


def get_cursor():
    from ctypes import wintypes
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def cursor_reached(expected, tol=2, timeout=1.5):
    """Ждёт, пока курсор окажется в нужной точке.

    Читаем сразу (событие уже применено до ответа сервера) и затем опрашиваем:
    если физическую мышь в этот момент двигают, единственное чтение может
    случайно попасть на чужую позицию.
    """
    last = None
    deadline = time.time() + timeout
    while True:
        last = get_cursor()
        if abs(last[0] - expected[0]) <= tol and abs(last[1] - expected[1]) <= tol:
            return True, last
        if time.time() >= deadline:
            return False, last
        time.sleep(0.02)


def start_server(control_enabled, password=None):
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    if control_enabled:
        env['STREAM_CONTROL'] = '1'
    else:
        env.pop('STREAM_CONTROL', None)
    if password:
        env['STREAM_PASSWORD'] = password
    else:
        env.pop('STREAM_PASSWORD', None)
    code = (f"from stream_project.web import app; app.run(host='127.0.0.1', port={PORT},"
            f" threaded=True, debug=False)")
    proc = subprocess.Popen([sys.executable, '-c', code], env=env, cwd=_ROOT,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for _ in range(80):
        try:
            requests.get(BASE + '/', timeout=0.5)
            return proc
        except requests.RequestException:
            if proc.poll() is not None:
                out = proc.stdout.read().decode('utf-8', 'replace')
                raise RuntimeError(f'server exited:\n{out}')
            time.sleep(0.25)
    proc.kill()
    raise RuntimeError('server did not start')


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# =====================================================================
print('=== 1. CONTROL DISABLED (default) ===')
proc = start_server(False)
try:
    r = requests.get(BASE + '/', timeout=5)
    check('GET / (viewing page)', r.status_code == 200, f'-> {r.status_code}')

    r = requests.get(BASE + '/screen/1', timeout=5, stream=True)
    ctype = r.headers.get('Content-Type', '')
    check('GET /screen/1 (MJPEG alive)', r.status_code == 200 and 'multipart' in ctype,
          f'-> {r.status_code} {ctype}')
    r.close()

    r = requests.post(BASE + '/input', json={'type': 'mousemove', 'mon': 1, 'x': 10, 'y': 10}, timeout=5)
    check('POST /input rejected when disabled', r.status_code == 403, f'-> {r.status_code}')

    r = requests.get(BASE + '/view?mon=1', timeout=5)
    check('GET /view renders', r.status_code == 200 and 'screen' in r.text, f'-> {r.status_code}')

    r = requests.get(BASE + '/', timeout=5)
    check('page reports control disabled', 'const CONTROL_ENABLED = false' in r.text)
finally:
    stop_server(proc)

# =====================================================================
print()
print('=== 2. CONTROL ENABLED (STREAM_CONTROL=1) ===')
saved = get_cursor()
proc = start_server(True)
try:
    r = requests.get(BASE + '/', timeout=5)
    check('page reports control enabled', 'const CONTROL_ENABLED = true' in r.text)

    # --- HTTP /input: mouse move ---
    target = (300, 200)
    r = requests.post(BASE + '/input', json={'type': 'mousemove', 'mon': 1, 'x': target[0], 'y': target[1]}, timeout=5)
    ok_pos, pos = cursor_reached(target)
    ok = r.status_code == 200 and ok_pos
    check('HTTP /input moves cursor', ok, f'-> {r.status_code}, cursor={pos}, expected={target}')

    # --- monitor 2: control must work on every monitor ---
    from stream_project.monitors import MONITOR_CONFIGS
    if len(MONITOR_CONFIGS) >= 2:
        mon2 = next(m for m in MONITOR_CONFIGS if m['id'] == 2)
        exp = (mon2['left'] + 300, mon2['top'] + 200)
        r = requests.post(BASE + '/input', json={'type': 'mousemove', 'mon': 2, 'x': 300, 'y': 200}, timeout=5)
        ok_pos, pos = cursor_reached(exp)
        ok = r.status_code == 200 and ok_pos
        check('HTTP /input moves cursor on monitor 2', ok, f'-> cursor={pos}, expected={exp}')
    else:
        print('[SKIP] monitor 2 check (single-monitor machine)')

    # --- keyboard events accepted ---
    r1 = requests.post(BASE + '/input', json={'type': 'keydown', 'code': 'ShiftLeft', 'key': 'Shift'}, timeout=5)
    r2 = requests.post(BASE + '/input', json={'type': 'keyup', 'code': 'ShiftLeft', 'key': 'Shift'}, timeout=5)
    check('HTTP /input accepts keys', r1.status_code == 200 and r2.status_code == 200,
          f'-> {r1.status_code}/{r2.status_code}')

    # --- release event ---
    r = requests.post(BASE + '/input', json={'type': 'release'}, timeout=5)
    check('HTTP /input accepts release', r.status_code == 200, f'-> {r.status_code}')

    # --- bad json ---
    r = requests.post(BASE + '/input', json=[1, 2, 3], timeout=5)
    check('HTTP /input rejects bad json', r.status_code == 400, f'-> {r.status_code}')

    # --- WebSocket end-to-end ---
    try:
        import simple_websocket
        ws = simple_websocket.Client(f'ws://127.0.0.1:{PORT}/ws')
        ws_target = (500, 350)
        ws.send(json.dumps({'events': [
            {'type': 'mousemove', 'mon': 1, 'x': ws_target[0], 'y': ws_target[1]},
        ]}))
        ok_pos, pos = cursor_reached(ws_target)
        check('WebSocket /ws moves cursor', ok_pos, f'-> cursor={pos}, expected={ws_target}')

        ws.send(json.dumps({'events': [
            {'type': 'keydown', 'code': 'KeyA', 'key': 'a'},
            {'type': 'keyup', 'code': 'KeyA', 'key': 'a'},
        ]}))
        time.sleep(0.2)
        check('WebSocket /ws accepts keys', True)
        ws.close()
    except Exception as e:
        check('WebSocket /ws works', False, f'-> {type(e).__name__}: {e}')

    # --- regression: viewing still fine with control on ---
    r = requests.get(BASE + '/screen/1', timeout=5, stream=True)
    chunk = next(r.iter_content(1024), b'')
    check('MJPEG still streams with control on', r.status_code == 200 and len(chunk) > 0)
    r.close()

    r = requests.get(BASE + '/', timeout=5)
    check('card has data-target/data-mon', 'data-mon=' in r.text and 'data-target=' in r.text)
finally:
    stop_server(proc)
    user32.SetCursorPos(saved[0], saved[1])
    print(f'(cursor restored to {saved})')

# =====================================================================
print()
print('=== 3. PASSWORD PROTECTION ===')
proc = start_server(True, password='secret')
try:
    r = requests.post(BASE + '/input', json={'type': 'mousemove', 'mon': 1, 'x': 1, 'y': 1}, timeout=5)
    check('POST /input without password rejected', r.status_code == 401, f'-> {r.status_code}')

    r = requests.post(BASE + '/input?pwd=secret', json={'type': 'release'}, timeout=5)
    check('POST /input with password accepted', r.status_code == 200, f'-> {r.status_code}')

    import simple_websocket

    denied = False
    try:
        ws = simple_websocket.Client(f'ws://127.0.0.1:{PORT}/ws')
        try:
            ws.send(json.dumps({'events': [{'type': 'release'}]}))
            ws.receive(timeout=1)
        except Exception:
            denied = True
        finally:
            try:
                ws.close()
            except Exception:
                pass
    except Exception:
        denied = True  # рукопожатие отклонено
    check('WebSocket without password rejected', denied)

    try:
        ws = simple_websocket.Client(f'ws://127.0.0.1:{PORT}/ws?pwd=secret')
        ws.send(json.dumps({'events': [{'type': 'release'}]}))
        check('WebSocket with password accepted', True)
        ws.close()
    except Exception as e:
        check('WebSocket with password accepted', False, f'-> {type(e).__name__}: {e}')
finally:
    stop_server(proc)

# =====================================================================
print()
passed = sum(1 for _, ok in results if ok)
total = len(results)
print(f'RESULT: {passed}/{total} checks passed')
failed = [n for n, ok in results if not ok]
if failed:
    print('FAILED: ' + ', '.join(failed))
    sys.exit(1)
print('ALL TESTS PASSED')
