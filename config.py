"""
Модуль конфигурации TelegramAssistant.

Загружает переменные окружения из файла .env:
- BOT_TOKEN: токен бота (получить у @BotFather)
- WEATHER_API_KEY: API ключ OpenWeatherMap (https://openweathermap.org/api)
- ADMIN_ID: Telegram ID администратора (получить у @userinfobot)

Пример .env файла:
    BOT_TOKEN=1234567890:AABBccDDeeFFggHHiiJJkkLLmmNNooP
    WEATHER_API_KEY=abcd1234efgh5678ijkl9012mnop3456
    ADMIN_ID=123456789
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

# Токен бота для доступа к Telegram Bot API
BOT_TOKEN = os.getenv("BOT_TOKEN")

# API ключ для сервиса OpenWeatherMap (используется для прогноза погоды)
# Получить ключ можно на https://openweathermap.org/api
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# Telegram ID администратора бота
# Получить можно через бота @userinfobot или @getmyid_bot
ADMIN_ID = os.getenv("ADMIN_ID")
