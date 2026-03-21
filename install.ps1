# ============================================================
# Скрипт установки TelegramAssistant на Windows
# ============================================================
# Использование:
#   powershell -ExecutionPolicy Bypass -File install.ps1
# ============================================================

# Цвета
function Write-Color {
    param($Text, $Color)
    Write-Host $Text -ForegroundColor $Color
}

# Логотип
Write-Host ""
Write-Color "╔══════════════════════════════════════════════════════════╗" Cyan
Write-Host "║   TelegramAssistant - Установка на Windows               ║"
Write-Color "╚══════════════════════════════════════════════════════════╝" Cyan
Write-Host ""

# ============================================================
# Проверка Python
# ============================================================
Write-Color "[1/6] Проверка Python..." Cyan

try {
    $pythonVersion = python --version 2>&1
    Write-Color "   ✓ Python найден: $pythonVersion" Green
} catch {
    Write-Color "   ❌ Python не найден!" Red
    Write-Color "   Установи Python с https://www.python.org/downloads/" Yellow
    Write-Color "   ✅ Отметь 'Add Python to PATH' при установке!" Yellow
    exit 1
}

# ============================================================
# Проверка Git
# ============================================================
Write-Color "`n[2/6] Проверка Git..." Cyan

try {
    $gitVersion = git --version 2>&1
    Write-Color "   ✓ Git найден: $gitVersion" Green
} catch {
    Write-Color "   ❌ Git не найден!" Red
    Write-Color "   Установи Git с https://git-scm.com/download/win" Yellow
    exit 1
}

# ============================================================
# Клонирование репозитория
# ============================================================
Write-Color "`n[3/6] Загрузка проекта..." Cyan

$projectPath = Join-Path $HOME "TelegramAssistant"

if (Test-Path $projectPath) {
    Write-Color "   ⊘ Проект уже существует, обновляем..." Yellow
    Set-Location $projectPath
    git pull 2>&1 | ForEach-Object { Write-Host "   $_" }
} else {
    Write-Color "   Скачивание из GitHub..." Yellow
    git clone https://github.com/Drentis/TelegramAssistant.git $projectPath 2>&1 | ForEach-Object { Write-Host "   $_" }
    Set-Location $projectPath
}

Write-Color "   ✓ Проект загружен в: $projectPath" Green

# ============================================================
# Виртуальное окружение
# ============================================================
Write-Color "`n[4/6] Настройка виртуального окружения..." Cyan

if (-not (Test-Path "venv")) {
    Write-Color "   Создание venv..." Yellow
    python -m venv venv
} else {
    Write-Color "   ✓ venv уже существует" Green
}

Write-Color "   Активация venv..." Yellow
& ".\venv\Scripts\Activate.ps1"

Write-Color "   Установка зависимостей..." Yellow
pip install --upgrade pip -q
pip install -r requirements.txt -q

Write-Color "   ✓ Зависимости установлены" Green

# ============================================================
# Настройка .env
# ============================================================
Write-Color "`n[5/6] Настройка токенов" Cyan

Write-Host ""
Write-Color "╔══════════════════════════════════════════════════════════╗" Cyan
Write-Host "║              НАСТРОЙКА TELEGRAM BOT TOKEN                ║"
Write-Color "╠══════════════════════════════════════════════════════════╣" Cyan
Write-Host "║  1. Откройте Telegram и найдите @BotFather               ║"
Write-Host "║  2. Отправьте команду /newbot                            ║"
Write-Host "║  3. Придумайте имя бота (например: MyNotebookBot)        ║"
Write-Host "║  4. Придумайте username (например: my_notebook_bot)      ║"
Write-Host "║  5. Скопируйте полученный токен                          ║"
Write-Color "╚══════════════════════════════════════════════════════════╝" Cyan
Write-Host ""

# Ввод токена бота
while ($true) {
    $botToken = Read-Host "   Введите токен бота"
    
    if ($botToken -like "*:*") {
        Write-Color "   ✓ Токен принят" Green
        break
    } else {
        Write-Color "   ❌ Неверный формат! Токен должен содержать ':'" Red
        Write-Color "   Попробуйте ещё раз" Yellow
    }
}

