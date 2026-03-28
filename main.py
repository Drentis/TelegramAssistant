"""
TelegramAssistant - Бот для ведения списков и заметок.

Этот бот помогает управлять:
- Списком покупок с автоматической классификацией по магазинам
- Списком дел с напоминаниями и датами
- Учебными задачами
- Идеями и заметками
- Рецептами с ингредиентами
- Прогнозом погоды

Основные возможности:
- Автоматическая классификация товаров (Магнит/Фикспрайс/Другое)
- Напоминания о делах (ежедневно в 9:00)
- Прогноз погоды и уведомления о дожде
- Гибкие настройки (триггеры, видимость кнопок, названия магазинов)

Версия: 1.0.10
"""

# Версия бота
BOT_VERSION = "1.0.10"

import asyncio
import subprocess
import re
import aiohttp
from datetime import datetime, date, timedelta
from typing import Optional
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, WEATHER_API_KEY, ADMIN_ID
import database as db


# ============================================================
# === ПРОВЕРКА ПРАВ (Admin Check)
# ============================================================

def is_admin(user_id: int) -> bool:
    """
    Проверить, является ли пользователь администратором.
    
    Args:
        user_id: Telegram ID пользователя
        
    Returns:
        bool: True если пользователь администратор
    """
    if not ADMIN_ID:
        return False
    return str(user_id) == str(ADMIN_ID)


# ============================================================
# === КЛАВИАТУРЫ (Keyboards)
# ============================================================

def get_main_keyboard(settings: dict = None):
    """
    Создать главное меню с кнопками с учётом настроек видимости.

    Args:
        settings: Настройки пользователя (если None, все кнопки показываются)

    Returns:
        ReplyKeyboardMarkup: Клавиатура для главного меню

    Примечание:
        Кнопки показываются только если соответствующие visibility_* = 1
    """
    keyboard_buttons = []

    # Добавляем кнопки только если они включены
    if settings is None or settings.get('visibility_shopping', 1):
        keyboard_buttons.append([KeyboardButton(text="🛒 Список покупок")])

    if settings is None or settings.get('visibility_todo', 1):
        keyboard_buttons.append([KeyboardButton(text="📋 Список дел")])

    if settings is None or settings.get('visibility_study', 1):
        keyboard_buttons.append([KeyboardButton(text="📚 Учёба")])

    if settings is None or settings.get('visibility_ideas', 1):
        keyboard_buttons.append([KeyboardButton(text="💡 Идеи")])

    if settings is None or settings.get('visibility_recipes', 1):
        keyboard_buttons.append([KeyboardButton(text="🍳 Рецепты")])

    if settings is None or settings.get('visibility_info', 1):
        keyboard_buttons.append([KeyboardButton(text="ℹ️ Инфо")])

    # Кнопка погоды (показывается только если включена)
    if settings is None or settings.get('weather_button', 1):
        keyboard_buttons.append([KeyboardButton(text="🌤 Погода")])

    keyboard_buttons.append([KeyboardButton(text="⚙️ Настройки")])

    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True
    )
    return keyboard


def get_shopping_categories_keyboard():
    """
    Создать клавиатуру с категориями списка покупок.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками магазинов
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🥕 Магнит (Продукты)", callback_data="shopping_magnit")],
            [InlineKeyboardButton(text="🏠 Фикспрайс (Бытовое)", callback_data="shopping_fixprice")],
            [InlineKeyboardButton(text="📦 Другое", callback_data="shopping_other")]
        ]
    )
    return keyboard


def get_item_actions_keyboard(category: str, item_id: int):
    """
    Создать клавиатуру действий с товаром (удаление).

    Args:
        category: Категория товара (magnit, fixprice, other)
        item_id: ID товара в базе данных

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой удаления
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_item_{category}_{item_id}")]
        ]
    )
    return keyboard


def get_list_actions_keyboard(list_type: str):
    """
    Создать клавиатуру действий со списком (очистка).

    Args:
        list_type: Тип списка (shopping, todo, study, ideas)

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой очистки
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Очистить список", callback_data=f"clear_{list_type}")]
        ]
    )
    return keyboard


def get_items_keyboard(items: list, list_type: str, category: str = None):
    """
    Создать клавиатуру для просмотра списка элементов.

    Args:
        items: Список элементов (не используется, оставлено для совместимости)
        list_type: Тип списка (shopping, todo, study, ideas)
        category: Категория для shopping (magnit, fixprice, other)

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой редактирования и "Назад"
    """
    buttons = [
        [InlineKeyboardButton(text="✏️ Редактировать список", callback_data=f"edit_{list_type}_{category if category else ''}")]
    ]
    # Добавляем кнопку "Назад" в зависимости от типа списка
    if list_type == "shopping":
        buttons.append([InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="back_to_shopping")])
    elif list_type == "ideas":
        buttons.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main")])
    else:
        buttons.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_edit_keyboard(items: list, list_type: str, category: str = None):
    """
    Создать клавиатуру для редактирования списка.

    Args:
        items: Список элементов для отображения
        list_type: Тип списка (shopping, todo, study, ideas)
        category: Категория для shopping (magnit, fixprice, other)

    Returns:
        InlineKeyboardMarkup: Клавиатура с элементами для управления

    Примечание:
        - Для shopping: показывает ✅ (взято) / ❌ (не взято) + удаление
        - Для todo/study/ideas: показывает только удаление
        - Текст задач обрезается до 30 символов
    """
    buttons = []
    for item in items:
        item_id = item['id']
        # Получаем текст и статус в зависимости от типа списка
        if list_type == "shopping":
            item_text = item['item']
            taken = item['taken']
            # Если товар не взят - зелёная галочка, если взят - красная
            if taken:
                buttons.append([
                    InlineKeyboardButton(
                        text=f"❌ {item_text}",
                        callback_data=f"toggle_{list_type}_{category if category else ''}_{item_id}"
                    ),
                    InlineKeyboardButton(
                        text="🗑",
                        callback_data=f"delete_{list_type}_{category if category else ''}_{item_id}"
                    )
                ])
            else:
                # Товар не взят - зелёная галочка
                buttons.append([InlineKeyboardButton(
                    text=f"✅ {item_text}",
                    callback_data=f"toggle_{list_type}_{category if category else ''}_{item_id}"
                )])
        else:
            # Для todo, study и ideas
            item_text = item['task'] if 'task' in item else item['idea']
            # Обрезаем текст до 30 символов
            if len(item_text) > 30:
                item_text = item_text[:27] + "..."
            buttons.append([InlineKeyboardButton(
                text=f"🗑 {item_text}",
                callback_data=f"delete_{list_type}_{category if category else ''}_{item_id}"
            )])

    buttons.append([InlineKeyboardButton(text="🗑 Очистить весь список", callback_data=f"clear_{list_type}_{category if category else ''}")])

    # Кнопка "Назад" или "Готово"
    if list_type == "shopping":
        buttons.append([InlineKeyboardButton(text="✅ Готово", callback_data=f"back_edit_{list_type}_{category if category else ''}")])
    else:
        buttons.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_back_keyboard():
    """
    Создать клавиатуру с кнопкой "Назад".

    Returns:
        InlineKeyboardMarkup: Клавиатура с одной кнопкой "Назад"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ]
    )
    return keyboard


# ============================================================
# === КЛАССИФИКАЦИЯ ТОВАРОВ (Product Classification)
# ============================================================

# Ключевые слова для классификации товаров по категориям
# Товары с этими словами будут добавляться в категорию "Магнит" (Продукты)
PRODUCT_KEYWORDS = [
    "еда", "продукт", "молоко", "хлеб", "сыр", "колбаса", "мясо", "рыба",
    "овощ", "фрукт", "яблоко", "банан", "картофель", "морковь", "лук",
    "напиток", "вода", "сок", "чай", "кофе", "пиво", "вино",
    "сахар", "соль", "масло", "яйцо", "творог", "кефир", "йогурт",
    "печень", "торт", "конфет", "шоколад", "морожен", "булка", "батон",
    "круп", "рис", "греч", "макарон", "мука", "дрожж",
    "консерв", "тушён", "горошек", "кукуруз", "томат", "паст",
    "снек", "чипс", "сухар", "орех", "семеч",
    "детск", "пюре", "каш", "смес",
    "корм", "лакомств"
]

# Ключевые слова для классификации товаров по категории "Фикспрайс" (Бытовое)
HOUSEHOLD_KEYWORDS = [
    "быт", "шампунь", "мыло", "гель", "порошок", "стир", "полоск",
    "убор", "тряп", "губк", "щётк", "веник", "швабр", "пылес",
    "туалет", "бумаг", "салфет", "полотенц", "платок",
    "посуд", "губк", "моющ", "средств", "чистящ",
    "космет", "крем", "лосьон", "маск", "скраб",
    "зуб", "паст", "щёток", "нит",
    "бритв", "лезв", "пен",
    "дезодор", "антиперспир",
    "парфюм", "дух", "туалетн",
    "лампоч", "батарей", "аккумулятор",
    "клей", "скотч", "изолент",
    "ножниц", "нож", "игл", "нитк",
    "канц", "руч", "карандаш", "тетрад", "блокнот", "папк",
    "игруш", "игра", "настол", "пазл",
    "декор", "свеч", "ваз", "рам",
    "посуд", "тарел", "чаш", "ложк", "вилк", "нож", "кастрюл", "сковород", "бокал", "кружк"
]


def classify_item(item_text: str) -> str:
    """
    Классифицировать товар по категориям на основе ключевых слов.

    Args:
        item_text: Название товара

    Returns:
        str: Категория ("magnit", "fixprice", "other")

    Алгоритм:
        1. Проверяем наличие ключевых слов продуктов → magnit
        2. Проверяем наличие ключевых слов бытовых товаров → fixprice
        3. Если не найдено совпадений → other
    """
    text_lower = item_text.lower()

    for keyword in PRODUCT_KEYWORDS:
        if keyword in text_lower:
            return "magnit"

    for keyword in HOUSEHOLD_KEYWORDS:
        if keyword in text_lower:
            return "fixprice"

    return "other"


# ============================================================
# === ПАРСИНГ ДАТЫ (Date Parsing)
# ============================================================

def parse_date_from_text(text: str) -> tuple[str, Optional[date]]:
    """
    Извлечь дату из текста задачи.

    Args:
        text: Текст задачи (например, "сделать уборку завтра" или "проект 15.03")

    Returns:
        tuple[str, Optional[date]]: (очищенный текст, дата или None)

    Распознаваемые форматы:
        - "завтра", "послезавтра", "сегодня"
        - "12.03", "12.03.2024" (DD.MM, DD.MM.YYYY)
        - "12 марта", "12-го марта" (DD месяц)
        - "на 12.03", "на завтра" (с предлогом "на")

    Примечание:
        Если дата в прошлом для текущего года, предполагается следующий год.
    """
    today = date.today()

    # Паттерны для даты
    patterns = [
        # "завтра"
        (r'\bзавтра\b', lambda: today + timedelta(days=1)),
        # "послезавтра"
        (r'\bпослезавтра\b', lambda: today + timedelta(days=2)),
        # "сегодня"
        (r'\bсегодня\b', lambda: today),
        # "на 12.03" или "12.03"
        (r'(?:на\s*)?(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?', lambda m=None: None),
        # "12 марта", "12-го марта"
        (r'(?:на\s*)?(\d{1,2})(?:-?го)?\s+(январ[яь]|феврал[яь]|март[аь]|апрел[яь]|мая|июн[яь]|июл[яь]|август[аь]|сентябр[яь]|октябр[яь]|ноябр[яь]|декабр[яь])', lambda m=None: None),
    ]

    # Словарь для преобразования названий месяцев в номера
    months = {
        'январ': 1, 'феврал': 2, 'март': 3, 'апрел': 4, 'май': 5, 'мая': 5,
        'июн': 6, 'июл': 7, 'август': 8, 'сентябр': 9, 'октябр': 10,
        'ноябр': 11, 'декабр': 12
    }

    due_date = None
    cleaned_text = text

    # Проверка на "завтра", "послезавтра", "сегодня"
    for pattern, date_func in patterns[:3]:
        match = re.search(pattern, cleaned_text, re.IGNORECASE)
        if match:
            due_date = date_func()
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
            break

    # Проверка на дату в формате DD.MM
    if not due_date:
        match = re.search(r'(?:на\s*)?(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?', cleaned_text)
        if match:
            day, month, year = match.groups()
            day, month = int(day), int(month)
            year = int(year) if year else today.year
            if year < 100:
                year = 2000 + year
            try:
                due_date = date(year, month, day)
                cleaned_text = cleaned_text.replace(match.group(0), '').strip()
            except ValueError:
                pass

    # Проверка на дату в формате "DD месяца"
    if not due_date:
        match = re.search(r'(?:на\s*)?(\d{1,2})(?:-?го)?\s+(январ[яь]|феврал[яь]|март[аь]|апрел[яь]|мая|июн[яь]|июл[яь]|август[аь]|сентябр[яь]|октябр[яь]|ноябр[яь]|декабр[яь])', cleaned_text, re.IGNORECASE)
        if match:
            day, month_name = match.groups()
            day = int(day)
            month = months.get(month_name[:6])
            if month:
                try:
                    due_date = date(today.year, month, day)
                    if due_date < today:
                        due_date = date(today.year + 1, month, day)
                    cleaned_text = cleaned_text.replace(match.group(0), '').strip()
                except ValueError:
                    pass

    # Очистка от лишних пробелов
    cleaned_text = ' '.join(cleaned_text.split())

    return cleaned_text, due_date


