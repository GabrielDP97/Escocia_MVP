@echo off
setlocal
cd /d "%~dp0"
if not exist .venv ( python -m venv .venv )
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
cd frontend
call npm install
cd ..
echo.
echo Instalacion terminada.
echo Usa start_dev_windows.bat o build_and_run_windows.bat
pause
