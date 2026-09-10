@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" main.py --trigger %*
) else (
    python main.py --trigger %*
)

