# ⚡ Быстрый старт

## 🚀 Установка в одну команду

### На Linux сервере:

```bash
curl -sSL https://raw.githubusercontent.com/Drentis/TelegramAssistant/main/deploy.sh | sudo bash
```

**Или через wget:**
```bash
wget -qO- https://raw.githubusercontent.com/Drentis/TelegramAssistant/main/deploy.sh | sudo bash
```

---

### На Windows:

Открой PowerShell и выполни:

```powershell
powershell -ExecutionPolicy Bypass -File (New-Object Net.WebClient).DownloadString('https://raw.githubusercontent.com/Drentis/TelegramAssistant/main/install.ps1') | iex
```

**Или скачай и запусти вручную:**
1. Скачай `install.ps1` из репозитория
2. Кликни правой кнопкой → **Запустить от имени администратора**
3. Следуй инструкциям

---

## 📋 Что сделает скрипт:

| Шаг | Действие |
|-----|----------|
| 1 | Проверка/установка зависимостей |
| 2 | Загрузка файлов бота из GitHub |
| 3 | Настройка виртуального окружения |
| 4 | Установка зависимостей Python |
| 5 | **Запрос токена и API ключа** 🔑 |
| 6 | Создание файла запуска |

---

## 🔑 Ввод токенов

Скрипт запросит:

### 1. Токен бота
- Получите у [@BotFather](https://t.me/BotFather)
- Отправьте `/newbot`
- Введите полученный токен

### 2. API ключ погоды (опционально)
- Получите на [OpenWeatherMap](https://openweathermap.org/api)
- Или нажмите **Enter** для пропуска

---

## ✅ Проверка работы

### На Linux:
```bash
telegramactl status
```

### На Windows:
- Открой `start.bat` в папке проекта
- Или в PowerShell: `python main.py`

Если бот активен — откройте Telegram и отправьте `/start` вашему боту!

---

## 🎮 Управление

### На Linux:
```bash
telegramactl start      # Запустить
telegramactl stop       # Остановить
telegramactl restart    # Перезапустить
telegramactl logs       # Логи
telegramactl update     # Обновить из GitHub
telegramactl status     # Статус
```

### На Windows:
- **Запуск:** открой `start.bat`
- **Остановка:** `Ctrl+C` в окне консоли
- **Обновление:** `git pull` + `pip install -r requirements.txt`

---

## 📖 Полная документация

[INSTALL.md](INSTALL.md)

---

## 🎉 Готово!

Бот работает и готов к использованию!

- ✅ На Linux: работает 24/7 в фоне
- ✅ На Windows: работает в окне консоли
- ✅ Автозапуск при загрузке (настраивается)
