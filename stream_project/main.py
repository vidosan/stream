"""Точка входа: выбор метода захвата и запуск сервера.

Запуск:
    python -m stream_project.main
    python -m stream_project.main --test
"""

import argparse
import os
import sys
import time

from .capture import available_methods, start_capture, test_dxcam, test_mss
from .config import CONFIG_FILE, CONTROL_ENABLED, JPEG_QUALITY, MAX_FPS, PASSWORD
from .deps import DXCAM_AVAILABLE
from .logs import log
from .web import app

HOST = '0.0.0.0'
PORT = 8000


def run_selftest():
    """Проверяет доступные методы захвата и выходит."""
    print("\n--- ЗАПУСК ТЕСТИРОВАНИЯ МЕТОДОВ ЗАХВАТА ---")
    if DXCAM_AVAILABLE:
        test_dxcam()
    test_mss()
    print("--- ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ---\n")


def choose_method_gui():
    """Диалог выбора метода захвата. Возвращает код метода или None."""
    import tkinter as tk

    chosen = {'method': None}

    def select(method):
        chosen['method'] = method
        window.destroy()

    window = tk.Tk()
    window.title("Выбор метода захвата")
    window.geometry("450x320")
    window.resizable(False, False)

    tk.Label(window, text="Выберите метод захвата экрана:",
             font=("Arial", 12, "bold"), pady=10).pack()

    styles = {
        'dxcam': ("#2196F3", "white"),
        'dxcam1': ("#81C7F6", "black"),
        'mss': ("#9E9E9E", "white"),
    }
    for code, label in available_methods():
        bg, fg = styles.get(code, ("#9E9E9E", "white"))
        tk.Button(window, text=label, font=("Arial", 10), bg=bg, fg=fg,
                  width=45, height=2, command=lambda c=code: select(c)).pack(pady=5)

    if not DXCAM_AVAILABLE:
        tk.Label(window, text="dxcam: НЕДОСТУПЕН", fg="red",
                 font=("Arial", 9)).pack()

    window.mainloop()
    return chosen['method']


def print_banner(capture_method):
    print("=" * 60)
    print("  Сервер трансляции")
    print(f"  Конфигурация: {os.path.abspath(CONFIG_FILE)}")
    print(f"  Качество JPEG: {JPEG_QUALITY} | FPS: {MAX_FPS}")
    print(f"  Пароль: {'включен' if PASSWORD else 'выключен'}")
    print(f"  Управление: {'ВКЛЮЧЕНО' if CONTROL_ENABLED else 'выключено (STREAM_CONTROL=1)'}")
    print(f"  Метод захвата: {capture_method}")
    print("-" * 60)
    print(f"  Запуск сервера на http://{HOST}:{PORT}")
    print("  Двойной клик по карточке - открыть в новом окне")
    if CONTROL_ENABLED:
        print("  Управление включено: кнопка 'Режим: Управление' на странице")
    print("=" * 60)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Сервер трансляции экрана")
    parser.add_argument('--test', action='store_true',
                        help="Запустить тесты всех методов захвата и выйти")
    args = parser.parse_args(argv)

    if args.test:
        run_selftest()
        return 0

    capture_method = choose_method_gui()
    if capture_method is None:
        log.error("Метод захвата не выбран - выход.")
        return 1

    start_capture(capture_method)
    time.sleep(2)
    log.info("Поток захвата запущен.")

    print_banner(capture_method)

    try:
        app.run(host=HOST, port=PORT, threaded=True, debug=False)
    except KeyboardInterrupt:
        log.info("Сервер остановлен пользователем.")
    except Exception as e:
        log.error(f"Критическая ошибка: {e}")

    if os.name == 'nt':
        try:
            input("\nНажмите Enter для выхода...")
        except (UnicodeDecodeError, KeyboardInterrupt, EOFError):
            pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