# === FSM состояния ===
class SettingsState(StatesGroup):
    choosing_category = State()
    editing_name = State()
    editing_short = State()


class RecipeState(StatesGroup):
    adding_recipe = State()
    adding_description = State()


# ============================================================
# === FSM СОСТОЯНИЯ (Finite State Machine)
# ============================================================

class SettingsState(StatesGroup):
    """
    Состояния для настройки категорий пользователя.

    Состояния:
        - choosing_category: выбор категории для настройки
        - editing_name: редактирование названия
        - editing_short: редактирование сокращения
    """
    choosing_category = State()
    editing_name = State()
    editing_short = State()


class RecipeState(StatesGroup):
    """
    Состояния для добавления рецепта.

    Состояния:
        - adding_recipe: добавление названия и ингредиентов
        - adding_description: добавление описания/инструкции
    """
    adding_recipe = State()
    adding_description = State()


class TodoState(StatesGroup):
    """
    Состояния для списка дел.

    Состояния:
        - waiting_for_task: ожидание ввода задачи
    """
    waiting_for_task = State()


class WeatherState(StatesGroup):
    """
    Состояния для настройки погоды.

    Состояния:
        - setting_city: установка города
        - setting_time: установка времени отправки
    """
    setting_city = State()
    setting_time = State()


# ============================================================
# === ХЕНДЛЕРЫ (Handlers)
# ============================================================

async def cmd_start(message: types.Message):
    """
    Обработчик команды /start.

    Отправляет приветственное сообщение с информацией о триггерных словах
    и показывает главное меню.

    Args:
        message: Сообщение от пользователя
    """
    settings = await db.get_category_settings(message.from_user.id)

    buy = settings.get('buy_trigger', 'купить')
    todo = settings.get('todo_trigger', 'сделать')
    study = settings.get('study_trigger', 'учёба')
    ideas = settings.get('ideas_trigger', 'идея')
    recipes = settings.get('recipes_trigger', 'рецепт')

    await message.answer(
        f"👋 Привет! Я ваш личный помощник для заметок и списков.\n\n"
        f"🛒 Покупки — `{buy}` (товары сами распределяются по магазинам)\n"
        f"📋 Дела — `{todo}` (задачи с датами и напоминаниями)\n"
        f"📚 Учёба — `{study}` (учебные задачи)\n"
        f"💡 Идеи — `{ideas}` (быстрые заметки)\n"
        f"🍳 Рецепты — `{recipes}` (рецепты с ингредиентами)\n\n"
        "⚙️ Настройки — настройте всё под себя\n"
        "ℹ️ Инфо — подробная справка\n\n"
        "💡 Лишние кнопки можно отключить в настройках\n\n"
        "Выберите раздел:",
        reply_markup=get_main_keyboard(settings),
        parse_mode="Markdown"
    )


async def cmd_version(message: types.Message):
    """
    Обработчик команды /version.

    Показывает текущую версию бота.

    Args:
        message: Сообщение от пользователя
    """
    await message.answer(
        f"🤖 **TelegramAssistant**\n\n"
        f"📦 Версия: `{BOT_VERSION}`\n\n"
        f"📝 [Changelog](https://github.com/Drentis/TelegramAssistant/blob/master/CHANGELOG.md)\n"
        f"📖 [GitHub](https://github.com/Drentis/TelegramAssistant)",
        parse_mode="Markdown"
    )


async def cmd_update(message: types.Message):
    """
    Обработчик команды /update для администратора.

    Обновляет бота из GitHub через Telegram.

    Args:
        message: Сообщение от пользователя
    """
    # Проверяем права админа
    if not is_admin(message.from_user.id):
        await message.answer("❌ Эта команда доступна только администратору.")
        return

    import subprocess
    import os
    import sys

    # Определяем директорию бота (где лежит main.py)
    bot_dir = os.path.dirname(os.path.abspath(__file__))

    # Определяем путь к pip в виртуальном окружении (кроссплатформенно)
    if sys.platform == 'win32':
        pip_path = os.path.join(bot_dir, 'venv', 'Scripts', 'pip.exe')
    else:
        pip_path = os.path.join(bot_dir, 'venv', 'bin', 'pip')

    await message.answer("🔄 **Проверка обновлений...**\n\nПодождите, это может занять несколько минут.", parse_mode="Markdown")

    try:
        # Проверяем, есть ли .git директория
        git_dir = os.path.join(bot_dir, '.git')

        if not os.path.exists(git_dir):
            # Если нет .git, инициализируем git и добавляем remote
            await message.answer("⚙️ **Первичная настройка git...**\n\nЭто займёт несколько секунд.", parse_mode="Markdown")

            # Инициализируем git
            subprocess.run(['git', 'init'], cwd=bot_dir, capture_output=True, check=True)

            # Добавляем remote (публичный репозиторий)
            remote_url = "https://github.com/Drentis/TelegramAssistant.git"

            subprocess.run(['git', 'remote', 'add', 'origin', remote_url], cwd=bot_dir, capture_output=True, check=True)
            subprocess.run(['git', 'fetch', 'origin'], cwd=bot_dir, capture_output=True, timeout=30, check=True)
            subprocess.run(['git', 'checkout', '-f', 'main'], cwd=bot_dir, capture_output=True, check=True)
            subprocess.run(['git', 'reset', '--hard', 'origin/main'], cwd=bot_dir, capture_output=True, timeout=30, check=True)

            result_stdout = "✓ Репозиторий инициализирован\n✓ Файлы обновлены"
            result_stderr = ""
        else:
            # Выполняем git pull
            result = subprocess.run(
                ['git', 'pull'],
                cwd=bot_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            result_stdout = result.stdout
            result_stderr = result.stderr

        # Проверяем результат
        if result_stderr and 'error' in result_stderr.lower():
            await message.answer(f"❌ **Ошибка обновления:**\n```{result_stderr[:1000]}```", parse_mode="Markdown")
        else:
            # Устанавливаем зависимости
            subprocess.run(
                [pip_path, 'install', '-r', os.path.join(bot_dir, 'requirements.txt')],
                capture_output=True,
                timeout=120
            )

            await message.answer(
                "✅ **Бот обновлён!**\n\n"
                "Обновления применены. Для применения некоторых изменений может потребоваться перезапуск бота.\n\n"
                f"📝 **Что изменилось:**\n```{result_stdout[:1000] if result_stdout else 'Файлы загружены'}```",
                parse_mode="Markdown"
            )

    except subprocess.TimeoutExpired:
        await message.answer("❌ **Превышено время ожидания.**\n\nПроверьте подключение к интернету и попробуйте ещё раз.", parse_mode="Markdown")
    except subprocess.CalledProcessError as e:
        await message.answer(f"❌ **Ошибка выполнения команды:**\n```\n{e.stderr[:1000] if e.stderr else str(e)}\n```", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ **Произошла ошибка:**\n```{str(e)}```", parse_mode="Markdown")


async def cmd_delete(message: types.Message):
    """
    Обработчик команды /delete для администратора.

    Полностью удаляет бота: базу данных, файлы и git-директорию.

    Args:
        message: Сообщение от пользователя
    """
    # Проверяем права админа
    if not is_admin(message.from_user.id):
        await message.answer("❌ Эта команда доступна только администратору.")
        return

    import os
    import shutil

    # Определяем директорию бота (где лежит main.py)
    bot_dir = os.path.dirname(os.path.abspath(__file__))

    # Показываем предупреждение
    await message.answer(
        "⚠️ **ВНИМАНИЕ: УДАЛЕНИЕ БОТА**\n\n"
        "Это действие удалит:\n"
        "• Всю базу данных (все списки, задачи, рецепты)\n"
        "• Все настройки пользователей\n"
        "• Файл .env (токены бота)\n"
        "• Git-директорию\n"
        "• Виртуальное окружение\n\n"
        "Действие **НЕОБРАТИМО**!\n\n"
        "Для подтверждения удаления отправьте: `/delete confirm`",
        parse_mode="Markdown"
    )


async def cmd_delete_confirm(message: types.Message):
    """
    Подтверждение удаления бота.

    Args:
        message: Сообщение от пользователя
    """
    # Проверяем права админа
    if not is_admin(message.from_user.id):
        return

    import os
    import shutil

    # Определяем директорию бота (где лежит main.py)
    bot_dir = os.path.dirname(os.path.abspath(__file__))

    # Файлы и директории для удаления
    files_to_delete = [
        'notebook.db',
        'notebook.db-shm',
        'notebook.db-wal',
        '.env',
        '.git',
        'venv',
        '__pycache__',
        '*.pyc'
    ]

    deleted_count = 0
    errors = []

    # Удаляем файлы и директории
    for item in files_to_delete:
        try:
            item_path = os.path.join(bot_dir, item)
            if item.endswith('*'):
                # Глоб-паттерн
                import glob
                for path in glob.glob(os.path.join(bot_dir, item)):
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    deleted_count += 1
            elif os.path.exists(item_path):
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
                deleted_count += 1
        except Exception as e:
            errors.append(f"{item}: {str(e)}")

    # Формируем отчёт
    if errors:
        await message.answer(
            "⚠️ **Удаление завершено с ошибками**\n\n"
            f"Удалено объектов: {deleted_count}\n\n"
            "Ошибки:\n```\n" + "\n".join(errors[:10]) + "\n```",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "🗑 **Бот полностью удалён!**\n\n"
            f"Удалено объектов: {deleted_count}\n\n"
            "Для повторной установки выполните:\n"
            "• Linux: `curl -sSL https://raw.githubusercontent.com/Drentis/TelegramAssistant/master/deploy.sh | sudo bash`\n"
            "• Windows: `powershell -ExecutionPolicy Bypass -File install.ps1`",
            parse_mode="Markdown"
        )

    # Останавливаем бота (не работает в poll mode, но оставляем на случай использования webhook)
    await message.answer("🛑 Бот будет остановлен после завершения работы текущего цикла...")


async def handle_shopping_button(message: types.Message | types.CallbackQuery):
    """
    Обработчик нажатия на кнопку 'Список покупок'.

    Показывает категории магазинов с настраиваемыми названиями.

    Args:
        message: Сообщение или CallbackQuery от пользователя
    """
    # Получаем настройки пользователя
    if isinstance(message, types.CallbackQuery):
        user_id = message.from_user.id
        send_method = message.message.answer
    else:
        user_id = message.from_user.id
        send_method = message.answer

    settings = await db.get_category_settings(user_id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🥕 {settings['magnit_name']} ({settings.get('magnit_desc', 'Продукты')})", callback_data="shopping_magnit")],
            [InlineKeyboardButton(text=f"🏠 {settings['fixprice_name']} ({settings.get('fixprice_desc', 'Бытовое')})", callback_data="shopping_fixprice")],
            [InlineKeyboardButton(text=f"📦 {settings['other_name']} ({settings.get('other_desc', 'Другое')})", callback_data="shopping_other")],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main")]
        ]
    )

    text = (
        f"🛒 **Список покупок**\n\n"
        f"🥕 **{settings['magnit_name']}** — {settings.get('magnit_desc', 'Продукты')}\n"
        f"🏠 **{settings['fixprice_name']}** — {settings.get('fixprice_desc', 'Бытовое')}\n"
        f"📦 **{settings['other_name']}** — {settings.get('other_desc', 'Другое')}\n\n"
        f"Чтобы добавить товар, напишите:\n"
        f"`{settings.get('buy_trigger', 'купить')}` молоко\n\n"
        f"Можно использовать названия магазинов:\n"
        f"`{settings['magnit_name']} {settings.get('buy_trigger', 'купить')}` хлеб\n\n"
        f"Или сокращения:\n"
        f"`{settings['magnit_short']} {settings.get('buy_trigger', 'купить')}`...\n"
        f"`{settings['fixprice_short']} {settings.get('buy_trigger', 'купить')}`...\n"
        f"`{settings['other_short']} {settings.get('buy_trigger', 'купить')}`...\n\n"
        "Выберите магазин для просмотра:"
    )

    if isinstance(message, types.CallbackQuery):
        await send_method(
            text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await message.answer()
    else:
        await send_method(
            text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


async def handle_shopping_callback(callback: types.CallbackQuery):
    """Обработка выбора категории покупок."""
    category = callback.data.replace("shopping_", "")

    # Получаем настройки пользователя
    settings = await db.get_category_settings(callback.from_user.id)
    category_settings = {
        "magnit": settings['magnit_name'],
        "fixprice": settings['fixprice_name'],
        "other": settings['other_name']
    }
    category_emoji = {
        "magnit": "🥕",
        "fixprice": "🏠",
        "other": "📦"
    }

    items = await db.get_shopping_items(callback.from_user.id, category)
    category_name = category_settings.get(category, category)
    category_em = category_emoji.get(category, "📦")

    if not items:
        text = f"{category_em} {category_name}\n\nСписок пуст."
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="back_to_shopping")]
            ]
        )
    else:
        text = f"{category_em} {category_name}:\n\n"
        for item in items:
            if item['taken']:
                text += f"✅ {item['item']}\n"
            else:
                text += f"• {item['item']}\n"
        text += f"\nВсего: {len(items)}"
        keyboard = get_items_keyboard(items, "shopping", category)

    try:
        await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
    except Exception:
        pass  # Игнорируем ошибки устаревших callback


