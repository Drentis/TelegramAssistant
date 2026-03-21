# 🚀 Установка на Сервер

Полная инструкция по развёртыванию Telegram бота TelegramAssistant.

---

## ⚡ Быстрый старт

### Linux сервер:

```bash
curl -sSL https://raw.githubusercontent.com/Drentis/TelegramAssistant/master/deploy.sh | sudo bash
```

**Или через wget:**
```bash
wget -qO- https://raw.githubusercontent.com/Drentis/TelegramAssistant/master/deploy.sh | sudo bash
```

---

### Windows:

```powershell
cd $HOME
git clone https://github.com/Drentis/TelegramAssistant.git
cd TelegramAssistant
.\install.ps1
```

---

## 🖥️ Локальная установка (без автозапуска)

### Шаг 1: Клонирование проекта

```bash
git clone https://github.com/Drentis/TelegramAssistant.git
cd TelegramAssistant
```

### Шаг 2: Создание виртуального окружения

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Шаг 3: Установка зависимостей

```bash
pip install -r requirements.txt
```

### Шаг 4: Настройка .env

Создай файл `.env` в корне проекта:

```env
# Токен бота (обязательно)
BOT_TOKEN=1234567890:AABBccDDeeFFggHHiiJJkkLLmmNNooP

# API ключ OpenWeatherMap (опционально)
WEATHER_API_KEY=abcd1234efgh5678ijkl9012mnop3456
```

### Шаг 5: Запуск бота

**Linux/Mac:**
```bash
python main.py
```

**Windows:**
```powershell
python main.py
```

### Запуск в фоновом режиме

**Linux (через systemd):**

Создай файл `/etc/systemd/system/telegramassistant.service`:

```ini
[Unit]
Description=TelegramAssistant Bot
After=network.target

[Service]
Type=simple
User=telegramassistant
WorkingDirectory=/opt/telegramassistant
ExecStart=/opt/telegramassistant/venv/bin/python /opt/telegramassistant/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Запусти:
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegramassistant
sudo systemctl start telegramassistant
```

**Windows (через планировщик):**

1. Открой **Планировщик заданий**
2. Создай задачу
3. Триггер: **При запуске**
4. Действие: `python.exe` с аргументом `C:\путь\к\TelegramAssistant\main.py`

---

## 📋 Что сделает скрипт установки:

1. ✅ Обновит систему
2. ✅ Установит Python 3 и все зависимости
3. ✅ Скачает бота из GitHub
4. ✅ Создаст виртуальное окружение
5. ✅ Установит все пакеты
6. ✅ **Запросит токен бота и API ключ** (интерактивно)
7. ✅ Настроит автозапуск (Linux через systemd)
8. ✅ Запустит бота
9. ✅ Создаст команду `telegramactl` для управления (Linux)

---

## 🎮 Управление ботом

### На Linux:

| Команда | Описание |
|---------|----------|
| `telegramactl start` | Запустить бота |
| `telegramactl stop` | Остановить бота |
| `telegramactl restart` | Перезапустить бота |
| `telegramactl status` | Показать статус |
| `telegramactl logs` | Логи в реальном времени |
| `telegramactl update` | Обновить из Git |

### На Windows:

| Действие | Команда |
|----------|---------|
| Запустить | Открой `start.bat` или `python main.py` |
| Остановить | `Ctrl+C` в окне консоли |
| Обновить | `git pull` + `pip install -r requirements.txt` |

---

## 📁 Структура после установки

### Linux:
```
/opt/telegramassistant/
├── main.py
├── database.py
├── config.py
├── requirements.txt
├── .env
├── venv/
└── notebook.db
```

### Windows:
```
C:\Users\ТвоёИмя\TelegramAssistant\
├── main.py
├── database.py
├── config.py
├── requirements.txt
├── .env
├── venv\
└── notebook.db
```

---

## 🛡️ Безопасность

- Бот работает от отдельного пользователя (Linux)
- Файл `.env` с правами `600` (только владелец читает)
- Автоматический перезапуск при ошибках
- Токены не хранятся в репозитории

---

## 🐛 Troubleshooting

### Бот не запускается на Linux

**Проверь логи:**
```bash
journalctl -u telegramassistant -n 50
```

**Возможные ошибки:**

1. **Invalid token** — проверь токен:
```bash
sudo nano /opt/telegramassistant/.env
telegramactl restart
```

2. **ModuleNotFoundError** — переустанови зависимости:
```bash
cd /opt/telegramassistant
source venv/bin/activate
pip install -r requirements.txt
telegramactl restart
```

### Бот не запускается на Windows

**Ошибка: python не найден**
```powershell
# Проверь установку
python --version

# Если не работает, переустанови Python
# https://www.python.org/downloads/
```

**Ошибка: ModuleNotFoundError**
```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Ошибка: .env не найден**

Создай файл `.env` в папке проекта:
```env
BOT_TOKEN=1234567890:AABBccDDeeFFggHHiiJJkkLLmmNNooP
WEATHER_API_KEY=
```

---

## 🔄 Обновление из GitHub

### На Linux:
```bash
telegramactl update
```

### На Windows:
```powershell
cd TelegramAssistant
git pull
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

---

## 💡 Советы

### Автозапуск на Windows

Создай файл `start.bat` (уже создан после установки):
```batch
@echo off
cd /d %~dp0
call venv\Scripts\activate
python main.py
pause
```

Или настрой задачу в **Планировщике заданий**:
1. Открой Планировщик заданий
2. Создай задачу
3. Триггер: **При запуске**
4. Действие: `python.exe` с аргументом `C:\путь\к\TelegramAssistant\main.py`

### Резервное копирование базы данных

```bash
# Linux
cp /opt/telegramassistant/notebook.db /backup/notebook_$(date +%Y%m%d).db

# Windows (PowerShell)
Copy-Item notebook.db "D:\Backup\notebook_$(Get-Date -Format 'yyyyMMdd').db"
```

---

## 📞 Поддержка

Если возникли проблемы:

1. Проверь логи: `telegramactl logs` (Linux) или смотри вывод в консоли (Windows)
2. Проверь статус: `telegramactl status` (Linux)
3. Проверь токен в `.env`: `cat /opt/telegramassistant/.env` или открой файл блокнотом
4. Перезапусти: `telegramactl restart` (Linux) или `Ctrl+C` → `python main.py` (Windows)

---

## 🎉 Готово!

После установки бот будет:
- ✅ Работать 24/7 (Linux с systemd)
- ✅ Автоматически перезапускаться при ошибках
- ✅ Запускаться при загрузке сервера (Linux)
- ✅ Вести логи всех событий

**Отправьте `/start` вашему боту в Telegram!**
