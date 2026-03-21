#!/bin/bash

# ============================================================
# Скрипт автоматической установки TelegramAssistant на VPS
# ============================================================
# Использование: ./install.sh
# ============================================================

set -e  # Выход при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # Без цвета

# Логотип
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  TelegramAssistant - Автоматическая установка на VPS     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ============================================================
# Проверка прав root
# ============================================================
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Пожалуйста, запустите от root (sudo ./install.sh)${NC}"
    exit 1
fi

# ============================================================
# Обновление системы
# ============================================================
echo -e "\n${YELLOW}📦 Обновление пакетов...${NC}"
apt update && apt upgrade -y

# ============================================================
# Установка зависимостей
# ============================================================
echo -e "\n${YELLOW}📦 Установка зависимостей...${NC}"
apt install -y python3 python3-pip python3-venv git curl

# ============================================================
# Создание пользователя для бота
# ============================================================
BOT_USER="telegramassistant"
BOT_DIR="/opt/telegramassistant"

if ! id "$BOT_USER" &>/dev/null; then
    echo -e "\n${YELLOW}👤 Создание пользователя $BOT_USER...${NC}"
    useradd -r -s /bin/false -d "$BOT_DIR" "$BOT_USER"
else
    echo -e "\n${GREEN}✓ Пользователь $BOT_USER уже существует${NC}"
fi

# ============================================================
# Создание директории
# ============================================================
echo -e "\n${YELLOW}📁 Создание директории $BOT_DIR...${NC}"
mkdir -p "$BOT_DIR"
chown "$BOT_USER:$BOT_USER" "$BOT_DIR"

# ============================================================
# Копирование файлов проекта
# ============================================================
echo -e "\n${YELLOW}📋 Копирование файлов проекта...${NC}"