Write-Host ""
Write-Color "╔══════════════════════════════════════════════════════════╗" Cyan
Write-Host "║           НАСТРОЙКА OPENWEATHERMAP API KEY               ║"
Write-Color "╠══════════════════════════════════════════════════════════╣" Cyan
Write-Host "║  API ключ для прогноза погоды (ОПЦИОНАЛЬНО)              ║"
Write-Host "║  • Получить на https://openweathermap.org/api            ║"
Write-Host "║  • Или нажмите Enter для пропуска                        ║"
Write-Color "╚══════════════════════════════════════════════════════════╝" Cyan
Write-Host ""

# Ввод API ключа
$weatherKey = Read-Host "   Введите API ключ погоды (или нажмите Enter для пропуска)"

if ([string]::IsNullOrWhiteSpace($weatherKey)) {
    Write-Color "   ⊘ Пропущено (погода будет недоступна)" Yellow
    $weatherKey = ""
} else {
    Write-Color "   ✓ API ключ принят" Green
}

# Создание .env файла
Write-Color "`n   Создание файла .env..." Yellow

$envContent = @"
# Токен бота (получить у @BotFather)
BOT_TOKEN=$botToken

# OpenWeatherMap API ключ (получить на https://openweathermap.org/api)
WEATHER_API_KEY=$weatherKey
"@

$envContent | Out-File -FilePath ".env" -Encoding UTF8

Write-Color "   ✓ Файл .env создан" Green

# ============================================================
# Создание файла запуска
# ============================================================
Write-Color "`n[6/6] Создание файла запуска..." Cyan

$startBatch = @"
@echo off
echo ========================================
echo   TelegramAssistant - Telegram Bot
echo ========================================
echo.
cd /d %~dp0
call venv\Scripts\activate
echo Запуск бота...
python main.py
pause
"@

$startBatch | Out-File -FilePath "start.bat" -Encoding Default

Write-Color "   ✓ Файл start.bat создан" Green

# ============================================================
# Финальное сообщение
# ============================================================
Write-Host ""
Write-Color "╔══════════════════════════════════════════════════════════╗" Green
Write-Host "║                  ✅ УСТАНОВКА ЗАВЕРШЕНА!                 ║"
Write-Color "╠══════════════════════════════════════════════════════════╣" Cyan
Write-Host "║  ✓ Проект установлен в: $projectPath"
Write-Host "║  ✓ Виртуальное окружение настроено"
Write-Host "║  ✓ Зависимости установлены"
Write-Host "║  ✓ Токены настроены"
Write-Host "╠══════════════════════════════════════════════════════════╣" Cyan
Write-Host "║  Запуск бота:                                            ║"
Write-Host "║  1. Открой файл start.bat в папке проекта                ║"
Write-Host "║  2. Или выполни в PowerShell:                            ║"
Write-Host "║     cd $projectPath                                      ║"
Write-Host "║     .\start.bat                                          ║"
Write-Host "╠══════════════════════════════════════════════════════════╣" Cyan
Write-Host "║  Проверка работы:                                        ║"
Write-Host "║  1. Открой Telegram                                      ║"
Write-Host "║  2. Найди своего бота по username                        ║"
Write-Host "║  3. Отправь /start                                       ║"
Write-Color "╚══════════════════════════════════════════════════════════╝" Green
Write-Host ""

if ($botToken) {
    Write-Color "✓ Токен бота настроен" Green
}

if ($weatherKey) {
    Write-Color "✓ API ключ погоды настроен" Green
} else {
    Write-Color "⊘ API ключ погоды не установлен (погода будет недоступна)" Yellow
}

Write-Host ""
Write-Color "🎉 Отправьте /start вашему боту в Telegram!" Green
Write-Host ""

# Автозапуск (опционально)
Write-Host ""
$autoStart = Read-Host "Хочешь добавить бота в автозапуск? (y/n)"

if ($autoStart -eq 'y' -or $autoStart -eq 'Y') {
    $startupPath = [Environment]::GetFolderPath("Startup")
    $shortcutPath = Join-Path $startupPath "TelegramAssistant.lnk"

    $WScript = New-Object -ComObject WScript.Shell
    $shortcut = $WScript.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = (Join-Path $projectPath "start.bat")
    $shortcut.WorkingDirectory = $projectPath
    $shortcut.Save()

    Write-Color "✓ Бот добавлен в автозапуск" Green
}

Write-Host ""
Write-Color "Нажми Enter для запуска бота..." Yellow
Read-Host

# Запуск бота
& ".\venv\Scripts\Activate.ps1"
python main.py
