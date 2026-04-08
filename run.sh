#!/bin/bash
# Скрипт для запуска программы
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/myenv/bin/activate"
echo "Окружение активировано"
echo "Запуск программы..."
python main.py
deactivate
