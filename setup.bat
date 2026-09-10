@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ============================================================
echo  CINA AI Assistant - Instalador y Desplegador para Windows
echo ============================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: 1. Verificar Python
echo [1/4] Verificando instalacion de Python...
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] No se encontro Python en el PATH del sistema.
        echo Por favor instala Python 3.10 o superior desde https://www.python.org/downloads/
        echo Asegurate de marcar la casilla "Add python.exe to PATH" durante la instalacion.
        pause
        exit /b 1
    ) else (
        set "PY_CMD=py -3"
    )
) else (
    set "PY_CMD=python"
)

%PY_CMD% --version
echo       Python detectado correctamente.
echo.

:: 2. Crear Entorno Virtual
echo [2/4] Configurando entorno virtual (venv)...
if not exist "venv\" (
    %PY_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
    echo       Entorno virtual creado exitosamente.
) else (
    echo       Entorno virtual existente detectado.
)
echo.

:: 3. Instalar Dependencias
echo [3/4] Instalando dependencias de requirements.txt...
call venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>nul
call venv\Scripts\pip.exe install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Ocurrio un problema al instalar las dependencias de Python.
    pause
    exit /b 1
)
echo       Dependencias instaladas con exito.
echo.

:: 4. Crear accesos directos en el Escritorio
echo [4/4] Creando accesos directos en el Escritorio...
cscript //nologo create_shortcut.vbs
echo.

echo ============================================================
echo  Instalacion completada con exito en Windows!
echo ============================================================
echo.
echo Para iniciar la aplicacion:
echo    - Ejecuta el archivo: run.bat
echo    - O usa el acceso directo "CINA AI Assistant" en tu Escritorio.
echo.
echo Atajo global configurado:
echo    - Presiona Ctrl+Alt+S en cualquier momento mientras este activo.
echo ============================================================
echo.
pause

