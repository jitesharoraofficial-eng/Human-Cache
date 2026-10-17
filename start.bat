@echo off
title Human Cache - Startup Launcher
echo ========================================================
echo           Starting Human Cache Services
echo ========================================================
echo.

echo [1/2] Starting FastAPI Backend on port 8000 ...
start "Human Cache Backend" cmd /k ".\venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000 --host 0.0.0.0 --reload"

timeout /t 3 /nobreak >nul

echo [2/2] Starting Next.js Frontend on http://localhost:3000 ...
cd frontend
start "Human Cache Frontend" cmd /k "npm run dev"

echo.
echo All services launched!
echo Open your browser at: http://localhost:3000
echo ========================================================
timeout /t 5 >nul
