@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Ejecuta setup_windows.bat primero.
  pause
  exit /b 1
)
cd /d "%~dp0frontend"
call npm run build
if errorlevel 1 (
  echo Error compilando React.
  pause
  exit /b 1
)
cd /d "%~dp0"
start "Roadkill Web MVP" /D "%~dp0" cmd /k ".venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000"
timeout /t 3 >nul
start http://127.0.0.1:8000
