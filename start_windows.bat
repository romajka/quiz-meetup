@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "run.py"
    exit /b %errorlevel%
)

where python >nul 2>nul
if %errorlevel%==0 (
    python "run.py"
    exit /b %errorlevel%
)

echo Python не найден. Установите Python 3.11+ или создайте .venv.
exit /b 1