# Копируем файлы из текущей директории
cp -r ./* "$BOT_DIR/"
chown -R "$BOT_USER:$BOT_USER" "$BOT_DIR"

# ============================================================
# Настройка виртуального окружения
# ============================================================
echo -e "\n${YELLOW}🐍 Создание виртуального окружения...${NC}"
cd "$BOT_DIR"
su -s /bin/bash "$BOT_USER" -c "python3 -m venv venv"

echo -e "\n${YELLOW}📦 Установка зависимостей Python...${NC}"
su -s /bin/bash "$BOT_USER" -c "$BOT_DIR/venv/bin/pip install --upgrade pip"
su -s /bin/bash "$BOT_USER" -c "$BOT_DIR/venv/bin/pip install -r $BOT_DIR/requirements.txt"

# ============================================================
# Настройка .env файла
# ============================================================
echo -e "\n${YELLOW}⚙️  Настройка токенов бота${NC}"

# Запрашиваем токен бота
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              НАСТРОЙКА TELEGRAM BOT TOKEN                ║${NC}"
echo -e "${BLUE}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║  Получить токен можно у @BotFather в Telegram            ║${NC}"
echo -e "${BLUE}║  Отправьте боту команду /newbot                          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

while true; do
    echo -en "${YELLOW}Введите токен бота: ${NC}"
    read BOT_TOKEN_INPUT
    
    # Проверяем формат токена (должен содержать :)
    if [[ "$BOT_TOKEN_INPUT" == *":"* ]]; then
        echo -e "${GREEN}✓ Токен принят${NC}"
        break
    else
        echo -e "${RED}❌ Неверный формат токена! Токен должен содержать ':'${NC}"
        echo -e "${YELLOW}Попробуйте ещё раз${NC}"
    fi
done

# Запрашиваем API ключ погоды (опционально)
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           НАСТРОЙКА OPENWEATHERMAP API KEY               ║${NC}"
echo -e "${BLUE}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║  API ключ для прогноза погоды (можно пропустить)         ║${NC}"
echo -e "${BLUE}║  Получить на https://openweathermap.org/api              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

while true; do
    echo -en "${YELLOW}Введите API ключ погоды (или нажмите Enter для пропуска): ${NC}"
    read WEATHER_KEY_INPUT

    if [[ -z "$WEATHER_KEY_INPUT" ]]; then
        echo -e "${YELLOW}⊘ Пропущено (погода будет недоступна)${NC}"
        break
    elif [[ ${#WEATHER_KEY_INPUT} -ge 16 ]]; then
        echo -e "${GREEN}✓ API ключ принят${NC}"
        break
    else
        echo -e "${RED}❌ Слишком короткий ключ!${NC}"
        echo -e "${YELLOW}Попробуйте ещё раз или нажмите Enter для пропуска${NC}"
    fi
done

# Запрашиваем ID администратора (опционально)
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              НАСТРОЙКА ADMIN ID                          ║${NC}"
echo -e "${BLUE}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║  Telegram ID администратора (можно пропустить)           ║${NC}"
echo -e "${BLUE}║  Получить через бота @userinfobot или @getmyid_bot       ║${NC}"
echo -e "${BLUE}║  Админ будет иметь доступ к статистике и обновлению      ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

while true; do
    echo -en "${YELLOW}Введите Telegram ID администратора (или Enter для пропуска): ${NC}"
    read ADMIN_ID_INPUT

    if [[ -z "$ADMIN_ID_INPUT" ]]; then
        echo -e "${YELLOW}⊘ Пропущено (админ-панель будет недоступна)${NC}"
        break
    elif [[ "$ADMIN_ID_INPUT" =~ ^[0-9]+$ ]]; then
        echo -e "${GREEN}✓ Admin ID принят${NC}"
        break
    else
        echo -e "${RED}❌ Неверный формат! ID должен быть числом${NC}"
        echo -e "${YELLOW}Попробуйте ещё раз или нажмите Enter для пропуска${NC}"
    fi
done

# Запрашиваем GitHub токен (опционально, для обновления через Telegram)
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           НАСТРОЙКА GITHUB TOKEN                         ║${NC}"
echo -e "${BLUE}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║  Токен для обновления бота через Telegram (можно         ║${NC}"
echo -e "${BLUE}║  пропустить, но тогда обновление через Telegram не       ║${NC}"
echo -e "${BLUE}║  будет работать)                                         ║${NC}"
echo -e "${BLUE}║  Создать: https://github.com/settings/tokens             ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

while true; do
    echo -en "${YELLOW}Введите GitHub токен (или Enter для пропуска): ${NC}"
    read GITHUB_TOKEN_INPUT

    if [[ -z "$GITHUB_TOKEN_INPUT" ]]; then
        echo -e "${YELLOW}⊘ Пропущено (обновление через Telegram будет недоступно)${NC}"
        break
    elif [[ "$GITHUB_TOKEN_INPUT" == ghp_* ]] || [[ ${#GITHUB_TOKEN_INPUT} -ge 30 ]]; then
        echo -e "${GREEN}✓ GitHub токен принят${NC}"
        break
    else
        echo -e "${RED}❌ Неверный формат! Токен должен начинаться с 'ghp_'${NC}"
        echo -e "${YELLOW}Попробуйте ещё раз или нажмите Enter для пропуска${NC}"
    fi
done

# Создаём .env файл
echo -e "\n${YELLOW}📝 Создание файла .env...${NC}"

cat > "$BOT_DIR/.env" << EOF
# Токен бота (получить у @BotFather)
BOT_TOKEN=$BOT_TOKEN_INPUT

# OpenWeatherMap API ключ (получить на https://openweathermap.org/api)
WEATHER_API_KEY=$WEATHER_KEY_INPUT

# Telegram ID администратора (получить у @userinfobot)
ADMIN_ID=$ADMIN_ID_INPUT

# GitHub токен (для обновления через Telegram)
GITHUB_TOKEN=$GITHUB_TOKEN_INPUT
EOF

chown "$BOT_USER:$BOT_USER" "$BOT_DIR/.env"
chmod 600 "$BOT_DIR/.env"  # Только владелец может читать/писать

echo -e "${GREEN}✓ Файл .env создан${NC}"

# ============================================================
# Создание systemd сервиса
# ============================================================
echo -e "\n${YELLOW}⚙️  Настройка systemd сервиса...${NC}"

cat > /etc/systemd/system/telegramassistant.service << 'EOF'
[Unit]
Description=TelegramAssistant Bot Service
After=network.target

[Service]
Type=simple
User=telegramassistant
Group=telegramassistant
WorkingDirectory=/opt/telegramassistant
ExecStart=/opt/telegramassistant/venv/bin/python /opt/telegramassistant/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=telegramassistant

# Ограничения ресурсов
MemoryLimit=512M
CPUQuota=50%

# Безопасность
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ systemd сервис создан${NC}"

# ============================================================
# Перезагрузка systemd и запуск сервиса
# ============================================================
echo -e "\n${YELLOW}🔄 Перезагрузка systemd...${NC}"
systemctl daemon-reload

echo -e "\n${YELLOW}🚀 Запуск бота...${NC}"
systemctl enable telegramassistant
systemctl start telegramassistant

# Пауза для запуска
sleep 2

# ============================================================
# Проверка статуса
# ============================================================
echo -e "\n${YELLOW}📊 Проверка статуса сервиса...${NC}"

if systemctl is-active --quiet telegramassistant; then
    echo -e "${GREEN}✓ Бот успешно запущен!${NC}"
else
    echo -e "${RED}❌ Бот не запустился. Проверьте логи:${NC}"
    echo -e "${YELLOW}journalctl -u telegramassistant -f${NC}"
    exit 1
fi

# ============================================================
# Настройка логирования (опционально)
# ============================================================
echo -e "\n${YELLOW}📝 Настройка логирования...${NC}"

# Создаём директорию для логов
mkdir -p /var/log/tgbot
chown "$BOT_USER:$BOT_USER" /var/log/tgbot

echo -e "${GREEN}✓ Логи доступны через:${NC}"
echo -e "${BLUE}journalctl -u tgbot -f${NC}"
echo -e "${BLUE}journalctl -u tgbot -n 100${NC}"

# ============================================================
# Создание скрипта управления
# ============================================================
echo -e "\n${YELLOW}🔧 Создание скрипта управления...${NC}"

cat > /usr/local/bin/telegramactl << 'EOF'
#!/bin/bash
# Скрипт управления Telegram ботом

ENV_FILE="/opt/telegramassistant/.env"

case "$1" in
    start)
        echo "Запуск бота..."
        systemctl start telegramassistant
        ;;
    stop)
        echo "Остановка бота..."
        systemctl stop telegramassistant
        ;;
    restart)
        echo "Перезапуск бота..."
        systemctl restart telegramassistant
        ;;
    status)
        systemctl status telegramassistant
        ;;
    logs)
        journalctl -u telegramassistant -f
        ;;
    update)
        echo "Обновление бота..."
        systemctl stop telegramassistant
        cd /opt/telegramassistant
        
        # Проверяем наличие .git директории
        if [ ! -d ".git" ]; then
            echo "⚠️  .git директория не найдена. Инициализация..."
            git init
            git remote add origin https://github.com/Drentis/TelegramAssistant.git
            git fetch origin
            git checkout -f main
            git reset --hard origin/main
        else
            git pull
        fi
        
        /opt/telegramassistant/venv/bin/pip install -r /opt/telegramassistant/requirements.txt
        chown -R telegramassistant:telegramassistant /opt/telegramassistant
        systemctl start telegramassistant
        echo "✓ Бот обновлён!"
        ;;
    edit)
        echo "╔══════════════════════════════════════════════════════════╗"
        echo "║              РЕДАКТИРОВАНИЕ НАСТРОЕК                     ║"
        echo "╚══════════════════════════════════════════════════════════╝"
        echo ""
        echo "Что хотите отредактировать?"
        echo "  1) Токен бота (BOT_TOKEN)"
        echo "  2) API ключ погоды (WEATHER_API_KEY)"
        echo "  3) Admin ID (ADMIN_ID)"
        echo "  4) Редактировать .env вручную"
        echo "  0) Выход"
        echo ""
        read -p "Введите номер (0-4): " choice

        case $choice in
            1)
                echo ""
                read -p "Введите новый токен бота: " new_token
                if [[ "$new_token" == *":"* ]]; then
                    sed -i "s/^BOT_TOKEN=.*/BOT_TOKEN=$new_token/" "$ENV_FILE"
                    echo "✓ Токен бота обновлён"
                    systemctl restart telegramassistant
                else
                    echo "❌ Неверный формат токена!"
                fi
                ;;
            2)
                echo ""
                read -p "Введите новый API ключ погоды: " new_key
                sed -i "s/^WEATHER_API_KEY=.*/WEATHER_API_KEY=$new_key/" "$ENV_FILE"
                echo "✓ API ключ погоды обновлён"
                systemctl restart telegramassistant
                ;;
            3)
                echo ""
                read -p "Введите новый Admin ID: " new_admin
                if [[ "$new_admin" =~ ^[0-9]+$ ]]; then
                    sed -i "s/^ADMIN_ID=.*/ADMIN_ID=$new_admin/" "$ENV_FILE"
                    echo "✓ Admin ID обновлён"
                    systemctl restart telegramassistant
                else
                    echo "❌ Admin ID должен быть числом!"
                fi
                ;;
            4)
                nano "$ENV_FILE"
                echo "✓ Файл .env отредактирован"
                systemctl restart telegramassistant
                ;;
            0)
                echo "Выход"
                ;;
            *)
                echo "❌ Неверный номер"
                ;;
        esac
        ;;
    delete)
        echo "⚠️  УДАЛЕНИЕ БОТА"
        echo "Это действие удалит:"
        echo "  • Все данные пользователей"
        echo "  • Все настройки бота"
        echo "  • Системный сервис"
        echo "  • Файлы бота"
        echo ""
        read -p "Вы уверены? Введите 'yes' для подтверждения: " confirm
        if [ "$confirm" = "yes" ]; then
            echo "Остановка бота..."
            systemctl stop telegramassistant
            systemctl disable telegramassistant
            echo "Удаление сервиса..."
            rm /etc/systemd/system/telegramassistant.service
            systemctl daemon-reload
            echo "Удаление файлов..."
            rm -rf /opt/telegramassistant
            echo "Удаление пользователя..."
            userdel -r telegramassistant 2>/dev/null || true
            rm /usr/local/bin/telegramactl
            echo "✓ Бот полностью удалён"
        else
            echo "❌ Удаление отменено"
        fi
        ;;
    version)
        echo "TelegramAssistant v1.0.2"
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs|update|edit|delete|version}"
        exit 1
        ;;
