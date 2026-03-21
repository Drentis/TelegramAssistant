#!/bin/bash

# ============================================================
# Скрипт быстрого развёртывания TelegramAssistant с GitHub
# ============================================================
# Использование:
#   curl -sSL https://raw.githubusercontent.com/Drentis/TelegramAssistant/main/deploy.sh | sudo bash
# Или:
#   wget -qO- https://raw.githubusercontent.com/Drentis/TelegramAssistant/main/deploy.sh | sudo bash
# ============================================================

set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Логотип
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   TelegramAssistant - Быстрое развёртывание              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Проверка прав root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Пожалуйста, запустите от root (sudo ...)${NC}"
    exit 1
fi

# URL репозитория (можно передать как аргумент)
DEFAULT_REPO="https://github.com/Drentis/TelegramAssistant.git"
REPO_URL="${1:-$DEFAULT_REPO}"
BRANCH="${2:-main}"

echo -e "\n${YELLOW}📦 Репозиторий: $REPO_URL${NC}"
echo -e "${YELLOW}📦 Ветка: $BRANCH${NC}"

# ============================================================
# Обновление системы
# ============================================================
echo -e "\n${MAGENTA}[1/8] Обновление пакетов...${NC}"
apt update -qq && apt upgrade -y -qq

# ============================================================
# Установка зависимостей
# ============================================================
echo -e "\n${MAGENTA}[2/8] Установка зависимостей...${NC}"
apt install -y -qq python3 python3-pip python3-venv git curl

# ============================================================
# Создание пользователя и директории
# ============================================================
BOT_USER="telegramassistant"
BOT_DIR="/opt/telegramassistant"

echo -e "\n${MAGENTA}[3/8] Создание пользователя и директории...${NC}"

if ! id "$BOT_USER" &>/dev/null; then
    useradd -r -s /bin/false -d "$BOT_DIR" "$BOT_USER"
    echo -e "${GREEN}   ✓ Пользователь $BOT_USER создан${NC}"
else
    echo -e "${GREEN}   ✓ Пользователь $BOT_USER уже существует${NC}"
fi

mkdir -p "$BOT_DIR"
chown "$BOT_USER:$BOT_USER" "$BOT_DIR"
echo -e "${GREEN}   ✓ Директория $BOT_DIR создана${NC}"

# ============================================================
# Клонирование репозитория
# ============================================================
echo -e "\n${MAGENTA}[4/8] Загрузка файлов бота...${NC}"
cd "$BOT_DIR"

if [ -d ".git" ]; then
    echo -e "${YELLOW}   Репозиторий уже существует, делаем pull...${NC}"
    su -s /bin/bash "$BOT_USER" -c "git pull origin $BRANCH 2>/dev/null" || true
else
    echo -e "${YELLOW}   Клонирование репозитория...${NC}"
    su -s /bin/bash "$BOT_USER" -c "git clone $REPO_URL . 2>/dev/null" || {
        echo -e "${RED}   ❌ Не удалось клонировать репозиторий${NC}"
        echo -e "${YELLOW}   Проверьте URL репозитория${NC}"
        exit 1
    }
    su -s /bin/bash "$BOT_USER" -c "git checkout $BRANCH 2>/dev/null" || true
    echo -e "${GREEN}   ✓ Репозиторий клонирован${NC}"
fi

# ============================================================
# Настройка виртуального окружения
# ============================================================
echo -e "\n${MAGENTA}[5/8] Настройка виртуального окружения...${NC}"
su -s /bin/bash "$BOT_USER" -c "python3 -m venv venv"
echo -e "${GREEN}   ✓ Виртуальное окружение создано${NC}"

echo -e "\n${YELLOW}   Установка зависимостей Python...${NC}"
su -s /bin/bash "$BOT_USER" -c "$BOT_DIR/venv/bin/pip install --upgrade pip -q"
su -s /bin/bash "$BOT_USER" -c "$BOT_DIR/venv/bin/pip install -r $BOT_DIR/requirements.txt -q"
echo -e "${GREEN}   ✓ Зависимости установлены${NC}"

# ============================================================
# Настройка .env файла с интерактивным вводом
# ============================================================
echo -e "\n${MAGENTA}[6/8] Настройка токенов${NC}"

