@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Ejecuta setup_windows.bat primero.
  pause
  exit /b 1
)
start "Roadkill API" /D "%~dp0" cmd /k ".venv\Scripts\python.exe -m uvicorn backend.app:app --reload --port 8000"
start "Roadkill React" /D "%~dp0frontend" cmd /k "npm run dev"
timeout /t 3 >nul
start http://localhost:5173
