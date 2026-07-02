@echo off
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo Python tapilmadi / Python не найден.
    echo Yukleyin: https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Muhit yaradilir / Создание окружения...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

pip show PySide6 >nul 2>&1
if errorlevel 1 (
    echo Asililiklar yuklenilir / Установка зависимостей...
    pip install -r requirements.txt
)

python main.py