# Заголовок
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              НАСТРОЙКА TELEGRAM BOT TOKEN                ║${NC}"
echo -e "${BLUE}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║  1. Откройте Telegram и найдите @BotFather               ║${NC}"
echo -e "${BLUE}║  2. Отправьте команду /newbot                            ║${NC}"
echo -e "${BLUE}║  3. Придумайте имя бота (например: MyNotebookBot)        ║${NC}"
echo -e "${BLUE}║  4. Придумайте username (например: my_notebook_bot)      ║${NC}"
echo -e "${BLUE}║  5. Скопируйте полученный токен                          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Ввод токена бота (обычный ввод, не скрытый)
while true; do
    echo -en "${YELLOW}   Введите токен бота: ${NC}"
    read BOT_TOKEN_INPUT
    
    if [[ "$BOT_TOKEN_INPUT" == *":"* ]]; then
        echo -e "${GREEN}   ✓ Токен принят${NC}"
        break
    else
        echo -e "${RED}   ❌ Неверный формат! Токен должен содержать ':'${NC}"
        echo -e "${YELLOW}   Попробуйте ещё раз${NC}"
    fi
done

# Заголовок для API ключа
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           НАСТРОЙКА OPENWEATHERMAP API KEY               ║${NC}"
echo -e "${BLUE}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║  API ключ для прогноза погоды (ОПЦИОНАЛЬНО)              ║${NC}"
echo -e "${BLUE}║  • Получить на https://openweathermap.org/api            ║${NC}"
echo -e "${BLUE}║  • Или нажмите Enter для пропуска                        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Ввод API ключа
while true; do
    echo -en "${YELLOW}   Введите API ключ погоды (или нажмите Enter для пропуска): ${NC}"
    read WEATHER_KEY_INPUT

    if [[ -z "$WEATHER_KEY_INPUT" ]]; then
        echo -e "${YELLOW}   ⊘ Пропущено (погода будет недоступна)${NC}"
        break
    elif [[ ${#WEATHER_KEY_INPUT} -ge 16 ]]; then
        echo -e "${GREEN}   ✓ API ключ принят${NC}"
        break
    else
        echo -e "${RED}   ❌ Слишком короткий ключ!${NC}"
        echo -e "${YELLOW}   Попробуйте ещё раз или нажмите Enter для пропуска${NC}"
    fi
done

# Ввод ADMIN ID
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
    echo -en "${YELLOW}   Введите Telegram ID администратора (или Enter для пропуска): ${NC}"
    read ADMIN_ID_INPUT

    if [[ -z "$ADMIN_ID_INPUT" ]]; then
        echo -e "${YELLOW}   ⊘ Пропущено (админ-панель будет недоступна)${NC}"
        break
    elif [[ "$ADMIN_ID_INPUT" =~ ^[0-9]+$ ]]; then
        echo -e "${GREEN}   ✓ Admin ID принят${NC}"
        break
    else
        echo -e "${RED}   ❌ Неверный формат! ID должен быть числом${NC}"
        echo -e "${YELLOW}   Попробуйте ещё раз или нажмите Enter для пропуска${NC}"
    fi
done

# Ввод GitHub токена
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           НАСТРОЙКА GITHUB TOKEN                         ║${NC}"
echo -e "${BLUE}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║  Токен для обновления бота через Telegram (можно         ║${NC}"
echo -e "${BLUE}║  пропустить)                                             ║${NC}"
echo -e "${BLUE}║  Создать: https://github.com/settings/tokens             ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

while true; do
    echo -en "${YELLOW}   Введите GitHub токен (или Enter для пропуска): ${NC}"
    read GITHUB_TOKEN_INPUT

    if [[ -z "$GITHUB_TOKEN_INPUT" ]]; then
        echo -e "${YELLOW}   ⊘ Пропущено (обновление через Telegram будет недоступно)${NC}"
        break
    elif [[ "$GITHUB_TOKEN_INPUT" == ghp_* ]] || [[ ${#GITHUB_TOKEN_INPUT} -ge 30 ]]; then
        echo -e "${GREEN}   ✓ GitHub токен принят${NC}"
        break
    else
        echo -e "${RED}   ❌ Неверный формат! Токен должен начинаться с 'ghp_'${NC}"
        echo -e "${YELLOW}   Попробуйте ещё раз или нажмите Enter для пропуска${NC}"
    fi
done

# Создание .env файла
echo -e "\n${YELLOW}   Создание файла .env...${NC}"

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
chmod 600 "$BOT_DIR/.env"
echo -e "${GREEN}   ✓ Файл .env создан${NC}"

# ============================================================
# Создание systemd сервиса
# ============================================================
echo -e "\n${MAGENTA}[7/8] Настройка автозапуска...${NC}"

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

echo -e "${GREEN}   ✓ systemd сервис создан${NC}"

# ============================================================
# Запуск сервиса
# ============================================================
echo -e "\n${MAGENTA}[8/8] Запуск бота...${NC}"
systemctl daemon-reload
systemctl enable telegramassistant -q
systemctl start telegramassistant

sleep 2

# ============================================================
# Проверка статуса
# ============================================================
if systemctl is-active --quiet telegramassistant; then
    echo -e "${GREEN}   ✓ Бот успешно запущен!${NC}"
else
    echo -e "${RED}   ⚠ Бот запущен, но есть предупреждения${NC}"
    echo -e "${YELLOW}   Проверьте логи: journalctl -u telegramassistant -n 20${NC}"
fi

# ============================================================
# Скрипт управления
# ============================================================
cat > /usr/local/bin/telegramactl << 'EOF'
#!/bin/bash
ENV_FILE="/opt/telegramassistant/.env"

case "$1" in
    start) systemctl start telegramassistant ;;
    stop) systemctl stop telegramassistant ;;
    restart) systemctl restart telegramassistant ;;
    status) systemctl status telegramassistant ;;
    logs) journalctl -u telegramassistant -f ;;
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
        
        /opt/telegramassistant/venv/bin/pip install -r requirements.txt -q
        chown -R telegramassistant:telegramassistant /opt/telegramassistant
        systemctl start telegramassistant
        echo "✓ Обновлено!"
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
                read -p "Введите новый API ключ погоды: " new_key
                sed -i "s/^WEATHER_API_KEY=.*/WEATHER_API_KEY=$new_key/" "$ENV_FILE"
                echo "✓ API ключ погоды обновлён"
                systemctl restart telegramassistant
                ;;
            3)
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
            0) echo "Выход" ;;
            *) echo "❌ Неверный номер" ;;
        esac
        ;;
    delete)
        echo "⚠️  УДАЛЕНИЕ БОТА"
        echo ""
        echo "Это действие удалит:"
        echo "  • Все данные пользователей"
        echo "  • Все настройки бота"
        echo "  • Системный сервис"
        echo "  • Файлы бота"
        echo "  • Пользователя telegramassistant"
        echo "  • Команду telegramactl"
        echo ""
        echo "⚠️  ВНИМАНИЕ: Это действие НЕОБРАТИМО!"
        echo ""
        read -p "Вы уверены? Введите 'yes' для подтверждения: " confirm
        if [ "$confirm" = "yes" ]; then
            echo ""
            echo "🔄 Остановка бота..."
            systemctl stop telegramassistant 2>/dev/null || true
            systemctl disable telegramassistant 2>/dev/null || true
            
            echo "🗑 Удаление сервиса..."
            rm -f /etc/systemd/system/telegramassistant.service
            systemctl daemon-reload
            
            # Удаляем логи
            echo "🗑 Удаление логов..."
            journalctl --rotate 2>/dev/null || true
            rm -f /var/log/journal/*telegramassistant* 2>/dev/null || true
            
            echo "🗑 Удаление файлов бота..."
            rm -rf /opt/telegramassistant
            
            echo "🗑 Удаление пользователя..."
            userdel -r telegramassistant 2>/dev/null || true
            
            echo "🗑 Удаление команды telegramactl..."
            rm -f /usr/local/bin/telegramactl
            
            echo ""
            echo "✓ Бот полностью удалён"
            echo ""
            echo "Для повторной установки выполните:"
            echo "  curl -sSL https://raw.githubusercontent.com/Drentis/TelegramAssistant/main/deploy.sh | sudo bash"
        else
            echo "❌ Удаление отменено"
        fi
        ;;
    version) echo "TelegramAssistant v1.0.2" ;;
    *) echo "Использование: $0 {start|stop|restart|status|logs|update|edit|delete|version}" ;;
esac
EOF

chmod +x /usr/local/bin/telegramactl

# ============================================================
# Финальное сообщение
# ============================================================
echo -e "\n${GREEN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                  ✅ УСТАНОВКА ЗАВЕРШЕНА!                 ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  ✓ Бот установлен в /opt/telegramassistant               ║"
echo "║  ✓ Запущен как systemd сервис                            ║"
echo "║  ✓ Автозапуск при загрузке включён                       ║"
echo "║  ✓ Логирование настроено                                 ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Команды управления:                                     ║"
echo "║  • telegramactl status    - Статус                       ║"
echo "║  • telegramactl logs      - Логи в реальном времени      ║"
echo "║  • telegramactl restart   - Перезапуск                   ║"
echo "║  • telegramactl update    - Обновить из git              ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Проверка работы:                                        ║"
echo "║  1. Откройте Telegram                                    ║"
echo "║  2. Найдите вашего бота по username                      ║"
echo "║  3. Отправьте /start                                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Проверка конфигурации
if grep -q "BOT_TOKEN=.*:.*" "$BOT_DIR/.env" 2>/dev/null; then
    echo -e "${GREEN}✓ Токен бота настроен${NC}"
fi

if grep -q "WEATHER_API_KEY=.\{16,\}" "$BOT_DIR/.env" 2>/dev/null; then
    echo -e "${GREEN}✓ API ключ погоды настроен${NC}"
else
    echo -e "${YELLOW}⊘ API ключ погоды не установлен (погода будет недоступна)${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Отправьте /start вашему боту в Telegram!${NC}"
echo ""