esac
EOF

chmod +x /usr/local/bin/telegramactl

echo -e "${GREEN}✓ Скрипт управления создан${NC}"
echo -e "${YELLOW}Используйте:${NC}"
echo -e "${BLUE}  telegramactl start    # Запустить бота${NC}"
echo -e "${BLUE}  telegramactl stop     # Остановить бота${NC}"
echo -e "${BLUE}  telegramactl restart  # Перезапустить бота${NC}"
echo -e "${BLUE}  telegramactl status   # Проверить статус${NC}"
echo -e "${BLUE}  telegramactl logs     # Просмотр логов${NC}"
echo -e "${BLUE}  telegramactl update   # Обновить бота${NC}"

# ============================================================
# Финальное сообщение
# ============================================================
echo -e "\n${GREEN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                  УСТАНОВКА ЗАВЕРШЕНА!                    ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  ✓ Бот установлен в /opt/telegramassistant               ║"
echo "║  ✓ Запущен как systemd сервис                            ║"
echo "║  ✓ Автозапуск при загрузке включён                       ║"
echo "║  ✓ Логирование настроено                                 ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Полезные команды:                                       ║"
echo "║  • telegramactl status     - Статус бота                 ║"
echo "║  • telegramactl logs       - Просмотр логов              ║"
echo "║  • telegramactl restart    - Перезапуск                  ║"
echo "║  • telegramactl update     - Обновление                  ║"
echo "║  • journalctl -u telegramassistant -f - Логи в реальном времени ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Проверка токена
if grep -q "BOT_TOKEN=.*:.*" "$BOT_DIR/.env" 2>/dev/null; then
    echo -e "${GREEN}✓ Токен бота настроен${NC}"
