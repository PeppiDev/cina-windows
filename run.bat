@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if not exist "venv\Scripts\python.exe" (
    echo [Cina] Entorno virtual no detectado. Iniciando instalacion automatica...
    call setup.bat
)

if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" main.py %*
) else (
    "venv\Scripts\python.exe" main.py %*
)