async def handle_edit_list_callback(callback: types.CallbackQuery):
    """Редактирование списка."""
    data = callback.data.replace("edit_", "")
    parts = data.split("_")

    if len(parts) >= 2:
        list_type = parts[0]
        category = parts[1] if len(parts) > 1 else None

        # Получаем настройки пользователя
        settings = await db.get_category_settings(callback.from_user.id)

        if list_type == "shopping":
            category_settings = {
                "magnit": settings['magnit_name'],
                "fixprice": settings['fixprice_name'],
                "other": settings['other_name']
            }
            category_emoji = {
                "magnit": "🥕",
                "fixprice": "🏠",
                "other": "📦"
            }
            items = await db.get_shopping_items(callback.from_user.id, category)
            category_name = category_settings.get(category, category)
            category_em = category_emoji.get(category, "📦")
            text = f"{category_em} {category_name}:\n\n"
            for item in items:
                taken_status = "✅" if item['taken'] else "❌"
                text += f"{taken_status} {item['item']}\n"
            text += f"\nВсего: {len(items)}\n\n✏️ _Нажимайте на товары, чтобы отметить их_"
            keyboard = get_edit_keyboard(items, "shopping", category)

            try:
                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            except Exception:
                pass
        elif list_type == "todo":
            items = await db.get_todo_items(callback.from_user.id)
            text = "📋 **Список дел:**\n\n"
            for item in items:
                text += f"❌ {item['task']}\n"
            text += f"\nВсего: {len(items)}\n\n✏️ _Нажимайте на задачи, чтобы удалить их_"
            keyboard = get_edit_keyboard(items, "todo")

            try:
                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            except Exception:
                pass
        elif list_type == "study":
            items = await db.get_study_items(callback.from_user.id)
            text = "📚 **Учёба:**\n\n"
            for item in items:
                text += f"❌ {item['task']}\n"
            text += f"\nВсего: {len(items)}\n\n✏️ _Нажимайте на задачи, чтобы удалить их_"
            keyboard = get_edit_keyboard(items, "study")

            try:
                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            except Exception:
                pass
        elif list_type == "ideas":
            items = await db.get_ideas(callback.from_user.id)
            text = "💡 **Идеи:**\n\n"
            for item in items:
                text += f"✨ {item['idea']}\n"
            text += f"\nВсего: {len(items)}\n\n✏️ _Нажимайте на идеи, чтобы удалить их_"
            keyboard = get_edit_keyboard(items, "ideas")

            try:
                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            except Exception:
                pass

    await callback.answer()


async def handle_back_from_edit_callback(callback: types.CallbackQuery):
    """Возврат из режима редактирования к просмотру."""
    data = callback.data.replace("back_edit_", "")
    parts = data.split("_")

    if len(parts) >= 2:
        list_type = parts[0]
        category = parts[1] if len(parts) > 1 else None

        if list_type == "shopping":
            # Возвращаемся к отображению списка покупок
            settings = await db.get_category_settings(callback.from_user.id)
            category_settings = {
                "magnit": settings['magnit_name'],
                "fixprice": settings['fixprice_name'],
                "other": settings['other_name']
            }
            category_emoji = {
                "magnit": "🥕",
                "fixprice": "🏠",
                "other": "📦"
            }
            items = await db.get_shopping_items(callback.from_user.id, category)
            category_name = category_settings.get(category, category)
            category_em = category_emoji.get(category, "📦")

            if not items:
                text = f"{category_em} {category_name}\n\nСписок пуст."
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="back_to_shopping")]
                    ]
                )
            else:
                text = f"{category_em} {category_name}:\n\n"
                for item in items:
                    taken_status = "✅" if item['taken'] else "❌"
                    text += f"{taken_status} {item['item']}\n"
                text += f"\nВсего: {len(items)}"
                keyboard = get_items_keyboard(items, "shopping", category)

            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except Exception:
                pass

    await callback.answer()


async def handle_todo_button(message: types.Message, state: FSMContext):
    """Нажатие на кнопку 'Список дел'."""
    await state.set_state(TodoState.waiting_for_task)
    await message.answer(
        "📋 **Список дел**\n\n"
        "Напишите задачу, начиная со слова _сделать_\n"
        "Можно указать дату: _сделать купить хлеб завтра_ или _сделать проект 15.03_\n\n"
        "Для отмены напишите /cancel",
        parse_mode="Markdown"
    )


async def handle_todo_view(message: types.Message):
    """Просмотр списка дел."""
    settings = await db.get_category_settings(message.from_user.id)
    items = await db.get_todo_items(message.from_user.id)

    if not items:
        await message.answer("📋 Список дел пуст\n\nДобавьте первую задачу!", reply_markup=get_main_keyboard(settings))
        return

    text = "📋 **Список дел:**\n\n"
    for item in items:
        emoji = "⚠️" if item['reminded'] else "📌"
        text += f"{emoji} {item['task']}"
        if item['due_date']:
            due = datetime.strptime(item['due_date'], '%Y-%m-%d').date()
            days_until = (due - date.today()).days
            if days_until == 0:
                text += " — **сегодня**"
            elif days_until == 1:
                text += " — **завтра**"
            elif days_until < 0:
                text += f" — просрочено ({abs(days_until)} дн. назад)"
            else:
                text += f" — через {days_until} дн. ({due.strftime('%d.%m.%Y')})"
        text += "\n"

    text += f"\nВсего: {len(items)}"
    keyboard = get_items_keyboard(items, "todo")
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


async def handle_study_view(message: types.Message):
    """Просмотр списка учёбы."""
    settings = await db.get_category_settings(message.from_user.id)
    items = await db.get_study_items(message.from_user.id)

    if not items:
        await message.answer("📚 Список учёбы пуст\n\nДобавьте первую задачу!", reply_markup=get_main_keyboard(settings))
        return

    text = "📚 **Учёба:**\n\n"
    for item in items:
        text += f"📖 {item['task']}\n"

    text += f"\nВсего: {len(items)}"
    keyboard = get_items_keyboard(items, "study")
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


async def handle_ideas_view(message: types.Message):
    """Просмотр списка идей."""
    settings = await db.get_category_settings(message.from_user.id)
    items = await db.get_ideas(message.from_user.id)

    if not items:
        await message.answer("💡 Список идей пуст\n\nДобавьте первую идею!", reply_markup=get_main_keyboard(settings))
        return

    text = "💡 **Идеи:**\n\n"
    for item in items:
        text += f"✨ {item['idea']}\n"

    text += f"\nВсего: {len(items)}"
    keyboard = get_items_keyboard(items, "ideas")
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


