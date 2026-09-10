# CINA - Asistente de Pantalla y Audio con IA (Edición Windows 10 / 11)

Aplicación para **Microsoft Windows** que se ejecuta en segundo plano o minimizada, captura la pantalla de manera completamente silenciosa (sin flashes, sin sonido de obturador, sin ventanas emergentes ni perder el foco), analiza la imagen con la API multimodal de **Google Gemini** para detectar preguntas, ejercicios o cuestionarios, y responde mediante **voz natural en tiempo real** a través de tus auriculares o altavoces.

---

## Características Principales en Windows

- **Captura 100% Silenciosa con DPI Awareness**: Utiliza la librería nativa Pillow (`PIL.ImageGrab`) con soporte de alta resolución (`SetProcessDPIAware`), capturando monitores individuales o configuraciones multimonitor a resolución nativa exacta sin recortes por escala (125%/150%).
- **Disparador Invisible sin Ventana Negra**: Incluye `cina-trigger.vbs` que permite disparar la captura desde atajos de teclado o botones macro sin que aparezca ninguna ventana de consola negra (cmd) parpadeante.
- **Audio Nativo sin Dependencias Externas**:
  - Síntesis de voz en español natural con **Edge-TTS** (voces neuronales de España, México, Argentina, Colombia, Chile).
  - Reproducción directa de MP3 con la API multimedia nativa de Windows (`winmm.dll` MCI API) o PowerShell MediaPlayer, sin necesidad de instalar códecs, ffmpeg ni reproductores de terceros.
  - Fallback offline integrado con el motor **SAPI de Windows** (`SAPI.SpVoice`).
- **IA Multimodal Gemini**: Soporta `gemini-3.7-flash` y `gemini-3.5-flash-lite` con razonamiento visual especializado en exámenes, cuestionarios, opciones múltiples, problemas de lógica y código.
- **Manejo Inteligente de Cuotas (Error 429)**:
  - **Fallback automático**: Conmuta automáticamente entre `gemini-3.7-flash` y `gemini-3.5-flash-lite` en milisegundos ante saturación de cuota.
  - **Rotación de múltiples claves**: Permite configurar varias API Keys separadas por comas.
  - **Mensajes de voz limpios**: Te avisa en lenguaje humano natural con el tiempo de espera restante sin leer código JSON.
- **Doble Sistema de Atajo Global**:
  - Escuchador global en segundo plano mediante `pynput` (`Ctrl+Alt+S`).
  - Atajo nativo de Windows integrado en el acceso directo del Escritorio.
  - Servidor IPC local de alta velocidad (`127.0.0.1:47832`).

---

## Despliegue Rápido en 1 Paso

### Requisitos Previos
Tener instalado **Python 3.10 o superior** en Windows (descárgalo desde [python.org](https://www.python.org/downloads/)).
> **IMPORTANTE**: Al instalar Python, asegúrate de marcar la casilla **"Add python.exe to PATH"**.

### Instalación Automática
Simplemente haz **doble clic en el archivo:**
```cmd
setup.bat
```

El script `setup.bat`:
1. Verifica la versión de Python.
2. Crea un entorno virtual aislado (`venv`).
3. Instala todas las dependencias (`google-genai`, `pillow`, `edge-tts`, `requests`, `pynput`).
4. Genera los accesos directos en el **Escritorio**:
   - `CINA AI Assistant.lnk` (para abrir la aplicación).
   - `CINA Trigger.lnk` (asociado al atajo global `Ctrl+Alt+S`).

---

## Cómo Iniciar la Aplicación

Puedes iniciar CINA de dos formas:
1. Haciendo doble clic en el acceso directo del Escritorio **"CINA AI Assistant"**.
2. O haciendo doble clic en el archivo **`run.bat`**.

---

## Configuración de la API Key

1. **Obtén tu clave gratuita** en [Google AI Studio](https://aistudio.google.com/).
2. En la ventana de la aplicación, ingresa tu clave en el campo **Gemini API Key** y pulsa **Guardar**.
   - *Tip*: Puedes ingresar varias claves separadas por comas para rotación automática si alcanzas los límites de cuota gratuita.
   - También puedes definir la variable de entorno de Windows: `setx GEMINI_API_KEY "tu-clave"`.

---

## Cómo Usar el Atajo de Teclado en Windows

1. Inicia la aplicación y minimízala si lo deseas.
2. Cada vez que tengas una pregunta o examen en pantalla, presiona:
   ```
   Ctrl + Alt + S
   ```
3. CINA capturará la pantalla en silencio y escucharás la respuesta por voz en tus auriculares en cuestión de segundos.

### Disparo Invisible para Teclados Macro o Stream Deck
Si tienes un teclado con teclas macro (Logitech G-Hub, Razer Synapse, Elgato Stream Deck, etc.), puedes asociar la tecla para que ejecute directamente:
```cmd
wscript.exe "C:\ruta\hacia\cina-windows\cina-trigger.vbs"
```
Esto disparará la captura de forma completamente invisible y silenciosa.

---

## Modos de Ejecución Avanzados

- **Modo Demonio sin Ventana Gráfica (Headless)**:
  Haz doble clic en:
  ```cmd
  run-headless.bat
  ```
- **Disparo manual desde símbolo del sistema (CMD / PowerShell)**:
  ```cmd
  cina-trigger.bat
  ```

