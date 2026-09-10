# AGENT GUIDE & SYSTEM ARCHITECTURE: CINA (WINDOWS EDITION)

Este documento está diseñado específicamente para que **agentes de Inteligencia Artificial** puedan auditar, extender, probar y desplegar esta edición de **CINA** en cualquier entorno con sistema operativo **Microsoft Windows (Windows 10 / 11)**.

---

## 1. Propósito de la Migración a Windows

Adaptar el asistente en tiempo real CINA al entorno Windows reemplazando componentes de Linux (KDE Spectacle, sockets Unix de `/tmp/`, PipeWire/PulseAudio y scripts bash) por primitivas nativas de Windows de alto rendimiento y cero dependencias pesadas:
- **Captura**: `PIL.ImageGrab` + `ctypes.windll.user32.SetProcessDPIAware()`.
- **Reproducción de Audio**: Windows Multimedia API (`winmm.dll` MCI) + PowerShell MediaPlayer + SAPI Speech API fallback.
- **IPC**: Localhost TCP (`127.0.0.1:47832`).
- **Disparador Invisible**: Windows Script Host (`cina-trigger.vbs` ejecutando `pythonw.exe`).
- **Lanzadores**: Scripts `.bat` y `.vbs` con rutas relativas (`%~dp0`).

---

## 2. Árbol del Repositorio (Windows)

```
cina-windows/
├── cina/
│   ├── __init__.py           # Metadata del paquete
│   ├── config.py             # Configuración en %APPDATA%\cina\config.json
│   ├── capture.py            # Captura silenciosa con Pillow y DPI awareness
│   ├── gemini_service.py     # Integración Gemini con fallback 429 y rotación de claves
│   ├── tts_service.py        # Edge-TTS + winmm MCI API + SAPI Windows fallback
│   ├── ipc_service.py        # Servidor y cliente TCP en 127.0.0.1:47832
│   ├── hotkey_service.py     # Listener global pynput en Windows + IPC
│   └── gui.py                # Interfaz gráfica moderna en Tkinter (tema oscuro Fluent)
├── main.py                   # Entrypoint único con modos GUI, headless y trigger
├── cina-trigger.bat          # Disparador para consola CMD/PowerShell
├── cina-trigger.vbs          # Disparador 100% invisible (sin parpadeo de consola)
├── run.bat                   # Lanzador de la interfaz gráfica
├── run-headless.bat          # Lanzador modo demonio sin interfaz
├── setup.bat                 # Instalador automático en 1 paso para Windows
├── create_shortcut.vbs       # Generador de accesos directos con hotkey Ctrl+Alt+S
├── requirements.txt          # Dependencias de Python para Windows
├── README.md                 # Documentación para usuarios de Windows
├── AGENT.md                  # Este documento
└── .gitignore                # Reglas de exclusión de git
```

---

## 3. Detalles de Implementación de la Arquitectura

### A. Captura Silenciosa e Invisible (`cina/capture.py`)
- Al cargar el módulo en Windows, se invoca `ctypes.windll.user32.SetProcessDPIAware()`. Esto evita que Windows escale virtualmente la ventana de captura, garantizando que el texto en pantalla se capture con máxima nitidez sin borrosidad ni recortes.
- Se invoca `ImageGrab.grab(all_screens=True)` para cubrir sistemas de múltiples pantallas.
- `optimize_image()` redimensiona proporcionalmente a un ancho máximo de 1920px y comprime a JPEG con calidad 85%, reduciendo el payload de red de ~5MB a ~250KB con latencia de subida inferior a 300ms.

### B. Síntesis y Reproducción de Audio (`cina/tts_service.py`)
1. **Generación**: `edge_tts.Communicate` genera un MP3 temporal usando voces neuronales naturales de Microsoft (ej: `es-ES-AlvaroNeural`, `es-MX-DaliaNeural`).
2. **Reproducción Primaria (MCI API)**:
   - Se utiliza `winmm.dll` mediante `ctypes`.
   - Se obtiene la ruta corta con `kernel32.GetShortPathNameW` para evitar problemas con espacios en rutas de Windows (`C:\Program Files\...`).
   - Se ejecuta el comando MCI `open "{path}" type mpegvideo alias cina_audio` y luego `play cina_audio wait`.
   - Al llamar a `stop()`, se ejecuta `stop cina_audio` y `close cina_audio`, silenciando el audio instantáneamente.
3. **Reproducción Secundaria**: PowerShell `System.Windows.Media.MediaPlayer`.
4. **Fallback Offline**: Si no hay conexión a Internet, invoca Windows SAPI:
   ```cmd
   powershell -WindowStyle Hidden -Command "(New-Object -ComObject SAPI.SpVoice).Speak('...')"
   ```

