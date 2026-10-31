@echo off
title GreenMine Demo
cd /d "%~dp0"

:: بررسی وجود محیط مجازی
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating Environment...
call venv\Scripts\activate

:: بررسی نصب بودن استریم‌لیت
python -c "import streamlit" 2>nul
if %errorlevel% neq 0 (
    echo Installing requirements...
    pip install streamlit pandas altair requests
)

echo Running GreenMine...
streamlit run proj1.py

pause
