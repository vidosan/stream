"""Запуск сервера трансляции экрана.

Весь код разнесён по пакету stream_project/ — этот файл оставлен только
для совместимости (старые ярлыки, инструкция, stream.spec):

    python stream.py            # обычный запуск
    python stream.py --test     # проверка методов захвата

Подробности — в stream_project/main.py и ИНСТРУКЦИЯ.md.
"""

import sys

from stream_project.main import main

if __name__ == '__main__':
    sys.exit(main())