else
    echo -e "${RED}⚠️  Проверьте .env файл - токен может быть не указан!${NC}"
fi

# Проверка API ключа погоды
if grep -q "WEATHER_API_KEY=.\{16,\}" "$BOT_DIR/.env" 2>/dev/null; then
    echo -e "${GREEN}✓ API ключ погоды настроен${NC}"
else
    echo -e "${YELLOW}⊘ API ключ погоды не установлен (погода будет недоступна)${NC}"
    echo -e "${YELLOW}  Для настройки: sudo nano /opt/telegramassistant/.env${NC}"
fi

# Проверка ADMIN ID
if grep -q "ADMIN_ID=[0-9]\+" "$BOT_DIR/.env" 2>/dev/null; then
    echo -e "${GREEN}✓ Admin ID настроен${NC}"
    echo -e "${YELLOW}  Админ-панель доступна в настройках бота${NC}"
else
    echo -e "${YELLOW}⊘ Admin ID не установлен (админ-панель будет недоступна)${NC}"
    echo -e "${YELLOW}  Для настройки: sudo nano /opt/telegramassistant/.env${NC}"
fi

echo ""
echo -e "${YELLOW}📖 Документация: $BOT_DIR/README.md${NC}"
echo ""
echo -e "${GREEN}🎉 Отправьте /start вашему боту в Telegram для проверки!${NC}"
echo ""
