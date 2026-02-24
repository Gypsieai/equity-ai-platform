@echo off
title StockPulse AI - Portable Edition
color 0B

echo.
echo  ================================================
echo   StockPulse AI - Neural Market Intelligence
echo   Portable Edition - No Installation Required
echo  ================================================
echo.

cd /d "%~dp0"

echo [*] Starting StockPulse AI Server...
echo.
echo  Dashboard will open automatically in 3 seconds...
echo.
echo  Server URL: http://localhost:8000
echo  Dashboard:  http://localhost:8000/dashboard
echo  API Docs:   http://localhost:8000/docs
echo.
echo  Press Ctrl+C to stop the server
echo.

timeout /t 3 /nobreak >nul
start http://localhost:8000/dashboard

StockPulse-AI.exe

pause
