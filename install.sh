#!/bin/bash

# ============================================================
# TelegramAssistant - Быстрая установка
# Версия: 1.0.5
# ============================================================
# Использование:
#   curl -sSL https://raw.githubusercontent.com/Drentis/TelegramAssistant/master/install.sh | sudo bash
# ============================================================

set -e

# Временная директория
TEMP_DIR=$(mktemp -d)
DEPLOY_SCRIPT="$TEMP_DIR/deploy.sh"

echo "⏳ Загрузка скрипта установки..."

# Скачиваем скрипт установки
curl -sSL "https://raw.githubusercontent.com/Drentis/TelegramAssistant/master/deploy.sh" -o "$DEPLOY_SCRIPT"

# Проверяем целостность
if [ ! -s "$DEPLOY_SCRIPT" ]; then
    echo "❌ Ошибка загрузки скрипта"
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo "✓ Скрипт загружен"
echo ""

# Запускаем скрипт с передачей stdin
chmod +x "$DEPLOY_SCRIPT"
bash "$DEPLOY_SCRIPT"

# Очистка
rm -rf "$TEMP_DIR"
