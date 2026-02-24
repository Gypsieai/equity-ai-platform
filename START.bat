@echo off
title StockPulse AI - Neural Market Intelligence
color 0A

echo.
echo  ========================================
echo   StockPulse AI - Starting Server...
echo  ========================================
echo.

cd /d "%~dp0backend"

echo [*] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

echo [*] Installing dependencies...
pip install -q -r requirements.txt

echo [*] Starting StockPulse AI Server...
echo.
echo  Dashboard will open automatically...
echo  Server URL: http://localhost:8000
echo  API Docs:   http://localhost:8000/docs
echo.
echo  Press Ctrl+C to stop the server
echo.

timeout /t 2 /nobreak >nul
start http://localhost:8000/dashboard

python server.py

pause
