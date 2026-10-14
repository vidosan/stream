"""Tests for the input pipeline (no real cursor involved).

Verifies that browser events are translated into correct Win32 calls:
monitor offsets, buttons, wheel, keys and the unicode/virtual-key choice.

Run: python -m stream_project.tests.test_input_pipeline
"""
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from stream_project.control import events, win32
from stream_project.monitors import MONITOR_CONFIGS

calls = []


def _record(*args):
    calls.append(args)


# Подменяем низкоуровневые вызовы — проверяем только логику разбора
win32.move_mouse = lambda x, y: _record('move', x, y)
win32.mouse_button = lambda b, d: _record('button', b, d)
win32.mouse_wheel = lambda d: _record('wheel', d)
win32.key_event = lambda c, k, d, unicode_mode=False: _record('key', c, k, d, unicode_mode)
win32.release_all_modifiers = lambda: _record('release')

results = []


def check(name, ok, extra=''):
    results.append((name, ok))
    print(f"[{'OK  ' if ok else 'FAIL'}] {name} {extra}")


def reset():
    calls.clear()


mon1 = next(m for m in MONITOR_CONFIGS if m['id'] == 1)
mon2 = next((m for m in MONITOR_CONFIGS if m['id'] == 2), None)

# ---------------------------------------------------------------- mouse move
reset()
events.apply_input_event({'type': 'mousemove', 'mon': 1, 'x': 10, 'y': 20})
expected = ('move', mon1['left'] + 10, mon1['top'] + 20)
check('mousemove on monitor 1 adds monitor offset', calls == [expected],
      f'-> {calls} vs {[expected]}')

if mon2:
    reset()
    events.apply_input_event({'type': 'mousemove', 'mon': 2, 'x': 10, 'y': 20})
    expected = ('move', mon2['left'] + 10, mon2['top'] + 20)
    check('mousemove on monitor 2 adds monitor offset', calls == [expected],
          f'-> {calls} vs {[expected]}')
else:
    print('[SKIP] monitor 2 offset check (single monitor)')

reset()
events.apply_input_event({'type': 'mousemove', 'x': 5, 'y': 6})
check('mousemove without mon defaults to monitor 1',
      calls == [('move', mon1['left'] + 5, mon1['top'] + 6)], f'-> {calls}')

reset()
events.apply_input_event({'type': 'mousemove', 'mon': 99, 'x': 5, 'y': 6})
check('mousemove with unknown monitor uses raw coords',
      calls == [('move', 5, 6)], f'-> {calls}')

# ---------------------------------------------------------------- buttons
reset()
events.apply_input_event({'type': 'mousedown', 'button': 'left'})
events.apply_input_event({'type': 'mouseup', 'button': 'left'})
events.apply_input_event({'type': 'mousedown', 'button': 'right'})
events.apply_input_event({'type': 'mousedown', 'button': 'middle'})
check('mouse buttons routed',
      calls == [('button', 'left', True), ('button', 'left', False),
                ('button', 'right', True), ('button', 'middle', True)], f'-> {calls}')

# ---------------------------------------------------------------- wheel
reset()
events.apply_input_event({'type': 'wheel', 'delta': -120})
events.apply_input_event({'type': 'wheel', 'delta': 120})
check('wheel routed', calls == [('wheel', -120), ('wheel', 120)], f'-> {calls}')

# ---------------------------------------------------------------- release
reset()
events.apply_input_event({'type': 'release'})
check('release routed', calls == [('release',)], f'-> {calls}')

# ---------------------------------------------------------------- keys
reset()
events.apply_input_event({'type': 'keydown', 'code': 'KeyA', 'key': 'a'})
check('plain letter sent as unicode',
      calls == [('key', 'KeyA', 'a', True, True)], f'-> {calls}')

reset()
events.apply_input_event({'type': 'keydown', 'code': 'ControlLeft', 'key': 'Control'})
events.apply_input_event({'type': 'keydown', 'code': 'KeyC', 'key': 'c'})
check('ctrl+c sent as virtual key (combo)',
      calls == [('key', 'ControlLeft', 'Control', True, False),
                ('key', 'KeyC', 'c', True, False)], f'-> {calls}')

reset()
events.apply_input_event({'type': 'keyup', 'code': 'ControlLeft', 'key': 'Control'})
events.apply_input_event({'type': 'keydown', 'code': 'KeyC', 'key': 'c'})
check('after ctrl released letter is unicode again',
      calls == [('key', 'ControlLeft', 'Control', False, False),
                ('key', 'KeyC', 'c', True, True)], f'-> {calls}')

reset()
events.apply_input_event({'type': 'keydown', 'code': 'ArrowUp', 'key': 'ArrowUp'})
check('special key sent as virtual key',
      calls == [('key', 'ArrowUp', 'ArrowUp', True, False)], f'-> {calls}')

# ---------------------------------------------------------------- unknown
reset()
events.apply_input_event({'type': 'nonsense'})
check('unknown event ignored', calls == [], f'-> {calls}')

# ---------------------------------------------------------------- summary
print()
passed = sum(1 for _, ok in results if ok)
total = len(results)
print(f'RESULT: {passed}/{total} checks passed')
failed = [n for n, ok in results if not ok]
if failed:
    print('FAILED: ' + ', '.join(failed))
    sys.exit(1)
print('ALL PIPELINE TESTS PASSED')
