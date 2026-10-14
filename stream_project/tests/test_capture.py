"""Tests for the capture layer (through the package API).

Checks that mss and dxcam capture threads actually fill the frame store
for every monitor, and that the helper functions behave.

Run: python -m stream_project.tests.test_capture
"""
import os
import sys
import threading
import time

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import cv2

from stream_project import capture
from stream_project.deps import DXCAM_AVAILABLE
from stream_project.frames import get_frame
from stream_project.monitors import MONITOR_CONFIGS

_HERE = os.path.dirname(os.path.abspath(__file__))
results = []


def check(name, ok, extra=''):
    results.append((name, ok))
    print(f"[{'OK  ' if ok else 'FAIL'}] {name} {extra}")


def wait_frames(monitor_ids, timeout=10.0):
    """Ждём, пока у всех мониторов появятся кадры."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if all(get_frame(mid) is not None for mid in monitor_ids):
            return True
        time.sleep(0.2)
    return False


def frame_sizes(monitor_ids):
    out = []
    for mid in monitor_ids:
        frame = get_frame(mid)
        out.append(f"mon{mid}={'None' if frame is None else frame.shape}")
    return ', '.join(out)


monitor_ids = [m['id'] for m in MONITOR_CONFIGS]
print(f"Мониторы: {monitor_ids}\n")

# ---------------------------------------------------------------- mss
threading.Thread(target=capture.mss_capture, daemon=True).start()
ok = wait_frames(monitor_ids)
check('mss fills frames for every monitor', ok, '-> ' + frame_sizes(monitor_ids))
for mid in monitor_ids:
    frame = get_frame(mid)
    if frame is not None:
        cv2.imwrite(os.path.join(_HERE, f'test_capture_mss_{mid}.jpg'), frame)

# ---------------------------------------------------------------- dxcam
if DXCAM_AVAILABLE:
    capture.dxcam_capture()  # стартует поток на каждый монитор
    ok = wait_frames(monitor_ids)
    check('dxcam fills frames for every monitor', ok, '-> ' + frame_sizes(monitor_ids))
else:
    print('[SKIP] dxcam not installed')

# ---------------------------------------------------------------- helpers
methods = [c for c, _ in capture.available_methods()]
check('available_methods lists mss', 'mss' in methods, f'-> {methods}')

name = capture.start_capture('nonexistent-method')
check('start_capture falls back to mss', name == 'mss_capture', f'-> {name}')

# ---------------------------------------------------------------- summary
print()
passed = sum(1 for _, ok in results if ok)
total = len(results)
print(f'RESULT: {passed}/{total} checks passed')
failed = [n for n, ok in results if not ok]
if failed:
    print('FAILED: ' + ', '.join(failed))
    sys.exit(1)
print('ALL CAPTURE TESTS PASSED')