async def handle_recipes_view(message: types.Message):
    """Просмотр списка рецептов."""
    settings = await db.get_category_settings(message.from_user.id)
    items = await db.get_recipes(message.from_user.id)

    if not items:
        await message.answer(
            "🍳 **Список рецептов пуст**\n\n"
            "Чтобы добавить рецепт, напишите:\n"
            "_рецепт Название рецепта_\n\n"
            "После этого бот предложит добавить ингредиенты.\n\n"
            "Для выхода напишите /cancel",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(settings)
        )
        return

    # Создаём клавиатуру со списком рецептов
    buttons = []
    for item in items:
        buttons.append([InlineKeyboardButton(text=f"📖 {item['name']}", callback_data=f"recipe_view_{item['id']}")])

    buttons.append([InlineKeyboardButton(text="➕ Добавить рецепт", callback_data="recipe_add_new")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = "🍳 **Мои рецепты:**\n\n"
    for item in items:
        # Получаем количество ингредиентов
        ingredients = await db.get_recipe_ingredients(item['id'])
        text += f"📖 **{item['name']}** — {len(ingredients)} инг.\n"

    text += f"\nВсего: {len(items)}"
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


async def handle_info_view(message: types.Message):
    """Просмотр информации о боте."""
    settings = await db.get_category_settings(message.from_user.id)

    buy = settings.get('buy_trigger', 'купить')
    todo = settings.get('todo_trigger', 'сделать')
    study = settings.get('study_trigger', 'учёба')
    ideas = settings.get('ideas_trigger', 'идея')
    recipes = settings.get('recipes_trigger', 'рецепт')

    await message.answer(
        f"ℹ️ **СПРАВКА**\n\n"
        f"Я помогу вам вести списки и заметки!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛒 **СПИСОК ПОКУПОК**\n"
        f"• Запишите: `{buy} молоко, яйца`\n"
        f"• Товары сами распределятся по магазинам\n"
        f"• Для ручной сортировки: `м {buy} хлеб`\n"
        f"• Отмечайте купленное и удаляйте лишнее\n\n"
        f"📋 **СПИСОК ДЕЛ**\n"
        f"• Запишите: `{todo} уборку завтра`\n"
        f"• Указывайте дату: завтра, 15.03, 10 марта\n"
        f"• Напоминание придёт за день до события\n\n"
        f"📚 **УЧЁБА**\n"
        f"• Запишите: `{study} выучить 50 слов`\n"
        f"• Все учебные задачи в одном месте\n\n"
        f"💡 **ИДЕИ**\n"
        f"• Запишите: `{ideas} записать мысль`\n"
        f"• Быстрые заметки для важных идей\n\n"
        f"🍳 **РЕЦЕПТЫ**\n"
        f"• Запишите: `{recipes} Борщ`\n"
        f"• Добавьте ингредиенты по одному\n"
        f"• Кнопка 'Добавить в корзину' перенесёт все продукты в список покупок\n\n"
        f"⚙️ **НАСТРОЙКИ**\n"
        f"• Меняйте названия магазинов\n"
        f"• Настраивайте команды\n"
        f"• Включайте и отключайте разделы\n\n"
        f"🌤 **ПОГОДА**\n"
        f"• Ежедневный прогноз в заданное время\n"
        f"• Предупреждения о дожде\n"
        f"• Настройте свой город\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 **Кнопки меню:**\n"
        f"⚙️ Настройки → 📱 Кнопки меню\n"
        f"Отключите разделы, которыми не пользуетесь!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆘 **Команды:**\n"
        f"/start — Главное меню\n"
        f"/cancel — Отменить\n"
        f"/done — Завершить рецепт",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(settings)
    )


# === Погода ===
async def get_weather(city: str) -> dict:
    """Получить погоду для города."""
    if not WEATHER_API_KEY or WEATHER_API_KEY == "your_api_key_here":
        return {"error": "API ключ не настроен"}

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": WEATHER_API_KEY,
        "units": "metric",
        "lang": "ru"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "temp": round(data["main"]["temp"]),
                        "feels_like": round(data["main"]["feels_like"]),
                        "description": data["weather"][0]["description"],
                        "icon": data["weather"][0]["icon"],
                        "humidity": data["main"]["humidity"],
                        "wind_speed": data["wind"]["speed"],
                        "city": data["name"],
                        "timezone": data.get("timezone", 0)  # Смещение в секундах от UTC
                    }
                elif response.status == 404:
                    return {"error": "Город не найден"}
                else:
                    return {"error": "Ошибка API"}
    except Exception as e:
        return {"error": f"Ошибка: {str(e)}"}


async def get_weather_forecast(city: str) -> dict:
    """Получить прогноз погоды (проверка на дождь)."""
    if not WEATHER_API_KEY or WEATHER_API_KEY == "your_api_key_here":
        return {"error": "API ключ не настроен"}

    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "q": city,
        "appid": WEATHER_API_KEY,
        "units": "metric",
        "lang": "ru"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    # Проверяем следующие 24 часа на дождь
                    rain_hours = []
                    max_temp = -50
                    min_temp = 50

                    for item in data["list"][:8]:  # 8 интервалов по 3 часа = 24 часа
                        dt = datetime.fromisoformat(item["dt_txt"])
                        weather_id = item["weather"][0]["id"]
                        temp = item["main"]["temp"]

                        # ID погоды: 2xx=гроза, 3xx=морось, 5xx=дождь
                        if weather_id >= 200 and weather_id < 600:
                            rain_hours.append(dt.strftime("%H:%M"))

                        max_temp = max(max_temp, temp)
                        min_temp = min(min_temp, temp)

                    return {
                        "success": True,
                        "will_rain": len(rain_hours) > 0,
                        "rain_hours": rain_hours[:3],  # Первые 3 периода
                        "max_temp": round(max_temp),
                        "min_temp": round(min_temp)
                    }
                else:
                    return {"error": "Ошибка API"}
    except Exception as e:
        return {"error": f"Ошибка: {str(e)}"}


def get_weather_icon(icon_code: str) -> str:
    """Получить emoji для погоды."""
    icons = {
        "01d": "☀️", "01n": "🌙",
        "02d": "⛅", "02n": "☁️",
        "03d": "☁️", "03n": "☁️",
        "04d": "☁️", "04n": "☁️",
        "09d": "🌧", "09n": "🌧",
        "10d": "🌦", "10n": "🌧",
        "11d": "⛈", "11n": "⛈",
        "13d": "❄️", "13n": "❄️",
        "50d": "🌫", "50n": "🌫"
    }
    return icons.get(icon_code, "🌤")


async def send_weather_report(bot: Bot, user_id: int, city: str):
    """Отправить отчёт о погоде."""
    weather = await get_weather(city)

    if not weather.get("success"):
        return

    icon = get_weather_icon(weather["icon"])
    text = (
        f"{icon} **Погода на сегодня**\n\n"
        f"📍 {weather['city']}\n"
        f"🌡 +{weather['temp']}°C (ощущается как +{weather['feels_like']}°C)\n"
        f"🌤 {weather['description'].capitalize()}\n"
        f"💨 Ветер {weather['wind_speed']} м/с\n"
        f"💧 Влажность {weather['humidity']}%\n\n"
        f"Хорошего дня! ☀️"
    )

    try:
        await bot.send_message(user_id, text, parse_mode="Markdown")
    except Exception:
        pass


async def send_rain_alert(bot: Bot, user_id: int, city: str):
    """Отправить уведомление о дожде."""
    forecast = await get_weather_forecast(city)

    if not forecast.get("success") or not forecast.get("will_rain"):
        return

    rain_times = ", ".join(forecast["rain_hours"])
    text = (
        f"☔ **Возьмите зонт!**\n\n"
        f"📍 {city}\n"
        f"Сегодня ожидается дождь.\n"
        f"🕐 Примерно в: {rain_times}\n\n"
        f"Не забудьте зонт! 🌂"
    )

    try:
        await bot.send_message(user_id, text, parse_mode="Markdown")
    except Exception:
        pass


async def handle_recipe_add_new_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начало добавления нового рецепта."""
    await state.set_state(RecipeState.adding_recipe)
    await callback.message.answer(
        "🍳 **Добавление рецепта**\n\n"
        "Напишите название рецепта:\n"
        "Например: _Борщ, Паста Карбонара, Оливье_\n\n"
        "Для отмены: /cancel",
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_recipe_view_callback(callback: types.CallbackQuery):
    """Просмотр конкретного рецепта."""
    data = callback.data.replace("recipe_view_", "")
    recipe_id = int(data)

    recipe = await db.get_recipe(callback.from_user.id, recipe_id)
    if not recipe:
        await callback.answer("❌ Рецепт не найден", show_alert=True)
        return

    ingredients = await db.get_recipe_ingredients(recipe_id)

    # Формируем текст рецепта
    text = f"🍳 **{recipe['name']}**\n\n"
    if recipe['description']:
        text += f"📝 **Инструкция:**\n{recipe['description']}\n\n"

    text += "🛒 **Ингредиенты:**\n"
    if ingredients:
        for ing in ingredients:
            text += f"• {ing['ingredient']}\n"
    else:
        text += "_Нет ингредиентов_\n"

    # Клавиатура с кнопками
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Добавить в корзину", callback_data=f"recipe_add_to_cart_{recipe_id}")],
            [InlineKeyboardButton(text="🗑 Удалить рецепт", callback_data=f"recipe_delete_{recipe_id}")],
            [InlineKeyboardButton(text="🔙 Назад к рецептам", callback_data="back_to_recipes")]
        ]
    )

    try:
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=keyboard)
    except Exception:
        pass

    try:
        await callback.answer()
    except Exception:
        pass  # Игнорируем устаревшие callback query


async def handle_recipe_add_to_cart_callback(callback: types.CallbackQuery):
    """Добавление ингредиентов рецепта в корзину."""
    data = callback.data.replace("recipe_add_to_cart_", "")
    recipe_id = int(data)

    ingredients = await db.get_recipe_ingredients(recipe_id)
    if not ingredients:
        await callback.answer("❌ В рецепте нет ингредиентов", show_alert=True)
        return

    # Получаем настройки для отображения
    settings = await db.get_category_settings(callback.from_user.id)
    magnit_name = f"🥕 {settings['magnit_name']} ({settings.get('magnit_desc', 'Продукты')})"

    added_items = []
    existing_items = []

    for ing in ingredients:
        ingredient_name = ing['ingredient']
        # Все ингредиенты добавляем в Магнит (продукты)
        success, _ = await db.add_shopping_item(callback.from_user.id, ingredient_name, "magnit")
        if success:
            added_items.append(f"{ingredient_name} → {magnit_name}")
        else:
            existing_items.append(f"{ingredient_name} (уже в {magnit_name})")

    # Формируем ответ
    response = "✅ **Добавлено в корзину:**\n"
    if added_items:
        for item in added_items[:10]:  # Показываем до 10 элементов
            response += f"• {item}\n"
        if len(added_items) > 10:
            response += f"... и ещё {len(added_items) - 10}\n"
    else:
        response += "_Ничего не добавлено_\n"

    if existing_items:
        response += "\n⚠️ **Уже есть в списке:**\n"
        for item in existing_items[:5]:  # Показываем до 5 элементов
            response += f"• {item}\n"
        if len(existing_items) > 5:
            response += f"... и ещё {len(existing_items) - 5}\n"

    try:
        await callback.answer(response, show_alert=True)
    except Exception:
        pass  # Игнорируем устаревшие callback query


async def handle_recipe_delete_callback(callback: types.CallbackQuery):
    """Удаление рецепта."""
    data = callback.data.replace("recipe_delete_", "")
    recipe_id = int(data)

    await db.delete_recipe(callback.from_user.id, recipe_id)

    try:
        await callback.message.edit_text("✅ Рецепт удалён.")
    except Exception:
        pass

    try:
        await callback.answer()
    except Exception:
        pass  # Игнорируем устаревшие callback query


async def handle_back_to_recipes_callback(callback: types.CallbackQuery):
    """Возврат к списку рецептов."""
    try:
        await callback.message.delete()
    except Exception:
        pass
    await handle_recipes_view(callback.message)
    try:
        await callback.answer()
    except Exception:
        pass


async def handle_shopping_message(message: types.Message, state: FSMContext):
    """Обработка сообщений для добавления покупок, дел и учёбы."""
    text = message.text.strip()
    text_lower = text.lower()

    # Игнорируем сообщения, которые являются кнопками меню
    menu_buttons = ["🛒 список покупок", "📋 список дел", "📚 учёба", "🍳 рецепты", "ℹ️ инфо", "🌤 погода", "⚙️ настройки"]
    if text_lower in menu_buttons:
        return
    
    # Обработка кнопки "💡 Идеи" — показываем список идей
    if text_lower == "💡 идеи":
        await handle_ideas_view(message)
        return

    # Получаем настройки пользователя
    settings = await db.get_category_settings(message.from_user.id)

    buy_trigger = settings.get('buy_trigger', 'купить')
    todo_trigger = settings.get('todo_trigger', 'сделать')
    study_trigger = settings.get('study_trigger', 'учёба')
    ideas_trigger = settings.get('ideas_trigger', 'идея')
    recipes_trigger = settings.get('recipes_trigger', 'рецепт')

    buy_trigger_lower = buy_trigger.lower()
    todo_trigger_lower = todo_trigger.lower()
    study_trigger_lower = study_trigger.lower()
    ideas_trigger_lower = ideas_trigger.lower()
    recipes_trigger_lower = recipes_trigger.lower()

    # Проверяем префиксы категорий (м, ф, д и т.д.)
    manual_category = None
    magnit_prefixes = [f"{settings['magnit_name'].lower()} ", f"{settings['magnit_short'].lower()} "]
    fixprice_prefixes = [f"{settings['fixprice_name'].lower()} ", f"{settings['fixprice_short'].lower()} "]
    other_prefixes = [f"{settings['other_name'].lower()} ", f"{settings['other_short'].lower()} "]

    # Проверяем, начинается ли сообщение с префикса категории
    for prefix_list, category in [(magnit_prefixes, "magnit"), (fixprice_prefixes, "fixprice"), (other_prefixes, "other")]:
        for prefix in prefix_list:
            if text_lower.startswith(prefix):
                manual_category = category
                text = text[len(prefix):].strip()
                text_lower = text.lower()
                break
        if manual_category:
            break

    # Проверяем, с какого триггера начинается сообщение (после удаления префикса категории)
    if text_lower.startswith(buy_trigger_lower) or text_lower.startswith(todo_trigger_lower) or text_lower.startswith(study_trigger_lower) or text_lower.startswith(ideas_trigger_lower) or text_lower.startswith(recipes_trigger_lower):
        # Определяем тип по первому слову
        if text_lower.startswith(buy_trigger_lower):
            # Это покупка
            item_text = text[len(buy_trigger):].strip()

            if not item_text:
                await message.answer("❌ Укажите, что нужно купить.\n\nНапример: _купить молоко, яйца, хлеб_", parse_mode="Markdown")
                return

            # Разбиваем по запятой, если есть несколько товаров
            items = [item.strip() for item in item_text.split(',')]

            category_names = {
                "magnit": f"🥕 {settings['magnit_name']} ({settings.get('magnit_desc', 'Продукты')})",
                "fixprice": f"🏠 {settings['fixprice_name']} ({settings.get('fixprice_desc', 'Бытовое')})",
                "other": f"📦 {settings['other_name']} ({settings.get('other_desc', 'Другое')})"
            }

            added_items = []
            existing_items = []

            for item in items:
                if not item:
                    continue
                # Сохраняем с заглавной буквы
                item = item.capitalize()
                category = classify_item(item) if not manual_category else manual_category
                success, status = await db.add_shopping_item(message.from_user.id, item, category)
                if success:
                    added_items.append(f"{item} → {category_names[category]}")
                else:
                    existing_items.append(f"{item} (уже в {category_names[category]})")

            if added_items or existing_items:
                response = ""
                if added_items:
                    response = "✅ Добавлено:\n" + "\n".join(f"• {item}" for item in added_items)
                if existing_items:
                    if response:
                        response += "\n\n"
                    response += "⚠️ Уже есть в списке:\n" + "\n".join(f"• {item}" for item in existing_items)
                await message.answer(response, parse_mode="Markdown")

        elif text_lower.startswith(todo_trigger_lower):
            # Это дело
            task_text = text[len(todo_trigger):].strip()
            cleaned_text, due_date = parse_date_from_text(task_text)

            if not cleaned_text:
                await message.answer("❌ Задача не может быть пустой.\n\nНапример: _сделать уборку завтра_", parse_mode="Markdown")
                return

            cleaned_text = cleaned_text.capitalize()
            success, status = await db.add_todo_item(message.from_user.id, cleaned_text, due_date)

            if success:
                response = f"✅ Задача добавлена: _{cleaned_text}_"
                if due_date:
                    days_until = (due_date - date.today()).days
                    if days_until == 0:
                        response += "\n📅 Срок: **сегодня**"
                    elif days_until == 1:
                        response += "\n📅 Срок: **завтра**"
                    else:
                        response += f"\n📅 Срок: **{due_date.strftime('%d.%m.%Y')}**"
            else:
                response = f"⚠️ Такая задача уже есть: _{cleaned_text}_"

            await message.answer(response, parse_mode="Markdown", reply_markup=get_main_keyboard(settings))

        elif text_lower.startswith(study_trigger_lower):
            # Это учёба
            task_text = text[len(study_trigger):].strip()

            if not task_text:
                await message.answer("❌ Задача не может быть пустой.\n\nНапример: _учёба выучить 50 слов_", parse_mode="Markdown")
                return

            task_text = task_text.capitalize()
            success, status = await db.add_study_item(message.from_user.id, task_text)

            if success:
                await message.answer(
                    f"✅ Добавлено в учёбу: _{task_text}_",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard(settings)
                )
            else:
                await message.answer(
                    f"⚠️ Такая задача уже есть: _{task_text}_",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard(settings)
                )

        elif text_lower.startswith(ideas_trigger_lower):
            # Это идея
            idea_text = text[len(ideas_trigger):].strip()

            if not idea_text:
                await message.answer("❌ Идея не может быть пустой.\n\nНапример: _идея записать мысль_", parse_mode="Markdown")
                return

            idea_text = idea_text.capitalize()
            success, status = await db.add_idea(message.from_user.id, idea_text)

            if success:
                await message.answer(
                    f"✅ Добавлено в идеи: _{idea_text}_",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard(settings)
                )
            else:
                await message.answer(
                    f"⚠️ Такая идея уже есть: _{idea_text}_",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard(settings)
                )

        elif text_lower.startswith(recipes_trigger_lower):
            # Это рецепт
            recipe_text = text[len(recipes_trigger):].strip()

            if not recipe_text:
                await message.answer("❌ Укажите название рецепта.\n\nНапример: _рецепт Борщ_", parse_mode="Markdown")
                return

            # Запускаем процесс добавления рецепта
            await state.set_state(RecipeState.adding_recipe)
            await state.update_data(recipe_name=recipe_text)
            await message.answer(
                f"🍳 **Добавляем рецепт: {recipe_text}**\n\n"
                "Добавьте ингредиенты по одному:\n"
                "Напишите ингредиент (например, _молоко 500мл_ или _яйца 6шт_).\n\n"
                "Когда закончите, напишите _готово_ или /done.\n"
                "Для отмены: /cancel",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(settings)
            )
    else:
        # Если сообщение не начинается с триггера, игнорируем
        pass


async def handle_settings_button(message: types.Message, state: FSMContext):
    """Нажатие на кнопку 'Настройки'."""
    await state.set_state(SettingsState.choosing_category)
    settings = await db.get_category_settings(message.from_user.id)
    
    # Проверяем, является ли пользователь админом
    is_admin_user = is_admin(message.from_user.id)

    keyboard_buttons = [
        [InlineKeyboardButton(
            text=f"🥕 {settings['magnit_name']} ({settings['magnit_short']})",
            callback_data="settings_magnit"
        )],
        [InlineKeyboardButton(
            text=f"🏠 {settings['fixprice_name']} ({settings['fixprice_short']})",
            callback_data="settings_fixprice"
        )],
        [InlineKeyboardButton(
            text=f"📦 {settings['other_name']} ({settings['other_short']})",
            callback_data="settings_other"
        )],
        [InlineKeyboardButton(text="🔤 Триггерные слова", callback_data="settings_triggers")],
        [InlineKeyboardButton(text="📱 Кнопки меню", callback_data="settings_visibility")],
        [InlineKeyboardButton(text="🌤 Погода", callback_data="settings_weather")],
        [InlineKeyboardButton(text="🗑 Сброс профиля", callback_data="settings_reset_profile")],
    ]
    
    # Добавляем кнопку админ-панели только для админа
    if is_admin_user:
        keyboard_buttons.append([InlineKeyboardButton(text="👤 Админ-панель", callback_data="admin_panel")])
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    admin_text = "\n\n👤 **Админ-панель** — статистика и обновление бота" if is_admin_user else ""

    await message.answer(
        f"⚙️ **Настройки**\n\n"
        f"Выберите, что хотите настроить:\n\n"
        f"🥕 **{settings['magnit_name']}** — {settings.get('magnit_desc', 'Продукты')}\n"
        f"   Сокращение: `{settings['magnit_short']}`\n\n"
        f"🏠 **{settings['fixprice_name']}** — {settings.get('fixprice_desc', 'Бытовое')}\n"
        f"   Сокращение: `{settings['fixprice_short']}`\n\n"
        f"📦 **{settings['other_name']}** — {settings.get('other_desc', 'Другое')}\n"
        f"   Сокращение: `{settings['other_short']}`\n\n"
        f"🔤 **Команды:**\n"
        f"   Покупки: `{settings.get('buy_trigger', 'купить')}`\n"
        f"   Дела: `{settings.get('todo_trigger', 'сделать')}`\n"
        f"   Учёба: `{settings.get('study_trigger', 'учёба')}`\n"
        f"   Идеи: `{settings.get('ideas_trigger', 'идея')}`\n"
        f"   Рецепты: `{settings.get('recipes_trigger', 'рецепт')}`\n\n"
        f"🌤 **Погода:**\n"
        f"   Город: `{settings.get('weather_city', 'не задан') or 'не задан'}`\n"
        f"   Прогноз: {'✅' if settings.get('weather_daily', 0) else '❌'}\n"
        f"   Уведомление о дожде: {'✅' if settings.get('weather_rain', 1) else '❌'}\n\n"
        f"Нажмите на магазин, чтобы изменить название или сокращение.\n"
        f"Нажмите на 'Команды', чтобы изменить слова для добавления.\n"
        f"Нажмите на 'Погода', чтобы настроить прогнозы.{admin_text}\n\n"
        f"⚠️ **Сброс профиля** удалит все данные и настройки!",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_settings_category_callback(callback: types.CallbackQuery, state: FSMContext):
    """Выбор категории для настройки."""
    category = callback.data.replace("settings_", "")
    await state.update_data(choosing_category=category)
    await state.set_state(SettingsState.editing_name)

    settings = await db.get_category_settings(callback.from_user.id)
    category_names = {
        'magnit': '🥕 Магнит',
        'fixprice': '🏠 Фикспрайс',
        'other': '📦 Другое'
    }

    current_name = settings[f'{category}_name']
    current_short = settings[f'{category}_short']
    current_desc = settings.get(f'{category}_desc', 'Описание')

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"settings_edit_name_{category}")],
            [InlineKeyboardButton(text="📝 Изменить описание", callback_data=f"settings_edit_desc_{category}")],
            [InlineKeyboardButton(text="🔤 Изменить сокращение", callback_data=f"settings_edit_short_{category}")],
            [InlineKeyboardButton(text="🔙 Назад к настройкам", callback_data="back_to_settings")]
        ]
    )

    await callback.message.answer(
        f"{category_names.get(category, 'Магазин')}\n\n"
        f"📝 Название: _{current_name}_\n"
        f"📄 Описание: _{current_desc}_\n"
        f"🔤 Сокращение: _{current_short}_\n\n"
        "Выберите, что хотите изменить:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_settings_edit_name_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начало редактирования названия категории."""
    category = callback.data.replace("settings_edit_name_", "")
    await state.update_data(editing_what="name", category=category)
    await state.set_state(SettingsState.editing_name)

    await callback.message.answer(
        "✏️ **Новое название магазина**\n\n"
        "Введите название (1-20 символов):\n"
        "Например: _Перекрёсток, Пятёрочка, Ашан_\n\n"
        "Для отмены: /cancel",
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_settings_edit_desc_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начало редактирования описания категории."""
    category = callback.data.replace("settings_edit_desc_", "")
    await state.update_data(editing_what="desc", category=category)
    await state.set_state(SettingsState.editing_name)

    await callback.message.answer(
        "📝 **Новое описание магазина**\n\n"
        "Введите описание (1-30 символов):\n"
        "Например: _Продукты, Бытовое, Электроника_\n\n"
        "Для отмены: /cancel",
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_settings_edit_short_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начало редактирования сокращения категории."""
    category = callback.data.replace("settings_edit_short_", "")
    await state.update_data(editing_what="short", category=category)
    await state.set_state(SettingsState.editing_short)

    await callback.message.answer(
        "🔤 **Новое сокращение**\n\n"
        "Введите одну букву:\n"
        "Например: _п, ф, д_\n\n"
        "Для отмены: /cancel",
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_settings_edit_trigger_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начало редактирования триггерного слова."""
    trigger_type = callback.data.replace("settings_edit_trigger_", "")
    await state.update_data(editing_what="trigger", trigger_type=trigger_type)
    await state.set_state(SettingsState.editing_name)

    trigger_names = {
        'buy': 'покупок',
        'todo': 'дел',
        'study': 'учёбы',
        'ideas': 'идей',
        'recipes': 'рецептов'
    }

    await callback.message.answer(
        f"✏️ **Новая команда для списка**\n\n"
        f"Введите слово для добавления в список {trigger_names.get(trigger_type, '')}:\n"
        f"(1-15 символов)\n\n"
        "Для отмены: /cancel",
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_settings_input(message: types.Message, state: FSMContext):
    """Обработка ввода нового значения."""
    data = await state.get_data()
    category = data.get('category')
    trigger_type = data.get('trigger_type')
    editing_what = data.get('editing_what')

    if not editing_what:
        await state.set_state(None)
        return

    new_value = message.text.strip()

    if editing_what == "name":
        if len(new_value) > 20:
            await message.answer("❌ Название слишком длинное (максимум 20 символов). Попробуйте ещё раз:")
            return
        await db.update_category_settings(message.from_user.id, **{f'{category}_name': new_value})
        await message.answer(f"✅ Название обновлено: _{new_value}_", parse_mode="Markdown")
    elif editing_what == "desc":
        if len(new_value) > 30:
            await message.answer("❌ Описание слишком длинное (максимум 30 символов). Попробуйте ещё раз:")
            return
        await db.update_category_settings(message.from_user.id, **{f'{category}_desc': new_value})
        await message.answer(f"✅ Описание обновлено: _{new_value}_", parse_mode="Markdown")
    elif editing_what == "short":
        if len(new_value) != 1:
            await message.answer("❌ Сокращение должно быть одной буквой. Попробуйте ещё раз:")
            return
        await db.update_category_settings(message.from_user.id, **{f'{category}_short': new_value})
        await message.answer(f"✅ Сокращение обновлено: _{new_value}_", parse_mode="Markdown")
    elif editing_what == "trigger":
        if len(new_value) > 15:
            await message.answer("❌ Команда слишком длинная (максимум 15 символов). Попробуйте ещё раз:")
            return
        await db.update_category_settings(message.from_user.id, **{f'{trigger_type}_trigger': new_value})
        await message.answer(f"✅ Команда обновлена: _{new_value}_", parse_mode="Markdown")

    await state.set_state(None)
    # Возвращаемся к настройкам
    await handle_settings_button(message, state)


async def handle_settings_visibility_callback(callback: types.CallbackQuery):
    """Настройка видимости кнопок меню."""
    settings = await db.get_category_settings(callback.from_user.id)

    # Формируем кнопки с индикаторами статуса
    def get_status(is_visible):
        return "✅ ВКЛ" if is_visible else "❌ ВЫКЛ"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"🛒 Покупки: {get_status(settings.get('visibility_shopping', 1))}",
                callback_data="settings_toggle_shopping"
            )],
            [InlineKeyboardButton(
                text=f"📋 Дела: {get_status(settings.get('visibility_todo', 1))}",
                callback_data="settings_toggle_todo"
            )],
            [InlineKeyboardButton(
                text=f"📚 Учёба: {get_status(settings.get('visibility_study', 1))}",
                callback_data="settings_toggle_study"
            )],
            [InlineKeyboardButton(
                text=f"💡 Идеи: {get_status(settings.get('visibility_ideas', 1))}",
                callback_data="settings_toggle_ideas"
            )],
            [InlineKeyboardButton(
                text=f"🍳 Рецепты: {get_status(settings.get('visibility_recipes', 1))}",
                callback_data="settings_toggle_recipes"
            )],
            [InlineKeyboardButton(
                text=f"ℹ️ Инфо: {get_status(settings.get('visibility_info', 1))}",
                callback_data="settings_toggle_info"
            )],
            [InlineKeyboardButton(
                text=f"🌤 Погода: {get_status(settings.get('weather_button', 1))}",
                callback_data="settings_toggle_weather"
            )],
            [InlineKeyboardButton(text="🔙 Назад к настройкам", callback_data="back_to_settings")]
        ]
    )

    await callback.message.answer(
        "📱 **Кнопки главного меню**\n\n"
        "Включите разделы, которыми пользуетесь,\n"
        "и отключите те, которые не нужны:\n\n"
        "🛒 **Покупки** — " + ("✅ ВКЛ" if settings.get('visibility_shopping', 1) else "❌ ВЫКЛ") + "\n"
        "📋 **Дела** — " + ("✅ ВКЛ" if settings.get('visibility_todo', 1) else "❌ ВЫКЛ") + "\n"
        "📚 **Учёба** — " + ("✅ ВКЛ" if settings.get('visibility_study', 1) else "❌ ВЫКЛ") + "\n"
        "💡 **Идеи** — " + ("✅ ВКЛ" if settings.get('visibility_ideas', 1) else "❌ ВЫКЛ") + "\n"
        "🍳 **Рецепты** — " + ("✅ ВКЛ" if settings.get('visibility_recipes', 1) else "❌ ВЫКЛ") + "\n"
        "ℹ️ **Инфо** — " + ("✅ ВКЛ" if settings.get('visibility_info', 1) else "❌ ВЫКЛ") + "\n"
        "🌤 **Погода** — " + ("✅ ВКЛ" if settings.get('weather_button', 1) else "❌ ВЫКЛ") + "\n\n"
        "Нажмите на раздел, чтобы включить или выключить его.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_settings_toggle_callback(callback: types.CallbackQuery):
    """Переключение видимости кнопки."""
    data = callback.data.replace("settings_toggle_", "")

    visibility_map = {
        'shopping': 'visibility_shopping',
        'todo': 'visibility_todo',
        'study': 'visibility_study',
        'ideas': 'visibility_ideas',
        'recipes': 'visibility_recipes',
        'info': 'visibility_info',
        'weather': 'weather_button'
    }

    section_names = {
        'shopping': '🛒 Покупки',
        'todo': '📋 Дела',
        'study': '📚 Учёба',
        'ideas': '💡 Идеи',
        'recipes': '🍳 Рецепты',
        'info': 'ℹ️ Инфо',
        'weather': '🌤 Погода'
    }

    if data not in visibility_map:
        await callback.answer()
        return

    settings = await db.get_category_settings(callback.from_user.id)
    current_value = settings.get(visibility_map[data], 1)
    new_value = 0 if current_value else 1

    await db.update_category_settings(callback.from_user.id, **{visibility_map[data]: new_value})

    status = "✅ ВКЛЮЧЕНО" if new_value else "❌ ВЫКЛЮЧЕНО"
    await callback.answer(f"{section_names.get(data, data)}: {status}")

    # Обновляем сообщение с настройками видимости
    await callback.message.delete()
    await handle_settings_visibility_callback(callback)


# === Сброс профиля ===
async def handle_settings_reset_profile_callback(callback: types.CallbackQuery):
    """Сброс профиля пользователя."""
    # Создаём клавиатуру с подтверждением
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚠️ ДА, сбросить всё!", callback_data="reset_profile_confirm"),
                InlineKeyboardButton(text="❌ Нет, отмена", callback_data="reset_profile_cancel")
            ],
            [InlineKeyboardButton(text="🔙 Назад в настройки", callback_data="back_to_settings")]
        ]
    )
    
    await callback.message.answer(
        "⚠️ **ВНИМАНИЕ! Сброс профиля!**\n\n"
        "Это действие удалит:\n"
        "🗑 Все товары из списка покупок\n"
        "🗑 Все задачи из списка дел\n"
        "🗑 Все учебные задачи\n"
        "🗑 Все идеи\n"
        "🗑 Все рецепты с ингредиентами\n"
        "🗑 Все настройки (названия магазинов, триггеры, погода)\n\n"
        "Вы уверены? Это действие **необратимо**!",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_reset_profile_confirm_callback(callback: types.CallbackQuery):
    """Подтверждение сброса профиля."""
    user_id = callback.from_user.id
    
    # Сбрасываем профиль
    await db.reset_user_profile(user_id)
    
    await callback.message.answer(
        "✅ **Профиль сброшен!**\n\n"
        "Все данные и настройки удалены.\n"
        "Теперь бот как новый - настройте его под себя!\n\n"
        "Нажмите /start для начала работы.",
        parse_mode="Markdown"
    )
    await callback.answer("Профиль сброшен!")


async def handle_reset_profile_cancel_callback(callback: types.CallbackQuery):
    """Отмена сброса профиля."""
    await callback.message.delete()
    await callback.answer("Сброс отменён")


async def handle_back_to_settings_callback(callback: types.CallbackQuery):
    """Возврат в настройки."""
    await callback.message.delete()
    await handle_settings_button(callback.message, FSMContext())


# ============================================================
# === АДМИН-ПАНЕЛЬ (Admin Panel)
# ============================================================

async def handle_admin_panel_callback(callback: types.CallbackQuery):
    """Админ-панель."""
    # Проверяем права админа
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    # Получаем статистику
    async with aiosqlite.connect(db.DB_PATH) as db_conn:
        db_conn.row_factory = aiosqlite.Row
        
        # Количество пользователей
        async with db_conn.execute("SELECT COUNT(DISTINCT user_id) FROM shopping_list") as cursor:
            shopping_users = await cursor.fetchone()
            shopping_users_count = shopping_users[0] if shopping_users else 0
        
        async with db_conn.execute("SELECT COUNT(DISTINCT user_id) FROM todo_list") as cursor:
            todo_users = await cursor.fetchone()
            todo_users_count = todo_users[0] if todo_users else 0
        
        # Общее количество пользователей (любой записи)
        async with db_conn.execute("""
            SELECT COUNT(DISTINCT user_id) FROM (
                SELECT user_id FROM shopping_list
                UNION
                SELECT user_id FROM todo_list
                UNION
                SELECT user_id FROM study_list
                UNION
                SELECT user_id FROM ideas_list
                UNION
                SELECT user_id FROM recipes
            )
        """) as cursor:
            total_result = await cursor.fetchone()
            total_users = total_result[0] if total_result else 0
        
        # Количество записей
        async with db_conn.execute("SELECT COUNT(*) FROM shopping_list") as cursor:
            total_shopping = await cursor.fetchone()
            total_shopping_count = total_shopping[0] if total_shopping else 0
        
        async with db_conn.execute("SELECT COUNT(*) FROM todo_list") as cursor:
            total_todo = await cursor.fetchone()
            total_todo_count = total_todo[0] if total_todo else 0
        
        async with db_conn.execute("SELECT COUNT(*) FROM recipes") as cursor:
            total_recipes = await cursor.fetchone()
            total_recipes_count = total_recipes[0] if total_recipes else 0
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить бота", callback_data="admin_update_bot")],
            [InlineKeyboardButton(text="🔙 Назад в настройки", callback_data="back_to_settings")]
        ]
    )
    
    text = (
        f"👤 **Админ-панель**\n\n"
        f"📊 **Статистика бота:**\n\n"
        f"👥 **Пользователи:**\n"
        f"   • Всего: `{total_users}`\n"
        f"   • С покупками: `{shopping_users_count}`\n"
        f"   • С делами: `{todo_users_count}`\n\n"
        f"📝 **Записи:**\n"
        f"   • Покупки: `{total_shopping_count}`\n"
        f"   • Дела: `{total_todo_count}`\n"
        f"   • Рецепты: `{total_recipes_count}`\n\n"
        f"⚙️ **Действия:**\n"
        f"Нажмите 'Обновить бота' для проверки и установки обновлений."
    )
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


async def handle_admin_update_bot_callback(callback: types.CallbackQuery):
    """Обновление бота из админ-панели."""
    # Проверяем права админа
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return

    import subprocess
    import os
    import sys

    # Определяем директорию бота (где лежит main.py)
    bot_dir = os.path.dirname(os.path.abspath(__file__))

    # Определяем путь к pip в виртуальном окружении (кроссплатформенно)
    if sys.platform == 'win32':
        pip_path = os.path.join(bot_dir, 'venv', 'Scripts', 'pip.exe')
        python_path = os.path.join(bot_dir, 'venv', 'Scripts', 'python.exe')
    else:
        pip_path = os.path.join(bot_dir, 'venv', 'bin', 'pip')
        python_path = os.path.join(bot_dir, 'venv', 'bin', 'python')

    await callback.message.answer("🔄 **Проверка обновлений...**\n\nПодождите, это может занять несколько минут.", parse_mode="Markdown")

    try:
        # Проверяем, есть ли .git директория
        git_dir = os.path.join(bot_dir, '.git')

        if not os.path.exists(git_dir):
            # Если нет .git, инициализируем git и добавляем remote
            await callback.message.answer("⚙️ **Первичная настройка git...**\n\nЭто займёт несколько секунд.", parse_mode="Markdown")

            # Инициализируем git
            subprocess.run(['git', 'init'], cwd=bot_dir, capture_output=True, check=True)

            # Добавляем remote (публичный репозиторий)
            remote_url = "https://github.com/Drentis/TelegramAssistant.git"

            subprocess.run(['git', 'remote', 'add', 'origin', remote_url], cwd=bot_dir, capture_output=True, check=True)
            subprocess.run(['git', 'fetch', 'origin'], cwd=bot_dir, capture_output=True, timeout=30, check=True)
            subprocess.run(['git', 'checkout', '-f', 'main'], cwd=bot_dir, capture_output=True, check=True)
            subprocess.run(['git', 'reset', '--hard', 'origin/main'], cwd=bot_dir, capture_output=True, timeout=30, check=True)

            result_stdout = "✓ Репозиторий инициализирован\n✓ Файлы обновлены"
            result_stderr = ""
        else:
            # Выполняем git pull
            result = subprocess.run(
                ['git', 'pull'],
                cwd=bot_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            result_stdout = result.stdout
            result_stderr = result.stderr

        # Проверяем результат
        if result_stderr and 'error' in result_stderr.lower():
            await callback.message.answer(f"❌ **Ошибка обновления:**\n```{result_stderr[:1000]}```", parse_mode="Markdown")
        else:
            # Устанавливаем зависимости
            subprocess.run(
                [pip_path, 'install', '-r', os.path.join(bot_dir, 'requirements.txt')],
                capture_output=True,
                timeout=120
            )

            await callback.message.answer(
                "✅ **Бот обновлён!**\n\n"
                "Обновления применены. Для применения некоторых изменений может потребоваться перезапуск бота.\n\n"
                f"📝 **Что изменилось:**\n```{result_stdout[:1000] if result_stdout else 'Файлы загружены'}```",
                parse_mode="Markdown"
            )

    except subprocess.TimeoutExpired:
        await callback.message.answer("❌ **Превышено время ожидания.**\n\nПроверьте подключение к интернету и попробуйте ещё раз.", parse_mode="Markdown")
    except subprocess.CalledProcessError as e:
        await callback.message.answer(f"❌ **Ошибка выполнения команды:**\n```\n{e.stderr[:1000] if e.stderr else str(e)}\n```", parse_mode="Markdown")
    except Exception as e:
        await callback.message.answer(f"❌ **Произошла ошибка:**\n```{str(e)}```", parse_mode="Markdown")

    await callback.answer()


# === Настройки погоды ===
async def handle_settings_weather_callback(callback: types.CallbackQuery):
    """Настройка погоды."""
    settings = await db.get_category_settings(callback.from_user.id)
    city = settings.get('weather_city', '') or 'не задан'

    daily_status = "✅ ВКЛ" if settings.get('weather_daily', 0) else "❌ ВЫКЛ"
    rain_status = "✅ ВКЛ" if settings.get('weather_rain', 1) else "❌ ВЫКЛ"
    weather_time = settings.get('weather_time', '06:00')

    # Получаем часовой пояс
    tz_name = datetime.now().astimezone().tzinfo

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"🏙 Город: {city}",
                callback_data="weather_set_city"
            )],
            [InlineKeyboardButton(
                text=f"🕐 Время отправки: {weather_time}",
                callback_data="weather_set_time"
            )],
            [InlineKeyboardButton(
                text=f"📅 Утренний прогноз: {daily_status}",
                callback_data="weather_toggle_daily"
            )],
            [InlineKeyboardButton(
                text=f"☂️ Уведомление о дожде: {rain_status}",
                callback_data="weather_toggle_rain"
            )],
            [InlineKeyboardButton(text="🔙 Назад к настройкам", callback_data="back_to_settings")]
        ]
    )

    await callback.message.answer(
        f"🌤 **Настройки погоды**\n\n"
        f"🏙 **Город:** `{city}`\n"
        f"🕐 **Время отправки:** `{weather_time}`\n"
        f"🌍 **Часовой пояс:** {tz_name}\n\n"
        f"📅 **Утренний прогноз:** {daily_status}\n"
        f"   Ежедневно в настроенное время будет приходить прогноз погоды\n\n"
        f"☂️ **Уведомление о дожде:** {rain_status}\n"
        f"   При дожде придёт предупреждение с зонтиком\n\n"
        f"⚠️ Уведомления выключены по умолчанию.\n"
        f"Включите их, чтобы получать прогнозы!\n\n"
        f"💡 Видимость кнопки погоды в главном меню:\n"
        f"⚙️ Настройки → 📱 Кнопки меню → 🌤 Погода",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_weather_set_city_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начало установки города."""
    await state.set_state(WeatherState.setting_city)
    await callback.message.answer(
        "🏙 **Введите название города**\n\n"
        "Напишите город, для которого хотите получать прогноз:\n"
        "Например: _Москва, Санкт-Петербург, Киев_\n\n"
        "Для отмены: /cancel",
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_weather_city_input(message: types.Message, state: FSMContext):
    """Установка города."""
    city = message.text.strip()

    # Проверяем город
    weather = await get_weather(city)

    if not weather.get("success"):
        await message.answer(
            f"❌ {weather.get('error', 'Ошибка')}\n\n"
            "Проверьте название города или попробуйте другой:",
            parse_mode="Markdown"
        )
        return

    await db.update_category_settings(message.from_user.id, weather_city=city)
    await state.set_state(None)

    await message.answer(
        f"✅ Город установлен: **{city}**\n\n"
        f"🌡 Сейчас: +{weather['temp']}°C, {weather['description']}",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    # Возвращаем настройки
    settings = await db.get_category_settings(message.from_user.id)
    await handle_settings_weather_button(message, settings)


async def handle_weather_set_time_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начало установки времени отправки погоды."""
    await state.set_state(WeatherState.setting_time)
    settings = await db.get_category_settings(callback.from_user.id)
    current_time = settings.get('weather_time', '06:00')

    # Получаем часовой пояс
    tz_name = datetime.now().astimezone().tzinfo

    await callback.message.answer(
        f"🕐 **Время отправки прогноза**\n\n"
        f"Текущее время: _{current_time}_\n"
        f"Часовой пояс: {tz_name}\n\n"
        "Введите время в формате ЧЧ:ММ:\n"
        "Например: _07:00, 08:30, 20:00_\n\n"
        "Для отмены: /cancel",
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_weather_time_input(message: types.Message, state: FSMContext):
    """Установка времени отправки погоды."""
    time_text = message.text.strip()

    # Проверяем формат времени (ЧЧ:ММ или Ч:ММ)
    time_match = re.match(r'^([0-9]|0[0-9]|1[0-9]|2[0-3]):([0-5][0-9])$', time_text)
    if not time_match:
        await message.answer(
            "❌ Неверный формат времени.\n\n"
            "Используйте формат ЧЧ:ММ (например, 7:00, 07:00, 08:30, 20:00)\n\n"
            "Попробуйте ещё раз:",
            parse_mode="Markdown"
        )
        return
    
    # Нормализуем время до формата ЧЧ:ММ (с ведущим нулём)
    hour = int(time_match.group(1))
    minute = int(time_match.group(2))
    normalized_time = f"{hour:02d}:{minute:02d}"

    await db.update_category_settings(message.from_user.id, weather_time=normalized_time)
    await state.set_state(None)

    await message.answer(
        f"✅ Время отправки установлено: **{normalized_time}**\n\n"
        f"Теперь прогноз погоды будет приходить ежедневно в {normalized_time}",
        parse_mode="Markdown"
    )
    # Возвращаем настройки
    settings = await db.get_category_settings(message.from_user.id)
    await handle_settings_weather_button(message, settings)


async def handle_weather_button(message: types.Message):
    """Кнопка быстрого запроса погоды."""
    settings = await db.get_category_settings(message.from_user.id)
    city = settings.get('weather_city', '')

    if not city:
        await message.answer(
            "❌ Город не задан\n\n"
            "Установите город в настройках:\n"
            "⚙️ Настройки → 🌤 Погода → 🏙 Город",
            reply_markup=get_main_keyboard(settings)
        )
        return

    await message.answer("🌤 Запрашиваю погоду...", reply_markup=get_main_keyboard(settings))

    weather = await get_weather(city)

    if not weather.get("success"):
        await message.answer(
            f"❌ {weather.get('error', 'Ошибка получения погоды')}",
            reply_markup=get_main_keyboard(settings)
        )
        return

    icon = get_weather_icon(weather["icon"])
    text = (
        f"{icon} **Погода сейчас**\n\n"
        f"📍 {weather['city']}\n"
        f"🌡 +{weather['temp']}°C (ощущается как +{weather['feels_like']}°C)\n"
        f"🌤 {weather['description'].capitalize()}\n"
        f"💨 Ветер {weather['wind_speed']} м/с\n"
        f"💧 Влажность {weather['humidity']}%\n\n"
        f"Хорошего дня! ☀️"
    )

    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard(settings))


async def handle_settings_weather_button(message: types.Message, settings: dict):
    """Показать настройки погоды."""
    city = settings.get('weather_city', '') or 'не задан'
    daily_status = "✅ ВКЛ" if settings.get('weather_daily', 0) else "❌ ВЫКЛ"
    rain_status = "✅ ВКЛ" if settings.get('weather_rain', 1) else "❌ ВЫКЛ"
    weather_time = settings.get('weather_time', '06:00')

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"🏙 Город: {city}",
                callback_data="weather_set_city"
            )],
            [InlineKeyboardButton(
                text=f"🕐 Время отправки: {weather_time}",
                callback_data="weather_set_time"
            )],
            [InlineKeyboardButton(
                text=f"📅 Утренний прогноз: {daily_status}",
                callback_data="weather_toggle_daily"
            )],
            [InlineKeyboardButton(
                text=f"☂️ Уведомление о дожде: {rain_status}",
                callback_data="weather_toggle_rain"
            )],
            [InlineKeyboardButton(text="🔙 Назад к настройкам", callback_data="back_to_settings")]
        ]
    )

    await message.answer(
        f"🌤 **Настройки погоды**\n\n"
        f"🏙 **Город:** `{city}`\n"
        f"🕐 **Время отправки:** `{weather_time}`\n"
        f"📅 **Утренний прогноз:** {daily_status}\n"
        f"☂️ **Уведомление о дожде:** {rain_status}\n"
        f"💡 Видимость кнопки: ⚙️ Настройки → 📱 Кнопки меню",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_weather_toggle_callback(callback: types.CallbackQuery):
    """Переключение настроек погоды."""
    data = callback.data

    settings = await db.get_category_settings(callback.from_user.id)

    if data == "weather_toggle_daily":
        new_value = 0 if settings.get('weather_daily', 0) else 1
        await db.update_category_settings(callback.from_user.id, weather_daily=new_value)
        status = "✅ ВКЛЮЧЕНО" if new_value else "❌ ВЫКЛЮЧЕНО"
        await callback.answer(f"📅 Прогноз погоды: {status}")
    elif data == "weather_toggle_rain":
        new_value = 0 if settings.get('weather_rain', 1) else 1
        await db.update_category_settings(callback.from_user.id, weather_rain=new_value)
        status = "✅ ВКЛЮЧЕНО" if new_value else "❌ ВЫКЛЮЧЕНО"
        await callback.answer(f"☂️ Уведомление о дожде: {status}")

    # Обновляем сообщение
    await callback.message.delete()
    await handle_settings_weather_callback(callback)


async def handle_settings_triggers_callback(callback: types.CallbackQuery, state: FSMContext):
    """Настройка триггерных слов."""
    settings = await db.get_category_settings(callback.from_user.id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"🛒 Покупки: {settings.get('buy_trigger', 'купить')}",
                callback_data="settings_edit_trigger_buy"
            )],
            [InlineKeyboardButton(
                text=f"📋 Дела: {settings.get('todo_trigger', 'сделать')}",
                callback_data="settings_edit_trigger_todo"
            )],
            [InlineKeyboardButton(
                text=f"📚 Учёба: {settings.get('study_trigger', 'учёба')}",
                callback_data="settings_edit_trigger_study"
            )],
            [InlineKeyboardButton(
                text=f"💡 Идеи: {settings.get('ideas_trigger', 'идея')}",
                callback_data="settings_edit_trigger_ideas"
            )],
            [InlineKeyboardButton(
                text=f"🍳 Рецепты: {settings.get('recipes_trigger', 'рецепт')}",
                callback_data="settings_edit_trigger_recipes"
            )],
            [InlineKeyboardButton(text="🔙 Назад к настройкам", callback_data="back_to_settings")]
        ]
    )

    await callback.message.answer(
        "🔤 **Команды**\n\n"
        "Эти слова используются для добавления записей:\n\n"
        f"🛒 **Покупки:** `{settings.get('buy_trigger', 'купить')}`\n"
        f"   Пример: _{settings.get('buy_trigger', 'купить')} молоко_\n\n"
        f"📋 **Дела:** `{settings.get('todo_trigger', 'сделать')}`\n"
        f"   Пример: _{settings.get('todo_trigger', 'сделать')} уборку завтра_\n\n"
        f"📚 **Учёба:** `{settings.get('study_trigger', 'учёба')}`\n"
        f"   Пример: _{settings.get('study_trigger', 'учёба')} выучить слова_\n\n"
        f"💡 **Идеи:** `{settings.get('ideas_trigger', 'идея')}`\n"
        f"   Пример: _{settings.get('ideas_trigger', 'идея')} записать мысль_\n\n"
        f"🍳 **Рецепты:** `{settings.get('recipes_trigger', 'рецепт')}`\n"
        f"   Пример: _{settings.get('recipes_trigger', 'рецепт')} Борщ_\n\n"
        "Нажмите на команду, чтобы изменить слово.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


async def handle_back_to_settings_callback(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к настройкам."""
    await state.set_state(None)
    await callback.message.delete()
    await handle_settings_button(callback.message, state)
    await callback.answer()


async def handle_delete_item_callback(callback: types.CallbackQuery):
    """Удаление элемента из списка."""
    data = callback.data
    parts = data.split("_")

    # Формат: delete_shopping_magnit_123 или delete_todo__123 или delete_study__123
    if len(parts) >= 4 and parts[0] == "delete":
        list_type = parts[1]
        item_id = int(parts[-1])
        category = parts[2] if len(parts) > 3 else None

        if list_type == "shopping":
            await db.delete_shopping_item(callback.from_user.id, item_id)
            await callback.answer("✅ Удалено")
            await refresh_edit_list(callback, "shopping", category)
        elif list_type == "todo":
            await db.delete_todo_item(callback.from_user.id, item_id)
            await callback.answer("✅ Удалено")
            await refresh_edit_list(callback, "todo", None)
        elif list_type == "study":
            await db.delete_study_item(callback.from_user.id, item_id)
            await callback.answer("✅ Удалено")
            await refresh_edit_list(callback, "study", None)
        elif list_type == "ideas":
            await db.delete_idea(callback.from_user.id, item_id)
            await callback.answer("✅ Удалено")
            await refresh_edit_list(callback, "ideas", None)

    try:
        await callback.answer()
    except Exception:
        pass


async def handle_toggle_item_callback(callback: types.CallbackQuery):
    """Переключение статуса taken у товара."""
    data = callback.data
    parts = data.split("_")

    # Формат: toggle_shopping_magnit_123
    if len(parts) >= 4 and parts[0] == "toggle":
        list_type = parts[1]
        item_id = int(parts[-1])
        category = parts[2] if len(parts) > 3 else None

        if list_type == "shopping":
            # Переключаем статус taken
            is_taken = await db.toggle_shopping_item_taken(callback.from_user.id, item_id)
            if is_taken:
                await callback.answer("✅ Взято")
            else:
                await callback.answer("↩️ Возвращено в список")
            # Обновляем сообщение с новым списком
            await refresh_edit_list(callback, "shopping", category)

    try:
        await callback.answer()
    except Exception:
        pass


async def refresh_edit_list(callback: types.CallbackQuery, list_type: str, category: str = None):
    """Обновить отображение списка в режиме редактирования."""
    # Получаем настройки пользователя
    settings = await db.get_category_settings(callback.from_user.id)

    if list_type == "shopping":
        category_settings = {
            "magnit": settings['magnit_name'],
            "fixprice": settings['fixprice_name'],
            "other": settings['other_name']
        }
        category_emoji = {
            "magnit": "🥕",
            "fixprice": "🏠",
            "other": "📦"
        }
        items = await db.get_shopping_items(callback.from_user.id, category)
        category_name = category_settings.get(category, category)
        category_em = category_emoji.get(category, "📦")
        text = f"{category_em} {category_name}:\n\n"
        for item in items:
            if item['taken']:
                text += f"✅ {item['item']}\n"
            else:
                text += f"• {item['item']}\n"
        text += f"\nВсего: {len(items)}\n\n✏️ _Нажимайте на товары, чтобы отметить их_"
        keyboard = get_edit_keyboard(items, "shopping", category)

        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except Exception:
            pass
    elif list_type == "todo":
        items = await db.get_todo_items(callback.from_user.id)
        text = "📋 **Список дел:**\n\n"
        for item in items:
            text += f"❌ {item['task']}\n"
        text += f"\nВсего: {len(items)}\n\n✏️ _Нажимайте на задачи, чтобы удалить их_"
        keyboard = get_edit_keyboard(items, "todo")

        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except Exception:
            pass
    elif list_type == "study":
        items = await db.get_study_items(callback.from_user.id)
        text = "📚 **Учёба:**\n\n"
        for item in items:
            text += f"❌ {item['task']}\n"
        text += f"\nВсего: {len(items)}\n\n✏️ _Нажимайте на задачи, чтобы удалить их_"
        keyboard = get_edit_keyboard(items, "study")

        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except Exception:
            pass
    elif list_type == "ideas":
        items = await db.get_ideas(callback.from_user.id)
        text = "💡 **Идеи:**\n\n"
        for item in items:
            text += f"✨ {item['idea']}\n"
        text += f"\nВсего: {len(items)}\n\n✏️ _Нажимайте на идеи, чтобы удалить их_"
        keyboard = get_edit_keyboard(items, "ideas")

        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except Exception:
            pass


async def handle_clear_list_callback(callback: types.CallbackQuery):
    """Очистка списка."""
    data = callback.data.replace("clear_", "")

    if data.startswith("shopping_"):
        category = data.replace("shopping_", "")
        await db.clear_shopping_list(callback.from_user.id, category)
        try:
            await callback.message.edit_text("✅ Список покупок очищен")
        except Exception:
            pass
    elif data == "todo" or data.startswith("todo_"):
        await db.clear_todo_list(callback.from_user.id)
        try:
            await callback.message.edit_text("✅ Список дел очищен")
        except Exception:
            pass
    elif data == "study" or data.startswith("study_"):
        await db.clear_study_list(callback.from_user.id)
        try:
            await callback.message.edit_text("✅ Список учёбы очищен")
        except Exception:
            pass
    elif data == "ideas" or data.startswith("ideas_"):
        await db.clear_ideas_list(callback.from_user.id)
        try:
            await callback.message.edit_text("✅ Список идей очищен")
        except Exception:
            pass

    try:
        await callback.answer()
    except Exception:
        pass


async def handle_back_callback(callback: types.CallbackQuery):
    """Возврат в главное меню."""
    settings = await db.get_category_settings(callback.from_user.id)
    await callback.message.answer(
        "🏠 **ГЛАВНОЕ МЕНЮ**\n\n"
        "Выберите раздел:\n\n"
        "🛒 Покупки | 📋 Дела | 📚 Учёба\n"
        "💡 Идеи | 🍳 Рецепты | ℹ️ Инфо\n\n"
        "⚙️ Настройки\n\n"
        "💡 Ненужные кнопки можно отключить:\n"
        "⚙️ Настройки → 📱 Кнопки меню\n\n"
        "Подробная справка — в разделе 'Инфо'",
        reply_markup=get_main_keyboard(settings),
        parse_mode="Markdown"
    )
    await callback.answer()


async def cmd_done(message: types.Message, state: FSMContext):
    """Завершение добавления ингредиентов и переход к описанию."""
    current_state = await state.get_state()
    if current_state != RecipeState.adding_recipe:
        return

    data = await state.get_data()
    recipe_name = data.get('recipe_name')
    ingredients = data.get('ingredients', [])

    if not recipe_name:
        await state.set_state(None)
        return

    # Переходим к состоянию добавления описания
    await state.set_state(RecipeState.adding_description)

    await message.answer(
        f"🍳 **Рецепт: {recipe_name}**\n"
        f"📝 Ингредиенты: {len(ingredients)} шт.\n\n"
        "Добавьте описание рецепта (необязательно):\n"
        "Например: _Перемешать всё и готовить при 180 градусах 15 минут_\n\n"
        "Чтобы пропустить, напишите _пропустить_ или /skip.\n"
        "Для отмены: /cancel",
        parse_mode="Markdown"
    )


async def handle_recipe_description(message: types.Message, state: FSMContext):
    """Обработка ввода описания рецепта."""
    current_state = await state.get_state()
    if current_state != RecipeState.adding_description:
        return

    settings = await db.get_category_settings(message.from_user.id)
    data = await state.get_data()
    recipe_name = data.get('recipe_name')
    ingredients = data.get('ingredients', [])

    text = message.text.strip()
    text_lower = text.lower()

    # Проверяем на "пропустить"
    if text_lower in ["пропустить", "skip", "/skip"]:
        description = None
    else:
        description = text

    # Создаём рецепт
    recipe_id, status = await db.add_recipe(message.from_user.id, recipe_name, description)

    if status == "already_exists":
        await state.set_state(None)
        await message.answer(
            f"⚠️ Рецепт «{recipe_name}» уже есть в списке.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(settings)
        )
        return

    # Добавляем ингредиенты
    for ingredient in ingredients:
        await db.add_recipe_ingredient(recipe_id, ingredient)

    await state.set_state(None)

    response = f"✅ Рецепт **{recipe_name}** сохранён!\n"
    response += f"📝 Ингредиенты: {len(ingredients)} шт.\n"
    if description:
        response += "📖 Описание: добавлено\n"
    response += "\nРецепт доступен в разделе 🍳 Рецепты."

    await message.answer(
        response,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(settings)
    )


async def handle_recipe_ingredient(message: types.Message, state: FSMContext):
    """Обработка ввода названия рецепта и ингредиентов."""
    current_state = await state.get_state()
    if current_state != RecipeState.adding_recipe:
        return

    data = await state.get_data()
    recipe_name = data.get('recipe_name')
    ingredients = data.get('ingredients', [])

    text = message.text.strip()
    text_lower = text.lower()

    # Проверяем на "готово"
    if text_lower in ["готово", "done", "/done"]:
        await cmd_done(message, state)
        return

    # Если название рецепта ещё не введено — это название
    if not recipe_name:
        await state.update_data(recipe_name=text)
        await message.answer(
            f"🍳 **Рецепт: {text}**\n\n"
            "Теперь добавьте ингредиенты по одному.\n"
            "Напишите ингредиент (например, _молоко 500мл_ или _яйца 6шт_).\n\n"
            "Когда закончите, напишите _готово_ или /done.\n"
            "Для отмены: /cancel",
            parse_mode="Markdown"
        )
    else:
        # Добавляем ингредиент
        ingredients.append(text)
        await state.update_data(ingredients=ingredients)

        await message.answer(
            f"✅ Добавлено: _{text}_\n\n"
            f"📝 Уже добавлено: {len(ingredients)}\n\n"
            "Добавляйте остальные ингредиенты по одному.\n"
            "Когда закончите, напишите _готово_ или /done.",
            parse_mode="Markdown"
        )


async def cmd_cancel(message: types.Message, state: FSMContext):
    """Отмена текущего состояния."""
    current_state = await state.get_state()
    settings = await db.get_category_settings(message.from_user.id)

    if current_state == RecipeState.adding_recipe:
        data = await state.get_data()
        recipe_name = data.get('recipe_name')
        if recipe_name:
            await message.answer(
                f"❌ Добавление рецепта «{recipe_name}» отменено.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(settings)
            )
        else:
            await message.answer("❌ Отменено.", reply_markup=get_main_keyboard(settings))

    elif current_state == RecipeState.adding_description:
        data = await state.get_data()
        recipe_name = data.get('recipe_name')
        if recipe_name:
            await message.answer(
                f"❌ Добавление рецепта «{recipe_name}» отменено.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard(settings)
            )
        else:
            await message.answer("❌ Отменено.", reply_markup=get_main_keyboard(settings))
    else:
        await message.answer("❌ Отменено.", reply_markup=get_main_keyboard(settings))

    await state.set_state(None)


# === Напоминания ===
async def send_reminders(bot: Bot):
    """Отправка напоминаний о делах."""
    async with aiosqlite.connect(db.DB_PATH) as db_conn:
        db_conn.row_factory = aiosqlite.Row
        async with db_conn.execute("SELECT DISTINCT user_id FROM todo_list") as cursor:
            users = await cursor.fetchall()

        tomorrow = date.today() + timedelta(days=1)

        for user in users:
            user_id = user['user_id']
            todos = await db.get_todos_for_reminder(user_id, tomorrow)

            if todos:
                text = "⏰ **Напоминание о делах на завтра:**\n\n"
                for todo in todos:
                    text += f"• {todo['task']}\n"
                    await db.mark_todo_reminded(user_id, todo['id'])

                try:
                    await bot.send_message(user_id, text, parse_mode="Markdown")
                except Exception:
                    pass


async def reminder_scheduler(bot: Bot):
    """Планировщик напоминаний (каждый день в 9:00)."""
    last_sent_date = None

    while True:
        now = datetime.now()
        current_date = now.date()

        # Проверяем, наступило ли время отправки (9:00)
        if now.hour == 9 and now.minute == 0:
            # Проверяем, не отправляли ли уже сегодня
            if last_sent_date != current_date:
                await send_reminders(bot)
                last_sent_date = current_date

        # Сбрасываем счётчик в полночь
        if now.hour == 0 and now.minute == 1:
            last_sent_date = None

        # Проверяем каждую минуту
        await asyncio.sleep(60)


async def weather_scheduler(bot: Bot):
    """Планировщик погоды (каждый день в настроенное время)."""
    last_sent = {}  # {user_id: date} - отслеживаем, кому уже отправили сегодня
    city_timezones = {}  # {city: timezone_offset} - кэш часовых поясов

    while True:
        now_utc = datetime.utcnow()

        # Получаем всех пользователей с настроенной погодой
        async with aiosqlite.connect(db.DB_PATH) as db_conn:
            db_conn.row_factory = aiosqlite.Row
            async with db_conn.execute(
                "SELECT user_id, weather_city, weather_daily, weather_rain, weather_time FROM category_settings WHERE weather_city != '' AND weather_city IS NOT NULL"
            ) as cursor:
                users = await cursor.fetchall()

        for user in users:
            user_id = user['user_id']
            city = user['weather_city']
            user_time = user['weather_time'] if user['weather_time'] else '06:00'

            # Преобразуем значения в int (из БД могут приходить как None)
            weather_daily = bool(user['weather_daily']) if user['weather_daily'] is not None else False
            weather_rain = bool(user['weather_rain']) if user['weather_rain'] is not None else False

            # Получаем часовой пояс города (из кэша или из API)
            tz_offset = city_timezones.get(city)
            if tz_offset is None:
                weather_data = await get_weather(city)
                if weather_data.get("success"):
                    tz_offset = weather_data.get("timezone", 0)
                    city_timezones[city] = tz_offset
                else:
                    continue  # Пропускаем, если не удалось получить данные

            # Вычисляем местное время города
            city_now = now_utc + timedelta(seconds=tz_offset)
            city_time_str = city_now.strftime('%H:%M')
            city_date = city_now.date()

            # Проверяем, наступило ли время отправки для этого пользователя
            if city_time_str == user_time:
                # Проверяем, не отправляли ли уже сегодня
                if user_id not in last_sent or last_sent[user_id] != city_date:
                    try:
                        # Утренний прогноз (если включено)
                        if weather_daily:
                            await send_weather_report(bot, user_id, city)

                        # Уведомление о дожде (если включено)
                        if weather_rain:
                            await send_rain_alert(bot, user_id, city)

                        # Отмечаем, что сегодня уже отправили
                        last_sent[user_id] = city_date
                    except Exception as e:
                        # Игнорируем ошибки отправки, но продолжаем работу
                        pass

        # Сбрасываем счётчик отправленных каждый день в 00:01 UTC
        if now_utc.hour == 0 and now_utc.minute == 1:
            last_sent.clear()

        # Проверяем каждую минуту
        await asyncio.sleep(60)


# === Основной запуск ===

async def check_for_updates() -> str | None:
    """
    Проверить наличие новой версии на GitHub.

    Returns:
        str | None: Номер новой версии или None если обновлений нет
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.github.com/repos/Drentis/TelegramAssistant/releases/latest",
                timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    latest_version = data.get("tag_name", "").lstrip("v")
                    if latest_version and latest_version != BOT_VERSION:
                        return latest_version
    except Exception:
        pass
    return None


async def notify_admin_on_startup(bot: Bot):
    """
    Отправить уведомление администратору при запуске бота.
    """
    if not ADMIN_ID:
        return

    try:
        # Проверка на обновления
        new_version = await check_for_updates()

        text = f"✅ **Бот запущен!**\n\n"
        text += f"📦 Версия: `{BOT_VERSION}`\n"

        if new_version:
            text += f"\n🆕 **Доступно обновление: v{new_version}**\n"
            text += f"Выполните: `/update` или `telegramactl update`\n\n"
            text += f"📝 [Changelog](https://github.com/Drentis/TelegramAssistant/releases/tag/v{new_version})"
        else:
            text += "\n✅ Версия актуальна"

        await bot.send_message(
            ADMIN_ID,
            text,
            parse_mode="Markdown"
        )
    except Exception:
        pass  # Игнорируем ошибки отправки


async def main():
    await db.init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Команды
    dp.message(Command("start"))(cmd_start)
    dp.message(Command("cancel"))(cmd_cancel)
    dp.message(Command("version"))(cmd_version)
    dp.message(Command("update"))(cmd_update)
    dp.message(Command("delete"))(cmd_delete)
    dp.message(F.text == "/delete confirm")(cmd_delete_confirm)

    # Состояния ожидания для настроек
    dp.message(SettingsState.editing_name, ~Command("cancel"))(handle_settings_input)
    dp.message(SettingsState.editing_short, ~Command("cancel"))(handle_settings_input)

    # Кнопки главного меню
    dp.message(F.text == "🛒 Список покупок")(handle_shopping_button)
    dp.message(F.text == "📋 Список дел")(handle_todo_view)
    dp.message(F.text == "📚 Учёба")(handle_study_view)
    dp.message(F.text == "🍳 Рецепты")(handle_recipes_view)
    dp.message(F.text == "ℹ️ Инфо")(handle_info_view)
    dp.message(F.text == "🌤 Погода")(handle_weather_button)
    dp.message(F.text == "⚙️ Настройки")(handle_settings_button)
    # Кнопка "💡 Идеи" обрабатывается через триггерное слово (handle_shopping_message)

    # Обработка ингредиентов рецепта и описания (ДО обработки триггерных слов!)
    dp.message(RecipeState.adding_recipe, ~Command("cancel"))(handle_recipe_ingredient)
    dp.message(RecipeState.adding_description, ~Command("cancel"))(handle_recipe_description)

    # Обработка установки города для погоды
    dp.message(WeatherState.setting_city, ~Command("cancel"))(handle_weather_city_input)
    # Обработка установки времени для погоды
    dp.message(WeatherState.setting_time, ~Command("cancel"))(handle_weather_time_input)

    # Команда /done
    dp.message(Command("done"))(cmd_done)

    # Обработка триггерных слов - проверяем все текстовые сообщения
    dp.message(F.text)(handle_shopping_message)

    # Callbacks
    dp.callback_query(F.data.startswith("shopping_"))(handle_shopping_callback)
    dp.callback_query(F.data.startswith("edit_"))(handle_edit_list_callback)
    dp.callback_query(F.data.startswith("back_edit_"))(handle_back_from_edit_callback)
    dp.callback_query(F.data.startswith("delete_"))(handle_delete_item_callback)
    dp.callback_query(F.data.startswith("toggle_"))(handle_toggle_item_callback)
    dp.callback_query(F.data.startswith("clear_"))(handle_clear_list_callback)
    dp.callback_query(F.data == "back_to_main")(handle_back_callback)
    dp.callback_query(F.data == "back_to_shopping")(handle_shopping_button)
    dp.callback_query(F.data == "back_to_settings")(handle_back_to_settings_callback)
    dp.callback_query(F.data.startswith("settings_magnit"))(handle_settings_category_callback)
    dp.callback_query(F.data.startswith("settings_fixprice"))(handle_settings_category_callback)
    dp.callback_query(F.data.startswith("settings_other"))(handle_settings_category_callback)
    dp.callback_query(F.data == "settings_triggers")(handle_settings_triggers_callback)
    dp.callback_query(F.data == "settings_visibility")(handle_settings_visibility_callback)
    dp.callback_query(F.data == "settings_weather")(handle_settings_weather_callback)
    dp.callback_query(F.data == "weather_set_city")(handle_weather_set_city_callback)
    dp.callback_query(F.data == "weather_set_time")(handle_weather_set_time_callback)
    dp.callback_query(F.data.startswith("weather_toggle_"))(handle_weather_toggle_callback)
    dp.callback_query(F.data.startswith("settings_toggle_"))(handle_settings_toggle_callback)
    dp.callback_query(F.data.startswith("settings_edit_name_"))(handle_settings_edit_name_callback)
    dp.callback_query(F.data.startswith("settings_edit_desc_"))(handle_settings_edit_desc_callback)
    dp.callback_query(F.data.startswith("settings_edit_short_"))(handle_settings_edit_short_callback)
    dp.callback_query(F.data.startswith("settings_edit_trigger_"))(handle_settings_edit_trigger_callback)
    
    # Сброс профиля
    dp.callback_query(F.data == "settings_reset_profile")(handle_settings_reset_profile_callback)
    dp.callback_query(F.data == "reset_profile_confirm")(handle_reset_profile_confirm_callback)
    dp.callback_query(F.data == "reset_profile_cancel")(handle_reset_profile_cancel_callback)
    
    # Админ-панель
    dp.callback_query(F.data == "admin_panel")(handle_admin_panel_callback)
    dp.callback_query(F.data == "admin_update_bot")(handle_admin_update_bot_callback)

    # Рецепты callbacks
    dp.callback_query(F.data == "recipe_add_new")(handle_recipe_add_new_callback)
    dp.callback_query(F.data.startswith("recipe_view_"))(handle_recipe_view_callback)
    dp.callback_query(F.data.startswith("recipe_add_to_cart_"))(handle_recipe_add_to_cart_callback)
    dp.callback_query(F.data.startswith("recipe_delete_"))(handle_recipe_delete_callback)
    dp.callback_query(F.data == "back_to_recipes")(handle_back_to_recipes_callback)

    # Запуск планировщика напоминаний
    asyncio.create_task(reminder_scheduler(bot))
    asyncio.create_task(weather_scheduler(bot))
    asyncio.create_task(notify_admin_on_startup(bot))

    print(f"Бот запущен (версия {BOT_VERSION})...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