### C. Socket IPC y Disparador Invisible (`cina/ipc_service.py`)
- Escucha exclusivamente en la interfaz de loopback `127.0.0.1` en el puerto configurable `47832`.
- Protocolo textual ligero (`TRIGGER`, `PING`, `STOP`).
- `cina-trigger.vbs` utiliza `wscript.exe` para invocar `pythonw.exe main.py --trigger` con flag de ventana oculta (0), eliminando cualquier ventana emergente o parpadeo visual.

---

## 4. Comandos de Verificación para Agentes

Para validar los módulos de Python en este directorio:

```bash
# 1. Verificar importación de todos los módulos
python3 -c "
import sys; sys.path.insert(0, '.')
import cina
from cina.config import config_mgr
from cina.capture import ScreenCapture
from cina.gemini_service import GeminiService
from cina.tts_service import TTSService
from cina.ipc_service import IPCServer, IPCClient
from cina.hotkey_service import HotkeyService
print('Todos los módulos de cina-windows se importan correctamente.')
"

# 2. Verificar servidor y cliente IPC TCP
python3 -c "
import sys, time; sys.path.insert(0, '.')
from cina.ipc_service import IPCServer, IPCClient
triggered = False
def on_trig():
    global triggered; triggered = True
server = IPCServer(on_trigger=on_trig)
server.start()
time.sleep(0.2)
assert IPCClient.is_server_running(), 'Servidor no responde a PING'
assert IPCClient.send_trigger(), 'Fallo al enviar TRIGGER'
time.sleep(0.2)
server.stop()
assert triggered, 'Callback no ejecutado'
print('Prueba IPC TCP exitosa en 127.0.0.1:47832.')
"

# 3. Probar captura de pantalla silenciosa
python3 -c "
import sys; sys.path.insert(0, '.')
from cina.capture import ScreenCapture
cap = ScreenCapture()
p = cap.capture_silent()
assert p, 'Captura fallida'
print('Captura exitosa:', p)
"

# 4. Probar síntesis y reproducción de voz
python3 -c "
import sys; sys.path.insert(0, '.')
from cina.tts_service import TTSService
tts = TTSService()
tts._speak_worker('Prueba de voz en Windows.')
print('TTS OK')
"
```

---

## 5. Despliegue Autónomo en Windows (Instrucciones para Agentes)

Si eres un agente ejecutando comandos en un sistema Windows (a través de PowerShell o CMD):

```powershell
# 1. Clonar el repositorio
git clone https://github.com/PeppiDev/cina-windows.git
cd cina-windows

# 2. Despliegue automatizado en 1 comando (ejecuta setup.bat)
.\setup.bat

# 3. O alternativamente mediante PowerShell nativo:
python -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\pip.exe install -r requirements.txt
cscript //nologo create_shortcut.vbs

# 4. Configurar la clave de API de Gemini:
# Opción A: Variable de entorno del sistema
[System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', 'TU_API_KEY_AQUI', 'User')

# Opción B: Archivo JSON de configuración
$configDir = "$env:APPDATA\cina"
if (!(Test-Path $configDir)) { New-Item -ItemType Directory -Path $configDir -Force }
$cfg = @{
    api_key = "TU_API_KEY_AQUI"
    model = "gemini-3.7-flash"
    voice = "es-ES-AlvaroNeural"
    tts_engine = "edge-tts"
    speech_rate = "+0%"
    speech_volume = "+0%"
    hotkey = "<ctrl>+<alt>+s"
    capture_backend = "pillow"
    prompt_style = "concise_answer"
    play_start_chime = $false
    tcp_port = 47832
} | ConvertTo-Json
Set-Content -Path "$configDir\config.json" -Value $cfg -Encoding UTF8

# 5. Iniciar la aplicación
# Modo normal (GUI):
.\run.bat

# Modo headless (demonio en segundo plano):
.\run-headless.bat

# Modo trigger (disparo de prueba):
.\venv\Scripts\python.exe main.py --trigger
```

---

## 6. Matriz de Solución de Problemas (Troubleshooting)

| Síntoma en Windows | Causa Raíz | Solución para el Agente |
|---|---|---|
| `python: orden no encontrada` | Python no fue agregado al PATH del sistema al instalarse. | Usar `py -3` o agregar `C:\Users\<user>\AppData\Local\Programs\Python\Python3xx` al PATH. |
| Ventana negra de consola parpadea al presionar atajo | Se ejecutó un script `.bat` en lugar de `.vbs`. | Usar siempre `cina-trigger.vbs` o `pythonw.exe` (con "w" final para silenciar consola). |
| Texto de pantalla borroso o capturado recortado en laptop | Escala de pantalla de Windows en 125% o 150%. | `cina/capture.py` incluye `SetProcessDPIAware()`, que evita automáticamente este fallo. |
| Sin audio ni altavoces activos | Dispositivo de audio de Windows deshabilitado. | Verificar salida de audio con `powershell -c "[System.Media.SystemSounds]::Beep.Play()"`. |
| Error 429 de Google Gemini | Límite de cuota alcanzado. | El servicio rota automáticamente a `gemini-3.5-flash-lite` y a claves adicionales si se ingresaron separadas por comas. |
