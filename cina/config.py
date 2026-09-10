import os
import re
import sys
import json
from pathlib import Path
from typing import Dict, Any

def get_project_dir() -> Path:
    """Devuelve el directorio raíz del proyecto."""
    return Path(__file__).resolve().parent.parent

def get_config_dir() -> Path:
    """Determina la ruta de configuración en Windows (con fallback)."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "cina"
    return Path.home() / ".config" / "cina"

PROJECT_DIR = get_project_dir()
LOCAL_CONFIG_FILE = PROJECT_DIR / "config.json"
LOCAL_ENV_FILE = PROJECT_DIR / ".env"

CONFIG_DIR = get_config_dir()
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "api_key": "",
    "model": "gemini-3.7-flash",
    "voice": "es-ES-AlvaroNeural",
    "tts_engine": "edge-tts",  # "edge-tts" o "sapi"
    "speech_rate": "+0%",
    "speech_volume": "+0%",
    "hotkey": "<ctrl>+<alt>+s",
    "capture_backend": "pillow",  # "pillow" nativo de Windows
    "prompt_style": "concise_answer",  # Respuestas directas preparadas para locución
    "play_start_chime": False,  # No emitir sonidos al capturar (100% silencioso)
    "tcp_port": 47832           # Puerto IPC local para Windows
}

AVAILABLE_VOICES = [
    ("es-ES-AlvaroNeural", "Español (España) - Álvaro (Hombre)"),
    ("es-ES-ElviraNeural", "Español (España) - Elvira (Mujer)"),
    ("es-MX-DaliaNeural", "Español (México) - Dalia (Mujer)"),
    ("es-MX-JorgeNeural", "Español (México) - Jorge (Hombre)"),
    ("es-AR-TomasNeural", "Español (Argentina) - Tomás (Hombre)"),
    ("es-AR-ElenaNeural", "Español (Argentina) - Elena (Mujer)"),
    ("es-CO-GonzaloNeural", "Español (Colombia) - Gonzalo (Hombre)"),
    ("es-CO-SalomeNeural", "Español (Colombia) - Salomé (Mujer)"),
    ("es-CL-LorenzoNeural", "Español (Chile) - Lorenzo (Hombre)"),
    ("es-CL-CatalinaNeural", "Español (Chile) - Catalina (Mujer)"),
]

AVAILABLE_MODELS = [
    ("gemini-3.7-flash", "Gemini 3.7 Flash (Recomendado y Multimodal)"),
    ("gemini-3.6-flash", "Gemini 3.6 Flash (Alta estabilidad)"),
    ("gemini-3.5-flash-lite", "Gemini 3.5 Flash Lite (Ultra Rápido, ~0.7s)"),
    ("gemini-flash-latest", "Gemini Flash Latest (Última versión)"),
]


def clean_api_key_str(raw: str) -> str:
    """Limpia comillas, prefijos 'export', 'GEMINI_API_KEY=', etc."""
    if not raw:
        return ""
    # Quitar posibles saltos de línea y espacios
    s = raw.strip()
    # Si copiaron la línea entera tipo "export GEMINI_API_KEY=xxx" o "set GEMINI_API_KEY=xxx"
    for prefix in ["export ", "set "]:
        if s.lower().startswith(prefix):
            s = s[len(prefix):].strip()
    if "=" in s and not s.startswith("AQ.") and not s.startswith("AIza"):
        s = s.split("=", 1)[1].strip()
    # Quitar comillas simples, dobles o tipográficas envolventes
    s = s.strip(' \t\r\n\'"“”«»')
    return s


def parse_dotenv(env_path: Path) -> Dict[str, str]:
    """Parsea archivos .env simples sin dependencias externas."""
    env_vars = {}
    if not env_path.exists():
        return env_vars
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = clean_api_key_str(val)
                    env_vars[key] = val
    except Exception as e:
        print(f"[Config] Error al leer {env_path}: {e}")
    return env_vars


class ConfigManager:
    def __init__(self):
        self.config: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self.load()

    def load(self) -> Dict[str, Any]:
        """Carga la configuración combinando APPDATA, carpeta local, .env y variables de entorno."""
        # 1. Cargar desde APPDATA / ~/.config
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.config.update(data)
        except Exception as e:
            print(f"[Config] Error al cargar {CONFIG_FILE}: {e}")

        # 2. Cargar desde config.json local del proyecto si existe
        if LOCAL_CONFIG_FILE.exists() and LOCAL_CONFIG_FILE != CONFIG_FILE:
            try:
                with open(LOCAL_CONFIG_FILE, "r", encoding="utf-8") as f:
                    local_data = json.load(f)
                    if local_data.get("api_key"):
                        self.config.update(local_data)
            except Exception as e:
                print(f"[Config] Error al cargar {LOCAL_CONFIG_FILE}: {e}")

        # 3. Cargar desde archivo .env en la raíz del proyecto
        env_vars = parse_dotenv(LOCAL_ENV_FILE)
        if env_vars.get("GEMINI_API_KEY") and not self.config.get("api_key"):
            self.config["api_key"] = env_vars["GEMINI_API_KEY"]
        elif env_vars.get("GOOGLE_API_KEY") and not self.config.get("api_key"):
            self.config["api_key"] = env_vars["GOOGLE_API_KEY"]

        # 4. Comprobar variables de entorno del sistema (GEMINI_API_KEY o GOOGLE_API_KEY)
        for env_var_name in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
            env_val = os.environ.get(env_var_name)
            if env_val:
                cleaned = clean_api_key_str(env_val)
                if cleaned:
                    # La variable de entorno tiene máxima prioridad
                    self.config["api_key"] = cleaned
                    break

        # Limpiar la clave final por si tenía comillas
        if self.config.get("api_key"):
            self.config["api_key"] = clean_api_key_str(self.config["api_key"])

        return self.config

    def save(self) -> bool:
        """Guarda la configuración actual en el disco tanto en APPDATA como localmente si aplica."""
        try:
            if self.config.get("api_key"):
                self.config["api_key"] = clean_api_key_str(self.config["api_key"])

            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            # También guardar una copia en el directorio del proyecto si es accesible
            try:
                with open(LOCAL_CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

            return True
        except Exception as e:
            print(f"[Config] Error al guardar configuración: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if key == "api_key" and isinstance(value, str):
            value = clean_api_key_str(value)
        self.config[key] = value
        self.save()


config_mgr = ConfigManager()
